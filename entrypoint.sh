#!/bin/bash
service cron start
#cron -l 2 -f
exec gunicorn --config /app/gunicorn_config.py app.wsgi:app
