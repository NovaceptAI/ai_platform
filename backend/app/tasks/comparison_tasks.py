# app/tasks/comparison_tasks.py
import logging
import time
from celery import shared_task
from sqlalchemy import asc
from app.db import db
from app.models import UploadedFile, Progress
from app.models.analysis_results import ComparisonResult
from app.services.stages.discover.comparison_service import ComparisonService

log = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=2, default_retry_delay=10, name="discover.comparison.build_for_files")
def build_comparison_for_files(self, file_ids: list, progress_id: str, force: bool = False):
    """
    Compare multiple files by analyzing their summaries and content.
    
    Args:
        file_ids: List of file IDs to compare
        progress_id: Progress tracking ID
        force: Whether to force re-analysis
    """
    s = db.session()
    svc = ComparisonService()

    try:
        if len(file_ids) < 2:
            log.error("[Comparison] Need at least 2 files to compare")
            _finish_progress(s, progress_id, "failed")
            return

        # 1) Load file information and summaries
        files = s.query(UploadedFile).filter(UploadedFile.id.in_(file_ids)).all()
        
        if len(files) < 2:
            log.error(f"[Comparison] Found only {len(files)} files out of {len(file_ids)} requested")
            _finish_progress(s, progress_id, "failed")
            return

        _bump_progress(s, progress_id, 20)

        # 2) Gather file summaries and key information
        file_summaries = []
        for file in files:
            summary_data = _get_file_summary_data(s, str(file.id))
            summary_data["file_id"] = str(file.id)
            summary_data["title"] = file.filename or "Untitled"
            file_summaries.append(summary_data)

        _bump_progress(s, progress_id, 50)

        # 3) Perform comparison analysis
        try:
            comparison_result = svc.compare_documents(file_summaries)
            
            if "error" in comparison_result:
                log.error(f"[Comparison] Service returned error: {comparison_result['error']}")
                _finish_progress(s, progress_id, "failed")
                return

            _bump_progress(s, progress_id, 80)

            # 4) Save comparison results
            _save_comparison_result(s, file_ids, comparison_result)
            
            _finish_progress(s, progress_id, "completed", 100)
            log.info(f"[Comparison] Completed comparison of {len(file_ids)} files")
            
        except Exception as e:
            s.rollback()
            log.error(f"[Comparison] Analysis failed: {e}")
            _finish_progress(s, progress_id, "failed")

    except Exception:
        s.rollback()
        log.exception(f"[Comparison] Task failed for files {file_ids}")
        _finish_progress(s, progress_id, "failed")
        raise
    finally:
        s.close()


def _get_file_summary_data(s, file_id: str) -> dict:
    """
    Get summary data for a file from various analysis results.
    """
    summary_data = {
        "summary": "No summary available",
        "key_points": [],
        "topics": [],
        "entities": []
    }
    
    try:
        # Try to get data from SummaryResult
        try:
            from app.models.analysis_results import SummaryResult
            summary_result = s.query(SummaryResult).filter_by(
                file_id=file_id, is_active=True
            ).first()
            
            if summary_result:
                if hasattr(summary_result, 'summary_content'):
                    summary_data["summary"] = summary_result.summary_content or "No summary"
                if hasattr(summary_result, 'key_points'):
                    summary_data["key_points"] = summary_result.key_points or []
                    
        except ImportError:
            log.debug("[Comparison] SummaryResult model not available")
        
        # Try to get data from DocumentAnalysisResult
        try:
            from app.models.analysis_results import DocumentAnalysisResult
            doc_result = s.query(DocumentAnalysisResult).filter_by(
                file_id=file_id, is_active=True
            ).first()
            
            if doc_result:
                if hasattr(doc_result, 'tags'):
                    summary_data["topics"] = doc_result.tags or []
                if hasattr(doc_result, 'entities'):
                    summary_data["entities"] = doc_result.entities or []
                    
        except ImportError:
            log.debug("[Comparison] DocumentAnalysisResult model not available")
        
        # If no summary available, try to get from FilePage
        if summary_data["summary"] == "No summary available":
            from app.models import FilePage
            pages = s.query(FilePage).filter_by(file_id=file_id).limit(3).all()
            if pages:
                preview_text = " ".join([p.page_text or "" for p in pages])
                if len(preview_text) > 500:
                    preview_text = preview_text[:500] + "..."
                summary_data["summary"] = f"Preview: {preview_text}"
    
    except Exception as e:
        log.error(f"[Comparison] Error getting summary data for file {file_id}: {e}")
    
    return summary_data


def _save_comparison_result(s, file_ids: list, comparison_data: dict):
    """Save comparison results to database."""
    try:
        # Check if ComparisonResult table exists
        try:
            from app.models.analysis_results import ComparisonResult
            
            # Create a unique identifier for this comparison
            comparison_key = "-".join(sorted(file_ids))
            
            # Mark previous comparisons with same files as inactive
            s.query(ComparisonResult).filter_by(
                comparison_key=comparison_key, is_active=True
            ).update({"is_active": False})
            
            # Create new comparison result
            result = ComparisonResult(
                comparison_key=comparison_key,
                file_ids=file_ids,
                similarities=comparison_data.get("similarities", []),
                differences=comparison_data.get("differences", []),
                themes=comparison_data.get("themes", []),
                synthesis=comparison_data.get("synthesis", ""),
                recommendations=comparison_data.get("recommendations", {}),
                comparison_stats={
                    "file_count": len(file_ids),
                    "similarity_count": len(comparison_data.get("similarities", [])),
                    "difference_count": len(comparison_data.get("differences", [])),
                    "theme_count": len(comparison_data.get("themes", []))
                },
                is_active=True
            )
            s.add(result)
            s.commit()
            log.info(f"[Comparison] Saved ComparisonResult for files {file_ids}")
            
        except ImportError:
            log.warning("[Comparison] ComparisonResult model not found - comparison data not persisted")
        except Exception as e:
            log.error(f"[Comparison] Failed to save ComparisonResult: {e}")
            
    except Exception as e:
        log.error(f"[Comparison] Error in _save_comparison_result: {e}")


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
