"""
This module is a Flask app to authenticate and
grab VPN configurations for OpenVPN Community Server
"""

# Standard libs as a whole
import json
import os
import time

# Specific modules of standard libs
from uuid import uuid4

# 3rd party libs as a whole
import certifi
import redis
import hvac

# Specific modules from 3rd party libs
from flask import Flask, url_for, session
from flask import render_template, redirect, Response
from authlib.integrations.flask_client import OAuth

print("Using cacerts from " + certifi.where())

# Flask Settings
app = Flask(__name__)
app_config = None
with open('config/app.json', 'r', encoding='utf-8') as f:
    app_config = json.load(f)
app.secret_key = app_config['FLASK_SECRET']

# App Settings
VPN_MAPPINGS = None
with open('config/vpn_group_mapping.json', 'r', encoding='utf-8') as f:
    VPN_MAPPINGS = json.load(f)

# Pages as constants
INDEX_PAGE = '/'
LOGIN_PAGE = '/login'
LOGOUT_PAGE = '/logout'
AUTH_ENDPOINT = '/auth'
API_BASE_PATH = '/api'

# Configure session parameters
SESSION_COOKIE_DOMAIN = app_config['HOSTNAME']
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'strict'
SESSION_COOKIE_SECURE = False
if app_config['ENV'] != 'development':  # Set Secure Cookie if not in dev
    SESSION_COOKIE_SECURE = True

# Setup OIDC
issuer = app_config['AUTH_ISSUER']
clientId = app_config['AUTH_CLIENT_ID']
clientSecret = app_config['AUTH_CLIENT_SECRET']
oidcDiscoveryUrl = f'{issuer}/.well-known/openid-configuration'
username_field = app_config['AUTH_USERNAME_FIELD']
groups_field = app_config['AUTH_GROUPS_FIELD']

oauth = OAuth(app=app)
oauth.register(
    name='keycloak',
    client_id=clientId,
    client_secret=clientSecret,
    server_metadata_url=oidcDiscoveryUrl,
    client_kwargs={
        'scope': 'openid email profile',
        'code_challenge_method': 'S256'  # enable PKCE
    },
)

# Setup the Redis session cache
rcon = redis.Redis(
    host=app_config['REDIS_HOST'],
    port=app_config['REDIS_PORT'],
    db=0)


@app.route(f'{INDEX_PAGE}')
def index():
    """UI - Index page for the portal"""

    uuid = session.get('user')
    user = None
    if uuid is not None and rcon.get(uuid) is not None:
        user = json.loads(rcon.get(uuid))
    else:
        return redirect(LOGIN_PAGE, 302)

    if user['expires_at'] <= time.time():
        return redirect(LOGIN_PAGE, 302)

    username = None if user is None else user['userinfo'][username_field]

    groups = user['userinfo'][groups_field]
    vpn_servers = []
    for mapping in VPN_MAPPINGS:
        if mapping['idp_group'] in groups:
            vpn_servers.append(mapping['vpn_server'])

    return render_template(
        'index.html',
        username=username,
        vpn_servers=vpn_servers)


@app.route(LOGIN_PAGE)
def login():
    """UI - Login redirection"""
    redirect_uri = url_for('auth', _external=True, _scheme='https')
    return oauth.keycloak.authorize_redirect(redirect_uri)


@app.route(AUTH_ENDPOINT)
def auth():
    """UI - Login token processing"""
    token = oauth.keycloak.authorize_access_token()

    if token:
        uuid = session.get('user')
        if uuid is None:
            uuid = uuid4().hex
            session['user'] = uuid
        rcon.set(uuid, json.dumps(token))

    return redirect(INDEX_PAGE)


@app.route(LOGOUT_PAGE)
def logout():
    """UI - Logout"""
    rcon.delete(session['user'])
    session.pop('user', None)
    return render_template('logout.html')


@app.route(f'{API_BASE_PATH}/<server>')
def get_server_config(server):
    """API - Request server access"""

    # Grab user session/groups from Redis
    uuid = session.get('user')
    user = None
    if uuid is not None and rcon.get(uuid) is not None:
        user = json.loads(rcon.get(uuid))
    else:
        redirect(INDEX_PAGE, 302)

    if user['expires_in'] <= 0:
        print('Expired session')
        redirect(LOGIN_PAGE, 302)

    groups = user['userinfo']['groups']

    # Validate if the user is allowed to request a cert for the server
    #   by verifying if the server is one of the groups the user has
    #   access to
    vault_parameters = {
        'metadata_mountpoint': None,
        'metadata_path': None,
        'pki_mountpoint': None,
        'jwt_role': None,
        'jwt_path': None
    }

    for mapping in VPN_MAPPINGS:
        if mapping['idp_group'] in groups and mapping['vpn_server'] == server:
            vault_parameters['metadata_mountpoint'] = mapping['vault_metadata_mountpoint']
            vault_parameters['metadata_path'] = mapping['vault_metadata_path']
            vault_parameters['pki_mountpoint'] = mapping['vault_pki_mountpoint']
            vault_parameters['jwt_role'] = mapping['vault_jwt_role']
            vault_parameters['jwt_path'] = mapping['vault_jwt_path']

    if (
        vault_parameters['metadata_mountpoint'] is None or
        vault_parameters['metadata_path'] is None or
        vault_parameters['pki_mountpoint'] is None or
        vault_parameters['jwt_role'] is None or
        vault_parameters['jwt_path'] is None
    ):
        # Redirect to INDEX_PAGE if user is unauthorized
        return redirect(INDEX_PAGE, 302)

    # Load custom CA Cert if needed
    vault_custom_ca = app_config['CUSTOM_VAULT_CA'] if 'CUSTOM_VAULT_CA' in app_config.keys() else None
    if app_config['ENV'] == 'development':
        print(f'CustomCA Value: {vault_custom_ca}')

    # Skip SSL verification if in development
    verify_cert = app_config['ENV'] != 'development'

    # Connect to vault
    vault = hvac.Client(
        url=app_config['VAULT_URL'],
        cert=vault_custom_ca,
        verify=verify_cert
    )

    vault.auth.jwt.jwt_login(
        role=vault_parameters['jwt_role'],
        jwt=user['access_token'],
        path=vault_parameters['jwt_path']
    )

    # Grab VPN Metadata
    vpnmeta = vault.secrets.kv.v1.read_secret(
        mount_point=vault_parameters['metadata_mountpoint'],
        path=vault_parameters['metadata_path']
    )['data']

    # Generate Certificate + Key
    cert_response = vault.secrets.pki.generate_certificate(
        name='client',
        common_name=user['userinfo'][username_field],
        mount_point=vault_parameters['pki_mountpoint']
    )['data']

    resp = Response(
        render_template(
            'template.ovpn',
            hostname=vpnmeta['hostname'],
            port=vpnmeta['port'],
            protocol=vpnmeta['protocol'],
            server_dn=vpnmeta['server_dn'],
            cipher=vpnmeta['cipher'],
            digest=vpnmeta['digest'],
            certificate_authority=vpnmeta['certificate_authority'],
            certificate=cert_response['certificate'],
            certificate_key=cert_response['private_key'],
            server_tls_key=vpnmeta['server_tls_key']),
        mimetype='text/plain')

    resp.headers['Content-Disposition'] = f"attachment; filename= {server}.ovpn"

    return resp


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
