#!/usr/bin/python2.5
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Starts up an appserver and runs end-to-end tests against it.

Instead of running this script directly, use the 'server_tests' shell script,
which sets up the PYTHONPATH and other necessary environment variables.
The actual test cases reside in server_test_cases.py.

Use -k to select particular test classes or methods by a substring match:
    tools/server_tests -k ConfigTests
    tools/server_tests -k test_delete_and_restore

Specify -v to show the name of each test as it runs (rather than just dots).
Specify -s to see the messages printed by all tests as they run (by default,
    stdout/stderr will be captured and then shown only for failing tests).
"""

import os
import pytest
import re
import signal
import smtpd
import subprocess
import sys
import threading
import time

from model import *
import remote_api
import setup_pf as setup


class ProcessRunner(threading.Thread):
    """A thread that starts a subprocess, collects its output, and stops it."""

    READY_RE = re.compile('')  # this output means the process is ready
    ERROR_RE = re.compile('ERROR|CRITICAL')  # output indicating failure
    OMIT_RE = re.compile('INFO |WARNING ')  # don't bother showing these lines
    debug = False  # set to True to see all log messages, ignoring OMIT_RE

    def __init__(self, name, args):
        threading.Thread.__init__(self)
        self.name = name
        self.args = args
        self.process = None  # subprocess.Popen instance
        self.ready = False  # process is running and ready
        self.failed = False  # process emitted an error message in its output
        self.output = []

    def run(self):
        """Starts the subprocess and collects its output while it runs."""
        self.process = subprocess.Popen(
            self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            close_fds=True)

        # Each subprocess needs a thread to be watching it and absorbing its
        # output; otherwise it will block when its stdout pipe buffer fills.
        while self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:  # process finished
                return
            if self.READY_RE.search(line):
                self.ready = True
            if not self.debug and self.OMIT_RE.search(line):  # omit these lines
                continue
            if self.ERROR_RE.search(line):  # something went wrong
                self.failed = True
            if line.strip():
                self.output.append(line.strip('\n'))

    def stop(self):
        """Terminates the subprocess and returns its status code."""
        if self.process:  # started
            if self.isAlive():  # still running
                os.kill(self.process.pid, signal.SIGKILL)
            else:
                self.failed = self.process.returncode != 0
        self.clean_up()
        if self.failed:
            self.flush_output()
            print >>sys.stderr, '%s failed (status %s).\n' % (
                self.name, self.process.returncode)
        else:
            print >>sys.stderr, '%s stopped.' % self.name

    def flush_output(self):
        """Flushes the buffered output from this subprocess to stderr."""
        self.output, lines_to_print = [], self.output
        if lines_to_print:
            sys.stderr.write('\n--- output from %s ---\n' % self.name)
            sys.stderr.write('\n'.join(lines_to_print) + '\n\n')

    def wait_until_ready(self, timeout=10):
        """Waits until the subprocess has logged that it is ready."""
        fail_time = time.time() + timeout
        while self.isAlive() and not self.ready and time.time() < fail_time:
            for jiffy in range(10):  # wait one second, aborting early if ready
                if not self.ready:
                    time.sleep(0.1)
            if not self.ready:
                self.flush_output()  # after each second, show output
        if self.ready:
            print >>sys.stderr, '%s started.' % self.name
        else:
            raise RuntimeError('%s failed to start.' % self.name)

    def clean_up(self):
        pass


class AppServerRunner(ProcessRunner):
    """Manages a dev_appserver subprocess."""

    READY_RE = re.compile('Running application')
    OMIT_RE = re.compile(
        'INFO |WARNING |DeprecationWarning: get_request_cpu_usage')

    def __init__(self, port, smtp_port):
        ProcessRunner.__init__(self, 'appserver', [
            os.environ['PYTHON'],
            os.path.join(os.environ['APPENGINE_DIR'], 'dev_appserver.py'),
            os.environ['APP_DIR'],
            '--port=%s' % port,
            '--datastore_path=/dev/null',
            '--require_indexes',
            '--smtp_host=localhost',
            '--smtp_port=%d' % smtp_port # '-d'
        ])


class MailThread(threading.Thread):
    """Runs an SMTP server and stores the incoming messages."""
    messages = []

    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port
        self.stop_requested = False

    def run(self):
        class MailServer(smtpd.SMTPServer):
            def process_message(self, peer, mailfrom, rcpttos, data):
                print >>sys.stderr, 'mail from:', mailfrom, 'to:', rcpttos
                MailThread.messages.append(
                    {'from': mailfrom, 'to': rcpttos, 'data': data})

        try:
            server = MailServer(('localhost', self.port), None)
        except Exception, e:
            print >>sys.stderr, 'SMTP server failed: %s' % e
            sys.exit(-1)
        print >>sys.stderr, 'SMTP server started.'
        while not self.stop_requested:
            smtpd.asyncore.loop(timeout=0.5, count=1)
        print >>sys.stderr, 'SMTP server stopped.'

    def stop(self):
        self.stop_requested = True

    def wait_until_ready(self, timeout=10):
        pass

    def flush_output(self):
        pass


class PyTestPlugin:
    """A plugin for pytest that does the setup and teardown for server tests."""

    def __init__(self):
        self.threads = []

    def pytest_addoption(self, parser):
        group = parser.getgroup(
            'server_tests', 'App Engine server testing', after='general')
        group.addoption('--server',
                        help='appserver URL (default: localhost:8081)')
        group.addoption('--port', type='int', default=8081,
                        help='appserver port number (default: 8081)')
        group.addoption('--mailport', type='int', default=8025,
                        help='SMTP server port number (default: 8025)')

    def pytest_configure(self, config):
        options = config.option
        url = options.server or 'localhost:%d' % options.port
        secure, host, port, path = remote_api.parse_url(url)
        if host == 'localhost':
            # We need to start up a clean new appserver for testing.
            self.threads.append(AppServerRunner(options.port, options.mailport))
        self.threads.append(MailThread(options.mailport))
        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            thread.wait_until_ready()

        # Connect to the datastore.
        url, app_id = remote_api.connect(url, 'test', 'test')

        # Reset the datastore for the first test.
        reset_data()

        # Give the tests access to configuration information.
        config.hostport = '%s:%d' % (host, port)
        config.mail_server = MailThread

    def pytest_unconfigure(self, config):
        for thread in self.threads:
            if hasattr(thread, 'flush_output'):
                thread.flush_output()
        for thread in self.threads:
            thread.stop()
            thread.join()

    def pytest_runtest_setup(self):
        MailThread.messages = []


def reset_data():
    """Reset the datastore to a known state, populated with test data."""
    setup.reset_datastore()
    db.put([
        Authorization.create(
            'haiti', 'test_key', domain_write_permission='test.google.com'),
        Authorization.create(
            'haiti', 'domain_test_key',
            domain_write_permission='mytestdomain.com'),
        Authorization.create(
            'haiti', 'reviewed_test_key',
            domain_write_permission='test.google.com',
            mark_notes_reviewed=True),
        Authorization.create(
            'haiti', 'not_allow_believed_dead_test_key',
            domain_write_permission='test.google.com',
            believed_dead_permission=False),
        Authorization.create(
            'haiti', 'allow_believed_dead_test_key',
            domain_write_permission='test.google.com',
            believed_dead_permission=True),
        Authorization.create(
            '*', 'global_test_key',
            domain_write_permission='globaltestdomain.com'),
        Authorization.create(
            'haiti', 'other_key', domain_write_permission='other.google.com'),
        Authorization.create(
            'haiti', 'read_key', read_permission=True),
        Authorization.create(
            'haiti', 'full_read_key', full_read_permission=True),
        Authorization.create(
            'haiti', 'search_key', search_permission=True),
        Authorization.create(
            'haiti', 'subscribe_key', subscribe_permission=True),
    ])

def monkeypatch_pytest_terminal_reporter():
    """Improves the output produced by _pytest.terminal.TerminalReporter."""
    import _pytest.terminal
    def write_sep(self, sep, title=None, **markup):
        if sep == '_':
            markup['cyan'] = 1  # highlight the failed test name in cyan
            self._tw.line()  # put a blank line before the failure report
        self._tw.sep(sep, title, **markup)
    _pytest.terminal.TerminalReporter.write_sep = write_sep


if __name__ == '__main__':
    monkeypatch_pytest_terminal_reporter()
    # Run the tests, using sys.exit to set exit status (nonzero for failure).
    sys.exit(pytest.main(plugins=[PyTestPlugin()]))
