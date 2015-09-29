import pytest

import hubcheck
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager


pytestmark = [ pytest.mark.website,
               pytest.mark.tool_session,
               pytest.mark.weekly,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade,
               pytest.mark.reboot,
             ]

class TestToolSessionApp(TestCase2):

    def setup_method(self,method):

        # start up a tool session container
        self.hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        self.cm = ContainerManager()
        self.ws = self.cm.access(host=self.hubname,
                                 username=self.username,
                                 password=self.userpass)

        self.session_number,es = self.ws.execute('echo $SESSION')
        self.ws.close()

        # setup a web browser
        self.browser.get(self.https_authority)

        self.utils.account.login_as(self.username,self.userpass)

        self.po = self.catalog.load_pageobject('ToolSessionPage',
                    'workspace',int(self.session_number))
        self.po.goto_page()


    def teardown_method(self,method):

        # get out of the workspace
        # shut down the ssh connection
        self.cm.sync_open_sessions(self.hubname,self.username)


    def test_terminate_container(self):
        """
        test pressing the terminate button on the app
        """

        # press the terminate button
        self.po.app.do_terminate()

        # check that the container terminated
        po = self.catalog.load_pageobject('MembersDashboardPage')
        po.goto_page()
        open_sessions = po.modules.my_sessions.get_session_numbers()

        assert int(self.session_number) not in open_sessions,\
            "after terminating session %s," % (self.session_number) \
            + " session still listed as open in my_sessions module"


    def test_keep_container(self):
        """
        test pressing the keep button on the app
        """

        # press the keep button
        self.po.app.do_keep()

        # check that the container is still open
        po = self.catalog.load_pageobject('MembersDashboardPage')
        po.goto_page()
        open_sessions = po.modules.my_sessions.get_session_numbers()

        assert int(self.session_number) in open_sessions,\
            "after keeping session %s," % (self.session_number) \
            + " session not listed as open in my_sessions module"


#    def test_popout_container(self):
#        """
#        test pressing the popout button on the app to popout the app
#        """
#
#        browser = self.browser._browser
#
#        # get current window info
#        url1 = browser.current_url
#        current_window = browser.current_window_handle
#
#        # press the popout button
#        self.po.app.do_popout()
#
#        # find the popup window
#        other_window = None
#        for w in browser.window_handles:
#            if w != current_window:
#                other_window = w
#
#        assert other_window is not None, \
#            "after pressing the popout button, no window popped out"
#
#
#    def test_popout_container_close(self):
#        """
#        test closing the popped out app does not end the session
#        """
#
#        browser = self.browser._browser
#
#        # get current window info
#        url1 = browser.current_url
#        current_window = browser.current_window_handle
#
#        # press the popout button
#        self.po.app.do_popout()
#
#        # find the popup window
#        other_window = None
#        for w in browser.window_handles:
#            if w != current_window:
#                other_window = w
#
#        assert other_window is not None, \
#            "after pressing the popout button, no window popped out"
#
#        # switch to the popup window
#        browser.switch_to_window(other_window)
#
#        # close the popup window
#        browser.close()
#        browser.switch_to_window(current_window)
#
#        # check that the container is still open
#        po = self.catalog.load_pageobject('MembersDashboardPage')
#        po.goto_page()
#        open_sessions = po.modules.my_sessions.get_session_numbers()
#
#        assert int(self.session_number) in open_sessions,\
#            "after closing popped out app," \
#            + " session %s not listed as open in my_sessions module" \
#            % (self.session_number)
#
#
#    def test_popout_container_popin(self):
#        """
#        test popping-in a popped out app
#        """
#
#        browser = self.browser._browser
#
#        # get current window info
#        url1 = browser.current_url
#        current_window = browser.current_window_handle
#
#        # press the popout button
#        self.po.app.do_popout()
#
#        # find the popup window
#        other_window = None
#        for w in browser.window_handles:
#            if w != current_window:
#                other_window = w
#
#        assert other_window is not None, \
#            "after pressing the popout button, no window popped out"
#
#        # pop the container back in the browser
#        self.po.app.do_popout()
#
#        # make sure the popped-out window closes
#        other_window = None
#        for w in browser.window_handles:
#            if w != current_window:
#                other_window = w
#
#        assert other_window is None, \
#            "after pressing the 'pop in' button," \
#            + " the popped out window still exists"
#
#        # check that the container is still open
#        po = self.catalog.load_pageobject('MembersDashboardPage')
#        po.goto_page()
#        open_sessions = po.modules.my_sessions.get_session_numbers()
#
#        assert int(self.session_number) in open_sessions,\
#            "after popping in the tool session container app," \
#            + " session %s not listed as open in my_sessions module" \
#            % (self.session_number)


    @hubcheck.utils.hub_version(min_version='1.1.2')
    @pytest.mark.user_storage
    def test_storage_meter(self):
        """
        retrieve the free storage amount
        """

        storage_amount = self.po.app.storage.storage_meter()

        assert storage_amount != '', \
            "invalid storage amount returned: %s" % (storage_amount)

        assert storage_amount != '0% of 0GB', \
            "user quotas not activated: storage_amount = %s" % (storage_amount)


