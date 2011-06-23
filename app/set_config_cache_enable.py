#!/usr/bin/python2.5
# Copyright 2011 Google Inc.
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

import logging

from utils import Handler, get_utcnow, set_utcnow_for_test, run
from config import caching_enable, config_cache_flush
from datetime import datetime

class SetConfigCacheEnable(Handler):
    """Enables/disables/flushes config_caches, FOR TESTING ONLY.
      
      To enable caching:
      http://localhost:8080/admin/config_cache_enable?test_mode=yes&config_cache_enable=True

      To disable caching:
      http://localhost:8080/admin/config_cache_enable?test_mode=yes&config_cache_enable=False
      
      To flush cache:
      http://localhost:8080/admin/config_cache_enable?test_mode=yes&flush_config_cache=yes
      
      To enable/disable and flush the cache together:
      http://localhost:8080/admin/config_cache_enable?test_mode=yes&flush_config_cache=yes&config_cache_enable=True/False
    """
    subdomain_required = False  # Run at the root domain, not a subdomain.

    def get(self):
        enable = self.params.config_cache_enable
        flush = self.params.flush_config_cache
        if self.is_test_mode():
            logging.info('Setting config_cache_enable to %s' % enable)
            if enable == "True":
                caching_enable(True)
            elif enable == "False":
                caching_enable(False)
                
            if flush:
                logging.info('Flushing config_cache')
                config_cache_flush()
        else: 
            return self.error(404, 'page not found')

if __name__ == '__main__':
    run(('/admin/config_cache_enable', SetConfigCacheEnable))
