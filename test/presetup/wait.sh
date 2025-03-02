#!/bin/bash

# Helper function to wait for a given url/name
wait_for_service() {
  local url="$1"
  local name="$2"
  echo "Waiting for $name to start"
  while true; do
    status=$(curl -sI "$url" | head -n1 | cut -d ' ' -f 2)
    # Ensure status is numeric; if not, assume the service is not ready
    if [[ "$status" =~ ^[0-9]+$ ]] && [ "$status" -lt 400 ]; then
      break
    fi
    echo -n '.'
    sleep 1
  done
  echo ""
}

# Wait for HAProxy to awake
echo "Giving HAProxy 5 seconds to start"
sleep 5

wait_for_service "http://kc.local.kronus.network" "Keycloak"
wait_for_service "http://hcv.local.kronus.network" "Vault"
