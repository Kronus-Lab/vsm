""" TEST - WhoAmI Endpoint """

import fixtures  # pylint: disable=unused-import


def test_whoami_not_loggedin(client):
    """WhoAmI test cases - not logged in"""
    response = client.get('/api/whoami')
    assert response.status_code == 401


def test_whoami_loggedin(client, login, logout):
    """WhoAmI test cases - logged in"""
    login(client)

    response = client.get('/api/whoami')
    assert response.status_code == 200
    assert 'testuser' in response.get_data(as_text=True)
    assert 'myserver' in response.get_data(as_text=True)
    assert 'myserver2' in response.get_data(as_text=True)
    assert 'myserver3' in response.get_data(as_text=True)
    assert 'myserver4' not in response.get_data(as_text=True)

    logout(client)


def test_whoami_expired(client, expire_session, login, logout):
    """WhoAmI test cases - expired session"""
    login(client)

    expire_session(client)

    response = client.get('/api/whoami')
    assert response.status_code == 401

    logout(client)
