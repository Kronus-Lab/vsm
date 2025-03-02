"""Expire Session fixture to expire active session from the cache"""

import json
import base64
import time
from collections.abc import Callable

import pytest
import redis
from flask.testing import FlaskClient


@pytest.fixture
def expire_session() -> Callable:
    """Helper function to expire an active session"""

    def factory(client: FlaskClient):
        # Grab the session UUID
        session = json.loads(
            base64.b64decode(
                client.get_cookie('session').decoded_value.split('.')[0] +
                "=="))
        uuid = session['user']

        # Connect to the cache server
        rcon = redis.Redis(
            host='localhost',
            port='6379',
            db=0)

        # Expire the current token
        token = json.loads(rcon.get(uuid))
        current_time = int(time.time())
        token['expires_at'] = current_time

        # Save the expired token to the cache
        rcon.set(uuid, json.dumps(token))

    return factory
