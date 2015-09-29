import unittest
import sys
import os
import pytest
import re
from string import Template

import hubcheck
from hubcheck.testcase import TestCase2
from hubcheck.shell import ContainerManager


pytestmark = [ pytest.mark.container,
               pytest.mark.rappture,
               pytest.mark.weekly,
               pytest.mark.reboot
             ]


SUB_SPACING = 12

TOOL_XML = """
<?xml version="1.0"?>
<run>
    <tool>
        <about>Press Simulate to view results.</about>
        <command>@tool/fermi @driver</command>
    </tool>
    <input>
        <number id="Ef">
            <about>
                <label>Fermi Level</label>
                <description>Energy at center of distribution.</description>
            </about>
            <units>eV</units>
            <min>-10eV</min>
            <max>10eV</max>
            <default>0.2556eV</default>
        </number>
    </input>
</run>
""".strip()

@pytest.mark.rappture_c
@pytest.mark.registereduser
@pytest.mark.usefixtures('rappture_version')
class TestContainerRapptureCApi(TestCase2):


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

        self.ws.execute('cd $SESSIONDIR')
        self.sessiondir,es = self.ws.execute('pwd')


    def teardown_method(self,method):

        # remove the executable and config files
        for fname in self.remove_files:
            self.ws.execute('rm -f %s' % (fname))

        # exit the workspace
        self.ws.close()


    def write_xml_file(self):

        # write xml file
        xmlfn = os.path.join(self.sessiondir,"tool.xml")
        self.ws.importfile(TOOL_XML,xmlfn,mode=0600,is_data=True)
        self.remove_files.append(xmlfn)


    def run_code(self,program,xmlfn='tool.xml'):

        # write program
        programfn = os.path.join(self.sessiondir,"program.c")
        self.ws.importfile(program,programfn,mode=0600,is_data=True)
        self.remove_files.append(programfn)

        # generate path for compiled executable
        compiledfn = os.path.join(self.sessiondir,'program')
        self.remove_files.append(compiledfn)

        # setup rappture environment
        self.ws.execute('. /etc/environ.sh')
        self.ws.execute('use -e -r %s' % (self.rappture_version))

        # setup RAPPTURE_INCLUDE and RAPPTURE_LIB
        rpflags  = '-I$RAPPTURE_PATH/include'
        rpflags += ' -L$RAPPTURE_PATH/lib -lrappture -lexpat -lz -lm'

        # compile the code
        command = 'gcc -o %s %s %s' % (compiledfn,rpflags,programfn)
        self.ws.execute(command)
        self.ws.execute('chmod 700 %s' % (compiledfn))

        # run the code
        command = '%s %s' % (compiledfn,xmlfn)
        output,es = self.ws.execute(command,fail_on_exit_code=False)

        return output,es


    @pytest.mark.dsktest
    def test_rpLibrary_valid_path(self):
        """
        rpLibrary()
        test the function using an xml file that exists on disk
        """

        program = """
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 1;

                lib = rpLibrary(argv[1]);

                if (lib != NULL) {
                    err = 0;
                }

                return err;
            }
        """

        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            "rpLibrary failed to open xml file, es = %s" % (es)


    @pytest.mark.skipif(True,reason="the rappture c api currently does not error on invalid path")
    def test_rpLibrary_invalid_path(self):
        """
        rpLibrary()
        test the function using an xml file that does not exist on disk
        """

        program = """
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                }

                return err;
            }
        """


        xmlfn = "tool_does_not_exist.xml"

        output,es = self.run_code(program,xmlfn)

        # check for success
        assert es == 1, \
            "rpLibrary successfully opened a file that does not exist: %s" \
            % (xmlfn)


    @pytest.mark.skipif(True,reason="the rappture c api currently does not error on blank path")
    def test_rpLibrary_no_path(self):
        """
        rpLibrary()
        test the function without giving a filename
        """

        program = """
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;

                lib = rpLibrary("");

                if (lib == NULL) {
                    err = 1;
                }

                return err;
            }
        """

        output,es = self.run_code(program)

        # check for success
        assert es == 1, \
            "rpLibrary initialized an object with blank filename"


    def test_rpLibrary_null_path(self):
        """
        rpLibrary()
        test the function giving a NULL pointer
        """

        program = """
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;

                lib = rpLibrary(NULL);

                if (lib == NULL) {
                    err = 1;
                }

                return err;
            }
        """


        xmlfn = "tool_does_not_exist.xml"

        output,es = self.run_code(program,xmlfn)

        # check for success
        assert es == 0, \
            "rpLibrary failed to initialize an object with NULL filename"


    def test_rpGetString_valid_path(self):
        """
        rpGetString()
        test the function with a valid xml path
        """

        path = "input.number(Ef).about.label"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                const char* val = NULL;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpGetString(lib,"$path",&val);

                printf("%s",val);

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpGetString with xml path %s' % (path)

        expected = 'Fermi Level'
        assert output == expected, \
            "rpGetString returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    @pytest.mark.skipif(True,reason="the rappture c api currently only returns 0 as an error code")
    def test_rpGetString_invalid_path(self):
        """
        rpGetString()

        test that calling the function with an invalid xml path returns a
        non zero error code.
        """

        path = "input.number(Ef).bad.path"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                const char* val = NULL;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpGetString(lib,"$path",&val);

                if (err == 0) {
                    printf("%s",val);
                }

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 1, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpGetString with bad xml path %s' % (path)

        expected = ''
        assert output == expected, \
            "rpGetString returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    def test_rpGetString_null_retcstr(self):
        """
        rpGetString()

        test that calling the function with a NULL retCStr
        non zero error code.
        """

        path = "input.number(Ef).about.label"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpGetString(lib,"$path",NULL);

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for segfault
        assert es == 139, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpGetString with retCStr == NULL'


    def test_rpGetDouble_valid_path(self):
        """
        rpGetDouble()
        test the function with a valid xml path
        """

        path = "input.number(Ef).default"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                double val = 0.0;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpGetDouble(lib,"$path",&val);

                printf("%g",val);

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpGetDouble with xml path %s' % (path)

        expected = '0.2556'
        assert output == expected, \
            "rpGetDouble returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    @pytest.mark.skipif(True,reason="the rappture c api currently only returns 0 as an error code")
    def test_rpGetDouble_invalid_path(self):
        """
        rpGetDouble()

        test that calling the function with an invalid xml path returns a
        non zero error code.
        """

        path = "input.number(Ef).bad.path"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                double val = 0.0;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpGetDouble(lib,"$path",&val);

                if (err == 0) {
                    printf("%g",val);
                }

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es != 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpGetDouble with bad xml path %s' % (path)

        expected = '0.2556'
        assert output == '', \
            "rpGetDouble returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    def test_rpGetDouble_null_retdval(self):
        """
        rpGetDouble()

        test that calling the function with a NULL retDVal
        returns a non zero error code.
        """

        path = "input.number(Ef).default"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpGetDouble(lib,"$path",NULL);

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for segfault
        assert es == 139, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpGetDouble with retDVal == NULL'


    def test_rpPutString_valid_path_valid_value(self):
        """
        rpPutString()
        test the function with a valid xml path and valid value
        """

        path = "output.string.current"
        val = "my new data"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                int append = 0;
                const char *path = "$path";
                const char *value = "$val";
                const char *rvalue = NULL;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpPutString(lib,path,value,append);

                rpGetString(lib,path,&rvalue);
                printf("%s",rvalue);

                return err;
            }
        """).substitute(path=path,val=val)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpPutString with xml path %s and string %s' % (path,val)

        expected = val
        assert output == expected, \
            "rpPutString returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    @pytest.mark.skipif(True,reason="the rappture c api currently only returns 0 as an error code")
    def test_rpPutString_invalid_path_valid_value(self):
        """
        rpPutString()
        test the function with an invalid xml path and valid value
        """

        path = "output..string.current"
        val = "my new data"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                int append = 0;
                const char *path = "$path";
                const char *value = "$val";
                const char *rvalue = NULL;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpPutString(lib,path,value,append);

                rpGetString(lib,path,&rvalue);
                printf("%s",rvalue);

                return err;
            }
        """).substitute(path=path,val=val)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es != 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpPutString with xml path %s and string %s' % (path,val)


    def test_rpPutString_valid_path_invalid_value(self):
        """
        rpPutString()
        test the function with a valid xml path and invalid value
        """

        path = "output.string.current"

        program = Template("""
            #include <stdio.h>
            #include "rappture.h"

            int main(int argc, char* argv[]) {

                RpLibrary* lib = NULL;
                int err = 0;
                int append = 0;
                const char *path = "$path";
                const char *value = NULL;
                const char *rvalue = NULL;

                lib = rpLibrary(argv[1]);

                if (lib == NULL) {
                    err = 1;
                    return err;
                }

                err = rpPutString(lib,path,value,append);

                rpGetString(lib,path,&rvalue);
                printf("%s",rvalue);

                return err;
            }
        """).substitute(path=path)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es != 139, \
            'program exited with status %s while trying to call' % (es) \
            + ' rpPutString with xml path %s and NULL string' % (path)


