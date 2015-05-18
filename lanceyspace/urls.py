"""lanceyspace URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

urlpatterns = [
    url(r'^',               include('grmblgrmbl.urls')),
    url(r'^auth/',          include('indieauth.urls')),
    #url(r'^webmention/',   include('webmention.urls')), # Webmention endpoint
    url(r'^admin/',         include(admin.site.urls)),
    url(r'^google7110dd68f0e6bdee.html$', lambda r : render( r, 'google7110dd68f0e6bdee.html') )    # Google verification
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
