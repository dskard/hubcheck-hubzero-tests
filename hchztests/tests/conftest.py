import pytest
import time
import re
import os

import hubcheck

def pytest_addoption(parser):
    parser.addoption(
        "--rappture_version",
        action="store",
        default='',
        help="use a specific version of rappture like 'dev' or 'nightly'")

    parser.addoption(
        "--delay",
        action="store",
        default=0,
        type=float,
        help="time (in seconds) to delay between each test")

    parser.addoption(
        "--repeat",
        action="store",
        default=1,
        type=int,
        help="number of times to repeat each test")


def pytest_generate_tests(metafunc):

    if metafunc.config.option.repeat > 1:
        for i in range(metafunc.config.option.repeat):
            metafunc.addcall()


def pytest_runtest_setup(item):
    delay = pytest.config.getoption("--delay")
    if delay > 0:
        time.sleep(delay)


def pytest_runtest_makereport(item, call, __multicall__):
    # execute all other hooks to obtain the report object
    rep = __multicall__.execute()

    # we only look at actual failing test calls, not setup/teardown
    if rep.when == "call" and rep.failed:
        setattr(item,'rep_take_screenshot',True)
    else:
        setattr(item,'rep_take_screenshot',False)

    return rep


@pytest.fixture(autouse=True)
def finalize_take_screenshot_on_error(request):
    """
    if the test case failed, take a screenshot of the browser
    """

    def fin():
        if hasattr(request.node,'rep_take_screenshot') is False \
           or request.node.rep_take_screenshot is False:
            return

        self = request.instance
        if self.screenshotfn is not None:
            if hasattr(self,'browser') and self.browser is not None:
                try:
                    self.browser.take_screenshot(self.screenshotfn)
                except Exception:
                    self.logger.debug('Exception ignored: %s %s'
                        % (sys.exc_info()[1],sys.exc_info()[2]))


    request.addfinalizer(fin)



@pytest.fixture(scope="class")
def rappture_version(request):
    rpversion = 'rappture'
    # accept rappture versions that match
    # dev, nightly-trunk, nightly-branch-x.x
    # where x is an integer
    match = re.search('^(dev|nightly-(trunk|(branch-\d+(\.\d+)?)))$',
                      request.config.getoption("--rappture_version"))
    if match is not None:
        rpversion = 'rappture-' + request.config.getoption("--rappture_version")

    request.cls.rappture_version = rpversion


@pytest.fixture(scope="session")
def testdata():

    testdata = hubcheck.conf.Testdata().load(
                hubcheck.conf.settings.tdfname,
                hubcheck.conf.settings.tdpass )

    return testdata


@pytest.fixture(scope="session")
def locators(testdata):

    locators = testdata.get_locators()

    return locators


@pytest.fixture(scope="session")
def urls(testdata):

    urls = {}

    # setup the https authority
    urls['https_uri'] = testdata.find_url_for('https')
    urls['https_port'] = testdata.find_url_for('httpsport')

    if urls['https_port'] == 443:
        urls['https_authority'] = "https://%s" % (urls['https_uri'])
    else:
        urls['https_authority'] = "https://%s:%s" % (urls['https_uri'],
                                                     urls['https_port'])

    # setup the http authority
    urls['http_uri'] = testdata.find_url_for('http')
    urls['http_port'] = testdata.find_url_for('httpport')

    if urls['http_port'] == 80:
        urls['http_authority'] = "http://%s" % (urls['http_uri'])
    else:
        urls['http_authority'] = "http://%s:%s" % (urls['http_uri'],
                                                   urls['http_port'])

    return urls

@pytest.fixture(scope='class')
def screenshotfn(request):

    fn = None

    fnbase = request.cls.__name__

    if hubcheck.conf.settings.screenshot_dir is not None:
        ssdir = os.path.abspath(
                    os.path.expanduser(
                        os.path.expandvars(
                            hubcheck.conf.settings.screenshot_dir)))

        fn = os.path.join(ssdir,"%s.png" % (fnbase))

    return fn


@pytest.fixture(scope='class')
def videofn(request):

    fn = None

    fnbase = request.cls.__name__

    if hubcheck.conf.settings.video_dir is not None:
        videodir = os.path.abspath(
                    os.path.expanduser(
                        os.path.expandvars(
                            hubcheck.conf.settings.video_dir)))
        fn = os.path.join(videodir,"%s.mp4" % (fnbase))

    return fn


@pytest.fixture(scope='session')
def hc(request,testdata,locators,urls):

    hc = hubcheck.Hubcheck(urls['https_uri'],
                           urls['http_port'],
                           urls['https_port'],
                           locators)

    return hc


