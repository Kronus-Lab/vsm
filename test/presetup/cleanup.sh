#!/bin/sh

# Stop docker compose
docker compose -f docker-compose-common.yml -f docker-compose-e2e.yml down

# Delete terraform tfstate
rm -f test/presetup/vsmdevel.tfstate