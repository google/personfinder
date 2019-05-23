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

"""Module for site-specific settings.

Some "constants" are expected to be the same for any Person Finder installation
(for example, the set of languages that are handled as right-to-left languages
would not change); those are stored in the const module. However, others things
might vary from one installation to another: for example, an organization that
runs Person Finder at a subdirectory instead of root would need to set the
OPTIONAL_PATH_PREFIX value here.

TODO(nworden): move more values here as appropriate (e.g.,
DEFAULT_LANGUAGE_CODE)
"""

# When Person Finder is run at an address under a subdirectory rather than at
# root (e.g., www.organization.org/personfinder/), that subdirectory should be
# specified here so that URLs can be handled correctly. The value MUST NOT start
# or end with a slash.
OPTIONAL_PATH_PREFIX = 'personfinder'

# Hosts allowed in prod (not applicable to local servers).
# We just allow everything for now, to handle the different domains we serve off
# of (e.g., different App Engine versions).
# TODO(nworden): Find a way to set this at deploy time. Maybe we could use an
# environment variable passed through app.yaml.
PROD_ALLOWED_HOSTS = ['*']

# This should be set to an admin's email address.
# In production, a global superadmin permission, with a three-day expiration,
# will be added for this user when the database is set up. That user should
# adjust their expiration date and add permissions for other users as needed.
# For development servers, a similar permission is set up for test@example.com
# instead, regardless of the PROD_ROOT_ADMIN setting.
PROD_ROOT_ADMIN = None
