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
"""Views for static pages."""

import views.base


class HomeView(views.base.BaseView):

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        if self.env.lang == 'ja':
            return self.render('home-ja.html')
        else:
            return self.render('home.html')


class RespondersView(views.base.BaseView):

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        if self.env.lang == 'ja':
            return self.render('responders-ja.html')
        else:
            return self.render('responders.html')


class HowToView(views.base.BaseView):

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        if self.env.lang == 'ja':
            return self.render('howto-ja.html')
        else:
            return self.render('howto.html')
