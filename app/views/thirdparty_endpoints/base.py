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

import django.utils.feedgenerator

import model
import utils
import views.base


class ThirdPartyEndpointBaseView(views.base.BaseView):
    """Base view for third-party endpoint views."""

    def setup(self, request, *args, **kwargs):
        """See docs on BaseView.setup."""
        # pylint: disable=attribute-defined-outside-init
        super(ThirdPartyEndpointBaseView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            get_params={'key': utils.strip},
            post_params={'key': utils.strip})
        self._set_auth()

    def _set_auth(self):
        self.auth = None
        if self.params.key:
            if self.env.repo != '*':
                self.auth = model.Authorization.get(
                    self.env.repo, self.params.key)
            if not self.auth:
                # If their key isn't a valid repo key, perhaps it's a global API
                # key.
                self.auth = model.Authorization.get('*', self.params.key)
        if self.auth and not self.auth.is_valid:
            self.auth = None

    def dispatch(self, request, *args, **kwargs):
        """See docs on django.views.View.dispatch."""
        if self.env.repo != 'global':
            repo_obj = model.Repo.get(self.env.repo)
            if not repo_obj:
                return self.error(404)
            if repo_obj.activation_status != model.Repo.ActivationStatus.ACTIVE:
                # TODO(nworden): something better
                return self.error(404)
        self.check_auth()
        return super(ThirdPartyEndpointBaseView, self).dispatch(
            request, args, kwargs)

    def check_auth(self):
        """Checks that the user is authorized.

        Should be implemented by subclasses.
        """
        raise NotImplementedError()

    def log_api_action(
            self, action, num_person_records=0, num_note_records=0,
            people_skipped=0, notes_skipped=0):
        version = None
        if self.params.version:
            version = self.params.version.version
        model.ApiActionLog.record_action(
            self.env.repo,
            self.params.key,
            version,
            action,
            num_person_records,
            num_note_records,
            people_skipped,
            notes_skipped,
            self.request.META.get('HTTP_USER_AGENT'),
            self.request.META.get('REMOTE_ADDR'),
            self.build_absolute_uri())


class ThirdPartyFeedBaseView(ThirdPartyEndpointBaseView):

    def get_feed(self, resp):
        """Get the feed to write to the response.

        Should be implemented by subclasses.

        Returns:
            SyndicationFeed: A Django SyndicationFeed object.
        """
        raise NotImplementedError()

    def get(self, request, *args, **kwargs):
        del request, args, kwargs  # Unused.
        resp = django.http.HttpResponse()
        resp['Content-Type'] = 'application/xml; charset=utf-8'
        self.get_feed().write(resp, 'UTF-8')
        return resp


class PersonFinderAtomFeed(django.utils.feedgenerator.Atom1Feed):

    def root_attributes(self):
        res = super(PersonFinderAtomFeed, self).root_attributes()
        res['xmlns:gpf'] = 'http://schemas.google.com/personfinder/2012'
        res['xmlns:georss'] = 'http://www.georss.org/georss'
        return res
