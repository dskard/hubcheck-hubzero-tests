import os
import pytest
import re
import sys
import unittest
import urlparse

import hubcheck
from hubcheck.testcase import TestCase
from hubcheck.shell import ContainerManager

pytestmark = [ pytest.mark.container,
               pytest.mark.firewall,
               pytest.mark.weekly,
               pytest.mark.reboot
             ]

@pytest.mark.registereduser
class container_firewall_registered_user(TestCase):

    def setUp(self):

        self.remove_files = []
        self.ws = None

        # get user account info
        self.hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=self.hubname,
                            username=self.username,
                            password=self.userpass)

        # copy the checknet executable to the session directory
        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')

        self.exe_fn = 'checknet.py'
        local_exe_path = os.path.join(hubcheck.conf.settings.data_dir,self.exe_fn)
        self.exe_path = os.path.join(sessiondir,self.exe_fn)
        self.remove_files.append(self.exe_path)

        self.ws.importfile(local_exe_path,self.exe_path,mode=0o700)


    def tearDown(self):

        # remove the executable from the workspace
        for fname in self.remove_files:
            self.ws.execute('rm -f %s' % (fname))

        # get out of the workspace
        # shut down the ssh connection
        if self.ws is not None:
            self.ws.close()


    def _run_checknet(self,desc,uri,port,eresult):

        command = '%s --protocol tcp4 %s %s' % (self.exe_path,uri,port)
        self.logger.debug('command = "%s"' % (command))
        aresult,es = self.ws.execute(command)

        if aresult == 'True':
            aresult = True
        else:
            aresult = False

        results = ''
        if eresult != aresult:
            results = '\n%s connection %s:%s received %s, expected %s' \
                        % (desc,uri,port,aresult,eresult)

        return results


    def test_basic_connections(self):
        """
        login to a tool session container and check basic network firewall
        settings for a registered user in no network affecting groups.
        """

        huburi = self.testdata.find_url_for('https')
        httpport = self.testdata.find_url_for('httpport')
        httpsport = self.testdata.find_url_for('httpsport')

        conns = [
            # (desc, uri, port, expected_result)
            ('hub http',        huburi,             httpport,   True),
            ('hub https',       huburi,             httpsport,  True),
            ('hub mysql',       huburi,             3360,       False),
            ('hub ldap',        huburi,             389,        False),
            ('rappture',        'rappture.org',     80,         True),
            ('google_http',     'google.com',       80,         False),
            ('ecn_systems',     'shay.ecn.purdue.edu', 22,      False),
            ('google_https',    'google.com',       443,        False),
            ('hz_dns0',         'ns0.hubzero.org',  53,         True),
            ('hz_dns1',         'ns1.hubzero.org',  53,         True),
            ('opendns',         '208.67.222.222',   53,         False),
            ('google_dns',      '8.8.8.8',          53,         False),
            ('octave_ftp',      'ftp.octave.org',   21,         False),
            ('localhost',       'localhost',        80,         False),
            ('ecn_matlab',      'matlab-license.ecn.purdue.edu', 1703, False),
        ]

        results = ''
        for (desc,uri,port,eresult) in conns:
            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_nanovis_server_connections(self):
        """
        login to a tool session container and check nanovis
        server connections through the network firewall
        for a registered user in no network affecting groups.
        """

        results = ''
        for host in self.ws.get_nanovis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_molvis_server_connections(self):
        """
        login to a tool session container and check molvis
        server connections through the network firewall
        for a registered user in no network affecting groups.
        """

        results = ''
        for host in self.ws.get_molvis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_vtkvis_server_connections(self):
        """
        login to a tool session container and check vtkvis
        server connections through the network firewall
        for a registered user in no network affecting groups.
        """

        results = ''
        for host in self.ws.get_vtkvis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_vmdmds_server_connections(self):
        """
        login to a tool session container and check vmdmds
        server connections through the network firewall
        for a registered user in no network affecting groups.
        """

        if self.hubname != 'nanohub.org':
            pytest.skip('test only valid for nanohub.org')

        results = ''
        for host in self.ws.get_vmdmds_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_submit_server_connections(self):
        """
        login to a tool session container and check submit
        server connections through the network firewall
        for a registered user in no network affecting groups.
        """

        results = ''
        host_count = 0
        fail_count = 0

        for host in self.ws.get_submit_hosts():
            netloc = urlparse.urlsplit(host).netloc
            uri,port = netloc.split(':',1)
            desc = host
            eresult = True
            host_count += 1

            rtext = self._run_checknet(desc,uri,port,eresult)

            if len(rtext):
                fail_count += 1
                results += rtext

        # we only need one submit host available
        self.assertTrue(host_count > fail_count, results.strip())


    def test_nciphub_specific_connections(self):
        """
        login to a tool session container and check network firewall
        settings specific to nciphub, for a registered user in no
        network affecting groups.
        """

        if self.hubname != 'nciphub.org':
            pytest.skip('test only valid for nciphub.org')

        conns = [
            # (desc, uri, port, expected_result)
            ('github http',     'github.com',        80,        True),
            ('github https',    'github.com',       443,        True),
            ('github git',      'github.com',      9418,        False),
        ]

        results = ''
        for (desc,uri,port,eresult) in conns:
            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


