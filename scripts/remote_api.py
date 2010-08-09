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

"""Initialize datastore access through the remote API.  Any command-line
scripts that need to access the datastore of a running appserver should
use this module, and should run under Python 2.5."""

import getpass
import os
import sys

# This script is in a scripts directory below the root project directory.
SCRIPTS_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPTS_DIR)
APP_DIR = os.path.join(PROJECT_DIR, 'app')
# Make imports work for Python modules that are part of this app.
sys.path.append(APP_DIR)

# Make imports work for Python modules included with App Engine.
APPENGINE_DIR = os.environ.get(
    'APPENGINE_DIR', os.environ['HOME'] + '/google_appengine')
sys.path.append(APPENGINE_DIR)
sys.path.append(APPENGINE_DIR + '/lib/django')
sys.path.append(APPENGINE_DIR + '/lib/webob')
sys.path.append(APPENGINE_DIR + '/lib/yaml/lib')

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

def init(app_id, host=None, username=None, password=None):
  if host is None:
    host = '%s.appspot.com' % app_id

  print 'App Engine server at %s' % host
  if not username:
    username = raw_input('Username: ')
  else:
    print 'Username: %s' % username
  if not password:
    password = getpass.getpass('Password: ')

  remote_api_stub.ConfigureRemoteDatastore(
      app_id, '/remote_api', lambda: (username, password), host)

  # Trigger authentication to verify username and password on startup.
  db.Query().get()
  return host

def detect_app_id():
  """Look for the application ID in the app.yaml file."""
  for line in open(os.path.join(APP_DIR, 'app.yaml')):
    if line.startswith('application:'):
      return line.split(':')[1].strip()
