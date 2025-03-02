"""Login fixture to create a new session for the test"""

from collections.abc import Callable

import pytest
import requests
from bs4 import BeautifulSoup
from flask.testing import FlaskClient

@pytest.fixture
def login() -> Callable:
    """Helper function to login to the application"""
   
    def factory(client: FlaskClient):
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
        response = requests_client.post(
            idp_authenticate_endpoint, data={
                "username": "testuser"}, allow_redirects=False)
        assert response.status_code == 302
        assert 'Location' in response.headers
        assert response.headers['Location'].startswith(
            'http://localhost/auth/callback?')

        # Finalize authentication with application
        response = client.get(response.headers['Location'])
        assert response.status_code == 302
        assert 'Location' in response.headers
        assert response.headers['Location'] == '/'

        # Finalize authentication with application
        response = client.get(response.headers['Location'])
        assert response.status_code == 200

    return factory
