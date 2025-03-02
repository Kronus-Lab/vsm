import pytest

pytest_plugins = [
    "fixtures.application",
    "fixtures.client",
    "fixtures.expire_session", 
    "fixtures.login",
    "fixtures.logout"
]