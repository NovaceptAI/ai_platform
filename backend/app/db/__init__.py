from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker, scoped_session

db = SQLAlchemy()

def create_task_session():
    """
    Create a new database session for Celery tasks.
    This ensures fresh connections with proper pool configuration.

    Usage in tasks:
        session = create_task_session()
        try:
            # ... your task logic ...
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    """
    Session = sessionmaker(bind=db.engine)
    return Session()   