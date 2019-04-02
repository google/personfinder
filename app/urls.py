from django.conf.urls import url

import site_settings
import views.admin.statistics


base_urlpatterns = [
    ('admin/statistics', 'global/admin/statistics/',
     views.admin.statistics.AdminStatisticsView.as_view)
]

urlpatterns = [
    url('^%s' % base_pattern[1], base_pattern[2](), {'action': base_pattern[0]})
    for base_pattern in base_urlpatterns
]

if site_settings.OPTIONAL_PATH_PREFIX:
    urlpatterns += [
        url('^%s%s' % (site_settings.OPTIONAL_PATH_PREFIX, base_pattern[1]),
            base_pattern[2](), {'action': base_pattern[0]})
        for base_pattern in base_urlpatterns
    ]
