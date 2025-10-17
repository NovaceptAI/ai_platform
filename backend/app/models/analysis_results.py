# app/models/analysis_results.py
from __future__ import annotations
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableDict  # optional but nice for in-place JSON edits
from sqlalchemy.orm import declared_attr, declarative_mixin

from app.db import db

@declarative_mixin
class _ResultBase:
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # IMPORTANT: matches UploadedFile.id (UUID) and cascades on delete
    file_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    method = db.Column(db.String(32))        # e.g., "semantic", "tfidf", "openai"
    model_version = db.Column(db.String(64)) # e.g., "gpt-4.1-2025-06-15"

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now(), nullable=False)

    # Use MutableDict so in-place JSON changes get tracked (optional but recommended)
    meta = db.Column(MutableDict.as_mutable(JSONB), default=dict)

    # ✅ relationships on mixins must use declared_attr
    @declared_attr
    def file(cls):
        return db.relationship("UploadedFile", lazy="joined")


# --------------------------------------------------------------------
# 1) Sentiment (per-file aggregate + per-page map)
# --------------------------------------------------------------------
class SentimentResult(db.Model, _ResultBase):
    __tablename__ = "sentiments"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_sentiments_file_version"),
    )

    # overall
    overall_label = db.Column(db.String(16))   # e.g., "positive" | "neutral" | "negative"
    overall_score = db.Column(db.Float)        # -1..1 or 0..1 depending on method

    # richer payloads
    emotion_scores = db.Column(JSONB)          # {"joy":0.71,"anger":0.03,...}
    page_sentiments = db.Column(JSONB)         # { "1": {"label":"pos","score":0.82}, "2": {...} }


# --------------------------------------------------------------------
# 2) Topics (LDA/NMF/LLM-topic labels)
# --------------------------------------------------------------------
class TopicModelResult(db.Model, _ResultBase):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_topics_file_version"),
    )

    num_topics = db.Column(db.Integer)
    coherence = db.Column(db.Float)            # topic coherence metric if available

    # list of topics with weights/keywords; keep it compact
    topics = db.Column(JSONB)                  # [{"label":"NLP","weight":0.22,"keywords":["token","bert","seq2seq"]}, ...]
    page_topics = db.Column(JSONB)             # { "1":[{"label":"NLP","weight":0.7}], "2":[...] }
    topic_graph = db.Column(JSONB)             # optional: {"nodes":[...], "edges":[...]}


# --------------------------------------------------------------------
# 3) Segments (logical sections across pages)
# --------------------------------------------------------------------
class SegmentResult(db.Model, _ResultBase):
    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_segments_file_version"),
    )

    num_segments = db.Column(db.Integer)

    # each segment: id, title, summary, page_start/end, tags/entities, optional children
    segments = db.Column(JSONB)                # [{"id":"s1","title":"Methods","summary":"...","page_start":3,"page_end":8,"tags":["methods"],"entities":["OpenAI"]}, ...]


# --------------------------------------------------------------------
# 4) Chronology (events timeline)
# --------------------------------------------------------------------
class ChronologyResult(db.Model, _ResultBase):
    __tablename__ = "chronologies"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_chronologies_file_version"),
    )

    # optional timeline bounds & quality metrics
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    coverage_ratio = db.Column(db.Float)       # 0..1 coverage of temporal refs across doc
    granularity = db.Column(db.String(16))     # "year" | "month" | "day" | "mixed"

    # events: iso_date or temporal expression, title, desc, page, entities, confidence
    events = db.Column(JSONB)                  # [{"when":"2021-06-10","title":"Launch","desc":"...","page":12,"entities":["CompanyX"],"confidence":0.93}, ...]


# --------------------------------------------------------------------
# 5) Document Analysis (holistic stats, outline, quality)
# --------------------------------------------------------------------
class DocumentAnalysisResult(db.Model, _ResultBase):
    __tablename__ = "document_analysis"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_document_analysis_file_version"),
    )

    # quick stats & diagnostics
    stats = db.Column(JSONB)                   # {"pages":124,"tokens":58219,"language":"en","reading_time_min":84}
    readability = db.Column(JSONB)             # {"flesch":58.2,"dale_chall":8.7}
    quality_scores = db.Column(JSONB)          # {"cohesion":0.74,"coverage":0.81,"redundancy":0.12}

    # structural & insight payloads
    outline = db.Column(JSONB)                 # [{"level":1,"title":"Introduction","page":1},{"level":2,"title":"Background","page":2}, ...]
    key_points = db.Column(JSONB)              # [{"text":"X is Y","page":7,"evidence":["..."]}, ...]
    risks = db.Column(JSONB)                   # [{"type":"assumption","text":"...","severity":"med"}]
    recommendations = db.Column(JSONB)         # [{"text":"Run an A/B study","priority":"high"}]
    
    # additional metadata (including entities_by_type)
    meta = db.Column(JSONB, default=dict)      # {"entities_by_type": {...}, "other_metadata": {...}}


