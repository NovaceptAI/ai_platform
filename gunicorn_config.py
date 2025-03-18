bind = "0.0.0.0:8000"
workers = 25
accesslog = "/home/azureuser/ai_platform/logs/gunicorn_access.log"
errorlog = "/home/azureuser/ai_platform/logs/gunicorn_error.log"
loglevel = "info"
timeout = 120  # Timeout limit of 2 minutes