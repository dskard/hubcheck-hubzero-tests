import pytest
import hubcheck
import pprint


pytestmark = [ pytest.mark.website,
               pytest.mark.tags,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade,
               pytest.mark.nt,
             ]


NON_EXISTENT_TAG = 'hubcheck_tag_that_does_not_really_exist'
EXISTENT_TAG = 'hubcheck'

class TestTags(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_version(min_version='1.0',max_version='1.1.4'),
        reason="hub version falls outside of valid range for this test")
    def test_tags_faq(self):
        """
        on the /tags page, click the FAQ link, check for 404
        clicking the FAQ link on /tags should take users to the Tags FAQ KB article
        """

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        start_url = po.current_url()

        # the link brings up a popup, so we need to get the
        # handle of that window and check the switch to it
        parent_h = self.browser._browser.current_window_handle

        # press the FAQ link
        self.browser.proxy_client.new_har("page")
        po.goto_faq()

        # click on the link that opens a new window
        handles = self.browser._browser.window_handles
        handles.remove(parent_h)
        self.browser._browser.switch_to_window(handles.pop())

        # get the page load details of the window
        har_entry = self.browser.page_load_details()
        end_url = po.current_url()

        # switch back to the main window
        self.browser._browser.switch_to_window(parent_h)

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri: %s. http archive unavailable." \
            % (end_url)
        assert self.browser.error_loading_page(har_entry) is False, \
            "while on the tags page %s," % (start_url) \
            + " pressing the Tags FAQ link returned error" \
            + " response code on page %s." % (end_url) \
            + " http archive follows:\n%s" % (pprint.pformat(har_entry))


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_version(min_version='1.0',max_version='1.1.4'),
        reason="hub version falls outside of valid range for this test")
    def test_tags_search_content_blank_1(self):
        """
        search for content, with an empty search box
        """

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        start_url = po.current_url()

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_content([])
        har_entry = self.browser.page_load_details()

        end_url = po.current_url()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is True, \
            "while on the tags page %s," % (start_url) \
            + " searching for content with no tags did not return an error" \
            + " response code on page %s." % (end_url) \
            + " http archive follows:\n%s" % (pprint.pformat(har_entry))


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_version(min_version='1.2.0'),
        reason="hub version falls outside of valid range for this test")
    def test_tags_search_content_blank_2(self):
        """
        search for content, with an empty search box
        in hubzero version 1.2.0 we now send users to a hub error page
        with a "Missing tag" error.
        """

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        start_url = po.current_url()

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_content([])
        har_entry = self.browser.page_load_details()

        end_url = po.current_url()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is False, \
            "while on the tags page %s," % (start_url) \
            + " searching for content with no tags returned an error" \
            + " response code on page %s." % (end_url) \
            + " http archive follows:\n%s" % (pprint.pformat(har_entry))


    def test_tags_content_search_invalid_tag(self):
        """on /tags, perform a content search for a non-existing tag"""

        global NON_EXISTENT_TAG

        po = self.catalog.load_pageobject('TagsPage')

        self.browser.proxy_client.new_har("page")
        po.goto_page()
        har_entry = self.browser.page_load_details()

        start_url = po.current_url()

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_content([NON_EXISTENT_TAG])
        har_entry = self.browser.page_load_details()

        end_url = po.current_url()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is True, \
            "while on the tags page %s," % (start_url) \
            + " searching for content with the tag '%s'" % (NON_EXISTENT_TAG) \
            + " did not return an error" \
            + " response code on page %s." % (end_url) \
            + " http archive follows:\n%s" % (pprint.pformat(har_entry))


    def test_tags_content_search_valid_tag(self,tag_with_items):
        """on /tags, perform a content search for an existing tag"""


        tag = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_content([tag])
        har_entry = self.browser.page_load_details()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is False, \
            "performing a content search using the tag" \
            + " '%s' returned an error response" % (tag) \
            + " code on the page %s" % (po.current_url()) \
            + " http archive follows:\n%s" % (pprint.pformat(har_entry))

        # get pagination counts
        po = self.catalog.load_pageobject('TagsViewPage')
        (start,end,total) = po.get_pagination_counts()

        # check for a valid total value
        assert total >= 0, \
            "performing a content search using the tag" \
            + " '%s' took user to a page with" % (tag) \
            + " invalid pagination: %s" % (po.current_url())


    def test_tags_tag_search_no_tag(self):
        """
        on /tags, perform a tag search using no tags
        """

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_tags('')
        har_entry = self.browser.page_load_details()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is False, \
            "performing a tag search using an empty string as the tag" \
            + "returned an error response code on the page" \
            + "%s http archive follows:\n%s" \
            % (po.current_url(),pprint.pformat(har_entry))


    def test_tags_tag_search_invalid_tag(self):
        """
        on /tags, perform a tag search using a tag that does not exist
        """

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()

        global NON_EXISTENT_TAG

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_tags(NON_EXISTENT_TAG)
        har_entry = self.browser.page_load_details()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is False, \
            "performing a tag search using an the tag" \
             + "'%s' returned an error response code" % (NON_EXISTENT_TAG) \
             + "on the page %s http archive follows:\n%s" \
            % (po.current_url(),pprint.pformat(har_entry))


    def test_tags_tag_search_valid_tag(self,tag_with_items):
        """
        on /tags, perform a tag search using a valid tag,
        check the pagination total on the tags view page.
        """

        tag = tag_with_items

        assert tag is not None, 'Could not find a tag with items'

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()

        # perform the search
        self.browser.proxy_client.new_har("page")
        po.search_for_tags(tag)
        har_entry = self.browser.page_load_details()

        # check for errors
        assert har_entry is not None, \
            "failed to load the uri. http archive unavailable."
        assert self.browser.error_loading_page(har_entry) is False, \
            "performing a tag search using an the tag" \
            + "'%s' returned an error response code on" % (tag) \
            + "the page %s http archive follows:\n%s" \
            % (po.current_url(),pprint.pformat(har_entry))

        # check for valid pagination total on tags view page
        po = self.catalog.load_pageobject('TagsViewPage')
        (start,end,total) = po.get_pagination_counts()

        assert total >= 0, \
            "performing a tag search using the tag" \
            + "'%s' took user to page (%s) with invalid pagination"\
            % (tag,po.current_url())


    def test_tags_recently_used_count(self):
        """
        on /tags, the number of recently used tags should be at most 25
        """

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        tags = po.get_recently_used_tags()
        assert len(tags) <= 25, \
            "# tags is %s, which is greater than 25" % (len(tags))


    def test_tags_recently_used_click(self):
        """
        on /tags, goto each of the recently used tags
        """

        self.browser.wait_time = 1
        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()

        # get the recently used tags
        tags = po.get_recently_used_tags()

        # click each tag, check for error page
        for tag in tags:

            self.browser.proxy_client.new_har("page")
            po.goto_recently_used_tag(tag['name'])
            har_entry = self.browser.page_load_details()

            # check for errors
            assert har_entry is not None, \
                "failed to load the uri. http archive unavailable."
            assert self.browser.error_loading_page(har_entry) is False, \
                "clicking on the recently used tag '%s'" % (tags) \
                + "returned an error response code on the page" \
                + "%s http archive follows:\n%s" \
                % (po.current_url(),pprint.pformat(har_entry))

            # go back to the tags page
            po.goto_page()


    def test_tags_top_100_count(self):
        """
        on /tags, the number of top 100 tags should be at most 100
        """
        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        tags = po.get_top_100_tags()
        assert len(tags) <= 100, \
            "# tags is %s, which is greater than 100" % (len(tags))


    def test_tags_top_100_click(self):
        """
        on /tags, click the top 100 tags, check for 404 error
        """

        self.browser.wait_time = 1
        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()

        # get the top 100 tags
        tags = po.get_top_100_tags()

        # click each tag, check for error page
        for tag in tags:

            self.browser.proxy_client.new_har("page")
            po.goto_top_100_tag(tag['name'])
            har_entry = self.browser.page_load_details()

            # check for errors
            assert har_entry is not None, \
                "failed to load the uri. http archive unavailable."
            assert self.browser.error_loading_page(har_entry) is False, \
                "clicking on the top 100 tag '%s'" % (tag) \
                + "returned an error response code on the" \
                + "page %s http archive follows:\n%s" \
                % (po.current_url(),pprint.pformat(har_entry))

            # go back to the tags page
            po.goto_page()


    def test_tags_click_browse_available(self):
        """
        on /tags, clicking "Browse Available Tags" takes user to /tags/browse
        """

        self.browser.wait_time = 1

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.goto_all_tags()

        po = self.catalog.load_pageobject('TagsBrowsePage')
        assert po.is_on_page() is True, \
            "Clicking the \"Browse available tags\" link takes users" \
            + "to \"%s\", expected \"%s\"" % (po.current_url,po.object_url)


