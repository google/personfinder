#!/usr/bin/python2.5
# Copyright 2010 Google Inc.
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

"""User-agent detection utilities."""

import re

# Regular expression to detect Japanese Tier-2 mobile phones.
JP_TIER2_MOBILE_USER_AGENT_RE = re.compile(
    r'^(KDDI|DoCoMo|SoftBank|J-PHONE|Vodafone)')

def is_jp_tier2_mobile_phone(request):
    """Returns True if the given request is from a Japanese Tier-2
    mobile phone, based on the User-Agent header in the request."""
    user_agent = request.headers.get('User-Agent')
    return user_agent and JP_TIER2_MOBILE_USER_AGENT_RE.match(user_agent)
