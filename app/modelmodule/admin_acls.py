"""Model for admin/moderator access control."""


from google.appengine.ext import db


class AdminAcl(db.Model):
    """Entity class for tracking admin/moderator access."""

    # The repository the access applies to ("global" for all repositories).
    repo = db.StringProperty(required=True)

    class AccessLevel(object):
        """An enum for the level of access the user has."""
        # Full admin access: the admin can edit the repo, add new admins, etc.
        FULL_ADMIN = 0
        # Moderator access: the admin can moderate user input, but not anything
        # else.
        MODERATOR = 1

    access_level = db.IntegerProperty(required=True)

    # The email address of the user.
    email_address = db.StringProperty(required=True)

    # The expiration date for the permission.
    expiration_date = db.DateTimeProperty(required=True)
