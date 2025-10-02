terraform {
  backend "local" {
    path = "vsmdevel.tfstate"
  }
  required_providers {
    keycloak = {
      source = "mrparkers/keycloak"
      version = "4.4.0"
    }
    vault = {
      source = "hashicorp/vault"
      version = "4.3.0"
    }
  }
}

variable "oidc_client_id" {
  type = string
  default = "vsm"
}

variable "oidc_client_secret" {
  type = string
  default = "devel1234"
}

variable "oidc_realm_name" {
  type = string
  default = "devel"
}

variable "oidc_redirect_urls" {
  type = list(string)
  default = [ "http://vsm.local.kronus.network/*", "http://localhost/*" ]
}

# Keycloak section

provider "keycloak" {
  client_id     = "admin-cli"
  username      = "admin"
  password      = "admin"
  url           = "http://kc.local.kronus.network"
}

resource "keycloak_realm" "devel" {
    realm                   = var.oidc_realm_name
    enabled                 = true
    display_name            = "Development Realm"
    display_name_html       = "<b>Development Realm</b>"
}

resource "keycloak_authentication_flow" "flow_alwaysgood" {
    realm_id    = keycloak_realm.devel.id
    alias       = "development-always-good"
}


resource "keycloak_authentication_execution" "flow_alwaysgood_execution_1" {
    realm_id            = keycloak_realm.devel.id
    parent_flow_alias   = keycloak_authentication_flow.flow_alwaysgood.alias
    authenticator       = "auth-username-form"
    requirement         = "REQUIRED"
}

resource "keycloak_authentication_execution" "flow_alwaysgood_execution_2" {
    realm_id            = keycloak_realm.devel.id
    parent_flow_alias   = keycloak_authentication_flow.flow_alwaysgood.alias
    authenticator       = "allow-access-authenticator"
    requirement         = "REQUIRED"

    depends_on = [ keycloak_authentication_execution.flow_alwaysgood_execution_1 ]
}

resource "keycloak_authentication_bindings" "authflowbindings" {
  realm_id      = keycloak_realm.devel.id
  browser_flow  = keycloak_authentication_flow.flow_alwaysgood.alias
}

resource "keycloak_group" "examplegroup" {
  realm_id  = keycloak_realm.devel.id
  name      = "example"
}

resource "keycloak_user" "testuser" {
  realm_id        = keycloak_realm.devel.id
  username        = "testuser"
  email           = "test@test.net"
  email_verified  = true
  first_name      = "Test"
  last_name       = "User" 
}

resource "keycloak_user_groups" "examplegroup_mapping" {
  realm_id    = keycloak_realm.devel.id
  user_id     = keycloak_user.testuser.id
  group_ids   = [ keycloak_group.examplegroup.id ]
}

resource "keycloak_openid_client" "vsm" {
  client_id               = var.oidc_client_id
  enabled                 = true
  realm_id                = keycloak_realm.devel.id
  access_type             = "CONFIDENTIAL"
  valid_redirect_uris     = var.oidc_redirect_urls
  client_secret           = var.oidc_client_secret
  standard_flow_enabled   = true
}

resource "keycloak_openid_group_membership_protocol_mapper" "group_membership_mapper" {
  realm_id    = keycloak_realm.devel.id
  client_id   = keycloak_openid_client.vsm.id
  name        = "group-membership-mapper"
  claim_name  = "groups"
}

resource "keycloak_openid_audience_protocol_mapper" "audience_mapper" {
  realm_id = keycloak_realm.devel.id
  name = "audience"
  client_id = keycloak_openid_client.vsm.id
  included_client_audience = keycloak_openid_client.vsm.client_id
  add_to_access_token = true
  add_to_id_token = true
}

# Vault Section

provider "vault" {
  address = "http://hcv.local.kronus.network"
  token = "admin"
}

resource "vault_jwt_auth_backend" "jwt" {
  path = "jwt"
  type = "jwt"
  default_role = "test-role"
  oidc_discovery_url = "http://kc.local.kronus.network/realms/devel"
  depends_on = [ keycloak_realm.devel ]
}

resource "vault_jwt_auth_backend_role" "name" {
  role_name = "test-role"
  user_claim = "preferred_username"
  groups_claim = "groups"
  bound_audiences = [ "vsm" ]
  verbose_oidc_logging = true
  backend = vault_jwt_auth_backend.jwt.path
  allowed_redirect_uris = var.oidc_redirect_urls
  bound_claims = {
    "groups" = keycloak_group.examplegroup.path
  }
  role_type = "jwt"
  token_policies = [ vault_policy.testvpnpolicy.name ]
  token_no_default_policy = true
}

resource "vault_mount" "vpnmeta" {
  path = "vpnmeta"
  type = "kv"
  options = { version = "2" }
  description = "VPN Metadata mount"
}

resource "vault_kv_secret_backend_v2" "vpnmetadata_settings_devel" {
  mount = vault_mount.vpnmeta.path
  max_versions = 2
  cas_required = false
}

resource "vault_mount" "pki_devel" {
  path = "vpn/devel"
  type = "pki"
  description = "PKI Infrastructure for VSM Devel Server"
}

resource "vault_pki_secret_backend_root_cert" "vpn_devel_ca" {
  backend = vault_mount.pki_devel.path
  type = "internal"
  common_name = "VSM Development Server"
  ttl = 315360000
  format = "pem"
  private_key_format = "der"
  key_type = "rsa"
  key_bits = 4096
  exclude_cn_from_sans = false
  ou = "VSM"
  organization = "Kronus Labs"
  country = "Canada"
  province = "Quebec"
  locality = "Gatineau"
}

resource "vault_pki_secret_backend_role" "pkiclient" {
  backend = vault_mount.pki_devel.path
  name = "client"
  ttl = 28800
  max_ttl = 28800
  enforce_hostnames = false
  allow_any_name = true
  key_type = "rsa"
  key_bits = 4096
  server_flag = false
  client_flag = true
  code_signing_flag = false
  email_protection_flag = false
}

resource "vault_kv_secret_v2" "testmeta" {
    mount = vault_mount.vpnmeta.path
    name = "develmeta"
    cas = 1
    delete_all_versions = true
    data_json = jsonencode(
    {
        "hostname": "myvpn.example.com",
        "port": 1194,
        "protocol": "udp",
        "server_dn": "C=CA, ST=Ontario, L=Toronto, O=My Org, emailAddress=admin@example.com, CN=myvpn.example.com",
        "cipher": "AES-256-CBC",
        "digest": "SHA1",
        "certificate_authority": "-----BEGIN CERTIFICATE-----\nsingleline\ncertificate\n-----END CERTIFICATE-----",
        "server_tls_key": "#\n# 2048 bit OpenVPN static key\n#\n-----BEGIN OpenVPN Static key V1-----\nsingleline\nstatickey\n-----END OpenVPN Static key V1-----\n"
    }
    )
}


resource "vault_policy" "testvpnpolicy" {
  name = "develvpn"
  policy = <<EOT
############################
# Reserved for VPN Role    #
############################

path "${vault_mount.pki_devel.path}/issue/client" {
    capabilities = ["create", "update"]
}

path "${vault_kv_secret_v2.testmeta.path}" {
    capabilities = ["read", "list"]
}
EOT
}