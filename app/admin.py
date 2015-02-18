#!/usr/bin/python2.7
# Copyright 2011 Google Inc.
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


from datetime import datetime
import simplejson
import sys

from const import *
from model import *
from utils import *
import const
import reveal
import tasks

class Handler(BaseHandler):
    # After a repository is deactivated, we still need the admin page to be
    # accessible so we can edit its settings.
    ignore_deactivation = True

    # We show global admin page, if a repo is not specified.
    repo_required = False

    def get(self):
        user = users.get_current_user()
        simplejson.encoder.FLOAT_REPR = str
        encoder = simplejson.encoder.JSONEncoder(ensure_ascii=False)
        config_json = dict((name, encoder.encode(self.config[name]))
                           for name in self.config.keys())
        #sorts languages by exonym; to sort by code, remove the key argument
        sorted_exonyms = sorted(list(const.LANGUAGE_EXONYMS.items()),
                                key= lambda lang: lang[1])
        sorted_exonyms = map(lambda elem: {'code' : elem[0],
                                           'exonym' : elem[1]}, sorted_exonyms)
        sorted_exonyms_json = encoder.encode(sorted_exonyms)
        repo_options = [Struct(repo=repo, url=self.get_url('/admin', repo))
                        for repo in sorted(Repo.list())]
        self.render('admin.html',
                    user=user,
                    repo_options=repo_options,
                    config=self.config, config_json=config_json,
                    login_url=users.create_login_url(self.request.url),
                    logout_url=users.create_logout_url(self.request.url),
                    language_exonyms_json=sorted_exonyms_json,
                    onload_function="add_initial_languages()",
                    id=self.env.domain + '/person.',
                    test_mode_min_age_hours=
                        tasks.CleanUpInTestMode.DELETION_AGE_SECONDS / 3600.0)

    def post(self):
        if self.params.operation == 'delete':
            # Redirect to the deletion handler with a valid signature.
            action = ('delete', str(self.params.id))
            self.redirect('/delete', id=self.params.id,
                          signature=reveal.sign(action))

        elif self.params.operation == 'create_repo':
            new_repo = self.params.new_repo
            Repo(key_name=new_repo).put()
            config.set_for_repo(  # Provide some defaults.
                new_repo,
                language_menu_options=['en', 'fr'],
                repo_titles={'en': 'Earthquake', 'fr': u'S\xe9isme'},
                keywords='person finder, people finder, person, people, ' +
                    'crisis, survivor, family',
                use_family_name=True,
                use_alternate_names=True,
                use_postal_code=True,
                allow_believed_dead_via_ui=False,
                min_query_word_length=2,
                show_profile_entry=False,
                profile_websites=DEFAULT_PROFILE_WEBSITES,
                map_default_zoom=6,
                map_default_center=[0, 0],
                map_size_pixels=[400, 280],
                read_auth_key_required=True,
                search_auth_key_required=True,
                deactivated=False,
                deactivation_message_html='',
                start_page_custom_htmls={'en': '', 'fr': ''},
                results_page_custom_htmls={'en': '', 'fr': ''},
                view_page_custom_htmls={'en': '', 'fr': ''},
                seek_query_form_custom_htmls={'en': '', 'fr': ''},
                footer_custom_htmls={'en': '', 'fr': ''},
                bad_words='',
                published_date=get_utcnow_timestamp(),
                updated_date=get_utcnow_timestamp(),
                test_mode=False,
                force_https=False,
            )
            self.redirect('/admin', new_repo)

        elif self.params.operation == 'save_repo':
            if not self.repo:
                self.redirect('/admin')
                return

            if self.__update_config(
                    self.repo,
                    # These settings are all entered in JSON.
                    json_config_names=[
                        'language_menu_options', 'repo_titles',
                        'use_family_name', 'family_name_first',
                        'use_alternate_names',
                        'use_postal_code', 'allow_believed_dead_via_ui',
                        'min_query_word_length', 'map_default_zoom',
                        'show_profile_entry', 'profile_websites',
                        'map_default_center', 'map_size_pixels',
                        'read_auth_key_required', 'search_auth_key_required',
                        'deactivated', 'start_page_custom_htmls',
                        'results_page_custom_htmls', 'view_page_custom_htmls',
                        'seek_query_form_custom_htmls', 'footer_custom_htmls',
                        'test_mode', 'force_https',
                    ],
                    # These settings are literal strings (not JSON).
                    literal_config_names=[
                        'keywords', 'deactivation_message_html', 'bad_words',
                    ],
                    # Update updated_date if any of the following settings are changed.
                    updating_config_names=[
                        'deactivated', 'test_mode',
                    ]):
                self.redirect('/admin')

        elif self.params.operation == 'save_global':
            if self.__update_config(
                    '*',
                    # These settings are all entered in JSON.
                    json_config_names=[
                        'sms_number_to_repo',
                    ],
                    # These settings are literal strings (not JSON).
                    literal_config_names=[
                    ]):
                self.redirect('/admin')

    def __update_config(
            self,
            repo,
            json_config_names,
            literal_config_names,
            updating_config_names=[]):
        values = {}
        for name in json_config_names:
            try:
                values[name] = simplejson.loads(self.request.get(name))
            except:
                self.error(
                    400, 'The setting for %s was not valid JSON.' % name)
                return False

        for name in literal_config_names:
            values[name] = self.request.get(name)

        for name in updating_config_names:
            if config.get_for_repo(repo, name) != values[name]:
                values['updated_date'] = get_utcnow_timestamp()
                break

        config.set_for_repo(repo, **values)
        return True
