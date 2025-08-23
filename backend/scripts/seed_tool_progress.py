import uuid
import datetime as dt
from app.db import db
from app.models import Progress
from app.main import app

DONE = [
    'ai-summarizer', 'segmenter', 'interactive-quiz-creator',
    'ai-chronology', 'document-analyzer'
]
HALF = [
    'creative-writing-prompts', 'story-visualizer'
]

SEED_USER = 'PROJECT'


def seed():
    now = dt.datetime.utcnow()
    for slug in DONE:
        p = Progress(
            id=uuid.uuid4(), user_id=SEED_USER, tool=slug,
            status='completed', percentage=100, created_at=now
        )
        db.session.add(p)
    for slug in HALF:
        p = Progress(
            id=uuid.uuid4(), user_id=SEED_USER, tool=slug,
            status='pending', percentage=50, created_at=now
        )
        db.session.add(p)
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        seed()
        print('Seeded Progress for DONE and HALF tools')