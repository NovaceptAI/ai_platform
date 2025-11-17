"""
Peer Review Tasks for Collaborate Stage
Handles review assignment, deadline management, and review analytics
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from celery import Celery, shared_task
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import joinedload
from app.db import db
from app.models.collaboration import (
    CollaborationSession, SessionParticipant, 
    PeerReview, CollaborationNotification
)
from app.models.users import Users
from app.services.websocket_service import socketio
# from app.celery_worker import celery
import random

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_deadline_reminders(self, session_id: int, hours_before: int = 24):
    """
    Send deadline reminders to participants with pending reviews
    """
    # Database operations
    try:
        # Database operations
        # Get session info
        collab_session = db.session.query(CollaborationSession).filter(
            CollaborationSession.id == session_id
        ).first()
        
        if not collab_session:
            return {"success": False, "error": "Session not found"}
        
        deadline_str = collab_session.metadata.get('deadline')
        if not deadline_str:
            return {"success": True, "message": "No deadline set for session"}
        
        deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
        reminder_time = deadline - timedelta(hours=hours_before)
        
        # Check if it's time to send reminder
        if datetime.utcnow() < reminder_time:
            return {"success": True, "message": "Not yet time to send reminder"}
        
        # Get participants with pending assignments
        pending_assignments = db.session.query(PeerReview).options(
            joinedload(PeerReview.reviewer)
        ).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'assignment',
                PeerReview.status == 'assigned'
            )
        ).all()
        
        if not pending_assignments:
            return {"success": True, "message": "No pending assignments"}
        
        reminders_sent = 0
        
        for assignment in pending_assignments:
            if assignment.reviewer:
                # Create reminder notification
                notification = CollaborationNotification(
                    user_id=assignment.reviewer_id,
                    session_id=session_id,
                    notification_type='deadline_reminder',
                    title='Peer Review Deadline Approaching',
                    message=f'Your review for "{collab_session.title}" is due in {hours_before} hours',
                    metadata={
                        'assignment_id': assignment.id,
                        'deadline': deadline_str,
                        'hours_remaining': hours_before
                    }
                )
                db.session.add(notification)
                
                # Emit real-time notification
                socketio.emit('deadline_reminder', {
                    'session_id': session_id,
                    'assignment_id': assignment.id,
                    'deadline': deadline_str,
                    'hours_remaining': hours_before
                }, room=f"user_{assignment.reviewer_id}", namespace='/notifications')
                
                reminders_sent += 1
        
        db.session.commit()
        
        logger.info(f"Sent {reminders_sent} deadline reminders for session {session_id}")
        
        return {
            "success": True,
            "reminders_sent": reminders_sent
        }
            
    except Exception as e:
        logger.error(f"Error sending deadline reminders: {str(e)}")
        self.retry(countdown=60, exc=e)

@shared_task(bind=True, max_retries=3)
def auto_assign_reviews(self, session_id: int, strategy: str = 'balanced'):
    """
    Automatically assign reviews based on submissions and participants
    """
    # Database operations
    try:
        # Database operations
        collab_session = db.session.query(CollaborationSession).filter(
            CollaborationSession.id == session_id
        ).first()
        
        if not collab_session:
            return {"success": False, "error": "Session not found"}
        
        # Get session settings
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
        
        # Get all participants
        participants = db.session.query(SessionParticipant).filter(
            and_(
                SessionParticipant.session_id == session_id,
                SessionParticipant.status == 'joined'
            )
        ).all()
        
        if len(participants) < 2 or not submissions:
            return {"success": False, "error": "Insufficient participants or submissions"}
        
        assignments_created = 0
        
        if strategy == 'balanced':
            # Balanced assignment: distribute reviews evenly across reviewers
            reviewers = [p for p in participants]
            reviewer_loads = {p.user_id: 0 for p in reviewers}
            
            for submission in submissions:
                # Get eligible reviewers
                eligible_reviewers = [r for r in reviewers 
                                    if allow_self_review or r.user_id != submission.author_id]
                
                if len(eligible_reviewers) < min_reviews:
                    continue
                
                # Sort by current load (ascending)
                eligible_reviewers.sort(key=lambda r: reviewer_loads[r.user_id])
                
                # Assign to least loaded reviewers
                assigned = 0
                for reviewer in eligible_reviewers:
                    if assigned >= min_reviews:
                        break
                    
                    if reviewer_loads[reviewer.user_id] >= max_reviews_per_reviewer:
                        continue
                    
                    # Check if assignment already exists
                    existing = db.session.query(PeerReview).filter(
                        and_(
                            PeerReview.session_id == session_id,
                            PeerReview.reviewer_id == reviewer.user_id,
                            PeerReview.target_submission_id == submission.id,
                            PeerReview.review_type == 'assignment'
                        )
                    ).first()
                    
                    if not existing:
                        assignment = PeerReview(
                            session_id=session_id,
                            reviewer_id=reviewer.user_id,
                            target_submission_id=submission.id,
                            review_type='assignment',
                            status='assigned',
                            metadata={
                                'auto_assigned': True,
                                'strategy': strategy
                            }
                        )
                        db.session.add(assignment)
                        reviewer_loads[reviewer.user_id] += 1
                        assignments_created += 1
                        assigned += 1
        
        elif strategy == 'expertise_matching':
            # Match reviewers based on expertise/interest (simplified)
            # This would require additional metadata about user expertise
            # For now, fall back to random assignment
            strategy = 'random'
        
        if strategy == 'random':
            # Random assignment with load balancing
            for submission in submissions:
                eligible_reviewers = [r for r in participants 
                                    if allow_self_review or r.user_id != submission.author_id]
                
                if len(eligible_reviewers) < min_reviews:
                    continue
                
                # Filter by current review load
                available_reviewers = []
                for reviewer in eligible_reviewers:
                    current_load = db.session.query(PeerReview).filter(
                        and_(
                            PeerReview.session_id == session_id,
                            PeerReview.reviewer_id == reviewer.user_id,
                            PeerReview.review_type == 'assignment'
                        )
                    ).count()
                    
                    if current_load < max_reviews_per_reviewer:
                        available_reviewers.append(reviewer)
                
                # Randomly select from available reviewers
                selected_count = min(min_reviews, len(available_reviewers))
                if selected_count > 0:
                    selected_reviewers = random.sample(available_reviewers, selected_count)
                    
                    for reviewer in selected_reviewers:
                        # Check if assignment already exists
                        existing = db.session.query(PeerReview).filter(
                            and_(
                                PeerReview.session_id == session_id,
                                PeerReview.reviewer_id == reviewer.user_id,
                                PeerReview.target_submission_id == submission.id,
                                PeerReview.review_type == 'assignment'
                            )
                        ).first()
                        
                        if not existing:
                            assignment = PeerReview(
                                session_id=session_id,
                                reviewer_id=reviewer.user_id,
                                target_submission_id=submission.id,
                                review_type='assignment',
                                status='assigned',
                                metadata={
                                    'auto_assigned': True,
                                    'strategy': strategy
                                }
                            )
                            db.session.add(assignment)
                            assignments_created += 1
        
        db.session.commit()
        
        # Send notifications to assigned reviewers
        new_assignments = db.session.query(PeerReview).options(
            joinedload(PeerReview.target_submission),
            joinedload(PeerReview.reviewer)
        ).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'assignment',
                PeerReview.metadata.contains({'auto_assigned': True})
            )
        ).all()
        
        for assignment in new_assignments:
            if assignment.reviewer and assignment.target_submission:
                notification = CollaborationNotification(
                    user_id=assignment.reviewer_id,
                    session_id=session_id,
                    notification_type='review_assignment',
                    title='New Peer Review Assignment',
                    message=f'You have been assigned to review "{assignment.target_submission.title}"',
                    metadata={
                        'assignment_id': assignment.id,
                        'submission_id': assignment.target_submission_id,
                        'auto_assigned': True
                    }
                )
                db.session.add(notification)
        
        db.session.commit()
        
        # Emit WebSocket event
        socketio.emit('auto_assignments_complete', {
            'session_id': session_id,
            'assignments_created': assignments_created,
            'strategy': strategy
        }, namespace='/collaborate')
        
        logger.info(f"Auto-assigned {assignments_created} reviews for session {session_id}")
        
        return {
            "success": True,
            "assignments_created": assignments_created,
            "strategy": strategy
        }
            
    except Exception as e:
        logger.error(f"Error in auto assignment: {str(e)}")
        self.retry(countdown=60, exc=e)

@shared_task(bind=True, max_retries=3)
def generate_review_analytics(self, session_id: int):
    """
    Generate comprehensive analytics for a review session
    """
    # Database operations
    try:
        # Database operations
        collab_session = db.session.query(CollaborationSession).filter(
            CollaborationSession.id == session_id
        ).first()
        
        if not collab_session:
            return {"success": False, "error": "Session not found"}
        
        # Basic counts
        total_participants = db.session.query(SessionParticipant).filter(
            SessionParticipant.session_id == session_id
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
        
        total_assignments = db.session.query(PeerReview).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'assignment'
            )
        ).count()
        
        # Completion rates
        completion_rate = (total_reviews / max(total_assignments, 1)) * 100
        participation_rate = (total_submissions / max(total_participants, 1)) * 100
        
        # Rating analysis
        reviews_with_ratings = db.session.query(PeerReview).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'review',
                PeerReview.rating.isnot(None)
            )
        ).all()
        
        ratings = [r.rating for r in reviews_with_ratings]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        rating_distribution = {}
        for rating in ratings:
            rating_distribution[rating] = rating_distribution.get(rating, 0) + 1
        
        # Review quality metrics (based on length and completeness)
        review_lengths = []
        reviews_with_rubric = 0
        
        for review in db.session.query(PeerReview).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'review'
            )
        ).all():
            if review.content:
                review_lengths.append(len(review.content.split()))
            
            if review.metadata and review.metadata.get('rubric_scores'):
                reviews_with_rubric += 1
        
        avg_review_length = sum(review_lengths) / len(review_lengths) if review_lengths else 0
        
        # Reviewer performance
        reviewer_stats = {}
        reviewers = db.session.query(PeerReview.reviewer_id).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'review'
            )
        ).distinct().all()
        
        for (reviewer_id,) in reviewers:
            user_reviews = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.reviewer_id == reviewer_id,
                    PeerReview.review_type == 'review'
                )
            ).all()
            
            user_ratings = [r.rating for r in user_reviews if r.rating is not None]
            avg_user_rating = sum(user_ratings) / len(user_ratings) if user_ratings else 0
            
            reviewer_stats[reviewer_id] = {
                'reviews_completed': len(user_reviews),
                'avg_rating_given': avg_user_rating,
                'avg_review_length': sum(len(r.content.split()) for r in user_reviews if r.content) / len(user_reviews) if user_reviews else 0
            }
        
        # Time analysis
        review_times = []
        for review in db.session.query(PeerReview).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'review'
            )
        ).all():
            if review.metadata and review.metadata.get('review_time_minutes'):
                review_times.append(review.metadata['review_time_minutes'])
        
        avg_review_time = sum(review_times) / len(review_times) if review_times else 0
        
        # Submission analysis
        submission_stats = {}
        submissions = db.session.query(PeerReview).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'submission'
            )
        ).all()
        
        for submission in submissions:
            submission_reviews = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.target_submission_id == submission.id,
                    PeerReview.review_type == 'review'
                )
            ).all()
            
            submission_ratings = [r.rating for r in submission_reviews if r.rating is not None]
            avg_submission_rating = sum(submission_ratings) / len(submission_ratings) if submission_ratings else 0
            
            submission_stats[submission.id] = {
                'title': submission.title,
                'author_id': submission.author_id,
                'reviews_received': len(submission_reviews),
                'avg_rating': avg_submission_rating,
                'word_count': submission.metadata.get('word_count', 0) if submission.metadata else 0
            }
        
        analytics_data = {
            'session_id': session_id,
            'generated_at': datetime.utcnow().isoformat(),
            'overview': {
                'total_participants': total_participants,
                'total_submissions': total_submissions,
                'total_reviews': total_reviews,
                'total_assignments': total_assignments,
                'completion_rate': round(completion_rate, 2),
                'participation_rate': round(participation_rate, 2)
            },
            'ratings': {
                'average_rating': round(avg_rating, 2),
                'rating_distribution': rating_distribution,
                'total_rated_reviews': len(ratings)
            },
            'review_quality': {
                'avg_review_length_words': round(avg_review_length, 2),
                'reviews_with_rubric': reviews_with_rubric,
                'rubric_usage_rate': round((reviews_with_rubric / max(total_reviews, 1)) * 100, 2),
                'avg_review_time_minutes': round(avg_review_time, 2)
            },
            'top_reviewers': sorted(
                [{'reviewer_id': k, **v} for k, v in reviewer_stats.items()],
                key=lambda x: x['reviews_completed'],
                reverse=True
            )[:5],
            'submission_summary': list(submission_stats.values())
        }
        
        # Store analytics in session metadata
        if not collab_session.metadata:
            collab_session.metadata = {}
        
        collab_session.metadata['analytics'] = analytics_data
        db.session.commit()
        
        logger.info(f"Generated review analytics for session {session_id}")
        
        return {"success": True, "analytics": analytics_data}
            
    except Exception as e:
        logger.error(f"Error generating review analytics: {str(e)}")
        self.retry(countdown=60, exc=e)

@shared_task(bind=True, max_retries=3)
def close_review_session(self, session_id: int):
    """
    Close a review session and generate final reports
    """
    # Database operations
    try:
        # Database operations
        collab_session = db.session.query(CollaborationSession).filter(
            CollaborationSession.id == session_id
        ).first()
        
        if not collab_session:
            return {"success": False, "error": "Session not found"}
        
        # Check if deadline has passed
        deadline_str = collab_session.metadata.get('deadline')
        if deadline_str:
            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            if datetime.utcnow() < deadline:
                return {"success": False, "error": "Deadline has not passed yet"}
        
        # Mark session as inactive
        collab_session.is_active = False
        collab_session.metadata = collab_session.metadata or {}
        collab_session.metadata['closed_at'] = datetime.utcnow().isoformat()
        
        # Generate final analytics
        analytics_task = generate_review_analytics.delay(session_id)
        
        # Mark all pending assignments as expired
        pending_assignments = db.session.query(PeerReview).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'assignment',
                PeerReview.status == 'assigned'
            )
        ).all()
        
        expired_count = 0
        for assignment in pending_assignments:
            assignment.status = 'expired'
            expired_count += 1
        
        # Notify all participants about session closure
        participants = db.session.query(SessionParticipant).options(
            joinedload(SessionParticipant.user)
        ).filter(
            SessionParticipant.session_id == session_id
        ).all()
        
        for participant in participants:
            notification = CollaborationNotification(
                user_id=participant.user_id,
                session_id=session_id,
                notification_type='session_closed',
                title='Review Session Closed',
                message=f'The peer review session "{collab_session.title}" has been closed',
                metadata={
                    'expired_assignments': expired_count,
                    'closed_at': collab_session.metadata['closed_at']
                }
            )
            db.session.add(notification)
        
        db.session.commit()
        
        # Emit WebSocket event
        socketio.emit('session_closed', {
            'session_id': session_id,
            'title': collab_session.title,
            'expired_assignments': expired_count,
            'closed_at': collab_session.metadata['closed_at']
        }, namespace='/collaborate')
        
        logger.info(f"Closed review session {session_id}, expired {expired_count} assignments")
        
        return {
            "success": True,
            "expired_assignments": expired_count,
            "participants_notified": len(participants)
        }
            
    except Exception as e:
        logger.error(f"Error closing review session: {str(e)}")
        self.retry(countdown=60, exc=e)

@shared_task(bind=True, max_retries=3)
def send_review_quality_feedback(self, session_id: int):
    """
    Send feedback to reviewers about their review quality
    """
    # Database operations
    try:
        # Database operations
        # Get all reviewers and their reviews
        reviewers = db.session.query(PeerReview.reviewer_id).filter(
            and_(
                PeerReview.session_id == session_id,
                PeerReview.review_type == 'review'
            )
        ).distinct().all()
        
        feedback_sent = 0
        
        for (reviewer_id,) in reviewers:
            user_reviews = db.session.query(PeerReview).filter(
                and_(
                    PeerReview.session_id == session_id,
                    PeerReview.reviewer_id == reviewer_id,
                    PeerReview.review_type == 'review'
                )
            ).all()
            
            if not user_reviews:
                continue
            
            # Calculate quality metrics
            avg_length = sum(len(r.content.split()) for r in user_reviews if r.content) / len(user_reviews)
            reviews_with_rubric = sum(1 for r in user_reviews if r.metadata and r.metadata.get('rubric_scores'))
            rubric_usage = (reviews_with_rubric / len(user_reviews)) * 100
            
            # Generate personalized feedback
            feedback_points = []
            
            if avg_length < 50:
                feedback_points.append("Consider providing more detailed feedback in your reviews")
            elif avg_length > 200:
                feedback_points.append("Great job providing comprehensive reviews!")
            
            if rubric_usage < 50:
                feedback_points.append("Try to use the rubric more consistently for structured feedback")
            elif rubric_usage > 80:
                feedback_points.append("Excellent use of the review rubric!")
            
            if len(user_reviews) >= 3:
                feedback_points.append("Thank you for actively participating in peer review!")
            
            if feedback_points:
                notification = CollaborationNotification(
                    user_id=reviewer_id,
                    session_id=session_id,
                    notification_type='review_feedback',
                    title='Peer Review Performance Feedback',
                    message=f'Based on your {len(user_reviews)} reviews: ' + '; '.join(feedback_points),
                    metadata={
                        'reviews_completed': len(user_reviews),
                        'avg_length': round(avg_length, 1),
                        'rubric_usage': round(rubric_usage, 1),
                        'feedback_points': feedback_points
                    }
                )
                db.session.add(notification)
                feedback_sent += 1
        
        db.session.commit()
        
        logger.info(f"Sent quality feedback to {feedback_sent} reviewers in session {session_id}")
        
        return {
            "success": True,
            "feedback_sent": feedback_sent
        }
            
    except Exception as e:
        logger.error(f"Error sending review quality feedback: {str(e)}")
        self.retry(countdown=60, exc=e)
