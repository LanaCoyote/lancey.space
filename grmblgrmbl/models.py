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

  def receive_webmention( self, source, target, soup ) :
    mention = Mention()
    mention.source  = source
    mention.post    = self

    # Get the mention type
    anchor = soup.find( "a", href = target )
    if anchor :
      if anchor.has_key( 'rel' ) and anchor['rel'] == "in-reply-to" :
        mention.resp_type = MENTION_REPLY

        content = soup.find( class_ = "e-content" )
        if content :
          if len( content.get_text() ) > 200 :
            mention.content = content.get_text()[:200] + "..."
          else :
            mention.content = content
      elif anchor.has_key( 'class' ) and "u-like-of" in anchor['class'] :
        mention.resp_type = MENTION_LIKE
      elif anchor.has_key( 'class' ) and "u-repost-of" in anchor['class'] :
        mention.resp_type = MENTION_REPOST
      else :
        mention.resp_type = MENTION_MENTION

    # Get the author's name
    author = soup.find( class_ = "p-author" )
    if author :
      if "h-card" in author['class'] :
        if author.find( class_ = "p-name" ) :
          mention.author = unicode( author.find( class_ = "p-name" ).string )
        else :
          mention.author = unicode( author.string )
      else :
        mention.author = author.get_text()

    mention.save()


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

class Mention ( models.Model ) :
  """
    A mention is an off-site reference to a post, such as a comment, like, or repost
  """

  source      = models.URLField( max_length = 200 )
  post        = models.ForeignKey( Post )

  date_posted = models.DateTimeField( auto_now_add = True )
  author      = models.CharField( max_length = 100 )
  content     = models.TextField( blank = True )

  resp_type   = models.SmallIntegerField( default = MENTION_MENTION )
