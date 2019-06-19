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
"""View for the global homepage."""

import views.enduser.base


class GlobalIndexView(views.enduser.base.EnduserBaseView):

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        if self.env.lang == 'ja':
            return self.render('home-ja.html')
        else:
            return self.render('home.html')
