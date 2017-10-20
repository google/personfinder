#!/usr/bin/python2.7
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

import urlparse
import start
import utils


class Handler(start.Handler):

    def get(self):
        self.env.amp = True
        self.env.canonical_url = self.set_canonical_url_param(self.request.url,
                                                              'lang', self.env.lang)
        self.render('start.html', cache_seconds=0, get_vars=self.get_vars)

    def set_canonical_url_param(self, url, param, value):
        """This modifies a URL setting the given param to the specified canonical url value.
        This may add the param or override an existing value, or, if the value is None,
        it will remove the param. Note that value must be a basestring and can't be
        an int, for example."""
        url_parts = list(urlparse.urlparse(url))
        url_parts[2] = url_parts[2].replace('/amp_start', '')
        url_parts[4] = utils.set_param(url_parts[4], param, value)
        return urlparse.urlunparse(url_parts)
