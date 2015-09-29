import unittest
import sys
import re
import pytest

import hubcheck
from hubcheck.testcase import TestCase
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager


pytestmark = [ pytest.mark.container,
               pytest.mark.config,
               pytest.mark.weekly,
               pytest.mark.reboot
             ]


ICEWM_CONF_DIR = '~/.icewm'
ICEWM_CONF_FILE_SPEC = [
        ('~/.icewm/keys',        '/usr/share/hubzero-icewm/keys'),
        ('~/.icewm/menu',        '/usr/share/hubzero-icewm/menu'),
        ('~/.icewm/preferences', '/usr/share/hubzero-icewm/preferences'),
        ('~/.icewm/theme',       '/usr/share/hubzero-icewm/theme'),
        ('~/.icewm/toolbar',     '/usr/share/hubzero-icewm/toolbar'),
        ('~/.icewm/icons',       '/usr/share/hubzero-icewm/icons'),
]

# module scriptname newpath oldpaths
#script_info = {
#    filexfer    filexfer        /usr/bin/filexfer       {/apps/bin/filexfer /apps/filexfer/bin/filexfer}
#    filexfer    importfile      /usr/bin/importfile     {/apps/bin/importfile /apps/filexfer/bin/importfile}
#    filexfer    exportfile      /usr/bin/exportfile     {/apps/bin/exportfile /apps/filexfer/bin/exportfile}
#    xvnc        clientaction    /usr/bin/clientaction   {/apps/xvnc/bin/clientaction /usr/lib/mw/bin/clientaction}
#    xvnc        pixelflip       /usr/bin/pixelflip      {/apps/xvnc/bin/pixelflip /usr/lib/mw/bin/pixelflip}
#    xvnc        mergeauth       /usr/bin/mergeauth      {/apps/xvnc/mergeauth /usr/lib/mw/bin/mergeauth}
#    xvnc        startxvnc       /usr/bin/startxvnc      {/apps/xvnc/start /usr/lib/mw/bin/startxvnc}
#    other       xsetroot        /usr/bin/xsetroot       {""}
#    wm          icewm           /usr/bin/icewm          {""}
#    wm          icewm-captive   /usr/bin/icewm-captive  {/apps/icewm/captive/invoke /usr/lib/hubzero/icewm/invoke}
#    wm          ratpoison       /usr/bin/ratpoison      {""}
#    wm          ratpoison-captive   /usr/bin/ratpoison-captive    {""}
#    invoke_app  invoke_app      /usr/bin/invoke_app     {/apps/rappture/invoke_app /apps/invoke/invoke_app /apps/share/invoke/invoke_app}
#    submit      submit          /usr/bin/submit         {""}
#}

