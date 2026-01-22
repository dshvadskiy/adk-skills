#!/bin/bash

# Script to kill process running on a specific port
# Usage: ./kill_port.sh [port]
# Default port: 8000

PORT=${1:-8000}

echo "Checking for processes on port $PORT..."

# Find process using the port
PID=$(lsof -i -P | grep LISTEN | grep -E ":$PORT " | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "No process found listening on port $PORT"
    exit 0
fi

echo "Found process $PID listening on port $PORT"
echo "Killing process..."

kill -9 $PID

if [ $? -eq 0 ]; then
    echo "Successfully killed process $PID"
else
    echo "Failed to kill process $PID. You may need sudo privileges."
    exit 1
fi
