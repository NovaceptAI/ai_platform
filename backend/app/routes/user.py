from flask import Blueprint, jsonify
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models.users import Users
from app.models.profiles import LearnerProfile, EducatorProfile, ProfessionalProfile, OrganizationProfile


user_bp = Blueprint('user', __name__)


@user_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    identity = get_jwt_identity()
    try:
        user_uuid = uuid.UUID(identity)
    except Exception:
        return jsonify({"error": "Invalid token identity"}), 401
    user = db.session.get(Users, user_uuid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile_summary = None
    if user.account_type == 'learner':
        lp = db.session.get(LearnerProfile, user.id)
        if lp:
            profile_summary = f"{lp.school}/{lp.class_name}"
    elif user.account_type == 'educator':
        ep = db.session.get(EducatorProfile, user.id)
        if ep and ep.subjects:
            profile_summary = f"{ep.school}/{ep.subjects[0]}"
    elif user.account_type == 'professional':
        pp = db.session.get(ProfessionalProfile, user.id)
        if pp:
            profile_summary = pp.job_title
    elif user.account_type == 'organization':
        op = db.session.get(OrganizationProfile, user.id)
        if op:
            profile_summary = op.org_name

    return jsonify({
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'account_type': user.account_type,
        'onboarding_status': user.onboarding_status,
        'profile_summary': profile_summary
    })

