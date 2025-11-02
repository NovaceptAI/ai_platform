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
        elif tool == "segmenter":
            self._run_segmenter(file_ids)
        elif tool == "doc_analysis":
            self._run_doc_analysis(file_ids)
        elif tool in {"chronology_strict", "chronology"}:
            self._run_chronology(file_ids)
        elif tool == "topic_modeller":
            # TODO: wire your topic modeller service here
            pass
        elif tool in {"timeline", "timeline_explorer"}:
            # TODO: call your timeline services here
            pass
        elif tool == "evidence_extractor":
            self._run_evidence_extractor(file_ids)
        elif tool == "comparison":
            self._run_comparison(file_ids)
        # ORGANIZE STAGE TOOLS
        elif tool == "collections_boards":
            self._run_collections(file_ids)
        elif tool == "tag_taxonomy_manager":
            self._run_tag_taxonomy(file_ids)
        elif tool == "cluster_builder":
            self._run_clustering(file_ids)
        elif tool == "concept_graph":
            self._run_concept_graph(file_ids)
        elif tool == "saved_views":
            self._run_saved_views(file_ids)
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

    def _run_segmenter(self, file_ids: Iterable[str]):
        """
        For each file_id, trigger segmentation task.
        """
        if not file_ids:
            log.info("[LP Runner] Segmenter invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.segmenter_tasks import build_segments_for_file
        
        for fid in file_ids:
            try:
                # Create progress tracking for this task
                prog = Progress(user_id=str(self.user_id), tool="segmenter", status="in_progress", percentage=0)
                db.session.add(prog)
                db.session.commit()
                
                # Launch segmentation task
                build_segments_for_file.apply_async(kwargs={
                    "file_id": fid,
                    "progress_id": str(prog.id),
                    "force": False
                })
                log.info("[LP Runner] Launched segmentation for file %s (progress_id=%s)", fid, prog.id)
            except Exception as e:
                log.exception("[LP Runner] Segmenter failed for file %s: %s", fid, e)

    def _run_doc_analysis(self, file_ids: Iterable[str]):
        """
        For each file_id, trigger document analysis task.
        """
        if not file_ids:
            log.info("[LP Runner] Doc Analysis invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.doc_analysis_tasks import build_doc_analysis_for_file
        
        for fid in file_ids:
            try:
                # Create progress tracking for this task
                prog = Progress(user_id=str(self.user_id), tool="doc_analysis", status="in_progress", percentage=0)
                db.session.add(prog)
                db.session.commit()
                
                # Launch doc analysis task
                build_doc_analysis_for_file.apply_async(kwargs={
                    "file_id": fid,
                    "progress_id": str(prog.id),
                    "force": False
                })
                log.info("[LP Runner] Launched doc analysis for file %s (progress_id=%s)", fid, prog.id)
            except Exception as e:
                log.exception("[LP Runner] Doc Analysis failed for file %s: %s", fid, e)

    def _run_chronology(self, file_ids: Iterable[str]):
        """
        For each file_id, trigger chronology analysis task.
        """
        if not file_ids:
            log.info("[LP Runner] Chronology invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.chrono_tasks import build_chronology_for_file
        
        for fid in file_ids:
            try:
                # Create progress tracking for this task
                prog = Progress(user_id=str(self.user_id), tool="chronology", status="in_progress", percentage=0)
                db.session.add(prog)
                db.session.commit()
                
                # Launch chronology task
                build_chronology_for_file.apply_async(kwargs={
                    "file_id": fid,
                    "progress_id": str(prog.id),
                    "force": False
                })
                log.info("[LP Runner] Launched chronology analysis for file %s (progress_id=%s)", fid, prog.id)
            except Exception as e:
                log.exception("[LP Runner] Chronology failed for file %s: %s", fid, e)

    def _run_evidence_extractor(self, file_ids: Iterable[str]):
        """
        For each file_id, trigger evidence extraction task.
        """
        if not file_ids:
            log.info("[LP Runner] Evidence Extractor invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.evidence_extractor_tasks import build_evidence_for_file
        
        for fid in file_ids:
            try:
                # Create progress tracking for this task
                prog = Progress(user_id=str(self.user_id), tool="evidence_extractor", status="in_progress", percentage=0)
                db.session.add(prog)
                db.session.commit()
                
                # Launch evidence extraction task
                build_evidence_for_file.apply_async(kwargs={
                    "file_id": fid,
                    "progress_id": str(prog.id),
                    "force": False
                })
                log.info("[LP Runner] Launched evidence extraction for file %s (progress_id=%s)", fid, prog.id)
            except Exception as e:
                log.exception("[LP Runner] Evidence Extractor failed for file %s: %s", fid, e)

    def _run_comparison(self, file_ids: Iterable[str]):
        """
        Run comparison analysis across all provided file_ids.
        """
        file_list = list(file_ids)
        if len(file_list) < 2:
            log.warning("[LP Runner] Comparison needs at least 2 files; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.comparison_tasks import build_comparison_for_files
        
        try:
            # Create progress tracking for this task
            prog = Progress(user_id=str(self.user_id), tool="comparison", status="in_progress", percentage=0)
            db.session.add(prog)
            db.session.commit()
            
            # Launch comparison task with all files
            build_comparison_for_files.apply_async(kwargs={
                "file_ids": file_list,
                "progress_id": str(prog.id),
                "force": False
            })
            log.info("[LP Runner] Launched comparison for %d files (progress_id=%s)", len(file_list), prog.id)
        except Exception as e:
            log.exception("[LP Runner] Comparison failed for files %s: %s", file_list, e)

    # ----------------------------
    # ORGANIZE STAGE TOOLS
    # ----------------------------

    def _run_collections(self, file_ids: Iterable[str]):
        """
        Run collections organization for all provided file_ids.
        """
        file_list = list(file_ids)
        if not file_list:
            log.info("[LP Runner] Collections invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.collections_tasks import create_collections_task
        
        try:
            # Prepare file data for collections service
            s = db.session()
            files = (
                s.query(UploadedFile)
                 .filter(UploadedFile.id.in_(file_list))
                 .all()
            )
            
            file_data = []
            for file in files:
                file_data.append({
                    "file_id": str(file.id),
                    "file_name": file.original_file_name,
                    "file_type": file.file_type,
                    # "file_size": file.file_size,
                    "summary": getattr(file, 'summary', ''),
                    "topics": getattr(file, 'topics', []),
                    "entities": getattr(file, 'entities', {}),
                    "created_at": file.created_at.isoformat() if file.created_at else None
                })
            
            # Launch collections task
            create_collections_task.apply_async(args=[self.user_id, file_ids])
            log.info("[LP Runner] Launched collections for %d files", len(file_list))
        except Exception as e:
            log.exception("[LP Runner] Collections failed for files %s: %s", file_list, e)

    def _run_tag_taxonomy(self, file_ids: Iterable[str]):
        """
        Run tag taxonomy building for all provided file_ids.
        """
        file_list = list(file_ids)
        if not file_list:
            log.info("[LP Runner] Tag Taxonomy invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.tagging_tasks import build_tag_taxonomy_task
        
        try:
            # Prepare file data for tagging service
            s = db.session()
            files = (
                s.query(UploadedFile)
                 .filter(UploadedFile.id.in_(file_list))
                 .all()
            )
            
            file_data = []
            for file in files:
                file_data.append({
                    "file_id": str(file.id),
                    "file_name": file.original_file_name,
                    "topics": getattr(file, 'topics', []),
                    "entities": getattr(file, 'entities', {}),
                    "keywords": getattr(file, 'keywords', []),
                    "summary": getattr(file, 'summary', '')
                })
            
            # Launch tag taxonomy task
            build_tag_taxonomy_task.apply_async(args=[self.user_id, file_ids])
            log.info("[LP Runner] Launched tag taxonomy for %d files", len(file_list))
        except Exception as e:
            log.exception("[LP Runner] Tag Taxonomy failed for files %s: %s", file_list, e)

    def _run_clustering(self, file_ids: Iterable[str]):
        """
        Run document clustering for all provided file_ids.
        """
        file_list = list(file_ids)
        if not file_list:
            log.info("[LP Runner] Clustering invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.clustering_tasks import create_content_clusters_task
        
        try:
            # Prepare file data for clustering service
            s = db.session()
            files = (
                s.query(UploadedFile)
                 .filter(UploadedFile.id.in_(file_list))
                 .all()
            )
            
            file_data = []
            for file in files:
                file_data.append({
                    "file_id": str(file.id),
                    "file_name": file.original_file_name,
                    "content": getattr(file, 'content', ''),
                    "summary": getattr(file, 'summary', ''),
                    "topics": getattr(file, 'topics', []),
                    "entities": getattr(file, 'entities', {}),
                    # "file_size": file.file_size
                })
            
            # Launch clustering task
            create_content_clusters_task.apply_async(args=[self.user_id, file_ids])
            log.info("[LP Runner] Launched clustering for %d files", len(file_list))
        except Exception as e:
            log.exception("[LP Runner] Clustering failed for files %s: %s", file_list, e)

    def _run_concept_graph(self, file_ids: Iterable[str]):
        """
        Run concept graph building for all provided file_ids.
        """
        file_list = list(file_ids)
        if not file_list:
            log.info("[LP Runner] Concept Graph invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.concept_graph_tasks import build_concept_graph_task
        
        try:
            # Prepare file data for concept graph service
            s = db.session()
            files = (
                s.query(UploadedFile)
                 .filter(UploadedFile.id.in_(file_list))
                 .all()
            )
            
            file_data = []
            for file in files:
                file_data.append({
                    "file_id": str(file.id),
                    "file_name": file.original_file_name,
                    "topics": getattr(file, 'topics', []),
                    "entities": getattr(file, 'entities', {}),
                    "relationships": getattr(file, 'relationships', []),
                    "summary": getattr(file, 'summary', ''),
                    "evidence_items": getattr(file, 'evidence_items', [])
                })
            
            # Launch concept graph task
            build_concept_graph_task.apply_async(args=[self.user_id, file_ids])
            log.info("[LP Runner] Launched concept graph for %d files", len(file_list))
        except Exception as e:
            log.exception("[LP Runner] Concept Graph failed for files %s: %s", file_list, e)

    def _run_saved_views(self, file_ids: Iterable[str]):
        """
        Run saved views creation for all provided file_ids.
        """
        file_list = list(file_ids)
        if not file_list:
            log.info("[LP Runner] Saved Views invoked with no file_ids; skipping.")
            return

        # Import here to avoid circular imports
        from app.tasks.saved_views_tasks import create_saved_views_task
        
        try:
            # Prepare file data for saved views service
            s = db.session()
            files = (
                s.query(UploadedFile)
                 .filter(UploadedFile.id.in_(file_list))
                 .all()
            )
            
            file_data = []
            for file in files:
                file_data.append({
                    "file_id": str(file.id),
                    "file_name": file.original_file_name,
                    "file_type": file.file_type,
                    "topics": getattr(file, 'topics', []),
                    "entities": getattr(file, 'entities', {}),
                    "evidence_items": getattr(file, 'evidence_items', []),
                    "created_at": file.created_at.isoformat() if file.created_at else None,
                    # "file_size": file.file_size
                })
            
            # For saved views, we need organization data from other tools
            # This is a simplified approach - in practice, you'd gather results from previous tools
            organization_data = {
                "collections": [],
                "tags": [],
                "clusters": []
            }
            
            # Launch saved views task
            create_saved_views_task.apply_async(args=[self.user_id, file_ids])
            log.info("[LP Runner] Launched saved views for %d files", len(file_list))
        except Exception as e:
            log.exception("[LP Runner] Saved Views failed for files %s: %s", file_list, e)
