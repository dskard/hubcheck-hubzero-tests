import os
import pytest
import re
import stat
import sys

import hubcheck
from hubcheck.testcase import TestCase
from hubcheck.shell import ContainerManager
from hubcheck.shell import SFTPClient

pytestmark = [ pytest.mark.container,
               pytest.mark.invokeapp,
               pytest.mark.weekly,
               pytest.mark.reboot
             ]


INVOKE_APP_PATH = "/usr/bin/invoke_app"
PARAMETERS_PATH = "parameters.hz"
FILES = {
    'datafile1' : { 'contents' : 'this is datafile1',
                    'mode' : stat.S_IRUSR },
    'datafile2' : { 'contents' : 'this is datafile2',
                    'mode' : stat.S_IRUSR },
    'slow_echo' : { 'contents' : 'sleep 3; echo $*',
                    'mode' : stat.S_IRUSR },
}

TOOLXML = """<?xml version="1.0"?>
<run>
    <tool>
        <about>Press Simulate to view results.</about>
        <command>echo hi</command>
    </tool>
    <input>
        <string id = "name">
            <about>
                <label>Hello World Name</label>
                <description>Enter your name here</description>
            </about>
            <default>yourname</default>
        </string>
    </input>
</run>
"""

@pytest.mark.registereduser
class container_invokeapp(TestCase):


    def setUp(self):

        self.remove_files = []

        # get user account info
        self.username,self.userpass = self.testdata.find_account_for('registeredworkspace')
        hubname = self.testdata.find_url_for('https')

        cm = ContainerManager()

        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        # cd into the session directory
        self.sftp = SFTPClient(
            host=hubname, username=self.username, password=self.userpass)

        self.ws.execute('cd $SESSIONDIR')
        self.sessiondir,es = self.ws.execute('pwd')
        self.sftp.chdir(self.sessiondir)


        # write data and script files to disk in the container.
        for fname,fprop in FILES.items():
            with self.sftp.open(fname,mode='w') as f:
                f.write(fprop['contents'])
            self.remove_files.append(os.path.join(self.sessiondir,fname))
            self.sftp.chmod(fname,fprop['mode'])


    def tearDown(self):

        # remove the executable and config files
        for fname in self.remove_files:
            self.sftp.remove(fname)
        self.sftp.close()

        # exit the workspace
        # shut down the ssh connection
        self.ws.close()


    def _run_invoke_app(self,command,parameters_text=None):

        if parameters_text is not None:
            with self.sftp.open(PARAMETERS_PATH,'w') as f:
                f.write(parameters_text)
            self.remove_files.append(os.path.join(self.sessiondir,PARAMETERS_PATH))
            cmd = 'export TOOL_PARAMETERS=%s' % (PARAMETERS_PATH)
            self.ws.execute(cmd)

        # allow up to 30 seconds for the command to run
        oldtimeout = self.ws.timeout
        self.ws.timeout = 30

        # run the command in xvfb to handle toolparams popup windows
        command = 'xvfb-run -s "-screen 0 800x600x24" ' + command

        # run the invoke_app command
        result,err = self.ws.execute(command,fail_on_exit_code=False)

        # reset the command timeout
        self.ws.timeout = oldtimeout

        # check for error while running invoke_app command
        toolout = None
        matches = re.search("\nexec'ing[^\n]+\n(.*)",result,re.DOTALL)
        if matches:
            # grab the output
            # strip off submit metrics from toolout
            pattern = "=SUBMIT-METRICS=>.*$"
            toolout = re.sub(pattern,'',matches.group(1),flags=re.MULTILINE)
            toolout = toolout.strip()

        return (result,err,toolout)


    def _find_bg_command(self,command):

        grep_cmd = 'ps aux | grep "' + command + '" | grep -v -e "bash\|grep"'
        result,err = self.ws.execute(grep_cmd)

        import re
        rexp = '(?P<user>[^\s]+)\s+' + \
               '(?P<pid>[^\s]+)\s+'  + \
               '(?P<cpu>[^\s]+)\s+'  + \
               '(?P<mem>[^\s]+)\s+'  + \
               '(?P<vsz>[^\s]+)\s+'  + \
               '(?P<rss>[^\s]+)\s+'  + \
               '(?P<tty>[^\s]+)\s+'  + \
               '(?P<stat>[^\s]+)\s+' + \
               '(?P<start>[^\s]+)\s+' + \
               '(?P<time>[^\s]+)\s+' + \
               '(?P<command>[^\n]+)'

        m = re.search(rexp,result)
        if m is None:
            return None

        # make sure we return the correct command
        if m.group('command') != command:
            # didn't find the correct command
            return None

        return m.groupdict()


    def test_1_command_no_templates(self):
        """launching invoke_app with one -C command (not template) should run the command
           ex: invoke_app -C "sh ./slow_echo hi"
           should produce: hi
        """

        # build our invoke_app command
        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo hi"'

        expected_out = "hi"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_3_commands_no_templates(self):
        """launching invoke_app with multiple non-templated -C commands
           should run the last command.
           ex: invoke_app -C "sh ./slow_echo hi" -C "sh ./slow_echo bye" -C "sh ./slow_echo yeah"
           should produce: yeah
        """

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "sh ./slow_echo bye"' \
                  + ' -C "sh ./slow_echo yeah"'

        expected_out = "yeah"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_template_0_default_run_template_1(self):
        """launching invoke_app with one -C template command should
           launch toolparams to run the command
           ex: invoke_app -C "cat @@file(datafile1)"
           should launch: toolparams 'cat @@file(datafile1)'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_template_1_default_run_template_1(self):
        """launching invoke_app with one -C template command
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           has a valid reference to file(datafile1), the templated
           command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(datafile1)' -default 'sh ./slow_echo hi'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_template_1_default_run_default(self):
        """launching invoke_app with one -C template command
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           does not have a valid reference to file(datafile1), the
           non-templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(datafile1)' -default 'sh ./slow_echo hi'
           and produce: hi
        """

        # create our parameters file
        parameters_text = '\n'.join([])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = "hi"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_default_1_template_run_template_1(self):
        """launching invoke_app with one -C non-template command
           and one -C template command should launch
           toolparams to run the command. when the parameters file
           has a valid reference to file(datafile1), the templated
           command should be run.
           ex: invoke_app -C "sh ./slow_echo hi" -C "cat @@file(datafile1)"
           should launch: toolparams 'cat @@file(datafile1)' -default 'sh ./slow_echo hi'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile1)"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_default_1_template_run_default(self):
        """launching invoke_app with one -C non-template command
           and one -C template command should launch
           toolparams to run the command. when the parameters file
           does not have a valid reference to file(datafile1), the
           non-templated command should be run.
           ex: invoke_app -C "sh ./slow_echo hi" -C "cat @@file(datafile1)"
           should launch: toolparams 'cat @@file(datafile1)' -default 'sh ./slow_echo hi'
           and produce: hi
        """

        # create our parameters file
        parameters_text = '\n'.join([])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile1)"'

        expected_out = "hi"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_2_templates_0_default_run_template_1(self):
        """launching invoke_app with two -C template commands
           and zero -C non-template command should launch
           toolparams to run the command. when the parameters file
           has a valid reference to file(datafile1), the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_2_templates_0_default_run_template_2(self):
        """launching invoke_app with two -C template commands
           and zero -C non-template command should launch
           toolparams to run the command. when the parameters file
           has a valid reference to file(datafile2), the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)'
           and produce: this is datafile2
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile2):%s" % os.path.join(self.sessiondir,'datafile2'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = FILES['datafile2']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_2_templates_1_default_run_template_1(self):
        """launching invoke_app with two -C template commands
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           has a valid reference to file(datafile1), the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "cat @@file(datafile2)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_2_templates_1_default_run_template_2(self):
        """launching invoke_app with two -C template commands
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           has a valid reference to file(datafile2), the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "cat @@file(datafile2)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile2
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile2):%s" % os.path.join(self.sessiondir,'datafile2'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = FILES['datafile2']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_2_templates_1_default_run_default(self):
        """launching invoke_app with two -C template commands
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           does not have a valid reference, the
           appropriate non-templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "cat @@file(datafile2)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: hi
        """

        # create our parameters file
        parameters_text = '\n'.join([])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = 'hi'

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_template_1_default_1_template_run_template_1(self):
        """launching invoke_app with one -C template command
           and one -C non-template command and a second
           -C template comamnd should launch toolparams
           to run the command. when the parameters file
           has a valid reference to file(datafile1), the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "sh ./slow_echo hi" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_template_1_default_1_template_run_template_2(self):
        """launching invoke_app with one -C template commands
           and one -C non-template command and a second
           -C template command should launch toolparams
           to run the command. when the parameters file
           has a valid reference to file(datafile2), the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "sh ./slow_echo hi" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile2
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile2):%s" % os.path.join(self.sessiondir,'datafile2'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = FILES['datafile2']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_template_1_default_1_template_run_default(self):
        """launching invoke_app with one -C template command
           and one -C non-template command and a second
           -C template command should launch toolparams
           to run the command. when the parameters file
           does not have a valid reference, the
           appropriate non-templated command should be run.
           ex: invoke_app -C "cat @@file(datafile1)" -C "sh ./slow_echo hi" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: hi
        """

        # create our parameters file
        parameters_text = '\n'.join([])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = 'hi'

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_default_2_templates_run_template_1(self):
        """launching invoke_app with one -C non-template command
           and two -C template commands should launch toolparams
           to run the command. when the parameters file
           has a valid reference to file(datafile1), the
           appropriate templated command should be run.
           ex: invoke_app -C "sh ./slow_echo hi" -C "cat @@file(datafile1)" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_default_2_templates_run_template_2(self):
        """launching invoke_app with one -C non-template command
           and two -C template commands should launch toolparams
           to run the command. when the parameters file
           has a valid reference to file(datafile2), the
           appropriate templated command should be run.
           ex: invoke_app -C "sh ./slow_echo hi" -C "cat @@file(datafile1)" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile2
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile2):%s" % os.path.join(self.sessiondir,'datafile2'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = FILES['datafile2']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_1_default_2_template_run_default(self):
        """launching invoke_app with one -C non-template command
           and two -C template command should launch toolparams
           to run the command. when the parameters file
           does not have a valid reference, the
           appropriate non-templated command should be run.
           ex: invoke_app -C "sh ./slow_echo hi" -C "cat @@file(datafile1)" -C "cat @@file(datafile2)"
           should launch: toolparams 'cat @@file(datafile1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: hi
        """

        # create our parameters file
        parameters_text = '\n'.join([])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "sh ./slow_echo hi"' \
                  + ' -C "cat @@file(datafile1)"' \
                  + ' -C "cat @@file(datafile2)"'

        expected_out = 'hi'

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_2_templates_1_default_run_index_1(self):
        """launching invoke_app with two -C template commands
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           has a valid positional reference, the
           appropriate templated command should be run.
           ex: invoke_app -C "cat @@file(#1)" -C "cat @@file(datafile2)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(#1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
           and produce: this is datafile1
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(#1)"' \
                  + ' -C "cat @@file(datafile2)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = FILES['datafile1']['contents']

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


#    def test_positional_2_templates_1_default_run_index_1_1(self):
#        """launching invoke_app with two -C template commands
#           and one -C non-template command should launch
#           toolparams to run the command. when the parameters file
#           has two valid positional references, the first matching
#           templated command should be run.
#           ex: invoke_app -C "cat @@file(#1)" -C "cat @@file(#1) @@file(#2)" -C "sh ./slow_echo hi"
#           should launch: toolparams 'cat @@file(#1)' -or 'cat @@file(datafile2)' -default 'sh ./slow_echo hi'
#           and produce: this is datafile1
#        """
#
#        # create our parameters file
#        parameters_text = '\n'.join([
#            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
#            "file(datafile2):%s" % os.path.join(self.sessiondir,'datafile2'),
#        ])
#
#        # build our invoke_app command
#        command = INVOKE_APP_PATH \
#                  + ' -C "cat @@file(#1)"' \
#                  + ' -C "cat @@file(#1) @@file(#2)"' \
#                  + ' -C "sh ./slow_echo hi"'
#
#        expected_out = FILES['datafile1']['contents']
#
#        # run invoke_app
#        result,err,toolout = self._run_invoke_app(command,parameters_text)
#
#        # check result
#        self.assertTrue(err == 0,
#            "Error while executing '%s': %s" % (command,toolout))
#
#        # parse the output
#        self.assertTrue(toolout == expected_out,
#            'Error while executing "%s": ' % (command)
#            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_positional_2_templates_1_default_run_index_1_2(self):
        """launching invoke_app with two -C template commands
           and one -C non-template command should launch
           toolparams to run the command. when the parameters file
           has two valid positional references, the first matching
           templated command should be run.
           ex: invoke_app -C "cat @@file(#1) @@file(#2)" -C "cat @@file(#1)" -C "sh ./slow_echo hi"
           should launch: toolparams 'cat @@file(#1) @@file(#2)' -or 'cat @@file(#1)' -default 'sh ./slow_echo hi'
           and produce:
           this is datafile1
           this is datafile2
        """

        # create our parameters file
        parameters_text = '\n'.join([
            "file(datafile1):%s" % os.path.join(self.sessiondir,'datafile1'),
            "file(datafile2):%s" % os.path.join(self.sessiondir,'datafile2'),
        ])

        # build our invoke_app command
        command = INVOKE_APP_PATH \
                  + ' -C "cat @@file(#1) @@file(#2)"' \
                  + ' -C "cat @@file(#1)"' \
                  + ' -C "sh ./slow_echo hi"'

        expected_out = "%s%s" % (FILES['datafile1']['contents'],
                                 FILES['datafile2']['contents'])

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command,parameters_text)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_command_arguments_1(self):
        """launching invoke_app with the -A flag, sending additional arguments
           ex: invoke_app -C "sh ./slow_echo" -A "hi pete"
           should produce: hi pete
        """

        # build our invoke_app command
        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo" -A "hi pete"'

        expected_out = "hi pete"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_command_arguments_2(self):
        """launching invoke_app with a blank -A flag,
           sending an empty string as additional arguments
           ex: invoke_app -C "sh ./slow_echo hi" -A ""
           should produce: hi
        """

        # build our invoke_app command
        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo hi" -A ""'

        expected_out = "hi"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_background_command_1(self):
        """launching invoke_app with a single -c flag,
           launching a background command
           ex: invoke_app -C "sh ./slow_echo hi" -c "sleep 23995946712"
           should produce: hi
        """

        # build our invoke_app command
        bg_cmd = "sleep 23995946712"
        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo hi" -c "' + bg_cmd + '"'

        expected_out = "hi"

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


        # check that the background job was started
        result = self._find_bg_command(bg_cmd)
        self.assertTrue(result is not None,)


    def test_working_directory_1(self):
        """launching invoke_app with a -d flag to change the working directory,
           ex: invoke_app -C "sh \${SESSIONDIR}/slow_echo \${PWD}" -d ${HOME}
           should produce: ${HOME}
        """

        # build our invoke_app command
        homedir,err = self.ws.execute('sh ./slow_echo ${HOME}')
        command = INVOKE_APP_PATH \
            + ' -C "sh \${SESSIONDIR}/slow_echo \${PWD}" -d ${HOME}'

        expected_out = homedir

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_environment_variable_1(self):
        """launching invoke_app with a -e flag to set an environment variable,
           ex: invoke_app -C "sh ./slow_echo \${FOO}" -e FOO=blahh
           should produce: blahh
        """

        # build our invoke_app command
        expected_out = 'blahh'
        command = INVOKE_APP_PATH \
            + ' -C "sh ./slow_echo \${FOO}"' \
            + ' -e FOO={0}'.format(expected_out)


        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_fullscreen_1(self):
        """launching invoke_app with a -f flag to
           not set the FULLSCREEN environment variable,
           ex: invoke_app -C "sh ./slow_echo \${FULLSCREEN}" -f
           should produce: ""
        """

        # build our invoke_app command
        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo \${FULLSCREEN}" -f'

        # because invoke_app checks if the command is associated with a tty
        # before starting a window manager or setting the FULLSCREEN
        # environment variable, we have to nohup the command and capture
        # the output.
        command = 'nohup {0} > nohup.out && cat nohup.out'.format(command)

        expected_out = ''

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # cleanup output, removing "XIO:  fatal IO error 11"
        # messages that arise because we close down the xvfb
        # in an unorthodox way (i think)
        toolout = re.sub(r'XIO.+remaining\.','',toolout,flags=re.DOTALL)
        toolout = toolout.strip()

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


    def test_fullscreen_2(self):
        """launching invoke_app without a -f flag to
           set the FULLSCREEN environment variable to "yes",
           ex: invoke_app -C "sh ./slow_echo \${FULLSCREEN}"
           should produce: yes
        """

        # build our invoke_app command
        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo \${FULLSCREEN}"'

        # because invoke_app checks if the command is associated with a tty
        # before starting a window manager or setting the FULLSCREEN
        # environment variable, we have to nohup the command and capture
        # the output.
        command = 'nohup {0} > nohup.out && cat nohup.out'.format(command)

        expected_out = 'yes'

        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # cleanup output, removing "XIO:  fatal IO error 11"
        # messages that arise because we close down the xvfb
        # in an unorthodox way (i think)
        toolout = re.sub(r'XIO.+remaining\.','',toolout,flags=re.DOTALL)
        toolout = toolout.strip()

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


