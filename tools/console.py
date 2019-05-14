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
import logging
import optparse
import os
import re
import sys
import traceback

from google.appengine.ext import db

import remote_api

def key_repr(key):
    """A more convenient replacement for db.Key.__repr__."""
    levels = []
    while key:
        levels.insert(0, '%s %s' % (key.kind(), key.id() or repr(key.name())))
        key = key.parent()
    return '<Key: %s>' % '/'.join(levels)

def model_repr(model):
    """A more convenient replacement for db.Model.__repr__."""
    if model.is_saved():
        key = model.key()
        return '<%s: %s>' % (key.kind(), key.id() or repr(key.name()))
    else:
        return '<%s: unsaved>' % model.kind()

    # Use a dummy password when connecting to a development app server.
    password = (address == 'localhost' and 'foo') or None

def connect(url, server_type=None):
    remote_api.connect(url, server_type=server_type)

    # ConfigureRemoteApi sets os.environ['APPLICATION_ID']
    app_id = os.environ['APPLICATION_ID']
    sys.ps1 = app_id + '> '  # for the interactive console

def main():
    parser = optparse.OptionParser(usage='''%prog [options] <appserver_url>

Starts an interactive Python console connected to an App Engine datastore.
Use the <appserver_url> argument to set the protocol, hostname, port number,
and path to the remote_api handler.  If <appserver_url> does not include a
protocol or port number, the default protocol is HTTPS.  The default path is
/remote_api (the remote API path specified in app.yaml).  Examples:

  # Start Python but don't connect
  % %prog

  # Connect to xyz.appspot.com, port 443, path /remote_api
  % %prog xyz.appspot.com

  # Connect to foo.org, port 80, try /bar/baz, then try /bar/baz/remote_api
  % %prog http://foo.org/bar/baz

  # Connect to localhost, port 6789, path /remote_api
  % %prog :6789''')
    parser.add_option('-c', dest='command', help='Python command to execute')
    parser.add_option('--server-type', dest='server_type',
                      help='"appengine": The server is AppEngine. '
                           '"local": The server is a local dev_appserver. '
                           'It is guessed automatically when omitted.')
    options, args = parser.parse_args()

    # Connect to the app server.
    if args:
        url = args[0]
        connect(url, server_type=options.server_type)
        banner = 'Connected to: ' + url
    else:
        banner = 'Not connected.  Use connect(appserver_url) to connect.'

    # Set up more useful representations for interactive data manipulation
    # and debugging.  Alas, the App Engine runtime relies on the specific
    # output of repr(), so this isn't safe in production, only debugging.
    db.Key.__repr__ = key_repr
    db.Model.__repr__ = model_repr
    locals()['connect'] = connect

    # Run startup commands.
    rc = os.environ.get('REMOTE_API_RC', '')
    if rc:
        banner = (banner + '\n' + rc).strip()
        exec rc in globals(), locals()

    if options.command:
        exec options.command
    else:
        code.interact(banner, None, locals())

if __name__ == '__main__':
    main()
