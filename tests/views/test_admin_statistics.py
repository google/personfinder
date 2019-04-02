import os
import unittest

import django
import django.test
from google.appengine.ext import testbed

import model


class AdminStatisticsViewTests(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.setup_env(
            user_email='fred@example.com', user_id='fred', is_admin='1')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        django.test.utils.setup_test_environment()
        self.client = django.test.Client()

    def tearDown(self):
        self.testbed.deactivate()
        django.test.utils.teardown_test_environment()

    def test_person_counter(self):
        counter = model.UsageCounter.create('haiti')
        setattr(counter, 'person', 3)
        counter.put()
        res = self.client.get('/global/admin/statistics').content
        raise Exception(res)
