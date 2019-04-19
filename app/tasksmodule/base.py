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

import model
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
        # Django renames headers, so X-AppEngine-TaskName will be in the META
        # dictionary as HTTP_X_APPENGINE_TASKNAME:
        # https://docs.djangoproject.com/en/1.11/ref/request-response/#django.http.HttpRequest.META
        if not (request.META.get('HTTP_X_APPENGINE_TASKNAME') or
                utils.is_dev_app_server()):
            logging.warn('Non-taskqueue access of: %s' % self.request.path)
            return self.error(403)
        return super(TasksBaseView, self).dispatch(request, args, kwargs)


class PerRepoTaskBaseView(TasksBaseView):
    """Base class for tasks that should be split up by repo.

    It's fairly common for our cron jobs to be split up by repo (it's the only
    good way we've thought of to split them up).

    GET requests are used for kicking the jobs off. Subclasses should implement
    their operations in the POST handler, and should implement schedule_task to
    handle their task names, parameters, etc.
    """

    def schedule_task(self, repo, **kwargs):
        """Schedules a new or continuation task."""
        del self, repo, kwargs  # unusued
        raise NotImplementedError()

    def get(self, request, *args, **kwargs):
        """Schedules tasks."""
        del request, args, kwargs  # unused
        if self.env.repo == 'global':
            for repo in model.Repo.list():
                self.schedule_task(repo)
        else:
            self.schedule_task(self.env.repo)
        return django.http.HttpResponse('')

    def post(self, request, *args, **kwargs):
        """Carries out task operations."""
        del request, args, kwargs  # unused
        raise NotImplementedError()
