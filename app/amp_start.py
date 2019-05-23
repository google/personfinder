# Copyright 2017 Google Inc.
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

from __future__ import absolute_import
import start


class Handler(start.Handler):
    """This handler shows AMP (Accelerated Mobile Pages)
    version of the repository's start page."""

    def get(self):
        self.env.amp = True
        # The reason for setting params.lang instead of env.lang
        # is not to attach lang parameter to the URL if it is not explicitly
        # specified in the current request.
        self.env.canonical_url = self.get_url('/', lang=self.params.lang)
        super(Handler, self).get()
