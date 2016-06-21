# pylint: disable=invalid-name
# pylint: disable=missing-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals

import json
import os
import re
import subprocess
import sys
import warnings
import yaml

TESTCASES = list()
INVENTORY = 'test/fixtures/hosts'

HERE = os.path.abspath(os.path.dirname(__file__))
ROLE = re.match(
    r'^.*\/ansible-eos-([^/\s]+)\/test/arista-ansible-role-test$', HERE).group(1)
RUN_CONFIG_BACKUP = '_eos_role_test_{}_running'.format(ROLE)
START_CONFIG_BACKUP = '_eos_role_test_{}_startup'.format(ROLE)

EOS_ROLE_PLAYBOOK = 'test/arista-ansible-role-test/eos_role.yml'
EOS_MODULE_PLAYBOOK = 'test/arista-ansible-role-test/eos_module.yml'

LOG_FILE = '{}/roletest.log'.format(HERE)
try:
    os.remove(LOG_FILE)
except OSError:
    pass
LOG = open(LOG_FILE, 'w')

SEPARATOR = '    ' + '*' * 50

class TestCase(object):
    def __init__(self, **kwargs):
        self.name = kwargs['name']
        self.module = kwargs['module']

        self.host = None

        self.inventory = kwargs.get('inventory')
        self.exitcode = kwargs.get('exitcode', 0)
        self.idempotent = kwargs.get('idempotent', True)
        self.changed = kwargs.get('changed', True)
        self.present = kwargs.get('present')
        self.absent = kwargs.get('absent')

        self.arguments = kwargs.get('arguments', list())
        self.variables = dict()

        # optional properties
        self.setup = kwargs.get('setup', list())
        self.teardown = kwargs.get('teardown', list())

    def __str__(self):
        return self.name


