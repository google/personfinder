#!/usr/bin/python2.7
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

import logging
import sys

import model
from utils import *

class Handler(BaseHandler):
    repo_required = False
    admin_required = True

    def get(self):
        """
        Get all repositories and
        num_persons and notes for each repository
        Return: list contains dictionarys, e.g.
        [{'repo': haiti, 'num_persons': 10, 'num_notes': 5}, {...}]
        """
        repos = sorted(model.Repo.list())
        all_usage = []
        for repo in repos:
            all_usage.append(self.get_usage(repo))
        self.render('admin_statistics.html',
                     all_usage=all_usage)

    def get_usage(self, repo):
        """
        Get num_persons and notes for specific repository
        Return: dictionary contains repository name,
        number of persons and notes, e.g.
        {'repo': haiti, 'num_persons': 10, 'num_notes': 5}
        """
        counters = model.UsageCounter.get(repo)
        persons = counters.person_counter if counters else 0
        notes = counters.note_counter if counters else 0
        usage = {}
        usage['repo'] = repo
        usage['num_persons'] = persons
        usage['num_notes'] = notes
        return usage
