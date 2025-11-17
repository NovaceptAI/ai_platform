# app/tasks/chrono_tasks.py
import logging, time
from datetime import date as _date
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import FilePage, Progress
from app.models.analysis_results import ChronologyResult
from app.services.stages.discover.chrono_service import ChronologyService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.chronology.build_for_file")
def build_chronology_for_file(self, file_id: str, progress_id: str, force: bool = False):
    s = db.session()
    svc = ChronologyService()
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

        has_col = hasattr(FilePage, "page_chronology")
        done = 0
        per_page_pairs = []
        pages_with_events = 0

        for page in pages:
            try:
                if not force and has_col and getattr(page, "page_chronology", None):
                    # ensure only dated items are kept if old data exists
                    events = [e for e in (getattr(page, "page_chronology") or []) if isinstance(e, dict) and e.get("date")]
                else:
                    events = svc.extract_events_from_text(page.page_text or "")
                    if has_col:
                        setattr(page, "page_chronology", events)  # already dated-only
                    s.commit()

                if events:
                    pages_with_events += 1
                per_page_pairs.append((page.page_number, events))
                done += 1
            except Exception as e:
                s.rollback()
                log.error(f"[Chronology] Failed page {getattr(page,'id','?')}: {e}")

            _bump_progress(s, progress_id, int((done / total) * 100))
            time.sleep(0.2)

        # Merge (dated-only)
        try:
            merged = svc.merge_events(per_page_pairs)  # will be [] if no dates
            start_d, end_d, gran = _derive_bounds_and_granularity(merged)
            coverage = round(pages_with_events / max(total, 1), 6)

            # Version bump; set active
            last = (
                s.query(ChronologyResult)
                 .filter(ChronologyResult.file_id == file_id)
                 .order_by(ChronologyResult.version.desc())
                 .first()
            )
            next_version = (last.version + 1) if last else 1
            s.query(ChronologyResult).filter_by(file_id=file_id, is_active=True).update({"is_active": False})

            rec = ChronologyResult(
                file_id=file_id,
                version=next_version,
                is_active=True,
                method="openai",
                model_version=svc.openai_engine,
                start_date=start_d,
                end_date=end_d,
                granularity=("none" if not merged else gran),
                coverage_ratio=(0.0 if not merged else coverage),
                events=merged,  # dated-only
                # mark that we found no dates so the route/UI can short-circuit
                meta={"no_dates_found": not bool(merged)},
            )
            s.add(rec)
            s.commit()
        except Exception as e:
            s.rollback()
            log.error(f"[Chronology] Failed to persist ChronologyResult: {e}")

        _finish_progress(s, progress_id, status="completed", pct=100)

    except Exception:
        s.rollback()
        log.exception("[Chronology] Task failed")
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

def _derive_bounds_and_granularity(merged_events):
    years, months, days = 0, 0, 0
    earliest, latest = None, None

    for ev in merged_events or []:
        d = (ev.get("date") or "").strip()
        if not d:
            continue
        parts = d.split("-")
        try:
            y = int(parts[0])
            if len(parts) == 1:
                dt_obj = _date(y, 1, 1)
                years += 1
                end_obj = _date(y, 12, 31)
            elif len(parts) == 2:
                m = int(parts[1])
                dt_obj = _date(y, m, 1)
                months += 1
                end_obj = _date(y, m, 28)
            else:
                m = int(parts[1]); d2 = int(parts[2])
                dt_obj = _date(y, m, d2)
                days += 1
                end_obj = dt_obj
        except Exception:
            continue

        if earliest is None or dt_obj < earliest:
            earliest = dt_obj
        if latest is None or end_obj > latest:
            latest = end_obj

    if days > 0:
        gran = "day"
    elif months > 0:
        gran = "month"
    elif years > 0:
        gran = "year"
    else:
        gran = "mixed"

    return earliest, latest, gran
