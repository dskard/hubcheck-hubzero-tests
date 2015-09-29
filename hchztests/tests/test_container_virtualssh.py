import hubcheck
import os
import pytest
import re
import sys

pytestmark = [ pytest.mark.container,
               pytest.mark.virtualssh,
               pytest.mark.reboot
             ]


class TestToolSession(hubcheck.testcase.TestCase2):

    def setup_method(self,method):

        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')
        hubname = self.testdata.find_url_for('https')

        self.session = hubcheck.shell.ToolSession(
            host=hubname, username=self.username, password=self.userpass)

        self._session_number = -1
        self.shell = None


    def teardown_method(self,method):

        if self.shell is not None:
            self.shell.close()

        if self._session_number > 0:
            self.session.stop(self._session_number)

        del(self.session)


    def test_session_help(self):
        """test issuing the 'session help' command"""

        i,o,e = self.session.help()
        output = o.read(1024)
        assert output != '', "output is empty, no help data printed"


#    def test_session_access_1(self):
#        """test issuing 'ssh user@<hub> session'
#           interactive shell without pty is not currently supported
#        """
#        shell = self.session.access(use_pty=False)
#        # since there is no pty, there is no prompt and
#        # we cannot use the execute() function
#        shell.send('echo $SESSION')
#        buf = self.get_buffer()
#        idx = shell.expect(['(\d+)'])
#        assert idx == 0,"echo $SESSION returned '%s'" % (buf)


#    def test_session_access_2_1(self):
#        """test issuing 'ssh -t user@<hub> session'
#           with no other open sessions
#        """
#
#        self.shell = self.session.access()
#        output,es = self.shell.execute('echo hi')
#        assert output == 'hi',"output = %s" % (output)


    def test_session_access_2_2(self):
        """test issuing 'ssh -t user@<hub> session'
           with other open sessions
        """

        # start up a session so we can get the session number
        i,o,e = self.session.create()
        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))
        assert session_number > 0, \
            "session_number = %s\noutput = %s" % (session_number,output)

        self._session_number = session_number

        self.shell = self.session.access()
        output,es = self.shell.execute('echo hi')
        assert output == 'hi',"output = %s" % (output)


#    def test_session_access_3_1(self):
#        """test issuing 'ssh -t user@<hub> session <command>'
#           with no other open sessions
#        """
#
#        i,o,e = self.session.access(command='echo hi')
#        output = o.read(1024)
#        assert output == 'hi\n',"output = %s" % (output)


    def test_session_access_3_2(self):
        """test issuing 'ssh -t user@<hub> session <command>'
           with other open sessions
        """

        # start up a session so we can get the session number
        i,o,e = self.session.create()
        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))
        assert session_number > 0, \
            "session_number = %s\noutput = %s" % (session_number,output)

        self._session_number = session_number

        i,o,e = self.session.access(command='echo hi')
        output = o.read(1024)
        assert output == 'hi\n',"output = %s" % (output)


    def test_session_access_4(self):
        """test issuing 'ssh -t user@<hub> session <session #>'
        """

        # start up a session so we can get the session number
        i,o,e = self.session.create()
        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))
        assert session_number > 0, \
            "session_number = %s\noutput = %s" % (session_number,output)

        self._session_number = session_number

        # try to access the newly started session
        self.shell = self.session.access(session_number=session_number)
        output,es = self.shell.execute('echo $SESSION')
        assert int(output) > 0,"output = %s" % (output)


    def test_session_access_5(self):
        """test issuing 'ssh -t user@<hub> session <session #> <command>'
        """

        # start up a session so we can get the session number
        i,o,e = self.session.create()
        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))
        assert session_number > 0, \
            "session_number = %s\noutput = %s" % (session_number,output)

        self._session_number = session_number

        # access the newly started session to run a command
        i,o,e = self.session.access(
                    session_number=session_number,
                    command='echo $SESSION')
        output = int(re.search('(\d+)',o.read(1024)).group(0))
        assert session_number == output, "output = %s" % (output)


    def test_session_list(self):
        """test issuing 'ssh user@<hub> session list'"""

        i,o,e = self.session.list()
        output = o.read(1024)
        assert output != '',"output of list command is empty"


    def test_session_create_1(self):
        """test issuing 'ssh user@<hub> session create'"""

        i,o,e = self.session.create()

        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))
        assert session_number > 0, \
            "output = %s\ninvalid session number: %s" % \
            (output,session_number)
        self._session_number = session_number


    def test_session_create_2(self):
        """test issuing 'ssh user@<hub> session create <title>'"""

        i,o,e = self.session.create(title="hc_test_workspace")

        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))
        assert session_number > 0, \
            "output = %s\ninvalid session number: %s" % \
            (output,session_number)
        self._session_number = session_number


    def test_session_start(self):
        """test issuing 'ssh -t user@<hub> session start'"""

        self.shell = self.session.start()
        output,es = self.shell.execute('echo $SESSION')
        assert int(output) > 0,"output = %s" % (output)
        self._session_number = int(output)


    def test_session_stop(self):
        """test issuing 'ssh -t user@<hub> session stop <session #>'"""

        # start up a session so we can get the session number
        i,o,e = self.session.create()
        session_number = int(re.search('(\d+)',o.read(1024)).group(0))
        assert session_number > 0, "session_number = %s" % (session_number)

        self._session_number = session_number

        # stop the session
        i,o,e = self.session.stop(session_number=session_number)
        output = o.read(1024)

