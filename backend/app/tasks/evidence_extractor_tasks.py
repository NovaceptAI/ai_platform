# app/tasks/evidence_extractor_tasks.py
import logging
import time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import EvidenceExtractionResult
from app.services.stages.discover.evidence_extractor_service import EvidenceExtractorService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.evidence.build_for_file")
def build_evidence_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Extract evidence from each page of a file and aggregate into document-level results.
    """
    s = db.session()
    svc = EvidenceExtractorService()

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

        has_col = hasattr(FilePage, "page_evidence")
        per_page_evidence = []  # [(page_number, [evidence_items])]
        done = 0

        # 2) Extract evidence from each page
        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_evidence", None):
                    evidence = getattr(page, "page_evidence") or []
                else:
                    evidence = svc.extract_evidence_from_page(page.page_text or "")
                    if has_col:
                        setattr(page, "page_evidence", evidence)
                    s.commit()

                per_page_evidence.append((page.page_number, evidence))
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Evidence] Failed page {getattr(page,'id','?')}: {e}")

            # Progress update
            pct = int((done / max(total, 1)) * 90)  # Leave 10% for aggregation
            _bump_progress(s, progress_id, pct)

        # 3) Aggregate evidence across all pages
        try:
            aggregated = svc.aggregate_evidence_by_file(per_page_evidence)
            
            # 4) Save to EvidenceExtractionResult table
            _save_evidence_result(s, file_id, per_page_evidence, aggregated)
            
            _finish_progress(s, progress_id, "completed", 100)
            log.info(f"[Evidence] Completed file {file_id}: {aggregated['stats']['total_evidence_items']} evidence items")
            
        except Exception as e:
            s.rollback()
            log.error(f"[Evidence] Aggregation failed for file {file_id}: {e}")
            _finish_progress(s, progress_id, "failed")

    except Exception:
        s.rollback()
        log.exception(f"[Evidence] Task failed for file {file_id}")
        _finish_progress(s, progress_id, "failed")
        raise
    finally:
        s.close()


def _save_evidence_result(s, file_id: str, per_page_evidence: list, aggregated: dict):
    """Save aggregated evidence results to database."""
    try:
        # Check if EvidenceExtractionResult table exists, if not we'll just log
        try:
            from app.models.analysis_results import EvidenceExtractionResult
            
            # Mark previous results as inactive
            s.query(EvidenceExtractionResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})
            
            # Create new result
            result = EvidenceExtractionResult(
                file_id=file_id,
                evidence_by_page=per_page_evidence,
                aggregated_evidence=aggregated["all_evidence"],
                summary=aggregated["summary"],
                is_active=True
            )
            s.add(result)
            s.commit()
            log.info(f"[Evidence] Saved EvidenceExtractionResult for file {file_id}")
            
        except ImportError:
            log.warning("[Evidence] EvidenceExtractionResult model not found - evidence data not persisted")
        except Exception as e:
            log.error(f"[Evidence] Failed to save EvidenceExtractionResult: {e}")
            
    except Exception as e:
        log.error(f"[Evidence] Error in _save_evidence_result: {e}")


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
