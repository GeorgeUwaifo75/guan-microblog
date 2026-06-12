#!/bin/bash

# Start the application in background
python main.py &
APP_PID=$!

# Wait for app to start
sleep 5

# Make a warm-up request to pre-load cache
curl -s http://localhost:8000/api/health > /dev/null 2>&1

# Wait for app process
wait $APP_PID