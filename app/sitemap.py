#!/usr/bin/python2.7
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

"""Exports the URLs of all person entries to a sitemap.xml file."""

__author__ = 'jocatalano@google.com (Joe Catalano) and many other Googlers'

import logging

from datetime import datetime, timedelta
from google.appengine.api import urlfetch
import const
from model import Repo


class SiteMap(BaseHandler):

    repo_required = False

    def get(self):
        langs = const.LANGUAGE_ENDONYMS.keys()
        urlpaths = []
        urlpaths.append({lang: '?lang=%s' % lang for lang in langs})
        for repo in Repo.list_launched():
            urlpaths.append({
                lang: '%s?lang=%s' % (repo, lang) for lang in langs})
        self.render('sitemap.xml', urlpaths=urlpaths)


class SiteMapPing(BaseHandler):
    """Pings the index server."""
    _INDEXER_MAP = {'google': 'http://www.google.com/ping?sitemap=%s'}

    def get(self):
        search_engine = self.request.get('search_engine')
        if not search_engine:
            self.error(500)
        if not self.ping_indexer(search_engine):
            self.error(500)

    def ping_indexer(self, search_engine):
        """Pings the server with sitemap updates; returns True if all succeed"""
        sitemap_url = 'https://%s/sitemap' % self.env.netloc
        ping_url = self._INDEXER_MAP[search_engine] % urlencode(sitemap_url)
        try:
            response = urlfetch.fetch(url=ping_url, method=urlfetch.GET)
            if response.status_code == 200:
                return True
            else:
                #TODO(nworden): Retry or email konbit-personfinder on failure.
                logging.error('Received %d pinging %s'
                              response.status_code, ping_url)
                return False