# --------------------------------------------------------------------
# 6) Evidence Extraction (quotes, facts, supporting statements)
# --------------------------------------------------------------------
class EvidenceExtractionResult(db.Model, _ResultBase):
    __tablename__ = "evidence_extractions"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_evidence_extractions_file_version"),
    )

    # per-page evidence findings
    evidence_by_page = db.Column(JSONB)        # [{"page":1,"evidence":[{"type":"quote","text":"...","confidence":0.9,"context":"..."}]}, ...]
    
    # aggregated evidence across document
    aggregated_evidence = db.Column(JSONB)     # {"quotes":[...],"facts":[...],"arguments":[...],"statistics":[...],"themes":[...]}
    
    # summary and insights
    summary = db.Column(JSONB)                 # {"total_evidence":45,"strongest_themes":["AI","performance"],"confidence_avg":0.82}


# --------------------------------------------------------------------
# 7) Comparison (multi-document similarities, differences, relationships)
# --------------------------------------------------------------------
class ComparisonResult(db.Model, _ResultBase):
    __tablename__ = "comparisons"
    __table_args__ = (
        # For multi-file comparisons, we need a different unique constraint
        # Using comparison_key which is a sorted string of file_ids
        UniqueConstraint("comparison_key", "version", name="uq_comparisons_key_version"),
    )

    # Override file_id constraint since this is multi-file
    comparison_key = db.Column(db.String(255), nullable=False, index=True)  # "file1_id_file2_id_file3_id"
    
    # comparison results
    similarities = db.Column(JSONB)            # {"themes":["AI","tech"],"overlap_ratio":0.73,"shared_concepts":[...]}
    differences = db.Column(JSONB)             # {"unique_to_file1":[...],"unique_to_file2":[...],"contrasting_viewpoints":[...]}
    relationships = db.Column(JSONB)           # {"temporal_sequence":[...],"causal_links":[...],"contradictions":[...]}
    synthesis = db.Column(JSONB)               # {"combined_narrative":"...","key_insights":[...],"resolution_points":[...]}


# ============================================================================
# ORGANIZE STAGE MODELS - For Deep Reading Learning Path Organization Tools
# ============================================================================

# --------------------------------------------------------------------
# 8) Collections (Intelligent Document Organization)
# --------------------------------------------------------------------
class CollectionsResult(db.Model, _ResultBase):
    __tablename__ = "collections"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_collections_file_version"),
    )

    # collection metadata
    total_collections = db.Column(db.Integer, default=0)
    
    # individual collections with file assignments
    collections = db.Column(JSONB)             # [{"id":"c1","name":"Research Papers","description":"...","file_details":[...],"theme_analysis":{...}}, ...]
    
    # thematic analysis across collections
    theme_analysis = db.Column(JSONB)          # {"extracted_themes":["AI","research"],"theme_relationships":{...},"quality_scores":{...}}
    
    # organization insights
    organization_insights = db.Column(JSONB)   # {"organization_quality":0.85,"coverage_analysis":{...},"recommendations":[...]}


# --------------------------------------------------------------------
# 9) Tag Taxonomy (Hierarchical Tagging System)
# --------------------------------------------------------------------
class TagTaxonomyResult(db.Model, _ResultBase):
    __tablename__ = "tag_taxonomies"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_tag_taxonomies_file_version"),
    )

    # taxonomy metadata
    total_tags = db.Column(db.Integer, default=0)
    taxonomy_depth = db.Column(db.Integer, default=0)
    
    # hierarchical tag structure
    tags = db.Column(JSONB)                    # [{"id":"t1","name":"Technology","level":1,"parent_id":null,"children":["t2","t3"]}, ...]
    hierarchy = db.Column(JSONB)               # {"root_categories":[...],"parent_child_map":{...},"depth_map":{...}}
    
    # semantic relationships between tags
    relationships = db.Column(JSONB)           # {"semantic_clusters":[...],"tag_similarities":{...},"cross_references":{...}}
    
    # automated tagging rules and applications
    tagging_rules = db.Column(JSONB)           # [{"rule_id":"r1","pattern":"...","target_tags":["t1","t2"],"confidence":0.9}, ...]
    file_tag_assignments = db.Column(JSONB)    # {"file_assignments":[...],"confidence_scores":{...},"rule_applications":{...}}


