

from django.conf.urls import include, url
from . import views

urlpatterns = [
  url( r'^$',         views.auth, name = 'authenticate' ),
  url( r'^logout/$',  views.log_out, name = 'logout' ),
]