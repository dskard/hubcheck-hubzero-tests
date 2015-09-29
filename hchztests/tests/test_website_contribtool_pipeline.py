import pytest
import hubcheck


pytestmark = [ pytest.mark.contribtool,
               pytest.mark.website,
               pytest.mark.reboot,
             ]


class TestContribtoolToolsPipeline(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        # setup a web browser
        self.browser.get(self.https_authority)

        self.username,self.password = \
            self.testdata.find_account_for('toolmanager')

        self.utils.account.login_as(self.username,self.password)
        self.po = self.catalog.load_pageobject('ToolsPipelinePage')
        self.po.goto_page()


    def test_search_for_by_full_alias(self):
        """
        check that users can search for tools by their alias.
        """

        # get a list of tool aliases
        aliases = []
        for tool_row in self.po.form.search_result_rows():
            aliases.append(tool_row.value()['alias'])

        assert len(aliases) > 0, \
            'no tools installed, all searches will fail'

        alias = aliases[0]
        self.po.search_for(alias)

        assert self.po.form.search_results.num_rows() >= 1, \
            'searching for alias %s produced no results' % (alias)

        for tool_row in self.po.form.search_result_rows():
            if tool_row.value()['alias'] == alias:
                break
        else:
            pytest.fail('Failed to find tool row for the aliases : %s' % (alias))


    def test_search_for_by_partial_alias(self):
        """
        check that users can search for tools by the first part of their alias.
        """


        # get a list of tool aliases
        aliases = []
        for tool_row in self.po.form.search_result_rows():
            aliases.append(tool_row.value()['alias'])

        assert len(aliases) > 0, \
            'no tools installed, all searches will fail'

        alias = aliases[0]
        search_term = alias[0:3]
        self.po.search_for(search_term)

        assert self.po.form.search_results.num_rows() >= 1, \
            'searching for alias %s produced no results' % (alias)

        for tool_row in self.po.form.search_result_rows():
            if tool_row.value()['alias'] == alias:
                break
        else:
            pytest.fail('Failed to find tool row for the aliases : %s' % (alias))


    def test_filter_alltools_check_counts(self):
        """
        check that all tools are listed when filtering all
        """

        # get the default filtering total number of tools
        (junk,junk,total1) = self.po.get_caption_counts()

        # explicitly filter by all tools
        self.po.form.filteroptions.filter_by_all()

        # get the total number of tools
        (junk,junk,total2) = self.po.get_caption_counts()

        assert total1 == total2, \
            "filtering by all fails to show all tools:" \
            + " inital total = %s, filtered total = %s" \
                % (total1, total2)


    def test_caption_counts_match_shown(self):
        """
        check that the number of tools listed in the caption counts matches
        the number of tools shown on the page
        """

        (start,end,total) = self.po.get_caption_counts()

        expected_shown = end - start + 1

        actual_shown = self.po.form.search_results.num_rows()

        assert expected_shown == actual_shown, \
            'wrong # tools listed on tools pipeline page:' \
            + ' expected %s (%s - %s + 1)' % (expected_shown,end,start) \
            + ' actual listed was %s' % (actual_shown)


    def validate_caption_pagination_counts(self,
        current_url,caption_start,caption_end,caption_total,
        pagination_start,pagination_end,pagination_total):

        assert caption_start == pagination_start, \
            "while checking caption and pagination counts" \
            + " on %s, caption_start is not equal to" % (current_url) \
            + " pagination_start: caption_start  == %s, pagination_start == %s"\
            % (caption_start,pagination_start)

        assert caption_end == pagination_end, \
            "while checking caption and pagination counts" \
            + " on %s, caption_end is not equal to" % (current_url) \
            + " pagination_end: caption_end  == %s, pagination_end == %s"\
            % (caption_end,pagination_end)

        assert caption_total == pagination_total, \
            "while checking caption and pagination counts" \
            + " on %s, caption_total is not equal to" % (current_url) \
            + " pagination_total: caption_total  == %s, pagination_total == %s"\
            % (caption_total,pagination_total)

        assert caption_start <= caption_end, \
            "while checking caption counts on %s," % (current_url) \
            + " caption_start > caption_end," \
            + " caption_start = %s, caption_end = %s" \
            % (caption_start,caption_end)

        assert caption_start <= caption_total, \
            "while checking caption counts on %s," % (current_url) \
            + " caption_start > caption_total," \
            + " caption_start = %s, caption_total= %s" \
            % (caption_start,caption_total)

        assert caption_end <= caption_total, \
            "while checking caption counts on %s," % (current_url) \
            + " caption_end > caption_total," \
            + " caption_end = %s, caption_total= %s"\
            % (caption_end,caption_total)

        assert caption_total >= 0, \
            "while checking caption counts on %s," % (current_url) \
            + " caption_total < 0, caption_total= %s" % (caption_total)

        assert caption_start >= 0, \
            "while checking caption counts on %s," % (current_url) \
            + " caption_start < 0, caption_start = %s" % (caption_start)

        assert caption_end >= 0, \
            "while checking caption counts on %s," % (current_url) \
            + " caption_end < 0, caption_end = %s" % (caption_end)

        assert pagination_start <= pagination_end, \
            "while checking pagination counts on %s," % (current_url) \
            + " pagination_start > pagination_end," \
            + " pagination_start = %s, pagination_end = %s" \
            % (pagination_start,pagination_end)

        assert pagination_start <= pagination_total, \
            "while checking pagination counts on %s," % (current_url) \
            + " pagination_start > pagination_total," \
            + " pagination_start = %s, pagination_total= %s" \
            % (pagination_start,pagination_total)

        assert pagination_end <= pagination_total, \
            "while checking pagination counts on %s," % (current_url) \
            + " pagination_end > pagination_total," \
            + " pagination_end = %s, pagination_total= %s"\
            % (pagination_end,pagination_total)

        assert pagination_total >= 0, \
            "while checking pagination counts on %s," % (current_url) \
            + " pagination_total < 0, pagination_total= %s" \
            % (pagination_total)

        assert pagination_start >= 0, \
            "while checking pagination counts on %s," % (current_url) \
            + " pagination_start < 0, pagination_start = %s" \
            % (pagination_start)

        assert pagination_end >= 0, \
            "while checking pagination counts on %s," % (current_url) \
            + " pagination_end < 0, pagination_end = %s" \
            % (pagination_end)


    def test_compare_caption_pagination_counts_display_default(self):
        """
        compare caption and footer start, end, and total counts
        """

        current_url = self.po.current_url()

        (caption_start,
         caption_end,
         caption_total) = self.po.get_caption_counts()

        (pagination_start,
         pagination_end,
         pagination_total) = self.po.get_pagination_counts()

        self.validate_caption_pagination_counts (
            current_url,caption_start,caption_end,caption_total,
            pagination_start,pagination_end,pagination_total)


    def test_compare_caption_pagination_counts_display_all(self):
        """
        change the display limit to 'All' and compare caption
        and footer start, end, and total counts
        """

        # change the display limit to 'All'
        new_display_limit = 'All'
        self.po.form.footer.display_limit(new_display_limit)

        current_url = self.po.current_url()

        (caption_start,
         caption_end,
         caption_total) = self.po.get_caption_counts()

        (pagination_start,
         pagination_end,
         pagination_total) = self.po.get_pagination_counts()

        self.validate_caption_pagination_counts (
            current_url,caption_start,caption_end,caption_total,
            pagination_start,pagination_end,pagination_total)


    def test_pagination_current_page(self):
        """
        on /tools/pipeline, check pagination current page is 1
        """

        current_page_number = self.po.get_current_page_number()
        assert current_page_number == '1', \
            "after loading the page %s and examining" % (self.po.current_url()) \
            + " the page links, the current page number" \
            + " is '%s', expected '1'" % (current_page_number)


    @pytest.mark.parametrize("display_limit",[None,5])
    def test_pagination_page_links(self,display_limit):
        """
        on /tools/pipeline, check pagination page links
        """

        if display_limit is not None:
            self.po.form.footer.display_limit(display_limit)

        pagenumbers = self.po.get_link_page_numbers()

        while len(pagenumbers) > 0:
            page = int(pagenumbers[0])
            starturl = self.po.current_url()

            # click the link to go to the next page
            self.po.goto_page_number(page)
            endurl = self.po.current_url()

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
                new_pagenumbers = self.po.get_link_page_numbers()
                assert len(new_pagenumbers) != 0, \
                    'retrieving new page numbers failed while evaluating' \
                    + ' page #%s (%s)' % (page,endurl)
                pagenumbers = [int(i) \
                    for i in new_pagenumbers if int(i) > page]
            else:
                pagenumbers = []


    def test_pagination_relative_links_end(self):
        """
        on /tools/pipeline, check pagination relative end link
        """

        pagenumbers = self.po.get_link_page_numbers()

        # FIXME: need a test where we add enough tools to have multiple pages

        if len(pagenumbers) == 0:
            return

        starturl = self.po.current_url()
        self.po.goto_page_relative('end')
        endurl = self.po.current_url()
        assert starturl != endurl, \
            "clicking the 'end' link in pagination did not change pages:" \
            + " starturl = %s, endurl = %s" % (starturl,endurl)

        pagenumbers = self.po.get_link_page_numbers()
        lastpage = pagenumbers[-1]
        current_page = self.po.current_url()

        assert current_page > lastpage, \
            "clicking the 'end' link in pagination did not take the user" \
            + " to the last page: current_page = %s, lastpage = %s" \
            % (current_page,lastpage)


    def test_pagination_relative_links_start(self):
        """
        on /tools/pipeline, check pagination relative start link
        """

        pagenumbers = self.po.get_link_page_numbers()

        # FIXME: need a test where we add enough tools to have multiple pages

        if len(pagenumbers) == 0:
            return

        self.po.goto_page_number(pagenumbers[0])
        starturl = self.po.current_url()
        self.po.goto_page_relative('start')
        endurl = self.po.current_url()
        assert starturl != endurl, \
            "clicking the 'start' link in pagination did not change pages:" \
            + " starturl = %s, endurl = %s" % (starturl,endurl)

        firstpage = "1"

        current_page = self.po.get_current_page_number()
        assert current_page == firstpage, \
            "clicking the 'start' link in pagination did not take the user" \
            + " to the first page: current_page = %s, firstpage = %s" \
            % (current_page,firstpage)


