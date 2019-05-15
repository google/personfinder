# Copyright 2019 Google Inc.
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


"""Tools to help run tests against the Django app."""

import const
import datetime
import modelmodule.admin_acls as admin_acls_model
import utils

import scrape
import testutils.base


class ViewTestsBase(testutils.base.ServerTestsBase):
    """A base class for tests for the Django app."""

    def setUp(self):
        super(ViewTestsBase, self).setUp()
        self._xsrf_tool = utils.XsrfTool()
        self.data_generator.admin_permission(
            repo_id='global', email_address='z@mib.gov',
            access_level=(
                admin_acls_model.AdminPermission.AccessLevel.SUPERADMIN),
            expiration_date=datetime.datetime(2051, 1, 20))
        self.data_generator.admin_permission(
            repo_id='global', email_address='k@mib.gov',
            access_level=admin_acls_model.AdminPermission.AccessLevel.MANAGER,
            expiration_date=datetime.datetime(2051, 1, 20))
        self.data_generator.admin_permission(
            repo_id='global', email_address='j@mib.gov',
            access_level=admin_acls_model.AdminPermission.AccessLevel.MODERATOR,
            expiration_date=datetime.datetime(2051, 1, 20))
        self._current_user_id = None

    def login_as_superadmin(self):
        self.testbed.setup_env(
            user_email='z@mib.gov',
            user_id='z',
            user_is_admin='0',
            overwrite=True)
        self._current_user_id = 'z'

    def login_as_manager(self):
        self.testbed.setup_env(
            user_email='k@mib.gov',
            user_id='k',
            user_is_admin='0',
            overwrite=True)
        self._current_user_id = 'k'

    def login_as_moderator(self):
        self.testbed.setup_env(
            user_email='j@mib.gov',
            user_id='j',
            user_is_admin='0',
            overwrite=True)
        self._current_user_id = 'j'

    def login_as_nonadmin(self):
        self.testbed.setup_env(
            user_email='frank@mib.gov',
            user_id='frank',
            user_is_admin='0',
            overwrite=True)
        self._current_user_id = 'frank'

    def xsrf_token(self, action_id):
        return self._xsrf_tool.generate_token(self._current_user_id, action_id)

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
