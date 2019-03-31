from django.conf.urls import url

import djangotest


urlpatterns = [
    url(r'^djangotest/', djangotest.djangotest),
    url(r'^personfinder/djangotest/', djangotest.pf_djangotest),
    url(r'^personfinder/(?P<repo_id>.+)/djangotest/', djangotest.pf_djangotest),
    url(r'^(?P<repo_id>.+)/djangotest/', djangotest.djangotest),
]
