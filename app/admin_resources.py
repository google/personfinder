#!/usr/bin/python2.5
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

from google.appengine.ext import db
import base64
import datetime
import mimetypes

import const
from resources import Resource, ResourceBundle
import utils

# Because this handler is used to administer resources such as templates and
# stylesheets, nothing in this handler depends on those resources. 

PREFACE = '''
<style>
body, table, th, td, input { font-family: arial; font-size: 13px; }
body, form, input { margin: 0; padding: 0; }

.nav { padding: 6px 12px; background: #cdf; }
a { text-decoration: none; color: #06c; }
a.sel { color: #000; font-weight: bold; }
a:hover { text-decoration: underline; }

form { display: inline; }
textarea { font-family: courier, courier new, monospace; font-size: 12px; }
img { margin: 12px; }

table { margin: 12px; border: 1px solid #ccc; }
tr { vertical-align: baseline; }
th, td { text-align: left; padding: 3px 6px; min-width: 10em; }
th, .add td { border-bottom: 1px solid #ccc; }
.active td { background: #afa; }

.warning { color: #a00; }
a.bundle { color: #06c; }
a.resource { color: #06c; }
a.file { color: #666; }
</style>
'''

def html(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def format_datetime(dt):
    now = datetime.datetime.utcnow()
    delta = now - dt
    if delta < datetime.timedelta(days=1):
        if delta.seconds < 3600:
            return '%d min ago' % int(delta.seconds / 60)
        return '%.1f h ago' % (delta.seconds / 3600.0)
    else:
        return '%04d-%02d-%02d %02d:%02d UTC' % (
            dt.year, dt.month, dt.day, dt.hour, dt.minute)


class Handler(utils.BaseHandler):
    """A page that lets app administrators create resource bundles, create
    and edit resources, and preview bundles before making them default."""

    # Resources apply to all repositories.
    repo_required = False

    def get_admin_url(self, bundle_name=None, name=None, lang=None, **params):
        return self.get_url('admin/resources',
                            resource_bundle=bundle_name,
                            resource_name=name,
                            resource_lang=lang,
                            **params)

    def format_nav_html(self, bundle_name, name, lang):
        crumbs = [('All bundles', ())]
        if bundle_name:
            crumbs.append(('Bundle: %s' % bundle_name, (bundle_name,)))
        if bundle_name and name:
            crumbs.append(('Resource: %s' % name, (bundle_name, name)))
        if bundle_name and name and lang:
            anchor = lang + ': ' + const.LANGUAGE_EXONYMS.get(lang, '?')
            crumbs.append((anchor, (bundle_name, name, lang)))
        last = crumbs[-1][1]
        return '<div class="nav">%s</div>' % (' &gt; '.join(
            '<a class="%s" href="%s">%s</a>' %
            (args == last and 'sel', self.get_admin_url(*args), html(anchor))
            for anchor, args in crumbs))

    def get(self):
        self.handle(None)

    def post(self):
        self.handle(self.params.operation)

    def handle(self, operation):
        bundle_name = self.params.resource_bundle or ''
        name = self.params.resource_name or ''
        lang = self.params.resource_lang or ''
        key_name = name + (lang and ':' + lang)
        editable = (bundle_name != self.env.default_resource_bundle)
        nav_html = self.format_nav_html(bundle_name, name, lang)
        
        if self.params.resource_set_preview:
            # Set the preview bundle cookie.
            self.response.headers['Set-Cookie'] = \
                'resource_bundle=%s; path=/' % bundle_name
            return self.redirect(self.get_admin_url())

        if operation == 'add_bundle':
            # Add a new resource bundle.
            new_bundle_name = self.params.resource_bundle_new
            new_bundle = ResourceBundle(key_name=new_bundle_name)
            entities = [new_bundle]
            if bundle_name:
                old_bundle = ResourceBundle.get_by_key_name(bundle_name)
                old_resources = Resource.all().ancestor(old_bundle)
                entities.extend([Resource(parent=new_bundle,
                                          key_name=resource.key().name(),
                                          cache_seconds=resource.cache_seconds,
                                          content=resource.content)
                                 for resource in old_resources])
            db.put(entities)
            return self.redirect(self.get_admin_url(new_bundle_name))

        if operation == 'add_resource' and editable:
            # Add a new empty resource.
            bundle = ResourceBundle.get_by_key_name(bundle_name)
            Resource(parent=bundle, key_name=key_name, content='').put()
            return self.redirect(self.get_admin_url(bundle_name, name, lang))

        if operation == 'put_resource' and editable:
            # Store the content of a resource.
            bundle = ResourceBundle.get_by_key_name(bundle_name)
            try:
                cache_seconds = float(self.request.get('cache_seconds'))
            except:
                cache_seconds = 1.0
            content = (self.request.get('file') or
                       self.request.get('content').encode('utf-8'))
            Resource(parent=bundle,
                     key_name=key_name,
                     cache_seconds=cache_seconds,
                     content=content).put()
            return self.redirect(self.get_admin_url(bundle_name, name, lang))

        if bundle_name and name:
            # Display a single resource for editing.
            resource = Resource.get(name + (lang and ':' + lang), bundle_name)
            content = resource.content or ''
            if name.endswith('.template'):
                type = 'text/html'
            else:
                type = mimetypes.guess_type(name)[0] or 'text/plain'

            if type.startswith('text/'):
                content_html = '''
<textarea name="content" cols=80 rows=40 %s>%s</textarea>
''' % (editable and ' ' or 'readonly', html(content))
            else:
                content_html = '%s data, %d bytes' % (type, len(content))
            if type.startswith('image/'):
                content_html += '<br><img src="data:%s;base64,%s">' % (
                    type, base64.encodestring(content))

            if editable:
                self.write(PREFACE + nav_html + '''
<form method="post" enctype="multipart/form-data">
<input name="operation" value="put_resource" type="hidden">
<input name="resource_bundle" value="%s" type="hidden">
<input name="resource_name" value="%s" type="hidden">
<input name="resource_lang" value="%s" type="hidden">
<table cellpadding=0 cellspacing=0>
  <tr><td colspan=2>%s</td></tr>
  <tr>
    <td><input type="file" name="file"></td>
    <td style="text-align: right">
      Cache seconds: <input name="cache_seconds" size=4 value="%.1f">
    </td>
  </tr>
  <tr>
    <td><input type="submit" name="upload_file" value="Upload file"></td>
    <td style="text-align: right">
      <input type="submit" name="save_content" value="Save content">
    </td>
  </tr>
</table></form>''' % (
    bundle_name, name, lang, content_html, resource.cache_seconds))

            else:
                self.write(PREFACE + nav_html + '''
<table cellpadding=0 cellspacing=0>
  <tr>
    <td class="warning">
      This bundle cannot be edited while it is set as default.
    </td>
  </tr>
  <tr><td colspan=2>%s</td></tr>
  <tr>
      <td style="text-align: right">
      Cache seconds: <input name="cache_seconds" size=4 value="%.1f" readonly>
    </td>
  </tr>
</table>''' % (content_html, resource.cache_seconds))

        elif self.params.resource_bundle:
            # List the resources in a given bundle.
            bundle = ResourceBundle.get_by_key_name(bundle_name)
            langs_by_name = {}
            for filename in Resource.list_files():
                name, lang = (filename.rsplit(':', 1) + [None])[:2]
                langs_by_name.setdefault(name, {})[lang] = 'file'
            for resource_name in bundle.list_resources():
                name, lang = (resource_name.rsplit(':', 1) + [None])[:2]
                langs_by_name.setdefault(name, {})[lang] = 'resource'

            rows = []
            for name in sorted(langs_by_name):
                langs = langs_by_name[name]
                if None in langs:
                    generic = '<a class="%s" href="%s">%s</a>' % (
                        langs[None],
                        html(self.get_admin_url(bundle_name, name)),
                        html(name))
                variants = ['<a class="%s" href="%s">%s</a>' % (
                    langs[lang],
                    html(self.get_admin_url(bundle_name, name, lang)),
                    html(lang))
                    for lang in sorted(langs) if lang]
                if editable:
                    variants.append('''
<form method="post">
  <input type="hidden" name="operation" value="add_resource">
  <input type="hidden" name="resource_bundle" value="%s">
  <input type="hidden" name="resource_name" value="%s">
  <input name="resource_lang" size=3>
</form>''' % (bundle_name, name))
                rows.append('<tr><td>%s</td><td>%s</td></tr>\n' %
                            (generic, ', '.join(variants)))

            add_html = editable and '''
  <td>
    <input name="resource_name" size="36"><input value="Add" type="submit">
  </td>
''' or '''
  <td class="warning">
    This bundle cannot be edited while it is set as default.
  </td>
'''
            self.write(PREFACE + nav_html + '''
<form method="post">
  <input name="operation" value="add_resource" type="hidden">
  <input name="resource_bundle" value="%s" type="hidden">
  <table cellpadding=0 cellspacing=0>
    <tr><th>Resource name</th><th>Localized variants</th></tr>
    <tr class="add">
      %s
      <td></td>
    </tr>
    %s
  </table>
</form>
<form method="post">
  <input name="operation" value="add_bundle" type="hidden">
  <input name="resource_bundle" value="%s" type="hidden">
  <table cellpadding=0 cellspacing=0>
    <tr><td>
      Copy this bundle to:
      <input name="resource_bundle_new" size="18">
      <input type="submit" value="Copy">
    </td></tr>
  </table>
</form>
''' % (bundle_name, add_html, ''.join(rows), bundle_name))

        else:
            # List the available resource bundles.
            bundles = list(ResourceBundle.all().order('-created'))
            rows = []
            for bundle in bundles:
                bundle_name_html = name = bundle.key().name()
                if name == self.env.default_resource_bundle:
                    bundle_name_html = '<b>%s</b> (default)' % name
                rows.append('''
<tr class="%s">
  <td><a class="bundle" href="%s">%s</a></td>
  <td>%s</td>
  <td><a href="%s"><input type="button" value="Preview"></a></td>
</tr>''' % (
    (name == self.env.resource_bundle) and 'active' or '',
    html(self.get_admin_url(name)),
    bundle_name_html,
    format_datetime(bundle.created),
    self.get_admin_url(name, resource_set_preview='yes')))
            self.write(PREFACE + nav_html + '''
<table cellpadding=0 cellspacing=0>
  <tr><th>Bundle name</th><th>Created</th><th>Preview</th></tr>
  <tr class="add"><td>
    <form method="post">
    <input name="operation" value="add_bundle" type="hidden">
    <input name="resource_bundle_new" size="18">
    <input value="Add" type="submit"></form></td><td></td>
    <td><a href="%s">
      <input type="button" value="Reset to default view">
    </a></td>
  </tr>
%s</table>
''' % (html(self.get_admin_url(resource_set_preview='yes')), ''.join(rows)))

