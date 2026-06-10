#!/bin/bash
set -e

LOG_FILE="/home/ubuntu/start_docker.log"
exec > "$LOG_FILE" 2>&1

export PATH=$PATH:/usr/local/bin:/usr/bin:/bin

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 682844365170.dkr.ecr.ap-south-1.amazonaws.com

echo "Pulling latest Docker image from ECR..."
# FIXED: Updated to the correct repository name
docker pull 682844365170.dkr.ecr.ap-south-1.amazonaws.com/time-prediction-system:latest

echo "Cleaning up any existing container..."
set +e
docker stop delivery_time_pred 2>/dev/null
docker rm delivery_time_pred 2>/dev/null
set -e

echo "Starting the new container..."
# FIXED: Updated the image URI at the end of the run command
docker run -d \
  -p 80:8000 \
  --name delivery_time_pred \
  --restart unless-stopped \
  -e DAGSHUB_USER_TOKEN=0cf1301f969792de31650f37e14a5f4f446e911a \
  682844365170.dkr.ecr.ap-south-1.amazonaws.com/time-prediction-system:latest

echo "Container started successfully."
chown ubuntu:ubuntu "$LOG_FILE"