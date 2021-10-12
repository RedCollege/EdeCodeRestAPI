#!/bin/bash
service cron start
#cron -l 2 -f
if [ -z "$DEBUG" ]
then
    echo "DEBUG not found"
    exec gunicorn --config ./gunicorn_config.py controller:app
else
    echo "DEBUG has the value: $DEBUG"
    exec gunicorn --config ./gunicorn_config.py controller:app --reload
fi