# =============================================================
# Tags Browse Tests
# =============================================================

class TestTagsBrowseCounts(hubcheck.testcase.TestCase2):

    def test_tags_browse_compare_caption_pagination_start_counts(self,
        tag_browse_caption_counts,tag_browse_pagination_counts):
        """
        on /tags/browse, compare caption and footer start counts
        """

        self.caption_start = tag_browse_caption_counts['start']
        self.pagination_start = tag_browse_pagination_counts['start']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_start == self.pagination_start, \
            "while checking caption and pagination counts" \
            + "on %s, caption_start is not equal to" % (self.current_url) \
            + "pagination_start: caption_start  == %s, pagination_start == %s"\
            % (self.caption_start,self.pagination_start)


    def test_tags_browse_compare_caption_pagination_end_counts(self,
        tag_browse_caption_counts,tag_browse_pagination_counts):
        """
        on /tags/browse, compare caption and footer end counts
        """

        self.caption_end = tag_browse_caption_counts['end']
        self.pagination_end = tag_browse_pagination_counts['end']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_end == self.pagination_end, \
            "while checking caption and pagination counts" \
            + "on %s, caption_end is not equal to" % (self.current_url) \
            + "pagination_end: caption_end  == %s, pagination_end == %s"\
            % (self.caption_end,self.pagination_end)


    def test_tags_browse_compare_caption_pagination_total_counts(self,
        tag_browse_caption_counts,tag_browse_pagination_counts):
        """
        on /tags/browse, compare caption and footer total counts
        """

        self.caption_total = tag_browse_caption_counts['total']
        self.pagination_total = tag_browse_pagination_counts['total']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_total == self.pagination_total, \
            "while checking caption and pagination counts" \
            + "on %s, caption_total is not equal to" % (self.current_url) \
            + "pagination_total: caption_total  == %s, pagination_total == %s"\
            % (self.caption_total,self.pagination_total)


    def test_tags_browse_caption_start_lte_caption_end(self,tag_browse_caption_counts):
        """
        on /tags/browse, check caption count start <= end
        """

        self.caption_start = tag_browse_caption_counts['start']
        self.caption_end = tag_browse_caption_counts['end']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_start <= self.caption_end, \
            "while checking caption counts on %s," % (self.current_url) \
            + "caption_start > caption_end," \
            + "caption_start = %s, caption_end = %s" \
            % (self.caption_start,self.caption_end)


    def test_tags_browse_caption_start_lte_caption_total(self,tag_browse_caption_counts):
        """
        on /tags/browse, check caption count start <= total
        """

        self.caption_start = tag_browse_caption_counts['start']
        self.caption_total = tag_browse_caption_counts['total']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_start <= self.caption_total, \
            "while checking caption counts on %s," % (self.current_url) \
            + "caption_start > caption_total," \
            + "caption_start = %s, caption_total= %s" \
            % (self.caption_start,self.caption_total)


    def test_tags_browse_caption_end_lte_caption_total(self,tag_browse_caption_counts):
        """
        on /tags/browse, check caption count end <= total
        """

        self.caption_end = tag_browse_caption_counts['end']
        self.caption_total = tag_browse_caption_counts['total']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_end <= self.caption_total, \
            "while checking caption counts on %s," % (self.current_url) \
            + "caption_end > caption_total," \
            + "caption_end = %s, caption_total= %s"\
            % (self.caption_end,self.caption_total)


    def test_tags_browse_caption_total_gte_zero(self,tag_browse_caption_counts):
        """
        on /tags/browse, check caption count total >= 0
        """

        self.caption_total = tag_browse_caption_counts['total']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_total >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + "caption_total < 0, caption_total= %s" % (self.caption_total)


    def test_tags_browse_caption_start_gte_zero(self,tag_browse_caption_counts):
        """
        on /tags/browse, check caption count start >= 0
        """

        self.caption_start = tag_browse_caption_counts['start']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_start >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + "caption_start < 0, caption_start = %s" % (self.caption_start)


    def test_tags_browse_caption_end_gte_zero(self,tag_browse_caption_counts):
        """
        on /tags/browse, check caption count end >= 0
        """

        self.caption_end = tag_browse_caption_counts['end']
        self.current_url = tag_browse_caption_counts['url']

        assert self.caption_end >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + "caption_end < 0, caption_end = %s" % (self.caption_end)


    def test_tags_browse_pagination_start_lte_pagination_end(self,tag_browse_pagination_counts):
        """
        on /tags/browse, check pagination count start <= end
        """

        self.pagination_start = tag_browse_pagination_counts['start']
        self.pagination_end = tag_browse_pagination_counts['end']
        self.pagination_url = tag_browse_pagination_counts['url']

        assert self.pagination_start <= self.pagination_end, \
            "while checking pagination counts on %s," % (self.current_url) \
            + "pagination_start > pagination_end," \
            + "pagination_start = %s, pagination_end = %s" \
            % (self.pagination_start,self.pagination_end)


    def test_tags_browse_pagination_start_lte_pagination_total(self,tag_browse_pagination_counts):
        """
        on /tags/browse, check pagination count start <= total
        """

        self.pagination_start = tag_browse_pagination_counts['start']
        self.pagination_total = tag_browse_pagination_counts['total']
        self.pagination_url = tag_browse_pagination_counts['url']

        assert self.pagination_start <= self.pagination_total, \
            "while checking pagination counts on %s," % (self.current_url) \
            + "pagination_start > pagination_total," \
            + "pagination_start = %s, pagination_total= %s" \
            % (self.pagination_start,self.pagination_total)


    def test_tags_browse_pagination_end_lte_pagination_total(self,tag_browse_pagination_counts):
        """
        on /tags/browse, check pagination count end <= total
        """

        self.pagination_end = tag_browse_pagination_counts['end']
        self.pagination_total = tag_browse_pagination_counts['total']
        self.pagination_url = tag_browse_pagination_counts['url']

        assert self.pagination_end <= self.pagination_total, \
            "while checking pagination counts on %s," % (self.current_url) \
            + "pagination_end > pagination_total," \
            + "pagination_end = %s, pagination_total= %s"\
            % (self.pagination_end,self.pagination_total)


    def test_tags_browse_pagination_total_gte_zero(self,tag_browse_pagination_counts):
        """
        on /tags/browse, check pagination count total >= 0
        """

        self.pagination_total = tag_browse_pagination_counts['total']
        self.pagination_url = tag_browse_pagination_counts['url']

        assert self.pagination_total >= 0, \
            "while checking pagination counts on %s," % (self.current_url) \
            + "pagination_total < 0, pagination_total= %s" \
            % (self.pagination_total)


    def test_tags_browse_pagination_start_gte_zero(self,tag_browse_pagination_counts):
        """
        on /tags/browse, check pagination count start >= 0
        """

        self.pagination_start = tag_browse_pagination_counts['start']
        self.pagination_url = tag_browse_pagination_counts['url']

        assert self.pagination_start >= 0, \
            "while checking pagination counts on %s," % (self.current_url) \
            + "pagination_start < 0, pagination_start = %s" \
            % (self.pagination_start)


    def test_tags_browse_pagination_end_gte_zero(self,tag_browse_pagination_counts):
        """
        on /tags/browse, check pagination count end >= 0
        """

        self.pagination_end = tag_browse_pagination_counts['end']
        self.pagination_url = tag_browse_pagination_counts['url']

        assert self.pagination_end >= 0, \
            "while checking pagination counts on %s," % (self.current_url) \
            + " pagination_end < 0, pagination_end = %s" \
             % (self.pagination_end)


