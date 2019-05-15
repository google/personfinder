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

"""Initialize Django.

We're currently in between web servers: Person Finder originally ran on webapp2,
which is no longer being maintained, and we're incrementally moving to Django.
The move is complicated by the fact that the original implementation uses Django
for templating and therefore requires some Django configuration. However, Django
can't be initialized more than once. If we try to treat the webapp2 app (with
its Django templating setup) and the new Django app totally independently, we'll
have a problem: whichever one happens to serve first from an instance will work
fine, and then the next one will crash when it tries to intialize Django a
second time. So, we want to have a single set of Django settings, intialized by
the Django app regardless of which app serves first from an instance. The
webapp2 app imports this, this imports the Django app's entrypoint (wsgi), and
Django is initialized from wsgi.
"""

__author__ = 'kpy@google.com (Ka-Ping Yee)'

import os

import django
import django.conf
import django.template
import django.template.loaders.base
import django.utils.translation
from django.utils.translation import activate, gettext_lazy, ugettext

import wsgi


if os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    # See https://web.archive.org/web/20160916120959/http://code.google.com/p/googleappengine/issues/detail?id=985
    import urllib
    urllib.getproxies_macosx_sysconf = lambda: {}