def _confirm_approve_tool(catalog):
    """
    confirm tool version, license, and tool info
    when changing tool state to "Approved"
    """

    # confirm the version
    po = catalog.load_pageobject('ToolsStatusApproveConfirmVersionPage')
    version = po.version_form.version.value
    try:
        version = float(version) + 0.01
    except:
        version = int(time.time())
    po.version_form.submit_form({'version':str(version)})


    # confirm the license
    po = catalog.load_pageobject('ToolsStatusApproveConfirmLicensePage')
    po.license_form.submit_form([('sourceaccess','open source'),
                                 ('templates','custom'),
                                 ('licensetext','.'),
                                 ('authorize',True)])

    # confirm the license
    po = catalog.load_pageobject('ToolsStatusApproveConfirmToolInfoPage')
    po.approve_tool()


def _setup_tool_state_x(request,hc,testdata,urls,videofn,state_name,
                        post_state_change_callback=None):
    """login as the toolmanager and make sure the
       tool is in the provided state.

       state_name is one of Registered, Created, Uploaded,
       Installed, Approved, Published
    """

    cls = {'Registered' : 'ToolsStatusRegisteredAdminPage',
           'Created'    : 'ToolsStatusCreatedAdminPage',
           'Uploaded'   : 'ToolsStatusUploadedAdminPage',
           'Installed'  : 'ToolsStatusInstalledAdminPage',
           'Approved'   : 'ToolsStatusApprovedAdminPage',
           'Published'  : 'ToolsStatusPublishedAdminPage'}

    state_cls = cls[state_name]

    tooldata = request.module.TOOLDATA
    toolname = request.module.TOOLNAME

    # start recording, start browser, login
    recording = hubcheck.utils.WebRecordXvfb(videofn)
    recording.start()

    hc.browser.get(urls['https_authority'])

    try:
        username,password = testdata.find_account_for('toolmanager')
        hc.utils.account.login_as(username,password)

        # navigate to the tools pipeline page
        # and find the tool resource page
        try:
            hc.utils.contribtool.goto_tool_status_page(toolname)
        except hubcheck.exceptions.NavigationError as e:
            # tool not found, register the tool
            po = hc.catalog.load_pageobject('GenericPage',toolname)
            po.goto_logout()

            username,password = testdata.find_account_for('toolsubmitter')

            hc.utils.account.login_as(username,password)
            hc.utils.contribtool.register(toolname,tooldata)

            po.goto_logout()

            username,password = testdata.find_account_for('toolmanager')
            hc.utils.account.login_as(username,password)

        # place the tool in the requested state
        po = hc.catalog.load_pageobject(state_cls,toolname)

        if po.get_tool_state() != state_name:
            po.submit_form({'status':state_name})

            if post_state_change_callback is not None:
                post_state_change_callback(hc.catalog)

        # logout, close browser, stop recording
        po.goto_logout()

    finally:
        hc.browser.close()

        recording.stop()


@pytest.fixture(scope='class')
def setup_tool_state_registered(request,hc,testdata,urls,videofn):
    """login as the toolmanager and make sure the
       tool is in the registered state.
    """

    _setup_tool_state_x(request,hc,testdata,urls,videofn,'Registered')


@pytest.fixture(scope='class')
def setup_tool_state_created(request,hc,testdata,urls,videofn):
    """login as the toolmanager and make sure the
       tool is in the created state.
    """

    _setup_tool_state_x(request,hc,testdata,urls,videofn,'Created')


@pytest.fixture(scope='class')
def setup_tool_state_uploaded(request,hc,testdata,urls,videofn):
    """login as the toolmanager and make sure the
       tool is in the uploaded state.
    """

    _setup_tool_state_x(request,hc,testdata,urls,videofn,'Uploaded')


@pytest.fixture(scope='class')
def setup_tool_state_installed(request,hc,testdata,urls,videofn):
    """login as the toolmanager and make sure the
       tool is in the installed state.
    """

    _setup_tool_state_x(request,hc,testdata,urls,videofn,'Installed')


@pytest.fixture(scope='class')
def setup_tool_state_approved(request,hc,testdata,urls,videofn):
    """login as the toolmanager and make sure the
       tool is in the approved state.
    """

    # FIXME: could probably reach into the calling class and pick up
    #        custom values for the version form and license form and
    #        feed them into cb()

    from selenium.common.exceptions import TimeoutException

    try:
        _setup_tool_state_x(request,hc,testdata,urls,videofn,'Approved',
                            _confirm_approve_tool)
    except TimeoutException:

        # there is a bug in contribtool that sends the user back to the tool
        # status page after updating the tool version.
        # to get around this bug, we try to change the status again.

        _setup_tool_state_x(request,hc,testdata,urls,videofn,'Approved',
                            _confirm_approve_tool)


