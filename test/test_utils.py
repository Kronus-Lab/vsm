"""TEST CASE UTILITIES"""

import json
import time
import base64

import redis
import requests
from bs4 import BeautifulSoup
from flask.testing import FlaskClient


def login(client: FlaskClient):
    """Login to the application using the running keycloak instance"""
    # Grab the index page which redirects to the login API
    response = client.get('/')
    assert response.status_code == 302
    assert 'Location' in response.headers
    assert response.headers['Location'] == '/auth/login'


    # Get the login API to send you to Keycloak's auth form
    response = client.get('/auth/login')
    assert response.status_code == 302
    assert 'Location' in response.headers
    auth_url = 'http://kc.local.kronus.network/realms/devel/protocol/openid-connect/auth?'
    assert response.headers['Location'].startswith(auth_url)

    # Get the authentication form using a session
    requests_client = requests.Session()
    response = requests_client.get(response.headers['Location'])
    soup = BeautifulSoup(response.content, features="html.parser")
    idp_authenticate_endpoint = soup.find('form')['action']

    # Send the form data
    response = requests_client.post(idp_authenticate_endpoint,
                                    data={"username": "testuser"}, allow_redirects=False)
    assert response.status_code == 302
    assert 'Location' in response.headers
    assert response.headers['Location'].startswith('http://localhost/auth/callback?')

    # Finalize authentication with application
    response = client.get(response.headers['Location'])
    assert response.status_code == 302
    assert 'Location' in response.headers
    assert response.headers['Location'] == '/'

def logout(client: FlaskClient):
    """Logout of the application"""
    # Logout from the application
    response = client.get('/auth/logout')
    assert response.status_code == 302
    assert 'Location' in response.headers
    assert response.headers['Location'] == '/'

def expire_session(client: FlaskClient):
    """Expire a user session from the redis cache"""
    session = json.loads(
        base64.b64decode(
            client.get_cookie('session').decoded_value.split('.')[0] + "=="))
    uuid = session['user']
    rcon = redis.Redis(
        host='localhost',
        port='6379',
        db=0)
    token = json.loads(rcon.get(uuid))
    current_time = int(time.time())
    token['expires_at'] = current_time
    rcon.set(uuid, json.dumps(token))
