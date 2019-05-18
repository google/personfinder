# Copyright 2016 Google Inc.
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

"""A command line tool to perform load test of Person Finder.

Usage:

  - Write config.json like this:

    {
      "base_url": "http://my-person-finder.appspot.com",
      "repo": "loadtest1",
      "num_records": 100,
      "num_queries": 100,
      "create_record_qps": 10,
      "search_record_qps": 10,
      "num_threads": 100,
      "output_dir": "/tmp/load_test_result",
      "test_mode": false
    }

  - Run this command to perform load test to create person records:
    $ ./tools/load_test config.json create

  - Run this command to perform load test to search person records:
    $ ./tools/load_test config.json search

  - Each of the command above outputs something like this:

    Average request latency (sec):            3.815
    90%tile request latency (sec):            6.122
    Average interval between requests (sec):  0.100
    90%tile interval between requests (sec):  0.100
    
    http_status:
      200: 5 (100.0%)

    "Request latency" shows how long it took to get HTTP responses to create
    or search one record.

    "Interval between requests" should roughly match the QPS specified in the
    config file. If it is much longer than expected, you need to increase
    num_threads.
  
  - Don't forget to deactivate the repository in the PF admin page to free up
    the datastore for the dummy records.

Config file reference:

  base_url:
    The base URL of Person Finder app.

  repo:
    The repository name used to perform load testing. The repository must
    not exist before performing load test.

  num_records:
    The number of records created in "create" test.

  num_queries:
    The number of queries sent in "search" test.

  create_record_qps:
    It sends requests in this QPS in "create" test.

  search_record_qps:
    It sends requests in this QPS in "search" test.

  num_threads:
    The number of threads to perform the requests. It should be more than
    the request latency * QPS.

  output_dir:
    The path to the directory to output a JSON file with detailed load test
    result. You may want to look into this file for more detailed analysis.

  test_mode:
    If true, allows running "create" test for an existing repository.
"""
from __future__ import print_function

import datetime
import logging
import json
import os
import random
import scrape
import sys
import threading
import time
import traceback
import Queue

from google.appengine.ext import db

import config
import model
import remote_api


class Worker(object):
    """Workers (threads) in WorkerPool."""

    def __init__(self):
        self.task_queue = Queue.Queue()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        while True:
            task = self.task_queue.get(block=True)
            if not task:
                break
            task()

    def do_async(self, task):
        self.task_queue.put(task)

    def join(self):
        self.task_queue.put(None)
        self.thread.join()


class WorkerPool(object):
    """An implementation of a thread pool.

    WorkerPool.do_async blocks when all threads are busy. This is different
    from typical thread pool implementation
    e.g., multiprocessing.pool.ThreadPool. But this behavior is desired for
    load testing to keep constant QPS even after threads are temporarily
    filled up.
    """

    def __init__(self, size):
        self.size = size
        self.inactive_workers = Queue.Queue()
        for _ in xrange(self.size):
            self.inactive_workers.put(Worker())

    def do_async(self, task, *args):
        """Calls task(*args) asynchronously."""
        worker = self.inactive_workers.get(block=True)
        def worker_task():
            task(*args)
            self.inactive_workers.put(worker)
        worker.do_async(worker_task)

    def join(self):
        """Waits until all tasks finish."""
        for _ in xrange(self.size):
            worker = self.inactive_workers.get(block=True)
            worker.join()


