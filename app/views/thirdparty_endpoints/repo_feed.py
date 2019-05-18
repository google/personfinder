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

import django.http
import xml.etree.ElementTree as ET

import config
import model
import utils
import views.thirdparty_endpoints.base


ATOM = views.thirdparty_endpoints.base.ATOM
GPF = views.thirdparty_endpoints.base.GPF
GEORSS = views.thirdparty_endpoints.base.GEORSS


class RepoFeedView(views.thirdparty_endpoints.base.ThirdPartyFeedBaseView):
    """View for the repo feed."""

    _TITLE = 'Person Finder Repository Feed'

    def check_auth(self):
        # Anyone can access the repos feed.
        pass

    def add_feed_elements(self, root):
        ET.SubElement(root, 'id').text = self.build_absolute_uri()
        ET.SubElement(root, 'title').text = RepoFeedView._TITLE
        if self.env.repo == 'global':
            repos = model.Repo.all().filter(
                'activation_status !=', model.Repo.ActivationStatus.STAGING)
        else:
            repo = model.Repo.get(self.env.repo)
            if repo.activation_status == model.Repo.ActivationStatus.ACTIVE:
                repos = [repo]
            else:
                raise django.http.Http404()
        repo_confs = {}
        for repo in repos:
            repo_id = repo.key().name()
            repo_conf = config.Configuration(repo_id, include_global=False)
            repo_confs[repo_id] = repo_conf
        updated_dates = [conf.updated_date for conf in repo_confs.values()]
        # If there's no non-staging repositories, it's not really clear what
        # updated_date should be; we just use the current time.
        latest_updated_date = (
            max(updated_dates) if updated_dates else utils.get_utcnow())
        ET.SubElement(root, 'updated').text = utils.format_utc_timestamp(
            latest_updated_date)
        for repo in repos:
            if repo.activation_status == model.Repo.ActivationStatus.ACTIVE:
                self._add_repo_entry(root, repo, repo_confs[repo.key().name()])

    def _add_repo_entry(self, root, repo, repo_conf):
        entry_el = ET.SubElement(root, 'entry')
        ET.SubElement(entry_el, 'id').text = self.build_absolute_uri(
            '/', repo.key().name())
        if repo_conf.language_menu_options:
            default_lang = repo_conf.language_menu_options[0]
            title_el = ET.SubElement(
                entry_el, 'title', {'lang': default_lang})
            title_el.text = repo_conf.repo_titles[default_lang]
        ET.SubElement(entry_el, 'updated').text = utils.format_utc_timestamp(
            repo_conf.updated_date)
        content_el = ET.SubElement(entry_el, 'content', {'type': 'text/xml'})
        repo_el = ET.SubElement(content_el, GPF + 'repo')
        for lang, title in repo_conf.repo_titles.items():
            ET.SubElement(repo_el, GPF + 'title', {'lang': lang}).text = title
        ET.SubElement(repo_el, GPF + 'read_auth_key_required').text = (
            'true' if repo_conf.read_auth_key_required else 'false')
        ET.SubElement(repo_el, GPF + 'search_auth_key_required').text = (
            'true' if repo_conf.search_auth_key_required else 'false')
        ET.SubElement(repo_el, GPF + 'test_mode').text = (
            'true' if repo.test_mode else 'false')
        center = repo_conf.map_default_center or [0, 0]
        location_el = ET.SubElement(repo_el, GPF + 'location')
        ET.SubElement(location_el, GEORSS + 'point').text = (
            '%f %f' % (center[0], center[1]))

    def log(self):
        self.log_api_action(model.ApiActionLog.REPO)
