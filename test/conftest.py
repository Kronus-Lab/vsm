"""Conftest file for pytest; Used to load all fixtures in current directory"""

pytest_plugins = [
    "fixtures.application",
    "fixtures.client",
    "fixtures.expire_session",
    "fixtures.login",
    "fixtures.logout"
]