@pytest.mark.container_exes
class container_config(TestCase):


    def setUp(self):

        # get user account info
        hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)


    def _check_script_details(self,script_name,current_path,old_paths):

        # check for script in search path
        command = 'which %s' % (script_name)
        output,es = self.ws.execute(command)
        self.assertTrue(output != '',"'%s' not in search path" % (script_name))

        # check for the current path of the script
        self.assertTrue(output == current_path,
            "'%s' calls '%s' instead of '%s'" \
            % (script_name,output,current_path))

        # check for old versions of the script
        old_found = []
        for p in old_paths:
            command = '[[ -e %s ]] && echo 1 || echo 0' % (p)
            output,es = self.ws.execute(command)
            if output == '1':
                old_found.append(p)
        self.assertTrue(len(old_found) == 0,
            "old locations of %s found: %s" % (script_name,old_found))


    def test_paths_filexfer(self):
        """
        check if 'filexfer' is in the search path
        """

        script_name = 'filexfer'
        current_path = '/usr/bin/filexfer'
        old_paths = ['/apps/bin/filexfer','/apps/filexfer/bin/filexfer']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_importfile(self):
        """
        check if 'importfile' is in the search path
        """

        script_name = 'importfile'
        current_path = '/usr/bin/importfile'
        old_paths = ['/apps/bin/importfile','/apps/filexfer/bin/importfile']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_exportfile(self):
        """
        check if 'exportfile' is in the search path
        """

        script_name = 'exportfile'
        current_path = '/usr/bin/exportfile'
        old_paths = ['/apps/bin/exportfile','/apps/filexfer/bin/exportfile']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_clientaction(self):
        """
        check if 'clientaction' is in the search path
        """

        script_name = 'clientaction'
        current_path = '/usr/bin/clientaction'
        old_paths = ['/apps/xvnc/bin/clientaction','/usr/lib/mw/bin/clientaction']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_pixelflip(self):
        """
        check if 'pixelflip' is in the search path
        """

        script_name = 'pixelflip'
        current_path = '/usr/bin/pixelflip'
        old_paths = ['/apps/xvnc/bin/pixelflip','/usr/lib/mw/bin/pixelflip']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_mergeauth(self):
        """
        check if 'mergeauth' is in the search path
        """

        script_name = 'mergeauth'
        current_path = '/usr/bin/mergeauth'
        old_paths = ['/apps/xvnc/mergeauth','/usr/lib/mw/bin/mergeauth']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_startxvnc(self):
        """
        check if 'startxvnc' is in the search path
        """

        script_name = 'startxvnc'
        current_path = '/usr/bin/startxvnc'
        old_paths = ['/apps/xvnc/start','/usr/lib/mw/bin/startxvnc']

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_xsetroot(self):
        """
        check if 'xsetroot' is in the search path
        """

        script_name = 'xsetroot'
        current_path = '/usr/bin/xsetroot'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_icewm(self):
        """
        check if 'icewm' is in the search path
        """

        script_name = 'icewm'
        current_path = '/usr/bin/icewm'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_icewm_captive(self):
        """
        check if 'icewm-captive' is in the search path
        """

        script_name = 'icewm-captive'
        current_path = '/usr/bin/icewm-captive'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_ratpoison(self):
        """
        check if 'ratpoison' is in the search path
        """

        script_name = 'ratpoison'
        current_path = '/usr/bin/ratpoison'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_ratpoison_captive(self):
        """
        check if 'ratpoison-captive' is in the search path
        """

        script_name = 'ratpoison-captive'
        current_path = '/usr/bin/ratpoison-captive'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_invoke_app(self):
        """
        check if 'invoke_app' is in the search path
        """

        script_name = 'invoke_app'
        current_path = '/usr/bin/invoke_app'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def test_paths_submit(self):
        """
        check if 'submit' is in the search path
        """

        script_name = 'submit'
        current_path = '/usr/bin/submit'
        old_paths = []

        self._check_script_details(script_name,current_path,old_paths)


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()


@pytest.mark.session_number
class container_session_number_config(TestCase):


    def setUp(self):

        # get user account info
        hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()


    def test_environment_session_number(self):
        """
        check if $SESSION exists and is an integer
        """

        command = 'echo $SESSION'
        session_number,es = self.ws.execute(command)

        try:
            int_session_number = int(session_number)
        except ValueError:
            self.fail("$SESSION doesn't appear to be a number: %s"
                % (session_number))

        self.assertTrue(int_session_number > 0,
            "$SESSION is not greater than 0: %s" % (session_number))


    def test_environment_session_dir(self):
        """
        check if $SESSIONDIR exists and is a path that exists
        """

        command = 'echo $SESSIONDIR'
        session_dir,es = self.ws.execute(command)

        self.assertTrue(session_dir != '',"$SESSIONDIR is empty")

        exists = self.ws.bash_test('-d %s' % (session_dir))

        self.assertTrue(exists,"$SESSIONDIR is not a directory: %s"
            % (session_dir))


    def test_environment_results_dir(self):
        """
        check if $RESULTSDIR is populated.

        I don't think $RESULTSDIR exists unless a Rappture tool
        is run. So we only test that the variable is populated.
        """

        command = 'echo $RESULTSDIR'
        results_dir,es = self.ws.execute(command)

        self.assertTrue(results_dir != '',"$RESULTSDIR is empty")


