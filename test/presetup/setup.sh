#!/bin/sh

MODE=$1

# Check if development environment is already up
if docker ps | grep -q vsm; then
    echo "Development environment up or broken. Please use cleanup task first"
    exit 1
fi

# Start docker compose
docker compose -f docker-compose-common.yml -f docker-compose-$MODE.yml up -d 

# Switch to presetup folder
cd test/presetup

# Wait for stack to be up
./wait.sh

# Configure using Terraform
terraform init --upgrade
terraform apply --auto-approve
