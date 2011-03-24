#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'argent@google.com (Evan Anderson), nakajima@google.com(Takahiro Nakajima)'

import config
import datetime
import logging
import model
import os
import random
import re
import simplejson
import sys
import urllib
import utils
from google.appengine.api import urlfetch

SUBDOMAIN = 'japan'

def get_modified_rank(normalized_query, entries, i):
    if (entries[i]['last_name'] + entries[i]['first_name']
            == normalized_query or
        entries[i]['first_name'] + entries[i]['last_name']
            == normalized_query or
        entries[i]['last_name'] == normalized_query or
        entries[i]['first_name'] == normalized_query):
        nonexact_match = 0
    else:
        nonexact_match = 1
    return (nonexact_match, i)

def twiddle_rank(data):
    """Boost exact match."""
    query = data['query']
    entries = data['name_entries']
    normalized_query = re.sub(ur' |　', u'', query)
    twiddled_index = sorted(xrange(0, len(entries)),
        key=lambda i: get_modified_rank(normalized_query, entries, i))
    data['name_entries'] = [entries[i] for i in twiddled_index]

def select_balanced_path(path, backend_list,
                         fetch_timeout=1.0, total_timeout=5.0):
    """Attempt to fetch a url at path from one or more backends.

    Args:
        path: The url-path that should be fetched
        backend_list: A list of backend hosts from which content may be
                      fetched.  This may be iterated over several times
                      if needed.
        fetch_timeout: The time in seconds to allow one request to wait before
                       retrying.
        total_timeout: The total time in seconds to retry a request before
                       giving up.
    Returns:
        A urlfetch.Response object, or None if the timeout has been
        exceeded.
    """
    end_time = (
        datetime.datetime.now() + datetime.timedelta(seconds=total_timeout))
    shuffled_backend_list = backend_list[:]
    random.shuffle(shuffled_backend_list)
    for backend in shuffled_backend_list:
        if datetime.datetime.now() >= end_time:
            return None
        attempt_url = 'http://%s%s' % (backend, path)
        logging.info('Balancing to %s', attempt_url)
        try:
            page = urlfetch.fetch(attempt_url, deadline=fetch_timeout)
            logging.info('Status code: %d' % page.status_code)
            logging.debug('Content:\n%s' % page.content)
            if page.status_code == 200:
                return page
        except:
            logging.info('Failed to fetch %s: %s', attempt_url,
                         str(sys.exc_info()[1]))
    return None

def dict_to_person(d):
    """Convert a dictionary representing a person returned from a backend to a
    Person model instance."""
    # Convert unicode keys to string keys.
    d = dict([(key.encode('utf-8'), value) for key, value in d.iteritems()])
    d['source_date'] = utils.validate_datetime(d['source_date'])
    # FIXME(ryok): the backend is not returning entry_date.
    d['entry_date'] = datetime.datetime.now()
    record_id = '%s:%s' % (SUBDOMAIN, d['person_record_id'])
    return model.Person.create_clone(SUBDOMAIN, record_id, **d)

def search(query):
    # jp_full_text_search_backends is a comma separated list of full text search
    # backends.
    backends = config.get_for_subdomain(
        SUBDOMAIN, 'jp_full_text_search_backends', '').split(',')
    if not backends or not backends[0]:
        return None
    path = '/pf_access.cgi?query=' + urllib.quote_plus(query.encode('utf-8'))
    page = select_balanced_path(path, backends)
    if page:
        try:
            data = simplejson.loads(page.content)
        except simplejson.decoder.JSONDecodeError:
            return None
        if data['name_entries'] or data['all_entries']:
            twiddle_rank(data)
            entries = data['name_entries'] + data['all_entries']
            return [dict_to_person(e) for e in entries]
    return None
