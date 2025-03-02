""" TEST - Index page """

import fixtures


def test_index(client, login, logout):
    """Index page test - logged in"""
    login(client)

    # Get the index page after being authenticated
    response = client.get('/')
    assert response.status_code == 200
    assert 'Logged in as: testuser' in response.get_data(as_text=True)
    assert 'Download VPN Server Configuration' in response.get_data(
        as_text=True)
    assert 'myserver' in response.get_data(as_text=True)
    assert 'myserver2' in response.get_data(as_text=True)
    assert 'myserver3' in response.get_data(as_text=True)
    assert 'myserver4' not in response.get_data(as_text=True)

    logout(client)


def test_index_expired(client, login, logout, expire_session):
    """Index page test - Expired session"""
    login(client)

    expire_session(client)

    response = client.get('/')
    assert response.status_code == 302
    assert response.headers['Location'] == '/auth/login'

    logout(client)
