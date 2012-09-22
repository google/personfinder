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
import cgi
import datetime
import mimetypes

import config
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
img { margin: 12px 0; border: 1px solid #eee; }
.editable .hide-when-editable { display: none; }
.readonly .hide-when-readonly { display: none; }

table { margin: 12px; border: 1px solid #ccc; }
tr { vertical-align: baseline; }
th, td { text-align: left; padding: 3px 10px; min-width: 5em; }
th { border-bottom: 1px solid #ccc; }
.active td { background: #afa; }
#show-unaltered { margin-left: 1em; font-weight: normal; color: #aaa; }

.warning { color: #a00; }
a.bundle { color: #06c; }
a.resource { color: #06c; }
a.file { color: #aaa; }
</style>
'''

def html(s):
    """Converts plain text to HTML."""
    try:
        s = s.decode('utf-8')  # for textarea editing, we need Unicode
    except:
        s = s.decode('latin-1')  # in case the content was uploaded binary data
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def format_datetime(dt):
    """Formats a datetime object for display in a directory listing."""
    now = datetime.datetime.utcnow()
    delta = now - dt
    if delta < datetime.timedelta(days=1):
        if delta.seconds < 3600:
            return '%d min ago' % int(delta.seconds / 60)
        return '%.1f h ago' % (delta.seconds / 3600.0)
    else:
        return '%04d-%02d-%02d %02d:%02d UTC' % (
            dt.year, dt.month, dt.day, dt.hour, dt.minute)

def put_bundle(new_bundle_name, original_bundle_name=None):
    """Puts a new ResourceBundle, optionally copying from another bundle."""
    new_bundle = ResourceBundle(key_name=new_bundle_name)
    entities = [new_bundle]
    if original_bundle_name:
        original_bundle = ResourceBundle.get_by_key_name(original_bundle_name)
        original_resources = Resource.all().ancestor(original_bundle)
        entities += [Resource(parent=new_bundle,
                              key_name=resource.key().name(),
                              cache_seconds=resource.cache_seconds,
                              content=resource.content)
                     for resource in original_resources]
    db.put(entities)

def put_resource(bundle_name, key_name, **kwargs):
    """Puts a Resource in the datastore under the specified ResourceBundle."""
    bundle = ResourceBundle(key_name=bundle_name)
    Resource(parent=bundle, key_name=key_name, **kwargs).put()

def format_content_html(content, name, editable):
    """Formats HTML to show a Resource's content, optionally for editing."""
    type = mimetypes.guess_type(name)[0] or 'text/plain'
    if name.endswith('.template') or type.startswith('text/'):
        return '<textarea name="content" cols=80 rows=40 %s>%s</textarea>' % (
            not editable and 'readonly' or '', html(content))
    content_html = '%s data, %d bytes' % (type, len(content))
    if type.startswith('image/'):
        content_html += '<br><img src="data:%s;base64,%s">' % (
            type, base64.encodestring(content))
    return content_html


class Handler(utils.BaseHandler):
    """A page that lets app administrators create resource bundles, create
    and edit resources, and preview bundles before making them default."""

    # Resources apply to all repositories.
    repo_required = False

    def get_admin_url(self, bundle_name=None, name=None, lang=None, **params):
        """Constructs a parameterized URL to this page."""
        return self.get_url('admin/resources',
                            resource_bundle=bundle_name,
                            resource_name=name,
                            resource_lang=lang,
                            **params)

    def format_nav_html(self, bundle_name, name, lang):
        """Formats the breadcrumb navigation bar."""
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
        self.handle(self.params.operation)

    def post(self):
        self.handle(self.params.operation)

    def handle(self, operation):
        """Handles both GET and POST requests.  POST requests include an
        'operation' param describing what the user is trying to change."""
        bundle_name = self.params.resource_bundle or ''
        name = self.params.resource_name or ''
        lang = self.params.resource_lang or ''
        key_name = name + (lang and ':' + lang)
        editable = (bundle_name != self.env.default_resource_bundle)
        if not ResourceBundle.get_by_key_name(self.env.default_resource_bundle):
            ResourceBundle(key_name=self.env.default_resource_bundle).put()

        if operation == 'set_preview':
            # Set the resource_bundle cookie.  This causes all pages to render
            # using the selected bundle (see main.py).  We use a cookie so that
            # it's possible to preview PF as embedded on external sites.
            self.response.headers['Set-Cookie'] = \
                'resource_bundle=%s; path=/' % bundle_name
            return self.redirect(self.get_admin_url())

        if operation == 'set_default':
            # Set the default resource bundle.
            config.set(default_resource_bundle=
                       self.params.resource_bundle_default)
            return self.redirect(self.get_admin_url())

        if operation == 'add_bundle' and editable:
            # Add a new bundle, optionally copying from an existing bundle.
            put_bundle(bundle_name, self.params.resource_bundle_original)
            return self.redirect(self.get_admin_url(bundle_name))

        if operation == 'add_resource' and editable:
            # Go to the edit page for a new resource (don't create until save).
            return self.redirect(self.get_admin_url(bundle_name, name, lang))

        if operation == 'delete_resource' and editable:
            # Delete a resource.
            resource = Resource.get(key_name, bundle_name)
            if resource:
                resource.delete()
            return self.redirect(self.get_admin_url(bundle_name))

        if operation == 'put_resource' and editable:
            # Store the content of a resource.
            if isinstance(self.request.POST.get('file'), cgi.FieldStorage):
                content = self.request.get('file')  # uploaded file content
            elif 'content' in self.request.POST:  # edited text
                content = self.request.get('content').encode('utf-8')
            else:  # modify cache_seconds but leave content unchanged
                resource = Resource.get(key_name, bundle_name)
                content = resource and resource.content or ''
            put_resource(bundle_name, key_name, content=content,
                         cache_seconds=self.params.cache_seconds)
            return self.redirect(self.get_admin_url(bundle_name))

        if not operation:
            self.write(PREFACE + self.format_nav_html(bundle_name, name, lang))
            if bundle_name and name:
                self.show_resource(bundle_name, key_name, name, lang, editable)
            elif bundle_name:
                self.list_resources(bundle_name, editable)
            else:
                self.list_bundles()

    def show_resource(self, bundle_name, key_name, name, lang, editable):
        """Displays a single resource, optionally for editing."""
        resource = Resource.get(key_name, bundle_name) or Resource()
        content = resource.content or ''
        self.write('''
<form method="post" class="%(class)s" enctype="multipart/form-data">
  <input type="hidden" name="operation" value="put_resource">
  <input type="hidden" name="resource_bundle" value="%(bundle_name)s">
  <input type="hidden" name="resource_name" value="%(name)s">
  <input type="hidden" name="resource_lang" value="%(lang)s">
  <table cellpadding=0 cellspacing=0>
    <tr>
      <td class="warning hide-when-editable">
        This bundle cannot be edited while it is set as default.
      </td>
    </tr>
    <tr><td colspan=2>%(content_html)s</td></tr>
    <tr>
      <td style="position: relative">
        <button style="position: absolute">Replace with a file</button>
        <input type="file" name="file" class="hide-when-readonly"
            onchange="document.forms[0].submit()"
            style="position: absolute; opacity: 0; z-index: 1">
      </td>
      <td style="text-align: right">
        Cache seconds: <input %(maybe_readonly)s size=4
            name="cache_seconds" value="%(cache_seconds).1f">
      </td>
    </tr>
    <tr class="hide-when-readonly">
      <td>
        <button onclick="delete_resource()">Delete resource</button>
      </td>
      <td style="text-align: right">
        <input type="submit" name="save_content" value="Save resource">
      </td>
    </tr>
  </table>
</form>
<script>
function delete_resource() {
  if (confirm('Really delete %(name)s?')) {
    document.forms[0].operation.value = 'delete_resource';
    document.forms[0].submit();
  }
}
</script>''' % {'class': editable and 'editable' or 'readonly',
                'bundle_name': bundle_name,
                'name': name,
                'lang': lang,
                'content_html': format_content_html(content, name, editable),
                'cache_seconds': resource.cache_seconds,
                'maybe_readonly': not editable and 'readonly' or ''})

    def list_resources(self, bundle_name, editable):
        """Displays a list of the resources in a bundle."""
        bundle = ResourceBundle.get_by_key_name(bundle_name)
        editable_class = editable and 'editable' or 'readonly'

        langs_by_name = {}  # Group language variants of each resource together.
        for filename in Resource.list_files():
            name, lang = (filename.rsplit(':', 1) + [None])[:2]
            langs_by_name.setdefault(name, {})[lang] = 'file'
        for resource_name in bundle.list_resources():
            name, lang = (resource_name.rsplit(':', 1) + [None])[:2]
            langs_by_name.setdefault(name, {})[lang] = 'resource'

        rows = []  # Each row shows one Resource and its localized variants.
        for name in sorted(langs_by_name):
            sources_by_lang = langs_by_name[name]
            altered = 'resource' in sources_by_lang.values()
            generic = '<a class="%s" href="%s">%s</a>' % (
                sources_by_lang.pop(None, 'missing'),
                self.get_admin_url(bundle_name, name), html(name))
            variants = ['<a class="%s" href="%s">%s</a>' % (
                sources_by_lang[lang],
                self.get_admin_url(bundle_name, name, lang), html(lang))
                for lang in sorted(sources_by_lang)]
            rows.append('''
<tr class="%(altered)s">
  <td>%(generic)s</td>
  <td>%(variants)s
    <form method="post" class="%(class)s">
      <input type="hidden" name="operation" value="add_resource">
      <input type="hidden" name="resource_name" value="%(name)s">
      <input name="resource_lang" size=3 class="hide-when-readonly"
          placeholder="lang">
      <input type="submit" value="Add" class="hide-when-readonly">
    </form>
  </td>
</tr>''' % {'altered': altered and 'altered' or 'unaltered',
            'generic': generic,
            'variants': ', '.join(variants),
            'class': editable_class,
            'name': name})

        self.write('''
<table cellpadding=0 cellspacing=0>
<tr><th>
  Resource name
  <span id="show-unaltered">
    <input id="show-unaltered-checkbox" type="checkbox"
        onchange="show_unaltered(this.checked)">
    <label for="show-unaltered-checkbox">Show unaltered files</label>
  </span>
</th><th>Localized variants</th></tr>
<tr class="add"><td>
  <form method="post" class="%(class)s">
    <input type="hidden" name="operation" value="add_resource">
    <input name="resource_name" size="36" class="hide-when-readonly"
        placeholder="resource filename">
    <input type="submit" value="Add" class="hide-when-readonly">
    <div class="warning hide-when-editable">
      This bundle cannot be edited while it is set as default.
    </div>
  </form>
</td><td></td></tr>
%(rows)s
</table>
<script>
function show_unaltered(show) {
  var rows = document.getElementsByClassName('unaltered');
  for (var r = 0; r < rows.length; r++) {
    rows[r].style.display = show ? '' : 'none';
  }
}
show_unaltered(false);
</script>
<form method="post" action="%(action)s">
  <input type="hidden" name="operation" value="add_bundle">
  <input type="hidden" name="resource_bundle_original" value="%(bundle_name)s">
  <table cellpadding=0 cellspacing=0>
    <tr><td>
      Copy all these resources to another bundle:
      <input name="resource_bundle" size="18"
          placeholder="bundle name">
      <input type="submit" value="Copy">
    </td></tr>
  </table>
</form>''' % {'class': editable_class,
              'rows': ''.join(rows),
              'action': self.get_admin_url(),
              'bundle_name': bundle_name})

    def list_bundles(self):
        """Displays a list of all the resource bundles."""
        bundles = list(ResourceBundle.all().order('-created'))
        rows = []
        for bundle in bundles:
            bundle_name = bundle.key().name()
            bundle_name_html = html(bundle_name)
            is_default = bundle_name == self.env.default_resource_bundle
            is_in_preview = bundle_name == self.env.resource_bundle
            if is_default:
                bundle_name_html = '<b>%s</b> (default)' % bundle_name_html
            elif is_in_preview:
                bundle_name_html += ' (in preview)'
            rows.append('''
<tr class="%(class)s">
  <td><a class="bundle" href="%(link)s">%(bundle_name_html)s</a></td>
  <td>%(created)s</td>
  <td><a href="%(preview)s"><input type="button" value="Preview"></a></td>
  <td><input type="radio" name="resource_bundle_default" value="%(bundle_name)s"
      %(default_checked)s></td>
</tr>''' % {
    'class': is_in_preview and 'active' or '',
    'link': self.get_admin_url(bundle_name),
    'bundle_name': bundle_name,
    'bundle_name_html': bundle_name_html,
    'default_checked': is_default and 'checked' or '',
    'created': format_datetime(bundle.created),
    'preview': self.get_admin_url(bundle_name, operation='set_preview')})

        self.write('''
<form method="post">
  <input type="hidden" name="operation" value="set_default">
  <table cellpadding=0 cellspacing=0>
    <tr><th>Bundle name</th><th>Created</th><th>Preview</th><th>Default</th></tr>
    <tr class="add"><td>
      <form method="post">
        <input type="hidden" name="operation" value="add_bundle">
        <input name="resource_bundle" size="18" placeholder="bundle name">
        <input type="submit" value="Add">
      </form>
    </td><td></td><td>
      <a href="%(reset)s"><input type="button" value="Reset to default view"></a>
    </td><td>
      <input type="submit" value="Set to default">
    </td></tr>
    %(rows)s
  </table>
</form>''' % {'reset': self.get_admin_url(operation='set_preview'),
               'rows': ''.join(rows)})
