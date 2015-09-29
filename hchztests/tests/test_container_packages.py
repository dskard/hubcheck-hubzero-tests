import unittest
import os
import pytest
import re
import sys
import ConfigParser
import StringIO
import urlparse

import hubcheck
from hubcheck.testcase import TestCase
from hubcheck.shell import ContainerManager


pytestmark = [ pytest.mark.container,
               pytest.mark.packages,
               pytest.mark.reboot
             ]


wheezypkginfo = [
#    PACKAGE NAME     PACKAGE DESCRIPTION                                        IS INSTALLED
    ( 'autoconf',    'the automatic configure script builder',                    True ),
    ( 'ant',         'Java based build tool like make',                           True ),
    ( 'bash',        'the GNU Bourne Again SHell',                                True ),
    ( 'bc',          'the GNU bc arbitrary precision calculator language',        True ),
    ( 'bison',       'a parser generator that is compatible with YACC',           True ),
    ( 'blt',         'the BLT extension library for Tcl/Tk - run-time package',   True ),
    ( 'bzip2',       'high-quality block-sorting file compressor - utilities',    True ),
    ( 'cmake',       'the cross-platform, open-source make system',               True ),
    ( 'coreutils',   'GNU core utilities',                                        True ),
    ( 'cvs',         'a concurrent a version control system',                     True ),
    ( 'ddd',         'the Data Display Debugger',                                 True ),
    ( 'doxygen',     'a documentation system for C, C++, Java, Python and other languages', True ),
    ( 'dpkg-dev',    'Debian package development tools',                          True ),
    ( 'dx',          'the OpenDX (IBM Visualization Data Explorer)',              True ),
    ( 'emacs',       'The GNU Emacs editor',                                      True ),
    ( 'expect',      'a program that can automate interactive applications',      True ),
    ( 'ffmpeg',      'an audio/video encoder, streaming server & audio/video file converter', True ),
    ( 'flex',        'a fast lexical analyzer generator',                         True ),
    ( 'fonts-freefont-ttf', 'Freefont Serif, Sans and Mono Truetype fonts',       True ),
    ( 'g++',         'the GNU C++ compiler',                                      True ),
    ( 'gcc',         'the GNU C compiler',                                        True ),
    ( 'gdb',         'the GNU C Debugger',                                        True ),
    ( 'geany',       'fast and lightweight IDE',                                  True ),
#    ( 'gedit',       'the official text editor of the GNOME desktop environment', True ),
    ( 'gfortran',    'the GNU Fortran 95 compiler',                               True ),
    ( 'gimp',        'the GNU Image Manipulation Program',                        True ),
    ( 'grep',        'a utility to search for text in files',                     True ),
    ( 'gv',          'a PostScript and PDF viewer for X',                         True ),
    ( 'gzip',        'GNU compression utilities',                                 True ),
    ( 'htop',        'an interactive processes viewer',                           True ),
    ( 'hubzero-chuse', "Graphical front end to 'use'",                            True ),
    ( 'hubzero-filexfer', 'HUBzero Session File Transfer Utility',                True ),
    ( 'hubzero-icewm', 'Provides configuration information for using icewm with hubzero', True ),
    ( 'hubzero-icewm-captive', 'Start a captive hubzero icewm script',            True ),
    ( 'hubzero-icewm-themes', 'Themes for the icewm Window Manager',              True ),
    ( 'hubzero-mw-session', 'HUBzero Middleware Session Tools',                   True ),
    ( 'hubzero-ratpoison-captive', 'HUBzero captive ratpoison window manager script', True ),
    ( 'hubzero-use', 'HUBzero User Environment Manager',                          True ),
    ( 'hubzero-use-apps', "HUBzero apps environment for 'use'",                   True ),
    ( 'iceweasel',   'Web browser based on Firefox',                              True ),
    ( 'icewm',       'wonderful Win95-OS/2-Motif-like window manager',            True ),
    ( 'imagemagick', 'a set of image manipulation programs',                      True ),
    ( 'inkscape',    'a vector-based drawing program',                            True ),
    ( 'kazehakase',  'GTK+-based web browser that allows pluggable rendering engines', False ),
    ( 'kazehakase-gecko', 'Gecko rendering engine for kazehakase',                False ),
    ( 'kcachegrind', 'a visualisation tool for the Valgrind profiler',            True ),
    ( 'less',        'a pager program similar to more',                           True ),
    ( 'libavcodec-dev',  'library to encode decode multimedia streams - devel files', True ),
    ( 'libavformat-dev', 'development files for the demuxer library from the ffmpeg project', True ),
    ( 'libavutil-dev',   'the ffmpeg video utility devel files',                  True ),
    ( 'libdx4-dev',  'OpenDX (IBM Visualization Data Explorer) - development files', True ),
    ( 'libexpat1-dev',   'XML parsing C library - development kit',               True ),
    ( 'libfreetype6-dev',    'FreeType 2 font engine, development files',         True ),
#    ( 'libgl1-mesa-dev', 'A free implementation of the OpenGL API -- development files', True ),
    ( 'libgl1-mesa-swx11-dev', 'free implementation of the OpenGL API -- development files', True ),
#    ( 'libglui-dev', 'a GLUT-based C++ user interface library',                   True ),
    ( 'libjpeg8-dev', 'Development files for the IJG JPEG library',               True ),
    ( 'libmysqlclient-dev', 'MySQL database development files',                   True ),
    ( 'libncurses5', 'shared libraries for terminal handling',                    True ),
    ( 'libncurses5-dev', "developer's libraries and docs for ncurses",            True ),
    ( 'liboctave-dev', "Development files for the GNU Octave language",           True ),
    ( 'libperl-dev', 'Perl library development files',                            True ),
    ( 'libpng12-dev', 'PNG library - development',                                True ),
    ( 'libqhull-dev', 'calculate convex hulls and related structures - needed for octave-3.2.4', True ),
    ( 'libreadline-dev', 'GNU readline and history libraries, development files', True ),
    ( 'libssl-dev',  'SSL development libraries',                                 True ),
    ( 'libswscale-dev', 'Development files for libswscale',                       True ),
    ( 'libtiff4-dev', 'Tag Image File Format library (TIFF), development files',  True ),
    ( 'libx11-dev',  'X11 client-side library (development headers)',             True ),
    ( 'libxext-dev', 'X11 miscellaneous extensions library (development headers)', True ),
    ( 'libxft-dev',  'FreeType-based font drawing library for X (development files)', True ),
    ( 'libxpm-dev',  'X11 pixmap library (development headers)',                  True ),
    ( 'libxrandr-dev',   'X11 RandR extension library (development headers)',     True ),
    ( 'libxt-dev',   'X11 toolkit intrinsics library (development headers)',      True ),
    ( 'make',        'an utility for directing compilation',                      True ),
    ( 'manpages',    'manual pages about using a GNU/Linux system',               True ),
    ( 'manpages-dev',    'manual pages about using GNU/Linux for development',    True ),
    ( 'mplayer',     'the Ultimate Movie Player For Linux',                       True ),
    ( 'nedit',       'a powerful, customizable, Motif based text editor',         False ),
    ( 'octave',      'GNU Octave language for numerical computations',            True ),
    ( 'openssh-client',  'secure shell (SSH) client, for secure access to remote machines', True ),
    ( 'perl',        'Larry Wall''s Practical Extraction and Report Language',    True ),
    ( 'perl-doc',    'Perl documentation',                                        True ),
    ( 'perl-tk',     'the Perl module providing the Tk graphics library',         True ),
    ( 'perlconsole', 'a small program that lets you evaluate Perl code interactively', True ),
    ( 'patch',       'a diff file applier',                                       True ),
    ( 'patchutils',  'utilities to work with patches',                            True ),
    ( 'python',      'an interactive high-level object-oriented language',        True ),
    ( 'python-dev',  'header files and a static library for Python',              True ),
    ( 'python-numpy',  'Numerical Python adds a fast array facility to the Python language',    True ),
    ( 'python-pexpect',  'Python module for automating interactive applications', True ),
    ( 'python-tk',   'Tkinter - Writing Tk applications with Python',             True ),
    ( 'python-scipy',    'scientific tools for Python',                           True ),
    ( 'python-matplotlib',   'a Python based plotting system in a style similar to Matlab', True ),
    ( 'ratpoison',   'a keyboard-only window manager',                            True ),
    ( 'readline-common', 'GNU readline and history libraries',                    True ),
    ( 'rsync',       'a fast remote file copy program (like rcp)',                True ),
    ( 'ruby',        'the interpreted scripting language for quick and easy object-oriented programming', True ),
    ( 'ruby-dev',    'header files for compiling extension modules for Ruby',     True ),
    ( 'scrot',       'a command line screen capture utility',                     True ),
    ( 'sharutils',   'a set of shell archives creation tools',                    True ),
    ( 'ssh-askpass', 'ssh-add passphrase querying program',                       True ),
    ( 'strace',      'a system call tracer',                                      True ),
    ( 'subversion',  'an advanced version control system',                        True ),
    ( 'sudo',        'a limited super user privilege giver',                      True ),
    ( 'openjdk-6-jdk', 'OpenJDK Development Kit (JDK)',                           True ),
    ( 'openjdk-6-jre', 'OpenJDK Java runtime, using Hotspot JIT',                 True ),
    ( 'tar',         'the GNU version of the tar archiving utility',              True ),
    ( 'tcl',         'the Tool Command Language (default version) - run-time files', True ),
    ( 'tcl-dev',     'the Tool Command Language (default version) - development files', True ),
    ( 'tcl-doc',     'the Tool Command Language (default version) - manual pages', True ),
    ( 'tcl-tclreadline', 'GNU Readline Extension for Tcl/Tk',                     True ),
    ( 'tcsh',        'the TENEX C Shell',                                         True ),
    ( 'time',        'the GNU time program for measuring cpu resource usage',     True ),
    ( 'tk-doc',      'The Tk toolkit for Tcl and X11 (default version) - manual pages', True ),
    ( 'tkcvs',       'provides tkdiff, graphical side by side "diff" utility',    True ),
    ( 'ttf-bitstream-vera', 'The Bitstream Vera family of free TrueType fonts',   True ),
    ( 'ttf-mscorefonts-installer', 'Installer for Microsoft TrueType core fonts', True ),
    ( 'ttf-unifont', 'TrueType version of the GNU Unifont',                       True ),
    ( 'unzip',       'a de-archiver for .zip files',                              True ),
    ( 'valgrind',    'a memory debugger and profiler',                            True ),
    ( 'vim',         'Vi IMproved - enhanced vi editor',                          True ),
    ( 'wget',        'a program to retrieve files from the web',                  True ),
    ( 'xfonts-100dpi', '100 dpi fonts for X',                                     True ),
    ( 'xfonts-75dpi', '75 dpi fonts for X',                                       True ),
    ( 'xloadimage',  'Graphics file viewer under X11',                            True ),
    ( 'xnest',       'a nested X server',                                         True ),
    ( 'xpdf',        'a Portable Document Format (PDF) suite',                    True ),
    ( 'xvfb',        "Virtual Framebuffer 'fake' X server",                       True ),
    ( 'x11-xserver-utils', 'X server utilities',                                  True ),
    ( 'zip',         'an archiver for .zip files',                                True ),
]

