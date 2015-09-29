import hubcheck
import pytest
import time
import string
import random

pytestmark = [ pytest.mark.website,
               pytest.mark.groups,
               pytest.mark.upgrade,
             ]

@pytest.mark.weekly
@pytest.mark.prod_safe_upgrade
class TestGroupsPage(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)

        GroupsPage = self.catalog.load('GroupsPage')
        self.po = GroupsPage(self.browser,self.catalog)
        self.po.goto_page()


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_version(min_version='1.1.5'),
        reason="hub version falls outside of valid range for this test")
    def test_blank_groups_need_help_page(self):
        """
        check that the "need help" link takes users to a non blank page
        """

        browser = self.browser._browser

        # get current window info
        url1 = browser.current_url
        current_window = browser.current_window_handle

        # click the need help link
        self.po.groups.goto_need_help()

        # find the popup window
        other_window = None
        for w in browser.window_handles:
            if w != current_window:
                other_window = w

        # switch to the popup window
        if other_window is not None:
            browser.switch_to_window(other_window)

        # get the text from the page
        url2 = browser.current_url
        html = browser.find_element_by_css_selector('html').text

        # close the popup window
        browser.close()

        if other_window is not None:
            browser.switch_to_window(current_window)

        assert html != "", \
            "clicking the 'need help' link on " \
            + "%s leads users to the blank page %s" % (url1,url2)


class TestGroupsCreate(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)

        self.username,self.password = \
            self.testdata.find_account_for('registeredworkspace')

        self.utils.account.login_as(self.username,self.password)
        GroupsNewPage = self.catalog.load('GroupsNewPage')
        self.po = GroupsNewPage(self.browser,self.catalog)
        self.po.goto_page()


    def test_group_create_form_missing_required(self):
        """
        try to submit the form with no data
        """

        self.po.create_group({})

        info = self.po.get_error_info()
        assert len(info) > 0, \
            "missing error messages after submitting" \
            + " blank create group form"


    def test_group_create_form_valid_data(self):
        """
        try to submit the form with data
        """

        groupid = "h%d" % (time.time())
        data = {
            'groupid'       : groupid,
            'title'         : "hubcheck unit test groups new page %s" % (groupid),
            'tags'          : ['hubcheck','hc'],
            'public_desc'   : 'hubcheck unit test public description',
            'private_desc'  : 'hubcheck unit test private description',
            'join_policy'   : 'Invite Only',
            'privacy'       : 'Hidden',
        }
        self.po.create_group(data)

        info = self.po.get_error_info()
        assert len(info) == 0, \
            "received unexpected error while creating group: %s" \
            % (info)

        info = self.po.get_success_info()
        assert len(info) > 0, \
            "missing success info message after creating group named %s" \
            % (groupid)


# we leave the single character test out because it will end up
# failing pretty often the more it is run
#        (''.join([random.choice(string.ascii_lowercase)
#            for i in range(1)])),

    @pytest.mark.parametrize("groupid",[
        (''.join([random.choice(string.ascii_lowercase)
            for i in range(10)])),
        ('h'+''.join([random.choice(string.digits)
            for i in range(10)])),
        ('h_'+''.join([random.choice(string.ascii_lowercase+string.digits+'_')
            for i in range(10)])),
        ('h'+''.join([random.choice(string.ascii_lowercase+string.digits+'_')
            for i in range(10)])+'_'),
    ])
    def test_group_create_form_groupid_valid(self,groupid):
        """
        try to submit the form with different alphanumeric characters
        """

        # groupid = groupid.lower()
        data = {
            'groupid'       : groupid,
            'title'         : "hubcheck unit test groups new page %s" % (groupid),
            'tags'          : ['hubcheck','hc'],
            'public_desc'   : 'hubcheck unit test public description',
            'private_desc'  : 'hubcheck unit test private description',
            'join_policy'   : 'Invite Only',
            'privacy'       : 'Hidden',
        }
        self.po.create_group(data)

        info = self.po.get_error_info()
        assert len(info) == 0, \
            "received unexpected error while creating group: %s" \
            % (info)

        info = self.po.get_success_info()
        assert len(info) > 0, \
            "missing success info message after creating group named %s" \
            % (groupid)
