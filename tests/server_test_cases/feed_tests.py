# encoding: utf-8
# Copyright 2010 Google Inc.
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

"""Test cases for end-to-end testing.  Run with the server_tests script."""

import datetime
from const import ROOT_URL
from model import *
from test_pfif import text_diff
import utils
from server_tests_base import ServerTestsBase


class FeedTests(ServerTestsBase):
    """Tests atom feeds.

    TODO(ryok): move feed tests from PersonNoteTests to FeedTests.
    """
    def setUp(self):
        ServerTestsBase.setUp(self)
        self.configure_api_logging()

    def tearDown(self):
        config.set_for_repo('haiti', deactivated=False)
        config.set_for_repo('japan', test_mode=False)
        ServerTestsBase.tearDown(self)

    def test_repo_feed_non_existing_repo(self):
        self.go('/none/feeds/repo')
        assert self.s.status == 404

    def test_repo_feed_deactivated_repo(self):
        config.set_for_repo('haiti', deactivated=True)
        doc = self.go('/haiti/feeds/repo')
        expected_content = '''\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://%s/personfinder/haiti/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
</feed>
''' % self.hostport
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

    def test_repo_feed_activated_repo(self):
        doc = self.go('/haiti/feeds/repo')
        expected_content = u'''\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://%s/personfinder/haiti/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
  <updated>2010-01-12T00:00:00Z</updated>
  <entry>
    <id>%s/haiti</id>
    <published>2010-01-12T00:00:00Z</published>
    <updated>2010-01-12T00:00:00Z</updated>
    <title xml:lang="en">Haiti Earthquake</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="en">Haiti Earthquake</gpf:title>
        <gpf:title xml:lang="ht">Tranbleman Tè an Ayiti</gpf:title>
        <gpf:title xml:lang="fr">Séisme en Haïti</gpf:title>
        <gpf:title xml:lang="es">Terremoto en Haití</gpf:title>
        <gpf:read_auth_key_required>false</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>false</gpf:search_auth_key_required>
        <gpf:test_mode>false</gpf:test_mode>
        <gpf:location>
          <georss:point>18.968637 -72.284546</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
</feed>
''' % (self.hostport, ROOT_URL)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # verify we logged the repo read.
        self.verify_api_log(ApiActionLog.REPO, api_key='')

    def test_repo_feed_all_launched_repos(self):
        haiti_repo = Repo.get('haiti')
        haiti_repo.activation_status = Repo.ActivationStatus.DEACTIVATED
        haiti_repo.put()
        japan_repo = Repo.get('japan')
        japan_repo.activation_status = Repo.ActivationStatus.ACTIVE
        japan_repo.put()
        config.set_for_repo(
                'japan', test_mode=True,
                updated_date=utils.get_timestamp(
                        datetime.datetime(2012, 03, 11)))
        config.set_for_repo('pakistan', test_mode=False)

        # 'haiti', 'japan', and 'pakistan' exist in the datastore. Only those
        # which are 'launched' and not 'deactivated' i.e., only 'japan' should
        # appear in the feed.
        doc = self.go('/global/feeds/repo')
        expected_content = u'''\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:gpf="http://schemas.google.com/personfinder/2012"
      xmlns:georss="http://www.georss.org/georss">
  <id>http://%s/personfinder/global/feeds/repo</id>
  <title>Person Finder Repository Feed</title>
  <updated>2012-03-11T00:00:00Z</updated>
  <entry>
    <id>%s/japan</id>
    <published>2011-03-11T00:00:00Z</published>
    <updated>2012-03-11T00:00:00Z</updated>
    <title xml:lang="ja">2011 日本地震</title>
    <content type="text/xml">
      <gpf:repo>
        <gpf:title xml:lang="ja">2011 日本地震</gpf:title>
        <gpf:title xml:lang="en">2011 Japan Earthquake</gpf:title>
        <gpf:title xml:lang="ko"></gpf:title>
        <gpf:title xml:lang="zh-CN">2011 日本地震</gpf:title>
        <gpf:title xml:lang="zh-TW">2011 日本地震</gpf:title>
        <gpf:title xml:lang="pt-BR">2011 Terremoto no Japão</gpf:title>
        <gpf:title xml:lang="es">2011 Terremoto en Japón</gpf:title>
        <gpf:read_auth_key_required>true</gpf:read_auth_key_required>
        <gpf:search_auth_key_required>true</gpf:search_auth_key_required>
        <gpf:test_mode>true</gpf:test_mode>
        <gpf:location>
          <georss:point>38 140.7</georss:point>
        </gpf:location>
      </gpf:repo>
    </content>
  </entry>
</feed>
''' % (self.hostport, ROOT_URL)
        assert expected_content == doc.content, \
            text_diff(expected_content, doc.content)

        # verify we logged the repo read.
        self.verify_api_log(ApiActionLog.REPO, api_key='')
