"""TEST CASES - INDEX"""

import unittest
import xmlrunner

import test_utils
from vsm import app


class VSMIndexTestCase(unittest.TestCase):
    """Test cases for the Index page"""
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_index(self):
        """Index page test - logged in"""
        test_utils.login(self.client)

        # Get the index page after being authenticated
        response = self.client.get('/')
        assert response.status_code == 200
        assert 'Logged in as: testuser' in response.get_data(as_text=True)
        assert 'Download VPN Server Configuration' in response.get_data(as_text=True)
        assert 'myserver' in response.get_data(as_text=True)
        assert 'myserver2' in response.get_data(as_text=True)
        assert 'myserver3' in response.get_data(as_text=True)
        assert 'myserver4' not in response.get_data(as_text=True)

        test_utils.logout(self.client)

    def test_index_expired(self):
        """Index page test - Expired session"""
        test_utils.login(self.client)

        test_utils.expire_session(self.client)

        response = self.client.get('/')
        assert response.status_code == 302
        assert response.headers['Location'] == '/auth/login'

        test_utils.logout(self.client)

if __name__ == '__main__':
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        failfast=False, buffer=False, catchbreak=False
    )