@pytest.mark.use
class container_use_config(TestCase):


    def setUp(self):

        # get user account info
        hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)


    def test_apps_environ_setup_sh_does_not_exist(self):
        """
        check that /apps/environ/.setup.sh does not exist
        """

        fname = '/apps/environ/.setup.sh'

        # check the file exists
        command = '[[ -e %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '0',"%s exists and should not." % (fname))


    def test_apps_environ_setup_csh_does_not_exist(self):
        """
        check that /apps/environ/.setup.csh does not exist
        """

        fname = '/apps/environ/.setup.csh'

        # check the file is readable
        command = '[[ -e %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '0',"%s exists and should not." % (fname))


    @hubcheck.utils.tool_container_version('debian6')
    def test_apps_share_environ_is_directory(self):
        """
        check that /apps/share/debian6/environ.d is a readable directory
        """

        fname = '/apps/share/debian6/environ.d'

        # check that file exists
        command = '[[ -r %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not readable" % (fname))

        # check that file is a directory
        command = '[[ -d %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not a directory" % (fname))


    @hubcheck.utils.tool_container_version('debian6')
    def test_apps_share64_environ_is_directory(self):
        """
        check that /apps/share64/debian6/environ.d is a readable directory
        """

        fname = '/apps/share64/debian6/environ.d'

        # check that file exists
        command = '[[ -r %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not readable" % (fname))

        # check that file is a directory
        command = '[[ -d %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not a directory" % (fname))


    @hubcheck.utils.tool_container_version('debian7')
    def test_apps_share_environ_is_directory(self):
        """
        check that /apps/share/debian7/environ.d is a readable directory
        """

        fname = '/apps/share/debian7/environ.d'

        # check that file exists
        command = '[[ -r %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not readable" % (fname))

        # check that file is a directory
        command = '[[ -d %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not a directory" % (fname))


    @hubcheck.utils.tool_container_version('debian7')
    def test_apps_share64_environ_is_directory(self):
        """
        check that /apps/share64/debian7/environ.d is a readable directory
        """

        fname = '/apps/share64/debian7/environ.d'

        # check that file exists
        command = '[[ -r %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not readable" % (fname))

        # check that file is a directory
        command = '[[ -d %s ]] && echo 1 || echo 0' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output == '1',"%s is not a directory" % (fname))


    @hubcheck.utils.tool_container_version('debian7')
    def test_apps_share64_environ_rappture_dev_link(self):
        """
        check that /apps/share64/debian7/environ.d/rappture-dev points to
        /apps/share64/debian7/rappture/dev/bin/rappture.use
        """

        fname = '/apps/share64/debian7/environ.d/rappture-dev'
        points_to = '/apps/share64/debian7/rappture/dev/bin/rappture.use'

        # see where fname points
        command = 'readlink -f %s' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output != fname,"%s does not exist" % (fname))

        # see where points_to points
        command = 'readlink -f %s' % (points_to)
        output,es = self.ws.execute(command)
        self.assertTrue(output != points_to,"%s does not exist" % (points_to))


    @hubcheck.utils.tool_container_version('debian7')
    def test_apps_share64_environ_rappture_link(self):
        """
        check that /apps/share64/debian7/environ.d/rappture points to
        /apps/share64/debian7/rappture/current/bin/rappture.use
        """

        fname = '/apps/share64/debian7/environ.d/rappture'
        points_to = '/apps/share64/debian7/rappture/current/bin/rappture.use'

        # see where fname points
        command = 'readlink -f %s' % (fname)
        output,es = self.ws.execute(command)
        self.assertTrue(output != fname,"%s does not exist" % (fname))

        # see where points_to points
        command = 'readlink -f %s' % (points_to)
        output,es = self.ws.execute(command)
        self.assertTrue(output != points_to,"%s does not exist" % (points_to))


    def test_use_shell_function_available(self):
        """
        see if use is available as a shell function
        """

        # get all the login shell profile stuff
        self.ws.source('/etc/profile')

        output,es = self.ws.execute('type use')
        self.assertTrue(re.search(r'use is a function',output) is not None,
            "use does not appear to be a function: %s" % (output))


    def test_unuse_shell_function_available(self):
        """
        see if unuse is available as a shell function
        """

        # get all the login shell profile stuff
        self.ws.source('/etc/profile')

        output,es = self.ws.execute('type unuse')
        self.assertTrue(re.search(r'unuse is a function',output) is not None,
            "unuse does not appear to be a function: %s" % (output))


    def test_use_recognizes_tags(self):
        """
        check that the use program recognizes the tags command
        """

        # get all the login shell profile stuff
        self.ws.source('/etc/profile')

        envdata  = 'conflict TEST_CHOICE\n'
        envdata += 'desc "Tags Test environment"\n'
        envdata += 'help "This environment tests that use recognizes the tags command"\n'
        envdata += 'tags DEVEL\n'

        script  = 'export HCENVIRON_DIRS=$ENVIRON_CONFIG_DIRS;'
        script += 'export ENVIRON_CONFIG_DIRS=$PWD;'
        script += 'echo "%s" > tagsenv;' % (envdata)
        script += 'use -e tagsenv;'

        output,es = self.ws.execute_script(script)

        self.assertTrue(re.search(r'tags: command not found',output) is None,
            "tags command not recognized in use: %s" % (output))


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()


