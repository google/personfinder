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
"""URL routing module."""

from django.conf import urls

import site_settings
import tasksmodule.datachecks
import tasksmodule.deletion
import tasksmodule.sitemap_ping
import views.admin.acls
import views.admin.api_keys
import views.admin.create_repo
import views.admin.dashboard
import views.admin.delete_record
import views.admin.global_index
import views.admin.repo_index
import views.admin.review
import views.admin.statistics
import views.enduser.global_index
import views.frontendapi
import views.meta.setup_datastore
import views.meta.sitemap
import views.meta.static_files
import views.meta.static_pages
import views.thirdparty_endpoints.repo_feed

# We include an optional trailing slash in all the patterns (Django has support
# for automatic redirection, but we don't want to send people redirect responses
# if it's not really needed).
_BASE_URL_PATTERNS = [
    ('admin_acls', r'(?P<repo>[^\/]+)/admin/acls/?',
     views.admin.acls.AdminAclsView.as_view),
    ('admin_apikeys-list', r'(?P<repo>[^\/]+)/admin/api_keys/list/?',
     views.admin.api_keys.ApiKeyListView.as_view),
    ('admin_apikeys-manage', r'(?P<repo>[^\/]+)/admin/api_keys/?',
     views.admin.api_keys.ApiKeyManagementView.as_view),
    ('admin_create-repo', r'global/admin/create_repo/?',
     views.admin.create_repo.AdminCreateRepoView.as_view),
    ('admin_dashboard', r'(?P<repo>[^\/]+)/admin/dashboard/?',
     views.admin.dashboard.AdminDashboardView.as_view),
    ('admin_delete-record', r'(?P<repo>[^\/]+)/admin/delete_record/?',
     views.admin.delete_record.AdminDeleteRecordView.as_view),
    ('admin_global-index', r'global/admin/?',
     views.admin.global_index.AdminGlobalIndexView.as_view),
    ('admin_repo-index', r'(?P<repo>[^\/]+)/admin/?',
     views.admin.repo_index.AdminRepoIndexView.as_view),
    ('admin_review', r'(?P<repo>[^\/]+)/admin/review/?',
     views.admin.review.AdminReviewView.as_view),
    ('admin_statistics', r'global/admin/statistics/?',
     views.admin.statistics.AdminStatisticsView.as_view),
    ('frontendapi_add-note', r'(?P<repo>[^\/]+)/d/add_note/?',
     views.frontendapi.AddNoteView.as_view),
    ('frontendapi_create', r'(?P<repo>[^\/]+)/d/create/?',
     views.frontendapi.CreateView.as_view),
    ('frontendapi_person', r'(?P<repo>[^\/]+)/d/person/?',
     views.frontendapi.PersonView.as_view),
    ('frontendapi_repo', r'(?P<repo>[^\/]+)/d/repo/?',
     views.frontendapi.RepoView.as_view),
    ('frontendapi_results', r'(?P<repo>[^\/]+)/d/results/?',
     views.frontendapi.ResultsView.as_view),
    ('meta_setup-datastore', r'setup_datastore/?',
     views.meta.setup_datastore.SetupDatastoreHandler.as_view),
    ('meta_sitemap', r'global/sitemap/?',
     views.meta.sitemap.SitemapView.as_view),
    ('meta_static-files', r'(?P<repo>[^\/]+)/static/(?P<filename>.+)',
     views.meta.static_files.ConfigurableStaticFileView.as_view),
    # The regular global homepage path is in _STARTING_SLASH_URL_PATTERNS below.
    ('enduser_global-index-altpath', r'global/home.html',
     views.enduser.global_index.GlobalIndexView.as_view),
    ('enduser_global-index-altpath2', r'global/?',
     views.enduser.global_index.GlobalIndexView.as_view),
    ('meta_static-howto', r'global/howto.html',
     views.meta.static_pages.HowToView.as_view),
    ('meta_static-responders', r'global/responders.html',
     views.meta.static_pages.RespondersView.as_view),
    ('tasks_process-expirations',
     r'(?P<repo>[^\/]+)/tasks/process_expirations/?',
     tasksmodule.deletion.ProcessExpirationsTask.as_view),
    ('tasks_check-expired-person-records',
     r'(?P<repo>[^\/]+)/tasks/check_expired_person_records/?',
     tasksmodule.datachecks.ExpiredPersonRecordCheckTask.as_view),
    ('tasks_check-person-data-validity',
     r'(?P<repo>[^\/]+)/tasks/check_person_data_validity/?',
     tasksmodule.datachecks.PersonDataValidityCheckTask.as_view),
    ('tasks_check-note-data-validity',
     r'(?P<repo>[^\/]+)/tasks/check_note_data_validity/?',
     tasksmodule.datachecks.NoteDataValidityCheckTask.as_view),
    ('tasks_cleanup-stray-notes',
     r'(?P<repo>[^\/]+)/tasks/cleanup_stray_notes/?',
     tasksmodule.deletion.CleanupStrayNotesTask.as_view),
    ('tasks_cleanup-stray-subscriptions',
     r'(?P<repo>[^\/]+)/tasks/cleanup_stray_subscriptions/?',
     tasksmodule.deletion.CleanupStraySubscriptionsTask.as_view),
    ('tasks_sitemap-ping', r'global/tasks/sitemap_ping/?',
     tasksmodule.sitemap_ping.SitemapPingTaskView.as_view),
    ('thirdparty-endpoints_repo-feed', r'(?P<repo>[^\/]+)/feeds/repo/?',
     views.thirdparty_endpoints.repo_feed.RepoFeedView.as_view),
]

# This pattern can't be automatically prefixed like the others, because it'll
# end up with a repeated slash ("personfinder//?").
_STARTING_SLASH_URL_PATTERNS = [
    ('enduser_global-index', r'/?',
     views.enduser.global_index.GlobalIndexView.as_view),
]

# pylint: disable=invalid-name
# Pylint would prefer that this name be uppercased, but Django's going to look
# for this value in the urls module; it has to be called urlpatterns.
urlpatterns = [
    urls.url('^%s$' % path_exp, view_func(), name=name)
    for (name, path_exp, view_func) in _BASE_URL_PATTERNS
]

starting_slash_urlpatterns = [
    urls.url('^%s$' % path_exp, view_func(), name=name)
    for (name, path_exp, view_func) in _STARTING_SLASH_URL_PATTERNS
]

if site_settings.OPTIONAL_PATH_PREFIX:
    urlpatterns += [
        urls.url(
            '^%(prefix)s/%(path)s$' % {
                'prefix': site_settings.OPTIONAL_PATH_PREFIX,
                'path': path_exp
            },
            view_func(),
            name='prefixed__%s' % name)
        for (name, path_exp, view_func) in _BASE_URL_PATTERNS
    ]
    starting_slash_urlpatterns += [
        urls.url(
            '^%(prefix)s%(path)s$' % {
                'prefix': site_settings.OPTIONAL_PATH_PREFIX,
                'path': path_exp
            },
            view_func(),
            name='prefixed__%s' % name)
        for (name, path_exp, view_func) in _STARTING_SLASH_URL_PATTERNS
    ]

urlpatterns += starting_slash_urlpatterns
