#!/usr/bin/python2.5
# Copyright 2014 Google Inc.
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

import base64
import datetime
import hashlib
import logging
import re
import urllib

import simplejson

from google.appengine.api import urlfetch

import utils

class Handler(utils.BaseHandler):
    """Proxy to perform search with third-party search engine."""
    def get(self):
        if (self.params.search_engine_id >=
                len(self.config.third_party_search_engines or [])):
            self.response.set_status(500)
            self.write('search_engine_id is out of range')
            return
        query = self.params.query
        # TODO(ichikawa) Support query_type "tel".
        query_type = ''
        search_engine = self.config.third_party_search_engines[
            self.params.search_engine_id]
        if self.env.lang == search_engine['default_language']:
            lang = ''
        elif self.env.lang in search_engine['supported_languages']:
            lang = self.env.lang
        else:
            lang = 'en'
        time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        signature_source = (
            query + query_type + lang + time + search_engine['auth_key'])
        signature = hashlib.sha256(signature_source).hexdigest()
        params = {
            'q': query,
            't': query_type,
            'lang': lang,
            'time': time,
            'signature': signature,
        }
        url = '%s?%s' % (search_engine['api_url'], urllib.urlencode(params))
        if search_engine.get('basic_auth_user'):
            basic_auth_value = base64.encodestring('%s:%s' % (
                    search_engine['basic_auth_user'],
                    search_engine['basic_auth_password']))
            # Result of base64.encodestring can include '\n', but HTTP header
            # value must not include '\n'.
            basic_auth_value = re.sub('\n', '', basic_auth_value)
            headers = {'Authorization': 'Basic %s' % basic_auth_value}
        else:
            headers = {}
        logging.info('urlfetch.fetch(%r, headers=%r)' % (url, headers))
        response = urlfetch.fetch(url, headers=headers, deadline=60)
        if response.status_code == 200:
            self.response.headers['Content-Type'] = 'application/json'
            self.write(response.content)
        else:
            self.response.set_status(500)
            self.write('Bad HTTP status code: %d' % response.status_code)
