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
"""Code shared by admin view modules."""

import django.shortcuts

import model
import utils
import views.base


class EnduserBaseView(views.base.BaseView):
    """Base view for end-user views."""

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(EnduserBaseView, self).setup(request, *args, **kwargs)
        self.params.read_values(get_params={'ui': utils.strip})

    def dispatch(self, request, *args, **kwargs):
        """See docs on django.views.View.dispatch."""
        if self.env.config.enable_react_ui:
            return self.render('react_index.html')
        return super(EnduserBaseView, self).dispatch(request, args, kwargs)
