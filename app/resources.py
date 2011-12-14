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

"""Resources are blobs in the datastore that can contain pages of HTML,
stylesheets, images, or templates.  A Resource is just like a small file
except for a few additional features:
    1. Resources can be fetched from the datastore or from files on disk.
    2. We can store localized versions of a resource and select one.
    3. We support compiling and rendering a resource as a Django template.
    4. We cache the fetched, compiled, or rendered result in RAM."""

import django_setup

import datetime
import utils

from google.appengine.ext import db
from google.appengine.ext import webapp


# Requests for files and pages pass through three stages:
#   1. get_rendered(): decides whether to serve plain data or render a Template
#   2. get_localized(): selects the localized version of a Resource
#   3. Resource.get(): gets a Resource from the datastore or from a file
#
# When a request is served by a dynamic handler, the handler prepares some
# template variables and then renders the template using the same four stages.
#
# Suppose that a static image file '/global/logo.jpg' is requested, the current
# language is 'ru', and there is a Resource entity with key name 'logo.jpg' in
# the datastore.  The expected sequence of calls is as follows:
#
# request for static image, action='logo.jpg'
# > get_rendered('logo.jpg', 'ru')
#   > get_localized('logo.jpg', 'ru')
#     > Resource.get('logo.jpg:ru') -> None
#       > Resource.get_by_key_name('logo.jpg:ru') -> None
#       > Resource.load_from_file('logo.jpg:ru') -> None
#     > Resource.get('logo.jpg')
#       > Resource.get_by_key_name('logo.jpg') -> R1
#     > LOCALIZED_CACHE.put(('logo.jpg', 'ru'), R1)
#   > RENDERED_CACHE.put(('logo.jpg', 'ru', None), R1.content)
# > self.response.out.write(R1.content)
#
# Suppose that a static page '/global/faq.html' is requested.  Assume there is
# a localized 'faq.html.template:ru' resource in Russian and a non-localized
# template file at 'resources/base.template', and all the caches are initially
# empty.  Due to the settings in django_setup.py, resources.TemplateLoader will
# handle template loading.  The expected sequence of calls is as follows:
#
# request for static page, action='faq.html'
# > get_rendered('faq.html', 'ru')
#   > get_localized('faq.html', 'ru') -> None
#   > get_localized('faq.html.template', 'ru')
#     > Resource.get('faq.html.template:ru')
#       > Resource.get_by_key_name('faq.html.template:ru') -> R2
#     > LOCALIZED_CACHE.put(('faq.html.template', 'ru'), R2)
#   > R2.get_template() -> T2  # compile the template
#   > T2.render(vars)  # T2 extends "base.html.template", so:
#     > TemplateLoader.load_template('base.html.template')
#       > get_localized('base.html.template', 'ru')
#         > Resource.get('base.html.template:ru')
#           > Resource.get_by_key_name('base.html.template:ru') -> None
#           > Resource.load_from_file('base.html.template:ru') -> None
#         > Resource.get('base.html.template')
#           > Resource.get_by_key_name('base.html.template') -> None
#           > Resource.load_from_file('base.html.template') -> R3
#         > LOCALIZED_CACHE.put(('base.html.template', 'ru'), R3)
#       > R3.get_template() -> T3  # compile the template
#     > return rendered_string
#   > RENDERED_CACHE.put(('faq.html', 'ru', None), rendered_string)
# > self.response.out.write(rendered_string)
#
# Suppose the dynamic page '/<repo>/view' is now requested.  Assume that R3
# is still cached from the above request.  The expected sequence of calls is:
# 
# request for dynamic page, action='view', with an 'id' query parameter
# > view.Handler.get()
#   > model.Person.get_by_key_name(person_record_id)
#   > BaseHandler.render('view.html', first_name=..., ...)
#     > get_rendered('view.html', 'ru', ..., first_name=..., ...)
#       > get_localized('view.html', 'ru') -> None
#       > get_localized('view.html.template', 'ru')
#         > Resource.get('view.html.template:ru') -> None
#           > Resource.get_by_key_name('view.html.template:ru') -> None
#           > Resource.load_from_file('view.html.template:ru') -> None
#         > Resource.get('view.html.template') -> None
#           > Resource.get_by_key_name('view.html.template') -> None
#           > Resource.load_from_file('view.html.template') -> R4
#         > LOCALIZED_CACHE.put(('view.template', 'ru'), R4)
#       > R4.get_template() -> T4  # compiled the template
#       > T4.render(first_name=..., ...)  # T4 extends "base.html.template", so:
#         > TemplateLoader.load_template('base.html.template')
#           > get_localized('base.html.template', 'ru')
#             > LOCALIZED_CACHE.get(('base.html.template', 'ru')) -> R3
#           > R3.get_template() -> T3  # gets previously compiled R3.template
#         > return rendered_string
#       > return rendered_string  # don't cache
#     > self.response.out.write(rendered_string)