class TestToolSessionShare(TestCase2):

    def setup_method(self,method):

        # start up a tool session container
        self.hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        self.cm = ContainerManager()
        self.ws = self.cm.access(host=self.hubname,
                                 username=self.username,
                                 password=self.userpass)

        self.session_number,es = self.ws.execute('echo $SESSION')
        self.ws.close()

        # setup a web browser
        self.browser.get(self.https_authority)

        self.utils.account.login_as(self.username,self.userpass)

        self.po = self.catalog.load_pageobject('ToolSessionPage',
                    'workspace',int(self.session_number))
        self.po.goto_page()


    def teardown_method(self,method):

        # disconnect all users from workspace

        self.po.goto_page()
        self.po.share.disconnect_all()


    def test_share_session_with_1(self):
        """
        test sharing the session with nobody
        """

        shared_with_1 = self.po.share.get_shared_with()

        self.po.share.share.click()
        self.po.share.wait_for_overlay()

        shared_with_2 = self.po.share.get_shared_with()

        assert len(shared_with_1) == len(shared_with_2), \
            "after pressing the share button, shared list changed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)

        s1 = set(shared_with_1)
        s2 = set(shared_with_2)
        s_union = s1 | s2

        assert len(s_union) == len(shared_with_1), \
            "after pressing the share button, shared list changed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)


    def test_share_session_with_2(self):
        """
        test sharing the session with another user
        """

        shared_with_1 = self.po.share.get_shared_with()

        username2,junk = \
            self.testdata.find_account_for('purdueworkspace')
        user2_data = self.testdata.get_userdata_for(username2)
        user2_name = '{0} {1}'.format(user2_data.firstname,user2_data.lastname)

        self.po.share.share_session_with(username2)

        shared_with_2 = self.po.share.get_shared_with()

        assert len(shared_with_1)+1 == len(shared_with_2), \
            "after sharing the session, wrong # users listed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)

        assert user2_name in shared_with_2, \
            "after sharing session with %s, user %s" % (username2,user2_name) \
            + " does not show up in shared with list: %s" % (shared_with_2)


    def test_share_session_with_3(self):
        """
        test sharing the session with a fake user
        """

        shared_with_1 = self.po.share.get_shared_with()

        self.po.share.share_session_with('fakeuserthatshouldnotexist')

        shared_with_2 = self.po.share.get_shared_with()

        assert len(shared_with_1) == len(shared_with_2), \
            "after sharing the session with a fake user, shared list changed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)

        s1 = set(shared_with_1)
        s2 = set(shared_with_2)
        s_union = s1 | s2

        assert len(s_union) == len(shared_with_1), \
            "after sharing the session with a fake user, shared list changed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)


#    def test_share_session_with_4(self):
#        """
#        test sharing the session with a group
#        """
#
#        self.po.share.share_session_with(group=0)


#    def test_share_session_with_5(self):
#        """
#        test sharing the session with another user, read only
#        """
#
#        shared_with_1 = self.po.share.get_shared_with()
#
#        username2,junk = \
#            self.testdata.find_account_for('purdueworkspace')
#        user2_data = self.testdata.get_userdata_for(username2)
#        user2_name = '{0} {1}'.format(user2_data.firstname,user2_data.lastname)

