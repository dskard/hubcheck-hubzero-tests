#! /usr/bin/env python

import sys
import os
import urllib
import re
import pytest
import time

import hubcheck
from hubcheck.exceptions import HCException
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager
from hubcheck.shell import ToolSession


pytestmark = [ pytest.mark.website,
               pytest.mark.container,
               pytest.mark.reboot,
               pytest.mark.weekly,
               pytest.mark.upgrade,
               pytest.mark.prod_safe_upgrade,
               pytest.mark.parampass,
             ]


TESTDATA = ''
TOOL_NAME = "hppt"
TOOL_REVISION = 2
INVOKE_APP_PATH = '/usr/bin/invoke_app'
TEST_PROGRAM_PARAMS_FNAME = "pp.out"
TEST_PROGRAM_NAME = 'printparams'
TEST_PROGRAM_SCRIPT = """#!/bin/sh
# \\
exec wish "$0" ${1+"$@"}

set params_file_out %(outfile)s
set fid [open $params_file_out w]
puts -nonewline $fid $argv
close $fid

label .text -text "Running..."
button .close -text "Quit" -command {exit 1}
pack .text -side top
pack .close -side top
""" % {'outfile':TEST_PROGRAM_PARAMS_FNAME}


class BadParameterError(HCException):
    pass


class HarStatusError(HCException):
    pass


class GroupMembershipError(HCException):
    pass


class SessionInvokeError(HCException):
    pass


def setup_tool(shell,tool_name,tool_revision,invoke_script,
               test_program_name,test_program_script):
    """
    install code to test parameter passing. the tool revision provided to
    this function will be overwritten with a tool that accepts parameters
    on the command line and prints out the parameter list to the file
    TEST_PROGRAM_PARAMS_FNAME. users can examine the TEST_PROGRAM_PARAMS_FNAME
    file to compare what was sent to invoke_app with the parameter list the
    tool was executed with.
    """

    # check that the user is in the apps group
    groups,es = shell.execute("echo ${USER} | groups")
    if "apps" not in groups.split():
        # user not in the apps group, bail
        username,es = shell.execute("echo ${USER}")
#        raise RuntimeError("user %s not in apps group: %s" % (username,groups))
        raise GroupMembershipError("user %s not in apps group: %s" % (username,groups))

    # become the apps user
    shell.send('sudo su - apps')
    shell.start_bash_shell()

    tool_revision_string = "r%s" % (tool_revision)
    tool_path = "/apps/%s/%s" % (tool_name, tool_revision_string)
    dev_path = "/apps/%s/dev" % (tool_name)

    # setup the new tool's invoke script
    #    mv %(tool_path)s %(tmp_tool_path)s;
    # tmp_tool_path = tool_path + ".old"
    # """ % {'tool_path' : tool_path, 'tmp_tool_path' : tmp_tool_path}
    script = """
        rm -rf %(tool_path)s;
        mkdir %(tool_path)s;
        rm -f %(dev_path)s;
        ln -s %(tool_path)s %(dev_path)s;
        cd %(tool_path)s;
        mkdir middleware bin;
    """ % {'tool_path'  : tool_path,
           'dev_path'   : dev_path}

    commands = script.strip().split('\n')
    shell.execute(commands)

    # write the invoke script to disk
    shell.write_file('middleware/invoke', invoke_script)
    shell.execute('chmod 755 middleware/invoke')

    # write the test program to disk
    shell.write_file("bin/%s" % (test_program_name), test_program_script)
    shell.execute("chmod 755 bin/%s" % (test_program_name))

    # exit from apps user
    shell.stop_bash_shell()
    shell.send('exit')


def setup_datafiles(shell,params_info):
    """
    write the datafiles to disk
    build the parameters file
    """

    parameters_text_items = []
    for key,value in params_info.items():
        shell.write_file(value['path'], value['text'])
        parameters_text_items.append("%s:%s" % (value['type'],value['path']))

    # generate the parameters file to feed into the url
    parameters_text = '\n'.join(parameters_text_items)

    return parameters_text


