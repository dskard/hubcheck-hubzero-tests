import pytest
import hubcheck


pytestmark = [ pytest.mark.website,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade
             ]


class TestHubLogin(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        # setup a web browser
        self.browser.get(self.https_authority)


    @pytest.mark.login
    def test_hub_login(self):
        """
        try to login to the hub website
        """

        self.utils.account.login_as(self.username,self.userpass)

        # verify you have successfully logged in
        po = self.catalog.load_pageobject('GenericPage')
        assert po.header.is_logged_in(),'Login Failed'


    @pytest.mark.logout
    def test_hub_logout(self):
        """
        try to login and logout of the hub website
        """

        self.utils.account.login_as(self.username,self.userpass)

        # verify you have successfully logged in
        po = self.catalog.load_pageobject('GenericPage')
        assert po.header.is_logged_in(),'Login Failed'

        # logout of the website
        po.header.goto_logout()

        # po = self.catalog.load_pageobject('GenericPage')
        assert not po.header.is_logged_in(),'Logout Failed'


    def test_https_to_http_logout(self):
        """
        check if requesting an http website after visiting
        an http web page logs the user out of the website.
        hubzero ticket #7247
        """

        self.utils.account.login_as(self.username,self.userpass)

        # verify you have successfully logged in
        po = self.catalog.load_pageobject('GenericPage')
        assert po.header.is_logged_in(),'Login Failed'

        # request an http web page
        self.browser.get(self.http_authority)

        # check if the user is still logged in
        assert po.header.is_logged_in(),'Login Failed'
