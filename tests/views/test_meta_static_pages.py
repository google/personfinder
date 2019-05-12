# encoding: utf-8

import view_tests_base


class MetaStaticPagesViewTests(view_tests_base.ViewTestsBase):

    def setUp(self):
        super(MetaStaticPagesViewTests, self).setUp()
        self.data_generator.repo()

    def test_get_homepage(self):
        resp = self.client.get('/', secure=True)
        self.assertTrue('You are now running Person Finder.' in resp.content)
        # Legacy path for the homepage.
        resp = self.client.get('/global/home.html', secure=True)
        self.assertTrue('You are now running Person Finder.' in resp.content)

    def test_get_responders_page(self):
        resp = self.client.get('/global/responders.html', secure=True)
        self.assertTrue('Information for responders' in resp.content)
        resp = self.client.get('/global/responders.html?lang=ja', secure=True)
        self.assertTrue('災害対応者向け情報' in resp.content)

    def test_get_howto_page(self):
        resp = self.client.get('/global/howto.html', secure=True)
        self.assertTrue('from a PC or mobile phone.' in resp.content)
        resp = self.client.get('/global/howto.html?lang=ja', secure=True)
        self.assertTrue('自分の安否を伝える' in resp.content)
