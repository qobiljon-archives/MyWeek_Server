from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
	url(r'^create$', views.create_event),
	url(r'^categories', views.get_categorycodes),
	url(r'^constants', views.get_constants),
	url(r'^suggest$', views.get_suggestion),
	url(r'^fetch$', views.get_events),
	url(r'^isfree$', views.check_periodfree),
	url(r'^find$', views.get_event_by_id),
	url(r'^disable$', views.disable_event),
	url(r'^flushdb$', views.flushdb),
	url(r'^populate$', views.populate)
]

urlpatterns = format_suffix_patterns(urlpatterns)
