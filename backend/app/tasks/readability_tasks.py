# app/tasks/readability_tasks.py
import logging
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.readability_results import ReadabilityAnalysisResult
from app.services.stages.discover.readability_service import ReadabilityService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.readability.analyze_file")
def analyze_readability_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Analyze readability for each page of a file and aggregate into document-level results.
    """
    s = db.session()
    svc = ReadabilityService()

    try:
        # 1) Load pages for this file
        pages = (
            s.query(FilePage)
             .filter(FilePage.file_id == file_id)
             .order_by(asc(FilePage.page_number))
             .all()
        )
        total = len(pages)
        if total == 0:
            _finish_progress(s, progress_id, "completed", 100)
            return

        per_page_analysis = []  # [(page_number, analysis_dict)]
        done = 0

        # 2) Analyze readability for each page
        for page in pages:
            try:
                analysis = svc.analyze_page_readability(page.page_text or "")
                per_page_analysis.append((page.page_number, analysis))
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Readability] Failed page {getattr(page,'id','?')}: {e}")

            # Progress update (90% for page analysis, 10% for aggregation)
            pct = int((done / max(total, 1)) * 90)
            _bump_progress(s, progress_id, pct)

        # 3) Aggregate readability across all pages
        try:
            aggregated = svc.aggregate_readability_by_file(per_page_analysis)

            # 4) Save to ReadabilityAnalysisResult table
            _save_readability_result(s, file_id, aggregated)

            _finish_progress(s, progress_id, "completed", 100)
            log.info(f"[Readability] Completed file {file_id}: {aggregated['doc_metrics'].get('total_words', 0)} words analyzed")

        except Exception as e:
            s.rollback()
            log.error(f"[Readability] Aggregation failed for file {file_id}: {e}")
            _finish_progress(s, progress_id, "failed")

    except Exception:
        s.rollback()
        log.exception(f"[Readability] Task failed for file {file_id}")
        _finish_progress(s, progress_id, "failed")
        raise
    finally:
        s.close()


def _save_readability_result(s, file_id: str, aggregated: dict):
    """Save aggregated readability results to database."""
    try:
        # Mark previous results as inactive
        s.query(ReadabilityAnalysisResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})

        # Determine target audience based on readability level
        dominant_readability = aggregated.get("style_analysis", {}).get("dominant_readability_level", "unknown")
        target_audience_map = {
            "very_easy": "elementary",
            "easy": "middle_school",
            "moderate": "high_school",
            "difficult": "college",
            "very_difficult": "academic"
        }
        target_audience = target_audience_map.get(dominant_readability, "general")

        # Create new result
        result = ReadabilityAnalysisResult(
            file_id=file_id,
            doc_metrics=aggregated.get("doc_metrics", {}),
            per_page_analysis=aggregated.get("per_page_analysis", []),
            style_analysis=aggregated.get("style_analysis", {}),
            readability_scores=aggregated.get("readability_scores", {}),
            issues=aggregated.get("issues", []),
            recommendations=aggregated.get("recommendations", []),
            summary=aggregated.get("summary", ""),
            target_audience=target_audience,
            is_active=True
        )
        s.add(result)
        s.commit()
        log.info(f"[Readability] Saved ReadabilityAnalysisResult for file {file_id}")

    except Exception as e:
        log.error(f"[Readability] Failed to save ReadabilityAnalysisResult: {e}")
        raise


def _bump_progress(s, progress_id, pct: int):
    """Update progress percentage."""
    p = s.query(Progress).get(progress_id)
    if p:
        p.percentage = max(p.percentage or 0, int(pct))
        s.commit()


def _finish_progress(s, progress_id, status: str, pct: int = None):
    """Mark progress as completed or failed."""
    p = s.query(Progress).get(progress_id)
    if p:
        p.status = status
        if pct is not None:
            p.percentage = pct
        s.commit()
