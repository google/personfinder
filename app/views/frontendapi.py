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


class ResultsView(FrontendApiBaseView):
    """View for returning search results."""

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
            'timestamp': timestamp.isoformat(),
            'localPhotoUrl': local_photo_url,
            # TODO(nworden): ask Travis/Pete if we should do something about
            # external photos here.
        }
