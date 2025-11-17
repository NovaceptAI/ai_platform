import logging, time, math
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.create.creative_prompts_service import CreativePromptsService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="creative_prompts.build_for_file")
def build_prompts_for_file(
    self,
    file_id: str,
    progress_id: str,
    num_prompts: int = 10,
    genre: str = "mixed",
    force: bool = False
):
    """
    1) Iterate pages for file_id; generate per-page creative prompts from page_text.
    2) (Optionally) store per-page prompts in FilePage.page_prompts if column exists.
    3) Update Progress percentage as we go.
    Final merged view is assembled in /creative_prompts/results.
    """
    s = db.session()
    svc = CreativePromptsService()
    try:
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

        has_col = hasattr(FilePage, "page_prompts")

        # Heuristic: target ~ceil(num_prompts / total) per page (cap 5)
        k_per_page = max(1, min(5, math.ceil(max(1, num_prompts) / total)))

        done = 0
        all_prompts = []
        per_page = []

        for page in pages:
            page_prompts = []
            try:
                if not force and has_col and getattr(page, "page_prompts", None):
                    page_prompts = getattr(page, "page_prompts", [])
                else:
                    page_prompts = svc.generate_prompts_from_text(
                        page.page_text or "",
                        k_per_page=k_per_page,
                        genre_filter=genre
                    )
                    if has_col:
                        setattr(page, "page_prompts", page_prompts)
                    s.commit()

                # Collect prompts for final result
                per_page.append({
                    "page": page.page_number,
                    "prompts": page_prompts
                })
                all_prompts.extend(page_prompts)
                done += 1

            except Exception as e:
                s.rollback()
                log.error(f"[CreativePrompts] Failed page {getattr(page, 'id', '?')}: {e}")
                # Add empty prompts for failed page
                per_page.append({
                    "page": page.page_number,
                    "prompts": []
                })

            _bump_progress(s, progress_id, int((done / total) * 100))
            time.sleep(0.2)

        # Flatten and deduplicate
        seen = set()
        flat = []
        for pr in all_prompts:
            key = (pr.get("prompt") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                flat.append(pr)

        # Limit to requested number
        final_prompts = flat[:max(1, num_prompts)]

        # Store results in Progress.result_data
        result_data = {
            "file_id": file_id,
            "genre": genre,
            "num_prompts": num_prompts,
            "total_generated": len(final_prompts),
            "per_page": per_page,
            "prompts": final_prompts
        }

        _finish_progress(s, progress_id, status="completed", pct=100, result_data=result_data)

    except Exception:
        s.rollback()
        log.exception("[CreativePrompts] Task failed")
        _finish_progress(s, progress_id, status="failed")
        raise
    finally:
        s.close()


def _bump_progress(s, progress_id, pct: int):
    p = s.query(Progress).get(progress_id)
    if p:
        p.percentage = max(p.percentage or 0, int(pct))
        s.commit()

def _finish_progress(s, progress_id, status: str, pct: int = None, result_data: dict = None):
    p = s.query(Progress).get(progress_id)
    if p:
        p.status = status
        if pct is not None:
            p.percentage = pct
        if result_data is not None:
            p.result_data = result_data
        s.commit()
