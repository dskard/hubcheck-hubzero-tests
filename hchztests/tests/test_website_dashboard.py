import unittest
import pytest
import datetime
import re

import hubcheck
from hubcheck.testcase import TestCase
from hubcheck.shell import ContainerManager


pytestmark = [ pytest.mark.website,
               pytest.mark.members_dashboard_mysession,
               pytest.mark.weekly,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade
             ]


class members_dashboard_my_session_storage(TestCase):

    def setUp(self):

        self.username,self.userpass = \
            self.testdata.find_account_for('purdueworkspace')

        # setup a web browser
        self.browser.get(self.https_authority)

        # navigate to the member dashboard page
        self.utils.account.login_as(self.username,self.userpass)

        self.po = self.catalog.load_pageobject('GenericPage')
        self.po.header.goto_myaccount()

        self.po = self.catalog.load_pageobject('MembersDashboardPage')

        self.my_sessions_module = self.po.modules.my_sessions


    @hubcheck.utils.hub_version(min_version='1.1.2')
    @pytest.mark.user_storage
    def test_storage_meter(self):
        """
        retrieve the free storage amount
        """

        storage_amount = self.my_sessions_module.storage.storage_meter()

        self.assertTrue(storage_amount != '',
            "invalid storage amount returned: %s" % (storage_amount))

        self.assertTrue(storage_amount != 'Error trying to retrieve disk usage',
            "invalid storage amount returned: %s" % (storage_amount))

        matches = re.match('(\d+)% of ([0-9.]+)([a-zA-Z]{2})',storage_amount)
        self.assertTrue(matches is not None,
            "invalid storage amount returned: \"%s\"" % (storage_amount))

        self.assertTrue(storage_amount != '0% of 0GB',
            "user quotas not activated: storage_amount = %s" % (storage_amount))

        (current,total,units) = matches.groups()
        self.assertTrue(total != '0',
            "storage amount total storage returned 0%s" % (units))


