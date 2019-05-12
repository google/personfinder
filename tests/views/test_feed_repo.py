import xml.etree

import model
import utils

import view_tests_base


class FeedRepoViewTests(view_tests_base.ViewTestsBase):

    _NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
    }

    def setUp(self):
        super(FeedRepoViewTests, self).setUp()
        self.haiti_updated_timestamp = 1552682469
        self.nepal_updated_timestamp = 1551682469
        self.pakistan_updated_timestamp = 1550682469
        self.data_generator.repo()
        self.data_generator.setup_repo_config(
            repo_id='haiti',
            updated_date=self.haiti_updated_timestamp)
        self.data_generator.repo(repo_id='nepal')
        self.data_generator.setup_repo_config(
            repo_id='nepal',
            updated_date=self.nepal_updated_timestamp)
        self.data_generator.repo(
            repo_id='pakistan',
            activation_status=model.Repo.ActivationStatus.DEACTIVATED)
        self.data_generator.setup_repo_config(
            repo_id='pakistan',
            updated_date=self.pakistan_updated_timestamp)

    def test_single_repo_feed(self):
        root = self._get_parsed_feed('/haiti/feeds/repo')
        all_entry_els = self._xml_findall(root, 'atom:entry')
        self.assertEqual(len(all_entry_els), 1)
        entry_el = all_entry_els[0]
        self.assertEqual(
            self._xml_findall(entry_el, 'atom:id')[0].text,
            'http://testserver/haiti/')
        all_title_els = self._xml_findall(entry_el, 'atom:title')
        self.assertEqual(len(all_title_els), 1)
        self.assertEqual(all_title_els[0].text, 'Haiti')
        self.assertEqual(
            self._xml_findall(entry_el, 'atom:updated')[0].text,
            utils.format_utc_timestamp(self.haiti_updated_timestamp))

    def atest_global_repo_feed(self):
        feed = self._get_parsed_feed('/global/feeds/repo')
        entry_els = feed.findall('{http://www.w3.org/2005/Atom}entry')
        self.assertEqual(len(entry_els), 2)
        haiti_el = entry_els[0]
        haiti_titles = haiti_el.findall('{http://www.w3.org/2005/Atom}title')
        self.assertEqual(len(haiti_titles), 3)
        self.assertEqual('haiti', haiti_titles[0].text)
        nepal_el = entry_els[1]

    def _get_parsed_feed(self, path):
        resp = self.client.get(path)
        return xml.etree.ElementTree.fromstring(resp.content)

    def _xml_findall(self, base_el, expr):
        return base_el.findall(expr, FeedRepoViewTests._NAMESPACES)
