"""Tools to help run tests against the Django app."""

import os
import unittest

import django
import django.test
from google.appengine.ext import testbed


class TaskTestsBase(unittest.TestCase):
    """A base class for tests for tasks."""

    # This HTTP header should be set to make the request appear to come from App
    # Engine (other task requests are rejected).
    _REQ_HEADERS = {'HTTP_X_APPENGINE_TASKNAME': 'notempty'}

    def init_testbed_stubs(self):
        """Initializes the App Engine testbed stubs.

        Subclasses can override this, but should include the user stub even if
        they don't need it directly (it seems to be required).
        """
        self.testbed.init_user_stub()

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.init_testbed_stubs()
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        django.test.utils.setup_test_environment()
        self.client = django.test.Client()

    def tearDown(self):
        self.testbed.deactivate()
        django.test.utils.teardown_test_environment()

    def run_task(self, path, data={}, method='GET'):
        """Makes a request to a task handler."""
        if method == 'GET':
            return self.client.get(path, data, **TaskTestsBase._REQ_HEADERS)
        else:
            return self.client.post(path, data, **TaskTestsBase._REQ_HEADERS)
