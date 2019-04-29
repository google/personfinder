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
"""The pages for granting/revoking admin access."""

import datetime

import django.shortcuts

import modelmodule.admin_acls as admin_acls_model
import utils
import views.admin.base


class AdminAclsView(views.admin.base.AdminBaseView):
    """The admin ACLs view."""

    ACTION_ID = 'admin/acls'

    _EXPIRATION_DATE_FORMAT = '%Y-%m-%d'

    _PARAM_VALUES_TO_ADMIN_LEVELS = {
        'superadmin': admin_acls_model.AdminPermission.AccessLevel.SUPERADMIN,
        'manager': admin_acls_model.AdminPermission.AccessLevel.MANAGER,
        'moderator': admin_acls_model.AdminPermission.AccessLevel.MODERATOR,
    }

    def setup(self, request, *args, **kwargs):
        super(AdminAclsView, self).setup(request, *args, **kwargs)
        self.params.read_values(
            post_params={
                'edit_button': utils.strip,
                'email_address': utils.strip,
                'expiration_date': utils.strip,
                'level': utils.strip,
                'revoke_button': utils.strip,
            })

    def _render_form(self):
        existing_acls = admin_acls_model.AdminPermission.get_for_repo(
            self.env.repo)
        editable_acls = [
            acl for acl in existing_acls if
            self.env.user_admin_permission.compare_level_to(acl.access_level)
            >= 0]
        fixed_acls = [
            acl for acl in existing_acls if
            self.env.user_admin_permission.compare_level_to(acl.access_level)
            < 0]
        default_expiration_date = (
            utils.get_utcnow() + datetime.timedelta(days=365))
        return self.render(
            'admin_acls.html',
            editable_acls=editable_acls,
            fixed_acls=fixed_acls,
            default_expiration_date=default_expiration_date,
            xsrf_token=self.xsrf_tool.generate_token(self.env.user.user_id(),
                                                     self.ACTION_ID))

    @views.admin.base.enforce_manager_admin_level
    def get(self, request, *args, **kwargs):
        """Serves GET requests with a form and list of existing ACLs.

        The returned page includes a list of all the existing ACls for the repo
        (with an option to edit or revoke them) and a form to add a new admin.
        """
        del request, args, kwargs  # unused
        return self._render_form()

    @views.admin.base.enforce_manager_admin_level
    def post(self, request, *args, **kwargs):
        """Serves POST requests, making the requested changes.

        This handler will edit, revoke, or add ACLs as requested, and then
        return the same page used for GET requests.
        """
        del request, args, kwargs  # unused
        self.enforce_xsrf(self.ACTION_ID)
        email_address = self.params.email_address
        level = AdminAclsView._PARAM_VALUES_TO_ADMIN_LEVELS[self.params.level]
        # Managers can make other people managers or moderators, and superadmins
        # can make other people any level. Moderators can't grant any
        # permissions to other people, but they can't access this page anyway,
        # so we don't need to worry about that here.
        if self.env.user_admin_permission.compare_level_to(level) < 0:
            raise django.core.exceptions.PermissionDenied
        expiration_date = datetime.datetime.strptime(
            self.params.expiration_date, AdminAclsView._EXPIRATION_DATE_FORMAT)
        # TODO(nworden): add logging for this
        if self.params.edit_button or self.params.revoke_button:
            acl = admin_acls_model.AdminPermission.get(
                self.env.repo, email_address)
            # You can't edit or revoke the permissions of someone at a higher
            # level.
            if self.env.user_admin_permission.compare_level_to(
                    acl.access_level) < 0:
                raise django.core.exceptions.PermissionDenied
            if self.params.edit_button:
                acl.access_level = level
                acl.expiration_date = expiration_date
                acl.put()
            elif self.params.revoke_button:
                acl.delete()
        else:
            admin_acls_model.AdminPermission.create(
                repo=self.env.repo,
                email_address=email_address,
                access_level=level,
                expiration_date=expiration_date).put()
        return self._render_form()
