"""Application fixture for pytest; provides access to the Flask application"""

import logging

import pytest
from flask import Flask

from vsm import app


@pytest.fixture
def application() -> Flask:
    """
    Application fixture to set the application in dev mode regardless of the
    environment variables specified.
    """

    app.config.update({
        "DEVELOPMENT": True
    })

    app.logger.level = logging.DEBUG

    yield app
