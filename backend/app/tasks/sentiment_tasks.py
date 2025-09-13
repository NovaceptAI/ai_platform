import logging, time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.discover.sentiment_service import SentimentService
from app.models.analysis_results import SentimentResult

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def build_sentiment_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Page-by-page sentiment analysis with progress.
    For now, it *computes* and updates progress; optionally stores per-page later if you add a column.
    """
    s = db.session()
    svc = SentimentService()
    per_page = []  # [(page_number, result_dict)]
    try:
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

        has_col = hasattr(FilePage, "page_sentiment")  # optional future column

        done = 0
        for page in pages:
            
            try:
                if not force and has_col and getattr(page, "page_sentiment", None):
                    pass
                else:
                    result = svc.analyze_page(page.page_text or "")
                    per_page.append((page.page_number, result))
                    if has_col:
                        setattr(page, "page_sentiment", result)
                    s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Sentiment] Failed page {page.id}: {e}")


            _bump_progress(s, progress_id, int(done * 100 / total))
            time.sleep(0.2)

        _finish_progress(s, progress_id, "completed", 100)

         # after loop, before marking completed:
        try:
            # aggregate
            agg = svc.aggregate_document(per_page)  # {"avg_score", "label_hist", "dominant_label"}

            # versioning: increment last version, deactivate previous active
            last = (
                s.query(SentimentResult)
                .filter(SentimentResult.file_id == file_id)
                .order_by(SentimentResult.version.desc())
                .first()
            )
            next_version = (last.version + 1) if last else 1
            s.query(SentimentResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})

            rec = SentimentResult(
                file_id=file_id,
                version=next_version,
                is_active=True,
                method="openai",
                model_version=svc.openai_engine,
                overall_label=agg.get("dominant_label"),
                overall_score=agg.get("avg_score"),
                page_sentiments={str(p): v for p, v in per_page},
                meta={"label_hist": agg.get("label_hist", {})},
            )
            s.add(rec)
            s.commit()
        except Exception as e:
            s.rollback()
            log.error(f"[Sentiment] Failed to persist SentimentResult: {e}")

    except Exception:
        s.rollback()
        log.exception("[Sentiment] Task failed")
        _finish_progress(s, progress_id, "failed")
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