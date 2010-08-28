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

from utils import *
from model import *


class Main(Handler):
    subdomain_required = False

    def get(self):
        if not self.subdomain:
            for key in Subdomain.all(keys_only=True):
                self.write('<a href="http://%s.%s/">%s</a><br>' %
                           (key.name(), self.env.netloc, key.name()))
            return

        if self.render_from_cache(cache_time=600):
            return

        # Round the stats to nearest 100 so people don't worry that it doesn't
        # increment every time they add a record.
        person_count = Counter.get_count(self.subdomain, Person)
        num_people = int(round(person_count, -2))

        self.render('templates/main.html', cache_time=600,
                    num_people=num_people,
                    seek_url=self.get_url('/query', role='seek'),
                    provide_url=self.get_url('/query', role='provide'))

if __name__ == '__main__':
    run(('/', Main))
