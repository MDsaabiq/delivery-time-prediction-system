#!/bin/bash

# Redirect stdout and stderr to the log file
LOG_FILE="/home/ubuntu/start_docker.log"
exec > "$LOG_FILE" 2>&1

# Ensure path includes common binary locations
export PATH=$PATH:/usr/local/bin:/usr/bin:/bin

echo "========================================="
echo "Deployment started at: $(date)"
echo "========================================="

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 682844365170.dkr.ecr.ap-south-1.amazonaws.com

echo "Pulling latest Docker image from ECR..."
docker pull 682844365170.dkr.ecr.ap-south-1.amazonaws.com/food_delivery_time_prediction:latest

echo "Cleaning up any existing container..."
# Forcefully stop and remove the container if it exists, ignore errors if it doesn't
docker stop delivery_time_pred 2>/dev/null || true
docker rm delivery_time_pred 2>/dev/null || true

echo "Starting the new container..."
docker run -d \
  -p 80:8000 \
  --name delivery_time_pred \
  --restart unless-stopped \
  -e DAGSHUB_USER_TOKEN=0cf1301f969792de31650f37e14a5f4f446e911a \
  682844365170.dkr.ecr.ap-south-1.amazonaws.com/food_delivery_time_prediction:latest

echo "Container started successfully."

# Fix log file permissions so the 'ubuntu' user can view it without sudo
chown ubuntu:ubuntu "$LOG_FILE"