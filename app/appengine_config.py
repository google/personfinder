#!/usr/bin/python2.5
# Copyright 2012 Google Inc.
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

"""App Engine configuration."""

__author__ = 'ryok@google.com (Ryo Kawaguchi)'

# We need to call use_library to set django version before App Engine SDK loads
# the default django version (0.96.4). Importing django_setup does what we want.
#
# For a bit more background:
# http://www.gae123.com/articles/dpwf/djgae1x.html
# https://developers.google.com/appengine/docs/python/tools/appstats#OptionalConfiguration
import django_setup
