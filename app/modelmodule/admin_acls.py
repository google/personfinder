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
"""Model for admin/moderator access control."""


from google.appengine.ext import db


class AdminPermission(db.Model):
    """Entity class for tracking admin/moderator access.

    There should be only one AdminPermission entity for any given repo/email
    address pair.
    """

    # The repository the access applies to ("global" for all repositories).
    repo = db.StringProperty(required=True)

    # The email address of the user.
    email_address = db.StringProperty(required=True)

    class AccessLevel(object):
        """An enum for the level of access the user has."""

        # Superadmins can do anything for a repo, and global superadmins can
        # create new repos.
        SUPERADMIN = 0
        # Managers have limited administrative access: e.g., they can edit
        # custom messages for their repo, but not the title.
        MANAGER = 1
        # Moderators can moderate user input.
        MODERATOR = 2

        # An ordered list of the admin access levels, from lowest to highest
        # (i.e., each level has the permissions of everything before it in the
        # list).
        ORDERING = [MODERATOR, MANAGER, SUPERADMIN]

    access_level = db.IntegerProperty(required=True)

    # The expiration date for the permission.
    expiration_date = db.DateTimeProperty(required=True)

    @staticmethod
    def _key_name(repo, email_address):
        return '%s:%s' % (repo, email_address)

    @staticmethod
    def create(repo, email_address, access_level, expiration_date):
        return AdminPermission(
            key_name=AdminPermission._key_name(repo, email_address),
            repo=repo,
            email_address=email_address,
            access_level=access_level,
            expiration_date=expiration_date)

    @staticmethod
    def get(repo, email_address):
        return AdminPermission.get_by_key_name(
            AdminPermission._key_name(repo, email_address))

    @staticmethod
    def get_for_repo(repo):
        return AdminPermission.all().filter('repo =', repo)

    def compare_level_to(self, other_level):
        """Compares the level of this permission to the given level.

        Args:
            other_level (int): An AccessLevel value to compare to.

        Returns:
            int: A negative value if this permission has a lower level, a
            positive value if this permission has a higher level, or 0 if the
            levels are the same.
        """
        if self.access_level == other_level:
            return 0
        level_index = AdminPermission.AccessLevel.ORDERING.index(
            self.access_level)
        other_level_index = AdminPermission.AccessLevel.ORDERING.index(
            other_level)
        if level_index < other_level_index:
            return -1
        else:
            return 1

    def permission_state(self):
        """Returns a string representation of the permission's state.

        This is meant for logging, not display within the user interace.
        """
        return (
            'repo: %(repo)s\n'
            'email_address: %(email_address)s\n'
            'access_level: %(access_level)d\n'
            'expiration_date: %(expiration_date)s' % {
                'repo': self.repo,
                'email_address': self.email_address,
                'access_level': self.access_level,
                'expiration_date': self.expiration_date.isoformat(),
            })
