# Copyright 2019 Google Inc.
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

"""The sitemap ping task."""

import django.http
import logging
import requests
import requests_toolbelt.adapters.appengine
import six.moves.urllib as urllib
import six.moves.urllib.parse as urlparse
import time

from google.appengine.api import taskqueue

import tasksmodule.base
import utils


# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
# TODO(nworden): see if we should condition this on the runtime (Python 2 vs. 3)
requests_toolbelt.adapters.appengine.monkeypatch()


_TASK_PARAM_SEARCH_ENGINE = 'search_engine'

_INDEXER_MAP = {
    'bing': 'https://www.bing.com/ping?sitemap=%s',
    'google': 'https://www.google.com/ping?sitemap=%s',
}


def add_ping_tasks():
    for search_engine in _INDEXER_MAP:
        name = 'sitemap_ping-%s-%s' % (search_engine, int(time.time()*1000))
        taskqueue.add(
            name=name, method='GET', url='/global/tasks/sitemap_ping',
            params={_TASK_PARAM_SEARCH_ENGINE: search_engine})


class SitemapPingTaskView(tasksmodule.base.TasksBaseView):
    """The sitemap ping handler."""

    ACTION_ID = 'tasks/sitemap_ping'

    def setup(self, request, *args, **kwargs):
        super(SitemapPingTaskView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            get_params={_TASK_PARAM_SEARCH_ENGINE: utils.strip})

    def get(self, request, *args, **kwargs):
        """Serves get requests.

        Args:
            request: Unused.
            *args: Unused.
            **kwargs: Unused.

        Returns:
            HttpResponse: A HTTP response with the admin statistics page.
        """
        del request, args, kwargs  # unused
        if not self.env.config.get('ping_sitemap_indexers'):
            logging.info('Skipping sitemap ping because it\'s disabled.')
            return django.http.HttpResponse(status=204)
        if not self.params.search_engine:
            return self.error(500)
        if self._ping_indexer(self.params.search_engine):
            return django.http.HttpResponse(status=200)
        else:
            return django.http.HttpResponse(status=500)

    def _ping_indexer(self, search_engine):
        # App Engine makes HTTP requests to tasks, so building a URL based on
        # the request will use HTTP instead of HTTPS, but we want to send search
        # engines HTTPS URLs.
        sitemap_url = self.build_absolute_uri('/global/sitemap')
        sitemap_url_parts = list(urlparse.urlparse(sitemap_url))
        sitemap_url_parts[0] = 'https'  # 0 is the index of the scheme part.
        sitemap_url = urlparse.urlunparse(sitemap_url_parts)
        ping_url = _INDEXER_MAP[search_engine] % urllib.parse.quote(sitemap_url)
        response = requests.get(ping_url)
        if response.status_code == 200:
            return True
        else:
            # TODO(nworden): Retry or email konbit-personfinder on failure.
            logging.error('Received %d pinging %s',
                          response.status_code, ping_url)
            return False
