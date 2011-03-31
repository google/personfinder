#!/usr/bin/python2.5
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

import datetime
import logging
import random
import simplejson
import sys
import urllib

import indexing
import model
from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_errors


def fetch_with_load_balancing(urls, fetch_timeout=1.0, retry_timeout=5.0):
    """Attempt to fetch a content from one or more urls.

    Args:
        urls: A list of urls from which content may be fetched.  This may be
              iterated over several times if needed.
        fetch_timeout: The time in seconds to allow one request to wait before
                       retrying.
        retry_timeout: The total time in seconds to allow for all requests
                       before giving up.
    Returns:
        A urlfetch.Response object, or None if the timeout has been exceeded.
    """
    end_time = (
        datetime.datetime.now() + datetime.timedelta(seconds=retry_timeout))
    shuffled_urls = urls[:]
    random.shuffle(shuffled_urls)
    for url in shuffled_urls:
        if datetime.datetime.now() >= end_time:
            logging.info('Fetch retry timed out.')
            return None
        logging.debug('Balancing to %s', url)
        try:
            page = urlfetch.fetch(url, deadline=fetch_timeout)
            if page.status_code == 200:
                return page
            logging.info('Bad status code: %d' % page.status_code)
        except urlfetch_errors.Error, e:
            logging.info('Failed to fetch: %s', str(e))
    return None


def remove_non_name_matches(entries, query_obj):
    """Filter out Person entries if there is no overlap between names_prefixes
    and query_obj.query_words."""
    filtered_entries = []
    for entry in entries:
        for word in query_obj.query_words:
            if word in entry.names_prefixes:
                filtered_entries.append(entry)
                break
    return filtered_entries


def search(subdomain, query_obj, max_results, backends):
    """Search persons using external search backends.

    Args:
        subdomain: PF's subdomain from which the query was sent.
        query_obj: TextQuery instance representing the input query.
        max_results: Maximum number of entries to return.
        backends: List of backend IPs or hostnames to access.
    Returns:
        List of Persons that are returned from an external search backend (may
        be []), or None if backends return bad responses.
    """
    escaped_query = urllib.quote_plus(query_obj.query.encode('utf-8'))
    urls = [b.replace('%s', escaped_query) for b in backends]
    page = fetch_with_load_balancing(urls, fetch_timeout=0.9, retry_timeout=0.1)
    if not page:
        return None
    try:
        data = simplejson.loads(page.content)
    except:
        logging.warn('Fetched content is broken.')
        return None
    logging.debug('external_search.search fetched name: %d, all: %d' %
                  (len(data['name_entries']), len(data['all_entries'])))

    # The entries returned from backends may include ones that are already taken
    # down in the production repository.  We need to ensure those are not
    # included in the returned results.
    ids = data['name_entries'] + data['all_entries']
    if not ids:
        return []
    # TODO(ryok): Remove once the backends stop returning the old data format.
    if isinstance(ids[0], dict):
        ids = [d['person_record_id'] for d in ids]
    key_names = ['%s:%s' % (subdomain, id) for id in ids]
    persons = model.Person.get_by_key_name(key_names)
    address_match_begin = len(data['name_entries'])
    name_matches = [p for p in persons[:address_match_begin] if p]
    address_matches = [p for p in persons[address_match_begin:] if p]
    logging.debug('external_search.search matches name: %d, all: %d' %
                  (len(name_matches), len(address_matches)))

    name_matches.sort(indexing.CmpResults(query_obj))
    all_matches = name_matches
    if address_matches:
        address_matches = remove_non_name_matches(address_matches, query_obj)
        logging.debug('address_matches after remove_non_name_matches: %d' %
                      len(address_matches))
        address_matches.sort(indexing.CmpResults(query_obj))
        address_matches[0].address_match_begins = True
        all_matches += address_matches
    logging.debug('external_search.search matched: %d' % len(all_matches))
    return all_matches[:max_results]
