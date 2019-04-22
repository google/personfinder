"""Tools to help run tests against the Django app."""

import testutils.base


class TaskTestsBase(testutils.base.ServerTestsBase):
    """A base class for tests for tasks."""

    # This HTTP header should be set to make the request appear to come from App
    # Engine (other task requests are rejected).
    _REQ_HEADERS = {'HTTP_X_APPENGINE_TASKNAME': 'notempty'}

    def run_task(self, path, data={}, method='GET'):
        """Makes a request to a task handler."""
        if method == 'GET':
            return self.client.get(path, data, **TaskTestsBase._REQ_HEADERS)
        else:
            return self.client.post(path, data, **TaskTestsBase._REQ_HEADERS)
