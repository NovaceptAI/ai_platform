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


@onboarding_bp.route('/state', methods=['GET'])
@jwt_required()
def get_state():
    identity = get_jwt_identity()
    try:
        user_uuid = uuid.UUID(identity)
    except Exception:
        return jsonify({"error": "Invalid token identity"}), 401
    user = db.session.get(Users, user_uuid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    has_profile = False
    if user.account_type == 'learner':
        has_profile = db.session.get(LearnerProfile, user.id) is not None
    elif user.account_type == 'educator':
        has_profile = db.session.get(EducatorProfile, user.id) is not None
    elif user.account_type == 'professional':
        has_profile = db.session.get(ProfessionalProfile, user.id) is not None
    elif user.account_type == 'organization':
        has_profile = db.session.get(OrganizationProfile, user.id) is not None

    return jsonify({
        'account_type': user.account_type,
        'onboarding_status': user.onboarding_status,
        'has_profile': has_profile
    })


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
    if not validate_account_type(account_type):
        return jsonify({"error": "Invalid account_type"}), 400

    if account_type == 'organization':
        allow_override = os.getenv('ALLOW_ORG_SIGNUP', 'false').lower() == 'true'
        if not allow_override:
            org = db.session.get(OrganizationProfile, user.id)
            if not org or org.subscription_status != 'active':
                return jsonify({
                    'code': 'ORG_SUBSCRIPTION_REQUIRED',
                    'message': 'Organization signup requires active subscription'
                }), 402

    user.account_type = account_type
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "ok"})


@onboarding_bp.route('/profile', methods=['POST'])
@jwt_required()
def upsert_profile():
    identity = get_jwt_identity()
    try:
        user_uuid = uuid.UUID(identity)
    except Exception:
        return jsonify({"error": "Invalid token identity"}), 401
    user = db.session.get(Users, user_uuid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.account_type:
        return jsonify({"error": "Begin onboarding first"}), 400

    data = request.get_json() or {}
    try:
        normalized = validate_profile_payload(user.account_type, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if user.account_type == 'learner':
        prof = db.session.get(LearnerProfile, user.id) or LearnerProfile(user_id=user.id)
        prof.school = normalized['school']
        prof.class_name = normalized['class_name']
        prof.favorite_subjects = normalized['favorite_subjects']
        prof.hobbies = normalized['hobbies']
        prof.interests = normalized['interests']
        db.session.add(prof)
    elif user.account_type == 'educator':
        prof = db.session.get(EducatorProfile, user.id) or EducatorProfile(user_id=user.id)
        prof.school = normalized['school']
        prof.subjects = normalized['subjects']
        prof.classes_taught = normalized['classes_taught']
        prof.students_count = normalized['students_count']
        prof.years_experience = normalized['years_experience']
        prof.hobbies = normalized['hobbies']
        db.session.add(prof)
    elif user.account_type == 'professional':
        prof = db.session.get(ProfessionalProfile, user.id) or ProfessionalProfile(user_id=user.id)
        prof.sector = normalized['sector']
        prof.job_title = normalized['job_title']
        prof.designation = normalized['designation']
        prof.years_experience = normalized['years_experience']
        prof.skills = normalized['skills']
        prof.interests = normalized['interests']
        prof.hobbies = normalized['hobbies']
        db.session.add(prof)
    elif user.account_type == 'organization':
        prof = db.session.get(OrganizationProfile, user.id) or OrganizationProfile(user_id=user.id)
        prof.org_name = normalized['org_name']
        prof.contact_email = normalized['contact_email']
        prof.website = normalized.get('website')
        db.session.add(prof)

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
    })
