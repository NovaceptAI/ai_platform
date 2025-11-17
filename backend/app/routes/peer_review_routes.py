"""
Peer Review Routes for Collaborate Stage
Handles REST API endpoints for peer review workflows and submissions
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.peer_review_service import PeerReviewService
from app.tasks.peer_review_tasks import (
    send_deadline_reminders,
    auto_assign_reviews,
    generate_review_analytics,
    close_review_session,
    send_review_quality_feedback
)

logger = logging.getLogger(__name__)

# Create blueprint for peer review routes
peer_review_bp = Blueprint('peer_review', __name__, url_prefix='/api/collaborate/peer-review')

# REST API Endpoints

@peer_review_bp.route('/create', methods=['POST'])
@jwt_required()
def create_review_session():
    """Create a new peer review session"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['learning_path_id', 'title']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate deadline format if provided
        if 'deadline' in data and data['deadline']:
            try:
                datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "Invalid deadline format. Use ISO format"}), 400
        
        # Add creator_id to data
        data['creator_id'] = user_id
        
        result = PeerReviewService.create_review_session(data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating review session: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/submit', methods=['POST'])
@jwt_required()
def submit_work(session_id):
    """Submit work for peer review"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({"error": "Submission content is required"}), 400
        
        if len(data['content'].strip()) == 0:
            return jsonify({"error": "Submission cannot be empty"}), 400
        
        if len(data['content']) > 50000:  # 50KB limit
            return jsonify({"error": "Submission too long (max 50,000 characters)"}), 400
        
        submission_data = {
            'session_id': session_id,
            'user_id': user_id,
            'title': data.get('title', '').strip(),
            'content': data['content'].strip(),
            'format': data.get('format', 'text'),
            'file_urls': data.get('file_urls', []),
            'notes': data.get('notes', '').strip()
        }
        
        result = PeerReviewService.submit_work_for_review(submission_data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error submitting work: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/assign', methods=['POST'])
@jwt_required()
def assign_reviews(session_id):
    """Manually assign reviews (facilitator only)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        strategy = data.get('strategy', 'random')
        valid_strategies = ['random', 'balanced', 'expertise_matching']
        
        if strategy not in valid_strategies:
            return jsonify({"error": f"Invalid strategy. Must be one of: {valid_strategies}"}), 400
        
        result = PeerReviewService.assign_reviews(session_id, user_id, strategy)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error assigning reviews: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/auto-assign', methods=['POST'])
@jwt_required()
def trigger_auto_assignment(session_id):
    """Trigger automatic review assignment"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        strategy = data.get('strategy', 'balanced')
        valid_strategies = ['balanced', 'random', 'expertise_matching']
        
        if strategy not in valid_strategies:
            return jsonify({"error": f"Invalid strategy. Must be one of: {valid_strategies}"}), 400
        
        # TODO: Add permission check - only facilitators should trigger auto-assignment
        
        # Trigger auto-assignment asynchronously
        task = auto_assign_reviews.delay(session_id, strategy)
        
        return jsonify({
            "success": True,
            "message": f"Auto-assignment started with {strategy} strategy",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error triggering auto-assignment: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/assignments', methods=['GET'])
@jwt_required()
def get_assignments(session_id):
    """Get review assignments for the current user"""
    try:
        user_id = get_jwt_identity()
        
        result = PeerReviewService.get_review_assignments(session_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error getting assignments: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/submit-review', methods=['POST'])
@jwt_required()
def submit_review(session_id):
    """Submit a peer review"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        required_fields = ['submission_id', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        if len(data['content'].strip()) == 0:
            return jsonify({"error": "Review content cannot be empty"}), 400
        
        if len(data['content']) > 10000:  # 10KB limit for reviews
            return jsonify({"error": "Review too long (max 10,000 characters)"}), 400
        
        # Validate rating if provided
        if 'rating' in data and data['rating'] is not None:
            try:
                rating = float(data['rating'])
                if not 1 <= rating <= 5:
                    return jsonify({"error": "Rating must be between 1 and 5"}), 400
                data['rating'] = rating
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid rating format"}), 400
        
        review_data = {
            'session_id': session_id,
            'reviewer_id': user_id,
            'submission_id': data['submission_id'],
            'content': data['content'].strip(),
            'rating': data.get('rating'),
            'rubric_scores': data.get('rubric_scores', {}),
            'strengths': data.get('strengths', '').strip(),
            'improvements': data.get('improvements', '').strip(),
            'review_time_minutes': data.get('review_time_minutes')
        }
        
        result = PeerReviewService.submit_review(review_data)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error submitting review: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/reviews-received', methods=['GET'])
@jwt_required()
def get_reviews_received(session_id):
    """Get reviews received for user's submissions"""
    try:
        user_id = get_jwt_identity()
        
        result = PeerReviewService.get_reviews_received(session_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error getting reviews received: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/overview', methods=['GET'])
@jwt_required()
def get_session_overview(session_id):
    """Get overview of a review session"""
    try:
        user_id = get_jwt_identity()
        
        result = PeerReviewService.get_review_session_overview(session_id, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 403
            
    except Exception as e:
        logger.error(f"Error getting session overview: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/analytics', methods=['GET'])
@jwt_required()
def get_session_analytics(session_id):
    """Get analytics for a review session (facilitator only)"""
    try:
        user_id = get_jwt_identity()
        
        # TODO: Add permission check - only facilitators should access analytics
        
        # Generate analytics asynchronously
        task = generate_review_analytics.delay(session_id)
        
        return jsonify({
            "success": True,
            "message": "Generating review session analytics",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error getting session analytics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/reminders', methods=['POST'])
@jwt_required()
def send_reminders(session_id):
    """Send deadline reminders to participants"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        hours_before = data.get('hours_before', 24)
        
        # Validate hours_before
        if not isinstance(hours_before, (int, float)) or hours_before <= 0:
            return jsonify({"error": "hours_before must be a positive number"}), 400
        
        hours_before = min(hours_before, 168)  # Max 1 week
        
        # TODO: Add permission check - only facilitators should send reminders
        
        # Send reminders asynchronously
        task = send_deadline_reminders.delay(session_id, int(hours_before))
        
        return jsonify({
            "success": True,
            "message": f"Sending deadline reminders for {hours_before} hours before deadline",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error sending reminders: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/close', methods=['POST'])
@jwt_required()
def close_session(session_id):
    """Close a review session (facilitator only)"""
    try:
        user_id = get_jwt_identity()
        
        # TODO: Add permission check - only facilitators should close sessions
        
        # Close session asynchronously
        task = close_review_session.delay(session_id)
        
        return jsonify({
            "success": True,
            "message": "Closing review session and generating final reports",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error closing session: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/<int:session_id>/feedback', methods=['POST'])
@jwt_required()
def send_quality_feedback(session_id):
    """Send review quality feedback to participants"""
    try:
        user_id = get_jwt_identity()
        
        # TODO: Add permission check - only facilitators should send feedback
        
        # Send feedback asynchronously
        task = send_review_quality_feedback.delay(session_id)
        
        return jsonify({
            "success": True,
            "message": "Sending review quality feedback to participants",
            "task_id": task.id
        }), 202
        
    except Exception as e:
        logger.error(f"Error sending quality feedback: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/active', methods=['GET'])
@jwt_required()
def get_active_sessions():
    """Get active peer review sessions for the current user"""
    try:
        user_id = get_jwt_identity()
        learning_path_id = request.args.get('learning_path_id', type=int)
        
        # TODO: Implement method in PeerReviewService to get active sessions
        # For now, return a placeholder response
        
        return jsonify({
            "success": True,
            "sessions": [],  # TODO: Implement actual session retrieval
            "message": "Active sessions retrieval not yet implemented"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@peer_review_bp.route('/rubrics/templates', methods=['GET'])
@jwt_required()
def get_rubric_templates():
    """Get available rubric templates for peer review"""
    try:
        # Default rubric templates
        templates = {
            "academic_essay": {
                "name": "Academic Essay Rubric",
                "categories": {
                    "content_quality": {
                        "name": "Content Quality",
                        "description": "Depth and accuracy of content",
                        "weight": 0.3,
                        "levels": {
                            1: "Poor content, inaccurate information",
                            2: "Basic content, some inaccuracies",
                            3: "Good content, mostly accurate",
                            4: "Excellent content, accurate and insightful",
                            5: "Outstanding content, exceptional insights"
                        }
                    },
                    "organization": {
                        "name": "Organization & Structure",
                        "description": "Logical flow and structure",
                        "weight": 0.25,
                        "levels": {
                            1: "Poor organization, confusing structure",
                            2: "Basic organization, some unclear sections",
                            3: "Good organization, clear structure",
                            4: "Excellent organization, logical flow",
                            5: "Outstanding organization, masterful structure"
                        }
                    },
                    "writing_quality": {
                        "name": "Writing Quality",
                        "description": "Grammar, style, and clarity",
                        "weight": 0.25,
                        "levels": {
                            1: "Poor writing, many errors",
                            2: "Basic writing, some errors",
                            3: "Good writing, few errors",
                            4: "Excellent writing, clear and engaging",
                            5: "Outstanding writing, exceptional clarity"
                        }
                    },
                    "sources_citations": {
                        "name": "Sources & Citations",
                        "description": "Use and citation of sources",
                        "weight": 0.2,
                        "levels": {
                            1: "No or poor use of sources",
                            2: "Basic use of sources, citation errors",
                            3: "Good use of sources, proper citations",
                            4: "Excellent use of diverse sources",
                            5: "Outstanding scholarly sources and citations"
                        }
                    }
                }
            },
            "presentation": {
                "name": "Presentation Rubric",
                "categories": {
                    "content": {
                        "name": "Content",
                        "description": "Accuracy and depth of information",
                        "weight": 0.4,
                        "levels": {
                            1: "Inaccurate or insufficient content",
                            2: "Basic content with some gaps",
                            3: "Good content, well-researched",
                            4: "Excellent content, comprehensive",
                            5: "Outstanding content, expert-level"
                        }
                    },
                    "delivery": {
                        "name": "Delivery",
                        "description": "Speaking skills and presentation style",
                        "weight": 0.3,
                        "levels": {
                            1: "Poor delivery, hard to follow",
                            2: "Basic delivery, some unclear moments",
                            3: "Good delivery, clear and engaging",
                            4: "Excellent delivery, confident and polished",
                            5: "Outstanding delivery, masterful presentation"
                        }
                    },
                    "visual_aids": {
                        "name": "Visual Aids",
                        "description": "Quality and effectiveness of visuals",
                        "weight": 0.2,
                        "levels": {
                            1: "Poor or no visual aids",
                            2: "Basic visual aids, minimal impact",
                            3: "Good visual aids, support content",
                            4: "Excellent visual aids, enhance presentation",
                            5: "Outstanding visual aids, masterfully integrated"
                        }
                    },
                    "time_management": {
                        "name": "Time Management",
                        "description": "Appropriate use of allotted time",
                        "weight": 0.1,
                        "levels": {
                            1: "Poor time management",
                            2: "Somewhat over/under time",
                            3: "Good time management",
                            4: "Excellent time management",
                            5: "Perfect time management"
                        }
                    }
                }
            },
            "creative_project": {
                "name": "Creative Project Rubric",
                "categories": {
                    "creativity": {
                        "name": "Creativity & Originality",
                        "description": "Innovation and unique approach",
                        "weight": 0.35,
                        "levels": {
                            1: "Little to no creativity",
                            2: "Some creative elements",
                            3: "Good creativity, some original ideas",
                            4: "High creativity, many original ideas",
                            5: "Exceptional creativity, highly original"
                        }
                    },
                    "technical_skill": {
                        "name": "Technical Skill",
                        "description": "Execution and craftsmanship",
                        "weight": 0.3,
                        "levels": {
                            1: "Poor technical execution",
                            2: "Basic technical skills shown",
                            3: "Good technical execution",
                            4: "Excellent technical skills",
                            5: "Master-level technical execution"
                        }
                    },
                    "concept_development": {
                        "name": "Concept Development",
                        "description": "Depth of idea development",
                        "weight": 0.25,
                        "levels": {
                            1: "Underdeveloped concept",
                            2: "Basic concept development",
                            3: "Well-developed concept",
                            4: "Thoroughly developed concept",
                            5: "Exceptionally developed concept"
                        }
                    },
                    "presentation": {
                        "name": "Presentation Quality",
                        "description": "How well the project is presented",
                        "weight": 0.1,
                        "levels": {
                            1: "Poor presentation quality",
                            2: "Basic presentation",
                            3: "Good presentation",
                            4: "Excellent presentation",
                            5: "Outstanding presentation"
                        }
                    }
                }
            }
        }
        
        return jsonify({
            "success": True,
            "templates": templates
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting rubric templates: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Export the blueprint
__all__ = ['peer_review_bp']
