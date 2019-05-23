# Copyright 2010 Google Inc.
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

"""Handler for a Turing test page, and utility functions for other pages,
to guard the display of sensitive information."""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import cgi
import hashlib
import os
import pickle
import random
import time
import urlparse

from recaptcha.client import captcha

from utils import *

REVEAL_KEY_LENGTH = 20

# ==== Signature generation and verification ===============================

def sha1_hash(string):
    """Computes the SHA-1 hash of the given string."""
    return hashlib.sha1(string).digest()

def xor(string, byte):
    """Exclusive-ors each character in a string with the given byte."""
    results = []
    for ch in string:
        results.append(chr(ord(ch) ^ byte))
    return ''.join(results)

def hmac(key, data, hash=sha1_hash):
    """Produces an HMAC for the given data."""
    return hash(xor(key, 0x5c) + hash(xor(key, 0x36) + pickle.dumps(data)))

def sign(data, lifetime=600):
    """Produces a limited-time signature for the given data."""
    expiry = int(time.time() + lifetime)
    key = get_reveal_key(length=REVEAL_KEY_LENGTH)
    return hmac(key, (expiry, data)).encode('hex') + '.' + str(expiry)

def verify(data, signature):
    """Checks that a signature matches the given data and hasn't yet expired."""
    try:
        mac, expiry = signature.split('.', 1)
        mac, expiry = mac.decode('hex'), int(expiry)
    except (TypeError, ValueError):
        return False
    key = get_reveal_key(length=REVEAL_KEY_LENGTH)
    return time.time() < expiry and hmac(key, (expiry, data)) == mac

def get_reveal_key(length=REVEAL_KEY_LENGTH):
    """Gets the key for authorizing reveal operations, or creates one if none
    exist."""
    key = config.get('reveal')
    if not key:
        key = generate_random_key(REVEAL_KEY_LENGTH)
        config.set(reveal=key)
    return key

def make_reveal_url(handler, content_id):
    """Produces a link to this reveal handler that, on success, redirects back
    to the given 'target' URL with a signature for the given 'content_id'."""
    return handler.get_url(
        '/reveal', target=handler.request.path_qs, content_id=content_id)


# ==== The reveal page, which authorizes revelation ========================
# To use this facility, handlers that want to optionally show sensitive
# information should do the following:
#
# 1.  Construct a 'content_id' string that canonically identifies what is
#     being requested (e.g. the name of the page and any parameters that
#     control what is shown on the page).
#
# 2.  Call reveal.verify(content_id, self.params.signature) to find out
#     whether the sensitive information should be shown.
#
# 3.  If reveal.verify() returns False, then replace the sensitive information
#     with a link to make_reveal_url(self, content_id).

class Handler(BaseHandler):
    def get(self):
        self.render('reveal.html', captcha_html=self.get_captcha_html())

    def post(self):
        captcha_response = self.get_captcha_response()
        if captcha_response.is_valid:
            signature = sign(self.params.content_id)
            # self.params.target contains only the path part of the URL e.g.,
            # "/test/view?...".
            #
            # - We verify that self.params.target starts with '/'.
            # - We put our own scheme and netloc to make it an absolute URL.
            #
            # These two are required to allow only URLs in our domain as the
            # target, avoiding this to be used as a redirector to aid phishing
            # attacks.
            if not self.params.target.startswith('/'):
                return self.error(400, 'Invalid target parameter')
            scheme, netloc, _, _, _ = urlparse.urlsplit(self.request.url)
            target = '%s://%s%s' % (scheme, netloc, self.params.target)
            self.redirect(
                set_url_param(target, 'signature', signature))
        else:
            self.render(
                'reveal.html',
                captcha_html=self.get_captcha_html(),
                content_id=self.params.content_id)
