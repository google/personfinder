import const
import model
import utils
import views.admin.base


class AdminStatisticsView(views.admin.base.AdminBaseView):

    def get(self, request, *args, **kwargs):
        repos = sorted(model.Repo.list())
        all_usage = [self._get_repo_usage(repo) for repo in repos]
        note_status_list = []
        for note_status in const.NOTE_STATUS_TEXT:
            if not note_status:
                note_status_list.append('num_notes_unspecified')
            else:
                note_status_list.append('num_notes_' + note_status)
        return self.render('admin_statistics.html',
                           all_usage=all_usage,
                           note_status_list=note_status_list)

    def _get_repo_usage(self, repo):
        """Gets number of persons and notes for a specific repository.

        Args:
            repo (str): The repository ID.

        Returns:
            dict: A dictionary containing, for each repository, the repository
            ID, the number of persons, and the number of notes. E.g.:
            {'repo': haiti, 'num_persons': 10, 'num_notes': 5, ...etc.}
        """
        counters = model.UsageCounter.get(repo)
        repo_usage = {'repo': repo,
                      'num_persons': getattr(counters, 'person', 0),
                      'num_notes': getattr(counters, 'note', 0)}
        for note_status in const.NOTE_STATUS_TEXT:
            if not note_status:
                note_status = 'unspecified'
            repo_usage['num_notes_' + note_status] = (
                getattr(counters, note_status, 0))
        return repo_usage
