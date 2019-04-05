"""Tools to help run tests against the Django app."""

import os
import unittest

import django
import django.test
from google.appengine.ext import testbed

import const

import scrape


class ViewTestsBase(unittest.TestCase):
    """A base class for tests for the Django app."""

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
        django.setup()
        django.test.utils.setup_test_environment()
        self.client = django.test.Client()

    def tearDown(self):
        self.testbed.deactivate()
        django.test.utils.teardown_test_environment()

    def login(self, is_admin=False):
        """Logs in the "user" for making requests.

        Args:
           is_admin (bool): Whether the user should be considered an admin.
        """
        self.testbed.setup_env(
            user_email='kay@mib.gov',
            user_id='k',
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def to_doc(self, response):
        """Produces a scrape.Document from the Django test response.

        Args:
            response (Response): A response from a Django test client.

        Returns:
            scrape.Document: A wrapper around the response's contents to help
                with examining it.
        """
        # TODO(nworden): when everything's on Django, make some changes to
        # scrape.py so it better fits Django's test framework.
        return scrape.Document(
            content_bytes=response.content,
            # The Django test Response objects don't include the URL, but that's
            # ok: the Document's url field is only used by scrape.Session, which
            # we're not using with the Django tests.
            url=None,
            status=response.status_code,
            # We aren't using this, at least not in the Django tests.
            message=None,
            # The response headers are accessed directly through the Response
            # object.
            headers=response,
            charset=const.CHARSET_UTF8)
