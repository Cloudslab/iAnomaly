import os

workers = int(os.environ.get('GUNICORN_PROCESSES', '3')) # Gunicorn documentation recommends (2 x $num_cores) + 1 as the no.of processes (i.e. workers)

# threads = int(os.environ.get('GUNICORN_THREADS', '4'))

# timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8080')

forwarded_allow_ips = '*'

secure_scheme_headers = { 'X-Forwarded-Proto': 'https' }