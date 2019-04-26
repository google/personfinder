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

"""The sitemap."""

import const
import model
import views.base


class SitemapView(views.base.BaseView):
    """The sitemap view."""

    ACTION_ID = 'sitemap'

    def get(self, request, *args, **kwargs):
        """Serves get requests.

        Args:
            request: Unused.
            *args: Unused.
            **kwargs: Unused.

        Returns:
            HttpResponse: A HTTP response with the sitemap.
        """
        del request, args, kwargs  # unused
        langs = const.LANGUAGE_ENDONYMS.keys()
        urimaps = []
        # Include the root/global homepage.
        urimaps.append({lang: self.build_absolute_uri('/?lang=%s' % lang)
                        for lang in langs})
        # Include the repo homepages.
        for repo in model.Repo.list_launched():
            urimaps.append({
                lang: self.build_absolute_uri('/%s?lang=%s' % (repo, lang))
                for lang in langs})
        return self.render('sitemap.xml', urimaps=urimaps)