class TestModule(object):
    def __init__(self, testcase):
        self.testcase = testcase
        self.description = 'Test [%s]: %s' % (testcase.module, testcase.name)

    def __call__(self):
        self.output('Run first pass')
        response = self.run_module()
        for device in response:
            hostname = device.keys()[0]
            reported = int(device[hostname]['changed'])
            expected = int(self.testcase.changed)
            msg = ("First pass role execution reported {} task change(s), "
                   "expected {}".format(reported, expected))
            self.output(msg)
            assert reported == expected, msg

        if self.testcase.idempotent:
            self.output('Run second pass')
            response = self.run_module()
            for device in response:
                hostname = device.keys()[0]
                reported = int(device[hostname]['changed'])
                msg = (
                    "Second pass role execution reported {} task change(s), "
                    "expected 0".format(reported))
                self.output(msg)
                assert not reported, msg

        if self.testcase.present:
            desc = 'Validate present configuration'
            self.output(desc)
            response = self.run_validation(self.testcase.present, desc=desc)
            for device in response:
                hostname = device.keys()[0]
                # Result should contain an empty list of updates
                delim = " ---\n"
                updates = device[hostname]['updates']
                msg = ("{} - Expected configuration\n{}{}\n{}not found "
                       "on device '{}'".format(desc, delim,
                                               '\n'.join(updates), delim,
                                               hostname))
                assert device[hostname]['updates'] == [], msg
                # Result should show no changes
                msg = ("{} - Device '{}' reported no updates, but "
                       "returned 'changed'".format(desc, hostname))
                assert device[hostname]['changed'] == False, msg

        if self.testcase.absent:
            desc = 'Validate absent configuration'
            self.output(desc)
            response = self.run_validation(self.testcase.absent, desc=desc)
            for device in response:
                hostname = device.keys()[0]
                # Result should show change has taken place
                msg = (
                    "{} - Entire absent configuration found on device '{}'".
                    format(desc, hostname)
                )
                assert device[hostname]['changed'] == True, msg
                # Compare changes with expected values, sorted at global level
                updates = '\n'.join(device[hostname]['updates'])
                updates = re.split(r'\n(?=\S)', updates)
                updates = '\n'.join(sorted(updates))
                absent = re.split(r'\n(?=\S)', self.testcase.absent.rstrip())
                absent = '\n'.join(sorted(absent))
                msg = ("{} - Some part of absent configuration found "
                       "on device '{}'".format(desc, hostname))
                assert updates == absent, msg

    def setUp(self):
        print("\n{}\n".format(SEPARATOR) +
              "  See run log for complete output:\n  {}".format(LOG_FILE) +
              "\n{}\n".format(SEPARATOR))

        LOG.write("\n\n\n{}\n".format(SEPARATOR) +
                  "  Begin log for {}".format(self.description) +
                  "\n{}\n\n".format(SEPARATOR))

        if self.testcase.setup:
            self.output('Running test case setup commands')
            setup_cmds = self.testcase.setup
            if not isinstance(setup_cmds, list):
                setup_cmds = setup_cmds.splitlines()
            self.output("{}".format(setup_cmds))

            args = {
                'module': 'eos_command',
                'description': 'Run test case setup commands',
                'cmds': ['configure terminal'] + setup_cmds,
            }

            arguments = [json.dumps(args)]

            ret_code, out, err = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                                  arguments=arguments)

            if ret_code != 0:
                LOG.write("Playbook stdout:\n\n{}".format(out))
                LOG.write("Playbook stderr:\n\n{}".format(err))
                raise

    def tearDown(self):
        if self.testcase.teardown:
            self.output('Running test case teardown commands')
            teardown_cmds = self.testcase.teardown
            if not isinstance(teardown_cmds, list):
                teardown_cmds = teardown_cmds.splitlines()
            self.output("{}\n".format(teardown_cmds))

            args = {
                'module': 'eos_command',
                'description': 'Run test case teardown_cmds commands',
                'cmds': ['configure terminal'] + teardown_cmds,
            }

            arguments = [json.dumps(args)]

            ret_code, out, err = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                                  arguments=arguments)

            if ret_code != 0:
                self.output("Playbook stdout:\n\n{}".format(out))
                self.output("Playbook stderr:\n\n{}".format(err))
                warnings.warn("\nError in test case teardown\n\n{}".format(
                    out))

    @classmethod
    def output(cls, text):
        print '>>', str(text)
        LOG.write('++ {}'.format(text) + '\n')

    def run_module(self):
        (retcode, out, _) = self.execute_module()
        out_stripped = re.sub(r'\"config\": \"! Command:.*\\nend\"',
                              '\"config\": \"--- stripped for space ---\"',
                              out)
        LOG.write("PLaybook stdout:\n\n{}".format(out_stripped))
        msg = "Return code: {}, Expected code: {}".format(retcode, self.testcase.exitcode)
        self.output(msg)
        assert retcode == self.testcase.exitcode, msg
        return self.parse_response(out)

    def execute_module(self):
        arguments = [json.dumps(self.testcase.arguments)]
        arguments.append(json.dumps(
            {'rolename': "ansible-eos-{}".format(ROLE)}))
        return ansible_playbook(EOS_ROLE_PLAYBOOK, arguments=arguments)

    def parse_response(self, output, validate=False):
        # Get all the lines after the 'PLAY RECAP ****...' header
        lines = re.sub(r'^.*PLAY RECAP \*+', '', output, 0, re.S).split('\n')
        # Remove any empty lines from the list
        lines = [x for x in lines if x]

        recap = []
        for line in lines:
            match = re.search(r'^(\S+)\s+\:\s+' \
                              r'ok=(\d+)\s+' \
                              r'changed=(\d+)\s+' \
                              r'unreachable=(\d+)\s+' \
                              r'failed=(\d+)', line)
            if not match:
                self.output("Playbook stdout:\n\n{}".format(output))
                raise ValueError("Unable to parse Ansible output for "
                                 "recap information")
            (name, okcount, changed, unreach, failed) = match.groups()
            recap.append({name: {'ok': okcount,
                                 'changed': changed,
                                 'unreachable': unreach,
                                 'failed': failed}})

        if not validate:
            return recap

        updates = []
        for device in recap:
            hostname = device.keys()[0]
            match = re.search(r'(?<!skipping: )\[%s\] => (\{.*\})' % hostname,
                              output, re.M)
            if not match:
                self.output("Playbook stdout:\n\n{}".format(output))
                raise ValueError("Unable to parse Ansible output for "
                                 "result validation")
            result = json.loads(match.group(1))
            updates.append({hostname: result})

        return updates

    def run_validation(self, src, desc='Validate configuration'):
        args = {'module': 'eos_template', 'description': desc, 'src': src, }
        arguments = [json.dumps(args)]
        (ret_code, out, _) = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                              arguments=arguments,
                                              options=['--check'])
        LOG.write(out)
        assert ret_code == 0, "Validation playbook failed execution"
        return self.parse_response(out, validate=True)