@pytest.mark.groups_time
class container_groups_config(TestCase):

    def setUp(self):

        self.ws = None


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        if self.ws is not None:
            self.ws.close()


    def _time_groups_for(self,usertype):

        # get user account info
        hubname = self.testdata.find_url_for('https')
        username,userpass = \
            self.testdata.find_account_for(usertype)


        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=username,
                            password=userpass)

        command = '/usr/bin/time -f "{0}" groups {1}'.format('%e',username)
        output,es = self.ws.execute(command)

        time_re = re.compile('%s : ([^\n]+)\r\n([^\n]+)(\r\n)?' % (username))
        match = time_re.search(output)
        self.assertTrue(match is not None, output)

        (grouplist,timecount,junk) = match.groups()

        self.assertTrue(float(timecount) < 1.0,
            "groups command took longer than 1 second: %s" % (timecount))

        self.assertTrue(grouplist != "",
            "groups list is empty: %s" % (output))

        fail_groups = []
        for group in grouplist.split():
            try:
                float(group)
                fail_groups.append(group)
            except ValueError:
                pass

        self.assertTrue(len(fail_groups) == 0,
            "groups with no name: %s" % (fail_groups))


    def test_groups_time_registered_user(self):
        """
        time the groups command for a registered user
        """

        self._time_groups_for('registeredworkspace')


    def test_groups_time_network_user(self):
        """
        time the groups command for a user in the network group
        """

        self._time_groups_for('networkworkspace')


    def test_groups_time_apps_user(self):
        """
        time the groups command for a user in the apps group
        """

        self._time_groups_for('appsworkspace')


@pytest.mark.xfonts
class container_fonts_config(TestCase):


    def setUp(self):

        # get user account info
        hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)


    def test_xfonts_fontpath(self):
        """
        check that the x fontpath includes 100dpi and 75dpi fonts
        """

        # get the running Xvnc command
        command = 'ps auxww | grep -e Xvnc -e Xtigervnc | grep nobody'
        output,es = self.ws.execute(command)
        self.assertTrue(output != '',"Xvnc (or Xtigervnc) doesn't appear to be running")

        # search for the fontpath
        font_re = re.compile('-fp ([^\s]+)')
        match = font_re.search(output)

        self.assertTrue(match is not None,
            "failed to find fontpath in Xvnc (or Xtigervnc) command: %s" % (output))

        fontpaths = match.groups()[0]
        fontdirlist = fontpaths.split(',')

        checked_dirs = []
        fail_dirs = []
        for fontdir in fontdirlist:

            # remove any :unscaled flags from dirname
            fontdir = re.sub('/?:\w+','',fontdir)

            # don't repeat directories
            if fontdir in checked_dirs:
                continue

            # check if the directory exists
            command = 'test -d %s && echo 1 || echo 0' % (fontdir)
            output,es = self.ws.execute(command)

            if output == 0:
                fail_dirs.append(fontdir)

            checked_dirs.append(fontdir)

        self.assertTrue(len(fail_dirs) == 0,
            "the following font directories do not exist: %s" % (fail_dirs))

        def list_index_by_re(l,r):
            rc = re.compile(r)
            matches = filter(rc.match,l)
            if len(matches) == 0:
                return -1
            else:
                return l.index(matches[0])

        f100_dpi_u_idx = list_index_by_re(fontdirlist,'/usr/share/fonts/X11/100dpi/?:unscaled')
        f75_dpi_u_idx  = list_index_by_re(fontdirlist,'/usr/share/fonts/X11/75dpi/?:unscaled')
        Type1_u_idx   = list_index_by_re(fontdirlist,'/usr/share/fonts/X11/Type1/?:unscaled')
        f100_dpi_idx   = list_index_by_re(fontdirlist,'/usr/share/fonts/X11/100dpi/?$')
        f75_dpi_idx    = list_index_by_re(fontdirlist,'/usr/share/fonts/X11/75dpi/?$')
        Type1_idx     = list_index_by_re(fontdirlist,'/usr/share/fonts/X11/Type1/?$')

        retval = ""

        if (f100_dpi_u_idx > Type1_u_idx) and (Type1_u_idx > -1):
            retval += "\n100dpi unscaled fonts listed after Type1 unscaled fonts"

        if (f75_dpi_u_idx > Type1_u_idx) and (Type1_u_idx > -1):
            retval += "\n75dpi unscaled fonts listed after Type1 unscaled fonts"

        if (f100_dpi_u_idx > Type1_idx) and (Type1_idx > -1):
            retval += "\n100dpi unscaled fonts listed after Type1 fonts"

        if (f75_dpi_u_idx > Type1_idx) and (Type1_idx > -1):
            retval += "\n75dpi unscaled fonts listed after Type1 fonts"

        self.assertTrue(retval == '',retval.strip())

    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()


