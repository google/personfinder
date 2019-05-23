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

"""Handlers for the frontend API."""

import django.http
import simplejson

import config
import model
import search.searcher
import utils
import views.base


class FrontendApiBaseView(views.base.BaseView):
    """The base class for frontend API views."""

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(FrontendApiBaseView, self).setup(request, *args, **kwargs)
        self._json_encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)

    def _json_response(self, data):
        return django.http.HttpResponse(
            self._json_encoder.encode(data),
            content_type='application/json; charset=utf-8')

class RepoView(FrontendApiBaseView):
    """View for information about repositories themselves."""

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        if self.env.repo == 'global':
            data = []
            repos = model.Repo.all().filter(
                'activation_status =', model.Repo.ActivationStatus.ACTIVE)
            for repo in repos:
                repo_id = repo.key().name()
                # TODO(nworden): Move this data onto the Repo object, like we
                # did for activation status. It'd be more efficient, and IMO the
                # code would be cleaner.
                repo_title = self._select_repo_title(
                    config.get_for_repo(repo_id, 'repo_titles'),
                    config.get_for_repo(repo_id, 'language_menu_options'))
                data.append({
                    'repoId': repo_id,
                    'title': repo_title,
                    'recordCount': self._get_person_count(repo_id),
                })
        else:
            repo_title = self._select_repo_title(
                self.env.config.get('repo_titles'),
                self.env.config.get('language_menu_options'))
            data = {
                'repoId': self.env.repo,
                'title': repo_title,
                'recordCount': self._get_person_count(self.env.repo),
            }
        return self._json_response(data)

    def _select_repo_title(self, titles, language_options):
        if self.env.lang in titles:
            return titles[self.env.lang]
        else:
            return titles[language_options[0]]

    def _get_person_count(self, repo_id):
        # TODO(nworden): factor this out somewhere we can share with the
        # Lite/AMP UIs. Part of me wants to just put it on model.Counter, but
        # part of me says this is frontend-y code that doesn't belong on a model
        # class.
        count = model.Counter.get_count(repo_id, 'person.all')
        if count < 100:
            return 0
        else:
            return int(round(count, -2))


class ResultsView(FrontendApiBaseView):
    """View for search results."""

    _MAX_RESULTS = 25

    def setup(self, request, *args, **kwargs):
        super(ResultsView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            get_params={'query_name': utils.strip, 'query': utils.strip})

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        # TODO(nworden): consider consolidating search stuff, especially since
        # full-text is going away.
        searcher = search.searcher.Searcher(
            self.env.repo, self.env.config.get('enable_fulltext_search'),
            ResultsView._MAX_RESULTS)
        results = searcher.search(
            self.params.query_name or self.params.query)
        return self._json_response([self._result_to_dict(r) for r in results])

    def _result_to_dict(self, person):
        photo_is_local = person.photo_is_local(self.build_absolute_uri())
        local_photo_url = (
            model.Person.get_thumbnail_url(person.photo_url) if photo_is_local
            else None)
        if (person.latest_status_source_date and
                person.latest_status_source_date > person.entry_date):
            timestamp_type = 'update'
            timestamp = person.latest_status_source_date
        else:
            timestamp_type = 'creation'
            timestamp = person.entry_date
        return {
            'personId': person.record_id,
            'fullNames': person.full_name_list,
            'alternateNames': person.alternate_names_list,
            'timestampType': timestamp_type,
            'timestamp': '%sZ' % timestamp.isoformat(),
            'localPhotoUrl': local_photo_url,
            # TODO(nworden): ask Travis/Pete if we should do something about
            # external photos here.
        }