@hubcheck.utils.hub_version(max_version='1.2.2')
class TestTagsBrowseCaptionCountsDisplayAll(hubcheck.testcase.TestCase2):

    def test_tags_browse_caption_start_lte_caption_end(self,tag_browse_caption_counts_all):
        """
        on /tags/browse, change the display limit to All
        and check caption start <= end
        """

        self.caption_start = tag_browse_caption_counts_all['start']
        self.caption_end = tag_browse_caption_counts_all['end']
        self.current_url = tag_browse_caption_counts_all['url']

        assert self.caption_start <= self.caption_end, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_start > caption_end," \
            + " caption_start = %s, caption_end = %s" \
            % (self.caption_start,self.caption_end)


    def test_tags_browse_caption_start_lte_caption_total(self,tag_browse_caption_counts_all):
        """
        on /tags/browse, change the display limit to All
        and check caption start <= total
        """

        self.caption_start = tag_browse_caption_counts_all['start']
        self.caption_total = tag_browse_caption_counts_all['total']
        self.current_url = tag_browse_caption_counts_all['url']

        assert self.caption_start <= self.caption_total, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_start > caption_total," \
            + " caption_start = %s, caption_total= %s" \
            % (self.caption_start,self.caption_total)


    def test_tags_browse_caption_end_equals_caption_total(self,tag_browse_caption_counts_all):
        """
        on /tags/browse, change the display limit to All
        and check caption end == total
        """

        self.caption_end = tag_browse_caption_counts_all['end']
        self.caption_total = tag_browse_caption_counts_all['total']
        self.current_url = tag_browse_caption_counts_all['url']

        assert self.caption_end == self.caption_total, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_end != caption_total," \
            + " caption_end = %s, caption_total= %s" \
            % (self.caption_end,self.caption_total)


    def test_tags_browse_caption_total_gte_zero(self,tag_browse_caption_counts_all):
        """
        on /tags/browse, change the display limit to All
        and check caption total >= 0
        """

        self.caption_total = tag_browse_caption_counts_all['total']
        self.current_url = tag_browse_caption_counts_all['url']

        assert self.caption_total >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_total < 0, caption_total= %s" % (self.caption_total)


    def test_tags_browse_caption_start_gte_zero(self,tag_browse_caption_counts_all):
        """
        on /tags/browse, change the display limit to All
        and check caption start >= 0
        """

        self.caption_start = tag_browse_caption_counts_all['start']
        self.current_url = tag_browse_caption_counts_all['url']

        assert self.caption_start >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_start < 0, caption_start= %s" % (self.caption_start)


    # FIXME:
    # add tests for the pagination when all items are displayed


