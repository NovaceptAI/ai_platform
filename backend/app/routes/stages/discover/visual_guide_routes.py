from flask import Blueprint, request, jsonify, current_app
import os, tempfile
from app.services.stages.discover.visual_guide_service import VisualGuideService

# If you want vault usage for docs:
try:
    from app.routes.upload import download_blob_to_tmp
except Exception:
    download_blob_to_tmp = None

vsg_bp = Blueprint("study_guide", __name__)

@vsg_bp.route("/generate_visual_study_guide", methods=["POST"])
def generate_visual_study_guide():
    """
    Accepts:
      JSON:
        { "method": "category", "category": "..." }
        { "method": "text", "text": "..." }
        { "method": "document", "fromVault": true, "filename": "<blob name>" }
      Multipart (document):
        file=<uploaded file>, method=document
    Returns:
      { "summary": str, "topics":[{name, study_method, time?, order, resources?}, ...] }
    """
    svc = VisualGuideService()
    tmp_path = None

    try:
        # === Multipart (upload) ===
        if "file" in request.files:
            method = (request.form.get("method") or "document").lower()
            if method != "document":
                return jsonify({"error": "For file uploads, method must be 'document'."}), 400

            f = request.files["file"]
            if not f or f.filename == "":
                return jsonify({"error": "No file provided"}), 400

            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, f"vsg_{next(tempfile._get_candidate_names())}_{f.filename}")
            f.save(tmp_path)
            current_app.logger.info(f"[VSG] Uploaded file saved at {tmp_path}")

            out = svc.from_document(tmp_path)
            return jsonify(out), 200

        # === JSON payload ===
        if request.is_json or request.content_type.startswith("application/json"):
            data = request.get_json(force=True, silent=True) or {}
            method = (data.get("method") or "category").lower()

            if method == "category":
                category = (data.get("category") or "").strip()
                if not category:
                    return jsonify({"error": "Missing category"}), 400
                return jsonify(svc.from_category(category)), 200

            if method == "text":
                txt = (data.get("text") or "").strip()
                if not txt:
                    return jsonify({"error": "Missing text"}), 400
                return jsonify(svc.from_text(txt)), 200

            if method == "document":
                # Vault flow (like Summarizer)
                from_vault = bool(data.get("fromVault"))
                filename = (data.get("filename") or "").strip()
                if from_vault and filename:
                    if not download_blob_to_tmp:
                        return jsonify({"error": "Vault download not available on server"}), 500
                    tmp_path = download_blob_to_tmp(filename)
                    current_app.logger.info(f"[VSG] Vault file downloaded to: {tmp_path}")
                    return jsonify(svc.from_document(tmp_path)), 200

                return jsonify({"error": "Document method requires multipart upload OR fromVault+filename"}), 400

            return jsonify({"error": "Invalid method"}), 400

        # No multipart and not JSON
        return jsonify({"error": "No valid payload provided"}), 400

    except Exception as e:
        current_app.logger.exception("[VSG] generation failed")
        return jsonify({"error": str(e) or "Failed to generate visual study guide."}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                current_app.logger.info(f"[VSG] Temp file removed: {tmp_path}")
            except Exception:
                pass