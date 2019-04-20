import os
import unittest

import django
import django.test
from google.appengine.ext import testbed

from testutils import data_generator


class ServerTestsBase(unittest.TestCase):

    def init_testbed_stubs(self):
        """Initializes the App Engine testbed stubs.

        Subclasses can override this, but should include the user stub even if
        they don't need it directly (it seems to be required).
        """
        self.testbed.init_user_stub()

    def setUp(self):
        self.data_generator = data_generator.TestDataGenerator()
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
