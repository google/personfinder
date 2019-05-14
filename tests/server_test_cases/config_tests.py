# encoding: utf-8
# Copyright 2010 Google Inc.
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

"""Test cases for end-to-end testing.  Run with the server_tests script."""

import simplejson
from model import *
import setup_pf as setup
from server_tests_base import ServerTestsBase


class ConfigTests(ServerTestsBase):
    """Tests related to configuration settings (ConfigEntry entities)."""

    # Repo and ConfigEntry entities should be wiped between tests.
    kinds_to_keep = ['Authorization']

    def tearDown(self):
        ServerTestsBase.tearDown(self)

        # Restore the configuration settings.
        setup.setup_repos()
        setup.setup_configs()

        # Flush the configuration cache.
        config.cache.enable(False)
        self.go('/haiti?lang=en&flush=config')

    def get_admin_page_error_message(self):
        error_divs = self.s.doc.cssselect('div.error')
        if error_divs:
            return 'Error message: %s' % error_divs[0].text
        else:
            return 'Whole page HTML:\n%s' % self.s.doc.content

    def test_config_cache_enabling(self):
        # The tests below flush the resource cache so that the effects of
        # the config cache become visible for testing.

        # Modify the custom title directly in the datastore.
        # With the config cache off, new values should appear immediately.
        config.cache.enable(False)
        db.put(config.ConfigEntry(key_name='haiti:repo_titles',
                                  value='{"en": "FooTitle"}'))
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'FooTitle' in doc.text
        db.put(config.ConfigEntry(key_name='haiti:repo_titles',
                                  value='{"en": "BarTitle"}'))
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'BarTitle' in doc.text

        # Now enable the config cache and load the main page again.
        # This should pull the configuration value from database and cache it.
        config.cache.enable(True)
        doc = self.go('/haiti?lang=en&flush=config,resource')
        assert 'BarTitle' in doc.text

        # Modify the custom title directly in the datastore.
        # The old message from the config cache should still be visible because
        # the config cache doesn't know that the datastore changed.
        db.put(config.ConfigEntry(key_name='haiti:repo_titles',
                                  value='{"en": "QuuxTitle"}'))
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'BarTitle' in doc.text

        # After 10 minutes, the cache should pick up the new value.
        self.advance_utcnow(seconds=601)
        doc = self.go('/haiti?lang=en&flush=resource')
        assert 'QuuxTitle' in doc.text


    def test_config_namespaces(self):
        # Tests the cache's ability to retrieve global or repository-specific
        # configuration entries.
        config.set_for_repo('*',
                            captcha_private_key='global_abcd',
                            captcha_public_key='global_efgh',
                            translate_api_key='global_hijk')
        cfg_global = config.Configuration('*')
        assert cfg_global.captcha_private_key == 'global_abcd'
        assert cfg_global.captcha_public_key == 'global_efgh'
        assert cfg_global.translate_api_key == 'global_hijk'

        config.set_for_repo('_foo',
                            captcha_private_key='abcd',
                            captcha_public_key='efgh')
        cfg_sub = config.Configuration('_foo')
        assert cfg_sub.captcha_private_key == 'abcd'
        assert cfg_sub.captcha_public_key == 'efgh'
        # If a key isn't present for a repository, its value for
        # the global domain is retrieved.
        assert cfg_sub.translate_api_key == 'global_hijk'

    def test_no_exception_for_unset_key(self):
        # Tests that a config will return None, and not throw an exception, when
        # asked for the value of an unknown key.
        config.set_for_repo('*', good_key_1='abc', good_key_2='def')
        config.set_for_repo('foo', good_key_1='ghi')
        cfg = config.Configuration('foo')
        assert cfg['good_key_1'] == 'ghi'
        assert cfg['good_key_2'] == 'def'
        assert cfg['unknown_key'] is None

    def test_get_with_default(self):
        config.set_for_repo('foo', key_1='abc')
        cfg = config.Configuration('foo')
        assert cfg.get('unknown_key', 'default_value') == 'default_value'

    def test_deactivation(self):
        # Deactivate an existing repository.
        repo_obj = Repo.get('haiti')
        repo_obj.activation_status=Repo.ActivationStatus.DEACTIVATED
        repo_obj.put()
        config.set_for_repo(
            'haiti',
            deactivation_message_html='de<i>acti</i>vated')

        # Ensure all paths listed in app.yaml are inaccessible, except /admin.
        for path in ['', '/query', '/results', '/create', '/view',
                     '/multiview', '/reveal', '/photo', '/embed',
                     '/gadget', '/delete', '/api/read', '/api/write',
                     '/feeds/note', '/feeds/person']:
            doc = self.go('/haiti%s' % path)
            assert 'de<i>acti</i>vated' in doc.content, \
                'path: %s, content: %s' % (path, doc.content)
            assert not doc.cssselect('form')
            assert not doc.cssselect('input')
            assert not doc.cssselect('table')
            assert not doc.cssselect('td')

    def test_non_test_mode(self):
        HTML_PATHS = ['', '/query', '/results', '/create', '/view',
                      '/multiview', '/reveal', '/photo', '/embed', '/delete']

        # First check no HTML pages show the test mode message.
        for path in HTML_PATHS:
            doc = self.go('/haiti%s' % path)
            assert 'currently in test mode' not in doc.content, \
                'path: %s, content: %s' % (path, doc.content)

    def test_the_test_mode(self):
        HTML_PATHS = ['', '/query', '/results', '/create', '/view',
                      '/multiview', '/reveal', '/photo', '/embed', '/delete']

        # Enable test-mode for an existing repository.
        config.set_for_repo('haiti', test_mode=True)

        # Ensure all HTML pages show the test mode message.
        for path in HTML_PATHS:
            doc = self.go('/haiti%s' % path)
            assert 'currently in test mode' in doc.content, \
                'path: %s, content: %s' % (path, doc.content)

    def test_custom_messages(self):
        config.set_for_repo(
            'haiti',
            language_menu_options=['en'],
            repo_titles={'en': 'Foo'},
            keywords='foo, bar',
            profile_websites='[]',
            start_page_custom_htmls=
                {'en': '<b>English</b> start page message',
                 'fr': '<b>French</b> start page message'},
            results_page_custom_htmls=
                {'en': '<b>English</b> results page message',
                 'fr': '<b>French</b> results page message'},
            view_page_custom_htmls=
                {'en': '<b>English</b> view page message',
                 'fr': '<b>French</b> view page message'},
            seek_query_form_custom_htmls=
                {'en': '<b>English</b> query form message',
                 'fr': '<b>French</b> query form message'},
            footer_custom_htmls=
                {'en': '<b>English</b> footer message',
                 'fr': '<b>French</b> footer message'},
        )

        # Add a person record
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            repo='haiti',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_status_full_name',
            author_name='_status_author_name'
        ))

        # Check for custom message on main page
        doc = self.go('/haiti?flush=*')
        assert 'English start page message' in doc.text
        doc = self.go('/haiti?flush=*&lang=fr')
        assert 'French start page message' in doc.text
        doc = self.go('/haiti?flush=*&lang=ht')
        assert 'English start page message' in doc.text

        # Check for custom messages on results page
        doc = self.go('/haiti/results?query_name=xy&role=seek&lang=en')
        assert 'English results page message' in doc.text
        assert 'English query form message' in doc.text
        doc = self.go('/haiti/results?query_name=xy&role=seek&lang=fr')
        assert 'French results page message' in doc.text
        assert 'French query form message' in doc.text
        doc = self.go('/haiti/results?query_name=xy&role=seek&lang=ht')
        assert 'English results page message' in doc.text
        assert 'English query form message' in doc.text

        # Check for custom message on view page
        doc = self.go('/haiti/view?id=test.google.com/person.1001&lang=en')
        assert 'English view page message' in doc.text
        doc = self.go(
            '/haiti/view?id=test.google.com/person.1001&lang=fr')
        assert 'French view page message' in doc.text
        doc = self.go(
            '/haiti/view?id=test.google.com/person.1001&lang=ht')
        assert 'English view page message' in doc.text

    def test_analytics_id(self):
        """Checks that the analytics_id config is used for analytics."""
        doc = self.go('/haiti/create')
        assert 'getTracker(' not in doc.content

        config.set(analytics_id='analytics_id_xyz')

        doc = self.go('/haiti/create')
        assert "'gaProperty': 'analytics_id_xyz'" in doc.content

    def test_maps_api_key(self):
        """Checks that maps don't appear when there is no maps_api_key."""
        db.put(Person(
            key_name='haiti:test.google.com/person.1001',
            repo='haiti',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_status_full_name',
            author_name='_status_author_name'
        ))
        doc = self.go('/haiti/create?role=provide')
        assert not doc.cssselect('#clickable_map')
        doc = self.go('/haiti/add_note?id=test.google.com/person.1001')
        assert not doc.cssselect('#clickable_map')

        config.set(maps_api_key='maps_api_key_xyz')

        doc = self.go('/haiti/create?role=provide')
        assert 'maps_api_key_xyz' in doc.content
        assert doc.cssselect('#clickable_map')
        doc = self.go('/haiti/add_note?id=test.google.com/person.1001')
        assert 'maps_api_key_xyz' in doc.content
        assert doc.cssselect('#clickable_map')

    def test_configuration_not_callable(self):
        """Checks that a Configuration instance is not callable.

        This is required to make it work in Django template. See the comment of
        config.Configuration.__getattr__() for details.
        """
        cfg = config.Configuration('xyz')
        assert not callable(cfg)
