#!/usr/bin/python2.5
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

"""Resources are typed blobs stored in the datastore, which we use to store
pages, stylesheets, images, and templates.  They are just like (small) files
except for a few additional features:
1. We can store localized versions of a resource and fetch the right one.
2. We support rendering a resource into a Django template.
3. We cache the fetched/localized/rendered result in memcache."""

import datetime
import utils
from google.appengine.ext import db
from google.appengine.ext import webapp


# An example of the sequence of calls for rendering a static page.
# In this example, there is a non-localized 'about' resource whose template_name
# is 'base', there is a Russian template at 'base:ru', and all the caches are
# initially empty.  After the page has been rendered, the local caches contain
# the page and template retrieved from the datastore, the compiled Template
# object, and the rendered result.
#
# get_rendered(('about', 'ru'), 'utf8', get_localized)
# > get_localized(('about', 'ru'))
# > > get_by_key_name('about:ru') -> None
# > > get_by_key_name('about:en') -> None
# > > get_by_key_name('about') -> R1
# > > LOCALIZED_CACHE.put(('about', 'ru'), R1, R1.cache_seconds)
# > R1.render()
# > > get_compiled(('base', 'ru'))
# > > > get_localized(('base', 'ru'))
# > > > > get_by_key_name('base:ru')
# > > > > get_by_key_name('base:en') -> R2
# > > > > LOCALIZED_CACHE.put(('base', 'ru'), R2, R2.cache_seconds)
# > > > django.compile(R2.content) -> T
# > > > COMPILED_CACHE.put(('base', 'ru'), T, R2.cache_seconds)
# > > T.execute(R1.title, R1.content, ...) -> html
# > RENDERED_CACHE.put(('about', 'ru'), html, R1.cache_seconds)

# An example of the sequence of calls for rendering a dynamic page.
# In this example, there is a Python handler at 'results.Results' that returns
# a Resource whose template_name is 'base', and all caches are initially empty.
# 
# get_rendered(('results', 'fr'), 'utf8', results.Results.get)
# > results.Results.get('results', 'fr') -> R3
# > R3.render()
# > > get_compiled(('base', 'fr'))
# > > > get_localized(('base', 'fr'))
# > > > > get_by_key_name('base:fr')
# > > > > get_by_key_name('base:en') -> R4
# > > > LOCALIZED_CACHE.put(('base', 'ru'), R4, R4.cache_seconds)
# > > django.compile(R4.content) -> T
# > > COMPILED_CACHE.put(('base', 'ru'), T, R4.cache_seconds)
# > T.execute(R3.title, R3.content, ...) -> html
# > RENDERED_CACHE.put(('results', 'fr'), html, R3.cache_seconds)


class RamCache:
    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache.clear()

    def put(self, key, value, ttl_seconds):
        if ttl_seconds:
            expiry = utils.get_utcnow() + datetime.timedelta(0, ttl_seconds)
            self.cache[key] = (value, expiry)

    def get(self, key):
        if key in self.cache:
            value, expiry = self.cache[key]
            if utils.get_utcnow() < expiry:
                return value


LOCALIZED_CACHE = RamCache()
COMPILED_CACHE = RamCache()
RENDERED_CACHE = RamCache()

def clear_caches():
    LOCALIZED_CACHE.clear()
    COMPILED_CACHE.clear()
    RENDERED_CACHE.clear()


class ResourceNotFoundError(Exception):
    def __init__(self, name, lang):
        Exception.__init__(
            self, 'Failed to find resource %r, lang %r' % (name, lang))


class Resource(db.Model):
    # key_name is a resource_name or resource_name + ':' + language_code
    title = db.StringProperty()  # localized title
    content = db.BlobProperty()  # binary data or UTF8-encoded text
    content_type = db.StringProperty()  # MIME type
    template_name = db.StringProperty()  # optional resource_name of a template
    cache_seconds = db.IntegerProperty()  # cache TTL of rendered resource

    def render(self, lang, **vars):
        """Renders the content of a resource.  If the content_type begins with
        'text/' then the result is a Unicode string; otherwise a byte string."""
        content = self.content
        if self.content_type.startswith('text/'):
            content = content.decode('utf-8')
        if self.template_name:
            template = get_compiled(self.template_name, lang)
            if template:
                dict = {'title': self.title, 'content': content}
                dict.update(vars)
                return template.render(webapp.template.Context(dict))
        return content


def get_localized(resource_name, lang):
    """Gets the localized version of a Resource."""
    cache_key = (resource_name, lang)
    result = LOCALIZED_CACHE.get(cache_key)
    if not result:
        if lang:
            result = Resource.get_by_key_name(resource_name + ':' + lang)
        if not result and lang != 'en':
            result = Resource.get_by_key_name(resource_name + ':en')
        if not result:
            result = Resource.get_by_key_name(resource_name)
        if result:
            LOCALIZED_CACHE.put(cache_key, result, result.cache_seconds)
    return result


def get_compiled(resource_name, lang):
    """Gets the compiled Template object for a template."""
    cache_key = (resource_name, lang)
    result = COMPILED_CACHE.get(cache_key)
    if not result:
        resource = get_localized(resource_name, lang)
        if not resource:
            raise ResourceNotFoundError(resource_name, lang)
        result = webapp.template.Template(
            resource.content, 'Resource', resource.key().name())
        COMPILED_CACHE.put(cache_key, result, resource.cache_seconds)
    return result


def get_rendered(resource_name, lang, charset, resource_getter, **vars):
    """Gets the rendered content of a page as a Unicode string."""
    cache_key = (resource_name, lang, charset)
    result = RENDERED_CACHE.get(cache_key)
    if not result:
        resource = resource_getter(resource_name, lang)
        if not resource:
            raise ResourceNotFoundError(resource_name, lang)
        result = resource.content_type, resource.render(lang, **vars)
        RENDERED_CACHE.put(cache_key, result, resource.cache_seconds)
    return result
