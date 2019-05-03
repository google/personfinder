from google.appengine.ext import db

import model

import view_tests_base


class AdminDashboardViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(AdminDashboardViewTests, self).setUp()
        self.data_generator.repo()
        self.data_generator.repo('pakistan')
        self.login_as_manager()

    def test_get(self):
        db.put([
            model.Counter(
                scan_name='Person', repo='haiti', last_key='', count_all=278),
            model.Counter(
                scan_name='Person', repo='pakistan', last_key='',
                count_all=127),
            model.Counter(
                scan_name='Note', repo='haiti', last_key='', count_all=12),
            model.Counter(
                scan_name='Note', repo='pakistan', last_key='', count_all=8)
        ])
        resp = self.client.get('/global/admin/dashboard')
        self.assertEqual(resp.status_code, 200)
