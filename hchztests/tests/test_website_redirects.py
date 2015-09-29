import pprint
import hubcheck
import pytest
import urlparse

from selenium.common.exceptions import TimeoutException


pytestmark = [ pytest.mark.website,
               pytest.mark.redirects,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade,
             ]


class TestWebsiteRedirectsHttp(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.http_authority)


    def test_connect_to_http_uri(self):
        """
        check that the http uri loads a page
        """

        self.browser.proxy_client.new_har("page")

        po = self.catalog.load_pageobject('GenericPage')
        po.goto_page(self.http_authority)

        har_entry = self.browser.page_load_details(self.http_authority)

        assert har_entry is not None, \
            "failed to load the uri %s. http archive unavailable." \
            % (self.http_authority)

        assert self.browser.error_loading_page(har_entry) is False, \
            "failed to load uri %s. http archive response follows:\n%s" \
            % (self.http_authority,pprint.pformat(har_entry))


    @pytest.mark.parametrize('linkname', ['login','register'])
    def test_http_link_redirects_to_https(self,linkname):
        """
        check that navigating to the http site, and clicking the
        link redirects the user to an https page.
        """

        po = self.catalog.load_pageobject('GenericPage')

        method_name = 'goto_%s' % (linkname)
        goto_link_method = getattr(po,method_name,None)

        if goto_link_method is None:
            raise RuntimeError('invalid method name: %s' % (method_name))

        # click the link
        try:
            goto_link_method()
        except TimeoutException:
            pytest.skip('no %s link available' % (linkname))

        loc = urlparse.urlsplit(po.current_url())
        assert loc.scheme == 'https', \
            "After loading %s, and clicking on the %s link," \
            + " scheme is: %s, expected: 'https'" \
            % (self.http_authority, linkname, loc.scheme)


    @pytest.mark.parametrize('pagename', ['login','register','administrator'])
    def test_http_url_redirects_to_https(self,pagename):
        """
        Check that url requests to the http version of the page
        redirect to an https page
        """

        url = '%s/%s' % (self.http_authority,pagename)

        po = self.catalog.load_pageobject('GenericPage')
        po.goto_page(url)

        loc = urlparse.urlsplit(po.current_url())
        assert loc.scheme == 'https', \
            "After loading %s, scheme is: %s, expected: 'https'" \
            % (url, loc.scheme)


    @pytest.mark.www_prefix
    def test_load_http_uri_with_www_prefix(self):
        """
        Check that the http uri prefixed with www loads a page
        """

        url = "http://www.%s" % (self.http_uri)

        self.browser.proxy_client.new_har("page")

        po = self.catalog.load_pageobject('GenericPage')
        po.goto_page(url)

        har_entry = self.browser.page_load_details(url)

        assert har_entry is not None, \
            "failed to load the uri %s. http archive unavailable." \
            % (url)

        assert self.browser.error_loading_page(har_entry) is False, \
            "failed to load the uri %s. http archive follows:\n%s" \
            % (url,pprint.pformat(har_entry))


class TestWebsiteRedirectsHttps(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)


    def test_connect_to_https_uri(self):
        """
        check that the https uri loads a page
        """

        self.browser.proxy_client.new_har("page")

        po = self.catalog.load_pageobject('GenericPage')
        po.goto_page(self.https_authority)

        har_entry = self.browser.page_load_details(self.https_authority)

        assert har_entry is not None, \
            "failed to load the uri %s. http archive unavailable." \
            % (self.https_authority)

        assert self.browser.error_loading_page(har_entry) is False, \
            "failed to load uri %s. http archive response follows:\n%s" \
            % (self.https_authority,pprint.pformat(har_entry))


    def test_kb_tips_webdav_has_text_HUBADDRESS(self):
        """
        check that /kb/tips/webdav does not contain the text HUBADDRESS
        """

        po = self.catalog.load_pageobject('GenericPage')
        po.goto_page(self.https_authority+"/kb/tips/webdav")

        page_text = self.browser._browser\
                        .find_element_by_css_selector('body').text

        assert 'HUBADDRESS' not in page_text, \
            "the page %s contains the word HUBADDRESS" \
            % (po.current_url())


    @pytest.mark.www_prefix
    def test_load_https_uri_with_www_prefix(self):
        """
        Check that the https uri prefixed with www loads a page
        """

        url = "https://www.%s" % (self.https_uri)

        self.browser.proxy_client.new_har("page")

        po = self.catalog.load_pageobject('GenericPage')
        po.goto_page(url)

        har_entry = self.browser.page_load_details(url)

        assert har_entry is not None, \
            "failed to load the uri %s. http archive unavailable." \
            % (url)

        assert self.browser.error_loading_page(har_entry) is False, \
            "failed to load the uri %s. http archive follows:\n%s" \
            % (url,pprint.pformat(har_entry))




