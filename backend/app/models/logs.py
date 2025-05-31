from db import db
from datetime import datetime

class EndpointLog(db.Model):
    __tablename__ = 'endpoint_logs'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    endpoint = db.Column(db.String(255))
    method = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))