"""TEST CASES - SERVER API"""

import unittest
import xmlrunner

import test_utils
from vsm import app


class VSMServerTestCase(unittest.TestCase):
    """Test cases for generating server configuration files"""
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_get_server_config(self):
        """Server config test case - valid config response"""
        test_utils.login(self.client)

        response = self.client.get('/api/servers/myserver')
        assert response.status_code == 200
        assert 'dev tun' in response.get_data(as_text=True)

        test_utils.logout(self.client)

    def test_get_server_config_expired(self):
        """Server config test case - expired user is redirected to login"""
        test_utils.login(self.client)
        test_utils.expire_session(self.client)

        response = self.client.get('/api/servers/myserver')
        assert response.status_code == 302
        assert response.headers['Location'] == '/auth/login'

        test_utils.logout(self.client)

    def test_get_server_config_not_logged_in(self):
        """Server config test case - not logged in redirects to /"""
        response = self.client.get('/api/servers/myserver')
        assert response.status_code == 302
        assert response.headers['Location'] == '/'

    def test_get_server_config_invalid_server(self):
        """Server config test case - invalid server choice redirects to /"""
        test_utils.login(self.client)

        response = self.client.get('/api/servers/mybadserver')
        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        test_utils.logout(self.client)

    def test_get_server_config_denied_server(self):
        """Server config test case - access denied is redirected to /"""
        test_utils.login(self.client)

        response = self.client.get('/api/servers/myserver4')
        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        test_utils.logout(self.client)


if __name__ == '__main__':
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        failfast=False, buffer=False, catchbreak=False
    )