@pytest.mark.rappture_python
@pytest.mark.registereduser
@pytest.mark.usefixtures('rappture_version')
class TestContainerRappturePythonApi(TestCase2):


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

        self.ws.execute('cd $SESSIONDIR')
        self.sessiondir,es = self.ws.execute('pwd')


    def teardown_method(self,method):

        # remove the executable and config files
        for fname in self.remove_files:
            self.ws.execute('rm -f %s' % (fname))

        # exit the workspace
        self.ws.close()


    def write_xml_file(self):

        # write xml file
        xmlfn = os.path.join(self.sessiondir,"tool.xml")
        self.ws.importfile(TOOL_XML,xmlfn,mode=0600,is_data=True)
        self.remove_files.append(xmlfn)


    def run_code(self,program,xmlfn='tool.xml'):

        # write program
        programfn = os.path.join(self.sessiondir,"program.py")
        self.ws.importfile(program,programfn,mode=0600,is_data=True)
        self.remove_files.append(programfn)

        # setup rappture environment
        self.ws.execute('. /etc/environ.sh')
        self.ws.execute('use -e -r %s' % (self.rappture_version))

        # run the code
        command = 'python %s %s' % (programfn,xmlfn)
        output,es = self.ws.execute(command,fail_on_exit_code=False)

        return output,es


    def test_library_valid_path(self):
        """
        Rappture.library()
        test the function using an xml file that exists on disk
        """

        program = """
            import sys
            import Rappture

            lib = Rappture.library(sys.argv[1])

            if lib is None:
                raise Exception("failed to open xml file: %s" % (sys.argv[1]))

            sys.exit()
        """

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            "Rappture.library failed to open xml file: %s" % (output)


    @pytest.mark.skipif(True,reason="the rappture python api currently does not error on invalid path")
    def test_library_invalid_path(self):
        """
        Rappture.library()
        test the function using an xml file that does not exist on disk
        """

        program = """
            import sys
            import Rappture

            lib = Rappture.library(sys.argv[1])

            sys.exit()
        """

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)

        xmlfn = "tool_does_not_exist.xml"

        output,es = self.run_code(program,xmlfn)

        # check for success
        assert es == 1, \
            "Rappture.library successfully opened a file that does not exist: %s" \
            % (xmlfn)


    @pytest.mark.skipif(True,reason="the rappture python api currently does not error on blank path")
    def test_library_no_path(self):
        """
        Rappture.library()
        test the function without giving a filename
        """

        program = """
            import sys
            import Rappture

            lib = Rappture.library('')

            sys.exit()
        """

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)


        output,es = self.run_code(program)

        # check for success
        assert es == 1, \
            "Rappture.library initialized an object with blank filename"


    def test_library_none_path(self):
        """
        Rappture.library()
        test the function giving a None object
        """

        program = """
            import sys
            import Rappture

            lib = Rappture.library(None)

            sys.exit()
        """

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)


        output,es = self.run_code(program)

        # check for success
        assert es == 1, \
            "Rappture.library initialized an object with 'None' filename"


    def test_get_valid_path(self):
        """
        get()
        test the function with a valid xml path
        """

        path = "input.number(Ef).about.label"

        program = Template("""
            import sys
            import Rappture

            val = None

            lib = Rappture.library(sys.argv[1])

            if lib is None:
                raise Exception("failed to open xml file: %s" % (sys.argv[1]))

            val = lib.get('$path')

            print "%s" % (val)

            sys.exit()
        """).substitute(path=path)

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' get() with xml path %s' % (path)

        expected = 'Fermi Level'
        assert output == expected, \
            "get() returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    @pytest.mark.skipif(True,reason="the rappture python api currently does not error on bad path")
    def test_get_invalid_path(self):
        """
        get()

        test that calling the function with an invalid xml path returns a
        non zero error code.
        """

        path = "input.number(Ef).bad.path"

        program = Template("""
            import sys
            import Rappture

            val = None

            lib = Rappture.library(sys.argv[1])

            if lib is None:
                raise Exception("failed to open xml file: %s" % (sys.argv[1]))

            val = lib.get('$path')

            print "%s" % (val)

            sys.exit()
        """).substitute(path=path)

        program = re.sub('\n {%d})' % (SUB_SPACING),'\n',program,flags=re.M)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 1, \
            'program exited with status %s while trying to call' % (es) \
            + ' get() with bad xml path %s' % (path)

        expected = ''
        assert output == expected, \
            "get() returned the wrong data, expected: %s, received: %s" \
            % (expected,output)


    def test_get_none_path(self):
        """
        get()

        test that calling the function with a None path returns a TypeError
        """


        program = """
            import sys
            import Rappture

            val = None

            lib = Rappture.library(sys.argv[1])

            if lib is None:
                raise Exception("failed to open xml file: %s" % (sys.argv[1]))

            val = lib.get(None)

            sys.exit()
        """

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for error code
        assert es == 1, \
            'program exited with status %s while trying to call' % (es) \
            + ' get() with path == None'

        # check for TypeError in output
        assert re.search("TypeError",output) is not None, \
            'program did not exit with a TypeError: %s' % (output)


    def test_put_valid_path_valid_value(self):
        """
        put()

        test the function with a valid xml path and valid value
        """

        path = "output.string.current"
        value = "my new data"

        program = Template("""
            import sys
            import Rappture

            path = '$path'
            value = '$value'

            lib = Rappture.library(sys.argv[1])

            if lib is None:
                raise Exception("failed to open xml file: %s" % (sys.argv[1]))

            lib.put(path,value)

            rval = lib.get(path)

            if value != rval:
                raise Exception("value stored differs from value returned."
                                + "\\nstored: %s" % (value)
                                + "\\nreturned: %s" % (rval))

            sys.exit()
        """).substitute(path=path,value=value)

        program = re.sub('\n {%d}' % (SUB_SPACING),'\n',program,flags=re.M)


        self.write_xml_file()
        output,es = self.run_code(program)

        # check for success
        assert es == 0, \
            'program exited with status %s while trying to call' % (es) \
            + ' put() with xml path %s and string %s: %s' % (path,value,output)


