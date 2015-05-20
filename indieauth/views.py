from django.shortcuts import render
from django.http import HttpResponseForbidden, HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.contrib.auth import login, logout, authenticate

# Create your views here.

def auth ( request ) :
  if request.GET.has_key( "code" ) :
    user = authenticate( code = request.GET['code'] )

    try:
      if user and user.is_active :
        login( request, user )
        return HttpResponseRedirect( "/" )
      else :
        # User can't log in because they don't exist or are marked inactive
        return HttpResponseForbidden()
    except Exception as e :
      return HttpResponseBadRequest( str(e) )
  else :
    return HttpResponseBadRequest()

def log_out( request ) :
  try :
    logout( request )
    return HttpResponseRedirect( "/" )
  except Exception as e :
    return HttpResponseBadRequest( str( e ) )