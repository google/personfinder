# Copyright 2016 Google Inc.
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

"""Provides a method to set up remote API to a Person Finder app."""

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
    # Passing a unicode object to ConfigureRemoteApiForOAuth() causes a weird error later.
    # Converts it into str.
    secure, host, port, path = parse_url(str(url))
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
        raise Exception(
                "\nERROR: Failed connecting to %s. See stack trace above for "
                "details. Follow these steps if you haven't, and try "
                "again:\n\n"
                "- Install Google Cloud SDK: https://cloud.google.com/sdk/\n"
                "- Run this command and log in with a Google account which is "
                "an administrator of the AppEngine app:\n"
                "  $ gcloud auth login"
                % url)