# 'stopping session' message doesnt seem to come across stdout or stderr
#        match = re.search("stopping session (\d+)",output)
#
#        self.assertTrue(match is not None,"output = %s" % (output))
#
#        out_session_number = match.group(0)
#        self.assertTrue(out_session_number == session_number,
#            "out_session_number = %s\nsession_number=%s" % \
#            (out_session_number,session_number))
#

        self._session_number = -1


    def test_get_open_session_detail_1(self):
        """test that get_open_session_detail, a wrapper for 'session list', returns a dict"""

        data = self.session.get_open_session_detail()


    def test_get_open_session_detail_2(self):
        """test that opening a new session shows up in get_open_session_detail"""

        self.shell = self.session.start()
        session_number = int(self.shell.execute('echo $SESSION')[0])
        assert session_number > 0, \
            "invalid session number: %s" % (session_number)
        self._session_number = session_number

        # account for the 5 seconds it takes between when the
        # session is created to when the 'session list' command
        # is updated
        import time
        time.sleep(5)

        data = self.session.get_open_session_detail()

        # check if the session number shows up in the
        # 'session list' command output
        has_session = False
        for session_info in data.values():
            if int(session_info['session_number']) == session_number:
                has_session = True
                break

        assert has_session, \
            "newly opened session number %d does not appear in %s" % \
            (session_number,data)


    def test_get_session_number_by_title_1(self):
        """test searching the 'session list' command for a session by title
           when there is a matching title.
        """

        title = 'tstest1'

        # start a test session with a title
        i,o,e = self.session.create(title)
        output = o.read(1024)
        session_number = int(re.search('(\d+)',output).group(0))

        assert session_number > 0, \
            "invalid session number: %s\noutput = '%s'" % \
            (session_number,output)

        self._session_number = session_number

        # account for the 5 seconds it takes between when the
        # session is created to when the 'session list' command
        # is updated
        import time
        time.sleep(5)

        test_sn = int(self.session.get_session_number_by_title(title))

        assert session_number == test_sn, \
            "session_number = '%s', test_sn = '%s', output = '%s'" % \
            (session_number,test_sn,output)


    def test_get_session_number_by_title_2(self):
        """test searching the 'session list' command for a session by title
           when there is no matching title.
        """

        title = 'tstest2'

        test_sn = int(self.session.get_session_number_by_title(title))

        assert test_sn == -1, "test_sn = '%s'" % (test_sn)