def filter_modules(modules, filenames):
    if modules:
        modules = ['{0}.yml'.format(s) for s in modules.split(',')]
        return list(set(modules).intersection(filenames))
    return filenames


def setup():
    print >> sys.stderr, "Test Suite Setup:"

    run_backup = "  Backing up running-config on nodes ..."
    print >> sys.stderr, run_backup
    LOG.write('++ ' + run_backup.strip())
    args = {
        'module': 'eos_command',
        'description': 'Back up running-config on node',
        'cmds': [
            'configure terminal',
            'copy running-config {}'.format(RUN_CONFIG_BACKUP)
        ],
    }
    arguments = [json.dumps(args)]

    ret_code, out, err = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                          arguments=arguments)

    if ret_code != 0:
        LOG.write(">> ansible-playbook {} stdout:\n{}".format(EOS_MODULE_PLAYBOOK, out))
        LOG.write(">> ansible-playbook {} stddrr:\n{}".format(EOS_MODULE_PLAYBOOK, err))
        teardown()
        raise RuntimeError("Error in Test Suite Setup")

    run_backup = "  Backing up startup-config on nodes ..."
    print >> sys.stderr, run_backup
    LOG.write('++ ' + run_backup.strip())
    args = {
        'module': 'eos_command',
        'description': 'Back up startup-config on node',
        'cmds': [
            'configure terminal',
            'copy startup-config {}'.format(START_CONFIG_BACKUP)
        ],
    }
    arguments = [json.dumps(args)]

    ret_code, out, err = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                          arguments=arguments)

    if ret_code != 0:
        LOG.write(">> ansible-playbook {} stdout:\n{}".format(EOS_MODULE_PLAYBOOK, out))
        LOG.write(">> ansible-playbook {} stddrr:\n{}".format(EOS_MODULE_PLAYBOOK, err))
        teardown()
        raise RuntimeError("Error in Test Suite Setup")

    print >> sys.stderr, "  Gathering test cases ..."

    modules = os.environ.get('ANSIBLE_ROLE_TEST_CASES')

    testcases_home = os.path.join(HERE, 'testcases')
    if not os.path.exists(testcases_home):
        print >> sys.stderr, "\n  ***** Testcase directory not found!! *****"
        teardown()
        raise RuntimeError("Testcase path '{}' does not exist".format(testcases_home))

    filenames = os.listdir(testcases_home)

    for module in filter_modules(modules, filenames):
        path = os.path.join(testcases_home, module)
        definition = yaml.load(open(path))

        defaults = definition.get('defaults', {})
        testcases = definition.get('testcases', [])
        if not testcases:
            print >> sys.stderr, ("\n  ***** No testcases defined in "
                                  "module {} *****\n".format(module))
        else:
            for testcase in definition.get('testcases', []):
                kwargs = defaults.copy()
                kwargs.update(testcase)
                TESTCASES.append(TestCase(**kwargs))

    print >> sys.stderr, "  Setup complete\n"


