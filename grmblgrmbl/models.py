import re
import requests
from django.db import models
from possem.twitter_utils import get_selfauthed_api_handler, resolve_tco_url

MENTION_REPLY     = 0
MENTION_LIKE      = 1
MENTION_REPOST    = 2
MENTION_MENTION   = 3

# Create your models here.

def valid_domain ( s ) :
  try :
    requests.get( "http://" + s )
    return True
  except :
    return False

def expand_local_ref ( site, ref ) :
  if ref.startswith( "http" ) :
    return ref

  while ref.startswith( "." ) :
    ref = ref[1:]

  if not ref.startswith( "/" ) :
    ref = "/" + ref

  return site + ref

class Post ( models.Model ) :
  """
    A post is a media-generic entry on the site. It's meant to be subclassed into various media types.
  """

  date_posted = models.DateTimeField( auto_now_add = True )
  hidden      = models.BooleanField( default = False )
  tags        = models.CharField( max_length = 200, blank = True )

  def kind( self ) :
    try :
      self.note
      try :
        self.note.reply
        return "Reply"
      except AttributeError :
        return "Note"
    except AttributeError :
      try :
        self.article
        return "Article"
      except AttributeError :
        return "Unknown"

  def get_next( self ) :
    if self.kind() == "Article" :
      kind = Article
    else :
      kind = Note

    try :
      return kind.objects.filter( date_posted__gt = self.date_posted ).only( "id" ).earliest( "date_posted" )
    except kind.DoesNotExist :
      return None

  def get_previous( self ) :
    if self.kind() == "Article" :
      kind = Article
    else :
      kind = Note

    try :
      return kind.objects.filter( date_posted__lt = self.date_posted ).only( "id" ).latest( "date_posted" )
    except kind.DoesNotExist :
      return None

  def get_likes( self ) :
    return Like.objects.filter( post_id = self.pk )

  def get_reposts( self ) :
    return Repost.objects.filter( post_id = self.pk )

  def get_comments( self ) :
    return Repost.objects.filter( post_id = self.pk )

  def get_mentions( self ) :
    return Mention.objects.filter( post_id = self.pk )

  def receive_webmention( self, source, target, soup ) :
    anchor = soup.find( href = target )
    if not anchor :
      return

    if anchor.has_key( "rel" ) and anchor['rel'] == "in-reply-to" :
      act = Comment()

      summary = soup.find( "", { "class" : "p-summary" } )
      act.content = summary.text if summary else soup.find( "", { "class" : "e-content" } ).text if soup.find( "", { "class" : "e-content" } ) else None

    elif anchor.has_key( "class" ) and "u-like-of" in anchor['class'] :
      act = Like()

    elif anchor.has_key( "class" ) and "u-repost-of" in anchor['class'] :
      act = Repost()

    else :
      act = Mention()

      pname = soup.find( "", { "class" : "p-name" } )
      act.title = pname.text if pname else source

    if isinstance( act, Comment ) or isinstance( act, Mention ) :
      # Get the mentioner's site and URL
      parts         = source.split( '/' )
      act.site      = parts[2]
      act.site_url  = '/'.join( parts[:3] )

      # Get the mentioner's name and avatar
      hcard = soup.find( "", { "class" : "h-card" } )
      if hcard :
        act.avatar = expand_local_ref( hcard.img['src'], act.site_url )

        if hcard.text :
          act.author = hcard.text
        elif hcard.has_key( "title" ) :
          act.author = hcard['title']
        elif hcard.img.has_key( "alt" ) :
          act.author = hcard.img['alt']
        else :
          act.author = act.site
      else :
        act.author = act.site

      # Get the date it was posted
      date = soup.find( "", { "class" : "dt-published" } )
      act.date_posted = date.text if date else "link to this"
    elif isinstance( act, Like ) or isinstance( act, Repost ) :
      # Get the toplevel URL of the actor
      parts = source.split( '/' )
      act.site_url = '/'.join( parts[:3] )

      # Get the actor's avatar
      hcard = soup.find( "", { "class" : "h-card" } )
      if hcard :
        act.avatar = expand_local_ref( hcard.img['src'], act.site_url )

    act.post    = self
    act.source  = source
    act.save()


