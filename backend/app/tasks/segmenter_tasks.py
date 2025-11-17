# app/tasks/segmenter_tasks.py
import logging
import time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import SegmentResult  # ← persist here
from app.services.stages.discover.segmenter_service import SegmenterService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.segments.build_for_file")
def build_segments_for_file(self, file_id: str, progress_id: str, force: bool = False):
    """
    Iterate pages → segment page_text → (optionally) store FilePage.page_segments →
    merge to outline → PERSIST a SegmentResult row (versioned, is_active=True) → update Progress.
    """
    s = db.session()
    svc = SegmenterService()

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

        has_col = hasattr(FilePage, "page_segments")
        per_page_pairs = []  # [(page_number, [segments])]
        done = 0

        # 2) Segment each page (reuse cached per-page segments when not forced)
        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_segments", None):
                    segs = getattr(page, "page_segments") or []
                else:
                    segs = svc.segment_page(page.page_text or "")
                    if has_col:
                        setattr(page, "page_segments", segs)
                    s.commit()

                per_page_pairs.append((page.page_number, segs))
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Segmentation] Failed page {getattr(page,'id','?')}: {e}")

            _bump_progress(s, progress_id, int(done * 100 / total))
            time.sleep(0.2)  # gentle pacing

        # 3) Merge per-page segments into a document outline
        try:
            outline = svc.merge_outline(per_page_pairs)  # list[segment dict]
        except Exception as e:
            log.error(f"[Segmentation] Merge/outline error: {e}")
            outline = []

        # 4) Persist to SegmentResult with version bump and is_active flag
        try:
            last = (
                s.query(SegmentResult)
                 .filter(SegmentResult.file_id == file_id)
                 .order_by(SegmentResult.version.desc())
                 .first()
            )
            next_version = (last.version + 1) if last else 1

            # deactivate currently-active rows
            s.query(SegmentResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})

            rec = SegmentResult(
                file_id=file_id,
                version=next_version,
                is_active=True,
                method="openai",
                model_version=svc.openai_engine,
                num_segments=len(outline),
                segments=outline,
                # Optional small stats for debugging/insights:
                meta={"pages_total": total, "pages_with_segments": sum(1 for _, segs in per_page_pairs if segs)}
            )
            s.add(rec)
            s.commit()
        except Exception as e:
            s.rollback()
            log.error(f"[Segmentation] Persist SegmentResult error: {e}")

        # 5) Finish progress
        _finish_progress(s, progress_id, "completed", 100)

    except Exception:
        s.rollback()
        log.exception("[Segmentation] Task failed")
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