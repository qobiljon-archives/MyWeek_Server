from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    url(r'^login$', views.handle_login),
    url(r'^register$', views.handle_register)
]

urlpatterns = format_suffix_patterns(urlpatterns)