class members_dashboard_my_session_item(TestCase):

    def setUp(self):

        # start up a tool session container
        hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('purdueworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        # setup a web browser
        self.browser.get(self.https_authority)

        self.utils.account.login_as(self.username,self.userpass)

        self.po = self.catalog.load_pageobject('GenericPage')
        self.po.header.goto_myaccount()

        self.po = self.catalog.load_pageobject('MembersDashboardPage')

        self.my_sessions_module = self.po.modules.my_sessions


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()


    @hubcheck.utils.hub_version(min_version='1.1.4')
    @pytest.mark.session_quick_launch
    def test_quick_launch(self):
        """
        click the quick launch link to open a session
        """


        # grab the url of the dashboard page
        pageurl1 = self.po.current_url()

        # find the list item for our session
        session_item = self.my_sessions_module.get_session_by_position(0)

        self.assertTrue(session_item.quick_launch.is_displayed(),
            "members dashboard my_session widgets don't appear to"
            + " have a quick launch link.")

        session_item.quick_launch_session()

        # make sure the tool session page has loaded
        po = self.catalog.load_pageobject('ToolSessionPage')
        po.get_session_number()

        # grab the url of the tool session page
        pageurl2 = po.current_url()
        self.assertTrue(pageurl1 != pageurl2,
            "after clicking the quick launch link to open a session,"
            + " url did not change: pageurl1 = %s, pageurl2 = '%s'"
            % (pageurl1,pageurl2))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    @pytest.mark.session_item_toggle
    def test_slide_open_close(self):
        """
        check if the slide down window is working
        """

        session_item = self.my_sessions_module.get_session_by_position(0)

        is_open_1 = session_item.is_slide_open()
        session_item.toggle_slide()
        is_open_2 = session_item.is_slide_open()

        self.assertTrue(is_open_1 != is_open_2,
            "after toggling the slide down window,"
            + " the state of the window didn't change:"
            + " is_open_1 = %s, is_open_2 = %s"
            % (is_open_1,is_open_2))

        session_item.toggle_slide()
        is_open_3 = session_item.is_slide_open()

        self.assertTrue(is_open_1 == is_open_3,
            "after toggling the slide down window a second time,"
            + " the window didn't go back to it's original state:"
            + " is_open_1 = %s, is_open_3 = %s"
            % (is_open_1,is_open_3))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    @pytest.mark.session_item_last_accessed
    def test_get_last_accessed(self):
        """
        retrieve the last accessed date time stamp
        """

        session_item = self.my_sessions_module.get_session_by_position(0)
        (dt1,dt2) = session_item.get_last_accessed()

        self.assertTrue(dt1 is not None and dt1 != '',
            "invalid text date time stamp: dt1 = %s" % (dt1))
        self.assertTrue(type(dt2) == datetime.datetime,
            "invalid text date time stamp type: type(dt2) = %s" % (type(dt2)))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_resume_click(self):
        """
        click the resume session link
        """

        pageurl1 = self.po.current_url()

        session_item = self.my_sessions_module.get_session_by_position(0)

        resume_is_displayed = session_item.resume.is_displayed()
        self.assertTrue(resume_is_displayed,
            "in the members dashboard my_session module,"
            + " the open session item does not show a resume link")

        session_item.resume_session()

        pageurl2 = self.po.current_url()
        self.assertTrue(pageurl1 != pageurl2,
            "after clicking the resume link for session,"
            + " url did not change: pageurl1 = %s, pageurl2 = '%s'"
            % (pageurl1,pageurl2))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_terminate_click_dismiss(self):
        """
        is the terminate session link displayed
        """

        pageurl1 = self.po.current_url()
        num_sessions_1 = self.my_sessions_module.count_sessions()

        session_item = self.my_sessions_module.get_session_by_position(0)

        terminate_is_displayed = session_item.terminate.is_displayed()
        self.assertTrue(terminate_is_displayed,
            "in the members dashboard my_session module,"
            + " the open session item does not show a terminate link")

        session_item.terminate_session(confirm=False)

        # check that the session is still listed on the page

        num_sessions_2 = self.my_sessions_module.count_sessions()

        self.assertTrue(num_sessions_1 == num_sessions_2,
            "after not confirming the termination of a session"
            + " the number of open sessions changed from %d to %d"
            % (num_sessions_1,num_sessions_2))


class members_dashboard_my_session_item_2(TestCase):

    def setUp(self):

        # start up a tool session container
        self.hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('purdueworkspace')

        self.cm = ContainerManager()
        self.ws = self.cm.create(host=self.hubname,
                                 username=self.username,
                                 password=self.userpass)

        self.session_number,es = self.ws.execute('echo $SESSION')
        self.session_number = int(self.session_number)

        # setup a web browser
        self.browser.get(self.https_authority)

        self.utils.account.login_as(self.username,self.userpass)

        self.po = self.catalog.load_pageobject('GenericPage')
        self.po.header.goto_myaccount()

        self.po = self.catalog.load_pageobject('MembersDashboardPage')

        self.my_sessions_module = self.po.modules.my_sessions


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()
        # resync our session data because in the test,
        # we attempted to close a session being tracked by cm
        self.cm.sync_open_sessions(self.hubname,self.username)


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_terminate_click_accept(self):
        """
        click the terminate session link and accept the confirmation
        """

        pageurl1 = self.po.current_url()
        num_sessions_1 = self.my_sessions_module.count_sessions()

        session_item = self.my_sessions_module.get_session_by_session_number(
                        self.session_number)

        self.assertTrue(session_item is not None,
            'No session exists for session numbered: %s'
            % (self.session_number))

        # open the slide down window
        if not session_item.is_slide_open():
            session_item.toggle_slide()

        session_item.terminate_session(confirm=True)

        self.my_sessions_module = self.po.modules.my_sessions
        session_numbers = self.my_sessions_module.get_session_numbers()

        self.assertTrue(self.session_number not in session_numbers,
            "after confirming the termination of a session"
            + " the session %d still appears in the list of open sessions"
            % (self.session_number))