class RamCache:
    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache.clear()

    def put(self, key, value, ttl_seconds):
        if ttl_seconds > 0:
            expiry = utils.get_utcnow() + datetime.timedelta(0, ttl_seconds)
            self.cache[key] = (value, expiry)

    def get(self, key):
        if key in self.cache:
            value, expiry = self.cache[key]
            if utils.get_utcnow() < expiry:
                return value


class Resource(db.Model):
    """Resources are blobs in the datastore that can contain pages of HTML,
    stylesheets, images, or templates.  A Resource is just like a small file
    except for a few additional features:
        1. Resources can be fetched from the datastore or from files on disk.
        2. We can store localized versions of a resource and select one.
        3. We support compiling and rendering a resource as a Django template.
        4. We cache the fetched, compiled, or rendered result in RAM.
    The key_name is a resource_name or resource_name + ':' + language_code."""
    cache_seconds = db.FloatProperty(default=1.0)  # cache TTL of resource
    content = db.BlobProperty()  # binary data or UTF8-encoded template text
    last_modified = db.DateTimeProperty(auto_now=True)  # for bookkeeping

    # TODO(kpy): Move all the templates and static files into app/resources
    # and change RESOURCE_DIR to 'resources'.
    RESOURCE_DIR = 'templates'  # directory containing resource files

    @staticmethod
    def load_from_file(name):
        """Creates a Resource from a file, or returns None if no such file."""
        try:
            file = open(Resource.RESOURCE_DIR + '/' + name)
            return Resource(key_name=name, content=file.read())
        except IOError:
            return None

    @staticmethod
    def get(name):
        """Fetches a resource, first looking in the datastore, then falling
        back to a file on disk.  Returns None if neither is found."""
        return Resource.get_by_key_name(name) or Resource.load_from_file(name)

    def get_template(self):
        """Compiles the content of this resource into a Template object."""
        if not hasattr(self, 'template'):
            self.template = webapp.template.Template(
                self.content.decode('utf-8'), 'Resource', self.key().name())
        return self.template


LOCALIZED_CACHE = RamCache()  # contains Resource objects
RENDERED_CACHE = RamCache()  # contains strings of rendered content

def clear_caches():
    LOCALIZED_CACHE.clear()
    RENDERED_CACHE.clear()

def get_localized(resource_name, lang):
    """Gets the localized (or if none, generic) version of a Resource from the
    cache, the datastore, or a file.  Returns None if no match is found."""
    cache_key = (resource_name, lang)
    resource = LOCALIZED_CACHE.get(cache_key)
    if not resource:
        if lang:
            resource = Resource.get(resource_name + ':' + lang)
        if not resource:
            resource = Resource.get(resource_name)
        if resource:
            LOCALIZED_CACHE.put(cache_key, resource, resource.cache_seconds)
    return resource

# TODO(kpy): Instead of taking **vars directly, take a callback and call it
# to obtain **vars only when the template actually needs to be rendered.
def get_rendered(resource_name, lang, extra_key=None, cache_seconds=1, **vars):
    """Gets the rendered content of a Resource from the cache or the datastore.
    If resource_name is 'foo.html', this looks for a Resource named 'foo.html'
    to serve as a plain file, then a Resource named 'foo.html.template' to
    render as a template.  Returns None if nothing suitable is found.
    The cache is keyed on resource_name, lang, and extra_key (use extra_key
    to capture any additional dependencies on the values in **vars)."""
    cache_key = (resource_name, lang, extra_key)
    content = RENDERED_CACHE.get(cache_key)
    if content is None:
        resource = get_localized(resource_name, lang)
        if resource:  # a plain file is available
            return resource.content  # already cached, no need to cache again
        resource = get_localized(resource_name + '.template', lang)
        if resource:  # a template is available
            content = render_with_lang(resource.get_template(), vars, lang)
            RENDERED_CACHE.put(cache_key, content, cache_seconds)
    return content

def render_with_lang(template, vars, lang):
    """Renders a template in a particular language.  Use this to enforce that
    Django's idea of the current language matches resources.py's caches."""
    import django.utils.translation
    original_lang = django.utils.translation.get_language()
    try:
        django.utils.translation.activate(lang)
        return template.render(webapp.template.Context(vars))
    finally:
        django.utils.translation.activate(original_lang)
