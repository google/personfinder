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

"""Exports the URLs of all person entries to a sitemap.xml file."""

__author__ = 'jocatalano@google.com (Joe Catalano) and many other Googlers'

import logging

from datetime import datetime, timedelta
from google.appengine.api import urlfetch
from model import *
from time import *
from utils import *

def _compute_max_shard_index(now, sitemap_epoch, shard_size_seconds):
    delta = now - sitemap_epoch
    delta_seconds = delta.days * 24 * 60 * 60 + delta.seconds
    return delta_seconds / shard_size_seconds

def _get_static_sitemap_info(repo):
    infos = StaticSiteMapInfo.all().fetch(2)
    if len(infos) > 1:
        logging.error("There should be at most 1 StaticSiteMapInfo record!")
        return None
    elif len(infos) == 1:
        return infos[0]
    else:
        # Set the sitemap generation time according to the time of the first
        # record with a timestamp.    This will make the other stuff work
        # correctly in case there is no static sitemap.
        query = Person.all_in_repo(repo)
        query = query.filter('last_modified != ', None)
        first_updated_person = query.order('last_modified').get()
        if not first_updated_person:
            # No records; set the time to now.
            time = get_utcnow()
        else:
            # Set the time to just before the first person was entered.
            time = first_updated_person.last_modified - timedelta(seconds=1)
        info = StaticSiteMapInfo(static_sitemaps_generation_time=time)
        db.put(info)
        return info

class SiteMap(BaseHandler):
    _FETCH_LIMIT = 1000

    def get(self):
        requested_shard_index = self.request.get('shard_index')
        sitemap_info = _get_static_sitemap_info(self.repo)
        shard_size_seconds = sitemap_info.shard_size_seconds
        then = sitemap_info.static_sitemaps_generation_time

        if not requested_shard_index:
            max_shard_index = _compute_max_shard_index(
                get_utcnow(), then, shard_size_seconds)
            shards = []
            for shard_index in range(max_shard_index + 1):
                shard = {}
                shard['index'] = shard_index
                offset_seconds = shard_size_seconds * (shard_index + 1)
                shard['lastmod'] = format_sitemaps_datetime(
                    then + timedelta(seconds=offset_seconds))
                shards.append(shard)
            self.render('templates/sitemap-index.xml', shards=shards,
                        static_lastmod=format_sitemaps_datetime(then),
                        static_map_files=sitemap_info.static_sitemaps)
        else:
            shard_index = int(requested_shard_index)
            assert 0 <= shard_index < 50000    #TODO: nicer error (400 maybe)
            persons = []
            time_lower = \
                then + timedelta(seconds=shard_size_seconds * shard_index)
            time_upper = time_lower + timedelta(seconds=shard_size_seconds)
            query = Person.all_in_repo(self.repo
                         ).filter('last_modified >', time_lower
                         ).filter('last_modified <=', time_upper
                         ).order('last_modified')
            fetched_persons = query.fetch(self._FETCH_LIMIT)
            while fetched_persons:
                persons.extend(fetched_persons)
                last_value = fetched_persons[-1].last_modified
                query = Person.all_in_repo(self.repo
                             ).filter('last_modified >', last_value
                             ).filter('last_modified <=', time_upper
                             ).order('last_modified')
                fetched_persons = query.fetch(self._FETCH_LIMIT)
            urlinfos = [
                {'person_record_id': p.record_id,
                 'lastmod': format_sitemaps_datetime(p.last_modified)}
                for p in persons]
            self.render('templates/sitemap.xml', urlinfos=urlinfos)

class SiteMapPing(BaseHandler):
    """Pings the index server with sitemap files that are new since last ping"""
    _INDEXER_MAP = {'google': 'http://www.google.com/webmasters/tools/ping?',
                    'not-specified': ''}

    def get(self):
        search_engine = self.request.get('search_engine')
        if not search_engine:
            search_engine = 'not-specified'

        last_update_query = SiteMapPingStatus.all()
        last_update_query.filter('search_engine = ', search_engine)
        last_update_status = last_update_query.fetch(1)
        if not last_update_status:
            last_shard = -1
            last_update_status = SiteMapPingStatus(search_engine=search_engine)
        else:
            last_update_status = last_update_status[0]
            last_shard = last_update_status.shard_index

        sitemap_info = _get_static_sitemap_info(self.repo)
        generation_time = sitemap_info.static_sitemaps_generation_time
        shard_size_seconds = sitemap_info.shard_size_seconds

        max_shard_index = _compute_max_shard_index(
            get_utcnow(), generation_time, shard_size_seconds)
        if not self.ping_indexer(
            last_shard+1, max_shard_index, search_engine, last_update_status):
            self.error(500)

    def ping_indexer(self, start_index, end_index, search_engine, status):
        """Pings the server with sitemap updates; returns True if all succeed"""
        try:
            for shard_index in range(start_index, end_index + 1):
                ping_url = self._INDEXER_MAP[search_engine]
                sitemap_url = 'http://%s/sitemap?shard_index=%s' % (
                    self.env.netloc, shard_index)
                ping_url = ping_url + urlencode({'sitemap': sitemap_url})
                response = urlfetch.fetch(url=ping_url, method=urlfetch.GET)
                if not response.status_code == 200:
                    #TODO(jocatalano): Retry or email haiticrisis on failure.
                    logging.error('Received %d pinging %s',
                                  response.status_code, ping_url)
                    return False
                else:
                    status.shard_index = shard_index
            return True
        finally:
            # Always update database to reflect how many the max shard that was
            # pinged particularly when a DeadlineExceededError is thrown
            db.put(status)