@pytest.mark.networkuser
class container_firewall_network_user(TestCase):

    def setUp(self):

        self.remove_files = []
        self.ws = None

        # get user account info
        self.hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('networkworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=self.hubname,
                            username=self.username,
                            password=self.userpass)

        # copy the checknet executable to the session directory
        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')

        self.exe_fn = 'checknet.py'
        local_exe_path = os.path.join(hubcheck.conf.settings.data_dir,self.exe_fn)
        self.exe_path = os.path.join(sessiondir,self.exe_fn)
        self.remove_files.append(self.exe_path)

        self.ws.importfile(local_exe_path,self.exe_path,mode=0o700)


    def tearDown(self):

        # remove the executable from the workspace
        for fname in self.remove_files:
            self.ws.execute('rm -f %s' % (fname))

        # get out of the workspace
        # shut down the ssh connection
        if self.ws is not None:
            self.ws.close()


    def _run_checknet(self,desc,uri,port,eresult):

        command = '%s --protocol tcp4 %s %s' % (self.exe_path,uri,port)
        self.logger.debug('command = "%s"' % (command))
        aresult,es = self.ws.execute(command)

        if aresult == 'True':
            aresult = True
        else:
            aresult = False

        results = ''
        if eresult != aresult:
            results = '\n%s connection %s:%s received %s, expected %s' \
                        % (desc,uri,port,aresult,eresult)

        return results


    def test_basic_connections(self):
        """
        login to a tool session container and check basic network firewall
        settings for a registered user in the network group.
        """

        huburi = self.testdata.find_url_for('https')
        httpport = self.testdata.find_url_for('httpport')
        httpsport = self.testdata.find_url_for('httpsport')

        conns = [
            # (desc, uri, port, expected_result)
            ('hub http',        huburi,             httpport,   True),
            ('hub https',       huburi,             httpsport,  True),
            ('hub mysql',       huburi,             3360,       False),
            ('hub ldap',        huburi,             389,        False),
            ('rappture',        'rappture.org',     80,         True),
            ('google_http',     'google.com',       80,         True),
            ('ecn_systems',     'shay.ecn.purdue.edu', 22,      True),
            ('google_https',    'google.com',       443,        True),
            ('hz_dns0',         'ns0.hubzero.org',  53,         True),
            ('hz_dns1',         'ns1.hubzero.org',  53,         True),
            ('opendns',         '208.67.222.222',   53,         True),
            ('google_dns',      '8.8.8.8',          53,         True),
            ('octave_ftp',      'ftp.octave.org',   21,         True),
            ('localhost',       'localhost',        80,         False),
            ('ecn_matlab',      'matlab-license.ecn.purdue.edu', 1703, True),
        ]

        results = ''
        for (desc,uri,port,eresult) in conns:
            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_nanovis_server_connections(self):
        """
        login to a tool session container and check nanovis
        server connections through the network firewall
        for a registered user in the network group.
        """

        results = ''
        for host in self.ws.get_nanovis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_molvis_server_connections(self):
        """
        login to a tool session container and check molvis
        server connections through the network firewall
        for a registered user in the network group.
        """

        results = ''
        for host in self.ws.get_molvis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_vtkvis_server_connections(self):
        """
        login to a tool session container and check vtkvis
        server connections through the network firewall
        for a registered user in the network group.
        """

        results = ''
        for host in self.ws.get_vtkvis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_submit_server_connections(self):
        """
        login to a tool session container and check submit
        server connections through the network firewall
        for a registered user in the network group.
        """

        results = ''
        host_count = 0
        fail_count = 0

        for host in self.ws.get_submit_hosts():
            netloc = urlparse.urlsplit(host).netloc
            uri,port = netloc.split(':',1)
            desc = host
            eresult = True
            host_count += 1

            rtext = self._run_checknet(desc,uri,port,eresult)

            if len(rtext):
                fail_count += 1
                results += rtext

        # we only need one submit host available
        self.assertTrue(host_count > fail_count, results.strip())


    def test_nciphub_specific_connections(self):
        """
        login to a tool session container and check network firewall
        settings specific to nciphub, for a registered user in the
        network group.
        """

        if self.hubname != 'nciphub.org':
            pytest.skip('test only valid for nciphub.org')

        conns = [
            # (desc, uri, port, expected_result)
            ('github http',     'github.com',        80,        True),
            ('github https',    'github.com',       443,        True),
            ('github git',      'github.com',      9418,        True),
        ]

        results = ''
        for (desc,uri,port,eresult) in conns:
            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