def launch_tool(https_authority,username,password,browser,catalog,utils,tool_name,
                tool_revision,parameters_text,add_empty_params=False):
    """
    launch the test/dev version of a tool to test parameter passing

    we launch the test version so we don't have to publish a tool
    just for testing parameter passing.
    """

    # login to the hub
    utils.account.login_as(username,password)

    # go to the page to launch the tool
    # with the parameters encoded in the url
    GenericPage = catalog.load('GenericPage')
    po = GenericPage(browser,catalog)

    # quote() is for escaping the path portion of the url
    # quote_plus() is for escaping the query portion of the url
    # and handles escaping / to %2F, but turns spaces into +'s
    encoded_parameters = urllib.quote_plus(parameters_text.encode('utf8'))

    url = "%(https_authority)s/tools/%(toolname)s/invoke/%(toolrev)s"

    if encoded_parameters != '' or add_empty_params:
        url += "?params=%(params)s"

    # hard code tool revision to test so we don't have to publish the tool
    tool_revision = 'test'

    url = url % {'https_authority' : https_authority,
                 'toolname' : tool_name,
                 'toolrev' : tool_revision,
                 'params' : encoded_parameters,}

    # print "parameters_text = %s" % (parameters_text)
    # print "url = %s" % (url)

    # launch the tool
    browser.proxy_client.new_har("page link")
    po.goto_page(url)
    har_entry = browser.page_load_details()

    if browser.error_loading_page(har_entry):
        # the tool session container may still start,
        # even if the har status is not 200 level
        # try to close it before raising the error

        har_status = har_entry['response']['status']
        # print har_status
        raise HarStatusError("unexpected error while launching tool: %s" % (har_status))

    # include a check for 'Bad Parameters' error box in html
    # because the error page returns status of 200
    for msg in po.get_errorbox_info():
        if 'bad parameters' in msg.lower():
            raise BadParameterError(
                "found a 'Bad Parameters' error box in the html of" \
                + " %s while passing parameters: %s\n%s" \
                % (url,parameters_text,msg))

    # one last check for middleware errors that take the user back to
    # the member's dashboard page. middleware can't send messages back
    # to the web server, so we get the message "Failed to invoke session"
    loc = 'css=dd.error'
    if po.is_displayed(loc):
        # there is an error message displayed
        e = po.find_element(loc)
        msg = e.text
        raise SessionInvokeError(msg)

    # get the session number from the tool session page
    ToolSessionPage = catalog.load('ToolSessionPage')
    po = ToolSessionPage(browser,catalog)
    tool_session_number = po.get_session_number()

    return tool_session_number


def retrieve_container_parameters(shell):

    parameters_text = ''

    # figure out what the TOOL_PARAMETERS environment variable is
    # by looking at the command that started the tool session
    # container.
    container_cmd,es = shell.execute('ps aux | grep TOOL_PARAMETERS')

    # container_cmd should at least contain the grep
    # fish out the assignment
    # if there is no assignment, return an empty string

    matches = re.search('TOOL_PARAMETERS=([^\s]+)',container_cmd)

    if matches:
        tool_parameters_filename = matches.group(1)
        parameters_text = shell.read_file(tool_parameters_filename)

    return parameters_text


def retrieve_program_output(shell,params_out_fname):

    fpath = '${SESSIONDIR}/%s' % (params_out_fname)
    count = 0

    # wait for the file to exist on disk for systems with slow nfs
    # if the file never appears, error out in the read_file() method

    while (count < 5) and shell.bash_test('-e %s' % (fpath)) is False:
        time.sleep(5)
        count = count + 1

    parameters_out = shell.read_file(fpath)
    return parameters_out


def shrink_space(data):
    """
    perform newline normalization on data
    """
    # remove leading and trailing spaces
    data = data.strip()
    # collapse multiple lines to one single line
    data = re.sub("\n+","\n",data)

    return data


def pass_parameters(apps_shell,reg_shell,invoke_script,params_info,
                    https_authority,reguser,regpass,browser,catalog,utils):

    # as the apps user, setup a fake tool
    setup_tool(apps_shell,TOOL_NAME,TOOL_REVISION,invoke_script,
               TEST_PROGRAM_NAME,TEST_PROGRAM_SCRIPT)

    # as the registered user, setup a datafiles that were
    # referenced by parameter passing
    parameters_text = setup_datafiles(reg_shell,params_info)

    # as the registered user, launch the session, passing parameters
    sessnum = launch_tool(https_authority,reguser,regpass,browser,catalog,utils,
                TOOL_NAME,TOOL_REVISION,parameters_text)

    return (sessnum,parameters_text)


