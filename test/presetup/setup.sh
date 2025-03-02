#!/bin/sh

# Check if development environment is already up
if docker ps | grep -q vsm; then
    echo "Development environment up or broken. Please use cleanup task first"
    exit 1
fi

# Start docker compose
docker compose up -d -f docker-compose-common.yml -f docker-compose-e2e.yml


# Wait for stack to be up
./wait.sh

# Switch to presetup folder
cd test/presetup

# Configure using Terraform
terraform init --upgrade
terraform apply --auto-approve