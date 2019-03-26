from django.conf.urls import url

import controller

urlpatterns = [
    url(r'^validate/results', controller.ValidatorController.as_view()),
]
