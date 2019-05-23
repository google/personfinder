# encoding: utf-8
import xml.etree

import model

import view_tests_base


class FeedRepoViewTests(view_tests_base.ViewTestsBase):

    _NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
    }

    _SINGLE_REPO_FEED_EXPECTED_CONTENT = (
        '<?xml version="1.0" encoding="UTF-8"?><feed '
        'xmlns:georss="http://www.georss.org/georss" '
        'xmlns:gpf="http://schemas.google.com/personfinder/2012" '
        'xmlns="http://www.w3.org/2005/Atom"><id>'
        'http://testserver/haiti/feeds/repo</id><title>Person Finder Repository'
        ' Feed</title><updated>2019-03-15T20:41:09Z</updated><entry><id>'
        'http://testserver/haiti/</id><title lang="en">Haiti Earthquake</title>'
        '<updated>2019-03-15T20:41:09Z</updated><content type="text/xml">'
        '<gpf:repo><gpf:title lang="fr">S&#233;isme en Ha&#239;ti</gpf:title>'
        '<gpf:title lang="en">Haiti Earthquake</gpf:title><gpf:title lang="es">'
        'Terremoto en Hait&#237;</gpf:title><gpf:title lang="ht">Tranbleman '
        'T&#232; an Ayiti</gpf:title><gpf:read_auth_key_required>false'
        '</gpf:read_auth_key_required><gpf:search_auth_key_required>false'
        '</gpf:search_auth_key_required><gpf:test_mode>false</gpf:test_mode>'
        '<gpf:location><georss:point>18.968637 -72.284546</georss:point>'
        '</gpf:location></gpf:repo></content></entry></feed>')

    def setUp(self):
        super(FeedRepoViewTests, self).setUp()
        self.haiti_updated_timestamp = 1552682469
        self.nepal_updated_timestamp = 1551682469
        self.pakistan_updated_timestamp = 1550682469
        self.data_generator.repo()
        self.data_generator.setup_repo_config(
            repo_id='haiti',
            updated_date=self.haiti_updated_timestamp,
            repo_titles={
                'en': 'Haiti Earthquake',
                'es': 'Terremoto en Haití',
                'fr': 'Séisme en Haïti',
                'ht': 'Tranbleman Tè an Ayiti',
            },
            map_default_center=[18.968637, -72.284546])
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

    def test_nonexistent_repo_feed(self):
        resp = self.client.get('/nonexistent/feeds/repo')
        self.assertEqual(resp.status_code, 404)

    def test_deactivated_repo_feed(self):
        resp = self.client.get('/pakistan/feeds/repo')
        self.assertEqual(resp.status_code, 404)

    def test_single_repo_feed(self):
        resp = self.client.get('/haiti/feeds/repo')
        self.assertEqual(
            resp.content, FeedRepoViewTests._SINGLE_REPO_FEED_EXPECTED_CONTENT)

    def test_global_repo_feed(self):
        feed = self._get_parsed_feed('/global/feeds/repo')
        entry_els = feed.findall('{http://www.w3.org/2005/Atom}entry')
        self.assertEqual(len(entry_els), 2)
        haiti_el = entry_els[0]
        self.assertEqual(
            haiti_el.findall('{http://www.w3.org/2005/Atom}id')[0].text,
            'http://testserver/haiti/')
        nepal_el = entry_els[1]
        self.assertEqual(
            nepal_el.findall('{http://www.w3.org/2005/Atom}id')[0].text,
            'http://testserver/nepal/')

    def _get_parsed_feed(self, path):
        resp = self.client.get(path)
        return xml.etree.ElementTree.fromstring(resp.content)
