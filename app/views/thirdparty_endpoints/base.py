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
        #self.get_feed().write(resp, 'UTF-8')
        resp.write("""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://localhost:8000/global/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
  <updated>2011-03-11T00:00:00Z</updated>
  <entry>
    <id>https://google.org/personfinder/haiti</id>
    <published>2010-01-12T00:00:00Z</published>
    <updated>2010-01-12T00:00:00Z</updated>
    <title xml:lang="en">Haiti Earthquake</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="en">Haiti Earthquake</gpf:title>
        <gpf:title xml:lang="ht">Tranbleman Te an Ayiti</gpf:title>
        <gpf:title xml:lang="fr">Seisme en Haiti</gpf:title>
        <gpf:title xml:lang="es">Terremoto en Haiti</gpf:title>
        <gpf:read_auth_key_required>false</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>false</gpf:search_auth_key_required>
        <gpf:test_mode>false</gpf:test_mode>
        <gpf:location>
          <georss:point>18.968637 -72.284546</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
  <entry>
    <id>https://google.org/personfinder/japan</id>
    <published>2011-03-11T00:00:00Z</published>
    <updated>2011-03-11T00:00:00Z</updated>
    <title xml:lang="ja">2011 abcd</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="ja">2011 abcd</gpf:title>
        <gpf:title xml:lang="en">2011 Japan Earthquake</gpf:title>
        <gpf:title xml:lang="ko"></gpf:title>
        <gpf:title xml:lang="zh-CN">2011 abcd</gpf:title>
        <gpf:title xml:lang="zh-TW">2011 abcd</gpf:title>
        <gpf:title xml:lang="pt-BR">2011 Terremoto no Japao</gpf:title>
        <gpf:title xml:lang="es">2011 Terremoto en Japon</gpf:title>
        <gpf:read_auth_key_required>true</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>true</gpf:search_auth_key_required>
        <gpf:test_mode>false</gpf:test_mode>
        <gpf:location>
          <georss:point>38 140.7</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
</feed>
""")
        return resp


class PersonFinderAtomFeed(django.utils.feedgenerator.Atom1Feed):

    def root_attributes(self):
        res = super(PersonFinderAtomFeed, self).root_attributes()
        res['xmlns:gpf'] = 'http://schemas.google.com/personfinder/2012'
        res['xmlns:georss'] = 'http://www.georss.org/georss'
        return res
