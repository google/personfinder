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

import model
import utils

class Handler(utils.BaseHandler):
    """Show various statistics for each repository,
    including repositories which are no longer active."""
    repo_required = False
    admin_required = True

    def get(self):
        repos = sorted(model.Repo.list())
        all_usage = [self.get_repo_usage(repo) for repo in repos]
        self.render('admin_statistics.html', all_usage=all_usage)

    def get_repo_usage(self, repo):
        """
        Get num_persons and notes for specific repository
        Return: dictionary contains repository name,
        number of persons and notes, e.g.
        {'repo': haiti, 'num_persons': 10, 'num_notes': 5}
        """
        counters = model.UsageCounter.get(repo)
        return {'repo': repo,
                'num_persons': counters.person_counter if counters else 0,
                'num_notes': counters.note_counter if counters else 0}
