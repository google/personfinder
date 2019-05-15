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


from __future__ import print_function
# Sample query for counting all the Person entries between dates.
from __future__ import print_function
import datetime

query = Person.all(filter_expired=False).filter(
    'entry_date >=', datetime.datetime(2013, 1, 1, 0, 0, 0)).filter(
    'entry_date <', datetime.datetime(2014, 1, 1, 0, 0, 0))
count = 0
while True:
    current_count = query.count()
    if current_count == 0:
        break
    count += current_count
    query.with_cursor(query.cursor())
print('# of persons =', count)
