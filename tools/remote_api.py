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
import urllib2
import urlparse
import yaml

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

# Replacements for db.Key.__repr__ and db.Model.__repr__ (used in main).
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

def connect(hostport, path='/_ah/remote_api',
            email=None, password=None, secure=True):
    """Sets up a connection to an app that has the remote_api handler."""
    if not email:
        sys.stderr.write('User e-mail: ')
        sys.stderr.flush()
        email = raw_input()  # don't use raw_input's prompt (it goes to stdout)
    else:
        print >>sys.stderr, 'User e-mail: %s' % email
    os.environ['USER_EMAIL'] = email  # used by users.get_current_user()
    if not password:
        password = getpass.getpass('Password: ', sys.stderr)
    remote_api_stub.ConfigureRemoteApi(
        None, path, lambda: (email, password), hostport, secure=secure)

    # ConfigureRemoteApi sets os.environ['APPLICATION_ID']
    print >>sys.stderr, 'Connected to %s, app ID: %s' % (
        hostport, os.environ['APPLICATION_ID'])

def main():
    default_address = 'localhost'
    default_port = 8000
    default_path = '/_ah/remote_api'
    default_email = os.environ.get(
        'APPENGINE_USER', os.environ['USER'] + '@google.com')

    parser = optparse.OptionParser(usage='''%%prog [options] [url]

Starts an interactive console connected to an App Engine datastore.
The [url] argument is a shorthand for setting the hostname, port number,
and path to the remote_api handler.  If a [url] is given without a port
number, the default protocol is HTTPS.  Examples:

  % %prog xyz.appspot.com  # xyz.appspot.com:443, path /_ah/remote_api
  % %prog http://foo.org/bar  # foo.org:80, path /bar/remote_api
  % %prog localhost:6789  # localhost:6789, path /_ah/remote_api
  % %prog  # default is localhost:8000, path /_ah/remote_api''')
    parser.add_option('-a', dest='address',
                      help='appserver hostname (default: localhost)')
    parser.add_option('-p', dest='port', type='int',
                      help='appserver port number (default: %d)' % default_port)
    parser.add_option('-P', dest='path',
                      help='path to remote_api (default: %s)' % default_path)
    parser.add_option('-e', dest='email',
                      help='user e-mail (default: %s)' % default_email)
    parser.add_option('-c', dest='command',
                      help='Python command to execute')
    options, args = parser.parse_args()

    # Shorthand for address, port number, and path.
    if args:
        url = ('//' in args[0]) and args[0] or '//' + args[0]
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        address, port = urllib2.splitport(netloc)
        default_address = address
        default_port = int(port or 443)
        default_path = path.rstrip('/') + '/remote_api'

    # Apply defaults.  (We don't use optparse defaults because we want to let
    # explicit settings override our defaults.)
    address = options.address or default_address
    port = options.port or default_port
    path = options.path or default_path
    email = options.email or default_email

    # Use a dummy password when connecting to a development app server.
    password = (address == 'localhost' and 'foo') or None

    # Connect to the app server.
    logging.basicConfig(file=sys.stderr, level=logging.ERROR)
    try:
        connect('%s:%d' % (address, port), path, email, password, port == 443)
    except urllib2.HTTPError, e:
        sys.exit('HTTP error %d from URL: %s' % (e.code, e.url))
    except urllib2.URLError, e:
        reason = hasattr(e.reason, 'args') and e.reason.args[-1] or e.reason
        sys.exit('Cannot connect to %s:%d: %s' % (address, port, reason))

    # Set up more useful representations for interactive data manipulation
    # and debugging.  Alas, the App Engine runtime relies on the specific
    # output of repr(), so this isn't safe in production, only debugging.
    db.Key.__repr__ = key_repr
    db.Model.__repr__ = model_repr

    # Run startup commands.
    rc = os.environ.get('APPENGINE_REMOTE_API_RC', '')
    if rc:
        print >>sys.stderr, rc
        exec rc in globals(), locals()

    if options.command:
        exec options.command
    else:
        code.interact('', None, locals())

if __name__ == '__main__':
    main()
