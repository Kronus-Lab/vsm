"""Logout fixture to delete the current session for the tests"""

from collections.abc import Callable

import pytest
from flask.testing import FlaskClient


@pytest.fixture
def logout() -> Callable:
    """Helper function to log out after we are done with the application"""

    def factory(client: FlaskClient):
        # Logout from the application
        response = client.get('/auth/logout')
        assert response.status_code == 302
        assert 'Location' in response.headers
        assert response.headers['Location'] == '/'

    return factory
