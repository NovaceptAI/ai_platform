import logging, time, math
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.services.stages.master.ethical_ai_tutor_service import EthicalAITutorService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="ethical_ai_tutor.build_for_file")
def build_ethical_ai_tutor_for_file(
    self,
    file_id: str,
    progress_id: str,
    num_scenarios: int = 5,
    difficulty: str = "medium",
    scenario_type: str = "mixed",
    force: bool = False
):
    """
    1) Iterate pages for file_id; generate per-page ethical AI scenarios from page_text.
    2) (Optionally) store per-page list in FilePage.page_ethical_ai_scenarios if column exists.
    3) Update Progress percentage as we go.
    Final assembly is returned by /ethical_ai_tutor/results.
    """
    s = db.session()
    svc = EthicalAITutorService()
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

        has_col = hasattr(FilePage, "page_ethical_ai_scenarios")

        # Heuristic: target ~ceil(num_scenarios / total) per page (cap 3)
        k_per_page = max(1, min(3, math.ceil(max(1, num_scenarios) / total)))

        done = 0
        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_ethical_ai_scenarios", None):
                    pass  # already exists
                else:
                    scenarios = svc.generate_scenarios_from_text(
                        page.page_text or "",
                        k=k_per_page,
                        difficulty=difficulty,
                        scenario_type=scenario_type
                    )
                    if has_col:
                        setattr(page, "page_ethical_ai_scenarios", scenarios)
                    s.commit()
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[EthicalAITutor] Failed page {getattr(page, 'id', '?')}: {e}")

            _bump_progress(s, progress_id, int((done / total) * 100))
            time.sleep(0.2)  # gentle pacing to avoid burst rate limits

        _finish_progress(s, progress_id, status="completed", pct=100)

    except Exception:
        s.rollback()
        log.exception("[EthicalAITutor] Task failed")
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
