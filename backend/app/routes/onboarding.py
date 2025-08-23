import os
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models.users import Users
from app.models.profiles import (
    LearnerProfile, EducatorProfile, ProfessionalProfile, OrganizationProfile
)
from app.utils.validators import (
    validate_account_type, validate_profile_payload
)
 

onboarding_bp = Blueprint('onboarding', __name__)

def _has_profile(user):
    # Because user_id IS the primary key on each profile table,
    # db.session.get(Profile, user.id) is valid and efficient.
    if user.account_type == 'learner':
        return db.session.get(LearnerProfile, user.id) is not None
    if user.account_type == 'educator':
        return db.session.get(EducatorProfile, user.id) is not None
    if user.account_type == 'professional':
        return db.session.get(ProfessionalProfile, user.id) is not None
    if user.account_type == 'organization':
        return db.session.get(OrganizationProfile, user.id) is not None
    return False

@onboarding_bp.route('/state', methods=['GET'])
@jwt_required()
def get_state():
    identity = get_jwt_identity()
    try:
        uid = uuid.UUID(identity)
    except Exception:
        return jsonify({"error": "Invalid token identity"}), 401

    user = db.session.get(Users, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    has_profile = _has_profile(user)

    # Derive status and self-heal the column to avoid future loops
    new_status = 'completed' if has_profile else 'pending'
    if user.onboarding_status != new_status:
        user.onboarding_status = new_status
        db.session.commit()

    return jsonify({
        "account_type": user.account_type,
        "onboarding_status": user.onboarding_status,
        "has_profile": has_profile
    }), 200


@onboarding_bp.route('/begin', methods=['POST'])
@jwt_required()
def begin_onboarding():
    identity = get_jwt_identity()
    try:
        user_uuid = uuid.UUID(identity)
    except Exception:
        return jsonify({"error": "Invalid token identity"}), 401

    user = db.session.get(Users, user_uuid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    payload = request.get_json() or {}
    account_type = (payload.get('account_type') or '').strip().lower()

    # Validate account type using your existing validator
    if not validate_account_type(account_type):
        return jsonify({"error": "Invalid account_type"}), 400

    # Organization gating (subscription check) unless explicitly allowed via env
    if account_type == 'organization':
        allow_override = os.getenv('ALLOW_ORG_SIGNUP', 'false').lower() == 'true'
        if not allow_override:
            org = db.session.get(OrganizationProfile, user.id)
            if not org or getattr(org, 'subscription_status', 'none') != 'active':
                return jsonify({
                    'code': 'ORG_SUBSCRIPTION_REQUIRED',
                    'message': 'Organization signup requires active subscription'
                }), 402

    # Set/Reset onboarding state to pending at begin (idempotent)
    user.account_type = account_type
    user.onboarding_status = 'pending'
    db.session.add(user)
    db.session.commit()

    return jsonify({"ok": True}), 200


@onboarding_bp.route('/profile', methods=['POST'])
@jwt_required()
def submit_profile():
    identity = get_jwt_identity()
    try:
        uid = uuid.UUID(identity)
    except Exception:
        return jsonify({"error": "Invalid token identity"}), 401

    user = db.session.get(Users, uid)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not user.account_type:
        return jsonify({"error": "Begin onboarding first"}), 400

    payload = request.get_json() or {}

    # Normalize/validate per account type (raises ValueError on bad input)
    try:
        normalized = validate_profile_payload(user.account_type, payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        if user.account_type == 'learner':
            rec = db.session.get(LearnerProfile, user.id) or LearnerProfile(user_id=user.id)
            rec.school = normalized['school']
            rec.class_name = normalized['class_name']
            rec.favorite_subjects = normalized.get('favorite_subjects', [])
            rec.hobbies = normalized.get('hobbies', [])
            rec.interests = normalized.get('interests', [])
            rec.extras = normalized.get('extras')
            db.session.add(rec)

        elif user.account_type == 'educator':
            rec = db.session.get(EducatorProfile, user.id) or EducatorProfile(user_id=user.id)
            rec.school = normalized['school']
            rec.subjects = normalized.get('subjects', [])
            rec.classes_taught = normalized.get('classes_taught', [])
            rec.students_count = int(normalized.get('students_count', 0))
            rec.years_experience = int(normalized.get('years_experience', 0))
            rec.hobbies = normalized.get('hobbies', [])
            rec.extras = normalized.get('extras')
            db.session.add(rec)

        elif user.account_type == 'professional':
            rec = db.session.get(ProfessionalProfile, user.id) or ProfessionalProfile(user_id=user.id)
            rec.sector = normalized['sector']
            rec.job_title = normalized['job_title']
            rec.designation = normalized['designation']
            rec.years_experience = int(normalized.get('years_experience', 0))
            rec.skills = normalized.get('skills', [])
            rec.interests = normalized.get('interests', [])
            rec.hobbies = normalized.get('hobbies', [])
            rec.extras = normalized.get('extras')
            db.session.add(rec)

        elif user.account_type == 'organization':
            rec = db.session.get(OrganizationProfile, user.id) or OrganizationProfile(user_id=user.id)
            rec.org_name = normalized['org_name']
            rec.contact_email = normalized['contact_email']
            rec.website = normalized.get('website')
            rec.admin_tier = normalized.get('admin_tier')
            rec.subscription_status = normalized.get('subscription_status', getattr(rec, 'subscription_status', 'none'))
            db.session.add(rec)

        # Flip status to completed (idempotent)
        user.onboarding_status = 'complete'
        db.session.add(user)
        db.session.commit()

        return jsonify({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'account_type': user.account_type,
            'onboarding_status': user.onboarding_status
        }), 200

    except KeyError as e:
        db.session.rollback()
        return jsonify({"error": f"Missing field: {e}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
