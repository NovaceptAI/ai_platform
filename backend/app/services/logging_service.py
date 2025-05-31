from models.logs import EndpointLog
from db import db

def log_endpoint(username, endpoint, method, ip_address):
    log = EndpointLog(
        username=username,
        endpoint=endpoint,
        method=method,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()