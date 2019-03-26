from django.conf.urls import url

import controller

urlpatterns = [
    url(r'^diff/results', controller.DiffController.as_view()),
    url(r'^validate/results', controller.ValidatorController.as_view()),
]
