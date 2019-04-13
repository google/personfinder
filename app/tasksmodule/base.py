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
"""Code shared by task view modules."""

import logging

import django.http

import utils
import views.base


class TasksBaseView(views.base.BaseView):
    """Base view for task views."""

    def dispatch(self, request, *args, **kwargs):
        """See docs on django.views.View.dispatch."""
        # If the X-AppEngine-TaskQueue header is set, it means the request came
        # from App Engine, not an external user:
        # https://cloud.google.com/appengine/docs/standard/python/taskqueue/push/creating-handlers#reading_request_headers
        # There are various reasons we'd prefer to prevent external users from
        # starting up tasks (e.g., because some tasks might be expensive
        # operations).
        if not (request.META.get('X-AppEngine-TaskName') or
                utils.is_dev_app_server()):
            logging.warn('Non-taskqueue access of: %s' % self.request.path)
            return django.http.HttpResponse(status=403)
        return super(TasksBaseView, self).dispatch(request, args, kwargs)
