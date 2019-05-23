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
"""The admin create-repo page."""

import django.shortcuts

import config
import const
import model
import utils
import views.admin.base


class AdminCreateRepoView(views.admin.base.AdminBaseView):
    """The admin create-repo view."""

    ACTION_ID = 'admin/create_repo'

    def setup(self, request, *args, **kwargs):
        super(AdminCreateRepoView, self).setup(request, *args, **kwargs)
        self.params.read_values(post_params={'new_repo': utils.strip})

    @views.admin.base.enforce_superadmin_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests.

        Args:
            request: Unused.
            *args: Unused.
            **kwargs: Unused.

        Returns:
            HttpResponse: A HTTP response with the admin create-repo page.
        """
        del request, args, kwargs  # unused
        return self.render(
            'admin_create_repo.html',
            xsrf_token=self.xsrf_tool.generate_token(self.env.user.user_id(),
                                                     self.ACTION_ID))

    @views.admin.base.enforce_superadmin_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, creating a new repo.

        Creates a new repository and sets some default values (assuming the user
        has permission and a valid XSRF token).

        Args:
            request: Unused.
            *args: Unused.
            **kwargs: Unused.

        Returns:
            HttpResponse: A redirect to the new repo's admin page.
        """
        del request, args, kwargs  # unused
        self.enforce_xsrf(self.ACTION_ID)
        new_repo = self.params.new_repo
        model.Repo(
            key_name=new_repo,
            activation_status=model.Repo.ActivationStatus.STAGING,
            test_mode=False).put()
        # Provide some defaults.
        config.set_for_repo(
            new_repo,
            language_menu_options=['en', 'fr'],
            repo_titles={
                'en': 'Earthquake',
                'fr': u'S\xe9isme'
            },
            keywords='person finder, people finder, person, people, ' +
            'crisis, survivor, family',
            use_family_name=True,
            use_alternate_names=True,
            use_postal_code=True,
            allow_believed_dead_via_ui=False,
            min_query_word_length=2,
            show_profile_entry=False,
            profile_websites=const.DEFAULT_PROFILE_WEBSITES,
            map_default_zoom=6,
            map_default_center=[0, 0],
            map_size_pixels=[400, 280],
            read_auth_key_required=True,
            search_auth_key_required=True,
            deactivated=False,
            launched=False,
            deactivation_message_html='',
            start_page_custom_htmls={
                'en': '',
                'fr': ''
            },
            results_page_custom_htmls={
                'en': '',
                'fr': ''
            },
            view_page_custom_htmls={
                'en': '',
                'fr': ''
            },
            seek_query_form_custom_htmls={
                'en': '',
                'fr': ''
            },
            footer_custom_htmls={
                'en': '',
                'fr': ''
            },
            bad_words='',
            published_date=utils.get_utcnow_timestamp(),
            updated_date=utils.get_utcnow_timestamp(),
            test_mode=False,
            force_https=True,
            zero_rating_mode=False,
            time_zone_offset=0,
            time_zone_abbreviation='UTC',
        )
        return django.shortcuts.redirect(
            self.build_absolute_path('/%s/admin' % new_repo))
