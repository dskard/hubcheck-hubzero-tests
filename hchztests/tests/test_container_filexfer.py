import pytest
import os
import time
import datetime

import hubcheck
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager


pytestmark = [ pytest.mark.website,
               pytest.mark.container,
               pytest.mark.filexfer,
               pytest.mark.weekly,
               pytest.mark.reboot,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade
             ]


class TestFilexfer(TestCase2):

    def setup_method(self,method):

        # get into a tool session container
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

        # setup file paths
        fxf_fn = 'hcfxf.txt'
        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')
        self.fxf_path = os.path.join(sessiondir,fxf_fn)
        self.localfn = os.path.join(os.getcwd(),'hcfxf.tmp')

        self.expected = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    def teardown_method(self,method):

        if os.path.isfile(self.localfn):
            os.remove(self.localfn)

        try:
            self.ws.execute('rm -f %s' % (self.fxf_path))
        finally:
            # get out of the workspace
            # shut down the ssh connection
            self.ws.close()


    def navigate_browser_to_clientaction_url(self):

        fxflogs,es = self.ws.execute('ls -tr $SESSIONDIR/filexfer*.log')

        assert fxflogs != '', "no filexfer log exists"

        fxflog = fxflogs.split('\n')[-1].strip()

        cmd = 'grep "/usr/bin/clientaction url" %s' % (fxflog)
        ca_urls,es = self.ws.execute(cmd)

        # ca_urls looks something like this:
        # /usr/bin/clientaction url /filexfer/W82sryIu4yaMbyFF/download/hi?token=DueydQ0EXaJcFxGFu5z2
        # /usr/bin/clientaction url /filexfer/W82sryIu4yaMbyFF/download/hi?token=bQnSnHjpnmTrLWZovekO
        #
        # of this, we grab the last clientaction line
        # and split it based on ' ', grabbing the 
        # end of the url:
        # "/filexfer/W82sryIu4yaMbyFF/download/hi?token=bQnSnHjpnmTrLWZovekO"

        url_tail = ca_urls.split('\n')[-1].split(' ')[2].strip()

        # navigate to the url clientaction would have opened
        self.browser.get(self.https_authority+url_tail)


    def start_importfile(self):

        # initiate an importfile filexfer session
        self.ws.execute('importfile %s &' % (self.fxf_path))
        # give the filexfer server 5 seconds to startup
        time.sleep(5)
        self.navigate_browser_to_clientaction_url()

        # upload file text through browser
        FilexferImportfilePage = self.catalog.load('FilexferImportfilePage')
        self.po = FilexferImportfilePage(self.browser,self.catalog)


    @pytest.mark.exportfile
    def test_exportfile_text_file(self):
        """
        export a text file from a tool session container to a browser
        """

        # write file to disk
        self.ws.importfile(self.expected,self.fxf_path,mode=0o600,is_data=True)

        # run exportfile and navigate browser to download page
        self.ws.execute('exportfile %s' % (self.fxf_path))
        self.navigate_browser_to_clientaction_url()

        # grab the downloaded file text
        FilexferExportfilePage = self.catalog.load('FilexferExportfilePage')
        self.po = FilexferExportfilePage(self.browser,self.catalog)
        received = self.po.get_file_text()

        assert self.expected == received, \
            "exported data does not match file data in tool session container:" \
            + "expected: \"%s\" received: \"%s\"" % (self.expected,received)


    @pytest.mark.importfile
    def test_importfile_text(self):
        """
        import text from a browser to a tool session container
        """

        self.start_importfile()

        # upload text through browser
        received = self.po.upload_text(self.expected)

        # read the file from the tool session container
        received,es = self.ws.execute('cat %s' % (self.fxf_path))

        assert self.expected == received, \
            "imported data does not match file data in tool session container:" \
            + "expected: \"%s\" received: \"%s\"" % (self.expected,received)

        #FIXME: check owner and file permission 0644


    @pytest.mark.importfile
    def test_importfile_text_file(self):
        """
        import text file from a browser to a tool session container
        """

        self.start_importfile()

        # write file to disk and upload file through browser
        with open(self.localfn, 'w') as f:
            f.write(self.expected)
        received = self.po.upload_file(self.localfn)

        # read the file from the tool session container

        received,es = self.ws.execute('cat %s' % (self.fxf_path))

        assert self.expected == received, \
            "imported data does not match file data in tool session container:" \
            + "expected: \"%s\" received: \"%s\"" % (self.expected,received)

        #FIXME: check owner and file permission 0644


