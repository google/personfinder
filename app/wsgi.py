"""Entrypoint to the Django WSGI app."""

import os
import sys

from django.core import wsgi

sys.path.append(os.path.join(os.path.dirname(__file__), 'vendors'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# pylint: disable=invalid-name
# Pylint doesn't like it being lower-case, but we call it this anyway because
# it's conventional with Django.
application = wsgi.get_wsgi_application()