class Note ( Post ) :
  """
    A note is a small snippet of text like a tweet.
  """

  content     = models.TextField()
  raw_content = models.TextField( default = "Missing raw data" )

  def __unicode__ ( self ) :
    return self.content[:110]

  def save ( self ) :
    self.raw_content = "<p class=\"note-content e-content p-name\">" + self.content + "</p>"
    # Parse out full links
    for link in re.finditer( "((https?|ftp)://|www\.)[^\s/$.?#].[^\s]*", self.raw_content ) :
      self.raw_content = self.raw_content.replace( link.group( 0 ), "<a href=\"" + link.group( 0 ) + "\">" + link.group( 0 ) + "</a>", 1 )

    # Parse out tags
    for tag in re.finditer( "#([\w-]+)", self.raw_content ) :
      self.raw_content = self.raw_content.replace( tag.group( 0 ), "<a href=\"/posts?tag=" + tag.group( 1 ) + "\">" + tag.group( 0 ) + "</a>", 1 )

      if not tag.group( 1 ) in self.tags :
        self.tags = self.tags + " " + tag.group( 1 )

    twitter_api = get_selfauthed_api_handler( )

    # Parse out mentions & replies
    for mention in re.finditer( "@([\w\.-]+)", self.raw_content ) :
      # If we're actually a reply, link to the replied content
      if isinstance( self, Reply ) and mention.group( 1 ) == self.display_name :
        self.raw_content = self.raw_content.replace( mention.group( 0 ), "<a href=\"" + self.profile + "\">" + mention.group( 0 ) + "</a>", 1 )

      # TODO: Search contacts (make contacts)

      # If the @-ref is a valid twitter handle, try to pull their website from their profile
      elif not "." in mention.group( 0 ) :
        try :
          user = twitter_api.get_user( mention.group( 1 ) )

          if user.url :
            url = resolve_tco_url( user.url )
          else :
            # Otherwise just link to their twitter profile
            url = "https://twitter.com/" + mention.group( 1 )

          self.raw_content = self.raw_content.replace( mention.group( 0 ), "<a href=\"" + url + "\">" + mention.group( 0 ) + "</a>", 1 )
        except Exception as e :
          print e

      # If the mentioned person is a valid domain anyway, link to that
      elif valid_domain( mention.group( 1 ) ) :
        self.raw_content = self.raw_content.replace( mention.group( 0 ), "<a href=\"http://" + mention.group( 1 ) + "\">" + mention.group( 0 ) + "</a>", 1 )


    Post.save( self )

class Reply ( Note ) :
  """
    A reply is a special kind of note that replies to some link.
  """

  reply_url     = models.URLField()
  display_name  = models.CharField( max_length = 100, blank = True )
  profile       = models.URLField()

  def save ( self ) :
    if self.display_name and not ("@" + self.display_name) in self.content :
      # The reply target name is not referenced in the post, we'll insert it
      self.content = "@" + self.display_name + " " + self.content

    # Find the "profile" to link to

    # TODO: Search contacts

    # Search silos
    if not "." in self.display_name :
      try :
        twitter_api = get_selfauthed_api_handler( )
        user = twitter_api.get_user( self.display_name )

        if user.url :
          url = resolve_tco_url( user.url )
        else :
          # Otherwise just link to their twitter profile
          url = "https://twitter.com/" + self.display_name

        self.profile = url
      except Exception as e :
        print e
        self.profile = self.reply_url

    # If the display name is a valid domain, that's their profile
    elif valid_domain( self.display_name ) :
      self.profile = "http://" + self.display_name

    # If there's no profile discernable, just make it the target url
    else :
      self.profile = self.reply_url

    Note.save( self )

class Article ( Post ) :
  """
    An article is a large content entry like a blog post.
  """

  title       = models.CharField( max_length = 100 )
  content     = models.TextField()

  def __unicode__ ( self ) :
    return self.title

class Activity ( models.Model ) :

  post        = models.ForeignKey( Post )
  source      = models.URLField()

class Mention ( Activity ) :

  site        = models.CharField( max_length = 100, blank = True )
  site_url    = models.URLField( blank = True )
  author      = models.CharField( max_length = 100, blank = True )
  avatar      = models.URLField( blank = True )
  title       = models.CharField( max_length = 200, blank = True )
  date_posted = models.CharField( max_length = 100, blank = True )

class Comment ( Activity ) :

  site        = models.CharField( max_length = 100, blank = True )
  site_url    = models.URLField( blank = True )
  author      = models.CharField( max_length = 100, blank = True )
  avatar      = models.URLField( blank = True )
  content     = models.TextField( blank = True )
  date_posted = models.CharField( max_length = 100, blank = True )

class Like ( Activity ) :

  site_url    = models.URLField( null = True )
  avatar      = models.URLField( blank = True )

class Repost ( Activity ) :

  site_url    = models.URLField( null = True )
  avatar      = models.URLField( blank = True )