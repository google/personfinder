import datetime

import config
from server_tests_base import ServerTestsBase


class XsrfToolTests(ServerTestsBase):

    def setUp(self):
        ServerTestsBase.setUp(self)
        config.set(xsrf_token_key='abcdef')

    def testRejectGlobalEdit(self):
        self._checkPostIsRejected(
            '/global/admin',
            {'operation': 'save_global',
             'tos_url': 'www.evil.com',
             'sms_number_to_repo': '{}',
             'repo_aliases': '{}',
             'unreviewed_notes_threshold': '{}',})

    def testRejectApiKeyEdit(self):
        self._checkPostIsRejected(
            '/global/admin/api_keys',
            {'contact_name': 'Fred',
             'contact_email': 'fred@example.com',
             'organization_name': 'Fred Inc.',})

    def testRejectCreateRepo(self):
        self._checkPostIsRejected(
            '/global/admin/create_repo',
            {'new_repo': 'buffalo'})

    def testRejectDeleteRecord(self):
        self._checkPostIsRejected(
            '/haiti/admin/delete_record',
            {'operation': 'delete',
             'id': 'localhost.person/123'})

    def testRejectSetDefaultResourceBundle(self):
        self._checkPostIsRejected(
            '/global/admin/resources',
            {'operation': 'set_default',
             'resource_bundle_default': 'newbundle'})

    def _checkPostIsRejected(self, path, data):
        data['xsrf_token'] = 'NotTheRightDigest/123'
        doc = self.go_as_admin(path, data=data)
        self.assertEqual(doc.status, 403)
