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
