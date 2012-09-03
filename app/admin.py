#!/usr/bin/python2.5
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

from model import *
from utils import *
import const
import reveal
import tasks

class Handler(BaseHandler):
    # After a repository is deactivated, we still need the admin page to be
    # accessible so we can edit its settings.
    ignore_deactivation = True

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
                bad_words='',
                published_date=get_utcnow_timestamp(),
                updated_date=get_utcnow_timestamp(),
                test_mode=False,
            )
            self.redirect('/admin', new_repo)

        elif self.params.operation == 'save_repo':
            values = {}
            for name in [  # These settings are all entered in JSON.
                'language_menu_options', 'repo_titles',
                'use_family_name', 'family_name_first', 'use_alternate_names',
                'use_postal_code', 'allow_believed_dead_via_ui',
                'min_query_word_length', 'map_default_zoom',
                'map_default_center', 'map_size_pixels',
                'read_auth_key_required', 'search_auth_key_required',
                'deactivated', 'start_page_custom_htmls',
                'results_page_custom_htmls', 'view_page_custom_htmls',
                'seek_query_form_custom_htmls',
                'test_mode',
            ]:
                try:
                    values[name] = simplejson.loads(self.request.get(name))
                except:
                    return self.error(
                        400, 'The setting for %s was not valid JSON.' % name)

            for name in ['keywords', 'deactivation_message_html', 'bad_words']:
                # These settings are literal strings (not JSON).
                values[name] = self.request.get(name)

            # Update updated_date if any of the following settings are changed.
            for name in ['deactivated', 'test_mode']:
                if config.get_for_repo(self.repo, name) != values[name]:
                    values['updated_date'] = get_utcnow_timestamp()
                    break

            config.set_for_repo(self.repo, **values)
            self.redirect('/admin')
