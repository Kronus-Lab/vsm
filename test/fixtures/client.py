"""Client fixture for pytest to access the application over http"""

import pytest
from flask import Flask
from flask.testing import FlaskClient

@pytest.fixture
def client(application: Flask) -> FlaskClient:
    return application.test_client()