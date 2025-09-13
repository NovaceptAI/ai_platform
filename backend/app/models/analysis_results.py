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