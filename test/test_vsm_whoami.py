import unittest

import test_utils
from vsm import app


class VSMIndexTestCase(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_whoami_not_loggedin(self):
        response = self.client.get('/api/whoami')
        assert response.status_code == 401

    def test_whoami_loggedin(self):
        test_utils.login(self.client)

        response = self.client.get('/api/whoami')
        assert response.status_code == 200
        assert 'testuser' in response.get_data(as_text=True)
        assert 'myserver' in response.get_data(as_text=True)
        assert 'myserver2' in response.get_data(as_text=True)
        assert 'myserver3' in response.get_data(as_text=True)
        assert 'myserver4' not in response.get_data(as_text=True)

        test_utils.logout(self.client)


    def test_whoami_expired(self):
        test_utils.login(self.client)

        test_utils.expire_session(self.client)

        response = self.client.get('/api/whoami')
        assert response.status_code == 401

        test_utils.logout(self.client)


if __name__ == '__main__':
    unittest.main()
