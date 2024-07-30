#!/bin/sh

# Stop docker compose
docker compose down

# Delete terraform tfstate
rm test/presetup/vsmdevel.tfstate