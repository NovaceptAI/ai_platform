"""
Peer Review Service for Collaborate Stage
Handles structured peer review workflows, anonymous feedback, and rubric-based assessment
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import joinedload
from app.db import db
from app.models.collaboration import (
    CollaborationSession, SessionParticipant, 
    PeerReview, CollaborationNotification
)
from app.models.users import Users
from app.models.learning_paths import LearningPath
from app.services.websocket_service import socketio
import random
import uuid

logger = logging.getLogger(__name__)

class PeerReviewService:
    """Service for managing peer review sessions and workflows"""
    
    @staticmethod
    def create_review_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new peer review session"""
        # Database operations
        try:
            # Database operations
            # Validate learning path exists
            learning_path = db.session.query(LearningPath).filter(
                LearningPath.id == session_data['learning_path_id']
            ).first()
            
            if not learning_path:
                return {"success": False, "error": "Learning path not found"}
            
            # Create collaboration session for peer review
            collaboration_session = CollaborationSession(
                learning_path_id=session_data['learning_path_id'],
                creator_id=session_data['creator_id'],
                session_type='peer_review',
                title=session_data.get('title', f"Peer Review: {learning_path.title}"),
                description=session_data.get('description'),
                max_participants=session_data.get('max_participants', 50),
                is_active=True,
                is_public=session_data.get('is_public', True),
                metadata={
                    'review_type': session_data.get('review_type', 'structured'),  # structured, open, anonymous
                    'deadline': session_data.get('deadline'),
                    'min_reviews_per_submission': session_data.get('min_reviews', 2),
                    'max_reviews_per_reviewer': session_data.get('max_reviews', 5),
                    'anonymous_reviews': session_data.get('anonymous', False),
                    'rubric': session_data.get('rubric', {}),
                    'allow_self_review': session_data.get('allow_self_review', False)
                }
            )
            
            db.session.add(collaboration_session)
            db.session.flush()  # Get the ID
            
            # Add creator as facilitator
            creator_participant = SessionParticipant(
                session_id=collaboration_session.id,
                user_id=session_data['creator_id'],
                role='facilitator',
                status='joined'
            )
            
            db.session.add(creator_participant)
            db.session.commit()
            
            # Emit WebSocket event for new review session
            socketio.emit('review_session_created', {
                'session_id': collaboration_session.id,
                'title': collaboration_session.title,
                'creator': session_data['creator_id'],
                'learning_path_id': collaboration_session.learning_path_id,
                'deadline': session_data.get('deadline')
            }, namespace='/collaborate')
            
            logger.info(f"Created peer review session {collaboration_session.id}")
            
            return {
                "success": True,
                "session_id": collaboration_session.id,
                "session": {
                    "id": collaboration_session.id,
                    "title": collaboration_session.title,
                    "description": collaboration_session.description,
                    "creator_id": collaboration_session.creator_id,
                    "deadline": session_data.get('deadline'),
                    "review_type": collaboration_session.metadata.get('review_type'),
                    "is_active": collaboration_session.is_active
                }
            }
                
        except Exception as e:
            logger.error(f"Error creating peer review session: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def submit_work_for_review(submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit work to be peer reviewed"""
        # Database operations
        try:    
            # Database operations
            # Verify user is participant in the session
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == submission_data['session_id'],
                    SessionParticipant.user_id == submission_data['user_id'],
                    SessionParticipant.status == 'joined'
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to submit to this review session"}
            
            # Check if submission already exists
            existing_review = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == submission_data['session_id'],
                    PeerReview.author_id == submission_data['user_id'],
                    PeerReview.review_type == 'submission'
                )
            ).first()
            
            if existing_review:
                return {"success": False, "error": "Work already submitted for this session"}
            
            # Create submission record
            submission = PeerReview(
                session_id=submission_data['session_id'],
                author_id=submission_data['user_id'],
                review_type='submission',
                title=submission_data.get('title', 'Untitled Submission'),
                content=submission_data['content'],
                submission_format=submission_data.get('format', 'text'),  # text, document, url, etc.
                metadata={
                    'file_urls': submission_data.get('file_urls', []),
                    'submission_notes': submission_data.get('notes'),
                    'word_count': len(submission_data['content'].split()) if submission_data['content'] else 0
                }
            )
            
            db.session.add(submission)
            db.session.flush()  # Get the ID
            
            # Update participant metadata
            if not participant.metadata:
                participant.metadata = {}
            participant.metadata['submitted'] = True
            participant.metadata['submission_id'] = submission.id
            participant.metadata['submission_date'] = datetime.utcnow().isoformat()
            
            db.session.commit()
            
            # Emit WebSocket event
            socketio.emit('work_submitted', {
                'session_id': submission_data['session_id'],
                'submission_id': submission.id,
                'author_id': submission_data['user_id'],
                'title': submission.title,
                'timestamp': submission.created_at.isoformat()
            }, namespace='/collaborate')
            
            logger.info(f"Work submitted for review: submission {submission.id} in session {submission_data['session_id']}")
            
            return {
                "success": True,
                "submission_id": submission.id,
                "message": "Work submitted successfully"
            }
                
        except Exception as e:
            logger.error(f"Error submitting work for review: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def assign_reviews(session_id: int, facilitator_id: int, assignment_strategy: str = 'random') -> Dict[str, Any]:
        """Assign submissions to reviewers"""
        # Database operations
        try:
            # Database operations
            # Verify facilitator permissions
            facilitator = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == facilitator_id,
                    SessionParticipant.role.in_(['facilitator', 'moderator'])
                )
            ).first()
            
            if not facilitator:
                return {"success": False, "error": "Not authorized to assign reviews"}
            
            # Get session metadata
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            min_reviews = collab_session.metadata.get('min_reviews_per_submission', 2)
            max_reviews_per_reviewer = collab_session.metadata.get('max_reviews_per_reviewer', 5)
            allow_self_review = collab_session.metadata.get('allow_self_review', False)
            
            # Get all submissions
            submissions = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.review_type == 'submission'
                )
            ).all()
            
            if not submissions:
                return {"success": False, "error": "No submissions to review"}
            
            # Get all participants who can be reviewers
            reviewers = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.status == 'joined'
                )
            ).all()
            
            if len(reviewers) < 2:
                return {"success": False, "error": "Not enough participants for peer review"}
            
            assignments_created = 0
            
            if assignment_strategy == 'random':
                # Random assignment strategy
                for submission in submissions:
                    # Get eligible reviewers (exclude author if self-review not allowed)
                    eligible_reviewers = [r for r in reviewers 
                                        if allow_self_review or r.user_id != submission.author_id]
                    
                    if len(eligible_reviewers) < min_reviews:
                        continue
                    
                    # Randomly select reviewers
                    selected_reviewers = random.sample(eligible_reviewers, 
                                                        min(min_reviews, len(eligible_reviewers)))
                    
                    for reviewer in selected_reviewers:
                        # Check if reviewer hasn't reached their limit
                        current_reviews = db.session.query(PeerReview).filter(
                            and_(
                                PeerReview.session_id == session_id,
                                PeerReview.reviewer_id == reviewer.user_id,
                                PeerReview.review_type == 'review'
                            )
                        ).count()
                        
                        if current_reviews >= max_reviews_per_reviewer:
                            continue
                        
                        # Check if assignment already exists
                        existing_assignment = db.session.query(PeerReview).filter(
                            and_(
                                PeerReview.session_id == session_id,
                                PeerReview.reviewer_id == reviewer.user_id,
                                PeerReview.target_submission_id == submission.id,
                                PeerReview.review_type == 'assignment'
                            )
                        ).first()
                        
                        if not existing_assignment:
                            # Create review assignment
                            assignment = PeerReview(
                                session_id=session_id,
                                reviewer_id=reviewer.user_id,
                                target_submission_id=submission.id,
                                review_type='assignment',
                                status='assigned',
                                metadata={
                                    'assigned_by': facilitator_id,
                                    'assignment_strategy': assignment_strategy
                                }
                            )
                            db.session.add(assignment)
                            assignments_created += 1
                            
                            # Create notification
                            notification = CollaborationNotification(
                                user_id=reviewer.user_id,
                                session_id=session_id,
                                notification_type='review_assignment',
                                title='New Peer Review Assignment',
                                message=f'You have been assigned to review "{submission.title}"',
                                metadata={'submission_id': submission.id, 'assignment_id': assignment.id}
                            )
                            db.session.add(notification)
            
            db.session.commit()
            
            # Emit WebSocket events for assignments
            socketio.emit('reviews_assigned', {
                'session_id': session_id,
                'assignments_created': assignments_created,
                'strategy': assignment_strategy
            }, namespace='/collaborate')
            
            logger.info(f"Created {assignments_created} review assignments for session {session_id}")
            
            return {
                "success": True,
                "assignments_created": assignments_created,
                "message": f"Successfully assigned {assignments_created} reviews"
            }
                
        except Exception as e:
            logger.error(f"Error assigning reviews: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def submit_review(review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a peer review"""
        # Database operations
        try:
            # Database operations
            # Verify assignment exists
            assignment = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == review_data['session_id'],
                    PeerReview.reviewer_id == review_data['reviewer_id'],
                    PeerReview.target_submission_id == review_data['submission_id'],
                    PeerReview.review_type == 'assignment',
                    PeerReview.status == 'assigned'
                )
            ).first()
            
            if not assignment:
                return {"success": False, "error": "Review assignment not found or already completed"}
            
            # Check if review already submitted
            existing_review = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == review_data['session_id'],
                    PeerReview.reviewer_id == review_data['reviewer_id'],
                    PeerReview.target_submission_id == review_data['submission_id'],
                    PeerReview.review_type == 'review'
                )
            ).first()
            
            if existing_review:
                return {"success": False, "error": "Review already submitted"}
            
            # Get session info for rubric
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == review_data['session_id']
            ).first()
            
            # Create review
            review = PeerReview(
                session_id=review_data['session_id'],
                reviewer_id=review_data['reviewer_id'],
                target_submission_id=review_data['submission_id'],
                review_type='review',
                content=review_data['content'],
                rating=review_data.get('rating'),
                status='completed',
                metadata={
                    'rubric_scores': review_data.get('rubric_scores', {}),
                    'strengths': review_data.get('strengths'),
                    'improvements': review_data.get('improvements'),
                    'is_anonymous': collab_session.metadata.get('anonymous_reviews', False),
                    'review_time_minutes': review_data.get('review_time_minutes')
                }
            )
            
            db.session.add(review)
            
            # Update assignment status
            assignment.status = 'completed'
            assignment.completed_at = datetime.utcnow()
            
            db.session.flush()  # Get review ID
            db.session.commit()
            
            # Get submission author for notification (if not anonymous)
            if not collab_session.metadata.get('anonymous_reviews', False):
                submission = db.session.query(PeerReview).filter(
                    PeerReview.id == review_data['submission_id']
                ).first()
                
                if submission:
                    notification = CollaborationNotification(
                        user_id=submission.author_id,
                        session_id=review_data['session_id'],
                        notification_type='review_received',
                        title='New Peer Review Received',
                        message=f'Your submission "{submission.title}" has received a new review',
                        metadata={'review_id': review.id, 'submission_id': submission.id}
                    )
                    db.session.add(notification)
                    db.session.commit()
            
            # Emit WebSocket event
            socketio.emit('review_submitted', {
                'session_id': review_data['session_id'],
                'review_id': review.id,
                'submission_id': review_data['submission_id'],
                'reviewer_id': review_data['reviewer_id'] if not collab_session.metadata.get('anonymous_reviews') else None,
                'rating': review.rating
            }, namespace='/collaborate')
            
            logger.info(f"Peer review submitted: {review.id} for submission {review_data['submission_id']}")
            
            return {
                "success": True,
                "review_id": review.id,
                "message": "Review submitted successfully"
            }
                
        except Exception as e:
            logger.error(f"Error submitting review: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_review_assignments(session_id: int, user_id: int) -> Dict[str, Any]:
        """Get review assignments for a user"""
        # Database operations
        try:
            # Database operations
            # Verify user is participant
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to view assignments"}
            
            # Get assignments
            assignments = db.session.query(PeerReview).options(
                joinedload(PeerReview.target_submission)
            ).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.reviewer_id == user_id,
                    PeerReview.review_type == 'assignment'
                )
            ).all()
            
            # Format assignments
            formatted_assignments = []
            for assignment in assignments:
                if assignment.target_submission:
                    formatted_assignments.append({
                        'assignment_id': assignment.id,
                        'submission_id': assignment.target_submission.id,
                        'submission_title': assignment.target_submission.title,
                        'submission_content': assignment.target_submission.content,
                        'submission_format': assignment.target_submission.submission_format,
                        'assignment_status': assignment.status,
                        'assigned_at': assignment.created_at.isoformat(),
                        'due_date': assignment.due_date.isoformat() if assignment.due_date else None,
                        'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None
                    })
            
            return {
                "success": True,
                "assignments": formatted_assignments
            }
                
        except Exception as e:
            logger.error(f"Error getting review assignments: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_reviews_received(session_id: int, user_id: int) -> Dict[str, Any]:
        """Get reviews received for user's submissions"""
        # Database operations
        try:
            # Database operations
            # Verify user is participant
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to view reviews"}
            
            # Get user's submissions
            submissions = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.author_id == user_id,
                    PeerReview.review_type == 'submission'
                )
            ).all()
            
            # Get reviews for each submission
            formatted_submissions = []
            for submission in submissions:
                reviews = db.session.query(PeerReview).options(
                    joinedload(PeerReview.reviewer)
                ).filter(
                    and_(
                        PeerReview.session_id == session_id,
                        PeerReview.target_submission_id == submission.id,
                        PeerReview.review_type == 'review'
                    )
                ).all()
                
                # Format reviews (respecting anonymity)
                collab_session = db.session.query(CollaborationSession).filter(
                    CollaborationSession.id == session_id
                ).first()
                
                is_anonymous = collab_session.metadata.get('anonymous_reviews', False)
                
                formatted_reviews = []
                for review in reviews:
                    review_data = {
                        'review_id': review.id,
                        'content': review.content,
                        'rating': review.rating,
                        'strengths': review.metadata.get('strengths'),
                        'improvements': review.metadata.get('improvements'),
                        'rubric_scores': review.metadata.get('rubric_scores', {}),
                        'submitted_at': review.created_at.isoformat()
                    }
                    
                    if not is_anonymous:
                        review_data['reviewer_id'] = review.reviewer_id
                        review_data['reviewer_name'] = review.reviewer.username if review.reviewer else 'Unknown'
                    
                    formatted_reviews.append(review_data)
                
                # Calculate average rating
                ratings = [r.rating for r in reviews if r.rating is not None]
                avg_rating = sum(ratings) / len(ratings) if ratings else None
                
                formatted_submissions.append({
                    'submission_id': submission.id,
                    'title': submission.title,
                    'content': submission.content,
                    'submitted_at': submission.created_at.isoformat(),
                    'reviews_count': len(reviews),
                    'average_rating': avg_rating,
                    'reviews': formatted_reviews
                })
            
            return {
                "success": True,
                "submissions": formatted_submissions
            }
                
        except Exception as e:
            logger.error(f"Error getting reviews received: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_review_session_overview(session_id: int, user_id: int) -> Dict[str, Any]:
        """Get overview of a review session"""
        # Database operations
        try:
            # Database operations
            # Verify user is participant
            participant = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.user_id == user_id
                )
            ).first()
            
            if not participant:
                return {"success": False, "error": "Not authorized to view session"}
            
            # Get session details
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            # Count statistics
            total_participants = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.status == 'joined'
                )
            ).count()
            
            total_submissions = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.review_type == 'submission'
                )
            ).count()
            
            total_reviews = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.review_type == 'review'
                )
            ).count()
            
            pending_assignments = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.review_type == 'assignment',
                    PeerReview.status == 'assigned'
                )
            ).count()
            
            # User-specific stats
            user_submitted = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.author_id == user_id,
                    PeerReview.review_type == 'submission'
                )
            ).first() is not None
            
            user_assignments = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.reviewer_id == user_id,
                    PeerReview.review_type == 'assignment'
                )
            ).count()
            
            user_completed_reviews = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.reviewer_id == user_id,
                    PeerReview.review_type == 'review'
                )
            ).count()
            
            return {
                "success": True,
                "session": {
                    "id": collab_session.id,
                    "title": collab_session.title,
                    "description": collab_session.description,
                    "created_at": collab_session.created_at.isoformat(),
                    "deadline": collab_session.metadata.get('deadline'),
                    "review_type": collab_session.metadata.get('review_type'),
                    "is_anonymous": collab_session.metadata.get('anonymous_reviews', False),
                    "min_reviews": collab_session.metadata.get('min_reviews_per_submission', 2)
                },
                "statistics": {
                    "total_participants": total_participants,
                    "total_submissions": total_submissions,
                    "total_reviews": total_reviews,
                    "pending_assignments": pending_assignments,
                    "completion_rate": round((total_reviews / max(pending_assignments + total_reviews, 1)) * 100, 2)
                },
                "user_progress": {
                    "has_submitted": user_submitted,
                    "assignments_count": user_assignments,
                    "completed_reviews": user_completed_reviews,
                    "pending_reviews": user_assignments - user_completed_reviews
                }
            }
                
        except Exception as e:
            logger.error(f"Error getting review session overview: {str(e)}")
            return {"success": False, "error": str(e)}