@pytest.mark.icewm
class TestIcewmUserConfig(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')
        self.hubname = self.testdata.find_url_for('https')

        # get into a workspace
        self.cm = ContainerManager()
        self.ws = self.cm.access(host=self.hubname,
                                 username=self.username,
                                 password=self.userpass)


    def teardown_method(self,method):
        pass


    def _check_icewm_config_file(self,fname,points_to):

        # check the file is a link
        assert self.ws.bash_test('-L {0}'.format(fname)), \
            '"{0}" not a link'.format(fname)

        # check the file points to default config
        command = 'readlink -e {0}'.format(fname)
        output,es = self.ws.execute(command)
        assert output == points_to, \
            '"{0}" points to "{1}", expected "{2}"'.format(fname,output,points_to)

        # check the default config is readable
        assert self.ws.bash_test('-r {0}'.format(points_to)), \
            '"{0}" not a readable'.format(points_to)


    def test_icewm_config(self):
        """
        check icewm config files point to hubzero config
        """

        # check if the icewm directory was created.
        msg = "User's IceWM config directory (~/.icewm) was not recreated" + \
              " by new workspace after being deleted"
        assert self.ws.bash_test('-d {0}'.format(ICEWM_CONF_DIR)), msg

        msg = "User's IceWM config directory (~/.icewm) is not readable" + \
              " by new workspace after being deleted"
        assert self.ws.bash_test('-r {0}'.format(ICEWM_CONF_DIR)), msg


        # check if the user has the default icewm user config for hubzero

        for (fname,points_to) in ICEWM_CONF_FILE_SPEC:
            self._check_icewm_config_file(fname,points_to)


    def test_updated_icewm_config(self):
        """
        check if starting a workspace created a new icewm config directory
        after the user deleted their original one.
        """

        # remove the user's icewm config dir
        self.ws.execute('rm -rf ~/.icewm')

        session_number = 0

        # create a new workspace
        ws2 = self.cm.create(host=self.hubname,
                             username=self.username,
                             password=self.userpass)

        session_number,es = ws2.execute('echo $SESSION')

        # exit the new workspace
        ws2.close()

        # stop the new container
        self.cm.stop(self.hubname,self.username,int(session_number))


        # check if the icewm directory was created.
        msg = "User's IceWM config directory (~/.icewm) was not recreated" + \
              " by new workspace after being deleted"
        assert self.ws.bash_test('-d {0}'.format(ICEWM_CONF_DIR)), msg

        msg = "User's IceWM config directory (~/.icewm) is not readable" + \
              " by new workspace after being deleted"
        assert self.ws.bash_test('-r {0}'.format(ICEWM_CONF_DIR)), msg


        # check if the user has the default icewm user config for hubzero

        for (fname,points_to) in ICEWM_CONF_FILE_SPEC:
            self._check_icewm_config_file(fname,points_to)


