#!/usr/bin/python2.5
# Copyright 2009-2010 by Ka-Ping Yee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An interactive Python console connected to an app's datastore.

Instead of running this script directly, use the 'console' shell script,
which sets up the PYTHONPATH and other necessary environment variables."""

import code
import getpass
import logging
import optparse
import os
import sys
import urllib
import yaml

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

# Make some useful environment variables available.

APP_DIR = os.environ['APP_DIR']
APPENGINE_DIR = os.environ['APPENGINE_DIR']
PROJECT_DIR = os.environ['PROJECT_DIR']
TESTS_DIR = os.environ['TESTS_DIR']
TOOLS_DIR = os.environ['TOOLS_DIR']

# Set up more useful representations, handy for interactive data manipulation
# and debugging.  Unfortunately, the App Engine runtime relies on the specific
# output of repr(), so this isn't safe in production, only debugging.

def key_repr(key):
    levels = []
    while key:
        levels.insert(0, '%s %s' % (key.kind(), key.id() or repr(key.name())))
        key = key.parent()
    return '<Key: %s>' % '/'.join(levels)

def model_repr(model):
    if model.is_saved():
        key = model.key()
        return '<%s: %s>' % (key.kind(), key.id() or repr(key.name()))
    else:
        return '<%s: unsaved>' % model.kind()

def get_app_id():
    """Gets the app_id from the app.yaml configuration file."""
    return yaml.safe_load(open(APP_DIR + '/app.yaml'))['application']

def connect(server, app_id=None, username=None, password=None, secure=True):
    """Sets up a connection to an app that has the remote_api handler."""
    if not app_id:
        app_id = get_app_id()
    print >>sys.stderr, 'Application ID: %s' % app_id
    print >>sys.stderr, 'Server: %s' % server
    if not username:
        sys.stderr.write('Username: ')
        sys.stderr.flush()
        username = raw_input()
    else:
        print >>sys.stderr, 'Username: %s' % username
    # Sets up users.get_current_user() inside of the console
    os.environ['USER_EMAIL'] = username
    if not password:
        password = getpass.getpass('Password: ', sys.stderr)
    remote_api_stub.ConfigureRemoteDatastore(
        app_id, '/remote_api', lambda: (username, password), server,
        secure=secure)

    db.Query().count()  # force authentication to happen now

def main():
    default_address = 'localhost'
    default_port = 8000
    default_app_id = get_app_id()
    default_username = os.environ.get(
        'APPENGINE_USER', os.environ['USER'] + '@google.com')

    parser = optparse.OptionParser(usage='''%%prog [options] [server]

Starts an interactive console connected to an App Engine datastore.
The [server] argument is a shorthand for setting the hostname, port
number, and application ID.  For example:

    %%prog xyz.appspot.com  # uses port 80, app ID 'xyz'
    %%prog localhost:6789  # uses port 6789, app ID %r''' % default_app_id)
    parser.add_option('-a', '--address',
                      help='appserver hostname (default: localhost)')
    parser.add_option('-p', '--port', type='int',
                      help='appserver port number (default: %d)' % default_port)
    parser.add_option('-A', '--application',
                      help='application ID (default: %s)' % default_app_id)
    parser.add_option('-u', '--username',
                      help='username (default: %s)' % default_username)
    parser.add_option('-c', '--command',
                      help='Python commands to execute')
    options, args = parser.parse_args()

    # Handle shorthand for address, port number, and app ID.
    if args:
        default_address, default_port = urllib.splitport(args[0])
        default_port = int(default_port or 443)
        if default_address != 'localhost':
            subdomain_name = default_address.split('.')[0]
            # If the subdomain name matches the default HR app ID, keep it.
            if default_app_id != 's~' + subdomain_name:
                default_app_id = subdomain_name

    # Apply defaults.  (We don't use optparse defaults because we want to let
    # explicit settings override our defaults.)
    address = options.address or default_address
    port = options.port or default_port
    app_id = options.application or default_app_id
    username = options.username or default_username
    password = None

    # Use a dummy password when connecting to a development app server.
    if address == 'localhost':
        password = 'foo'

    # Connect to the app server.
    logging.basicConfig(file=sys.stderr, level=logging.INFO)
    connect('%s:%d' % (address, port), app_id, username, password,
            secure=(port == 443))

    # Set up more useful representations for interactive data manipulation
    # and debugging.  Alas, the App Engine runtime relies on the specific
    # output of repr(), so this isn't safe in production, only debugging.
    db.Key.__repr__ = key_repr
    db.Model.__repr__ = model_repr

    # Make some useful functions available in the interactive console.
    import model
    import setup
    locals().update(model.__dict__)
    locals().update(setup.__dict__)

    if options.command:
        exec options.command
    else:
        code.interact('', None, locals())

if __name__ == '__main__':
    main()
