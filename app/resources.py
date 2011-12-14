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

import datetime
import utils

from google.appengine.ext import db
from google.appengine.ext import webapp


# Requests for files and pages pass through four stages:
#   1. get_rendered(): decides whether to serve plain data or render a Template
#   2. get_compiled(): compiles template source code into a Template
#   3. get_localized(): selects the localized version of a Resource
#   4. Resource.get(): gets a Resource from the datastore or from a file
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
#   > get_localized('logo.jpg')
#     > Resource.get('logo.jpg:ru') -> None
#       > Resource.get_by_key_name('logo.jpg:ru') -> None
#       > Resource.load_from_file('logo.jpg:ru') -> None
#     > Resource.get('logo.jpg')
#       > Resource.get_by_key_name('logo.jpg') -> R1
#     > LOCALIZED_CACHE.put(('logo.jpg', 'ru'), R1)
#   > RENDERED_CACHE.put(('logo.jpg', 'ru'), R1.content)
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
#   > get_compiled('faq.html.template', 'ru')
#     > get_localized('faq.html.template', 'ru')
#       > Resource.get('faq.html.template:ru')
#         > Resource.get_by_key_name('faq.html.template:ru') -> R2
#       > LOCALIZED_CACHE.put(('faq.html.template', 'ru'), R2)
#     > webapp.Template(R2.content) -> T2  # compile the template
#     > COMPILED_CACHE.put(('faq.html.template', 'ru'), T2)
#   > T2.render(vars)  # T2 extends "base.html.template", so:
#     > TemplateLoader.load_template('base.html.template')
#       > get_compiled('base.html.template', 'ru')
#         > get_localized('base.html.template', 'ru')
#           > Resource.get('base.html.template:ru')
#             > Resource.get_by_key_name('base.html.template:ru') -> None
#             > Resource.load_from_file('base.html.template:ru') -> None
#           > Resource.get('base.html.template')
#             > Resource.get_by_key_name('base.html.template') -> None
#             > Resource.load_from_file('base.html.template') -> R3
#           > LOCALIZED_CACHE.put(('base.html.template', 'ru'), R3)
#         > webapp.Template(R3.content) -> T3
#         > COMPILED_CACHE.put(('base.html.template', 'ru'), T3)
#       > return T3
#     > return rendered_string
#   > RENDERED_CACHE.put(('faq.html', 'ru', 'utf8'), rendered_string)
# > self.response.out.write(rendered_string)
#
# Suppose the dynamic page '/<repo>/view' is now requested.  Assume that T3
# is still cached from the above request.  The expected sequence of calls is:
# 
# request for dynamic page, action='view', with an 'id' query parameter
# > view.Handler.get()
#   > model.Person.get_by_key_name(person_record_id)
#   > BaseHandler.render('view.html', first_name=..., ...)
#     > get_rendered('view.html', 'ru', ..., first_name=..., ...)
#       > get_localized('view.html', 'ru') -> None
#       > get_compiled('view.html.template', 'ru')
#         > get_localized('view.html.template', 'ru')
#           > Resource.get('view.html.template:ru') -> None
#           > Resource.get('view.html.template') -> None
#             > Resource.get_by_key_name('view.html.template') -> None
#             > Resource.load_from_file('view.html.template') -> R4
#           > LOCALIZED_CACHE.put(('view.template', 'ru'), R4)
#         > webapp.Template(R4.content) -> T4
#         > COMPILED_CACHE.put(('view.html.template', 'ru'), T4)
#       > T4.render(first_name=..., ...)  # T4 extends "base.html.template", so:
#         > TemplateLoader.load_template('base.html.template')
#           > get_compiled('base.html.template', 'ru')
#             > COMPILED_CACHE.get(('base.html.template', 'ru')) -> T3
#           > return T3
#         > return rendered_string
#       > return rendered_string  # don't cache
#     > self.response.out.write(rendered_string)


class RamCache:
    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache.clear()

    def put(self, key, value):
        self.cache[key] = (utils.get_utcnow(), value)

    def get(self, key, max_age):
        if max_age > 0 and key in self.cache:
            time, value = self.cache[key]
            if utils.get_utcnow() < time + datetime.timedelta(seconds=max_age):
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



LOCALIZED_CACHE = RamCache()  # contains Resource objects
COMPILED_CACHE = RamCache()  # contains Template objects
RENDERED_CACHE = RamCache()  # contains strings of rendered content


def clear_caches():
    LOCALIZED_CACHE.clear()
    COMPILED_CACHE.clear()
    RENDERED_CACHE.clear()


def get_localized(resource_name, lang, max_age=0.5):
    """Gets the best available localized version of a Resource from the cache,
    the datastore, or a file.  Returns None if nothing suitable is found."""
    cache_key = (resource_name, lang)
    result = LOCALIZED_CACHE.get(cache_key, max_age)
    if not result:
        if lang:
            result = Resource.get(resource_name + ':' + lang)
        if not result:
            result = Resource.get(resource_name)
        if result:
            LOCALIZED_CACHE.put(cache_key, result)
    return result


def get_compiled(resource_name, lang, max_age=0.5):
    """Gets a compiled Template object from the cache or by compiling a
    Resource from get_localized.  Returns None if nothing suitable is found."""
    cache_key = (resource_name, lang)
    result = COMPILED_CACHE.get(cache_key, max_age)
    if not result:
        resource = get_localized(resource_name, lang)
        if resource:
            content = resource.content.decode('utf-8')
            key_name = resource.key().name()
            result = webapp.template.Template(content, 'Resource', key_name)
        if result:
            COMPILED_CACHE.put(cache_key, result)
    return result


def get_rendered(resource_name, lang, extra_key=None, max_age=0, **vars):
    """Gets the rendered content of a Resource from the cache, or as a plain
    file from get_localized, or by rendering a template from get_compiled.
    If resource_name is 'foo.html', this looks for a Resource named 'foo.html'
    to serve as a plain file, then a Resource named 'foo.html.template' to
    render as a template.  Returns None if nothing suitable is found.
    The cache is keyed on resource_name, lang, and extra_key (use extra_key
    to capture any additional dependencies on the values in **vars)."""
    cache_key = (resource_name, lang, extra_key)
    result = RENDERED_CACHE.get(cache_key, max_age)
    if result is None:
        resource = get_localized(resource_name, lang)
        if resource:  # a plain file is available
            result = resource.content
        else:
            template = get_compiled(resource_name + '.template', lang)
            if template:  # a template is available
                result = template.render(webapp.template.Context(vars))
        if result is not None:
            RENDERED_CACHE.put(cache_key, result)
    return result
