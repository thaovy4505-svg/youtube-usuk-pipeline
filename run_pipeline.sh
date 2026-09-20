#!/bin/bash
cd /home/vy/youtube_data_pipeline
source .venv/bin/activate
python3 main.py >> logs/cron.log 2>&1

