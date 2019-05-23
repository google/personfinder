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

"""Tools to help run tests against the Django app."""

import testutils.base


class TaskTestsBase(testutils.base.ServerTestsBase):
    """A base class for tests for tasks."""

    # This HTTP header should be set to make the request appear to come from App
    # Engine (other task requests are rejected).
    _REQ_HEADERS = {'HTTP_X_APPENGINE_TASKNAME': 'notempty'}

    def run_task(self, path, data={}, method='GET'):
        """Makes a request to a task handler."""
        if method == 'GET':
            return self.client.get(path, data, **TaskTestsBase._REQ_HEADERS)
        else:
            return self.client.post(path, data, **TaskTestsBase._REQ_HEADERS)
