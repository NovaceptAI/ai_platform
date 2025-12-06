"""
Research Artifacts Service

Wrapper service for generating flashcards and presentations from research workspace.
Routes requests to existing FlashcardsService and AIPresentationBuilderService.
Manages research_artifacts table for tracking creations within research sessions.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.db import db
from app.models.research import ResearchArtifact, ResearchSession
from app.models.status import Progress
from app.models.files import UploadedFile
from app.tasks.flashcards_tasks import create_flashcards_task
from app.tasks.ai_presentation_builder_tasks import generate_presentation_content_task

logger = logging.getLogger(__name__)


class ResearchArtifactsService:
    """
    Service for managing research artifacts (flashcards and presentations).
    Acts as a wrapper around existing tool services.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_flashcards(
        self,
        session_id: str,
        user_id: str,
        file_ids: List[str],
        title: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate flashcards from research session documents.
        
        Args:
            session_id: Research session UUID
            user_id: User UUID
            file_ids: List of file UUIDs to process
            title: Title for the flashcards artifact
            options: Flashcard generation options (max_cards, difficulty, etc.)
            
        Returns:
            Dict with artifact_id and progress_id
        """
        try:
            # Validate session
            session = db.session.query(ResearchSession).filter(
                ResearchSession.id == session_id,
                ResearchSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError(f"Research session not found: {session_id}")
            
            # Create progress record
            progress = Progress(
                user_id=user_id,
                tool="flashcards",
                stage="master",
                status="pending",
                percentage=0,
                created_at=datetime.utcnow()
            )
            db.session.add(progress)
            db.session.flush()
            
            # Create artifact record
            artifact = ResearchArtifact(
                session_id=session_id,
                artifact_type="flashcards",
                title=title,
                status="pending",
                config_data={
                    "file_ids": file_ids,
                    "options": options or {},
                    "user_id": user_id
                },
                progress_id=progress.id
            )
            db.session.add(artifact)
            db.session.commit()
            
            self.logger.info(f"[ResearchArtifacts] Created flashcards artifact {artifact.id} for session {session_id}")
            
            # Launch Celery task with artifact_id
            task_options = options or {}
            create_flashcards_task.apply_async(
                args=[user_id, file_ids, str(progress.id), task_options],
                kwargs={"artifact_id": str(artifact.id)}
            )
            
            return {
                "artifact_id": str(artifact.id),
                "progress_id": str(progress.id),
                "status": "pending"
            }
            
        except Exception as e:
            self.logger.error(f"[ResearchArtifacts] Error generating flashcards: {str(e)}")
            db.session.rollback()
            raise
    
    def generate_presentation(
        self,
        session_id: str,
        user_id: str,
        file_id: Optional[str],
        title: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate AI presentation from research session documents.
        
        Args:
            session_id: Research session UUID
            user_id: User UUID
            file_id: Optional file UUID (can be None for text-based)
            title: Title for the presentation artifact
            options: Presentation options (source_type, text_prompt, total_slides, theme)
            
        Returns:
            Dict with artifact_id and progress_id
        """
        try:
            # Validate session
            session = db.session.query(ResearchSession).filter(
                ResearchSession.id == session_id,
                ResearchSession.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError(f"Research session not found: {session_id}")
            
            # Create progress record
            progress = Progress(
                user_id=user_id,
                tool="presentation",
                stage="create",
                status="pending",
                percentage=0,
                created_at=datetime.utcnow()
            )
            db.session.add(progress)
            db.session.flush()
            
            # Create artifact record
            artifact = ResearchArtifact(
                session_id=session_id,
                artifact_type="presentation",
                title=title,
                status="pending",
                config_data={
                    "file_id": file_id,
                    "options": options,
                    "user_id": user_id
                },
                progress_id=progress.id
            )
            db.session.add(artifact)
            db.session.commit()
            
            self.logger.info(f"[ResearchArtifacts] Created presentation artifact {artifact.id} for session {session_id}")
            
            # Launch Celery task with artifact_id
            generate_presentation_content_task.apply_async(
                args=[user_id, file_id, str(progress.id), options],
                kwargs={"artifact_id": str(artifact.id)}
            )
            
            return {
                "artifact_id": str(artifact.id),
                "progress_id": str(progress.id),
                "status": "pending"
            }
            
        except Exception as e:
            self.logger.error(f"[ResearchArtifacts] Error generating presentation: {str(e)}")
            db.session.rollback()
            raise
    
    def get_artifact(self, artifact_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get artifact by ID with user validation.
        
        Args:
            artifact_id: Artifact UUID
            user_id: User UUID for validation
            
        Returns:
            Artifact dict or None
        """
        try:
            artifact = db.session.query(ResearchArtifact).join(
                ResearchSession
            ).filter(
                ResearchArtifact.id == artifact_id,
                ResearchSession.user_id == user_id
            ).first()
            
            if not artifact:
                return None
            
            return self._artifact_to_dict(artifact)
            
        except Exception as e:
            self.logger.error(f"[ResearchArtifacts] Error getting artifact: {str(e)}")
            return None
    
    def list_artifacts(
        self,
        session_id: str,
        user_id: str,
        artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List artifacts for a research session.
        
        Args:
            session_id: Research session UUID
            user_id: User UUID for validation
            artifact_type: Optional filter by type (flashcards/presentation)
            
        Returns:
            List of artifact dicts
        """
        try:
            query = db.session.query(ResearchArtifact).join(
                ResearchSession
            ).filter(
                ResearchArtifact.session_id == session_id,
                ResearchSession.user_id == user_id
            )
            
            if artifact_type:
                query = query.filter(ResearchArtifact.artifact_type == artifact_type)
            
            artifacts = query.order_by(ResearchArtifact.created_at.desc()).all()
            
            return [self._artifact_to_dict(a) for a in artifacts]
            
        except Exception as e:
            self.logger.error(f"[ResearchArtifacts] Error listing artifacts: {str(e)}")
            return []
    
    def update_artifact_result(
        self,
        artifact_id: str,
        result_data: Dict[str, Any],
        status: str = "completed"
    ) -> bool:
        """
        Update artifact with result data from Celery task.
        Called by task completion callbacks.
        
        Args:
            artifact_id: Artifact UUID
            result_data: Result data from tool service
            status: New status (completed/failed)
            
        Returns:
            True if successful
        """
        try:
            artifact = db.session.query(ResearchArtifact).filter(
                ResearchArtifact.id == artifact_id
            ).first()
            
            if not artifact:
                self.logger.error(f"[ResearchArtifacts] Artifact not found: {artifact_id}")
                return False
            
            artifact.result_data = result_data
            artifact.status = status
            artifact.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"[ResearchArtifacts] Updated artifact {artifact_id} with status {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"[ResearchArtifacts] Error updating artifact: {str(e)}")
            db.session.rollback()
            return False
    
    def update_artifact_error(
        self,
        artifact_id: str,
        error_message: str
    ) -> bool:
        """
        Update artifact with error information.
        
        Args:
            artifact_id: Artifact UUID
            error_message: Error description
            
        Returns:
            True if successful
        """
        try:
            artifact = db.session.query(ResearchArtifact).filter(
                ResearchArtifact.id == artifact_id
            ).first()
            
            if not artifact:
                return False
            
            artifact.status = "failed"
            artifact.error_message = error_message
            artifact.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"[ResearchArtifacts] Marked artifact {artifact_id} as failed")
            return True
            
        except Exception as e:
            self.logger.error(f"[ResearchArtifacts] Error updating artifact error: {str(e)}")
            db.session.rollback()
            return False
    
    def _artifact_to_dict(self, artifact: ResearchArtifact) -> Dict[str, Any]:
        """Convert artifact model to dict."""
        return {
            "id": str(artifact.id),
            "session_id": str(artifact.session_id),
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "status": artifact.status,
            "config_data": artifact.config_data,
            "result_data": artifact.result_data,
            "progress_id": str(artifact.progress_id) if artifact.progress_id else None,
            "error_message": artifact.error_message,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
            "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None
        }