class TestTagsBrowsePagination(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)


    def test_tags_browse_pagination_current_page(self):
        """
        on /tags/browse, check pagination current page is 1
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        current_page_number = po.get_current_page_number()
        assert current_page_number == '1', \
            "after loading the page %s and examining" % (po.current_url()) \
            + " the page links, the current page number" \
            + " is '%s', expected '1'" % (current_page_number)


    def test_tags_browse_pagination_page_links(self):
        """
        on /tags/browse, check pagination page links
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        pagenumbers = po.get_link_page_numbers()

        while len(pagenumbers) > 0:
            page = int(pagenumbers[0])
            starturl = po.current_url()

            # click the link to go to the next page
            po.goto_page_number(page)
            endurl = po.current_url()

            # make sure the page changed
            assert starturl != endurl, \
                "clicking the page link for page %s" % (page) \
                + " did not change pages: starturl = %s," % (starturl) \
                + " endurl = %s" % (endurl)


            # update the page numbers
            # generally only a few page numbers surrounding the
            # current page are shown. as we progress through the
            # pages, more page numbers become available.
            if len(pagenumbers) > 1:
                new_pagenumbers = po.get_link_page_numbers()
                assert len(new_pagenumbers) != 0, \
                    'retrieving new page numbers failed while evaluating' \
                    + ' page #%s (%s)' % (page,endurl)
                pagenumbers = [int(i) \
                    for i in new_pagenumbers if int(i) > page]
            else:
                pagenumbers = []


            #FIXME: check the current page number matches page


    def test_tags_browse_pagination_relative_links_end(self):
        """
        on /tags/browse, check pagination relative end link
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        pagenumbers = po.get_link_page_numbers()

        # FIXME: need a test where we add enough tags to have multiple pages

        if len(pagenumbers) == 0:
            return

        starturl = po.current_url()
        po.goto_page_relative('end')
        endurl = po.current_url()
        assert starturl != endurl, \
            "clicking the 'end' link in pagination did not change pages:" \
            + " starturl = %s, endurl = %s" % (starturl,endurl)

        pagenumbers = po.get_link_page_numbers()
        lastpage = pagenumbers[-1]
        current_page = po.current_url()

        assert current_page > lastpage, \
            "clicking the 'end' link in pagination did not take the user" \
            + " to the last page: current_page = %s, lastpage = %s" \
            % (current_page,lastpage)


    def test_tags_browse_pagination_relative_links_start(self):
        """
        on /tags/browse, check pagination relative start link
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        pagenumbers = po.get_link_page_numbers()

        # FIXME: need a test where we add enough tags to have multiple pages

        if len(pagenumbers) == 0:
            return

        po.goto_page_number(pagenumbers[0])
        starturl = po.current_url()
        po.goto_page_relative('start')
        endurl = po.current_url()
        assert starturl != endurl, \
            "clicking the 'start' link in pagination did not change pages:" \
            + " starturl = %s, endurl = %s" % (starturl,endurl)

        firstpage = "1"

        current_page = po.get_current_page_number()
        assert current_page == firstpage, \
            "clicking the 'start' link in pagination did not take the user" \
            + " to the first page: current_page = %s, firstpage = %s" \
            % (current_page,firstpage)


