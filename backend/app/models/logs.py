from app.db import db
from datetime import datetime

class EndpointLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    endpoint = db.Column(db.Text)  # Changed from String(255) to Text to handle long URLs
    method = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))