# app/routes/stages/master/science_lab_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
from app.db import db
from app.models.science_lab import ScienceLabExperiment
from app.services.stages.master.science_lab_service import ScienceLabService
import logging

log = logging.getLogger(__name__)

science_lab_bp = Blueprint("science_lab", __name__)

def _get_user_id():
    return get_jwt_identity()

# =============================================================================
# SIMULATION ENDPOINTS
# =============================================================================

@science_lab_bp.route("/simulate", methods=["POST"])
@jwt_required()
def run_simulation():
    """Run a science simulation and return results."""
    data = request.get_json(force=True)
    experiment_type = data.get("experiment_type")
    parameters = data.get("parameters", {})

    if not experiment_type:
        return jsonify({"error": "experiment_type required"}), 400

    service = ScienceLabService()

    try:
        # Route to appropriate simulation
        if experiment_type == "physics_pendulum":
            results = service.simulate_pendulum(parameters)
        elif experiment_type == "physics_projectile":
            results = service.simulate_projectile_motion(parameters)
        elif experiment_type == "physics_springs":
            results = service.simulate_springs(parameters)
        elif experiment_type == "chemistry_ph":
            results = service.simulate_ph_calculation(parameters)
        elif experiment_type == "chemistry_reaction":
            results = service.simulate_chemical_reaction(parameters)
        else:
            return jsonify({"error": f"Unknown experiment type: {experiment_type}"}), 400

        return jsonify({
            "success": True,
            "experiment_type": experiment_type,
            "parameters": parameters,
            "results": results
        }), 200

    except Exception as e:
        log.error(f"[ScienceLab] Simulation error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# AI TUTOR ENDPOINTS
# =============================================================================

@science_lab_bp.route("/hint", methods=["POST"])
@jwt_required()
def get_hint():
    """Get an AI-generated hint for the current experiment."""
    data = request.get_json(force=True)
    experiment_type = data.get("experiment_type")
    current_data = data.get("current_data", {})
    question = data.get("question")

    if not experiment_type:
        return jsonify({"error": "experiment_type required"}), 400

    service = ScienceLabService()

    try:
        hint = service.generate_hint(experiment_type, current_data, question)
        return jsonify({
            "success": True,
            "hint": hint
        }), 200
    except Exception as e:
        log.error(f"[ScienceLab] Hint generation error: {e}")
        return jsonify({"error": str(e)}), 500

@science_lab_bp.route("/feedback", methods=["POST"])
@jwt_required()
def get_feedback():
    """Get AI feedback on experiment results and conclusions."""
    data = request.get_json(force=True)
    experiment_type = data.get("experiment_type")
    trials = data.get("trials", [])
    observations = data.get("observations", "")
    conclusions = data.get("conclusions", "")

    if not experiment_type:
        return jsonify({"error": "experiment_type required"}), 400

    service = ScienceLabService()

    try:
        feedback = service.provide_feedback(experiment_type, trials, observations, conclusions)
        return jsonify({
            "success": True,
            "feedback": feedback
        }), 200
    except Exception as e:
        log.error(f"[ScienceLab] Feedback generation error: {e}")
        return jsonify({"error": str(e)}), 500

@science_lab_bp.route("/suggest-next", methods=["POST"])
@jwt_required()
def suggest_next():
    """Suggest the next experiment based on completed work."""
    data = request.get_json(force=True)
    completed_experiments = data.get("completed_experiments", [])
    subject = data.get("subject", "physics")

    service = ScienceLabService()

    try:
        suggestion = service.suggest_next_experiment(completed_experiments, subject)
        return jsonify({
            "success": True,
            "suggestion": suggestion
        }), 200
    except Exception as e:
        log.error(f"[ScienceLab] Suggestion error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# EXPERIMENT SAVE/LOAD ENDPOINTS
# =============================================================================

@science_lab_bp.route("/save", methods=["POST"])
@jwt_required()
def save_experiment():
    """Save an experiment to the database."""
    user_id = _get_user_id()
    data = request.get_json(force=True)

    experiment_id = data.get("experiment_id")
    experiment_type = data.get("experiment_type")
    experiment_title = data.get("experiment_title")
    subject = data.get("subject", "physics")
    initial_parameters = data.get("initial_parameters", {})
    trial_data = data.get("trial_data", [])
    observations = data.get("observations", "")
    conclusions = data.get("conclusions", "")
    status = data.get("status", "in_progress")

    if not experiment_type or not experiment_title:
        return jsonify({"error": "experiment_type and experiment_title required"}), 400

    try:
        if experiment_id:
            # Update existing experiment
            experiment = db.session.query(ScienceLabExperiment).filter_by(
                id=experiment_id,
                user_id=user_id
            ).first()

            if not experiment:
                return jsonify({"error": "Experiment not found"}), 404

            experiment.trial_data = trial_data
            experiment.observations = observations
            experiment.conclusions = conclusions
            experiment.status = status
        else:
            # Create new experiment
            experiment = ScienceLabExperiment(
                user_id=user_id,
                experiment_type=experiment_type,
                experiment_title=experiment_title,
                subject=subject,
                initial_parameters=initial_parameters,
                trial_data=trial_data,
                observations=observations,
                conclusions=conclusions,
                status=status
            )
            db.session.add(experiment)

        db.session.commit()

        return jsonify({
            "success": True,
            "experiment_id": str(experiment.id),
            "message": "Experiment saved successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[ScienceLab] Save error: {e}")
        return jsonify({"error": str(e)}), 500

@science_lab_bp.route("/experiments", methods=["GET"])
@jwt_required()
def list_experiments():
    """Get all experiments for the current user."""
    user_id = _get_user_id()

    try:
        experiments = db.session.query(ScienceLabExperiment).filter_by(
            user_id=user_id
        ).order_by(ScienceLabExperiment.updated_at.desc()).all()

        experiments_data = [{
            "id": str(exp.id),
            "experiment_type": exp.experiment_type,
            "experiment_title": exp.experiment_title,
            "subject": exp.subject,
            "status": exp.status,
            "trial_count": len(exp.trial_data) if exp.trial_data else 0,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "updated_at": exp.updated_at.isoformat() if exp.updated_at else None
        } for exp in experiments]

        return jsonify({
            "success": True,
            "experiments": experiments_data
        }), 200

    except Exception as e:
        log.error(f"[ScienceLab] List experiments error: {e}")
        return jsonify({"error": str(e)}), 500

@science_lab_bp.route("/experiments/<uuid:experiment_id>", methods=["GET"])
@jwt_required()
def get_experiment(experiment_id):
    """Get a specific experiment."""
    user_id = _get_user_id()

    try:
        experiment = db.session.query(ScienceLabExperiment).filter_by(
            id=experiment_id,
            user_id=user_id
        ).first()

        if not experiment:
            return jsonify({"error": "Experiment not found"}), 404

        return jsonify({
            "success": True,
            "experiment": {
                "id": str(experiment.id),
                "experiment_type": experiment.experiment_type,
                "experiment_title": experiment.experiment_title,
                "subject": experiment.subject,
                "initial_parameters": experiment.initial_parameters or {},
                "trial_data": experiment.trial_data or [],
                "observations": experiment.observations or "",
                "conclusions": experiment.conclusions or "",
                "ai_hints": experiment.ai_hints or [],
                "ai_feedback": experiment.ai_feedback or {},
                "status": experiment.status,
                "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
                "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None
            }
        }), 200

    except Exception as e:
        log.error(f"[ScienceLab] Get experiment error: {e}")
        return jsonify({"error": str(e)}), 500

@science_lab_bp.route("/experiments/<uuid:experiment_id>", methods=["DELETE"])
@jwt_required()
def delete_experiment(experiment_id):
    """Delete an experiment."""
    user_id = _get_user_id()

    try:
        experiment = db.session.query(ScienceLabExperiment).filter_by(
            id=experiment_id,
            user_id=user_id
        ).first()

        if not experiment:
            return jsonify({"error": "Experiment not found"}), 404

        db.session.delete(experiment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Experiment deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[ScienceLab] Delete experiment error: {e}")
        return jsonify({"error": str(e)}), 500
