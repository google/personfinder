#!/usr/bin/python2.5
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

"""Unittest initialization for handlers.  No actual tests"""

__author__ = 'lschumacher@google.com (Lee Schumacher)'

import main
import model
import types
import webob
import urllib

from google.appengine.ext import webapp

def initialize_handler(
        handler_class, action, repo='haiti', environ=None, params=None):
    model.Repo(key_name=repo).put()
    params_str = ('?' + urllib.urlencode(params)) if params else ''
    request = webapp.Request(webob.Request.blank(
        '/' + repo + '/' + action + params_str, environ=environ).environ)
    response = webapp.Response()
    return handler_class(request, response, main.setup_env(request))
