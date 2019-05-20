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

"""The datastore setup handler."""

import django.shortcuts

import setup_pf
import views.base


class SetupDatastoreHandler(views.base.BaseView):
    """The datastore setup handler."""

    ACTION_ID = 'setup_datastore'

    def get(self, request, *args, **kwargs):
        """Sets up datastore, if it's not already set up."""
        del request, args, kwargs  # unused
        if self.env.config.get('initialized'):
            return self.error(400)
        setup_pf.setup_datastore()
        return django.shortcuts.redirect(self.build_absolute_uri('/'))
