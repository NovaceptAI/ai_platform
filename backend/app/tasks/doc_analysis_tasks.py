# app/tasks/doc_analysis_task.py
import logging
import time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import DocumentAnalysisResult
from app.services.stages.discover.doc_analysis_service import DocAnalysisService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.doc_analysis.build_for_file")
def build_doc_analysis_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Run page-by-page analysis (tags, entities, length), aggregate to document-level,
    persist to DocumentAnalysisResult (versioned, is_active), and update Progress.
    """
    # Create a new session for this task
    from app.db import create_task_session
    s = create_task_session()
    svc = DocAnalysisService()

    try:
        # 1) Load pages
        pages = (
            s.query(FilePage)
             .filter(FilePage.file_id == file_id)
             .order_by(asc(FilePage.page_number))
             .all()
        )
        total = len(pages)
        if total == 0:
            _finish_progress(s, progress_id, status="completed", pct=100)
            return

        # 2) Page-by-page analysis (in-memory)
        per_page = []  # [(page_number, analysis_dict)]
        done = 0
        for page in pages:
            try:
                analysis = svc.analyze_page(page.page_text or "")
                per_page.append((page.page_number, analysis))
                done += 1
            except Exception as e:
                log.error(f"[DocAnalysis] Failed page {getattr(page, 'id', '?')}: {e}")

            _bump_progress(s, progress_id, int(done * 100 / total))
            time.sleep(0.2)  # gentle pacing for API limits

        # 3) Aggregate document-level summary
        doc_summary = {}
        try:
            doc_summary = svc.aggregate(per_page)  # {"totals","top_tags","entities_by_type"}
        except Exception as e:
            log.error(f"[DocAnalysis] Aggregation error: {e}")
            doc_summary = {"totals": {}, "top_tags": [], "entities_by_type": {}}

        # Map UI-expected "top_tags" into persisted "key_points"
        key_points = [
            {"text": (t.get("tag") or ""), "count": t.get("count"), "pages": (t.get("pages") or [])}
            for t in (doc_summary.get("top_tags") or [])
        ]

        # 4) Version bump + persist DocumentAnalysisResult
        try:
            last = (
                s.query(DocumentAnalysisResult)
                 .filter(DocumentAnalysisResult.file_id == file_id)
                 .order_by(DocumentAnalysisResult.version.desc())
                 .first()
            )
            next_version = (last.version + 1) if last else 1

            # deactivate previous active records
            s.query(DocumentAnalysisResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})

            rec = DocumentAnalysisResult(
                file_id=file_id,
                version=next_version,
                is_active=True,
                method="openai",
                model_version=svc.openai_engine,
                # persisted fields
                stats=doc_summary.get("totals") or {},
                key_points=key_points,
                meta={"entities_by_type": doc_summary.get("entities_by_type") or {}},
                # Optional extras (leave None unless you compute them)
                readability=None,
                quality_scores=None,
                outline=None,
                risks=None,
                recommendations=None,
            )
            s.add(rec)
            s.commit()
        except Exception as e:
            s.rollback()
            log.error(f"[DocAnalysis] Persist error: {e}")

        # 5) Finish progress
        _finish_progress(s, progress_id, status="completed", pct=100)

    except Exception:
        s.rollback()
        log.exception("[DocAnalysis] Task failed")
        _finish_progress(s, progress_id, status="failed")
        raise
    finally:
        s.close()


def _bump_progress(s, progress_id, pct: int):
    p = s.query(Progress).get(progress_id)
    if p:
        p.percentage = max(p.percentage or 0, int(pct))
        s.commit()

def _finish_progress(s, progress_id, status: str, pct: int = None):
    p = s.query(Progress).get(progress_id)
    if p:
        p.status = status
        if pct is not None:
            p.percentage = pct
        s.commit()