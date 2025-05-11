"""
This module is a Flask app to authenticate and
grab VPN configurations for OpenVPN Community Server
"""

# Standard libs as a whole
import json
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
APP_CONFIG = None
with open('config/vsm/app.json', 'r', encoding='utf-8') as f:
    APP_CONFIG = json.load(f)
app.secret_key = APP_CONFIG['FLASK_SECRET']

# Enable flask debug mode for development environment
app.debug = APP_CONFIG['ENV'] == 'development'

# App Settings
VPN_MAPPINGS = None
with open('config/vsm/vpn_group_mapping.json', 'r', encoding='utf-8') as f:
    VPN_MAPPINGS = json.load(f)
    for loaded_mapping in VPN_MAPPINGS:
        app.logger.info("Loaded Mapping: %s to %s",
                        loaded_mapping["vpn_server"],
                        loaded_mapping["idp_group"])

# Pages as constants
INDEX_PAGE = '/'
LOGIN_PAGE = '/auth/login'
LOGOUT_PAGE = '/auth/logout'
AUTH_ENDPOINT = '/auth/callback'
API_BASE_PATH = '/api/servers'
WHOAMI_ENDPOINT = '/api/whoami'

# Configure session parameters
SESSION_COOKIE_DOMAIN = APP_CONFIG['HOSTNAME']
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'strict'
SESSION_COOKIE_SECURE = False
if APP_CONFIG['ENV'] != 'development':  # Set Secure Cookie if not in dev
    SESSION_COOKIE_SECURE = True  # pragma: no cover

# Setup OIDC
ISSUER = APP_CONFIG['AUTH_ISSUER']
CLIENTID = APP_CONFIG['AUTH_CLIENT_ID']
CLIENTSECRET = APP_CONFIG['AUTH_CLIENT_SECRET']
OIDCDISCOVERYURL = f'{ISSUER}/.well-known/openid-configuration'
USERNAMEFIELD = APP_CONFIG['AUTH_USERNAME_FIELD']
GROUPSFIELD = APP_CONFIG['AUTH_GROUPS_FIELD']

oauth = OAuth(app=app)
oauth.register(
    name='keycloak',
    client_id=CLIENTID,
    client_secret=CLIENTSECRET,
    server_metadata_url=OIDCDISCOVERYURL,
    client_kwargs={
        'scope': 'openid email profile',
        'code_challenge_method': 'S256'  # enable PKCE
    },
)

# Setup the Redis session cache
rcon = redis.Redis(
    host=APP_CONFIG['REDIS_HOST'],
    port=APP_CONFIG['REDIS_PORT'],
    db=0)


def vpn_servers_access(groups: list[str]) -> list[str]:
    """Map the oAuth token groups claim to VPN Server accesses"""
    vpn_servers: list[str] = []
    for mapping in VPN_MAPPINGS:
        if mapping['idp_group'] in groups:
            vpn_servers.append(mapping['vpn_server'])
    return vpn_servers


def get_user_session() -> dict:
    """Validate the session and test if the user needs to relogin"""

    uuid = session.get('user')
    user = None

    # Load the user session from the cache if it exists
    if uuid is not None and rcon.get(uuid) is not None:
        user = json.loads(rcon.get(uuid))

    # Void the user session if it is expired
    if user is not None and user['expires_at'] <= time.time():
        user = None

    return user


@app.route(f'{WHOAMI_ENDPOINT}')
def whoami():
    """API - Fetch user info from session"""

    # If user is not logged-in, return a 401
    user = get_user_session()
    if user is None:
        return Response(status=401)

    groups = user['userinfo'][GROUPSFIELD]

    vpn_servers = vpn_servers_access(groups)

    response_payload = {
        'username': user['userinfo'][USERNAMEFIELD],
        'vpn_servers': vpn_servers
    }

    app.logger.debug(
        "whoami?: %s",
        response_payload
    )

    return Response(
        json.dumps(response_payload),
        status=200,
        content_type='application/json')


@app.route(f'{INDEX_PAGE}')
def index():
    """UI - Index page for the portal"""

    # If user is not logged-in, redirect to login page
    user = get_user_session()
    if user is None:
        return redirect(LOGIN_PAGE, 302)

    username = user['userinfo'][USERNAMEFIELD]
    groups = user['userinfo'][GROUPSFIELD]

    app.logger.info(
        "%s has logged in and is in the following groups: %s",
        username,
        groups)

    vpn_servers = vpn_servers_access(groups)

    return render_template(
        'index.html',
        username=username,
        vpn_servers=vpn_servers)


@app.route(LOGIN_PAGE)
def login():
    """UI - Login redirection"""
    scheme = 'http' if APP_CONFIG['ENV'] == 'development' else 'https'
    redirect_uri = url_for('auth', _external=True, _scheme=scheme)
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
    return redirect(INDEX_PAGE, 302)


@app.route(f'{API_BASE_PATH}/<server>')
def get_server_config(server):
    """API - Request server access"""

    # If user is not logged-in, return a 401
    user = get_user_session()
    if user is None:
        return Response(status=401)

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
    vault_custom_ca = None
    if 'CUSTOM_VAULT_CA' in APP_CONFIG.keys():
        vault_custom_ca = APP_CONFIG['CUSTOM_VAULT_CA']  # pragma: no cover

    if APP_CONFIG['ENV'] == 'development':
        print(f'CustomCA Value: {vault_custom_ca}')

    # Skip SSL verification if in development
    verify_cert = APP_CONFIG['ENV'] != 'development'

    # Connect to vault
    vault = hvac.Client(
        url=APP_CONFIG['VAULT_URL'],
        cert=vault_custom_ca,
        verify=verify_cert
    )

    vault.auth.jwt.jwt_login(
        role=vault_parameters['jwt_role'],
        jwt=user['access_token'],
        path=vault_parameters['jwt_path']
    )

    # Grab VPN Metadata
    vpnmeta = vault.secrets.kv.v2.read_secret(
        mount_point=vault_parameters['metadata_mountpoint'],
        path=vault_parameters['metadata_path'],
        raise_on_deleted_version=True
    )['data']['data']

    # Generate Certificate + Key
    cert_response = vault.secrets.pki.generate_certificate(
        name='client',
        common_name=user['userinfo'][USERNAMEFIELD],
        mount_point=vault_parameters['pki_mountpoint']
    )['data']

    app.logger.info("VPN Metadata: %s", vpnmeta)

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


if __name__ == '__main__':  # pragma: no cover
    app.run(host='0.0.0.0', port=3000)
