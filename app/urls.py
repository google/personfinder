"""URL routing module."""

from django.conf import urls

import site_settings
import views.admin.statistics

_BASE_URL_PATTERNS = [('global/admin/statistics/',
                       views.admin.statistics.AdminStatisticsView.as_view)]

# pylint: disable=invalid-name
urlpatterns = [
    urls.url('^%s' % base_pattern[0], base_pattern[1]())
    for base_pattern in _BASE_URL_PATTERNS
]

if site_settings.OPTIONAL_PATH_PREFIX:
    urlpatterns += [
        urls.url(
            '^%s%s' % (site_settings.OPTIONAL_PATH_PREFIX, base_pattern[0]),
            base_pattern[1]()) for base_pattern in _BASE_URL_PATTERNS
    ]