@pytest.fixture(scope='class')
def setup_tool_state_published(request,hc,testdata,urls,videofn):
    """login as the toolmanager and make sure the
       tool is in the published state.
    """

    _setup_tool_state_x(request,hc,testdata,urls,videofn,'Published')





#@pytest.fixture(scope='class')
#def setup_tool_state_created(request):
#    """
#    login as the toolmanager and make sure the
#    tool is in the created state.
#    """
#
#    # FIXME: fails here because request.instance is None
#    self = request.instance
#
#    tooldata = request.module.TOOLDATA
#    toolname = request.module.TOOLNAME
#
#    self.browser.get(self.https_authority)
#
#    adminuser,adminpass = self.testdata.find_account_for('toolmanager')
#    self.utils.account.login_as(adminuser,adminpass)
#
#    try:
#        # navigate to the tools pipeline page
#        # and find the tool resource page
#        try:
#            self.utils.contribtool.goto_tool_status_page(toolname)
#        except hubcheck.exceptions.NavigationError as e:
#            # tool not found, register the tool
#            po = self.catalog.load_pageobject('GenericPage',toolname)
#            po.goto_logout()
#
#            username,password = self.testdata.find_account_for('toolsubmitter')
#
#            self.utils.account.login_as(username,password)
#            self.utils.contribtool.register(toolname,tooldata)
#
#            po.goto_logout()
#
#            self.utils.account.login_as(adminuser,adminpass)
#
#        # place the tool in the created state if needed
#        po = self.catalog.load_pageobject(
#                'ToolsStatusCreatedAdminPage',toolname)
#
#        if po.get_tool_state() != 'Created':
#            po.submit_form({'status':'Created'})
#
#    finally:
#        po.goto_logout()


def finalize_set_tool_state_x(request,state_name,
                              post_state_change_callback=None):
    """
    at the end of a test, login as the toolmanager
    and set the tool state to the provided state_name.

    state_name is one of Registered, Created, Uploaded,
    Installed, Approved, Published

    post_state_change_callback is a callback that is run
    after a state change
    """

    cls = {'Registered' : 'ToolsStatusRegisteredAdminPage',
           'Created'    : 'ToolsStatusCreatedAdminPage',
           'Uploaded'   : 'ToolsStatusUploadedAdminPage',
           'Installed'  : 'ToolsStatusInstalledAdminPage',
           'Approved'   : 'ToolsStatusApprovedAdminPage',
           'Published'  : 'ToolsStatusPublishedAdminPage'}

    state_cls = cls[state_name]

    def fin():
        self = request.instance

        toolname = request.module.TOOLNAME

        # we don't record the xvfb because this should be run at the
        # end of a test function, which should already be recording.

        self.browser.get(self.https_authority)

        # log out if needed
        po = self.catalog.load_pageobject('GenericPage')
        if po.is_logged_in():
            self.utils.account.logout()

        # login as the tool manager
        username,password = self.testdata.find_account_for('toolmanager')
        self.utils.account.login_as(username,password)

        # navigate to the tools pipeline page
        # and find the tool resource page
        self.utils.contribtool.goto_tool_status_page(toolname)

        # place the tool in the created state
        po = self.catalog.load_pageobject(state_cls,toolname)

        if po.get_tool_state() != state_name:
            po.submit_form({'status':state_name})

            if post_state_change_callback is not None:
                post_state_change_callback(self.catalog)

        po.goto_logout()

    request.addfinalizer(fin)


@pytest.fixture(scope='function')
def finalize_set_tool_state_created(request):
    """
    at the end of a test, login as the toolmanager
    and set the tool state to created.
    """

    finalize_set_tool_state_x(request,'Created')


@pytest.fixture(scope='function')
def finalize_set_tool_state_installed(request):
    """
    at the end of a test, login as the toolmanager
    and set the tool state to installed.
    """

    finalize_set_tool_state_x(request,'Installed')


@pytest.fixture(scope='function')
def finalize_set_tool_state_approved(request):
    """
    at the end of a test, login as the toolmanager
    and set the tool state to approved.
    """

    finalize_set_tool_state_x(request,'Approved',_confirm_approve_tool)


@pytest.fixture(scope='function')
def finalize_set_tool_state_published(request):
    """
    at the end of a test, login as the toolmanager
    and set the tool state to published.
    """

    finalize_set_tool_state_x(request,'Published')