def teardown():
    print >> sys.stderr, "\nTest Suite Teardown:"

    no_teardown = os.environ.get('NO_ANSIBLE_ROLE_TEST_TEARDOWN')

    if no_teardown:
        print >> sys.stderr, ("{}\n"
                              "  Skipping test suite teardown due to "
                              "NO_ANSIBLE_ROLE_TEST_TEARDOWN\n"
                              "  To restore each device to pre-test state "
                              "execute the following commands\n"
                              "  - configure terminal\n"
                              "  - configure replace {}\n"
                              "  - delete {}\n"
                              "  - copy {} startup-config\n"
                              "  - delete {}\n"
                              "{}".format(SEPARATOR, RUN_CONFIG_BACKUP,
                                          RUN_CONFIG_BACKUP,
                                          START_CONFIG_BACKUP,
                                          START_CONFIG_BACKUP, SEPARATOR))
    else:
        # Restore the running-config on the nodes
        # ---------------------------------------
        restore_backup = "  Restoring running-config on nodes ..."
        print >> sys.stderr, restore_backup
        LOG.write('++ ' + restore_backup.strip())
        args = {
            'module': 'eos_command',
            'description': 'Restore running-config from backup',
            'cmds': [
                'configure terminal',
                'configure replace {}'.format(RUN_CONFIG_BACKUP),
                'delete {}'.format(RUN_CONFIG_BACKUP),
            ],
        }
        arguments = [json.dumps(args)]

        # ret_code, out, err = ansible_playbook(CMD_PLAY, arguments=arguments)
        ret_code, out, err = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                              arguments=arguments)

        if ret_code != 0:
            msg = "Error restoring running-config on nodes\n" \
                  "Running ansible-playbook {} -e {}\n" \
                  ">> stdout: {}\n" \
                  ">> stderr: {}\n".format(EOS_MODULE_PLAYBOOK, arguments, out, err)
            warnings.warn(msg)

        # Restore the startup-config on the nodes
        # ---------------------------------------
        restore_backup = "  Restoring startup-config on nodes ..."
        print >> sys.stderr, restore_backup
        LOG.write('++ ' + restore_backup.strip())
        args = {
            'module': 'eos_command',
            'description': 'Restore startup-config from backup',
            'cmds': [
                'configure terminal',
                'copy {} startup-config'.format(START_CONFIG_BACKUP),
                'delete {}'.format(START_CONFIG_BACKUP),
            ],
        }
        arguments = [json.dumps(args)]

        # ret_code, out, err = ansible_playbook(CMD_PLAY, arguments=arguments)
        ret_code, out, err = ansible_playbook(EOS_MODULE_PLAYBOOK,
                                              arguments=arguments)

        if ret_code != 0:
            msg = "Error restoring startup-config on nodes\n" \
                  "Running ansible-playbook {} -e {}\n" \
                  ">> stdout: {}\n" \
                  ">> stderr: {}\n".format(EOS_MODULE_PLAYBOOK, arguments, out, err)
            warnings.warn(msg)


    print >> sys.stderr, "  Teardown complete"


def test_module():
    for testcase in TESTCASES:
        yield TestModule(testcase)


def ansible_playbook(playbook, arguments=None, options=None):
    if arguments is None:
        arguments = []
    if options is None:
        options = []

    command = ['ansible-playbook']

    command.append(playbook)
    command.extend(['-i', INVENTORY])
    for arg in arguments:
        command.extend(['-e', arg])
    for opt in options:
        command.append(opt)
    command.append('-vvv')

    # Format the command string for output on error - for easier
    # copy/paste for manual run
    cmdstr = ''
    for segment in command:
        if segment[0] == '{':
            cmdstr = cmdstr + "\'{}\' ".format(segment)
        else:
            cmdstr = cmdstr + "{} ".format(segment)
    LOG.write("-- Ansible playbook command:\n-- {}\n".format(cmdstr))

    stdout = subprocess.PIPE
    stderr = subprocess.PIPE
    proc = subprocess.Popen(command, stdout=stdout, stderr=stderr)
    out, err = proc.communicate()

    return (proc.returncode, out, err)
