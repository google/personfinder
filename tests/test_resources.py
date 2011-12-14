#!/usr/bin/python2.5
# encoding: utf-8
# Copyright 2011 Google Inc.
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

"""Tests for resources.py."""

import unittest

from google.appengine.ext import db
from google.appengine.ext import webapp
import resources
from resources import Resource
import utils
import sys


class RamCacheTests(unittest.TestCase):
    def setUp(self):
        utils.set_utcnow_for_test(0)

    def tearDown(self):
        utils.set_utcnow_for_test(None)

    def test_data_is_cached(self):
        cache = resources.RamCache()
        cache.put('a', 'b')
        assert cache.get('a', 1) == 'b'

    def test_max_age_zero_ignores_cache(self):
        cache = resources.RamCache()
        cache.put('a', 'b')
        assert cache.get('a', 0) is None

    def test_data_expires_after_max_age(self):
        cache = resources.RamCache()
        cache.put('a', 'b')
        utils.set_utcnow_for_test(9.99)
        assert cache.get('a', 10) == 'b'
        utils.set_utcnow_for_test(10.01)
        assert cache.get('a', 10) is None

    def test_clear(self):
        cache = resources.RamCache()
        cache.put('a', 'b')
        assert cache.get('a', 1) == 'b'
        cache.clear()
        assert cache.get('a', 1) is None


