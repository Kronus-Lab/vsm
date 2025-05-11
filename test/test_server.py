""" TEST - Server Endpoint """

import fixtures  # pylint: disable=unused-import


def test_get_server_config(client, login, logout):
    """Server config test case - valid config response"""
    login(client)

    response = client.get('/api/servers/myserver')
    assert response.status_code == 200
    assert 'dev tun' in response.get_data(as_text=True)

    logout(client)


def test_get_server_config_expired(client, expire_session, login, logout):
    """Server config test case - expired session"""
    login(client)
    expire_session(client)

    response = client.get('/api/servers/myserver')
    assert response.status_code == 401

    logout(client)


def test_get_server_config_not_logged_in(client):
    """Server config test case - not logged in redirects to /"""
    response = client.get('/api/servers/myserver')
    assert response.status_code == 401


def test_get_server_config_invalid_server(client, login, logout):
    """Server config test case - invalid server choice redirects to /"""
    login(client)

    response = client.get('/api/servers/mybadserver')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

    logout(client)


def test_get_server_config_denied_server(client, login, logout):
    """Server config test case - access denied is redirected to /"""
    login(client)

    response = client.get('/api/servers/myserver4')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

    logout(client)
