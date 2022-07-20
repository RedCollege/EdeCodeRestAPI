#!/bin/bash
service cron start
#cron -l 2 -f
exec gunicorn --config ./gunicorn_config.py controller:app
