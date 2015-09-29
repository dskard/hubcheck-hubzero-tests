import unittest
import sys
import os
import pytest
import re
import ConfigParser
import StringIO
import urlparse

import hubcheck
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager
from hubcheck.shell import SFTPClient


pytestmark = [ pytest.mark.container,
               pytest.mark.submit,
               pytest.mark.reboot
             ]


sayhi_py_fn = "sayhi.py"
sayhi_py_data = """
import time
import sys

if len(sys.argv) < 2:
    name = "world"
else:
    name = sys.argv[1]

time.sleep(10)

print "hello %s" % (name)
"""


@pytest.mark.weekly
@pytest.mark.submituser
class TestContainerSubmitSubmituser(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = self.testdata.find_account_for('submituser')
        hubname = self.testdata.find_url_for('https')

        cm = ContainerManager()

        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')
        self.exe_path = os.path.join(sessiondir,sayhi_py_fn)
        self.ws.importfile(sayhi_py_data,self.exe_path,mode=0o600,is_data=True)

        self.ws.timeout = 30


    def teardown_method(self,method):

        try:
            self.ws.execute('rm -f %s' % (self.exe_path))
        finally:
            # get out of the workspace
            # shut down the ssh connection
            self.ws.close()


    @pytest.mark.submit_help
    def test_submit_help_submituser(self):
        """
        get the help text from submit for a submituser
        """

        command = 'submit --help'

        # request the submit help menu
        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        assert output != '', "'%s' returned no output" % output


    @pytest.mark.submit_local
    def test_submit_local_no_metrics_submituser(self):
        """
        as submituser, submit local using "submit --local"
        """

        command = 'submit --local python %s' % (self.exe_path)

        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        expected = 'hello world'
        assert output == expected, \
            "issuing the command '%s' returned '%s', expected '%s'" \
            % (command,output,expected)


    @pytest.mark.submit_local
    def test_submit_local_metrics_submituser(self):
        """
        as submituser, submit local using "submit --local --metrics"
        """

        command = 'submit --local --metrics python %s' % (self.exe_path)

        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        # output is embedded between SUBMIT-METRICS stanzas
        metricsre1 = re.compile(r"""=SUBMIT-METRICS=>\sjob=(\d+)\s+
                                   hello\ world\s+
                                   =SUBMIT-METRICS=>\sjob=(\d+)\s
                                                      venue=([^\s]+)\s
                                                      status=([^\s]+)\s
                                                      cputime=([^\s]+)\s
                                                      realtime=([^\s]+)\s*""",
                                re.VERBOSE)

        # output is after SUBMIT-METRICS stanzas
        metricsre2 = re.compile(r"""=SUBMIT-METRICS=>\sjob=(\d+)\s+
                                    =SUBMIT-METRICS=>\sjob=(\d+)\s
                                                       venue=([^\s]+)\s
                                                       status=([^\s]+)\s
                                                       cputime=([^\s]+)\s
                                                       realtime=([^\s]+)\s+
                                   hello\ world\s*""",
                                re.VERBOSE)
        assert (metricsre1.match(output) or metricsre2.match(output)) \
            is not None, "issuing the command '%s' returned '%s'" \
            % (command, output)


@pytest.mark.nightly
@pytest.mark.registereduser
class TestContainerSubmitRegisteredWorkspace(TestCase2):

    def setup_method(self,method):

        # get user account info
        self.username,self.userpass = self.testdata.find_account_for('registeredworkspace')
        hubname = self.testdata.find_url_for('https')

        self.submit_config = '/etc/submit/submit-client.conf'

        cm = ContainerManager()

        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')
        self.exe_path = os.path.join(sessiondir,sayhi_py_fn)
        self.ws.importfile(sayhi_py_data,self.exe_path,mode=0o600,is_data=True)

        self.ws.timeout = 30


    def teardown_method(self,method):

        # exit the workspace
        try:
            self.ws.execute('rm -f %s' % (self.exe_path))
        finally:
            # get out of the workspace
            # shut down the ssh connection
            self.ws.close()


    @pytest.mark.submit_help
    def test_submit_help_registeredworkspace(self):
        """
        get the help text from submit for a registeredworkspace user
        """

        command = 'submit --help'

        # request the submit help menu
        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        assert output != '', "'%s' returned no output" % output


    @pytest.mark.submit_local
    def test_submit_local_no_metrics_registeredworkspace(self):
        """
        as a registeredworkspace user, submit local using "submit --local"
        """

        command = 'submit --local python %s' % (self.exe_path)

        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        expected = 'hello world'
        assert output == expected, \
            "issuing the command '%s' returned '%s', expected '%s'" \
            % (command,output,expected)


    @pytest.mark.submit_local
    def test_submit_local_metrics_registeredworkspace(self):
        """
        as a registeredworkspace user, submit local using
        "submit --local --metrics"
        """

        command = 'submit --local --metrics python %s' % (self.exe_path)

        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        # output is embedded between SUBMIT-METRICS stanzas
        metricsre1 = re.compile(r"""=SUBMIT-METRICS=>\sjob=(\d+)\s+
                                   hello\ world\s+
                                   =SUBMIT-METRICS=>\sjob=(\d+)\s
                                                      venue=([^\s]+)\s
                                                      status=([^\s]+)\s
                                                      cputime=([^\s]+)\s
                                                      realtime=([^\s]+)\s*""",
                                re.VERBOSE)

        # output is after SUBMIT-METRICS stanzas
        metricsre2 = re.compile(r"""=SUBMIT-METRICS=>\sjob=(\d+)\s+
                                    =SUBMIT-METRICS=>\sjob=(\d+)\s
                                                       venue=([^\s]+)\s
                                                       status=([^\s]+)\s
                                                       cputime=([^\s]+)\s
                                                       realtime=([^\s]+)\s+
                                   hello\ world\s*""",
                                re.VERBOSE)

        assert (metricsre1.match(output) or metricsre2.match(output)) \
            is not None, "issuing the command '%s' returned '%s'" \
            % (command, output)


    @pytest.mark.submit_local
    def test_submit_local_noHeartbeat_flag(self):
        """
        check that submit accepts the --noHeartbeat flag
        """

        command = 'submit --local --noHeartbeat python %s' % (self.exe_path)

        output,es = self.ws.execute(command,fail_on_exit_code=False)

        assert es == 0,"While executing commands: %s\n%s" % (command,output)

        expected = 'hello world'
        assert output == expected, \
            "issuing the command '%s' returned '%s', expected '%s'" \
            % (command,output,expected)


    @pytest.mark.submit_targets
    def test_submit_resources_targets(self):
        """
        check that at least one of the submit targets is available
        """

        # copy the checknet executable to the session directory
        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')
        exe_fn = 'checknet.py'
        local_exe_path = os.path.join(hubcheck.conf.settings.data_dir,exe_fn)
        exe_path = os.path.join(sessiondir,exe_fn)
        self.ws.importfile(local_exe_path,exe_path,mode=0o700)


        data = self.ws.read_file(self.submit_config)
        s = StringIO.StringIO(data)

        c = ConfigParser.ConfigParser()
        c.readfp(s)
        listen_uris = c.get('client','listenURIs')

        # could look like one of these:
        #
        # tls://hubzero.org:831
        # tcp://hubzero.org:830, tls://hubzero.org:831

        submit_uri = None

        listen_uris = listen_uris.split(',')
        for uri in listen_uris:
            uri = uri.strip()
            netloc = urlparse.urlsplit(uri).netloc
            (host,port) = netloc.split(':')

            command = '%s --protocol tcp4 %s %s' % (exe_path,host,int(port))
            listening,es = self.ws.execute(command)

            if listening == 'True':
                submit_uri = uri
                break

        self.ws.execute('rm -f %s' % (exe_path))

        assert submit_uri is not None, \
            "Could not connect to submit server. listen_uris = %s" % listen_uris


    @pytest.mark.submit_targets
    def test_submit_resources_configuration_readable(self):
        """
        check if the submit client config file is readable
        """

        command = '[[ -r %s ]] && echo 1 || echo 0' % self.submit_config
        output,es = self.ws.execute(command)
        assert output == '1', \
            'Submit configuration file (%s) is not readable' \
            % self.submit_config


    @pytest.mark.submit_version
    def test_submit_version(self):
        """
        check the full submit pipeline with the --version flag
        """

        command = 'submit --version'

        # failure to contact the submit server
        # could take over 2 minutes to return.
        self.ws.timeout = 180

        output,es = self.ws.execute(command,fail_on_exit_code=False)

        # the output should look like this:
        # Submit client version: 2.4.2
        # Submit server version: 2.4.2
        # Submit distributor version: 2.4.3

        version_re = re.compile(r"""Submit\ client\ version:\s([^\s]+)\s+
                                    Submit\ server\ version:\s([^\s]+)\s+
                                    Submit\ distributor\ version:\s([^\s]+)\s*""",
                                re.VERBOSE)

        assert version_re.match(output) is not None, \
            "command '%s' returned: %s" % (command,output)


@pytest.mark.registereduser
@pytest.mark.submit_examples
@pytest.mark.weekly
class TestContainerSubmitParameterExamples(TestCase2):


    def setup_method(self,method):

        self.remove_files = []

        # get user account info
        self.username,self.userpass = self.testdata.find_account_for('registeredworkspace')
        hubname = self.testdata.find_url_for('https')

        # access a tool session container
        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)

        # copy the executable to the session directory
        self.sftp = SFTPClient(
            host=hubname, username=self.username, password=self.userpass)

        local_exe_path = os.path.join(hubcheck.conf.settings.data_dir,
                                 'capacitor_voltage','sim1.py')

        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')

        self.exe_fn = 'sim1.py'
        self.exe_path = os.path.join(sessiondir,self.exe_fn)
        self.remove_files.append(self.exe_path)

        self.sftp.chdir(sessiondir)
        self.sftp.put(local_exe_path,self.exe_fn)
        self.sftp.chmod(self.exe_path,0700)

        # shouldn't take more than 60 seconds
        # to run submit --local commands
        self.ws.timeout = 60


    def teardown_method(self,method):

        # remove the executable and config files
        for fname in self.remove_files:
            self.sftp.remove(fname)
        self.sftp.close()

        # exit the workspace
        self.ws.close()


    def test_submit_single_parameter_substitution(self):
        """
        submit single parameter substitution in input deck

        submit --local -p @@C=10e-12,100e-12,1e-6 \
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        num_sweep_params = 3
        command = 'submit --local -p @@C=10e-12,100e-12,1e-6 %s --inputdeck @:%s' \
            % (self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_multiple_parameter_substitution(self):
        """
        submit multiple parameter substitution in input deck

        submit --local -p @@Vin=0:0.2:5 -p @@C=10e-12,100e-12,1e-6 \
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        num_sweep_params = 26*3
        command  = 'submit --local'
        command += ' -p @@Vin=0:0.2:5'
        command += ' -p @@C=10e-12,100e-12,1e-6'
        command += ' %s --inputdeck @:%s'
        command = command % (self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # adjust the timeout to allow for 5 minutes to run the tests
        old_timeout = self.ws.timeout
        self.ws.timeout = 300

        # run the command
        output,es = self.ws.execute(command)

        # adjust the timeout back to the default
        self.ws.timeout = old_timeout

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_read_parameters_from_file(self):
        """
        submit multiple parameter substitutions, reading parameters
        from a file named 'params'. perform substitutions in an input deck

        submit --local -p params sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        self.paramsfn = 'params'
        num_sweep_params = 26*3
        command  = 'submit --local -p %s %s --inputdeck @:%s'
        command = command % (self.paramsfn,self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # write the parameters file to disk in the container.
        params_data  = "parameter @@Vin=0:0.2:5\n" \
                       + "parameter @@C = 10e-12,100e-12,1e-6\n"
        self.ws.write_file(self.paramsfn,params_data)
        self.remove_files.append(self.paramsfn)

        # adjust the timeout to allow for 5 minutes to run the tests
        old_timeout = self.ws.timeout
        self.ws.timeout = 300

        # run the command
        output,es = self.ws.execute(command)

        # adjust the timeout back to the default
        self.ws.timeout = old_timeout

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_read_params_file_load_extra_params(self):
        """
        read submit parameters from a file, load additional parameters
        from the command line.

        submit --local -p "params;@@Vin=5-7;@@R=100e3" \
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        self.paramsfn = 'params'
        # 3 C values * 3 Vin values * 1 R value
        num_sweep_params = 3*3*1
        command  = 'submit --local' \
                   ' -p "%s;@@Vin=5-7;@@R=100e3"' \
                   ' %s --inputdeck @:%s' \
                   % (self.paramsfn,self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\nR = @@R\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # write the parameters file to disk in the container.
        params_data = "parameter @@C = 10e-12,100e-12,1e-6\n"
        self.ws.write_file(self.paramsfn,params_data)
        self.remove_files.append(self.paramsfn)

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_read_params_from_csv_file(self):
        """
        read submit parameters from a csv file

        submit --local -d input.csv \
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        self.paramsfn = 'input.csv'
        # 4 Vin & C combinations
        num_sweep_params = 4
        command  = 'submit --local -d %s'
        command += ' %s --inputdeck @:%s'
        command = command % (self.paramsfn,self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # write the parameters file to disk in the container.
        params_data = "@@Vin, @@C\n1.1, 1e-12\n2.2, 1e-12\n1.1, 10e-12\n2.2, 10e-12"
        self.ws.write_file(self.paramsfn,params_data)
        self.remove_files.append(self.paramsfn)

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    @pytest.mark.stalenfs
    def test_submit_read_csv_params_load_extras_from_args(self):
        """
        read submit parameters from a csv file, load extra params

        submit --local -d input.csv -p "@@R=1e3-1e5 in 3 log"\
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        self.paramsfn = 'input.csv'
        # 4 Vin & C combinations * 3 R values
        num_sweep_params = 4*3
        command  = 'submit --local -d %s'
        command += ' -p "@@R=1e3-1e5 in 3 log"'
        command += ' %s --inputdeck @:%s'
        command = command % (self.paramsfn,self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\nR = @@R\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # write the parameters file to disk in the container.
        params_data = "@@Vin, @@C\n1.1, 1e-12\n2.2, 1e-12\n1.1, 10e-12\n2.2, 10e-12"
        self.ws.write_file(self.paramsfn,params_data)
        self.remove_files.append(self.paramsfn)

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    @pytest.mark.stalenfs
    @pytest.mark.clparse
    def test_submit_read_csv_params_load_extras_from_file(self):
        """
        read submit parameters from a csv file, load extra params

        submit --local -d input.csv -i @:data.txt \
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        self.paramsfn = 'input.csv'
        self.extrafn = 'data.txt'
        # 4 Vin & C combinations
        num_sweep_params = 4
        command  = 'submit --local -d %s -i @:%s %s --inputdeck @:%s' \
                    % (self.paramsfn,self.extrafn,self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)
        self.ws.execute('ls {0}'.format(self.indeckfn))

        # write the input deck to disk in the container.
        extra_template = "# extra templated data file\nVin = @@Vin\nC = @@C\n"
        self.ws.write_file(self.extrafn,extra_template)
        self.remove_files.append(self.extrafn)
        self.ws.execute('ls {0}'.format(self.extrafn))

        # write the parameters file to disk in the container.
        params_data = "@@Vin, @@C\n1.1, 1e-12\n2.2, 1e-12\n1.1, 10e-12\n2.2, 10e-12"
        self.ws.write_file(self.paramsfn,params_data)
        self.remove_files.append(self.paramsfn)
        self.ws.execute('ls {0}'.format(self.paramsfn))

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_change_separator(self):
        """
        Change the separator to slash

        submit --local -s / -p @@Vin=5/6/7 -s , -p @@C=1e-12,10e-12 \
            sim1.py --inputdeck @:sim1.indeck.template
        """

        self.indeckfn = 'sim1.indeck.template'
        # 3 Vin values * 2 C values
        num_sweep_params = 3*2
        command  = 'submit --local' \
                   + ' -s / -p @@Vin=5/6/7' \
                   + ' -s , -p @@C=1e-12,10e-12' \
                   + ' %s --inputdeck @:%s' \
                   % (self.exe_path,self.indeckfn)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input deck to disk in the container.
        indeck_template = "[inputs]\nC = @@C\nVin = @@Vin\n"
        self.ws.write_file(self.indeckfn,indeck_template)
        self.remove_files.append(self.indeckfn)

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_parameter_substitute_in_command_arguments(self):
        """
        Substitute parameters into command line arguments

        submit --local -p @@Vin=1-5 sim1.py --Vin @@Vin
        """

        # 5 Vin values
        num_sweep_params = 5
        command  = 'submit --local -p @@Vin=1-5 %s --Vin @@Vin'
        command = command % (self.exe_path)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    def test_submit_parameter_glob_file_search(self):
        """
        Perform glob style file pattern matching to generate parameters
        substitutions.

        submit --local -p @@file=glob:sim1.indeck* sim1.py --inputdeck @@file
        """

        self.fbase = 'sim1.indeck'
        # 5 Vin values
        num_sweep_params = 4
        command  = 'submit --local -p @@file=glob:%s* %s --inputdeck @@file'
        command = command % (self.fbase,self.exe_path)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # write the input decks to disk in the container.
        counter = 0
        for (Vin,C) in [(1.1,1e-12),(2.2,1e-12),(1.1,10e-12),(2.2,10e-12)]:
            counter += 1
            indeck_template = "[inputs]\nC = %s\nVin = %s\n" % (C,Vin)
            fname = self.fbase + '.%s' % (counter)
            self.ws.write_file(fname,indeck_template)
            self.remove_files.append(fname)


        # run the command
        output,es = self.ws.execute(command)

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # get the directory names of sweep results
        output,es = self.ws.execute('ls -d %s/*/' % resultsdir)

        # check if the number of directories matches the number of
        # parameters we used in the sweep
        results_dirs = output.split()
        num_results_dirs = len(results_dirs)
        assert num_results_dirs == num_sweep_params, \
            "num_results_dirs = %s, num_sweep_params = %s" \
            % (num_results_dirs,num_sweep_params)

        # check that the output file was copied back to
        # the results directory
        for r in results_dirs:
            command = '[[ -r %s/out.log ]] && echo 1 || echo 0' % r
            exists,es = self.ws.execute(command)
            assert exists == '1', "missing %s/out.log" % r


    @pytest.mark.submit_parameter_error
    def test_submit_parameter_error_code(self):
        """
        Check for submit errors after substituting parameters
        into command line arguments

        submit --local -p @@Vin=1-3 sim1.py --Vin @@Vin
        """

        # 3 Vin values
        num_sweep_params = 3
        command  = 'submit --local -p @@Vin=1-3 %s --Vin @@Vin'
        command = command % (self.exe_path)

        # we redirect stdin to a file for submit commands with
        # parameters so the ncurses window doesn't pop up and
        # interfere with our expect like terminal parsing.
        command += ' 0</dev/null'

        # run the command
        output,es = self.ws.execute(command,fail_on_exit_code=False)

        if es == 0:
            return

        # search for results
        results_re = re.compile('Results are stored in directory ([^\s]+)')
        match = results_re.search(output)
        assert match is not None, \
            "could not find results directory in output: %s" % output
        resultsdir = match.group(1)

        # look for a stderr file
        stderr_file = os.path.basename(resultsdir)
        stderr_file_path = os.path.join(resultsdir,stderr_file) + ".stderr"

        stderr_file_exists = self.ws.bash_test('-e %s' % (stderr_file_path))
        assert stderr_file_exists, \
            'The command "%s" produced the output "%s"' % (command,output) \
            + ' and exited with exit code %s, but' % (es) \
            + ' the stderr file "%s" does not exist' % (stderr_file_path)

        read_stderr_cmd = 'cat %s' % (stderr_file_path)
        stderr_out,stderr_es = self.ws.execute(read_stderr_cmd)

        # we don't really want the file to be empty, but we want to
        # capture whatever is in the file.
        assert stderr_out == '', \
            'The command "%s", produced the output "%s",' % (command,output) \
            + ' exited with exit code %s,' % (es) \
            + ' and wrote the following to stderr file' \
            + ' "%s": %s' % (stderr_file_path, stderr_out)

