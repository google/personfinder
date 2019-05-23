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

"""The admin statistics page."""

import const
import model
import views.admin.base


class AdminStatisticsView(views.admin.base.AdminBaseView):
    """The admin statistics view."""

    ACTION_ID = 'admin/statistics'

    @views.admin.base.enforce_manager_admin_level
    def get(self, request, *args, **kwargs):
        """Serves get requests.

        Args:
            request: Unused.
            *args: Unused.
            **kwargs: Unused.

        Returns:
            HttpResponse: A HTTP response with the admin statistics page.
        """
        del request, args, kwargs  # unused
        repos = sorted(model.Repo.list())
        all_usage = [_get_repo_usage(repo) for repo in repos]
        note_status_list = []
        for note_status in const.NOTE_STATUS_TEXT:
            if not note_status:
                note_status_list.append('num_notes_unspecified')
            else:
                note_status_list.append('num_notes_' + note_status)
        return self.render(
            'admin_statistics.html',
            all_usage=all_usage,
            note_status_list=note_status_list)


def _get_repo_usage(repo):
    """Gets number of persons and notes for a specific repository.

    Args:
        repo (str): The repository ID.

    Returns:
        dict: A dictionary containing, for each repository, the repository ID,
        the number of persons, and the number of notes. E.g.:
        {'repo': haiti, 'num_persons': 10, 'num_notes': 5, ...etc.}
    """
    counters = model.UsageCounter.get(repo)
    repo_usage = {
        'repo': repo,
        'num_persons': getattr(counters, 'person', 0),
        'num_notes': getattr(counters, 'note', 0)
    }
    for note_status in const.NOTE_STATUS_TEXT:
        if not note_status:
            note_status = 'unspecified'
        repo_usage['num_notes_' + note_status] = (getattr(
            counters, note_status, 0))
    return repo_usage
