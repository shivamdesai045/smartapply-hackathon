import os

bind = "0.0.0.0:" + os.getenv("PORT", "10000")
# OCR jobs/cache are process-local: do not increase workers or service replicas.
workers = 1
worker_class = "gthread"
threads = 4
timeout = 240
graceful_timeout = 30
preload_app = False
# Avoid storing request URLs containing session identifiers.
accesslog = None
errorlog = "-"
