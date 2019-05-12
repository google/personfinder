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
"""Code shared by third-party endpoint (API and feeds) view modules."""

import datetime

import config
import model
import views.thirdparty_endpoints.base


class RepoFeedView(views.thirdparty_endpoints.base.ThirdPartyFeedBaseView):
    """View for the repo feed."""

    _TITLE = 'Person Finder Repository Feed'

    def check_auth(self):
        # Anyone can access the repos feed.
        pass

    def get_feed(self):
        if self.env.repo == 'global':
            repos = model.Repo.list_launched()
        else:
            repos = [self.env.repo]
        feed = _RepoFeed(
            RepoFeedView._TITLE,
            self.build_absolute_uri(),  # link
            None,  # description
            feed_guid=self.build_absolute_uri())
        for repo in repos:
            repo_conf = config.Configuration(repo, include_global=False)
            feed.add_item(
                repo,
                self.build_absolute_uri('/', repo=repo),
                None,  # description
                unique_id=self.build_absolute_uri('/', repo=repo),
                updateddate=datetime.datetime.fromtimestamp(
                    repo_conf.updated_date),
                repo_id=repo,
                repo_conf=repo_conf)
        self.log_api_action(model.ApiActionLog.REPO)
        return feed


class _RepoFeed(views.thirdparty_endpoints.base.PersonFinderAtomFeed):

    def add_item_elements(self, handler, item):
        super(_RepoFeed, self).add_item_elements(handler, item)
        if 'repo_id' not in item:
            return
        repo_id = item['repo_id']
        repo_conf = item['repo_conf']
        repo_obj = model.Repo.get(repo_id)
        for lang, title in repo_conf.repo_titles.items():
            handler.addQuickElement('title', title, {'xml:lang': lang})
        handler.addQuickElement(
            'gpf:read_auth_key_required',
            'true' if repo_conf.read_auth_key_required else 'false')
        handler.addQuickElement(
            'gpf:search_auth_key_required',
            'true' if repo_conf.search_auth_key_required else 'false')
        handler.addQuickElement(
            'gpf:test_mode',
            'true' if repo_obj.test_mode else 'false')
        center = repo_conf.map_default_center or [0, 0]
        handler.startElement('gpf:location', {})
        handler.addQuickElement(
            'georss:point', '%f %f' % (center[0], center[1]))
        handler.endElement('gpf:location')