#        self.po.share.share_session_with(username2,readonly=True)
#
#        shared_with_2 = self.po.share.get_shared_with()
#
#        assert len(shared_with_1)+1 == len(shared_with_2), \
#            "after sharing the session, wrong # users listed: " \
#            + "before: %s, after: %s" % (shared_with_1,shared_with_2)
#
#        assert user2_name in shared_with_2, \
#            "after sharing session with %s, user %s" % (username2,user2_name) \
#            + " does not show up in shared with list: %s" % (shared_with_2)
#
#        # check if the user was added to the list with the "read only" property


    def test_share_session_with_6(self):
        """
        test sharing the session with another user twice

        user should only show up once in list
        """

        shared_with_1 = self.po.share.get_shared_with()

        username2,junk = \
            self.testdata.find_account_for('purdueworkspace')
        user2_data = self.testdata.get_userdata_for(username2)
        user2_name = '{0} {1}'.format(user2_data.firstname,user2_data.lastname)

        self.po.share.share_session_with(username2)
        self.po.share.share_session_with(username2)

        shared_with_2 = self.po.share.get_shared_with()

        assert len(shared_with_1)+1 == len(shared_with_2), \
            "after sharing the session, wrong # users listed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)

        assert user2_name in shared_with_2, \
            "after sharing session with %s, user %s" % (username2,user2_name) \
            + " does not show up in shared with list: %s" % (shared_with_2)


    def test_share_session_with_7(self):
        """
        test sharing the session with multiple users
        """

        shared_with_1 = self.po.share.get_shared_with()

        username2,junk = \
            self.testdata.find_account_for('purdueworkspace')
        user2_data = self.testdata.get_userdata_for(username2)
        user2_name = '{0} {1}'.format(user2_data.firstname,user2_data.lastname)

        username3,junk = \
            self.testdata.find_account_for('networkworkspace')
        user3_data = self.testdata.get_userdata_for(username3)
        user3_name = '{0} {1}'.format(user3_data.firstname,user3_data.lastname)

        self.po.share.share_session_with([username2,username3])

        shared_with_2 = self.po.share.get_shared_with()

        assert len(shared_with_1)+2 == len(shared_with_2), \
            "after sharing the session, wrong # users listed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)

        assert user2_name in shared_with_2, \
            "after sharing session with %s, user %s" % (username2,user2_name) \
            + " does not show up in shared with list: %s" % (shared_with_2)

        assert user3_name in shared_with_2, \
            "after sharing session with %s, user %s" % (username3,user3_name) \
            + " does not show up in shared with list: %s" % (shared_with_2)


    def test_share_session_with_8(self):
        """
        test sharing the session with multiple users, one at a time
        """

        shared_with_1 = self.po.share.get_shared_with()

        username2,junk = \
            self.testdata.find_account_for('purdueworkspace')
        user2_data = self.testdata.get_userdata_for(username2)
        user2_name = '{0} {1}'.format(user2_data.firstname,user2_data.lastname)

        username3,junk = \
            self.testdata.find_account_for('networkworkspace')
        user3_data = self.testdata.get_userdata_for(username3)
        user3_name = '{0} {1}'.format(user3_data.firstname,user3_data.lastname)

        self.po.share.share_session_with([username2])
        self.po.share.share_session_with([username3])

        shared_with_2 = self.po.share.get_shared_with()

        assert len(shared_with_1)+2 == len(shared_with_2), \
            "after sharing the session, wrong # users listed: " \
            + "before: %s, after: %s" % (shared_with_1,shared_with_2)

        assert user2_name in shared_with_2, \
            "after sharing session with %s, user %s" % (username2,user2_name) \
            + " does not show up in shared with list: %s" % (shared_with_2)

        assert user3_name in shared_with_2, \
            "after sharing session with %s, user %s" % (username3,user3_name) \
            + " does not show up in shared with list: %s" % (shared_with_2)


    def test_disconnect_1(self):
        """
        test disconnecting a connected user from a tool session container
        """

        shared_with_1 = self.po.share.get_shared_with()

        username2,junk = \
            self.testdata.find_account_for('purdueworkspace')
        user2_data = self.testdata.get_userdata_for(username2)
        user2_name = '{0} {1}'.format(user2_data.firstname,user2_data.lastname)

        # share the session with someone
        self.po.share.share_session_with(username2)

        shared_with_2 = self.po.share.get_shared_with()

        assert user2_name in shared_with_2, \
            "after sharing session with %s, user does" % (username2) \
            + " not show up in shared with list %s" % (shared_with_2)

        # disconnect user from session
        self.po.share.disconnect(username2)

        # check that user was disconnected
        shared_with_3 = self.po.share.get_shared_with()

        assert user2_name not in shared_with_3, \
            "after unsharing session with %s, user %s" \
            % (username2, user2_name) \
            + " still shows up in shared with list: %s" \
            % (shared_with_3)

