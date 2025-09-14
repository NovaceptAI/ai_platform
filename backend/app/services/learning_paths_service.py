# app/services/learning_paths_service.py
import logging
from typing import Iterable, List, Dict, Any

from app.db import db
from app.models.status import Progress
from app.models.learning_paths import LearningPathStep
from app.models import UploadedFile  # exposed via app.models.__init__
from app.services.stages.discover.summarizer_service import Summarizer

log = logging.getLogger(__name__)


class LearningPathRunner:
    """
    Executes a single LearningPathStep against the provided inputs.
    For tools that operate on files, pass file_ids via step.config["file_ids"].

    Note: Stage-level orchestration and progress updates are handled in Celery tasks.
    This runner focuses only on invoking the right tool for a given step.
    """

    def __init__(self, user_id, progress: Progress):
        self.user_id = user_id
        self.progress = progress

    def run_step(self, step: LearningPathStep):
        tool = (step.tool_key or "").strip().lower()
        cfg: Dict[str, Any] = step.config or {}

        # Common input convention: a list of uploaded file UUIDs
        file_ids: List[str] = cfg.get("file_ids", []) or []

        if tool == "summarizer":
            self._run_summarizer(file_ids)
        elif tool == "topic_modeller":
            # TODO: wire your topic modeller service here
            pass
        elif tool in {"timeline", "timeline_explorer", "chronology_strict"}:
            # TODO: call your chronology/timeline services here
            pass
        else:
            log.warning("[LP Runner] Unknown or unsupported tool_key='%s' — no-op", tool)

    # ----------------------------
    # Tool adapters
    # ----------------------------

    def _run_summarizer(self, file_ids: Iterable[str]):
        """
        For each file_id, resolve file_path and run Summarizer on the file.
        """
        if not file_ids:
            log.info("[LP Runner] Summarizer invoked with no file_ids; skipping.")
            return

        s = db.session()
        smz = Summarizer()  # uses your rotating Azure OpenAI creds

        # Resolve file paths
        files = (
            s.query(UploadedFile)
             .filter(UploadedFile.id.in_(list(file_ids)))
             .all()
        )
        path_map = {str(f.id): f.file_path for f in files if getattr(f, "file_path", None)}

        # Run per file (resilient)
        for fid in file_ids:
            path = path_map.get(str(fid))
            if not path:
                log.error("[LP Runner] UploadedFile not found or missing path (id=%s)", fid)
                continue

            try:
                result = smz._summarize_file(path)  # uses your current API
                # TODO: persist 'result' into your analysis tables if needed,
                #       or emit KnowledgeItem, or attach to a Results table.
                log.info("[LP Runner] Summarized file %s (%s) — toc=%s segments=%s",
                         fid, path, bool(result.get("toc")), len(result.get("segments", [])))
            except Exception as e:
                log.exception("[LP Runner] Summarizer failed for file %s (%s): %s", fid, path, e)
