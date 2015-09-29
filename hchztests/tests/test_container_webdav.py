import unittest
import pytest
import sys
import time
import hubcheck

from webdav import WebdavClient
from webdav.Connection import WebdavError,AuthorizationError


pytestmark = [ pytest.mark.container,
               pytest.mark.webdav,
               pytest.mark.nightly,
               pytest.mark.reboot
             ]


# sleep for 15 minutes to avoid fail2ban related errors
SLEEPTIME=60*15

@pytest.mark.registereduser
class container_webdav(hubcheck.testcase.TestCase):


    def setUp(self):

        # get user account info
        self.username,self.userpass = self.testdata.find_account_for(
                                        'registeredworkspace')
        webdav_base = self.testdata.find_url_for('webdav')

        self.webdav_url = 'https://%s/webdav' % webdav_base

        self.do_sleep = True


    @pytest.mark.webdav_login
    def test_valid_user_valid_password_login(self):
        """
        try webdav login with valid user and valid password

        """

        c = WebdavClient.CollectionStorer(self.webdav_url)
        c.connection.addBasicAuthorization(self.username,self.userpass)
        try:
            c.validate()
            # successful login does not require sleep
            self.do_sleep = False
        except AuthorizationError, e:
            self.fail("webdav login to %s as %s failed: %s"
                % (self.webdav_url,self.username,e))


    def test_invalid_user_login(self):
        """
        try webdav login with an invalid user

        """

        c = WebdavClient.CollectionStorer(self.webdav_url)
        c.connection.addBasicAuthorization('invaliduser','invalidpass')
        with self.assertRaises(WebdavError) as cm:
            c.validate()


    def test_valid_user_invalid_passwordlogin(self):
        """
        try webdav login with a valid user and invalid password

        """

        c = WebdavClient.CollectionStorer(self.webdav_url)
        c.connection.addBasicAuthorization(self.username,'invalidpass')
        with self.assertRaises(AuthorizationError) as cm:
            c.validate()


    def tearDown(self):

        if self.do_sleep:
            time.sleep(SLEEPTIME)