@pytest.mark.registereduser
@pytest.mark.appsuser
class TestParameterPassingInvokeApp(TestCase2):

    def setup_method(self,method):

        self.remove_files = []

        # get user account info
        self.reguser,self.regpass = self.testdata.find_account_for('registeredworkspace')
        self.appsuser,self.appspass = self.testdata.find_account_for('appsworkspace')
        hubname = self.testdata.find_url_for('https')

        # setup a web browser
        self.browser.get(self.https_authority)

        # setup access to tool session containers
        cm = ContainerManager()

        self.reg_ws = cm.access(host=hubname,
                                username=self.reguser,
                                password=self.regpass)

        self.apps_ws = cm.access(host=hubname,
                                 username=self.appsuser,
                                 password=self.appspass,
                                 toolname=hubcheck.conf.settings.apps_workspace_toolname)

        self.session = ToolSession(
            host=hubname, username=self.reguser, password=self.regpass)

        self.reg_ws.execute('cd $SESSIONDIR')

        # get a list of session open before the test was run
        # incase the test fails unexpectedly, we can cleanup
        self.existing_sessions = self.session.get_open_session_detail()
        self.close_sessions = []

    def teardown_method(self,method):

        # exit the workspace
        # shut down the ssh connection
        self.reg_ws.close()
        self.apps_ws.close()

        # see if we can find any sessions accidentally left open.
        open_sessions = self.session.get_open_session_detail()
        open_sessions_numbers = []

        for row in open_sessions.values():
            open_sessions_numbers.append(row['session_number'])
            if re.search(TOOL_NAME,row['name']) is not None:
                # we found an open session that matches the name of our test tool
                # check if it was open before we started the test.
                old_session = False
                for existing_row in self.existing_sessions.values():
                    if existing_row['session_number'] == row['session_number']:
                        old_session = True
                        break
                if old_session is False:
                    # we found a session that was not open when the test started
                    # but is open now. there is a small chance it was opened by
                    # someone else.
                    # check if it is already in the list of sessions to be closed,
                    # if not, add the session to the list
                    if row['session_number'] not in self.close_sessions:
                        self.close_sessions.append(row['session_number'])

        # close the parampass tool's container
        for session_number in self.close_sessions:
            # check if the session is still open before closing it
            if session_number in open_sessions_numbers:
                self.session.stop(session_number)

        del self.session


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_1_command_no_templates_no_parameters_file(self):
        """
        launch a tool with an invoke script with one -C option that is not
        templated. do not create a parameters file.
        """

        invoke_script = """#!/bin/sh
        %(invoke_app_path)s -C %(test_program)s
        """ % {'invoke_app_path' : INVOKE_APP_PATH,
               'test_program' : TEST_PROGRAM_NAME}

        params_info = {
        }

        expected_parameters = ''

        sessnum,parameters_text = pass_parameters(self.apps_ws, self.reg_ws,
                                      invoke_script, params_info,
                                      self.https_authority, self.reguser,
                                      self.regpass, self.browser,
                                      self.catalog, self.utils)

        self.close_sessions.append(sessnum)

        # log into the tool session container to get the list of parameters
        # passed into the test program. we check that the paramaters were
        # all found in our original parameters file we generated earlier.

        ws = self.session.access(session_number=sessnum)
        ws.execute('echo $SESSION')

        ws_params_text = retrieve_container_parameters(ws)
        ws_params_out = retrieve_program_output(ws,TEST_PROGRAM_PARAMS_FNAME)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))

        # check that toolparams started the correct tool based on
        # parameters passed into the container.
        assert expected_parameters == ws_params_out, \
            "expected parameters: %s\nreceived parameters: %s" \
            % (repr(expected_parameters),repr(ws_params_out))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_1_command_no_templates_with_parameters_file(self):
        """
        launch a tool with an invoke script with one -C option that is not
        templated. create a parameters file. no parameters should be passed
        to the test program.
        """

        homedir,es = self.reg_ws.execute('echo ${HOME}')

        invoke_script = """#!/bin/sh
        %(invoke_app_path)s -C %(test_program)s
        """ % {'invoke_app_path' : INVOKE_APP_PATH,
               'test_program' : TEST_PROGRAM_NAME}

        params_info = {
            'datafile1' : {
                'text' : 'this is datafile1',
                'type' : 'file(datafile1)',
                'path' : "%s/datafile1" % (homedir),
            },
        }

        expected_parameters = ''

        sessnum,parameters_text = pass_parameters(self.apps_ws, self.reg_ws,
                                      invoke_script, params_info,
                                      self.https_authority, self.reguser,
                                      self.regpass, self.browser,
                                      self.catalog, self.utils)

        self.close_sessions.append(sessnum)

        # log into the tool session container to get the list of parameters
        # passed into the test program. we check that the paramaters were
        # all found in our original parameters file we generated earlier.

        ws = self.session.access(session_number=sessnum)
        ws.execute('echo $SESSION')

        ws_params_text = retrieve_container_parameters(ws)
        ws_params_out = retrieve_program_output(ws,TEST_PROGRAM_PARAMS_FNAME)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))

        # check that toolparams started the correct tool based on
        # parameters passed into the container.
        assert expected_parameters == ws_params_out, \
            "expected parameters: %s\nreceived parameters: %s" \
            % (repr(expected_parameters),repr(ws_params_out))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_1_template_1_default_run_default(self):
        """
        launch a tool with an invoke script with two -C options. the first
        -C option is templated and accepts a named file. the second -C option
        is not templated. invoke_app should make the non-templated command the
        default option for toolparams. toolparams should run the default option
        because there is no TOOL_PARAMETERS file and no templates will match.
        no TOOL_PARAMETERS file will be created. no parameters should be passed
        to the test program.
        """

        invoke_script = """#!/bin/sh
        %(invoke_app_path)s -C "%(test_program)s @@file(datafile1)" -C %(test_program)s
        """ % {'invoke_app_path' : INVOKE_APP_PATH,
               'test_program' : TEST_PROGRAM_NAME}

        params_info = {
        }

        expected_parameters = ''

        sessnum,parameters_text = pass_parameters(self.apps_ws, self.reg_ws,
                                      invoke_script, params_info,
                                      self.https_authority, self.reguser,
                                      self.regpass, self.browser,
                                      self.catalog, self.utils)

        self.close_sessions.append(sessnum)

        # log into the tool session container to get the list of parameters
        # passed into the test program. we check that the paramaters were
        # all found in our original parameters file we generated earlier.

        ws = self.session.access(session_number=sessnum)
        ws.execute('echo $SESSION')

        ws_params_text = retrieve_container_parameters(ws)
        ws_params_out = retrieve_program_output(ws,TEST_PROGRAM_PARAMS_FNAME)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))

        # check that toolparams started the correct tool based on
        # parameters passed into the container.
        assert expected_parameters == ws_params_out, \
            "expected parameters: %s\nreceived parameters: %s" \
            % (repr(expected_parameters),repr(ws_params_out))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_1_template_1_default_run_template(self):
        """
        launch a tool with an invoke script with two -C options. the first
        -C option is templated and accepts a named file. the second -C option
        is not templated. invoke_app should make the non-templated command the
        default option for toolparams. toolparams should run the templated option
        because it will match a value in the TOOL_PARAMETERS file.
        one parameter should be passed to the test program.
        """

        homedir,es = self.reg_ws.execute('echo ${HOME}')

        invoke_script = """#!/bin/sh
        %(invoke_app_path)s -C "%(test_program)s @@file(datafile1)" -C %(test_program)s
        """ % {'invoke_app_path' : INVOKE_APP_PATH,
               'test_program' : TEST_PROGRAM_NAME}

        params_info = {
            'datafile1' : {
                'text' : 'this is datafile1',
                'type' : 'file(datafile1)',
                'path' : "%s/datafile1" % (homedir),
            },
        }

        expected_parameters = params_info['datafile1']['path']

        sessnum,parameters_text = pass_parameters(self.apps_ws, self.reg_ws,
                                      invoke_script, params_info,
                                      self.https_authority, self.reguser,
                                      self.regpass, self.browser,
                                      self.catalog, self.utils)

        self.close_sessions.append(sessnum)

        # log into the tool session container to get the list of parameters
        # passed into the test program. we check that the paramaters were
        # all found in our original parameters file we generated earlier.

        ws = self.session.access(session_number=sessnum)
        ws.execute('echo $SESSION')

        ws_params_text = retrieve_container_parameters(ws)
        ws_params_out = retrieve_program_output(ws,TEST_PROGRAM_PARAMS_FNAME)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))

        # check that toolparams started the correct tool based on
        # parameters passed into the container.
        assert expected_parameters == ws_params_out, \
            "expected parameters: %s\nreceived parameters: %s" \
            % (repr(expected_parameters),repr(ws_params_out))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_1_template_0_default_run_template_1(self):
        """
        launching a tool with an invoke script with one -C template command
        should launch toolparams to run the command. toolparams
        should launch the tool with the templated argument.
        """

        homedir,es = self.reg_ws.execute('echo ${HOME}')

        invoke_script = """#!/bin/sh
        %(invoke_app_path)s -C "%(test_program)s @@file(datafile1)"
        """ % {'invoke_app_path' : INVOKE_APP_PATH,
               'test_program' : TEST_PROGRAM_NAME}

        params_info = {
            'datafile1' : {
                'text' : 'this is datafile1',
                'type' : 'file(datafile1)',
                'path' : "%s/datafile1" % (homedir),
            },
        }

        expected_parameters = params_info['datafile1']['path']

        sessnum,parameters_text = pass_parameters(self.apps_ws, self.reg_ws,
                                      invoke_script, params_info,
                                      self.https_authority, self.reguser,
                                      self.regpass, self.browser,
                                      self.catalog, self.utils)

        self.close_sessions.append(sessnum)

        # log into the tool session container to get the list of parameters
        # passed into the test program. we check that the paramaters were
        # all found in our original parameters file we generated earlier.

        ws = self.session.access(session_number=sessnum)
        ws.execute('echo $SESSION')

        ws_params_text = retrieve_container_parameters(ws)
        ws_params_out = retrieve_program_output(ws,TEST_PROGRAM_PARAMS_FNAME)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))

        # check that toolparams started the correct tool based on
        # parameters passed into the container.
        assert expected_parameters == ws_params_out, \
            "expected parameters: %s\nreceived parameters: %s" \
            % (repr(expected_parameters),repr(ws_params_out))


