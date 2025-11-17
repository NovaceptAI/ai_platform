"""
Group Discussion Tasks for Collaborate Stage
Handles discussion moderation, activity tracking, and participant engagement
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
# from celery import Celery
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import joinedload
from app.db import db
from app.models.collaboration import (
    CollaborationSession, SessionParticipant, 
    CollaborationComment, CollaborationNotification
)
from app.models.users import Users
from app.services.websocket_service import socketio
from app.celery_worker import celery_app
import random

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def monitor_discussion_activity(self, session_id: int):
    """
    Monitor discussion activity and send engagement notifications
    """
    try:
        with db.app.app_context():
            # Get session info
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session or not collab_session.is_active:
                return {"success": False, "error": "Session not found or inactive"}
            
            # Get participants
            participants = db.session.query(SessionParticipant).options(
                joinedload(SessionParticipant.user)
            ).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.status == 'joined'
                )
            ).all()
            
            if not participants:
                return {"success": True, "message": "No participants found"}
            
            # Check activity in last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Get recent messages
            recent_messages = db.session.query(CollaborationComment).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message',
                    CollaborationComment.created_at >= cutoff_time
                )
            ).count()
            
            # Get active participants (those who posted recently)
            active_users = db.session.query(CollaborationComment.user_id).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message',
                    CollaborationComment.created_at >= cutoff_time
                )
            ).distinct().all()
            
            active_user_ids = [user_id for (user_id,) in active_users]
            
            # Find inactive participants
            inactive_participants = [p for p in participants if p.user_id not in active_user_ids]
            
            # Send engagement notifications to inactive users
            notifications_sent = 0
            for participant in inactive_participants:
                # Check if user was active in last 48 hours (don't spam)
                last_activity = db.session.query(CollaborationComment).filter(
                    and_(
                        CollaborationComment.session_id == session_id,
                        CollaborationComment.user_id == participant.user_id,
                        CollaborationComment.created_at >= cutoff_time - timedelta(hours=24)
                    )
                ).first()
                
                if not last_activity:
                    notification = CollaborationNotification(
                        user_id=participant.user_id,
                        session_id=session_id,
                        notification_type='engagement_reminder',
                        title='Discussion Activity',
                        message=f'New activity in "{collab_session.title}" - {recent_messages} new messages',
                        notification_metadata={
                            'recent_messages': recent_messages,
                            'active_participants': len(active_user_ids),
                            'total_participants': len(participants)
                        }
                    )
                    db.session.add(notification)
                    
                    # Emit real-time notification
                    socketio.emit('engagement_reminder', {
                        'session_id': session_id,
                        'recent_messages': recent_messages,
                        'title': collab_session.title
                    }, room=f"user_{participant.user_id}", namespace='/notifications')
                    
                    notifications_sent += 1
            
            db.session.commit()
            
            # Update session metadata with activity stats
            if not collab_session.session_metadata:
                collab_session.session_metadata = {}
            
            collab_session.session_metadata.update({
                'last_activity_check': datetime.utcnow().isoformat(),
                'recent_message_count': recent_messages,
                'active_participants': len(active_user_ids),
                'total_participants': len(participants)
            })
            db.session.commit()
            
            logger.info(f"Monitored activity for session {session_id}: {recent_messages} messages, {len(active_user_ids)} active users")
            
            return {
                "success": True,
                "recent_messages": recent_messages,
                "active_participants": len(active_user_ids),
                "notifications_sent": notifications_sent
            }
            
    except Exception as e:
        logger.error(f"Error monitoring discussion activity: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def moderate_discussion_content(self, session_id: int):
    """
    Automatically moderate discussion content for inappropriate material
    """
    try:
        with db.app.app_context():
            # Get session info
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            # Get recent unmoderated messages (last hour)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            recent_messages = db.session.query(CollaborationComment).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message',
                    CollaborationComment.created_at >= cutoff_time,
                    CollaborationComment.is_flagged == False,
                    CollaborationComment.is_deleted == False
                )
            ).all()
            
            if not recent_messages:
                return {"success": True, "message": "No new messages to moderate"}
            
            # Simple content filtering (can be enhanced with AI/ML models)
            flagged_keywords = [
                'spam', 'inappropriate', 'offensive', 'harassment', 
                'bullying', 'hate', 'discrimination', 'toxic'
            ]
            
            moderated_count = 0
            
            for message in recent_messages:
                content_lower = message.content.lower()
                
                # Check for flagged keywords
                flagged = False
                flagged_reason = []
                
                for keyword in flagged_keywords:
                    if keyword in content_lower:
                        flagged = True
                        flagged_reason.append(f"Contains '{keyword}'")
                        break
                
                # Check for excessive caps (potential shouting)
                if len(message.content) > 20:
                    caps_ratio = sum(1 for c in message.content if c.isupper()) / len(message.content)
                    if caps_ratio > 0.7:
                        flagged = True
                        flagged_reason.append("Excessive caps")
                
                # Check for excessive length (potential spam)
                if len(message.content) > 5000:
                    flagged = True
                    flagged_reason.append("Excessive length")
                
                # Check for repeated characters (spam indicator)
                if len(set(message.content)) < len(message.content) * 0.3 and len(message.content) > 10:
                    flagged = True
                    flagged_reason.append("Repeated characters")
                
                if flagged:
                    message.is_flagged = True
                    message.moderation_reason = 'Auto-flagged: ' + ', '.join(flagged_reason)
                    message.moderated_at = datetime.utcnow()
                    moderated_count += 1
                    
                    # Notify moderators
                    moderators = db.session.query(SessionParticipant).filter(
                        and_(
                            SessionParticipant.session_id == session_id,
                            SessionParticipant.role.in_(['facilitator', 'moderator']),
                            SessionParticipant.status == 'joined'
                        )
                    ).all()
                    
                    for moderator in moderators:
                        notification = CollaborationNotification(
                            user_id=moderator.user_id,
                            session_id=session_id,
                            notification_type='moderation_alert',
                            title='Content Flagged for Review',
                            message=f'A message has been auto-flagged in "{collab_session.title}"',
                            notification_metadata={
                                'message_id': message.id,
                                'reason': message.moderation_reason,
                                'author_id': message.user_id
                            }
                        )
                        db.session.add(notification)
                    
                    # Emit WebSocket event for real-time moderation
                    socketio.emit('message_moderated', {
                        'message_id': message.id,
                        'session_id': session_id,
                        'reason': message.moderation_reason,
                        'auto_flagged': True
                    }, room=f"discussion_{session_id}", namespace='/collaborate')
            
            db.session.commit()
            
            logger.info(f"Moderated {moderated_count} messages in session {session_id}")
            
            return {
                "success": True,
                "messages_checked": len(recent_messages),
                "messages_flagged": moderated_count
            }
            
    except Exception as e:
        logger.error(f"Error moderating discussion content: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def generate_discussion_summary(self, session_id: int, time_period_hours: int = 24):
    """
    Generate a comprehensive summary of discussion activity and key topics
    """
    try:
        with db.app.app_context():
            # Get session info
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            # Get messages from specified time period
            cutoff_time = datetime.utcnow() - timedelta(hours=time_period_hours)
            messages = db.session.query(CollaborationComment).options(
                joinedload(CollaborationComment.user)
            ).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message',
                    CollaborationComment.created_at >= cutoff_time,
                    CollaborationComment.is_deleted == False
                )
            ).order_by(CollaborationComment.created_at).all()
            
            if not messages:
                return {"success": True, "message": "No messages in time period"}
            
            # Basic statistics
            total_messages = len(messages)
            unique_participants = len(set(msg.user_id for msg in messages))
            
            # Participant activity analysis
            participant_stats = {}
            for message in messages:
                user_id = message.user_id
                if user_id not in participant_stats:
                    participant_stats[user_id] = {
                        'username': message.user.username if message.user else 'Unknown',
                        'message_count': 0,
                        'total_words': 0,
                        'first_message': message.created_at,
                        'last_message': message.created_at,
                        'thread_starts': 0,
                        'replies': 0
                    }
                
                participant_stats[user_id]['message_count'] += 1
                participant_stats[user_id]['total_words'] += len(message.content.split())
                
                if message.created_at > participant_stats[user_id]['last_message']:
                    participant_stats[user_id]['last_message'] = message.created_at
                
                if message.parent_id is None:
                    participant_stats[user_id]['thread_starts'] += 1
                else:
                    participant_stats[user_id]['replies'] += 1
            
            # Top contributors
            top_contributors = sorted(
                participant_stats.items(),
                key=lambda x: x[1]['message_count'],
                reverse=True
            )[:5]
            
            # Word frequency analysis (simple keyword extraction)
            all_words = []
            for message in messages:
                words = message.content.lower().split()
                # Filter out common words and short words
                filtered_words = [w for w in words if len(w) > 4 and w.isalpha() 
                                and w not in ['this', 'that', 'with', 'from', 'they', 'have', 'will', 'been', 'their']]
                all_words.extend(filtered_words)
            
            word_freq = {}
            for word in all_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
            
            # Thread analysis
            threaded_messages = [msg for msg in messages if msg.parent_id is not None]
            thread_count = len(set(msg.parent_id for msg in threaded_messages))
            
            # Time distribution analysis
            hour_distribution = {}
            day_distribution = {}
            for message in messages:
                hour = message.created_at.hour
                day = message.created_at.strftime('%Y-%m-%d')
                hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
                day_distribution[day] = day_distribution.get(day, 0) + 1
            
            # Engagement metrics
            avg_response_time = 0
            if len(threaded_messages) > 0:
                response_times = []
                for reply in threaded_messages:
                    parent_msg = next((m for m in messages if m.id == reply.parent_id), None)
                    if parent_msg:
                        time_diff = (reply.created_at - parent_msg.created_at).total_seconds() / 60  # minutes
                        response_times.append(time_diff)
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
            
            # Generate summary
            summary_data = {
                'session_id': session_id,
                'time_period_hours': time_period_hours,
                'generated_at': datetime.utcnow().isoformat(),
                'overview': {
                    'total_messages': total_messages,
                    'unique_participants': unique_participants,
                    'threaded_discussions': thread_count,
                    'avg_messages_per_participant': round(total_messages / max(unique_participants, 1), 1),
                    'avg_words_per_message': round(sum(len(msg.content.split()) for msg in messages) / total_messages, 1),
                    'avg_response_time_minutes': round(avg_response_time, 1)
                },
                'top_contributors': [
                    {
                        'user_id': user_id,
                        'username': stats['username'],
                        'message_count': stats['message_count'],
                        'word_count': stats['total_words'],
                        'thread_starts': stats['thread_starts'],
                        'replies': stats['replies'],
                        'participation_span_hours': round((stats['last_message'] - stats['first_message']).total_seconds() / 3600, 1)
                    }
                    for user_id, stats in top_contributors
                ],
                'top_keywords': [{'word': word, 'frequency': freq} for word, freq in top_keywords],
                'activity_patterns': {
                    'by_hour': hour_distribution,
                    'by_day': day_distribution,
                    'peak_hour': max(hour_distribution.items(), key=lambda x: x[1])[0] if hour_distribution else 0,
                    'most_active_day': max(day_distribution.items(), key=lambda x: x[1])[0] if day_distribution else None
                },
                'engagement_metrics': {
                    'thread_participation_rate': round((thread_count / max(total_messages, 1)) * 100, 1),
                    'avg_response_time_minutes': round(avg_response_time, 1),
                    'messages_per_hour': round(total_messages / time_period_hours, 1)
                }
            }
            
            # Store summary in session metadata
            if not collab_session.session_metadata:
                collab_session.session_metadata = {}
            
            if 'summaries' not in collab_session.session_metadata:
                collab_session.session_metadata['summaries'] = []
            
            collab_session.session_metadata['summaries'].append(summary_data)
            
            # Keep only last 10 summaries
            if len(collab_session.session_metadata['summaries']) > 10:
                collab_session.session_metadata['summaries'] = collab_session.session_metadata['summaries'][-10:]
            
            db.session.commit()
            
            logger.info(f"Generated discussion summary for session {session_id}: {total_messages} messages")
            
            return {"success": True, "summary": summary_data}
            
    except Exception as e:
        logger.error(f"Error generating discussion summary: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def send_discussion_digest(self, session_id: int, recipient_user_id: int = None):
    """
    Send a digest of discussion activity to participants
    """
    try:
        with db.app.app_context():
            # Get session info
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            # Get recent activity (last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_messages = db.session.query(CollaborationComment).options(
                joinedload(CollaborationComment.user)
            ).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message',
                    CollaborationComment.created_at >= cutoff_time,
                    CollaborationComment.is_deleted == False
                )
            ).order_by(desc(CollaborationComment.created_at)).limit(10).all()
            
            if not recent_messages:
                return {"success": True, "message": "No recent activity to digest"}
            
            # Get participants to send digest to
            if recipient_user_id:
                participants = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.user_id == recipient_user_id,
                        SessionParticipant.status == 'joined'
                    )
                ).all()
            else:
                participants = db.session.query(SessionParticipant).filter(
                    and_(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.status == 'joined'
                    )
                ).all()
            
            # Create digest content
            digest_content = {
                'session_title': collab_session.title,
                'session_id': session_id,
                'period': '24 hours',
                'total_messages': len(recent_messages),
                'unique_contributors': len(set(msg.user_id for msg in recent_messages)),
                'top_messages': [
                    {
                        'id': msg.id,
                        'author': msg.user.username if msg.user else 'Unknown',
                        'content': msg.content[:300] + ('...' if len(msg.content) > 300 else ''),
                        'created_at': msg.created_at.isoformat(),
                        'is_reply': msg.parent_id is not None,
                        'word_count': len(msg.content.split())
                    }
                    for msg in recent_messages[:5]  # Top 5 recent messages
                ]
            }
            
            # Send digest to participants
            digests_sent = 0
            for participant in participants:
                # Don't send digest to very active users (more than 5 messages in period)
                user_recent_messages = [msg for msg in recent_messages if msg.user_id == participant.user_id]
                if len(user_recent_messages) > 5:
                    continue
                
                notification = CollaborationNotification(
                    user_id=participant.user_id,
                    session_id=session_id,
                    notification_type='discussion_digest',
                    title=f'Discussion Digest: {collab_session.title}',
                    message=f'{len(recent_messages)} new messages from {len(set(msg.user_id for msg in recent_messages))} participants',
                    notification_metadata=digest_content
                )
                db.session.add(notification)
                digests_sent += 1
            
            db.session.commit()
            
            logger.info(f"Sent discussion digest to {digests_sent} participants for session {session_id}")
            
            return {
                "success": True,
                "digests_sent": digests_sent,
                "recent_messages": len(recent_messages)
            }
            
    except Exception as e:
        logger.error(f"Error sending discussion digest: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def send_inactivity_reminders(self, session_id: int, hours_inactive: int = 24):
    """
    Send reminders to participants who haven't been active
    """
    try:
        with db.app.app_context():
            # Get session info
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session or not collab_session.is_active:
                return {"success": False, "error": "Session not found or inactive"}
            
            # Get participants who haven't been active
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_inactive)
            
            participants = db.session.query(SessionParticipant).options(
                joinedload(SessionParticipant.user)
            ).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.status == 'joined'
                )
            ).all()
            
            reminders_sent = 0
            
            for participant in participants:
                # Check last activity
                last_activity = db.session.query(CollaborationComment).filter(
                    and_(
                        CollaborationComment.session_id == session_id,
                        CollaborationComment.user_id == participant.user_id,
                        CollaborationComment.created_at >= cutoff_time
                    )
                ).first()
                
                if not last_activity:
                    # Get recent topics for context
                    recent_topics = db.session.query(CollaborationComment).filter(
                        and_(
                            CollaborationComment.session_id == session_id,
                            CollaborationComment.parent_id == None,  # Top-level messages
                            CollaborationComment.created_at >= cutoff_time
                        )
                    ).limit(3).all()
                    
                    topic_preview = ', '.join([msg.content[:50] + '...' for msg in recent_topics])
                    
                    notification = CollaborationNotification(
                        user_id=participant.user_id,
                        session_id=session_id,
                        notification_type='inactivity_reminder',
                        title='Discussion Reminder',
                        message=f'Join the conversation in "{collab_session.title}" - Recent topics: {topic_preview}',
                        notification_metadata={
                            'hours_inactive': hours_inactive,
                            'recent_activity_count': len(recent_topics),
                            'session_url': f'/collaborate/discussions/{session_id}'
                        }
                    )
                    db.session.add(notification)
                    
                    # Emit WebSocket notification
                    socketio.emit('inactivity_reminder', {
                        'session_id': session_id,
                        'title': collab_session.title,
                        'hours_inactive': hours_inactive
                    }, room=f"user_{participant.user_id}", namespace='/notifications')
                    
                    reminders_sent += 1
            
            db.session.commit()
            
            logger.info(f"Sent {reminders_sent} inactivity reminders for session {session_id}")
            
            return {
                "success": True,
                "reminders_sent": reminders_sent,
                "hours_inactive": hours_inactive
            }
            
    except Exception as e:
        logger.error(f"Error sending inactivity reminders: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def generate_discussion_analytics(self, session_id: int):
    """
    Generate comprehensive analytics for a discussion session
    """
    try:
        with db.app.app_context():
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            # Basic counts
            total_participants = db.session.query(SessionParticipant).filter(
                SessionParticipant.session_id == session_id
            ).count()
            
            total_messages = db.session.query(CollaborationComment).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message'
                )
            ).count()
            
            # Advanced analytics
            messages = db.session.query(CollaborationComment).options(
                joinedload(CollaborationComment.user)
            ).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message'
                )
            ).all()
            
            # Participation distribution
            user_message_counts = {}
            for msg in messages:
                user_message_counts[msg.user_id] = user_message_counts.get(msg.user_id, 0) + 1
            
            # Calculate participation equality (Gini coefficient approximation)
            if user_message_counts:
                sorted_counts = sorted(user_message_counts.values())
                n = len(sorted_counts)
                index = list(range(1, n + 1))
                gini = (2 * sum(index[i] * sorted_counts[i] for i in range(n))) / (n * sum(sorted_counts)) - (n + 1) / n
                participation_equality = 1 - gini  # Higher = more equal participation
            else:
                participation_equality = 0
            
            # Message quality metrics
            avg_message_length = sum(len(msg.content.split()) for msg in messages) / len(messages) if messages else 0
            
            # Thread depth analysis
            thread_depths = {}
            for msg in messages:
                if msg.parent_id:
                    depth = 1
                    current_parent = msg.parent_id
                    while current_parent:
                        parent_msg = next((m for m in messages if m.id == current_parent), None)
                        if parent_msg and parent_msg.parent_id:
                            depth += 1
                            current_parent = parent_msg.parent_id
                        else:
                            break
                    thread_depths[msg.id] = depth
                else:
                    thread_depths[msg.id] = 0
            
            max_thread_depth = max(thread_depths.values()) if thread_depths else 0
            avg_thread_depth = sum(thread_depths.values()) / len(thread_depths) if thread_depths else 0
            
            # Sentiment analysis (simplified)
            positive_words = ['great', 'good', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'awesome']
            negative_words = ['bad', 'terrible', 'awful', 'hate', 'dislike', 'horrible', 'wrong', 'disagree']
            
            sentiment_scores = []
            for msg in messages:
                content_words = msg.content.lower().split()
                positive_count = sum(1 for word in content_words if word in positive_words)
                negative_count = sum(1 for word in content_words if word in negative_words)
                
                if positive_count + negative_count > 0:
                    sentiment = (positive_count - negative_count) / (positive_count + negative_count)
                    sentiment_scores.append(sentiment)
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            analytics_data = {
                'session_id': session_id,
                'generated_at': datetime.utcnow().isoformat(),
                'overview': {
                    'total_participants': total_participants,
                    'total_messages': total_messages,
                    'messages_per_participant': round(total_messages / max(total_participants, 1), 2),
                    'session_duration_hours': round((datetime.utcnow() - collab_session.created_at).total_seconds() / 3600, 1)
                },
                'engagement': {
                    'participation_equality': round(participation_equality, 3),
                    'most_active_users': sorted(user_message_counts.items(), key=lambda x: x[1], reverse=True)[:5],
                    'lurker_count': total_participants - len(user_message_counts)  # Users with 0 messages
                },
                'content_quality': {
                    'avg_message_length_words': round(avg_message_length, 1),
                    'max_thread_depth': max_thread_depth,
                    'avg_thread_depth': round(avg_thread_depth, 1),
                    'avg_sentiment_score': round(avg_sentiment, 3)  # -1 to 1, where 1 is most positive
                },
                'moderation': {
                    'flagged_messages': sum(1 for msg in messages if msg.is_flagged),
                    'deleted_messages': sum(1 for msg in messages if msg.is_deleted),
                    'flagged_percentage': round((sum(1 for msg in messages if msg.is_flagged) / max(len(messages), 1)) * 100, 1)
                }
            }
            
            # Store analytics in session metadata
            if not collab_session.session_metadata:
                collab_session.session_metadata = {}
            
            collab_session.session_metadata['analytics'] = analytics_data
            db.session.commit()
            
            logger.info(f"Generated discussion analytics for session {session_id}")
            
            return {"success": True, "analytics": analytics_data}
            
    except Exception as e:
        logger.error(f"Error generating discussion analytics: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def archive_inactive_discussions(self, days_inactive: int = 7):
    """
    Archive discussions that have been inactive for specified days
    """
    try:
        with db.app.app_context():
            cutoff_time = datetime.utcnow() - timedelta(days=days_inactive)
            
            # Find inactive group discussions
            inactive_sessions = db.session.query(CollaborationSession).filter(
                and_(
                    CollaborationSession.session_type == 'group_discussion',
                    CollaborationSession.is_active == True,
                    CollaborationSession.created_at < cutoff_time
                )
            ).all()
            
            archived_count = 0
            
            for session in inactive_sessions:
                # Check for recent activity
                recent_activity = db.session.query(CollaborationComment).filter(
                    and_(
                        CollaborationComment.session_id == session.id,
                        CollaborationComment.created_at >= cutoff_time
                    )
                ).first()
                
                if not recent_activity:
                    # Generate final analytics before archiving
                    analytics_task = generate_discussion_analytics.delay(session.id)
                    
                    # Archive the session
                    session.is_active = False
                    if not session.session_metadata:
                        session.session_metadata = {}
                    session.session_metadata['archived_at'] = datetime.utcnow().isoformat()
                    session.session_metadata['archived_reason'] = f'Inactive for {days_inactive} days'
                    
                    # Update participants status
                    participants = db.session.query(SessionParticipant).filter(
                        and_(
                            SessionParticipant.session_id == session.id,
                            SessionParticipant.status == 'joined'
                        )
                    ).all()
                    
                    for participant in participants:
                        participant.status = 'archived'
                        
                        notification = CollaborationNotification(
                            user_id=participant.user_id,
                            session_id=session.id,
                            notification_type='session_archived',
                            title='Discussion Archived',
                            message=f'The discussion "{session.title}" has been archived due to inactivity',
                            notification_metadata={
                                'archived_at': session.session_metadata['archived_at'],
                                'reason': session.session_metadata['archived_reason']
                            }
                        )
                        db.session.add(notification)
                    
                    archived_count += 1
            
            db.session.commit()
            
            logger.info(f"Archived {archived_count} inactive discussions")
            
            return {
                "success": True,
                "archived_count": archived_count,
                "days_inactive": days_inactive
            }
            
    except Exception as e:
        logger.error(f"Error archiving inactive discussions: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def cleanup_old_notifications(self, session_id: int = None, days_old: int = 30):
    """
    Clean up old notifications for discussion sessions
    """
    try:
        with db.app.app_context():
            cutoff_time = datetime.utcnow() - timedelta(days=days_old)
            
            # Build query for old notifications
            query = db.session.query(CollaborationNotification).filter(
                and_(
                    CollaborationNotification.created_at < cutoff_time,
                    CollaborationNotification.is_read == True
                )
            )
            
            if session_id:
                query = query.filter(CollaborationNotification.session_id == session_id)
            
            old_notifications = query.all()
            deleted_count = len(old_notifications)
            
            for notification in old_notifications:
                db.session.delete(notification)
            
            db.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old notifications" + 
                       (f" for session {session_id}" if session_id else ""))
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "days_old": days_old,
                "session_id": session_id
            }
            
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        self.retry(countdown=60, exc=e)

@celery.task(bind=True, max_retries=3)
def suggest_discussion_topics(self, session_id: int):
    """
    Suggest new discussion topics based on conversation patterns and learning objectives
    """
    try:
        with db.app.app_context():
            collab_session = db.session.query(CollaborationSession).filter(
                CollaborationSession.id == session_id
            ).first()
            
            if not collab_session:
                return {"success": False, "error": "Session not found"}
            
            # Analyze recent conversation topics
            recent_messages = db.session.query(CollaborationComment).filter(
                and_(
                    CollaborationComment.session_id == session_id,
                    CollaborationComment.comment_type == 'message',
                    CollaborationComment.created_at >= datetime.utcnow() - timedelta(hours=24),
                    CollaborationComment.parent_id == None  # Top-level messages only
                )
            ).all()
            
            # Extract keywords from recent topics
            topic_keywords = []
            for msg in recent_messages:
                words = [w.lower() for w in msg.content.split() 
                        if len(w) > 4 and w.isalpha()]
                topic_keywords.extend(words)
            
            # Simple topic suggestions based on learning context
            learning_path_suggestions = [
                "What are the key challenges in applying this concept?",
                "How does this relate to real-world scenarios?",
                "What examples can you share from your experience?",
                "What questions do you still have about this topic?",
                "How would you explain this to someone new?",
                "What are the implications of this concept?",
                "How does this connect to other topics we've discussed?",
                "What would you change or improve about this approach?"
            ]
            
            # Randomly select suggestions (could be enhanced with AI)
            selected_suggestions = random.sample(learning_path_suggestions, 
                                               min(3, len(learning_path_suggestions)))
            
            suggestions_data = {
                'session_id': session_id,
                'generated_at': datetime.utcnow().isoformat(),
                'suggested_topics': selected_suggestions,
                'based_on_keywords': list(set(topic_keywords))[:10],  # Top 10 unique keywords
                'message_count_analyzed': len(recent_messages)
            }
            
            # Store suggestions in session metadata
            if not collab_session.session_metadata:
                collab_session.session_metadata = {}
            
            collab_session.session_metadata['topic_suggestions'] = suggestions_data
            db.session.commit()
            
            # Notify facilitators about new suggestions
            facilitators = db.session.query(SessionParticipant).filter(
                and_(
                    SessionParticipant.session_id == session_id,
                    SessionParticipant.role == 'facilitator',
                    SessionParticipant.status == 'joined'
                )
            ).all()
            
            for facilitator in facilitators:
                notification = CollaborationNotification(
                    user_id=facilitator.user_id,
                    session_id=session_id,
                    notification_type='topic_suggestions',
                    title='New Discussion Topics Available',
                    message=f'AI has generated {len(selected_suggestions)} new topic suggestions for "{collab_session.title}"',
                    notification_metadata=suggestions_data
                )
                db.session.add(notification)
            
            db.session.commit()
            
            logger.info(f"Generated {len(selected_suggestions)} topic suggestions for session {session_id}")
            
            return {"success": True, "suggestions": suggestions_data}
            
    except Exception as e:
        logger.error(f"Error generating topic suggestions: {str(e)}")
        self.retry(countdown=60, exc=e)