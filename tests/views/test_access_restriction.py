import urls
import views

import django_tests_base


class AccessRestrictionTests(django_tests_base.DjangoTestsBase):

    IS_RESTRICTED_TO_ADMINS = {
        views.admin.statistics.AdminStatisticsView: True,
    }

    def test_restricted_to_admins(self):
        for cls in filter(
            lambda item: item[1],
            AccessRestrictionTests.IS_RESTRICTED_TO_ADMINS.items()):
            print cls

    def test_all_views_included(self):
        for pattern in urls.urlpatterns:
            raise Exception(pattern.callback.__name__)
