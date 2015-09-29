import pytest
import os
import re
import hubcheck


pytestmark = [ pytest.mark.website,
               pytest.mark.tickets,
               pytest.mark.report_problems,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade
             ]


class TestReportProblems(hubcheck.testcase.TestCase2):

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


    def test_new_submit_logged_in_defaults(self):
        """
        login and submit a ticket with the default values populated
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        # submit an empty ticket with defaults filled in
        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()
        po.submit_ticket({})

        # we expect 2 error boxes, missing fields and missing description
        info = po.get_error_info()
        assert len(info) == 2, \
            "while populating required field, expected 2 errors, received %s" \
            % (info)


    def test_new_submit_logged_in_required(self):
        """
        login and submit a ticket with the required values populated
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        data = {
            'name'         : self.username,
            'email'        : 'hubchecktest@hubzero.org',
            'problem'      : "hubcheck test ticket\n%s" % (self.fnbase),
        }

        # submit the ticket
        po.submit_ticket(data)

        po = self.catalog.load_pageobject('SupportTicketSavePage')
        self.ticket_number = po.get_ticket_number()

        info = po.get_error_info()
        assert len(info) == 0, "received unexpected error: %s" % (info)
        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, \
            "invalid ticket number returned: %s" % (self.ticket_number)


    def test_new_submit_logged_in_missing_name(self):
        """
        login and submit a ticket with the required name field missing
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        # clear out the name field
        # po.name.value = "%s" % ""*len(po.name.value)
        data = {
            'name'         : ' ',
            'email'        : 'hubchecktest@hubzero.org',
            'problem'      : "hubcheck test ticket\n%s" % (self.fnbase),
        }

        # submit the ticket
        po.submit_ticket(data)
        info = po.get_error_info()
        assert len(info) > 0, "No error info found after submitting a" \
            + " support ticket with no name"


    def test_new_submit_logged_in_missing_email(self):
        """
        login and submit a ticket with the required email field missing
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        # clear out the email field
        # po.email.value = "%s" % ""*len(po.email.value)
        data = {
            'name'         : self.username,
            'email'        : ' ',
            'problem'      : "hubcheck test ticket\n%s" % (self.fnbase),
        }

        # submit the ticket
        po.submit_ticket(data)
        info = po.get_error_info()
        assert len(info) > 0, "No error info found after submitting a" \
            + " support ticket with no email address"


    def test_new_submit_logged_in_missing_detail(self):
        """
        login and submit a ticket with the required detail field missing
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        # clear out the problem field
        # po.detail.value = "%s" % ""*len(po.detail.value)
        data = {
            'name'         : self.username,
            'email'        : 'hubchecktest@hubzero.org',
            'problem'      : ' ',
        }

        # submit the ticket
        po.submit_ticket(data)
        info = po.get_error_info()
        assert len(info) > 0, "No error info found after submitting a" \
            + " support ticket with no problem text"


    def test_new_submit_logged_in_invalid_email(self):
        """
        login and submit a ticket with an invalid email address
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        # invalid email address
        # po.email.value = 'ktest@hero.orgtest@huro.org'
        data = {
            'name'         : self.username,
            'email'        : 'ktest@hero.orgtest@huro.org',
            'problem'      : "hubcheck test ticket\n%s" % (self.fnbase),
        }

        # submit the ticket
        po.submit_ticket(data)
        info = po.get_error_info()
        assert len(info) > 0, "No error info found after submitting a" \
            + " support ticket with an invalid email address"


    @pytest.mark.vhub_457
    def test_page_error_juser(self):
        """
        login and submit a ticket with the default values populated

        vhub.org ticket #457
        needs read access in acl to see error
        or have tickets in the queue
        error  is "juser::_load:"
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()
        problem_text = 'hubcheck test ticket\n%s' % (self.fnbase)
        po.submit_ticket({'problem' : problem_text})

        info = po.get_error_info()
        assert len(info) == 0, "unexpected error received: %s" % (info)

        po = self.catalog.load_pageobject('SupportTicketSavePage')
        self.ticket_number = po.get_ticket_number()

        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, \
            "ticket number = '%s'" % self.ticket_number

        po.goto_tracking_system()

        # we should see no error boxes
        po = self.catalog.load_pageobject('SupportTicketSearchPage')

        info = po.get_error_info()
        assert len(info) == 0, \
            "Searching for support ticket resulted in errors: %s" % (info)


    @pytest.mark.ticket_status
    def test_submitter_status_waiting(self):
        """
        as ticket submitter, try changing the status of a support
        ticket to "Awaiting user action"
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        # submit a ticket
        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()
        problem_text = 'hubcheck test ticket\n%s' % (self.fnbase)
        po.submit_ticket({'problem' : problem_text})

        po = self.catalog.load_pageobject('SupportTicketSavePage')
        self.ticket_number = po.get_ticket_number()
        po.goto_logout()



        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, "Submitting a support ticket" \
            + " returned ticket number: %s" % (self.ticket_number)

        # login to the website as a ticket submitter
        self.utils.account.login_as(self.username,self.password)

        # change the ticket status
        # we also add a comment so the status change
        # is not hidden from the ticket submitter
        po = self.catalog.load_pageobject('SupportTicketViewPage',
                self.ticket_number)
        po.goto_page()
        comment_data = {
            'comment'   : 'comment',
            'status'    : 'Awaiting user action'
        }
        po.add_comment(comment_data)

        # get the ticket status from the comment form.
        current_url = po.current_url()
        status = po.get_ticket_status()
        assert status == "Open", \
            "After changing the status of support ticket" \
            + " #%s (%s) status = '%s', expected '%s'" \
            % (self.ticket_number,current_url,status,comment_data['status'])

        # retrieve the last comment
        # check the ticket comment's changelog for the status change
        comment = po.get_nth_comment(-1)
        assert comment.is_new_status_waiting() is False, \
            "After changing the status of support ticket" \
            + " #%s (%s) comment status = '%s', expected 'accepted'" \
            % (self.ticket_number,current_url,comment.get_status_changes()[1])



    @pytest.mark.ticket_status
    def test_manager_status_waiting(self):
        """
        as ticket manager, try changing the status of a support
        ticket to "Awaiting user action"
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        # submit a ticket
        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()
        problem_text = 'hubcheck test ticket\n%s' % (self.fnbase)
        po.submit_ticket({'problem' : problem_text})

        po = self.catalog.load_pageobject('SupportTicketSavePage')
        self.ticket_number = po.get_ticket_number()
        po.goto_logout()



        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, "Submitting a support ticket" \
            + " returned ticket number: %s" % (self.ticket_number)

        # login to the website as a ticket manager
        self.utils.account.login_as(self.adminuser,self.adminpass)

        # change the ticket status
        # we also add a comment so the status change
        # is not hidden from the ticket submitter
        po = self.catalog.load_pageobject('SupportTicketViewPage',
                self.ticket_number)
        po.goto_page()
        comment_data = {
            'comment'   : 'comment',
            'status'    : 'Awaiting user action'
        }
        po.add_comment(comment_data)

        # get the ticket status from the comment form.
        current_url = po.current_url()
        status = po.get_ticket_status()
        assert status == comment_data['status'], \
            "After changing the status of support ticket" \
            + " #%s (%s) status = '%s', expected '%s'" \
            % (self.ticket_number,current_url,status,comment_data['status'])

        # retrieve the last comment
        # check the ticket comment's changelog for the status change
        comment = po.get_nth_comment(-1)
        assert comment.is_new_status_waiting() is True, \
            "After changing the status of support ticket" \
            + " #%s (%s) comment status = '%s', expected 'waiting'" \
            % (self.ticket_number,current_url,comment.get_status_changes()[1])


    @pytest.mark.nt
    def test_support_track_tickets_login_redirect(self):
        """
        check redirect after logging into track_tickets
        """

        # click the need help link,
        # check if the url changes

        po = self.catalog.load_pageobject('SupportPage')
        po.goto_page()
        expected_url = po.support.quicklink_track.get_attribute('href')
        po.goto_quicklink_track()

        po = self.catalog.load_pageobject('LoginPage')
        po.login_as(self.username,self.password,remember=False)

        po = self.catalog.load_pageobject('SupportTicketSearchPage')
        start_url = po.current_url()
        assert po.is_on_page(), "After login, user was taken to %s," \
            + " expected %s" % (start_url,expected_url)


    @pytest.mark.ticket_comment_attach_jpg
    def test_attach_jpg_to_ticket_comment(self):
        """
        login and submit a ticket, attach an image to a comment
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        data = {
            'problem'      : "hubcheck test ticket\n%s" % (self.fnbase),
        }

        # submit the ticket
        po.submit_ticket(data)

        po = self.catalog.load_pageobject('SupportTicketSavePage')
        self.ticket_number = po.get_ticket_number()

        info = po.get_error_info()
        assert len(info) == 0, "received unexpected error: %s" % (info)
        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, \
            "invalid ticket number returned: %s" % (self.ticket_number)


        # attach a jpeg image to a comment
        uploadfilename = 'app2.jpg'
        uploadfilepath = os.path.join(self.datadir,'images',uploadfilename)

        po = self.catalog.load_pageobject('SupportTicketViewPage',
                self.ticket_number)
        po.goto_page()
        comment_data = {
            'comment'   : 'attaching a jpg image',
            'upload'    : uploadfilepath,
        }
        po.add_comment(comment_data)


        # check if the image was uploaded
        comment = po.get_nth_comment(-1)
        imgsrc = comment.download_attachment(uploadfilename)

        # not sure how to really download image files yet.
        # so we assume that as long as opening the image didn't
        # cause an error, the test passed.

        assert re.search(uploadfilename,imgsrc) is not None, \
            "After uploading an image to support ticket" \
            + " #%s, could not download image %s" \
            % (self.ticket_number,uploadfilename)


    @pytest.mark.ticket_comment_attach_movie
    def test_attach_movie_to_ticket_comment(self):
        """
        login and submit a ticket, attach an image to a comment
        """

        # login to the website
        self.utils.account.login_as(self.username,self.password)

        po = self.catalog.load_pageobject('SupportTicketNewPage')
        po.goto_page()

        # name, email and description are required
        data = {
            'problem'      : "hubcheck test ticket\n%s" % (self.fnbase),
        }

        # submit the ticket
        po.submit_ticket(data)

        po = self.catalog.load_pageobject('SupportTicketSavePage')
        self.ticket_number = po.get_ticket_number()

        info = po.get_error_info()
        assert len(info) == 0, "received unexpected error: %s" % (info)
        assert self.ticket_number is not None, "no ticket number returned"
        assert int(self.ticket_number) > 0, \
            "invalid ticket number returned: %s" % (self.ticket_number)


        # attach a movie image to a comment
        uploadfilename = 'movie1.mpg'
        uploadfilepath = os.path.join(self.datadir,'images',uploadfilename)

        po = self.catalog.load_pageobject('SupportTicketViewPage',
                self.ticket_number)
        po.goto_page()
        comment_data = {
            'comment'   : 'attaching a movie file',
            'upload'    : uploadfilepath,
        }
        po.add_comment(comment_data)


        # check if the movie was uploaded
        comment = po.get_nth_comment(-1)
        moviesrc = comment.download_attachment(uploadfilename)

        # not sure how to really download movie files yet.
        # so we assume that as long as opening the image didn't
        # cause an error, the test passed.

        assert re.search(uploadfilename,moviesrc) is not None, \
            "After uploading a movie to support ticket" \
            + " #%s, could not download movie %s" \
            % (self.ticket_number,uploadfilename)

