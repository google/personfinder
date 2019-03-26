from django.conf.urls import url

import controller

urlpatterns = [
    url(r'^test', controller.test_view),
]
