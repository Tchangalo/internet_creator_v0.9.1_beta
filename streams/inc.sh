#!/bin/bash

EVENTLET_HUB=poll gunicorn --worker-class eventlet -w 2 -b 0.0.0.0:32100 --timeout 120 --graceful-timeout 30 app:app