@pytest.fixture(scope='function')
def setup_clear_tool_repository(request):
    """
    delete any files in the hubzero tool repository,
    leaving only the original directory structure
    and the (possibly modified) invoke script
    """

    self = request.instance
    toolname = request.module.TOOLNAME
    hubname = self.testdata.find_url_for('https')

    username,userpass = self.testdata.find_account_for('toolmanager')

    cm = hubcheck.shell.ContainerManager()

    # login to a tool session container
    ws = cm.access(host=hubname,
                   username=username,
                   password=userpass)

    # check out the tool's source code repository
    repo_url_template = 'https://%(hubname)s/tools/%(toolname)s/svn/trunk'
    repo_url = repo_url_template % {
                    'hubname'  : hubname,
                    'toolname' : toolname,
               }
    repo = hubcheck.actionobjects.contribtool.Subversion(ws,username,userpass)
    revision = repo.checkout(repo_url,toolname)

    # find all of the files in the repository
    ws.execute('cd %s' % (toolname))
    files,err = ws.execute('find . -type f -not -path "*/.svn/*"')
    files = files.split()

    # remove the ./middleware/invoke script from the file list
    files.remove('./middleware/invoke')

    # mark the files as deleted in the local copy of the repository
    repo.remove(files)

    # commit the changes to the repo server
    repo.commit('clearing the files from the repository')


@pytest.fixture(scope='function')
def setup_populate_tool_repository(request):
    """
    make sure the tool's files are in the hubzero tool repository
    """

    self = request.instance
    toolname = request.module.TOOLNAME
    toolfiledata = request.module.TOOLFILEDATA
    hubname = self.testdata.find_url_for('https')

    username,userpass = self.testdata.find_account_for('toolsubmitter')

    # upload code into the repository
    msg = 'uploading copy of tool code'
    self.utils.contribtool.upload_code(
        toolname,toolfiledata,username,userpass,msg)


@pytest.fixture(scope='session')
def tag_browse_pagination_counts(request,hc,urls):
    """
    retrieve the pagination counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        counts = po.get_pagination_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_browse_caption_counts(request,hc,urls):
    """
    retrieve the caption counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        counts = po.get_caption_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_browse_pagination_counts_all(request,hc,urls):
    """
    retrieve the pagination counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # change the display limit to 'All'
        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        counts = po.get_pagination_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_browse_caption_counts_all(request,hc,urls):
    """
    retrieve the caption counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsBrowsePage')
        po.goto_page()

        # change the display limit to 'All'
        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        counts = po.get_caption_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_with_items(request,hc,urls):
    """
    go through the tags and find one that has visible items associated with it
    """

    hc.browser.get(urls['https_authority'])

    try:
        tag_name = hc.utils.tags.find_tag_with_items()

    finally:
        hc.browser.close()

    assert tag_name is not None, 'Could not find tag with items'
    return tag_name


@pytest.fixture(scope='session')
def tag_view_pagination_counts(request,hc,urls,tag_with_items):
    """
    retrieve the pagination counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([tag_with_items])

        po = hc.catalog.load_pageobject('TagsViewPage')

        # counts has (pagination_start, pagination_end, pagination_total)

        counts = po.get_pagination_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_view_caption_counts(request,hc,urls,tag_with_items):
    """
    retrieve the caption counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([tag_with_items])

        po = hc.catalog.load_pageobject('TagsViewPage')

        # counts has (caption_start, caption_end, caption_total)

        counts = po.get_caption_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_view_pagination_counts_all(request,hc,urls,tag_with_items):
    """
    retrieve the pagination counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([tag_with_items])

        po = hc.catalog.load_pageobject('TagsViewPage')

        # counts has (pagination_start, pagination_end, pagination_total)

        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        counts = po.get_pagination_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r


@pytest.fixture(scope='session')
def tag_view_caption_counts_all(request,hc,urls,tag_with_items):
    """
    retrieve the caption counts for a tag
    """

    hc.browser.get(urls['https_authority'])

    try:
        po = hc.catalog.load_pageobject('TagsPage')
        po.goto_page()
        po.search_for_content([tag_with_items])

        po = hc.catalog.load_pageobject('TagsViewPage')

        # counts has (caption_start, caption_end, caption_total)

        new_display_limit = 'All'
        po.form.footer.display_limit(new_display_limit)

        counts = po.get_caption_counts()

        current_url = po.current_url()

    finally:
        hc.browser.close()

    r = {'start'    : counts[0],
         'end'      : counts[1],
         'total'    : counts[2],
         'url'      : current_url}

    return r
