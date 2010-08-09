#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unix command-line utility: interactive administration console."""

import code
import logging
import remote_api
import sys
from model import *

if __name__ == '__main__':
  if len(sys.argv) < 2:
    raise SystemExit('Usage: %s app_id [host]' % sys.argv[0])
  logging.basicConfig(stream=sys.stderr, level=logging.INFO)
  remote_api.init(*sys.argv[1:])
  code.interact('', None, locals())
