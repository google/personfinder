"""Tools to help run tests against the Django app."""

import const
import utils

import scrape
import testutils.base


class ViewTestsBase(testutils.base.ServerTestsBase):
    """A base class for tests for the Django app."""

    _USER_ID = 'k'

    def setUp(self):
        super(ViewTestsBase, self).setUp()
        self._xsrf_tool = utils.XsrfTool()

    def login(self, is_admin=False):
        """Logs in the "user" for making requests.

        Args:
           is_admin (bool): Whether the user should be considered an admin.
        """
        self.testbed.setup_env(
            user_email='kay@mib.gov',
            user_id=ViewTestsBase._USER_ID,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def xsrf_token(self, action_id):
        return self._xsrf_tool.generate_token(ViewTestsBase._USER_ID, action_id)

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