@pytest.mark.nightly
@pytest.mark.registereduser
class container_packages_list(TestCase):


    def setUp(self):

        # get user account info
        hubname = self.testdata.find_url_for('https')
        self.username,self.userpass = \
            self.testdata.find_account_for('registeredworkspace')

        cm = ContainerManager()
        self.ws = cm.access(host=hubname,
                            username=self.username,
                            password=self.userpass)


    def test_package_list_available(self):
        """
        check if the container package list is available
        """

        command = '[[ -r /var/tmp/installed_pkgs ]] && echo 1 || echo 0'
        output,es = self.ws.execute(command)


    def tearDown(self):

        # get out of the workspace
        # shut down the ssh connection
        self.ws.close()


@pytest.mark.debian7
@pytest.mark.weekly
@pytest.mark.registereduser
class container_packages(TestCase):

    data = None

    def setUp(self):

        self.ws = None

        if self.data is None:
            # only get the package list once

            # get user account info
            hubname = self.testdata.find_url_for('https')
            self.username,self.userpass = \
                self.testdata.find_account_for('registeredworkspace')

            cm = ContainerManager()
            self.ws = cm.access(host=hubname,
                                username=self.username,
                                password=self.userpass)

            self.data = self.ws.read_file('/var/tmp/installed_pkgs')


    def _is_package_installed(self,pkgname):

        pkg_re = re.compile('ii  %s(:amd64)?\s[^\n]+\n' % re.escape(pkgname))
        match = pkg_re.search(self.data)
        return match is not None


    @hubcheck.utils.tool_container_version('debian7')
    def test_wheezy_packages(self):
        """
        the automatic configure script builder
        """

        pkgs_to_be_installed = []
        pkgs_to_be_removed = []
        unsupported = []

        for (pkg,desc,installed_state) in wheezypkginfo:
            if self._is_package_installed(pkg) is not installed_state:
                if installed_state is True:
                    pkgs_to_be_installed.append(pkg)
                elif installed_state is False:
                    pkgs_to_be_removed.append(pkg)
                else:
                    unsupported.append((pkg,installed_state))

        self.assertTrue(len(pkgs_to_be_installed) == 0 and
                        len(pkgs_to_be_removed) == 0 and
                        len(unsupported) == 0,
                        "packages to be installed: %s\npackages to be removed %s\nunsupported state: %s" \
                        % (pkgs_to_be_installed,pkgs_to_be_removed,unsupported))


    def tearDown(self):

        if self.ws is not None:
            # get out of the workspace
            # shut down the ssh connection
            self.ws.close()


