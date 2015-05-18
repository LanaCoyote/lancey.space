

from django.conf.urls import include, url
from . import views

urlpatterns = [
  url( r'^$', views.frontpage, name = 'frontpage' ),
  url( r'^posts$', views.post_list, name = 'post_list' ),
  url( r'^posts/(?P<pid>[0-9]+)$', views.post_detail, name = 'post_detail' ),
  url( r'^feed$', views.feed, name = 'feed' ),
  url( r'^articles$', views.articles, name = 'articles' ),
  url( r'^p(?P<pid>[0-9]+)$', views.shortlink, name = 'shortlink' ),

  url( r'^compose$', views.compose, name = 'compose' ),
]