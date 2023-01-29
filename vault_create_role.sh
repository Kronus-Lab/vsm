#!/bin/bash

if [[ $# -ne 4 ]]; then
    exit 1
fi

AUTH_PATH=$1
ROLE=$2
OIDC_DISCOVERY_URL=$3
POLICY=$4

# Enable JWT auth at given path
vault auth enable -path=$AUTH_PATH jwt

# Setup JWT auth config
vault write auth/$AUTH_PATH/config oidc_discovery_url=$OIDC_DISCOVERY_URL default_role=$ROLE oidc_client_id="" oidc_client_secret=""

# Create role
vault write auth/$AUTH_PATH/role/$ROLE user_claim="sub" policies=$POLICY role_type="jwt" oidc_scopes="" ttl=1 bound_audiences="vsm"