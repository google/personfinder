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
        view_config = self.__model_config_to_view_config(self.config)
        view_config_json = dict(
                (name, encoder.encode(value))
                for name, value in view_config.iteritems())
        all_view_config_json = encoder.encode(view_config)
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
                    view_config=view_config,
                    view_config_json=view_config_json,
                    all_view_config_json=all_view_config_json,
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
                launched=False,
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
                        'allow_believed_dead_via_ui',
                        'family_name_first',
                        'footer_custom_htmls',
                        'force_https',
                        'language_menu_options',
                        'map_default_center',
                        'map_default_zoom',
                        'map_size_pixels',
                        'min_query_word_length',
                        'profile_websites',
                        'read_auth_key_required',
                        'repo_titles',
                        'results_page_custom_htmls',
                        'search_auth_key_required',
                        'seek_query_form_custom_htmls',
                        'show_profile_entry',
                        'start_page_custom_htmls',
                        'test_mode',
                        'use_alternate_names',
                        'use_family_name',
                        'use_postal_code',
                        'view_page_custom_htmls',
                    ],
                    # These settings are literal strings (not JSON).
                    literal_config_names=[
                        'bad_words',
                        'deactivation_message_html',
                        'keywords',
                        'launch_status',
                    ],
                    # Update updated_date if any of the following settings are
                    # changed.
                    updating_config_names=[
                        'launch_status',
                        'test_mode',
                    ]):
                self.redirect('/admin')

        elif self.params.operation == 'save_global':
            if self.__update_config(
                    '*',
                    # These settings are all entered in JSON.
                    json_config_names=[
                        'sms_number_to_repo',
                        'repo_aliases',
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

        orig_view_config = self.__model_config_to_view_config(
                config.Configuration(repo))
        for name in updating_config_names:
            if orig_view_config.get(name) != values[name]:
                values['updated_date'] = get_utcnow_timestamp()
                break

        config.set_for_repo(repo, **self.__view_config_to_model_config(values))
        return True

    def __model_config_to_view_config(self, model_config):
        """Converts the config in the database to the config for admin page
        rendering."""
        view_config = {}
        for name, value in model_config.iteritems():
            if name not in ['deactivated', 'launched']:
                view_config[name] = value

        if model_config.deactivated:
            view_config['launch_status'] = 'deactivated'
        elif model_config.launched:
            view_config['launch_status'] = 'activated'
        else:
            view_config['launch_status'] = 'staging'

        return view_config

    def __view_config_to_model_config(self, view_config):
        """Converts the config for admin page rendering to the config in the
        database."""
        model_config = {}
        for name, value in view_config.iteritems():
            if name == 'launch_status':
                if value == 'staging':
                    model_config['deactivated'] = False
                    model_config['launched'] = False
                elif value == 'activated':
                    model_config['deactivated'] = False
                    model_config['launched'] = True
                elif value == 'deactivated':
                    model_config['deactivated'] = True
                    model_config['launched'] = False
                else:
                    raise Exception(
                            'Invalid value for config.launch_status: %p'
                            % value)
            else:
                model_config[name] = value
        return model_config