class TestTagsBrowsePage(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)


    def test_tags_browse_more_tags_link(self):
        """
        on /tags/browse, clicking "more tags" should take user to /tags
        """


        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        po.goto_more_tags()


        po = self.catalog.load_pageobject('TagsPage')
        assert po.is_on_page() is True, \
            "clicking the 'more tags' link takes user to" \
            + " '%s', expected '%s'" % (po.current_url(),po.object_url())
        ebinfos = po.get_errorbox_info()
        assert len(ebinfos) == 0, \
            "clicking the 'more tags' link leads to an error page: %s" % ebinfos


    def test_tags_browse_default_display_limit_matches_pagination(self):
        """
        on /tags/browse, check the default display limit matches pagination
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # get the display limit
        display_limit = po.form.footer.display_limit()

        if display_limit == 'All':
            # no numeric value to compare if display_limit is 'All'
            return

        display_limit = int(display_limit)

        # get the pagination counts
        (start,end,total) = po.get_pagination_counts()

        # compare the display limit against pagination counts
        assert start < display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " start value is not less than the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)

        assert end <= display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " end value is not less than or equal to the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)


    def test_tags_browse_updated_min_display_limit_matches_pagination(self):
        """
        on /tags/browse, change the display limit to min
        and check that the display limit matches pagination
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # update the display limit
        new_display_limit = '5'
        po.form.footer.display_limit(new_display_limit)

        # get the new display limit
        display_limit = int(po.form.footer.display_limit())

        assert display_limit == int(new_display_limit), \
            "after changing the display limit to %s," % (display_limit) \
            + "retrieved display limit does not match:" \
            + "%s" % (new_display_limit)

        # get the new pagination counts
        (start,end,total) = po.get_pagination_counts()

        assert start < display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " start value is not less than the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)

        assert end <= display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " end value is not less than or equal to the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)


    @hubcheck.utils.hub_version(max_version='1.2.2')
    def test_tags_browse_updated_max_display_limit_matches_pagination(self):
        """
        on /tags/browse, change the display limit to max
        and check that the display limit matches pagination
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # change the display limit to 'All'
        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = po.form.footer.display_limit()

        assert display_limit == new_display_limit, \
            "updated display limit does not match the display limit" \
            + " set by user: updated display limit = " \
            + " '%s', user set display limit = '%s'" \
            % (display_limit,new_display_limit)

        # get the updated pagination counts
        (start,end,total) = po.get_pagination_counts()

        assert start == 1, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " after setting display limit to %s," % (new_display_limit) \
            + " pagination start = '%s', expected start = 1." % (start)

        assert end == total, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " after setting display limit to %s," % (new_display_limit) \
            + " pagination end = '%s', total = '%s'." % (end,total) \
            + " expected end == total."


    def test_tags_browse_updated_min_display_limit_page_links(self):
        """
        on /tags/browse, change the display limit to min
        and check footer for page links
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # change the display limit to 5
        new_display_limit = '5'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = int(po.form.footer.display_limit())

        assert display_limit == int(new_display_limit), \
            "updated display limit does not match the display limit" \
            + " set by user: updated display limit =" \
            + " '%s', user set display limit = '%s'" \
            % (display_limit,new_display_limit)

        # get the updated page number links
        page_numbers = po.get_link_page_numbers()

        # get the updated pagination counts
        (start,end,total) = po.get_pagination_counts()

        if total > display_limit:
            # there are more items to display than are allowed by
            # the display limit. this means there should be page
            # number links

            assert len(page_numbers) != 0, \
                "on tags browse page (%s), after setting" % (po.current_url()) \
                + " display limit to %s, the following" % (new_display_limit) \
                + " link page numbers are still available: %s" % (page_numbers)



    def test_tags_browse_click_page_links_check_items_displayed(self):
        """
        on /tags/browse, change the display limit
        to min and click the page links
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # change the display limit to 5
        new_display_limit = '5'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = int(po.form.footer.display_limit())

        assert display_limit == int(new_display_limit), \
            "updated display limit does not match the display" \
            + " limit set by user: updated display limit =" \
            + " '%s', user set display limit = '%s'" \
            % (display_limit,new_display_limit)

        # get the updated page number links
        page_numbers = po.get_link_page_numbers()

        page_url = po.current_url()

        for p in page_numbers:
            # click the page number link
            po.goto_page_number(p)

            po2 = self.catalog.load_pageobject('TagsBrowsePage')

            # get the number of items that should be displayed
            # according to the pagination counts
            (start,end,total) = po2.get_pagination_counts()
            num_pag = (end-start+1)

            # get the number of items that are actually displayed
            num_rows = po2.form.search_results.num_rows()

            # compare that is should be displayed to what is displayed
            assert num_pag == num_rows, \
                "after clicking page link #%s on %s," % (p,page_url) \
                + " the number of items displayed does not match the" \
                + " number of items listed in the pagination counts:" \
                + " displayed = %s, start = %s," % (num_rows,start) \
                + " end = %s, end-start+1 (what should be displayed) = %s" \
                % (end,num_pag)

            # return back to our original page
            self.browser._browser.back()


    @hubcheck.utils.hub_version(max_version='1.2.2')
    def test_tags_browse_updated_max_display_limit_no_page_links(self):
        """
        on /tags/browse, change the display limit to All
        and check footer for no page links
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # change the display limit to 'All'
        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = po.form.footer.display_limit()

        assert display_limit == new_display_limit, \
            "updated display limit does not match the display limit" \
            + " set by user: updated display limit =" \
            + " '%s', user set display limit = '%s'" \
            % (display_limit,new_display_limit)

        # get the updated page number links
        page_numbers = po.get_link_page_numbers()

        assert len(page_numbers) == 0, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " after setting display limit to" \
            + " %s, the following link page numbers are still available: %s" \
            % (new_display_limit,page_numbers)


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_version(min_version='1.0',max_version='1.1.4'),
        reason="hub version falls outside of valid range for this test")
    def test_tags_browse_valid_tag_name_count(self):
        """
        on /tags/browse, check that the '# tagged' are numeric values
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        po.form.footer.display_limit('All')

        for row in po.search_result_rows():
            rowv = row.value()

            assert rowv['name'].strip() != '', \
                "invalid name for tag '%s': name is blank" \
                % (rowv['name'])

            assert rowv['count'] >= 0, \
                "invalid count for tag '%s': count = %s" \
                % (rowv['name'],rowv['count'])


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_version(min_version='1.0',max_version='1.1.4'),
        reason="hub version falls outside of valid range for this test")
    def test_tag_count_matches_tagged_items(self):
        """
        check that browse page tag counts match view page resources
        """

        po = self.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()
        po.form.footer.display_limit('All')
        tags_browse_url = po.current_url()

        po2 = self.catalog.load_pageobject('TagsViewPage')

        for row in po.search_result_rows():
            tag_info = row.value()

            self.browser.proxy_client.new_har("page")
            row.goto_tag()
            har_entry = self.browser.page_load_details()

            tags_view_url = po2.current_url()

            # check for errors loading the page
            assert har_entry is not None, \
                "failed to load the uri. http archive unavailable."
            assert self.browser.error_loading_page(har_entry) is False, \
                "clicking on the tag '%s' on '%s' " \
                    % (tag_info['name'],tags_browse_url) + \
                "returned an error response code on the page '%s'. " \
                    % (tags_view_url) + \
                "http archive follows:\n%s" \
                    % (pprint.pformat(har_entry))

            # get the total number of resources
            (junk,junk,total) = po2.get_pagination_counts()

            # compare the total number of resources
            # with the count provided by the tag
            assert tag_info['count'] == total, \
                "The number of resources listed for the" \
                + " tag '%s' (%s) on %s does not match the total" \
                    % (tag_info['name'],tag_info['count'],tags_browse_url) \
                + " number of resources listed on %s (%s)" \
                    % (tags_view_url,total)

            # go back to the Tags page
            self.browser._browser.back()


# =============================================================
# Tags View Tests
# =============================================================


@pytest.mark.tags_view_counts
class TestTagsViewCounts(hubcheck.testcase.TestCase2):


    def test_compare_caption_pagination_start_counts(self,
            tag_view_caption_counts,tag_view_pagination_counts):
        """
        on /tags/view, compare caption and footer start counts
        """
        self.caption_start = tag_view_caption_counts['start']
        self.pagination_start = tag_view_pagination_counts['start']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_start == self.pagination_start, \
            "while checking caption and pagination counts on %s," \
                % (self.current_url) \
            + " caption_start is not equal to pagination_start:" \
            + " caption_start  == %s, pagination_start == %s" \
                % (self.caption_start,self.pagination_start)


    def test_compare_caption_pagination_end_counts(self,
            tag_view_caption_counts,tag_view_pagination_counts):
        """
        on /tags/view, compare caption and footer end counts
        """

        self.caption_end = tag_view_caption_counts['end']
        self.pagination_end = tag_view_pagination_counts['end']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_end == self.pagination_end, \
            "while checking caption and pagination counts on %s," \
                % (self.current_url) \
            + " caption_end is not equal to pagination_end:" \
            + " caption_end  == %s, pagination_end == %s" \
                % (self.caption_end,self.pagination_end)


    def test_compare_caption_pagination_total_counts(self,
            tag_view_caption_counts,tag_view_pagination_counts):
        """
        on /tags/view, compare caption and footer total counts
        """

        self.caption_total = tag_view_caption_counts['total']
        self.pagination_total = tag_view_pagination_counts['total']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_total == self.pagination_total, \
            "while checking caption and pagination counts on %s," \
                % (self.current_url) \
            + " caption_total is not equal to pagination_total:" \
            + " caption_total  == %s, pagination_total == %s" \
                % (self.caption_total,self.pagination_total)


    def test_caption_start_lte_caption_end(self, tag_view_caption_counts):
        """
        on /tags/view, check caption count start <= end
        """

        self.caption_start = tag_view_caption_counts['start']
        self.caption_end = tag_view_caption_counts['end']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_start <= self.caption_end, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_start > caption_end," \
            + " caption_start = %s, caption_end = %s" \
                % (self.caption_start,self.caption_end)


    def test_caption_start_lte_caption_total(self, tag_view_caption_counts):
        """
        on /tags/view, check caption count start <= total
        """

        self.caption_start = tag_view_caption_counts['start']
        self.caption_total = tag_view_caption_counts['total']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_start <= self.caption_total, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_start > caption_total," \
            + " caption_start = %s, caption_total= %s" \
                % (self.caption_start,self.caption_total)


    def test_caption_end_lte_caption_total(self, tag_view_caption_counts):
        """
        on /tags/view, check caption count end <= total
        """

        self.caption_end = tag_view_caption_counts['end']
        self.caption_total = tag_view_caption_counts['total']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_end <= self.caption_total, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_end > caption_total," \
            + " caption_end = %s, caption_total= %s" \
                % (self.caption_end,self.caption_total)


    def test_caption_total_gte_zero(self, tag_view_caption_counts):
        """
        on /tags/view, check caption count total >= 0
        """

        self.caption_total = tag_view_caption_counts['total']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_total >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
             + " caption_total < 0, caption_total= %s" % (self.caption_total)


    def test_caption_start_gte_zero(self, tag_view_caption_counts):
        """
        on /tags/view, check caption count start >= 0
        """

        self.caption_start = tag_view_caption_counts['start']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_start >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_start < 0, caption_start = %s" % (self.caption_start)


    def test_caption_end_gte_zero(self, tag_view_caption_counts):
        """
        on /tags/view, check caption count end >= 0
        """

        self.caption_end = tag_view_caption_counts['end']
        self.current_url = tag_view_caption_counts['url']

        assert self.caption_end >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_end < 0, caption_end = %s" % (self.caption_end)


    def test_pagination_start_lte_pagination_end(self,tag_view_pagination_counts):
        """
        on /tags/view, check pagination count start <= end
        """

        self.pagination_start = tag_view_pagination_counts['start']
        self.pagination_end = tag_view_pagination_counts['end']
        self.current_url = tag_view_pagination_counts['url']

        assert self.pagination_start <= self.pagination_end, \
            "while checking pagination counts on %s," \
                % (self.current_url) \
            + " pagination_start > pagination_end," \
            + " pagination_start = %s, pagination_end = %s" \
                % (self.pagination_start,self.pagination_end)


    def test_pagination_start_lte_pagination_total(self,tag_view_pagination_counts):
        """
        on /tags/view, check pagination count start <= total
        """

        self.pagination_start = tag_view_pagination_counts['start']
        self.pagination_total = tag_view_pagination_counts['total']
        self.current_url = tag_view_pagination_counts['url']

        assert self.pagination_start <= self.pagination_total, \
            "while checking pagination counts on %s," \
                % (self.current_url) \
            + " pagination_start > pagination_total," \
            + " pagination_start = %s, pagination_total= %s"\
                % (self.pagination_start,self.pagination_total)


    def test_pagination_end_lte_pagination_total(self,tag_view_pagination_counts):
        """
        on /tags/view, check pagination count end <= total
        """

        self.pagination_end = tag_view_pagination_counts['end']
        self.pagination_total = tag_view_pagination_counts['total']
        self.current_url = tag_view_pagination_counts['url']

        assert self.pagination_end <= self.pagination_total, \
            "while checking pagination counts on %s," \
                % (self.current_url) \
            + " pagination_end > pagination_total," \
            + " pagination_end = %s, pagination_total= %s" \
                % (self.pagination_end,self.pagination_total)


    def test_pagination_total_gte_zero(self,tag_view_pagination_counts):
        """
        on /tags/view, check pagination count total >= 0
        """

        self.pagination_total = tag_view_pagination_counts['total']
        self.current_url = tag_view_pagination_counts['url']

        assert self.pagination_total >= 0, \
            "while checking pagination counts on %s," \
                % (self.current_url) \
            + " pagination_total < 0, pagination_total= %s" \
                % (self.pagination_total)


    def test_pagination_start_gte_zero(self,tag_view_pagination_counts):
        """
        on /tags/view, check pagination count start >= 0
        """

        self.pagination_start = tag_view_pagination_counts['start']
        self.current_url = tag_view_pagination_counts['url']

        assert self.pagination_start >= 0, \
            "while checking pagination counts on %s," \
                % (self.current_url) \
            + " pagination_start < 0, pagination_start = %s" \
                % (self.pagination_start)


    def test_pagination_end_gte_zero(self,tag_view_pagination_counts):
        """
        on /tags/view, check caption count end >= 0
        """

        self.pagination_end = tag_view_pagination_counts['end']
        self.current_url = tag_view_pagination_counts['url']

        assert self.pagination_end >= 0, \
            "while checking pagination counts on %s," \
                % (self.current_url) \
            + " pagination_end < 0, pagination_end = %s" \
                % (self.pagination_end)


@hubcheck.utils.hub_version(max_version='1.2.2')
class TestTagsViewCaptionCountsDisplayAll(hubcheck.testcase.TestCase2):


    def test_tags_view_caption_start_lte_caption_end(self,tag_view_caption_counts_all):
        """
        on /tags/view, change the display limit to All and
        check caption counts start <= end
        """

        self.caption_start = tag_view_caption_counts_all['start']
        self.caption_end = tag_view_caption_counts_all['end']
        self.current_url = tag_view_caption_counts_all['url']

        assert self.caption_start <= self.caption_end, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_start > caption_end," \
            + " caption_start = %s, caption_end = %s" \
                 % (self.caption_start,self.caption_end)


    def test_tags_view_caption_start_lte_caption_total(self,tag_view_caption_counts_all):
        """
        on /tags/view, change the display limit to All and
        check caption counts start <= total
        """

        self.caption_start = tag_view_caption_counts_all['start']
        self.caption_total = tag_view_caption_counts_all['total']
        self.current_url = tag_view_caption_counts_all['url']

        assert self.caption_start <= self.caption_total, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_start > caption_total," \
            + " caption_start = %s, caption_total= %s" \
                % (self.caption_start,self.caption_total)


    def test_tags_view_caption_end_equals_caption_total(self,tag_view_caption_counts_all):
        """
        on /tags/view, change the display limit to All and
        check caption counts end == total
        """

        self.caption_end = tag_view_caption_counts_all['end']
        self.caption_total = tag_view_caption_counts_all['total']
        self.current_url = tag_view_caption_counts_all['url']

        assert self.caption_end == self.caption_total, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_end != caption_total," \
            + " caption_end = %s, caption_total= %s" \
                % (self.caption_end,self.caption_total)


    def test_tags_view_caption_total_gte_zero(self,tag_view_caption_counts_all):
        """
        on /tags/view, change the display limit to All and
        check caption counts total >= 0
        """

        self.caption_total = tag_view_caption_counts_all['total']
        self.current_url = tag_view_caption_counts_all['url']

        assert self.caption_total >= 0, \
            "while checking caption counts on %s," % (self.current_url) \
            + " caption_total < 0, caption_total= %s" % (self.caption_total)


    def test_tags_view_caption_start_gte_zero(self,tag_view_caption_counts_all):
        """
        on /tags/view, change the display limit to All and
        check caption counts start >= 0
        """

        self.caption_start = tag_view_caption_counts_all['start']
        self.current_url = tag_view_caption_counts_all['url']

        assert self.caption_start >= 0, \
            "while checking caption counts on %s," \
                % (self.current_url) \
            + " caption_start < 0, caption_start= %s" \
                % (self.caption_total)


class TestTagsViewPagination(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.browser.get(self.https_authority)


    def test_tags_view_pagination_current_page(self,tag_with_items):
        """
        on /tags/view, check pagination current page is 1
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        current_page_number = po.get_current_page_number()
        assert current_page_number == '1', \
            "after loading the page %s and examining the page links," \
                % (po.current_url()) \
            + " the current page number is '%s', expected '1'" \
                % (current_page_number)


    def test_tags_view_pagination_page_links(self,tag_with_items):
        """
        on /tags/view, check pagination page links
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        pagenumbers = po.get_link_page_numbers()

        for page in pagenumbers:
            starturl = po.current_url()
            po.goto_page_number(page)
            endurl = po.current_url()
            assert starturl != endurl, \
                "clicking the page link for page %s" % (page) \
                + " did not change pages:" \
                + " starturl = %s, endurl = %s" % (starturl,endurl)

            #FIXME: check the current page number matches page


    def test_tags_view_pagination_relative_links_end(self,tag_with_items):
        """
        on /tags/view, check pagination relative end link
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        pagenumbers = po.get_link_page_numbers()

        # FIXME: need a test where we add enough content to have multiple pages

        if len(pagenumbers) == 0:
            return

        starturl = po.current_url()
        po.goto_page_relative('end')
        endurl = po.current_url()

        assert starturl != endurl, \
            "clicking the 'end' link in pagination did not change pages:" \
            + " starturl = %s, endurl = %s" % (starturl,endurl)

        pagenumbers = po.get_link_page_numbers()
        lastpage = pagenumbers[-1]
        current_page = po.current_url()

        assert current_page > lastpage, \
            "clicking the 'end' link in pagination" \
            + " did not take the user to the last page:" \
            + " current_page = %s, lastpage = %s" \
                % (current_page,lastpage)


    def test_tags_view_pagination_relative_links_start(self,tag_with_items):
        """
        on /tags/view, check pagination relative start link
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        pagenumbers = po.get_link_page_numbers()

        # FIXME: need a test where we add enough tags to have multiple pages

        if len(pagenumbers) == 0:
            return

        po.goto_page_number(pagenumbers[0])
        starturl = po.current_url()
        po.goto_page_relative('start')
        endurl = po.current_url()
        assert starturl != endurl, \
            "clicking the 'start' link in pagination did not change pages:" \
            + " starturl = %s, endurl = %s" % (starturl,endurl)

        firstpage = "1"

        current_page = po.get_current_page_number()
        assert current_page == firstpage, \
            "clicking the 'start' link in pagination" \
            + " did not take the user to the first page:" \
            + " current_page = %s, firstpage = %s" \
                % (current_page,firstpage)


    def test_tags_view_more_tags_link(self,tag_with_items):
        """
        on /tags/view, clicking "more tags" should take user to /tags
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')
        po.goto_more_tags()

        po = self.catalog.load_pageobject('TagsPage')

        assert po.is_on_page() is True, \
            "clicking the 'more tags' link" \
            + " takes user to '%s', expected '%s'" \
                % (po.current_url(),po.object_url())

        ebinfos = po.get_errorbox_info()
        assert len(ebinfos) == 0, \
            "clicking the 'more tags' link leads to an error page: %s" % ebinfos


    def test_tags_view_default_display_limit_matches_pagination(self,tag_with_items):
        """
        on /tags/view, check the default display limit matches pagination
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        # get the display limit
        display_limit = po.form.footer.display_limit()

        if display_limit == 'All':
            # no numeric value to compare if display_limit is 'All'
            return

        display_limit = int(display_limit)

        # get the pagination counts
        (start,end,total) = po.get_pagination_counts()

        # compare the display limit against pagination counts
        assert start < display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " start value is not less than the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)

        assert end <= display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " end value is not less than or equal to the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)


    def test_tags_view_updated_min_display_limit_matches_pagination(self,tag_with_items):
        """
        on /tags/view, change the display limit to min
        and check that the display limit matches pagination
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        # update the display limit
        new_display_limit = '5'
        po.form.footer.display_limit(new_display_limit)

        # get the new display limit
        display_limit = int(po.form.footer.display_limit())

        assert display_limit == int(new_display_limit), \
            "after changing the display limit to %s, retrieved\
            display limit does not match: %s"\
            % (display_limit, new_display_limit)

        # get the new pagination counts
        (start,end,total) = po.get_pagination_counts()

        assert start < display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " start value is not less than the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)

        assert end <= display_limit, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " end value is not less than or equal to the display limit:" \
            + " start = %s, display_limit = %s" % (start,display_limit)


    @hubcheck.utils.hub_version(max_version='1.2.2')
    def test_tags_view_updated_max_display_limit_matches_pagination(self,tag_with_items):
        """
        on /tags/view, change the display limit to max
        and check that the display limit matches pagination
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        # change the display limit to 'All'
        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = po.form.footer.display_limit()

        assert display_limit == new_display_limit, \
            "updated display limit does not match the display limit" \
            + " set by user: updated display limit = " \
            + " '%s', user set display limit = '%s'" \
                % (display_limit,new_display_limit)

        # get the updated pagination counts
        (start,end,total) = po.get_pagination_counts()

        assert start == 1, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " after setting display limit to" \
            + " %s, pagination start = '%s', expected start = 1." \
                % (new_display_limit,start)

        assert end == total, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " after setting display limit to" \
            + " %s, pagination end = '%s', total = '%s'." \
                % (new_display_limit,end,total) \
            + " expected end == total."


    def test_tags_view_updated_min_display_limit_page_links(self,tag_with_items):
        """
        on /tags/view, change the display limit to min and
        check footer for page links
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        # change the display limit to 5
        new_display_limit = '5'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = int(po.form.footer.display_limit())

        assert display_limit == int(new_display_limit), \
            "updated display limit does not match the display limit" \
            + "set by user: updated display limit = '%s'," % (display_limit) \
            + "user set display limit = '%s'" % (new_display_limit)

        # get the updated page number links
        page_numbers = po.get_link_page_numbers()

        # get the updated pagination counts
        (start,end,total) = po.get_pagination_counts()

        if total > display_limit:
            # there are more items to display than are allowed by
            # the display limit. this means there should be page
            # number links

            assert len(page_numbers) != 0, \
                "on tags browse page (%s)," % (po.current_url()) \
                + "after setting display limit to %s," % (new_display_limit) \
                + "the following link page numbers are" \
                + "still available: %s" % (page_numbers)


    def test_tags_view_click_page_links_check_items_displayed(self,tag_with_items):
        """
        on /tags/view, change display limit to min and click page links
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        # change the display limit to 5
        new_display_limit = '5'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = int(po.form.footer.display_limit())

        assert display_limit == int(new_display_limit), \
            "updated display limit does not match the display limit" \
            + " set by user: updated display limit =" \
            + " '%s', user set display limit = '%s'" \
                % (display_limit,new_display_limit)

        # get the updated page number links
        page_numbers = po.get_link_page_numbers()

        page_url = po.current_url()

        for p in page_numbers:
            # click the page number link
            po.goto_page_number(p)

            po2 = self.catalog.load_pageobject('TagsViewPage')

            # get the number of items that should be displayed
            # according to the pagination counts
            (start,end,total) = po2.get_pagination_counts()
            num_pag = (end-start+1)

            # get the number of items that are actually displayed
            num_rows = po2.form.search_results.num_rows()

            # compare that is should be displayed to what is displayed
            assert num_pag == num_rows, \
                "after clicking page link #%s on %s," \
                    % (p,page_url) \
                + " the number of items displayed does not match the" \
                + " number of items listed in the pagination counts:" \
                + " displayed = %s, start = %s, end = %s," \
                    % (num_rows,start,end) \
                + " end-start+1 (what should be displayed) = %s" \
                    % (num_pag)

            # return back to our original page
            self.browser._browser.back()


    @hubcheck.utils.hub_version(max_version='1.2.2')
    def test_tags_view_updated_max_display_limit_no_page_links(self,tag_with_items):
        """
        on /tags/view, change the display limit to All and
        check footer for no page links
        """

        self.tag_name = tag_with_items

        po = self.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([self.tag_name])

        po = self.catalog.load_pageobject('TagsViewPage')

        # change the display limit to 'All'
        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        # get the updated display limit
        display_limit = po.form.footer.display_limit()

        assert display_limit == new_display_limit, \
            "updated display limit does not match the display limit" \
            + " set by user: updated display limit =" \
            + "'%s', user set display limit = '%s'" \
                % (display_limit,new_display_limit)

        # get the updated page number links
        page_numbers = po.get_link_page_numbers()

        assert len(page_numbers) == 0, \
            "on tags browse page (%s)," % (po.current_url()) \
            + " after setting display limit to %s," % (new_display_limit) \
            + " the following link page numbers are still available: %s" \
                % (page_numbers)
