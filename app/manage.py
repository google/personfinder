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
