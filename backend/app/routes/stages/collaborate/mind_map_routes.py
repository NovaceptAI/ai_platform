# app/routes/stages/collaborate/mind_map_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4
from app.db import db
from app.models.mind_maps import (
    MindMap, MindMapNode, MindMapConnection,
    MindMapCollaborator, MindMapComment, MindMapVersion
)
from app.models.users import Users
import logging

log = logging.getLogger(__name__)

mind_map_bp = Blueprint("mind_map", __name__)

def _get_user_id():
    return get_jwt_identity()

# =============================================================================
# MIND MAP CRUD
# =============================================================================

@mind_map_bp.route("/", methods=["POST"])
@jwt_required()
def create_mind_map():
    """Create a new mind map."""
    user_id = _get_user_id()
    data = request.get_json(force=True)

    title = data.get("title", "Untitled Mind Map")
    description = data.get("description")
    template_type = data.get("template_type")
    canvas_settings = data.get("canvas_settings", {})

    try:
        mind_map = MindMap(
            owner_id=user_id,
            title=title,
            description=description,
            template_type=template_type,
            canvas_settings=canvas_settings
        )
        db.session.add(mind_map)
        db.session.commit()

        return jsonify({
            "success": True,
            "mind_map_id": str(mind_map.id),
            "message": "Mind map created successfully"
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Create error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/", methods=["GET"])
@jwt_required()
def list_mind_maps():
    """List all mind maps user has access to."""
    user_id = _get_user_id()

    try:
        # Maps owned by user
        owned_maps = db.session.query(MindMap).filter_by(owner_id=user_id, status='active').all()

        # Maps where user is a collaborator
        collab_maps = db.session.query(MindMap).join(MindMapCollaborator).filter(
            MindMapCollaborator.user_id == user_id,
            MindMap.status == 'active'
        ).all()

        all_maps = list(set(owned_maps + collab_maps))

        maps_data = [{
            "id": str(m.id),
            "title": m.title,
            "description": m.description,
            "is_owner": str(m.owner_id) == user_id,
            "is_public": m.is_public,
            "node_count": len(m.nodes),
            "collaborator_count": len(m.collaborators),
            "updated_at": m.updated_at.isoformat() if m.updated_at else None
        } for m in all_maps]

        return jsonify({
            "success": True,
            "mind_maps": maps_data
        }), 200

    except Exception as e:
        log.error(f"[MindMap] List error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/public", methods=["GET"])
@jwt_required()
def list_public_mind_maps():
    """List all public mind maps for discovery."""
    try:
        # Get all public mind maps ordered by most recent
        public_maps = db.session.query(MindMap).filter_by(
            is_public=True,
            status='active'
        ).order_by(MindMap.updated_at.desc()).limit(50).all()

        maps_data = [{
            "id": str(m.id),
            "title": m.title,
            "description": m.description,
            "owner_name": m.owner.username if m.owner else "Unknown",
            "owner_id": str(m.owner_id),
            "node_count": len(m.nodes),
            "collaborator_count": len(m.collaborators),
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            "is_public": True
        } for m in public_maps]

        return jsonify({
            "success": True,
            "mind_maps": maps_data
        }), 200

    except Exception as e:
        log.error(f"[MindMap] List public error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>", methods=["GET"])
@jwt_required()
def get_mind_map(mind_map_id):
    """Get complete mind map data."""
    user_id = _get_user_id()

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        # Check access
        is_owner = str(mind_map.owner_id) == user_id
        collaborator = db.session.query(MindMapCollaborator).filter_by(
            mind_map_id=mind_map_id,
            user_id=user_id
        ).first()

        if not is_owner and not collaborator and not mind_map.is_public:
            return jsonify({"error": "Access denied"}), 403

        # Serialize nodes
        nodes_data = [{
            "id": str(node.id),
            "type": node.node_type,
            "content": node.content,
            "title": node.title,
            "position": {"x": node.position_x, "y": node.position_y},
            "size": {"width": node.width, "height": node.height},
            "style": {"color": node.color, "shape": node.shape, "icon": node.icon},
            "metadata": node.node_metadata or {},  # Fixed: use node_metadata from model
            "parent_id": str(node.parent_node_id) if node.parent_node_id else None,
            "created_by": str(node.created_by) if node.created_by else None
        } for node in mind_map.nodes]

        # Serialize connections
        connections_data = [{
            "id": str(conn.id),
            "source_id": str(conn.source_node_id),
            "target_id": str(conn.target_node_id),
            "style": {
                "line_type": conn.line_type,
                "line_color": conn.line_color,
                "arrow_direction": conn.arrow_direction
            },
            "label": conn.label
        } for conn in mind_map.connections]

        # Serialize collaborators
        collaborators_data = [{
            "id": str(collab.id),
            "user_id": str(collab.user_id),
            "username": collab.user.username if collab.user else "Unknown",
            "permission_level": collab.permission_level,
            "is_online": collab.is_online
        } for collab in mind_map.collaborators]

        return jsonify({
            "success": True,
            "mind_map": {
                "id": str(mind_map.id),
                "title": mind_map.title,
                "description": mind_map.description,
                "owner_id": str(mind_map.owner_id),
                "is_owner": is_owner,
                "canvas_settings": mind_map.canvas_settings or {},
                "template_type": mind_map.template_type,
                "nodes": nodes_data,
                "connections": connections_data,
                "collaborators": collaborators_data
            }
        }), 200

    except Exception as e:
        log.error(f"[MindMap] Get error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>", methods=["PUT"])
@jwt_required()
def update_mind_map(mind_map_id):
    """Update mind map metadata."""
    user_id = _get_user_id()
    data = request.get_json(force=True)

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        if str(mind_map.owner_id) != user_id:
            return jsonify({"error": "Only owner can update mind map settings"}), 403

        if "title" in data:
            mind_map.title = data["title"]
        if "description" in data:
            mind_map.description = data["description"]
        if "canvas_settings" in data:
            mind_map.canvas_settings = data["canvas_settings"]
        if "is_public" in data:
            mind_map.is_public = data["is_public"]

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Mind map updated"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Update error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>", methods=["DELETE"])
@jwt_required()
def delete_mind_map(mind_map_id):
    """Delete mind map."""
    user_id = _get_user_id()

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        if str(mind_map.owner_id) != user_id:
            return jsonify({"error": "Only owner can delete mind map"}), 403

        mind_map.status = 'deleted'
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Mind map deleted"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Delete error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# NODES
# =============================================================================

@mind_map_bp.route("/<uuid:mind_map_id>/nodes", methods=["POST"])
@jwt_required()
def create_node(mind_map_id):
    """Create a new node."""
    user_id = _get_user_id()
    data = request.get_json(force=True)

    try:
        node = MindMapNode(
            mind_map_id=mind_map_id,
            node_type=data.get("type", "text"),
            content=data.get("content"),
            title=data.get("title"),
            position_x=data.get("position_x", 0),
            position_y=data.get("position_y", 0),
            width=data.get("width", 200),
            height=data.get("height", 100),
            color=data.get("color", "#667eea"),
            shape=data.get("shape", "rectangle"),
            icon=data.get("icon"),
            metadata=data.get("metadata", {}),
            parent_node_id=data.get("parent_id"),
            created_by=user_id
        )
        db.session.add(node)
        db.session.commit()

        return jsonify({
            "success": True,
            "node": {
                "id": str(node.id),
                "type": node.node_type,
                "content": node.content,
                "position": {"x": node.position_x, "y": node.position_y}
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Create node error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/nodes/<uuid:node_id>", methods=["PUT"])
@jwt_required()
def update_node(mind_map_id, node_id):
    """Update a node."""
    data = request.get_json(force=True)

    try:
        node = db.session.query(MindMapNode).filter_by(id=node_id, mind_map_id=mind_map_id).first()
        if not node:
            return jsonify({"error": "Node not found"}), 404

        # Update fields
        if "content" in data:
            node.content = data["content"]
        if "title" in data:
            node.title = data["title"]
        if "position_x" in data:
            node.position_x = data["position_x"]
        if "position_y" in data:
            node.position_y = data["position_y"]
        if "width" in data:
            node.width = data["width"]
        if "height" in data:
            node.height = data["height"]
        if "color" in data:
            node.color = data["color"]
        if "shape" in data:
            node.shape = data["shape"]
        if "icon" in data:
            node.icon = data["icon"]
        if "metadata" in data:
            node.metadata = data["metadata"]

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Node updated"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Update node error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/nodes/<uuid:node_id>", methods=["DELETE"])
@jwt_required()
def delete_node(mind_map_id, node_id):
    """Delete a node."""
    try:
        node = db.session.query(MindMapNode).filter_by(id=node_id, mind_map_id=mind_map_id).first()
        if not node:
            return jsonify({"error": "Node not found"}), 404

        db.session.delete(node)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Node deleted"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Delete node error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# CONNECTIONS
# =============================================================================

@mind_map_bp.route("/<uuid:mind_map_id>/connections", methods=["POST"])
@jwt_required()
def create_connection(mind_map_id):
    """Create a connection between nodes."""
    data = request.get_json(force=True)

    try:
        connection = MindMapConnection(
            mind_map_id=mind_map_id,
            source_node_id=data["source_id"],
            target_node_id=data["target_id"],
            line_type=data.get("line_type", "curved"),
            line_color=data.get("line_color", "#9ca3af"),
            label=data.get("label"),
            arrow_direction=data.get("arrow_direction", "forward")
        )
        db.session.add(connection)
        db.session.commit()

        return jsonify({
            "success": True,
            "connection_id": str(connection.id)
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Create connection error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/connections/<uuid:connection_id>", methods=["DELETE"])
@jwt_required()
def delete_connection(mind_map_id, connection_id):
    """Delete a connection."""
    try:
        connection = db.session.query(MindMapConnection).filter_by(
            id=connection_id,
            mind_map_id=mind_map_id
        ).first()

        if not connection:
            return jsonify({"error": "Connection not found"}), 404

        db.session.delete(connection)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Connection deleted"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Delete connection error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# COLLABORATORS
# =============================================================================

@mind_map_bp.route("/<uuid:mind_map_id>/collaborators", methods=["GET"])
@jwt_required()
def get_collaborators(mind_map_id):
    """Get all collaborators for a mind map."""
    user_id = _get_user_id()

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        # Check access
        is_owner = str(mind_map.owner_id) == user_id
        is_public = mind_map.is_public
        is_collaborator = db.session.query(MindMapCollaborator).filter_by(
            mind_map_id=mind_map_id,
            user_id=user_id
        ).first() is not None

        if not (is_owner or is_public or is_collaborator):
            return jsonify({"error": "Access denied"}), 403

        collaborators = db.session.query(MindMapCollaborator).filter_by(
            mind_map_id=mind_map_id
        ).all()

        collaborators_data = []
        for collab in collaborators:
            user = db.session.query(Users).get(collab.user_id)
            collaborators_data.append({
                "id": str(collab.id),
                "user_id": str(collab.user_id),
                "username": user.username if user else "Unknown",
                "email": user.email if user else "",
                "permission_level": collab.permission_level,
                "joined_at": collab.joined_at.isoformat() if collab.joined_at else None,
                "is_online": False  # Will be updated by WebSocket active sessions
            })

        return jsonify({
            "success": True,
            "collaborators": collaborators_data
        }), 200

    except Exception as e:
        log.error(f"[MindMap] Get collaborators error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/collaborators", methods=["POST"])
@jwt_required()
def add_collaborator(mind_map_id):
    """Add a collaborator to the mind map."""
    user_id = _get_user_id()
    data = request.get_json(force=True)

    collaborator_user_id = data.get("user_id")
    permission_level = data.get("permission_level", "edit")

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        if str(mind_map.owner_id) != user_id:
            return jsonify({"error": "Only owner can add collaborators"}), 403

        # Check if already a collaborator
        existing = db.session.query(MindMapCollaborator).filter_by(
            mind_map_id=mind_map_id,
            user_id=collaborator_user_id
        ).first()

        if existing:
            return jsonify({"error": "User is already a collaborator"}), 400

        collaborator = MindMapCollaborator(
            mind_map_id=mind_map_id,
            user_id=collaborator_user_id,
            permission_level=permission_level,
            invited_by=user_id
        )
        db.session.add(collaborator)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Collaborator added"
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Add collaborator error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/collaborators/<uuid:collaborator_id>", methods=["DELETE"])
@jwt_required()
def remove_collaborator(mind_map_id, collaborator_id):
    """Remove a collaborator."""
    user_id = _get_user_id()

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        if str(mind_map.owner_id) != user_id:
            return jsonify({"error": "Only owner can remove collaborators"}), 403

        collaborator = db.session.query(MindMapCollaborator).get(collaborator_id)
        if not collaborator:
            return jsonify({"error": "Collaborator not found"}), 404

        db.session.delete(collaborator)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Collaborator removed"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Remove collaborator error: {e}")
        return jsonify({"error": str(e)}), 500

# =============================================================================
# COMMENTS
# =============================================================================

@mind_map_bp.route("/<uuid:mind_map_id>/comments", methods=["GET"])
@jwt_required()
def get_comments(mind_map_id):
    """Get all comments for a mind map."""
    user_id = _get_user_id()

    try:
        mind_map = db.session.query(MindMap).get(mind_map_id)
        if not mind_map:
            return jsonify({"error": "Mind map not found"}), 404

        # Check access
        is_owner = str(mind_map.owner_id) == user_id
        is_public = mind_map.is_public
        is_collaborator = db.session.query(MindMapCollaborator).filter_by(
            mind_map_id=mind_map_id,
            user_id=user_id
        ).first() is not None

        if not (is_owner or is_public or is_collaborator):
            return jsonify({"error": "Access denied"}), 403

        comments = db.session.query(MindMapComment).filter_by(
            mind_map_id=mind_map_id
        ).order_by(MindMapComment.created_at.desc()).all()

        comments_data = []
        for comment in comments:
            author = db.session.query(Users).get(comment.user_id)
            comments_data.append({
                "id": str(comment.id),
                "content": comment.content,
                "node_id": str(comment.node_id) if comment.node_id else None,
                "author_id": str(comment.user_id),
                "author_name": author.username if author else "Unknown",
                "created_at": comment.created_at.isoformat(),
                "is_resolved": comment.is_resolved,
                "parent_comment_id": str(comment.parent_comment_id) if comment.parent_comment_id else None
            })

        return jsonify({
            "success": True,
            "comments": comments_data
        }), 200

    except Exception as e:
        log.error(f"[MindMap] Get comments error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/comments", methods=["POST"])
@jwt_required()
def add_comment(mind_map_id):
    """Add a comment."""
    user_id = _get_user_id()
    data = request.get_json(force=True)

    try:
        comment = MindMapComment(
            mind_map_id=mind_map_id,
            node_id=data.get("node_id"),
            user_id=user_id,
            content=data["content"],
            parent_comment_id=data.get("parent_comment_id")
        )
        db.session.add(comment)
        db.session.commit()

        return jsonify({
            "success": True,
            "comment_id": str(comment.id)
        }), 201

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Add comment error: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_bp.route("/<uuid:mind_map_id>/comments/<uuid:comment_id>/resolve", methods=["POST"])
@jwt_required()
def resolve_comment(mind_map_id, comment_id):
    """Resolve a comment thread."""
    user_id = _get_user_id()

    try:
        comment = db.session.query(MindMapComment).filter_by(
            id=comment_id,
            mind_map_id=mind_map_id
        ).first()

        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        comment.is_resolved = True
        comment.resolved_by = user_id
        comment.resolved_at = db.func.now()
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment resolved"
        }), 200

    except Exception as e:
        db.session.rollback()
        log.error(f"[MindMap] Resolve comment error: {e}")
        return jsonify({"error": str(e)}), 500
