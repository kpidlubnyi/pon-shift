import multiprocessing

bind = "0.0.0.0:8000"
backlog = 2048

workers = min(3, (multiprocessing.cpu_count() * 2) + 1)
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

max_requests = 1000
max_requests_jitter = 100

preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

disable_redirect_access_to_syslog = True
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = "gunicorn-pon-shift"

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}