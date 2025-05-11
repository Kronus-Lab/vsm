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
    """
    Tests that accessing the server configuration with an expired session returns 401 Unauthorized.
    """
    login(client)
    expire_session(client)

    response = client.get('/api/servers/myserver')
    assert response.status_code == 401

    logout(client)


def test_get_server_config_not_logged_in(client):
    """
    Tests that accessing the server configuration endpoint without logging in returns a 401 status code.
    """
    response = client.get('/api/servers/myserver')
    assert response.status_code == 401


def test_get_server_config_invalid_server(client, login, logout):
    """
    Tests that requesting the configuration for a non-existent server redirects to the home page.
    
    Sends a GET request for an invalid server and asserts a 302 redirect to "/".
    """
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
