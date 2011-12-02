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

__author__ = 'lschumacher@google.com (Lee Schumacher)'

import urlparse
import utils

"""Handle redirect from old-style urls with host or query based repo_names to
the new path based urls.
TODO(lschumacher): delete this after we no longer require legacy redirect.
"""

   
# copied from utils to avoid circularity:
def strip(string):
    # Trailing nulls appear in some strange character encodings like Shift-JIS.
    return string.strip().rstrip('\0')

def get_repo_name(handler):
    """Determines the repo_name of the request."""
    if handler.ignore_repo_name:
        return None

    # The 'repo_name' query parameter always overrides the hostname
    if strip(handler.request.get('repo_name', '')):
        return strip(handler.request.get('repo_name'))

    levels = handler.request.headers.get('Host', '').split('.')
    if levels[-2:] == ['appspot', 'com'] and len(levels) >= 4:
        # foo.person-finder.appspot.com -> repo_name 'foo'
        # bar.kpy.latest.person-finder.appspot.com -> repo_name 'bar'
        return levels[0]

def do_redirect(handler):
    """Return True when the request should be redirected."""
    return handler.config.missing_repo_name_redirect_enabled and \
        get_repo_name(handler)

def redirect(handler):
    repo_name = get_repo_name(handler)
    if not repo_name and handler.repo_name_required:
        return handler.error(400, 'No repo_name specified')
    scheme, netloc, path, params, query, _ = urlparse.urlparse(handler.request.url)
    params = utils.set_param(params, 'repo_name', None)
    host = utils.get_host(netloc)
    if path.startswith('/'):
        path = path[1:]
    path = '%s/%s' % (repo_name, path)
    url = urlparse.urlunparse((scheme, host, path, params, query, ''))
    return handler.redirect(url)

