import pytest

import hubcheck
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager


pytestmark = [
               pytest.mark.hc_account_setup,
             ]


class TestWebsite(TestCase2):

    def setup_method(self,method):

        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        # setup a web browser
        self.browser.get(self.https_authority)


    def test_hub_login_test_accounts(self):
        """
        try to login to the hub website with each of the test accounts
        """

        failed_logins = []
        errors = []

        for username in self.testdata.get_usernames():
            userpass = self.testdata.find_account_password(username)

            logout = False
            try:
                self.utils.account.login_as(username,userpass)

                # verify you have successfully logged in
                po = self.catalog.load_pageobject('GenericPage')
                assert po.header.is_logged_in(),'Login Failed'

                logout = True

                # check if the password is expired by trying
                # to access web elements on the support ticket page.
                # if the password is expired, or there is some other
                # problem with the account, we won't be able to leave
                # the initial greeting page. An exception will be
                # raised when trying to interact with the missing elements.
                po = self.catalog.load_pageobject('SupportTicketNewPage')
                po.goto_page()
                assert po.ticketform.name.is_displayed() and \
                       po.ticketform.email.is_displayed() and \
                       po.ticketform.problem.is_displayed(), \
                       'Not on SupportTicketNewPage'
            except Exception as e :
                self.logger.exception(e)
                errors.append(e)
                failed_logins.append(username)
            finally:
                if logout:
                    try:
                        # logout of the website
                        po.header.goto_logout()
                    except:
                        pass


        assert len(failed_logins) == 0, \
            'login failed for the following accounts: %s,%s' % (failed_logins,errors)


class TestWorkspaceUser(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.hubname = self.testdata.find_url_for('https')

        # access a tool session container
        self.cm = ContainerManager()


    def teardown_method(self,method):

        pass


    def test_workspace_access(self):
        """
        the hc accounts specified as being in the mw-login group
        should be able to ssh into a workspace using virtual ssh
        """

        failed_logins = []

        for username in self.testdata.get_usernames():
            userdata = self.testdata.get_userdata_for(username)

            if 'mw-login' not in userdata.admin_properties.groups:
                continue

            ws = None

            try:
                ws = self.cm.access(host=self.hubname,
                                    username=userdata.username,
                                    password=userdata.password)

                sessiondir = ws.execute('echo $SESSIONDIR')

            except:
                failed_logins.append(userdata.username)

            finally:
                if ws is not None:
                    ws.close()
                    ws = None


        assert len(failed_logins) == 0, \
            'login failed for the following accounts: %s' % (failed_logins)


class TestAppsUserSetup(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = \
            self.testdata.find_account_for('appsworkspace')
        hubname = self.testdata.find_url_for('https')

        # access a tool session container
        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        self.sessiondir = self.ws.execute('echo $SESSIONDIR')


    def teardown_method(self,method):

        # exit the workspace
        self.ws.close()


    def test_sudo_apps(self):
        """
        the hc account specified as the apps user
        should be able to 'sudo su - apps'
        """

        exit_apps = False
        try:
            # become the apps user
            self.ws.send('sudo su - apps')
            self.ws.start_bash_shell()
            output,es = self.ws.execute('whoami')
            exit_apps = True
            assert output == 'apps', \
                "doesn't look like we were able to become the apps user"
        finally:
            self.ws.stop_bash_shell()
            if exit_apps:
                self.ws.send('exit')


