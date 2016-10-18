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

from model import *
from utils import *


def persons_num(repo):
	"""Return #Persons for specific repo"""
	counters = UsageCounter.get(repo)
	persons = counters.person_counter if counters else 0
	return persons

def notes_num(repo):
	"""Return #Notes for specific repo"""	
	counters = UsageCounter.get(repo)
	notes = counters.note_counter if counters else 0
	return notes

class Handler(BaseHandler):
    repo_required = False
    ignore_deactivation = True
    admin_required = True

    def get(self):
        repos = sorted(Repo.list())
        total_usage = []
        for repo in repos:
        	repo_usage = []
        	repo_usage.append(repo)
        	repo_usage.append(persons_num(repo))
        	repo_usage.append(notes_num(repo))
        	total_usage.append(repo_usage)

        self.render('admin_summary.html', 
        			total_usage=total_usage)



