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
import create
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
            repo = model.Repo.get(self.env.repo)
            if not repo:
                return self.error(404)
            # We permit requests for staging repos so that admins can preview
            # the repo. In the future we might consider requiring admin status
            # to see them, though we'd need to provide some kind of login flow
            # for that.
            if (repo.activation_status ==
                    model.Repo.ActivationStatus.DEACTIVATED):
                return self.error(404)
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


class CreateView(FrontendApiBaseView):
    """View for creating a new record."""

    def setup(self, request, *args, **kwargs):
        super(CreateView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            post_params={
                'add_note': utils.validate_yes,
                'age': utils.validate_age,
                'alternate_family_names': utils.strip,
                'alternate_given_names': utils.strip,
                'author_email': utils.strip,
                'author_made_contact': utils.validate_yes,
                'author_name': utils.strip,
                'author_phone': utils.strip,
                'users_own_email': utils.strip,
                'users_own_phone': utils.strip,
                'clone': utils.validate_yes,
                'description': utils.strip,
                'email_of_found_person': utils.strip,
                'family_name': utils.strip,
                'given_name': utils.strip,
                'home_city': utils.strip,
                'home_country': utils.strip,
                'home_neighborhood': utils.strip,
                'home_postal_code': utils.strip,
                'home_state': utils.strip,
                'last_known_location': utils.strip,
                'note_photo': utils.validate_image,
                'note_photo_url': utils.strip,
                'phone_of_found_person': utils.strip,
                'photo': utils.validate_image,
                'photo_url': utils.strip,
                'referrer': utils.strip,
                'sex': utils.validate_sex,
                'source_date': utils.strip,
                'source_name': utils.strip,
                'source_url': utils.strip,
                'status': utils.validate_status,
                'text': utils.strip,
                'own_info': utils.validate_yes,
            })
        if request.method == 'POST':
            profile_urls = []
            profile_field_index = 0
            # 100 profile URLs should be enough for anyone.
            for profile_field_index in range(100):
                field_key = 'profile-url-%d' % profile_field_index
                if field_key in self.request.POST:
                    profile_urls.append(
                        utils.strip(self.request.POST[field_key]))
                else:
                    break
            if profile_urls:
                self.params['profile_urls'] = profile_urls

    def post(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        person = create.create_person(
            repo=self.env.repo,
            config=self.env.config,
            user_ip_address=self.request.META.get('REMOTE_ADDR'),
            given_name=self.params.given_name,
            family_name=self.params.family_name,
            own_info=self.params.own_info,
            clone=self.params.clone,
            status=self.params.status,
            source_name=self.params.source_name,
            source_url=self.params.source_url,
            source_date=self.params.source_date,
            referrer=self.params.referrer,
            author_name=self.params.author_name,
            author_email=self.params.author_email,
            author_phone=self.params.author_phone,
            author_made_contact=self.params.author_made_contact,
            users_own_email=self.params.your_own_email,
            users_own_phone=self.params.your_own_phone,
            alternate_given_names=self.params.alternate_given_names,
            alternate_family_names=self.params.alternate_family_names,
            home_neighborhood=self.params.home_neighborhood,
            home_city=self.params.home_city,
            home_state=self.params.home_state,
            home_postal_code=self.params.home_postal_code,
            home_country=self.params.home_country,
            age=self.params.age,
            sex=self.params.sex,
            description=self.params.description,
            photo=self.params.photo or None,
            photo_url=self.params.photo_url,
            note_photo=self.params.note_photo or None,
            note_photo_url=self.params.note_photo_url,
            profile_urls=self.params.profile_urls,
            add_note=self.params.add_note,
            text=self.params.text,
            email_of_found_person=self.params.email_of_found_person,
            phone_of_found_person=self.params.phone_of_found_person,
            last_known_location=self.params.last_known_location,
            url_builder=self.build_absolute_uri)
        return self._json_response({'record_id': person.record_id})