# --------------------------------------------------------------------
# 10) Document Clusters (ML-based Content Grouping)
# --------------------------------------------------------------------
class DocumentClustersResult(db.Model, _ResultBase):
    __tablename__ = "document_clusters"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_document_clusters_file_version"),
    )

    # clustering metadata
    total_clusters = db.Column(db.Integer, default=0)
    algorithm_used = db.Column(db.String(64))  # "kmeans", "hierarchical", "dbscan", etc.
    
    # cluster definitions and file assignments
    clusters = db.Column(JSONB)                # [{"cluster_id":"cl1","name":"...","file_details":[...],"characteristics":{...}}, ...]
    
    # similarity matrices and analysis
    similarity_data = db.Column(JSONB)         # {"similarity_matrix":[...],"distance_metrics":{...},"optimal_clusters":3}
    
    # cluster quality and insights
    quality_metrics = db.Column(JSONB)         # {"silhouette_score":0.72,"intra_cluster_similarity":0.85,"inter_cluster_distance":0.34}
    visualization_data = db.Column(JSONB)      # {"scatter_plot_coords":[...],"dendogram_data":{...},"interactive_config":{...}}


# --------------------------------------------------------------------
# 11) Concept Graph (Knowledge Network Visualization)
# --------------------------------------------------------------------
class ConceptGraphResult(db.Model, _ResultBase):
    __tablename__ = "concept_graphs"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_concept_graphs_file_version"),
    )

    # graph metadata
    total_nodes = db.Column(db.Integer, default=0)
    total_edges = db.Column(db.Integer, default=0)
    graph_density = db.Column(db.Float)        # 0..1 connectivity density
    
    # graph structure (nodes and edges)
    nodes = db.Column(JSONB)                   # [{"id":"n1","label":"AI","type":"concept","centrality":0.8,"file_mentions":[...]}, ...]
    edges = db.Column(JSONB)                   # [{"source":"n1","target":"n2","weight":0.75,"relationship":"relates_to","evidence":[...]}, ...]
    
    # graph analysis and metrics
    graph_analysis = db.Column(JSONB)          # {"centrality_analysis":{...},"community_detection":{...},"paths_analysis":{...}}
    
    # hierarchical organization
    hierarchies = db.Column(JSONB)             # {"topic_hierarchies":[...],"entity_hierarchies":[...],"concept_layers":{...}}
    
    # interactive features and visualization
    interactive_features = db.Column(JSONB)    # {"layout_config":{...},"filtering_options":[...],"interaction_modes":[...]}
    visualization_data = db.Column(JSONB)      # {"positions":{...},"styling":{...},"animation_config":{...}}


# --------------------------------------------------------------------
# 12) Saved Views (Custom Document Views and Filters)
# --------------------------------------------------------------------
class SavedViewsResult(db.Model, _ResultBase):
    __tablename__ = "saved_views"
    __table_args__ = (
        UniqueConstraint("file_id", "version", name="uq_saved_views_file_version"),
    )

    # views metadata
    total_views = db.Column(db.Integer, default=0)
    
    # smart default views
    default_views = db.Column(JSONB)           # [{"view_id":"recent","name":"Recent Files","filters":{...},"sort_order":[...]}, ...]
    
    # contextual views based on content analysis
    contextual_views = db.Column(JSONB)        # [{"view_id":"topic_ai","name":"AI Documents","type":"topic","metadata":{...}}, ...]
    
    # filter combinations and search capabilities
    filter_combinations = db.Column(JSONB)     # {"quick_filters":[...],"advanced_combinations":[...],"saved_searches":[...]}
    
    # view templates for common workflows
    view_templates = db.Column(JSONB)          # [{"template_id":"research_project","name":"Research Template","views":[...]}, ...]
    
    # management and analytics features
    management_features = db.Column(JSONB)     # {"view_organization":{...},"sharing_options":{...},"automation":{...}}
    analytics_framework = db.Column(JSONB)     # {"usage_tracking":{...},"optimization_suggestions":[...],"reporting":{...}}