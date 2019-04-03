"""Django management script.

This can be used to run a local Django server (which is not particularly useful
now, when we depend on so many App Engine APIs, but will be useful once we
migrate off them).
"""

import os
import sys

from django.core import management


if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    management.execute_from_command_line(sys.argv)
