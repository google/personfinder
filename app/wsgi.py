# Copyright 2019 Google Inc.
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

"""Entrypoint to the Django WSGI app."""

import os
import sys

from django.core import wsgi

sys.path.append(os.path.join(os.path.dirname(__file__), 'vendors'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# pylint: disable=invalid-name
# Pylint doesn't like it being lower-case, but we call it this anyway because
# it's conventional with Django.
application = wsgi.get_wsgi_application()
