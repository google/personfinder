from mock import patch
import unittest

from google.appengine.ext import testbed

import sitemap
import test_handler

class SitemapTests(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_user_stub()
        self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def testAddPingTasks(self):
        sitemap.SiteMapPing.add_ping_tasks()
        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(
            tasks[0].url, '/global/sitemap/ping?search_engine=bing')
        self.assertEqual(
            tasks[1].url, '/global/sitemap/ping?search_engine=google')

    def testPingIndexer(self):
        with patch('requests.get') as requests_mock:
            handler = test_handler.initialize_handler(
                sitemap.SiteMapPing, action='sitemap/ping', repo='global',
                params={'search_engine': 'google'})
            handler.get()
            assert len(requests_mock.call_args_list) == 1
            call_args, _ = requests_mock.call_args_list[0]
            assert call_args[0] == ('http://www.google.com/ping?sitemap='
                                    'https%3A//localhost/global/sitemap')
