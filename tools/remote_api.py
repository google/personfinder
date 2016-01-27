#!/usr/bin/python2.7
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
import re
import sys
import traceback
import urllib2
import urlparse
import yaml

from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.ext import db

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

def parse_url(url):
    # Determine the protocol, host, port, and path from the URL argument.
    if '//' not in url:
        url = '//' + url
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    host, port = urllib2.splitport(netloc)
    port = int(port or (scheme == 'http' and 80 or 443))  # default to https
    secure = (port == 443)
    host = host or 'localhost'
    path = path or '/remote_api'
    return secure, host, port, path

def configure_remote_api(hostport, path, secure, server_type):
    if server_type == 'appengine':
        remote_api_stub.ConfigureRemoteApiForOAuth(
                hostport, path, secure=secure, auth_tries=1)
    elif server_type == 'local':
        # It seems local dev_appserver doesn't support remote API with OAuth.
        remote_api_stub.ConfigureRemoteApi(
                None,
                path,
                lambda: ('admin@example.com', None),
                hostport,
                secure=secure)
    else:
        raise Exception('Unknown --server_type: %r' % server_type)

def connect(url, server_type=None):
    """Sets up a connection to an app that has the remote_api handler."""
    secure, host, port, path = parse_url(url)
    hostport = '%s:%d' % (host, port)
    url = (secure and 'https' or 'http') + '://' + hostport + path

    if not server_type:
        if (re.search(r'\.appspot\.com$', host)
                    or host in ('google.org', 'www.google.org')):
            server_type = 'appengine'
        elif host == 'localhost':
            server_type = 'local'
        else:
            raise Exception(
                    "Couldn't determine the server type. Specify either "
                    "--server-type=appengine or --server-type=local.")

    # Connect to the appserver.
    try:
        logging.basicConfig(file=sys.stderr, level=logging.ERROR)
        try:
            configure_remote_api(hostport, path, secure, server_type)
        except Exception, e:
            if not path.endswith('/remote_api'):
                path = path.rstrip('/') + '/remote_api'
                configure_remote_api(hostport, path, secure, server_type)
            else:
                raise

    except Exception, e:
        traceback.print_exc()
        print >>sys.stderr, (
                "\nERROR: Failed connecting to %s. See stack trace above for "
                "details. Follow these steps if you haven't, and try "
                "again:\n\n"
                "- Install Google Cloud SDK: https://cloud.google.com/sdk/\n"
                "- Run this command and log in with a Google account which is "
                "an administrator of the AppEngine app:\n"
                "  $ gcloud auth login"
                % url)
        return None, None

    # ConfigureRemoteApi sets os.environ['APPLICATION_ID']
    app_id = os.environ['APPLICATION_ID']
    sys.ps1 = app_id + '> '  # for the interactive console
    return url, app_id

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
        url, app_id = connect(args[0], server_type=options.server_type)
        if not url:
            sys.exit(1)
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
