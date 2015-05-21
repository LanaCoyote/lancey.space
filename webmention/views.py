import re
import requests
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from grmblgrmbl.models import Post

# Create your views here.

@csrf_exempt
def endpoint ( request ) :
  if request.method == "POST" :

    # Check that the POST request is a valid Webmention with a source and target
    if not request.POST.has_key( "source" ) or not request.POST.has_key( "target" ) :
      return HttpResponseBadRequest( content = "Source or target URL not provided." )

    # TODO: validate the source, check if it has a vouch, confirm the vouch, and proceed

    # Check that the target of the Webmention can accept Webmentions
    pattern = r"lancey.space/posts/(\d+)"
    match   = re.search( pattern, request.POST["target"] )
    if match :
      try :
        # Get the post associated with the target
        post = Post.objects.get( pk = int(match.group( 1 )) )
      except :
        return HttpResponseBadRequest( content = "Specified target URL does not accept webmentions." )
    else :
      return HttpResponseBadRequest( content = "Invalid target URL provided." )

    # Check that the source of the Webmention contains a valid link to the target
    srcrq   = requests.get( request.POST["source"] )

    if not srcrq.headers['Content-Type'].startswith( "text" ) :
      # Not a textual content response
      return HttpResponseBadRequest( content = "Source URL of invalid content type." )

    soup    = BeautifulSoup( srcrq.text )
    if not soup.find( "a", href = request.POST["target"] ) :
      return HttpResponseBadRequest( content = "Source URL does not contain a link to the target URL." )

    # Do something with the webmention
    post.receive_webmention( request.POST["source"], request.POST["target"], soup )

    # Reply successfully
    return HttpResponse( status = 200, content = "Webmention received successfully." )
  else :
    # Someone's accessing the endpoint without a POST request, show a page
    return render( request, 'wm/endpoint.html' )