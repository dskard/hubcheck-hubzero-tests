import pytest
import os
import socket
import sys

import hubcheck
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager
from hubcheck.exceptions import ConnectionClosedError


pytestmark = [ pytest.mark.container,
               pytest.mark.user,
               pytest.mark.weekly,
               pytest.mark.reboot
             ]


@pytest.mark.appsuser
class TestAppsUser(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = \
            self.testdata.find_account_for('appsworkspace')
        hubname = self.testdata.find_url_for('https')

        # access a tool session container
        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        self.sessiondir = self.ws.execute('echo $SESSIONDIR')


    def teardown_method(self,method):

        # exit the workspace
        self.ws.close()


    def test_umask(self):
        """
        apps user's umask should be 0022
        """

        expected = '0022'

        try:
            # become the apps user
            self.ws.send('sudo su - apps')
            self.ws.start_bash_shell()
            output,es = self.ws.execute('whoami')
            exit_apps = True
            assert output == 'apps', \
                "doesn't look like we were able to become the apps user"

            # get the user's umask
            umask,es = self.ws.execute('umask')

        finally:
            self.ws.stop_bash_shell()
            if exit_apps:
                self.ws.send('exit')


        assert umask == expected, \
            'incorrect umask: %s, expected: %s' % (umask,expected)


    def test_home_directory(self):
        """
        apps user should have a home directory /home/<hubname>/apps
        """

        homedir,es = self.ws.execute('echo $HOME')
        expected = os.path.join(os.path.dirname(homedir),'apps')

        homedir = None
        try:
            # become the apps user
            self.ws.send('sudo su - apps')
            self.ws.start_bash_shell()
            output,es = self.ws.execute('whoami')
            exit_apps = True
            assert output == 'apps', \
                "doesn't look like we were able to become the apps user"

            # get the user's home directory
            homedir,es = self.ws.execute('echo $HOME')

        finally:
            self.ws.stop_bash_shell()
            if exit_apps:
                self.ws.send('exit')


        assert homedir == expected, \
            'incorrect homedir: %s, expected: %s' % (homedir,expected)



@pytest.mark.registereduser
class TestRegisteredUser(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = \
            self.testdata.find_account_for('purdueworkspace')
        hubname = self.testdata.find_url_for('https')

        # access a tool session container
        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        self.sessiondir = self.ws.execute('echo $SESSIONDIR')


    def teardown_method(self,method):

        # exit the workspace
        self.ws.close()


    def test_umask(self):
        """
        registered user's umask should be 0027
        """

        expected = '0027'

        # get the user's umask
        umask,es = self.ws.execute('umask')

        assert umask == expected, \
            'incorrect umask: %s, expected: %s' % (umask,expected)


@pytest.mark.registereduser
class TestRegisteredUserTTYRecycle(TestCase2):
    """
    testing tty recycle requires its own tool session container
    that is not suitable for use after the end of the test

    https://hubzero.org/support/ticket/4069
    """

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')
        self.hubname = self.testdata.find_url_for('https')


    def teardown_method(self,method):
        pass


    def test_tty_recycle(self):
        """
        check if ttys are being released after ssh connections are closed.

        ssh'ing into a workspace, opening a shell, and closing the ssh
        connection should release the pty. tool session containers get 15 ptys.
        we are checking to see if ptys are being released after the user exits
        the pty.

        the failue occurs in the call to cm.access().
        """

        session_number = 0
        cm = ContainerManager()

        for i in range(31):

            try:
                # access a tool session container
                ws = cm.access(host=self.hubname,
                               username=self.username,
                               password=self.userpass)

                session_number,es = ws.execute('echo $SESSION')

                # start up a new bash shell manually
                ws.send('/bin/bash')

                # exit the workspace
                ws.close()
            except (ConnectionClosedError,socket.timeout) as e:
                if session_number > 0:
                    # container is hosed, shut it down.
                    cm.stop(self.hubname,self.username,int(session_number))
                assert False, "After connecting %s time(s): %s" \
                    % (i,sys.exc_info()[0])