class LoadTest(object):
    """Base class for a load testing job."""

    def __init__(self, name, conf):
        self.name = name
        self.conf = conf
        self.data = {
            'request_latency_seconds': [],
            'request_interval_seconds': [],
            'http_statuses': [],
        }

    def execute_all(self):
        """Calls self.execute_one() for each input returned by
        self.generate_input() in QPS specified by self.get_qps().
        """
        pool = WorkerPool(self.conf['num_threads'])
        for input in self.generate_input():
            start_time = datetime.datetime.now()
            pool.do_async(self.execute_one_internal, input)
            time.sleep(1.0 / self.get_qps())
            self.data['request_interval_seconds'].append(
                (datetime.datetime.now() - start_time).total_seconds())
        pool.join()

    def execute_one_internal(self, input):
        try:
            start_time = datetime.datetime.now()
            self.execute_one(input)
            end_time = datetime.datetime.now()
            self.data['request_latency_seconds'].append(
                (end_time - start_time).total_seconds())
        except Exception as e:
            traceback.print_exc()

    def save_result(self):
        """Saves load testing result to a JSON file.
        It may be used for more detailed analysis later.
        """
        file_name = '%s/%s_%s_result.json' % (
            self.conf['output_dir'],
            self.name,
            datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        output = {
            'conf': self.conf,
            'data': self.data,
        }
        with open(file_name, 'w') as f:
            json.dump(output, f)

    def print_stats(self):
        print()
        print ('Average request latency (sec):\t%.3f'
            % self.average(self.data['request_latency_seconds']))
        print ('90%%tile request latency (sec):\t%.3f'
            % self.ninety_percentile(self.data['request_latency_seconds']))
        print ('Average interval between requests (sec):\t%.3f'
            % self.average(self.data['request_interval_seconds']))
        print ('90%%tile interval between requests (sec):\t%.3f'
            % self.ninety_percentile(self.data['request_interval_seconds']))

        print()
        print('http_status:')
        http_status_freqs = {}
        for status in self.data['http_statuses']:
            if status in http_status_freqs:
                http_status_freqs[status] += 1
            else:
                http_status_freqs[status] = 1
        for status, freq in http_status_freqs.iteritems():
            status_str = str(status) if status else 'Error'
            print('  %s: %d (%.1f%%)' % (
                status_str, freq, 100.0 * freq / len(self.data['http_statuses'])))

    def average(self, deltas):
        if deltas:
            return sum(deltas, 0.0) / len(deltas)
        else:
            return float('nan')

    def ninety_percentile(self, deltas):
        if deltas:
            return sorted(deltas)[int(len(deltas) * 0.9)]
        else:
            return float('nan')

    def load_names(self, file_name):
        with open(file_name) as f:
            return [line.rstrip('\n') for line in f]


class CreateRecordsLoadTest(LoadTest):
    """Load test for creating person records.

    It creates records with first num_records entries (specified in conf)
    in tests/load_test/names_in_db.txt.
    """

    def __init__(self, conf):
        super(CreateRecordsLoadTest, self).__init__('create_record', conf)

        repo_exists = self.conf['repo'] in model.Repo.list()
        if not self.conf['test_mode'] and repo_exists:
            raise Exception(
                '"create" task must be done against a new repository, but a '
                'repository "%s" already exists. If you really want to do '
                'this, set "test_mode" to true in the config JSON.'
                % self.conf['repo'])
        if not repo_exists:
            self.create_repo(self.conf['repo'])

        scraper = scrape.Session(verbose=1)
        self.create_page = scraper.go(
            '%s/%s/create?role=provide'
                % (self.conf['base_url'], self.conf['repo']))

    def get_qps(self):
        return self.conf['create_record_qps']

    def generate_input(self):
        names = (self.load_names('tests/load_test/names_in_db.txt')
            [:self.conf['num_records']])
        for name in names:
            yield name

    def execute_one(self, name):
        status = None
        try:
            logging.info('Create record: %s', name)

            # Creates a new scrape.Session instance here because scrape.Session
            # is not thread-safe. Note that this scraper.go() doesn't cause
            # extra HTTP request.
            scraper = scrape.Session(verbose=1)
            scraper.go(self.create_page)

            (given_name, family_name) = name.split(' ')
            scraper.submit(
                scraper.doc.cssselect_one('form'),
                given_name=given_name,
                family_name=family_name,
                author_name='load_test.py',
                text='This is a record created by load_test.py.')
            status = scraper.status

        finally:
            self.data['http_statuses'].append(status)

    def create_repo(self, repo):
        logging.info('Create repo: %s', repo)
        db.put([model.Repo(key_name=repo)])
        # Provides some defaults.
        config.set_for_repo(
            repo,
            language_menu_options=['en'],
            repo_titles={'en': repo},
            keywords='',
            use_family_name=True,
            use_alternate_names=True,
            use_postal_code=True,
            allow_believed_dead_via_ui=False,
            min_query_word_length=1,
            show_profile_entry=False,
            profile_websites=[],
            map_default_zoom=6,
            map_default_center=[0, 0],
            map_size_pixels=[400, 280],
            read_auth_key_required=True,
            search_auth_key_required=True,
            deactivated=False,
            launched=False,
            deactivation_message_html='',
            start_page_custom_htmls={},
            results_page_custom_htmls={},
            view_page_custom_htmls={},
            seek_query_form_custom_htmls={},
            footer_custom_htmls={},
            bad_words='',
            published_date=0.0,
            updated_date=0.0,
            test_mode=False,
            force_https=False,
            zero_rating_mode=False,
        )


class SearchRecordsLoadTest(LoadTest):
    """Load test for searching records.

    It searches for given names, family names or full names in equal
    probability. The names are taken randomly from:
      - the first num_records entries in tests/load_test/names_in_db.txt
      - the first num_records entries in tests/load_test/names_not_in_db.txt
    """

    def __init__(self, conf):
        super(SearchRecordsLoadTest, self).__init__('search_record', conf)

        assert self.conf['repo'] in model.Repo.list(), (
            'Repository "%s" doesn\'t exist.' % self.conf['repo'])

        scraper = scrape.Session(verbose=1)
        self.search_page = scraper.go(
            '%s/%s/query?role=seek'
                % (self.conf['base_url'], self.conf['repo']))
        
    def get_qps(self):
        return self.conf['search_record_qps']

    def generate_input(self):
        r = random.Random()
        r.seed(0)  # For reproducible result.

        full_names = (
            self.load_names('tests/load_test/names_in_db.txt')
                [:self.conf['num_records']] +
            self.load_names('tests/load_test/names_not_in_db.txt')
                [:self.conf['num_records']])

        given_names = []
        family_names = []
        for full_name in full_names:
            (given_name, family_name) = full_name.split(' ')
            given_names.append(given_name)
            family_names.append(family_name)

        names = full_names + given_names + family_names

        for _ in xrange(self.conf['num_queries']):
            yield r.choice(names)

    def execute_one(self, query):
        status = None
        try:
            logging.info('Search record: %s', query)
            scraper = scrape.Session(verbose=1)
            scraper.go(self.search_page)
            scraper.submit(
                scraper.doc.cssselect_one('form'),
                query=query)
            status = scraper.status
        finally:
            self.data['http_statuses'].append(status)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) != 3 or sys.argv[2] not in ('create', 'search'):
        sys.stderr.write(
            'Usage:\n'
            'tools/load_test config.json create\n'
            'tools/load_test config.json search\n')

    with open(sys.argv[1]) as f:
        conf = json.load(f)

    if not os.path.exists(conf['output_dir']):
        os.makedirs(conf['output_dir'])

    remote_api.connect(conf['base_url'])

    if len(sys.argv) == 3 and sys.argv[2] == 'create':
        load_test = CreateRecordsLoadTest(conf)
    elif sys.argv[2] == 'search':
        load_test = SearchRecordsLoadTest(conf)
    else:
        raise Exception('Should not happen')

    load_test.execute_all()
    load_test.save_result()
    load_test.print_stats()
