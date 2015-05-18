from django.shortcuts import render, get_object_or_404, render_to_response
from django.template import RequestContext
from .models import Post, Note, Article

# Create your views here.

def frontpage ( request ) :
  return post_list( request )

def feed ( request ) :
  # Get page number
  try :
    page  = int( request.GET["page"] )
    start = ( page - 1 ) * 30
    end   = start + 30
  except :
    page  = 1
    start = 0
    end   = 30

  post_list = Note.objects.order_by( '-date_posted' )[start:end]
  
  last_page = len( post_list ) < 30

  return render_to_response( 'grmbl/post_list.html', { 'post_list' : post_list, 'page' : page, 'last_page' : last_page }, context_instance = RequestContext( request ) )

def articles ( request ) :
  # Get page number
  try :
    page  = int( request.GET["page"] )
    start = ( page - 1 ) * 10
    end   = start + 10
  except :
    page  = 1
    start = 0
    end   = 10

  post_list = Article.objects.order_by( '-date_posted' )[start:end]
  
  last_page = len( post_list ) < 10

  return render_to_response( 'grmbl/post_list.html', { 'post_list' : post_list, 'page' : page, 'last_page' : last_page }, context_instance = RequestContext( request ) )

def post_list ( request ) :
  # Get page number
  try :
    page  = int( request.GET["page"] )
    start = ( page - 1 ) * 15
    end   = start + 15
  except :
    page  = 1
    start = 0
    end   = 15

  # Get search tags
  try :
    tag   = request.GET["tag"]
    post_list = Post.objects.filter( tags__contains = tag ).order_by( '-date_posted' )[start:end]
  except :
    post_list = Post.objects.order_by( '-date_posted' )[start:end]
  
  last_page = len( post_list ) < 15

  return render_to_response( 'grmbl/post_list.html', { 'post_list' : post_list, 'page' : page, 'last_page' : last_page }, context_instance = RequestContext( request ) )

def post_detail ( request, pid ) :
  post = get_object_or_404( Post, pk = pid )

  return render_to_response( 'grmbl/post_detail.html', { 'post' : post, 'tags' : post.tags.split( " " ) }, context_instance = RequestContext( request ) )