#    def test_nanowhim_1(self):
#        """launching invoke_app with a -n flag to
#           setup the nanowhim version,
#           ex: invoke_app -C "sh ./slow_echo " -n dev
#           should produce:
#        """
#
#        # build our invoke_app command
#        command = INVOKE_APP_PATH + ' -C "sh ./slow_echo ${FULLSCREEN}"'
#
#        expected_out = 'yes'
#
#        # run invoke_app
#        result,err,toolout = self._run_invoke_app(command)
#
#        # check result
#        self.assertTrue(err == 0,
#            "Error while executing '%s': %s" % (command,toolout))
#
#        # parse the output
#        self.assertTrue(toolout == expected_out,
#            'Error while executing "%s": ' % (command)
#            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))
#


    def test_path_environment_variable_1(self):
        """launching invoke_app with a -p flag to set
           the PATH environment variable,
           ex: invoke_app -C "sh ./slow_echo \${PATH} | cut -d\":\" -f 1" -p /blahh
           should produce: /blahh
        """

        # build our invoke_app command
        expected_out = '/blahh'
        command = INVOKE_APP_PATH \
            + ' -C "sh ./slow_echo \${PATH} | cut -d\":\" -f 1"'\
            + ' -p {0}'.format(expected_out)


        # run invoke_app
        result,err,toolout = self._run_invoke_app(command)

        # check result
        self.assertTrue(err == 0,
            "Error while executing '%s': %s" % (command,toolout))

        # parse the output
        self.assertTrue(toolout == expected_out,
            'Error while executing "%s": ' % (command)
            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))


#    def test_rappture_version_1(self):
#        """launching invoke_app with a -r flag to set the rappture version
#           ex: invoke_app -C "sh ./slow_echo hi" -r dev
#           should produce: hi
#        """
#
#        # write a tool.xml file in the workspace.
#        fname = 'tool.xml'
#        text = TOOLXML
#        with self.sftp.open(fname,mode='w') as f:
#            f.write(text)
#        self.remove_files.append(os.path.join(self.sessiondir,fname))
#
#        # build our invoke_app command
#        command = INVOKE_APP_PATH \
#            + ' -C "rappture -tool {0}" -r dev'.format(fname)
#
#        expected_out = 'hi'
#
#        # run invoke_app
#        result,err,toolout = self._run_invoke_app(command)
#
#        # check result
#        self.assertTrue(err == 0,
#            "Error while executing '%s': %s" % (command,toolout))
#
#        # parse the output
#        self.assertTrue(toolout == expected_out,
#            'Error while executing "%s": ' % (command)
#            + 'expected "%s"\nreceived "%s"' % (expected_out,toolout))
#
#
#        matches = re.search("\nRAPPTURE_PATH = ([^\n]+)\n",result,re.DOTALL)



