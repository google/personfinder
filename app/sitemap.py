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

import logging
import requests
import requests_toolbelt.adapters.appengine
import time
import urllib

from datetime import datetime, timedelta
from google.appengine.api import taskqueue

import config
import const
from model import Repo
from utils import BaseHandler


# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
# TODO(nworden): see if we should condition this on the runtime (Python 2 vs. 3)
requests_toolbelt.adapters.appengine.monkeypatch()


class SiteMap(BaseHandler):

    repo_required = False

    def get(self):
        langs = const.LANGUAGE_ENDONYMS.keys()
        urlpaths = []
        # Include the root/global homepage.
        urlpaths.append({lang: '?lang=%s' % lang for lang in langs})
        # Include the repo homepages.
        for repo in Repo.list_launched():
            urlpaths.append({
                lang: '%s?lang=%s' % (repo, lang) for lang in langs})
        self.render('sitemap.xml', urlpaths=urlpaths)


# TODO(nworden): move this under a /tasks URL for consistency
class SiteMapPing(BaseHandler):
    """Pings the index server."""
    _INDEXER_MAP = {
        'bing': 'https://www.bing.com/ping?sitemap=%s',
        'google': 'https://www.google.com/ping?sitemap=%s',
    }

    _GET_PARAM_SEARCH_ENGINE = 'search_engine'

    repo_required = False

    # App Engine issues HTTP requests to tasks.
    https_required = False

    @staticmethod
    def add_ping_tasks():
        for search_engine in SiteMapPing._INDEXER_MAP:
            name = 'sitemapping-%s-%s' % (search_engine, int(time.time()*1000))
            taskqueue.add(
                name=name, method='GET', url='/global/sitemap/ping',
                params={SiteMapPing._GET_PARAM_SEARCH_ENGINE: search_engine})

    def get(self):
        if not config.get('ping_sitemap_indexers'):
            logging.info('Skipping sitemap ping because it\'s disabled.')
            return
        search_engine = self.request.get(SiteMapPing._GET_PARAM_SEARCH_ENGINE)
        if not search_engine:
            self.error(500)
        if not self._ping_indexer(search_engine):
            self.error(500)

    def _ping_indexer(self, search_engine):
        """Pings the server with sitemap updates; returns True if all succeed"""
        sitemap_url = 'https://%s/global/sitemap' % self.env.netloc
        ping_url = self._INDEXER_MAP[search_engine] % urllib.quote(sitemap_url)
        response = requests.get(ping_url)
        if response.status_code == 200:
            return True
        else:
            #TODO(nworden): Retry or email konbit-personfinder on failure.
            logging.error('Received %d pinging %s',
                          response.status_code, ping_url)
            return False
