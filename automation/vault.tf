terraform {
  required_providers {
    vault = {
      source = "hashicorp/vault"
      version = "4.2.0"
    }
  }
}

provider "vault" {
  address = "http://localhost:8200"
  token = "admin"
}

resource "vault_mount" "vpnmeta" {
  path = "vpnmeta/vpn"
  type = "kv-v2"
  options = {
    version = "2"
    type = "kv-v2"
  }
  description = "VPN Metadata"
}

resource "vault_kv_secret_v2" "testmeta" {
    mount = vault_mount.vpnmeta.path
    name = "testmeta"
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

resource "vault_mount" "testvpnpki" {
    path = "vpn/test"
    type = "pki"

}

resource "vault_pki_secret_backend_root_cert" "testroot" {
    backend = vault_mount.testvpnpki.path
    type = "internal"
    common_name = "testvpn"
    ttl = "86400"
}

resource "vault_pki_secret_backend_issuer" "testissuer" {
  backend = vault_pki_secret_backend_root_cert.testroot.backend
  issuer_ref = vault_pki_secret_backend_root_cert.testroot.issuer_id
  issuer_name = "testvpn-issuer"
}

resource "vault_pki_secret_backend_role" "testvpnrole" {
  backend = vault_mount.testvpnpki.path
  name = "client"
  max_ttl = 28800
  allow_any_name = true
  key_bits = 4096
  enforce_hostnames = false
}

resource "vault_policy" "testvpnpolicy" {
  name = "testvpn"
  policy = <<EOT
############################
# Reserved for VPN Role    #
############################

path "${vault_mount.testvpnpki.path}/issue/client" {
    capabilities = ["create", "update"]
}

path "${vault_kv_secret_v2.testmeta.path}" {
    capabilities = ["read", "list"]
}
EOT
}