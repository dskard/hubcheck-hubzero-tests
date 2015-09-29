import pytest
import hubcheck
import time


pytestmark = []


class Timer(object):
    """A little timer class that we can use to time code in a with statement"""

    def __enter__(self):
        self.start = time.time()
        return self


    def __exit__(self,*args):
        self.end = time.time()
        self.elapsed = self.end - self.start


@pytest.mark.hub_timings
class TestHubTimings(hubcheck.testcase.TestCase2):

    def test_timed_login(self):
        """
        time logging into the hub website
        average login (and verification) through selenium is about 14 seconds
        if login takes longer than 30 seconds, we consider it a failure

        https://nanohub.org/support/ticket/265286
        https://nanohub.org/support/ticket/265257
        https://nanohub.org/support/ticket/265234
        https://nanohub.org/support/ticket/258652
        """

        self.username,self.userpass = \
            self.testdata.find_account_for('timinguser')

        # setup a web browser
        self.browser.get(self.https_authority)

        with Timer() as t:
            self.utils.account.login_as(self.username,self.userpass)

            # verify you have successfully logged in
            po = self.catalog.load_pageobject('GenericPage')
            assert po.header.is_logged_in(),'Login Failed'


        self.logger.info('elapsed time = %0.3f seconds' % (t.elapsed))
        assert t.elapsed < 30, \
            'logging into the website took %0.3f seconds' % t.elapsed

