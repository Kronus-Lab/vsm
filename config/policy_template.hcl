############################
# Reserved for VPN Role    #
############################

path "<vault_pki_mountpoint>/issue/client" {
    capabilities = ["create", "update"]
}

path "<vault_metadata_mountpoint>/<vault_metadata_path>" {
    capabilities = ["read", "list"]
}
