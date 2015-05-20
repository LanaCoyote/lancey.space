from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, render_to_response
from django.template import RequestContext
from possem.twitter import tweet_post, delete_post
from possem.twitter_utils import get_selfauthed_api_handler, get_status_id_from_url
from .models import Post, Note, Article, Reply
from .forms import ComposeForm

# Create your views here.

def frontpage ( request ) :
  return post_list( request )

def feed ( request ) :
  return post_list( request, model = Note, page_len = 30 )

def articles ( request ) :
  return post_list( request, model = Article, page_len = 10 )

def post_list ( request, model = Post, page_len = 15 ) :
  # Get page number
  try :
    page  = int( request.GET["page"] )
    start = ( page - 1 ) * page_len
    end   = start + page_len
  except :
    page  = 1
    start = 0
    end   = page_len

  # Get search tags
  try :
    tag   = request.GET["tag"]
    post_list = model.objects.filter( tags__contains = tag ).order_by( '-date_posted' )[start:end]
  except :
    post_list = model.objects.order_by( '-date_posted' )[start:end]
  
  last_page = len( post_list ) < page_len

  return render_to_response( 'grmbl/post_list.html', { 'post_list' : post_list, 'page' : page, 'last_page' : last_page }, context_instance = RequestContext( request ) )

def post_detail ( request, pid ) :
  post    = get_object_or_404( Post, pk = pid )
  context = {}

  if post.kind() == "Reply" :
    # Try to assemble some sort of reply context
    if "twitter.com" in post.note.reply.reply_url :
      status_id = get_status_id_from_url( post.note.reply.reply_url )

      if status_id :
        api     = get_selfauthed_api_handler()
        status  = api.get_status( status_id )

        context = {
          "avatar"  : status.author.profile_image_url,
          "author"  : status.author.name,
          "title"   : "@" + status.author.screen_name,
          "content" : "<p>" +  status.text + "</p>",
        }

  return render_to_response( 'grmbl/post_detail.html', { 'post' : post, 'tags' : post.tags.split( " " ), 'reply_context' : context }, context_instance = RequestContext( request ) )

def shortlink( request, pid ) :
  # Shortlinks should just redirect to the valid post
  return HttpResponseRedirect( '/posts/' + str( pid ) )

def compose ( request ) :
  if not request.user.is_authenticated or not request.user.is_staff :
    return HttpResponseForbidden()

  if request.method == "POST" :
    form = ComposeForm( request.POST )

    if form.is_valid() :
      title   = form.cleaned_data['title']
      content = form.cleaned_data['content']
      tags    = form.cleaned_data['tags']

      try :
        post = Post.objects.get( pk = form.cleaned_data['post_id'] )

        if form.cleaned_data['delete'] :
          try :
            if post.posse_data.twitter :
              delete_post( post )
          except Exception as e :
            print e

          post.delete()
          return HttpResponseRedirect( '/' )

        if post.kind() == "Article" :
          post.article.title    = title
          post.article.content  = content
          post.article.tags     = tags

          post.article.save()
        else :
          post.note.content   = content
          post.note.tags      = tags

          if post.kind() == "Reply" :
            post.note.reply.reply_url     = form.cleaned_data['reply_to']
            post.note.reply.display_name  = form.cleaned_data['reply_name']
            post.note.reply.profile       = form.cleaned_data['reply_prof']

            post.note.reply.save()
          else :
            post.note.save()
      except Post.DoesNotExist :
        if title :
          new_article         = Article()
          new_article.title   = title
          new_article.content = content
          new_article.tags    = tags

          new_article.save()
          post = new_article
        else :
          if form.cleaned_data['reply_to'] :
            reply_to    = form.cleaned_data['reply_to']
            reply_name  = form.cleaned_data['reply_name']
            reply_prof  = form.cleaned_data['reply_prof']

            new_reply         = Reply()
            new_reply.content = content
            new_reply.tags    = tags

            new_reply.reply_url     = reply_to
            new_reply.display_name  = reply_name
            new_reply.profile       = reply_prof

            new_reply.save()
            post = new_reply
          else :
            new_note          = Note()
            new_note.content  = content
            new_note.tags     = tags

            new_note.save()
            post = new_note

        if form.cleaned_data['syn_twitter'] :
          tweet_post( post )

      return HttpResponseRedirect( '/posts/' + str( post.pk ) )
  else :
    try :
      if request.GET.has_key( 'post_id' ) :
        post      = Post.objects.get( pk = request.GET['post_id'] )
        
        if post.kind() == "Article" :
          init_data = {
            'title'   : post.article.title,
            'content' : post.article.content,
            'tags'    : post.tags,
          }
        else :
          init_data = {
            'content' : post.note.content,
            'tags'    : post.tags,
          }

          if post.kind() == "Reply" :
            init_data['reply_to']   = post.note.reply.reply_url
            init_data['reply_name'] = post.note.reply.display_name
            init_data['reply_prof'] = post.note.reply.profile

        init_data['post_id']  = post.pk

        form      = ComposeForm( init_data )
      else :
        form      = ComposeForm()
    except Post.DoesNotExist :
      form        = ComposeForm()

  return render_to_response( 'grmbl/compose.html', { 'form' : form }, context_instance = RequestContext( request ) )