@pytest.mark.purdueuser
class container_firewall_purdue_user(TestCase):

    def setUp(self):

        self.remove_files = []
        self.ws = None

        # get user account info
        self.hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('purdueworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=self.hubname,
                            username=self.username,
                            password=self.userpass)

        # copy the checknet executable to the session directory
        self.ws.execute('cd $SESSIONDIR')
        sessiondir,es = self.ws.execute('pwd')

        self.exe_fn = 'checknet.py'
        local_exe_path = os.path.join(hubcheck.conf.settings.data_dir,self.exe_fn)
        self.exe_path = os.path.join(sessiondir,self.exe_fn)
        self.remove_files.append(self.exe_path)

        self.ws.importfile(local_exe_path,self.exe_path,mode=0o700)


    def tearDown(self):

        # remove the executable from the workspace
        for fname in self.remove_files:
            self.ws.execute('rm -f %s' % (fname))

        # get out of the workspace
        # shut down the ssh connection
        if self.ws is not None:
            self.ws.close()


    def _run_checknet(self,desc,uri,port,eresult):

        command = '%s --protocol tcp4 %s %s' % (self.exe_path,uri,port)
        self.logger.debug('command = "%s"' % (command))
        aresult,es = self.ws.execute(command)

        if aresult == 'True':
            aresult = True
        else:
            aresult = False

        results = ''
        if eresult != aresult:
            results = '\n%s connection %s:%s received %s, expected %s' \
                        % (desc,uri,port,aresult,eresult)

        return results


    def test_basic_connections(self):
        """
        login to a tool session container and check basic network firewall
        settings for a registered user in the purdue group.
        """

        huburi = self.testdata.find_url_for('https')
        httpport = self.testdata.find_url_for('httpport')
        httpsport = self.testdata.find_url_for('httpsport')

        conns = [
            # (desc, uri, port, expected_result)
            ('hub http',        huburi,             httpport,   True),
            ('hub https',       huburi,             httpsport,  True),
            ('hub mysql',       huburi,             3360,       False),
            ('hub ldap',        huburi,             389,        False),
            ('rappture',        'rappture.org',     80,         True),
            ('google_http',     'google.com',       80,         False),
            ('ecn_systems',     'shay.ecn.purdue.edu', 22,      True),
            ('google_https',    'google.com',       443,        False),
            ('hz_dns0',         'ns0.hubzero.org',  53,         True),
            ('hz_dns1',         'ns1.hubzero.org',  53,         True),
            ('opendns',         '208.67.222.222',   53,         False),
            ('google_dns',      '8.8.8.8',          53,         False),
            ('octave_ftp',      'ftp.octave.org',   21,         False),
            ('localhost',       'localhost',        80,         False),
            ('ecn_matlab',      'matlab-license.ecn.purdue.edu', 1703, True),
        ]

        results = ''
        for (desc,uri,port,eresult) in conns:
            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_nanovis_server_connections(self):
        """
        login to a tool session container and check nanovis
        server connections through the network firewall
        for a registered user in the purdue group.
        """

        results = ''
        for host in self.ws.get_nanovis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_molvis_server_connections(self):
        """
        login to a tool session container and check molvis
        server connections through the network firewall
        for a registered user in the purdue group.
        """

        results = ''
        for host in self.ws.get_molvis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_vtkvis_server_connections(self):
        """
        login to a tool session container and check vtkvis
        server connections through the network firewall
        for a registered user in the purdue group.
        """

        results = ''
        for host in self.ws.get_vtkvis_hosts():
            uri,port = host.split(':',1)
            desc = host
            eresult = True

            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


    def test_submit_server_connections(self):
        """
        login to a tool session container and check submit
        server connections through the network firewall
        for a registered user in the purdue group.
        """

        results = ''
        host_count = 0
        fail_count = 0

        for host in self.ws.get_submit_hosts():
            netloc = urlparse.urlsplit(host).netloc
            uri,port = netloc.split(':',1)
            desc = host
            eresult = True
            host_count += 1

            rtext = self._run_checknet(desc,uri,port,eresult)

            if len(rtext):
                fail_count += 1
                results += rtext

        # we only need one submit host available
        self.assertTrue(host_count > fail_count, results.strip())


    def test_nciphub_specific_connections(self):
        """
        login to a tool session container and check network firewall
        settings specific to nciphub, for a registered user in the
        purdue groups.
        """

        if self.hubname != 'nciphub.org':
            pytest.skip('test only valid for nciphub.org')

        conns = [
            # (desc, uri, port, expected_result)
            ('github http',     'github.com',        80,        True),
            ('github https',    'github.com',       443,        True),
            ('github git',      'github.com',      9418,        False),
        ]

        results = ''
        for (desc,uri,port,eresult) in conns:
            results += self._run_checknet(desc,uri,port,eresult)

        self.assertTrue(len(results) == 0, results.strip())


