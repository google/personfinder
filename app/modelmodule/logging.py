"""Entities for logging permissions changes and other such things."""


from google.appengine.ext import db


class AdminPermissionManagementLog(db.Model):
    """An entity class for logging changes to admin permissions."""

    # The email address of the admin making the change.
    managing_admin_email = db.StringProperty(required=True)

    # The IP address of the user making the change.
    ip_address = db.StringProperty(required=True)

    # The time of the change.
    timestamp = db.DateTimeProperty(auto_now_add=True)

    # The repo the permission is for, or "global".
    repo = db.StringProperty(required=True)

    # The user the permission is for.
    email_address = db.StringProperty(required=True)

    class Action(object):
        """An enum for the types of change that can be made."""
        CREATE = 0
        UPDATE = 1
        REVOKE = 2
        ALL = [CREATE, UPDATE, REVOKE]

    action = db.IntegerProperty(required=True, choices=Action.ALL)

    # The state of the permission after this change was made (empty if the
    # permission was deleted).
    permission_state = db.TextProperty()