#test -compare notin \
#    -tags {website reboot upgrade prod_safe_upgrade} \
#    {website/favicon/notnanohub} \
#    {Check that the site is not using the nanohub favicon}\
#{@tcl
#    package require http
#    package require base64
#
#    set hubname         @@tcl:HCVAR options(-hubhostname)@@
#    set hubport         @@tcl:HCVAR options(-hubhttpport)@@
#
#    if {$hubname == "nanohub.org"} {
#        return ""
#    }
#
#    set url "http://${hubname}:${hubport}/favicon.ico"
#
#    set r [http::geturl $url -binary 1]
#
#    return [base64::encode [http::data $r]]
#
#} {AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAA
#AAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A
#////AP///wD///8A////AP///wCdnZ9uycnKPP///wD///8A////AP///wD///8A////AP///wD/
#//8A/Pz8AbS0tVS5ubpN////AP///wD///8AcmhS/VpUSu7ExMVC////AP///wD///8A////AP//
#/wD///8A////AJycnXFhWUn6iYJ0x////wD///8A////ANW/i//JtYT/nZeKp////wD///8A////
#AP///wD///8A////AP///wCSiHLZ076K/9vGkv////8A////AP///wDbxpL/2cON/7Kmisn///8A
#////AP///wD///8A////AP///wD///8AuKeA7dnDjf/bxpL/////AP///wD///8A28aS/9nDjf+z
#p4vJ////AP///wD///8A////AP///wD///8A////ALengerZw43/28aS/////wD///8A////ANvG
#kv/Zw43/s6eLx////wD///8A////AP///wD///8A////AP///wC2poDq2cON/9vGkv////8A////
#AP///wDbxpL/2cON/7Clicn///8A////AP///wD///8A////AP///wD///8AtKR+6tnDjf/bxpL/
#////AP///wD///8A28aS/9nDjf+dkXTj+vr6A////wD///8A////AP///wD///8A2dnZKqycdvjZ
#w43/28aS/////wD///8A////ANvGkv/Zw43/rZ11/Z2dnXH///8A////AP///wD///8A9/f3B4J+
#d7HGsoL/2cON/83Bpaj///8A////AP///wDf1LaU2cON/9S+iv93bVf4hYWHi87OzzXg4OAiwsLD
#RHFwcaiUhmb/2cON/9bAi/3w6ttK////AP///wD///8A+vjzGNbDl93Zw43/0r2J/4R4XP9WUEju
#UUxJ41pUSPWYiWj/2MKN/9nDjf/e0K2u/f38A////wD///8A////AP///wD07+I+2MWW49nDjf/Z
#w43/ybWE/8Guf//OuYf/2cON/9nDjf/ezKTH+vfyGf///wD///8A////AP///wD///8A////APfz
#6ivez6u11cGN+NnDjf/Zw43/2cON/9bBkPPk2LmU+/n1FP///wD///8A////AP///wD///8A////
#AP///wD///8A+vj0FfDn02Do27uX5te1pendv43y69tN/Pv4DP///wD///8A////AP///wD///8A
#////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD/
#//8A//8AAP//AADP+QAAx/EAAMfxAADH8QAAx/EAAMfxAADH8QAAx+EAAMHDAADgAwAA8AcAAPgP
#AAD+PwAA//8AAA==}