@pytest.mark.registereduser
@pytest.mark.appsuser
class TestParameterPassingUrl(TestCase2):

    def setup_method(self,method):

        self.remove_files = []

        # get user account info
        self.reguser,self.regpass = self.testdata.find_account_for('registeredworkspace')
        self.appsuser,self.appspass = self.testdata.find_account_for('appsworkspace')
        self.hubname = self.testdata.find_url_for('https')

        # setup a web browser
        self.browser.get(self.https_authority)

        # setup access to tool session containers
        cm = ContainerManager()

        self.reg_ws = cm.access(host=self.hubname,
                                username=self.reguser,
                                password=self.regpass)

        self.session = ToolSession(
            host=self.hubname, username=self.reguser, password=self.regpass)

        # get a list of session open before the test was run
        # incase the test fails unexpectedly, we can cleanup
        self.existing_sessions = self.session.get_open_session_detail()
        self.close_sessions = []

    def teardown_method(self,method):

        # exit the workspace
        # shut down the ssh connection
        self.reg_ws.close()

        # see if we can find any sessions accidentally left open.
        open_sessions = self.session.get_open_session_detail()
        open_sessions_numbers = []

        for row in open_sessions.values():
            open_sessions_numbers.append(row['session_number'])
            if re.search(TOOL_NAME,row['name']) is not None:
                # we found an open session that matches the name of our test tool
                # check if it was open before we started the test.
                old_session = False
                for existing_row in self.existing_sessions.values():
                    if existing_row['session_number'] == row['session_number']:
                        old_session = True
                        break
                if old_session is False:
                    # we found a session that was not open when the test started
                    # but is open now. there is a small chance it was opened by
                    # someone else.
                    # check if it is already in the list of sessions to be closed,
                    # if not, add the session to the list
                    if row['session_number'] not in self.close_sessions:
                        self.close_sessions.append(row['session_number'])

        # close the parampass tool's container
        for session_number in self.close_sessions:
            # check if the session is still open before closing it
            if session_number in open_sessions_numbers:
                self.session.stop(session_number)

        del self.session


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_no_parameters_file(self):
        """
        launch a tool with no parameters argument in url.
        """

        parameters_text = ''

        sessnum = launch_tool(self.https_authority,self.reguser,self.regpass,
                    self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @pytest.mark.skipif(True, reason="we no longer do file validation")
    @hubcheck.utils.hub_version(min_version='1.1.4')
    def dnr_test_launch_tool_invalid_path_1(self):
        """
        launch a tool with a parameter file with an invalid filename.

        file(datafile1):/home/hubname/testuser/file_does_not_exist
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = 'file(datafile1):%s/file_does_not_exist' % (home_dir)

        try:
            sessnum = launch_tool(self.https_authority,self.reguser,
                        self.regpass,self.browser,self.catalog,self.utils,
                        TOOL_NAME,TOOL_REVISION,parameters_text)

            self.close_sessions.append(sessnum)

            assert False, "while passing tool parameters, cms failed to" \
                + " catch invalid path: %s" % (repr(parameters_text))

        except BadParameterError as e:
            pass


    @pytest.mark.skipif(True, reason="we no longer do file validation")
    @hubcheck.utils.hub_version(min_version='1.1.4')
    def dnr_test_launch_tool_invalid_path_2(self):
        """
        launch a tool with a parameter file with an invalid user.

        file(datafile1):/home/hubname/non_existent_fake_user/file_does_not_exist
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')
        home_base = os.path.dirname(home_dir)
        home_dir = os.path.join(home_base,'non_existent_fake_user')

        parameters_text = 'file(datafile1):%s/file_does_not_exist' % (home_dir)

        try:
            sessnum = launch_tool(self.https_authority,self.reguser,
                        self.regpass,self.browser,self.catalog,self.utils,
                        TOOL_NAME,TOOL_REVISION,parameters_text)

            self.close_sessions.append(sessnum)

            assert False, "while passing tool parameters, cms failed to" \
                + " catch invalid path: %s" % (repr(parameters_text))

        except BadParameterError as e:
            pass


    @pytest.mark.skipif(True, reason="we no longer do file validation")
    @hubcheck.utils.hub_version(min_version='1.1.4')
    def dnr_test_launch_tool_invalid_path_3(self):
        """
        launch a tool with a parameter file with an invalid hubname.

        file(datafile1):/home/bad_hubname/fake_user/file_does_not_exist
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')
        home_base = os.path.dirname(os.path.dirname(home_dir))
        home_dir = os.path.join(home_base,'bad_hubname','fake_user')

        parameters_text = 'file(datafile1):%s/file_does_not_exist' % (home_dir)

        try:
            sessnum = launch_tool(self.https_authority,self.reguser,
                        self.regpass,self.browser,self.catalog,self.utils,
                        TOOL_NAME,TOOL_REVISION,parameters_text)

            self.close_sessions.append(sessnum)

            assert False, "while passing tool parameters, cms failed to" \
                + " catch invalid path: %s" % (repr(parameters_text))

        except BadParameterError as e:
            pass


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_invalid_path_4(self):
        """
        launch a tool with a parameter file with an invalid hubname.

        file(datafile1):/bad_home/bad_hubname/fake_user/file_does_not_exist
        """

        home_dir = os.path.join('/','bad_home','bad_hubname','fake_user')

        parameters_text = 'file(datafile1):%s/file_does_not_exist' % (home_dir)

        try:
            sessnum = launch_tool(self.https_authority,self.reguser,
                        self.regpass,self.browser,self.catalog,self.utils,
                        TOOL_NAME,TOOL_REVISION,parameters_text)

            self.close_sessions.append(sessnum)

            assert False, "while passing tool parameters, cms failed to" \
                + " catch invalid path: %s" % (repr(parameters_text))

        except BadParameterError as e:
            pass


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_blacklisted_path_1(self):
        """
        launch a tool with a parameter file with an blacklisted path.

        file(datafile1):/etc/environ
        """

        parameters_text = 'file(datafile1):/etc/environ'

        try:
            sessnum = launch_tool(self.https_authority,self.reguser,
                        self.regpass,self.browser,self.catalog,self.utils,
                        TOOL_NAME,TOOL_REVISION,parameters_text)

            self.close_sessions.append(sessnum)

            assert False, "while passing tool parameters, cms failed to" \
                + " catch blacklisted path: %s" % (repr(parameters_text))

        except BadParameterError as e:
            pass


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_hostname(['nees.org']),
        reason="nees.org specific test")
    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_whitelisted_path_1(self):
        """
        launch a tool with a parameter file with a whitelisted path.

        directory:/nees
        """

        parameters_text = 'directory:/nees'

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @pytest.mark.skipif(
        not hubcheck.utils.check_hub_hostname(['nees.org']),
        reason="nees.org specific test")
    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_whitelisted_path_2(self):
        """
        launch a tool with a parameter file with a whitelisted path.

        file:/nees/home/Public.groups/thumb_1235445883_Model-18EP-a.jpg
        """

        parameters_text = 'file:/nees/home/Public.groups/thumb_1235445883_Model-18EP-a.jpg'

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_whitelisted_path_3(self):
        """
        launch a tool with a parameter file with a whitelisted path.

        directory:/home/blahh
        """

        parameters_text = 'directory:/home/blahh'

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_home_expansion_1(self):
        """
        launch a tool with a parameter file with a ~ in the path.

        file(datafile1):~/.icewm/menu
        """

        parameters_text = 'file(datafile1):~/.icewm/menu'

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_named_file_1(self):
        """
        launch a tool with a single named file parameter in url.
        """

        session_dir,es = self.reg_ws.execute('echo ${SESSIONDIR}')

        parameters_text = 'file(datafile1):%s/resources' % (session_dir)

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_named_file_2(self):
        """
        launch a tool with multiple named file parameter in url.
        files are located in home directory
        """

        session_dir,es = self.reg_ws.execute('echo ${SESSIONDIR}')
        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            'file(datafile1):%s/resources' % (session_dir),
            'file(datafile2):%s/.icewm/menu' % (home_dir),
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_file_format_1(self):
        """
        launch a tool with single named file parameter and an
        extra newline at the end of the file.
        https://nees.org/groups/parampass/wiki/MainPage step 1 (b)
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            'file(datafile2):%s/.icewm/menu' % (home_dir),
            '',
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        parameters_text = shrink_space(parameters_text)

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_file_format_2(self):
        """
        launch a tool with single named file parameter and
        multiple extra newlines at the end of the file.
        https://nees.org/groups/parampass/wiki/MainPage step 1 (b)
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            'file(datafile2):%s/.icewm/menu' % (home_dir),
            '',
            '',
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        parameters_text = shrink_space(parameters_text)

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_file_format_3(self):
        """
        launch a tool with single named file parameter and
        surrounded by multiple extra newlines.
        https://nees.org/groups/parampass/wiki/MainPage step 1 (b)
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            '',
            '',
            'file(datafile2):%s/.icewm/menu' % (home_dir),
            '',
            '',
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        parameters_text = shrink_space(parameters_text)

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_file_format_4(self):
        """
        launch a tool with single named file parameter and
        preceeded by multiple extra newlines.
        https://nees.org/groups/parampass/wiki/MainPage step 1 (b)
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            '',
            '',
            'file(datafile2):%s/.icewm/menu' % (home_dir),
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        parameters_text = shrink_space(parameters_text)

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_file_format_5(self):
        """
        launch a tool with multiple named file parameter and
        a single extra newlines between the parameters.
        https://nees.org/groups/parampass/wiki/MainPage step 1 (b)
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            'file(datafile2):%s/.icewm/menu' % (home_dir),
            '',
            'file(datafile2):%s/.icewm/preferences' % (home_dir),
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))


    @hubcheck.utils.hub_version(min_version='1.1.4')
    def test_launch_tool_file_format_6(self):
        """
        launch a tool with multiple named file parameter and
        multiple extra newlines between the parameters.
        https://nees.org/groups/parampass/wiki/MainPage step 1 (b)
        """

        home_dir,es = self.reg_ws.execute('echo ${HOME}')

        parameters_text = '\n'.join([
            'file(datafile2):%s/.icewm/menu' % (home_dir),
            '',
            '',
            'file(datafile2):%s/.icewm/preferences' % (home_dir),
        ])

        sessnum = launch_tool(self.https_authority,self.reguser,
                    self.regpass,self.browser,self.catalog,self.utils,
                    TOOL_NAME,TOOL_REVISION,parameters_text)

        self.close_sessions.append(sessnum)

        ws = self.session.access(session_number=sessnum)
        ws.execute('cd $SESSIONDIR')

        ws_params_text = retrieve_container_parameters(ws)

        ws.close()

        # check that the TOOL_PARAMETERS file has the same info
        # as out parameters_text variable it was created from
        assert parameters_text == ws_params_text, \
            "TOOL_PARAMETERS file in container does not match data" \
            + " sent through url.\nexpected:\n%s\nreceived:\n%s\n" \
            % (repr(parameters_text),repr(ws_params_text))

