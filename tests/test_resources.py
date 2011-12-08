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
import utils
import sys


class RamCacheTests(unittest.TestCase):
    def setUp(self):
        utils.set_utcnow_for_test(0)

    def tearDown(self):
        utils.set_utcnow_for_test(None)

    def test_data_is_cached(self):
        cache = resources.RamCache()
        cache.put('a', 'b', 1)
        assert cache.get('a') == 'b'

    def test_ttl_zero_not_cached(self):
        cache = resources.RamCache()
        cache.put('a', 'b', 0)
        assert cache.get('a') is None

    def test_data_expires_after_ttl(self):
        cache = resources.RamCache()
        cache.put('a', 'b', 10)
        utils.set_utcnow_for_test(9.99)
        assert cache.get('a') == 'b'
        utils.set_utcnow_for_test(10.01)
        assert cache.get('a') is None

    def test_clear(self):
        cache = resources.RamCache()
        cache.put('a', 'b', 1)
        assert cache.get('a') == 'b'
        cache.clear()
        assert cache.get('a') is None


class ResourcesTests(unittest.TestCase):
    def setUp(self):
        utils.set_utcnow_for_test(0)
        resources.clear_caches()

        self.temp_entities = [resources.Resource(
            key_name='page:fr',
            title='page',
            content='fran\xc3\xa7ais',
            content_type='text/html',
            template_name='template',
            cache_seconds=20.0
        ), resources.Resource(
            key_name='page',
            title='page',
            content='default',
            content_type='text/html',
            template_name='template',
            cache_seconds=30.0
        ), resources.Resource(
            key_name='template:es',
            title='template',
            content='\xc2\xa1hola! {{content|safe}}',
            content_type='text/html',
            cache_seconds=40.0
        ), resources.Resource(
            key_name='template:en', title='template',
            content='hi! {{content|safe}}',
            content_type='text/html',
            cache_seconds=50.0
        ), resources.Resource(
            key_name='data', title='data',
            content='\xff\xfe\xfd\xfc',
            content_type='application/data'
        )]
        db.put(self.temp_entities)

        test_self = self
        self.fetch_count = 0
        self.compile_count = 0
        self.render_count = 0

        class ResourceForTest(resources.Resource):
            @staticmethod
            def get_by_key_name(*args):
                # Track the number of datastore fetches.
                test_self.fetch_count += 1
                return test_self.original_resource.get_by_key_name(*args)

        class TemplateForTest(webapp.template.Template):
            def __init__(self, *args):
                # Track the number of template compilations.
                test_self.compile_count += 1
                test_self.original_template.__init__(self, *args)

            def render(self, *args):
                # Track the number of template renderings.
                test_self.render_count += 1
                return test_self.original_template.render(self, *args)

        self.original_resource = resources.Resource
        resources.Resource = ResourceForTest

        self.original_template = webapp.template.Template
        webapp.template.Template = TemplateForTest

    def tearDown(self):
        utils.set_utcnow_for_test(None)
        resources.clear_caches()

        db.delete(self.temp_entities)

        resources.Resource = self.original_resource
        webapp.template.Template = self.original_template

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

