# app/models/mind_maps.py
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import db

class MindMap(db.Model):
    """Collaborative mind map - main container."""
    __tablename__ = 'mind_maps'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Owner and permissions
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False)

    # Canvas settings
    canvas_settings = db.Column(JSONB, nullable=True)  # {zoom, center_x, center_y, background_color}
    template_type = db.Column(db.String(50), nullable=True)  # brainstorm, swot, timeline, fishbone, etc.

    # Metadata
    status = db.Column(db.String(20), default='active')  # active, archived, deleted
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = db.relationship('Users', lazy='joined')
    nodes = db.relationship('MindMapNode', back_populates='mind_map', cascade='all, delete-orphan')
    connections = db.relationship('MindMapConnection', back_populates='mind_map', cascade='all, delete-orphan')
    collaborators = db.relationship('MindMapCollaborator', back_populates='mind_map', cascade='all, delete-orphan')
    comments = db.relationship('MindMapComment', back_populates='mind_map', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<MindMap(id={self.id}, title={self.title})>"


class MindMapNode(db.Model):
    """Individual nodes (ideas) in the mind map."""
    __tablename__ = 'mind_map_nodes'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mind_map_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_maps.id', ondelete='CASCADE'), nullable=False, index=True)

    # Node content
    node_type = db.Column(db.String(50), default='text')  # text, image, document, ai_summary, topic
    content = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(500), nullable=True)

    # Visual properties
    position_x = db.Column(db.Float, default=0)
    position_y = db.Column(db.Float, default=0)
    width = db.Column(db.Float, default=200)
    height = db.Column(db.Float, default=100)
    color = db.Column(db.String(20), default='#667eea')
    shape = db.Column(db.String(20), default='rectangle')  # rectangle, circle, bubble, diamond
    icon = db.Column(db.String(50), nullable=True)

    # Additional data
    node_metadata = db.Column(JSONB, nullable=True)  # images, attachments, links, etc.
    parent_node_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_map_nodes.id', ondelete='SET NULL'), nullable=True)

    # Tracking
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    mind_map = db.relationship('MindMap', back_populates='nodes')
    creator = db.relationship('Users', lazy='joined')
    children = db.relationship('MindMapNode', backref=db.backref('parent', remote_side=[id]))

    def __repr__(self):
        return f"<MindMapNode(id={self.id}, type={self.node_type})>"


class MindMapConnection(db.Model):
    """Connections/edges between nodes."""
    __tablename__ = 'mind_map_connections'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mind_map_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_maps.id', ondelete='CASCADE'), nullable=False, index=True)

    # Connection endpoints
    source_node_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_map_nodes.id', ondelete='CASCADE'), nullable=False)
    target_node_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_map_nodes.id', ondelete='CASCADE'), nullable=False)

    # Visual properties
    line_type = db.Column(db.String(20), default='curved')  # straight, curved, dotted, dashed
    line_color = db.Column(db.String(20), default='#9ca3af')
    label = db.Column(db.String(100), nullable=True)  # e.g., "causes", "supports", "contradicts"
    arrow_direction = db.Column(db.String(20), default='forward')  # forward, backward, both, none

    # Metadata
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mind_map = db.relationship('MindMap', back_populates='connections')
    source_node = db.relationship('MindMapNode', foreign_keys=[source_node_id])
    target_node = db.relationship('MindMapNode', foreign_keys=[target_node_id])

    def __repr__(self):
        return f"<MindMapConnection(source={self.source_node_id}, target={self.target_node_id})>"


class MindMapCollaborator(db.Model):
    """Collaborators with specific permissions."""
    __tablename__ = 'mind_map_collaborators'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mind_map_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_maps.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Permissions
    permission_level = db.Column(db.String(20), default='edit')  # view, comment, edit, admin

    # Presence tracking
    is_online = db.Column(db.Boolean, default=False)
    last_active_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cursor_position = db.Column(JSONB, nullable=True)  # {x, y, node_id}

    # Metadata
    invited_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    invited_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    mind_map = db.relationship('MindMap', back_populates='collaborators')
    user = db.relationship('Users', foreign_keys=[user_id], lazy='joined')
    inviter = db.relationship('Users', foreign_keys=[invited_by])

    def __repr__(self):
        return f"<MindMapCollaborator(user={self.user_id}, permission={self.permission_level})>"


class MindMapComment(db.Model):
    """Comments on nodes or general mind map."""
    __tablename__ = 'mind_map_comments'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mind_map_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_maps.id', ondelete='CASCADE'), nullable=False, index=True)
    node_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_map_nodes.id', ondelete='CASCADE'), nullable=True)  # null = general comment

    # Comment content
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # Threading
    parent_comment_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_map_comments.id', ondelete='CASCADE'), nullable=True)

    # Status
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    mind_map = db.relationship('MindMap', back_populates='comments')
    node = db.relationship('MindMapNode')
    user = db.relationship('Users', foreign_keys=[user_id], lazy='joined')
    resolver = db.relationship('Users', foreign_keys=[resolved_by])
    replies = db.relationship('MindMapComment', backref=db.backref('parent_comment', remote_side=[id]))

    def __repr__(self):
        return f"<MindMapComment(id={self.id}, user={self.user_id})>"


class MindMapVersion(db.Model):
    """Version history for undo/redo and restore."""
    __tablename__ = 'mind_map_versions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mind_map_id = db.Column(UUID(as_uuid=True), db.ForeignKey('mind_maps.id', ondelete='CASCADE'), nullable=False, index=True)

    # Version snapshot
    version_number = db.Column(db.Integer, nullable=False)
    snapshot_data = db.Column(JSONB, nullable=False)  # Complete state of nodes, connections, etc.

    # Change metadata
    changed_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    change_description = db.Column(db.String(255), nullable=True)

    # Timestamp
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mind_map = db.relationship('MindMap')
    user = db.relationship('Users', lazy='joined')

    def __repr__(self):
        return f"<MindMapVersion(map={self.mind_map_id}, version={self.version_number})>"