class ResourcesTests(unittest.TestCase):
    def setUp(self):
        utils.set_utcnow_for_test(0)
        resources.clear_caches()

        self.temp_entity_keys = []
        self.put_resource('page.html:fr',
                          '{% extends "base.html.template" %} fran\xc3\xa7ais')
        self.put_resource('page.html', 'default')
        self.put_resource('base.html.template:es', 
                          '\xc2\xa1hola! {{content|safe}}')
        self.put_resource('base.html.template',
                          'hi! {% block content %} {% endblock content %}')
        self.put_resource('data', '\xff\xfe\xfd\xfc')

        self.fetches = []
        self.compilations = []
        self.renderings = []

        self.resource_get_by_key_name_original = Resource.get_by_key_name
        self.template_init_original = webapp.template.Template.__init__
        self.template_render_original = webapp.template.Template.render

        test_self = self

        @staticmethod
        def resource_get_by_key_name_for_test(key_name):
            test_self.fetches.append(key_name)  # track datastore fetches
            return test_self.resource_get_by_key_name_original(key_name)

        def template_init_for_test(self, content, origin, name):
            test_self.compilations.append(name)  # track compilations
            test_self.template_init_original(self, content, origin, name)

        def template_render_for_test(self, context):
            test_self.renderings.append(self.name)  # track render calls
            return test_self.template_render_original(self, context)

        Resource.get_by_key_name = resource_get_by_key_name_for_test
        webapp.template.Template.__init__ = template_init_for_test
        webapp.template.Template.render = template_render_for_test

    def tearDown(self):
        utils.set_utcnow_for_test(None)
        resources.clear_caches()

        db.delete(self.temp_entity_keys)

        Resource.get_by_key_name = self.resource_get_by_key_name_original
        webapp.template.Template.__init__ = self.template_init_original
        webapp.template.Template.render = self.template_render_original

    def put_resource(self, key_name, content):
        """Puts a Resource in the datastore for testing, and tracks it to
        be cleaned up in test teardown."""
        key = Resource(key_name=key_name, content=content).put()
        self.temp_entity_keys.append(key)

    def delete_resource(self, key_name):
        """Deletes a Resource that was put by put_resource."""
        key = db.Key.from_path('Resource', key_name)
        db.delete(key)
        self.temp_entity_keys.remove(key)

    def test_get(self):
        # Verify that Resource.get fetches a Resource from the datastore.
        assert Resource.get('xyz') is None
        self.put_resource('xyz', 'pqr')
        assert Resource.get_by_key_name('xyz').content == 'pqr'
        assert Resource.get('xyz').content == 'pqr'
        self.delete_resource('xyz')
        assert Resource.get('xyz') is None

        # Verify that Resource.get fetches a Resource from a file.
        file_content = Resource.get('message.html.template').content
        assert file_content != 'pqr'

        # Verify that the file can be overriden by a datastore entity.
        self.put_resource('message.html.template', 'pqr')
        assert Resource.get('message.html.template').content == 'pqr'
        self.delete_resource('message.html.template')
        assert Resource.get('message.html.template').content == file_content

    def test_get_localized(self):
        get_localized = resources.get_localized

        assert get_localized('page', 'es').content == 'default'
        assert self.fetch_count == 3  # page:es, page:en, page
        assert get_localized('page', 'en').content == 'default'
        assert self.fetch_count == 5  # page:en, page
        assert get_localized('page', 'fr').content == 'fran\xc3\xa7ais'
        assert self.fetch_count == 6  # page:fr

        # These should now be cache hits, and shouldn't touch the datastore.
        self.fetch_count = 0
        assert get_localized('page', 'es').content == 'default'
        assert get_localized('page', 'en').content == 'default'
        assert get_localized('page', 'fr').content == 'fran\xc3\xa7ais'
        assert self.fetch_count == 0

        # Expire page:fr from the cache.
        utils.set_utcnow_for_test(21)
        assert get_localized('page', 'es').content == 'default'
        assert get_localized('page', 'en').content == 'default'
        assert self.fetch_count == 0
        assert get_localized('page', 'fr').content == 'fran\xc3\xa7ais'
        assert self.fetch_count == 1

        # Expire page:es from the cache.  (page:fr remains cached.)
        utils.set_utcnow_for_test(31)
        self.fetch_count = 0
        assert get_localized('page', 'es').content == 'default'
        assert self.fetch_count == 3
        assert get_localized('page', 'en').content == 'default'
        assert self.fetch_count == 5
        assert get_localized('page', 'fr').content == 'fran\xc3\xa7ais'
        assert self.fetch_count == 5

    def test_get_compiled(self):
        context = webapp.template.Context({'content': 'x'})
        get_compiled = resources.get_compiled

        assert get_compiled('template', 'fr').render(context) == 'hi! x'
        assert self.fetch_count == 2  # template:fr, template:en
        assert self.compile_count == 1
        assert get_compiled('template', 'es').render(context) == u'\xa1hola! x'
        assert self.fetch_count == 3  # template:es
        assert self.compile_count == 2
        assert get_compiled('template', 'en').render(context) == 'hi! x'
        assert self.fetch_count == 4  # template:en
        assert self.compile_count == 3

        # These should now be cache hits, and shouldn't compile or fetch.
        self.fetch_count = 0
        self.compile_count = 0
        assert get_compiled('template', 'fr').render(context) == 'hi! x'
        assert get_compiled('template', 'es').render(context) == u'\xa1hola! x'
        assert get_compiled('template', 'en').render(context) == 'hi! x'
        assert self.fetch_count == 0
        assert self.compile_count == 0

        # Expire template:es from the cache.  (template:en remains cached.)
        utils.set_utcnow_for_test(41)
        assert get_compiled('template', 'fr').render(context) == 'hi! x'
        assert self.fetch_count == 0
        assert self.compile_count == 0
        assert get_compiled('template', 'es').render(context) == u'\xa1hola! x'
        assert self.fetch_count == 1
        assert self.compile_count == 1
        assert get_compiled('template', 'en').render(context) == 'hi! x'
        assert self.fetch_count == 1  # template:en is still cached
        assert self.compile_count == 1

        # Expire template:en from the cache.  (template:es remains cached.)
        utils.set_utcnow_for_test(51)
        self.fetch_count = 0
        self.compile_count = 0
        assert get_compiled('template', 'fr').render(context) == 'hi! x'
        assert self.fetch_count == 2
        assert self.compile_count == 1
        assert get_compiled('template', 'es').render(context) == u'\xa1hola! x'
        assert self.fetch_count == 2  # template:es is still cached
        assert self.compile_count == 1
        assert get_compiled('template', 'en').render(context) == 'hi! x'
        assert self.fetch_count == 3
        assert self.compile_count == 2

    def test_get_rendered(self):
        get_rendered = lambda name, lang: resources.get_rendered(
            name, lang, 'utf-8', resources.get_localized)

        assert get_rendered('page', 'es') == ('text/html', u'\xa1hola! default')
        assert self.fetch_count == 4  # page:es, page:en, page, template:es
        assert self.compile_count == 1
        assert self.render_count == 1

        assert get_rendered('page', 'fr') == ('text/html', u'hi! fran\xe7ais')
        assert self.fetch_count == 7  # page:fr, template:fr, template:en
        assert self.compile_count == 2
        assert self.render_count == 2

        assert get_rendered('page', 'en') == ('text/html', u'hi! default')
        assert self.fetch_count == 10  # page:en, page, template:en
        assert self.compile_count == 3
        assert self.render_count == 3

        # These should be cache hits, and shouldn't compile, fetch, or render.
        self.fetch_count = 0
        self.compile_count = 0
        self.render_count = 0
        assert get_rendered('page', 'es') == ('text/html', u'\xa1hola! default')
        assert get_rendered('page', 'fr') == ('text/html', u'hi! fran\xe7ais')
        assert get_rendered('page', 'en') == ('text/html', u'hi! default')
        assert self.fetch_count == 0
        assert self.compile_count == 0
        assert self.render_count == 0

        # Expire the pages but not the templates.
        utils.set_utcnow_for_test(31)
        assert get_rendered('page', 'es') == ('text/html', u'\xa1hola! default')
        assert self.fetch_count == 3  # page:es, page:en, page
        assert self.compile_count == 0
        assert self.render_count == 1
        assert get_rendered('page', 'fr') == ('text/html', u'hi! fran\xe7ais')
        assert self.fetch_count == 4  # page:fr
        assert self.compile_count == 0
        assert self.render_count == 2
        assert get_rendered('page', 'en') == ('text/html', u'hi! default')
        assert self.fetch_count == 6  # page:en, page
        assert self.compile_count == 0
        assert self.render_count == 3

        # Expire the templates and page:fr (page:en and page:es remain cached).
        utils.set_utcnow_for_test(52)
        self.fetch_count = 0
        self.compile_count = 0
        self.render_count = 0
        assert get_rendered('page', 'es') == ('text/html', u'\xa1hola! default')
        assert self.fetch_count == 0  # rendered page is still cached
        assert self.compile_count == 0
        assert self.render_count == 0
        assert get_rendered('page', 'fr') == ('text/html', u'hi! fran\xe7ais')
        assert self.fetch_count == 3  # page:fr, template:fr, template:en
        assert self.compile_count == 1
        assert self.render_count == 1
        assert get_rendered('page', 'en') == ('text/html', u'hi! default')
        assert self.fetch_count == 3  # rendered page is still cached
        assert self.compile_count == 1
        assert self.render_count == 1

        # Expire the rendered versions of page:es and page:en.
        utils.set_utcnow_for_test(62)
        self.fetch_count = 0
        self.compile_count = 0
        self.render_count = 0
        assert get_rendered('page', 'es') == ('text/html', u'\xa1hola! default')
        assert self.fetch_count == 4  # page:es, page:en, page, template:es
        assert self.compile_count == 1
        assert self.render_count == 1
        assert get_rendered('page', 'en') == ('text/html', u'hi! default')
        assert self.fetch_count == 7  # page:en, page, template:en
        assert self.compile_count == 2
        assert self.render_count == 2

        # Ensure binary data is preserved.
        assert get_rendered('data', 'en') == (
            'application/data', '\xff\xfe\xfd\xfc')

