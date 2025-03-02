#!/bin/sh

# Wait for HAProxy to awake
echo "Giving HAProxy 5 seconds to start"
sleep 5

# Wait for Keycloak to be up
echo "Waiting for Keycloak to start"
while [ $(curl -sI http://kc.local.kronus.network | head -n1 | cut -d ' ' -f 2) -ge 400 ]; do
    echo -n '.'
    sleep 1
    done

echo ''

# Wait for Vault to be up
echo "Waiting for Vault to start"
while [ $(curl -sI http://hcv.local.kronus.network | head -n1 | cut -d ' ' -f 2) -ge 400 ]; do
    echo -n '.'
    sleep 1
    done
