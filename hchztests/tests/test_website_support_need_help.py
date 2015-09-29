import pytest
import sys
import os
import re

import hubcheck


pytestmark = [ pytest.mark.website,
               pytest.mark.tickets,
               pytest.mark.need_help,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade
             ]


class TestNeedHelp(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        # setup a web browser
        self.browser.get(self.https_authority)

        # get user account info
        self.username,self.password = \
            self.testdata.find_account_for('ticketsubmitter')
        self.adminuser,self.adminpass = \
            self.testdata.find_account_for('ticketmanager')

        self.ticket_number = None


    def teardown_method(self,method):

        # if we created a ticket, delete the ticket
        if self.ticket_number is not None \
            and (self.adminuser != "") \
            and (self.adminpass != ""):

            try:
                self.utils.account.logout()
            except:
                pass

            self.utils.account.login_as(self.adminuser,self.adminpass)
            self.utils.support.close_support_ticket_invalid(self.ticket_number)


    def test_link_exists(self):
        """
        click the need help link, to see if the widget exists
        """

        po = self.catalog.load_pageobject('SupportNeedHelpPage')
        po.open()
        po.close()


    @pytest.mark.nt
    def test_link_changes_webpage(self):
        """
        click the need help link, check if the url changes
        """

        po = self.catalog.load_pageobject('GenericPage')
        start_url = po.current_url()
        po.toggle_needhelp()
        end_url = po.current_url()

        assert start_url == end_url, "clicking the 'Need Help?' link" \
             + " changed the web page from %s to %s" % (start_url,end_url)


    def test_if_link_leads_to_support_url(self):
        """
        open the "Need Help?" dialogue to ensure it does not lead to
        /support

        Sometime found when javascript is turned off, but if javascript
        is on, clicking this link should not send the user to the
        /support webpage.

        """

        # store the start and end page url's for comparison
        # click the needhelp link and see if it takes us to /support
        po = self.catalog.load_pageobject('SupportNeedHelpPage')
        startpageurl = po.current_url()
        po.open()
        endpageurl = po.current_url()

        assert startpageurl == endpageurl, \
            "User was redirected to %s\n" % endpageurl

        # FIXME: use urlparse here
        # create a pattern for a url regular expression
        p = re.compile('(([^:]+)://)?([^:/]+)(:([0-9]+))?(/.*)?')
        (junk, junk, junk, junk, junk, path) = p.search(endpageurl).groups()

        # check that the page we were taken to is not /support
        s = "pageurl = %s\npath = %s\n" % (endpageurl,path)
        assert path != '/support', s


    def test_submit_ticket_logged_in_using_need_help_link(self):
        """
        login to the website as the "ticket submitter" and submit a
        ticket using the need help link.
        """

        problem = 'hubcheck test ticket\n%s' % (self.fnbase)

        # login to the website and click the need help link
        self.utils.account.login_as(self.username,self.password)
        po = self.catalog.load_pageobject('SupportNeedHelpPage')
        po.open()

        # fill in the trouble report
        # username, name, and email fields are
        # not accessible while logged in
        self.ticket_number = po.submit_ticket({'problem':problem})

        # check if the ticket number is a valid number
        assert self.ticket_number is not None, "no ticket number returned"
        assert re.match('\d+',self.ticket_number) is not None, \
            "cound not find a matching ticket number in '%s'" \
            % (self.ticket_number)

        # convert to a number and ensure it is not ticket #0
        assert int(self.ticket_number) > 0, \
            "invalid ticket number returned: %s" % (self.ticket_number)


    @pytest.mark.captcha
    def test_submit_ticket_logged_out_using_need_help_link(self):
        """
        submit a support ticket using the need help link while not
        logged into the website.
        """


        # data for trouble report
        data = {
            'name'         : 'hubcheck testuser',
            'email'        : 'hubchecktest@hubzero.org',
            'problem'      : 'hubcheck test ticket\n%s' % (self.fnbase),
            'captcha'      : True,
        }

        # navigate to the SupportNeedHelp Page:
        po = self.catalog.load_pageobject('SupportNeedHelpPage')
        po.open()

        # fill in the trouble report
        # username is optional
        self.ticket_number = po.submit_ticket(data)

        # check if the ticket number is a valid number
        assert self.ticket_number is not None, \
            "no ticket number returned"
        assert re.match('\d+',self.ticket_number) is not None, \
            "cound not find a matching ticket number in '%s'" \
            % (self.ticket_number)

        # convert to a number and ensure it is not ticket #0
        assert int(self.ticket_number) > 0, \
            "invalid ticket number returned: %s" % (self.ticket_number)


    @pytest.mark.tickets_attach_jpg
    def test_attaching_jpg_image_to_ticket_submitted_through_need_help(self):
        """
        Login to the website and submit a ticket, using the need help
        link, with an attached jpeg image.
        """

        problem = 'hubcheck test ticket\nattaching jpg image\n%s' \
            % (self.fnbase)

        uploadfilename = 'app2.jpg'
        uploadfilepath = os.path.join(self.datadir,'images',uploadfilename)
        data = {
            'problem'   : problem,
            'upload'    : uploadfilepath,
        }

        # login to the website and navigate to the need help form
        self.utils.account.login_as(self.username,self.password)
        po = self.catalog.load_pageobject('SupportNeedHelpPage')
        # po.open()
        po.needhelplink.click()

        # submit a trouble report
        # username, name, and email fields are not accessible
        self.ticket_number = po.submit_ticket(data)

        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, \
            "invalid ticket number returned: %s" % (self.ticket_number)
        po.goto_ticket()

        po = self.catalog.load_pageobject('SupportTicketViewPage')
        content = po.get_ticket_content()
        imgsrc = content.download_image(uploadfilename)

        # not sure how to really download image files yet.
        # so we assume that as long as opening the image didn't
        # cause an error, the test passed.

        assert re.search(uploadfilename,imgsrc) is not None, \
            "After uploading an image to support ticket" \
            + " #%s, could not download image %s" \
            % (self.ticket_number,uploadfilename)