#class container_firewall_hubdev_user(TestCase):
#
#    def setUp(self):
#
#        self.remove_files = []
#        self.ws = None
#
#        # get user account info
#        hubname = self.testdata.find_url_for('https')
#        self.username,self.userpass = \
#            self.testdata.find_account_for('hubdevworkspace')
#
#        cm = ContainerManager()
#        self.ws = cm.access(host=hubname,
#                            username=self.username,
#                            password=self.userpass)
#
#        # copy the checknet executable to the session directory
#        self.ws.execute('cd $SESSIONDIR')
#        sessiondir,es = self.ws.execute('pwd')
#
#        self.exe_fn = 'checknet.py'
#        local_exe_path = os.path.join(hubcheck.conf.settings.data_dir,self.exe_fn)
#        self.exe_path = os.path.join(sessiondir,self.exe_fn)
#        self.remove_files.append(self.exe_path)
#
#        self.ws.importfile(local_exe_path,self.exe_path,mode=0o700)
#
#
#    def tearDown(self):
#
#        # remove the executable from the workspace
#        for fname in self.remove_files:
#            self.ws.execute('rm -f %s' % (fname))
#
#        # get out of the workspace
#        # shut down the ssh connection
#        if self.ws is not None:
#            self.ws.close()
#
#
#    def _run_checknet(self,desc,uri,port,eresult):
#
#        command = '%s --protocol tcp4 %s %s' % (self.exe_path,uri,port)
#        self.logger.debug('command = "%s"' % (command))
#        aresult,es = self.ws.execute(command)
#
#        if aresult == 'True':
#            aresult = True
#        else:
#            aresult = False
#
#        results = ''
#        if eresult != aresult:
#            results = '\n%s connection %s:%s received %s, expected %s' \
#                        % (desc,uri,port,aresult,eresult)
#
#        return results
#
#
#    def test_basic_connections(self):
#        """
#        login to a tool session container and check basic network firewall
#        settings for a registered user in the hubdev group.
#        """
#
#        huburi = self.testdata.find_url_for('https')
#        httpport = self.testdata.find_url_for('httpport')
#        httpsport = self.testdata.find_url_for('httpsport')
#
#        conns = [
#            # (desc, uri, port, expected_result)
#            ('hub http',        huburi,             httpport,   True),
#            ('hub https',       huburi,             httpsport,  True),
#            ('hub mysql',       huburi,             3360,       False),
#            ('hub ldap',        huburi,             389,        False),
#            ('rappture',        'rappture.org',     80,         True),
#            ('google_http',     'google.com',       80,         False),
#            ('ecn_systems',     'shay.ecn.purdue.edu', 22,      False),
#            ('google_https',    'google.com',       443,        False),
#            ('hz_dns0',         'ns0.hubzero.org',  53,         True),
#            ('hz_dns1',         'ns1.hubzero.org',  53,         True),
#            ('opendns',         '208.67.222.222',   53,         False),
#            ('google_dns',      '8.8.8.8',          53,         False),
#            ('octave_ftp',      'ftp.octave.org',   21,         False),
#            ('localhost',       'localhost',        80,         False),
#            ('ecn_matlab',      'matlab-license.ecn.purdue.edu', 1703, False),
#        ]
#
#        results = ''
#        for (desc,uri,port,eresult) in conns:
#            results += self._run_checknet(desc,uri,port,eresult)
#
#        self.assertTrue(len(results) == 0, results.strip())
#
#
#    def test_nanovis_server_connections(self):
#        """
#        login to a tool session container and check nanovis
#        server connections through the network firewall
#        for a registered user in the submit group.
#        """
#
#        results = ''
#        for host in self.ws.get_nanovis_hosts():
#            uri,port = host.split(':',1)
#            desc = host
#            eresult = True
#
#            results += self._run_checknet(desc,uri,port,eresult)
#
#        self.assertTrue(len(results) == 0, results.strip())
#
#
#    def test_molvis_server_connections(self):
#        """
#        login to a tool session container and check molvis
#        server connections through the network firewall
#        for a registered user in the hubdev group.
#        """
#
#        results = ''
#        for host in self.ws.get_molvis_hosts():
#            uri,port = host.split(':',1)
#            desc = host
#            eresult = True
#
#            results += self._run_checknet(desc,uri,port,eresult)
#
#        self.assertTrue(len(results) == 0, results.strip())
#
#
#    def test_vtkvis_server_connections(self):
#        """
#        login to a tool session container and check vtkvis
#        server connections through the network firewall
#        for a registered user in the hubdev group.
#        """
#
#        results = ''
#        for host in self.ws.get_vtkvis_hosts():
#            uri,port = host.split(':',1)
#            desc = host
#            eresult = True
#
#            results += self._run_checknet(desc,uri,port,eresult)
#
#        self.assertTrue(len(results) == 0, results.strip())
#
#
#    def test_submit_server_connections(self):
#        """
#        login to a tool session container and check submit
#        server connections through the network firewall
#        for a registered user in the hubdev group.
#        """
#
#        results = ''
#        host_count = 0
#        fail_count = 0
#
#        for host in self.ws.get_submit_hosts():
#            netloc = urlparse.urlsplit(host).netloc
#            uri,port = netloc.split(':',1)
#            desc = host
#            eresult = True
#            host_count += 1
#
#            rtext = self._run_checknet(desc,uri,port,eresult)
#
#            if len(rtext):
#                fail_count += 1
#                results += rtext
#
#        # we only need one submit host available
#        self.assertTrue(host_count > fail_count, results.strip())
#
