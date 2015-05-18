import re
from django.db import models

MENTION_REPLY     = 0
MENTION_LIKE      = 1
MENTION_REPOST    = 2
MENTION_MENTION   = 3

# Create your models here.

def valid_domain ( s ) :
  return re.match( "[\w-]+\.([\w-]+\.*)+", s )

class Post ( models.Model ) :
  """
    A post is a media-generic entry on the site. It's meant to be subclassed into various media types.
  """

  date_posted = models.DateTimeField( auto_now_add = True )
  hidden      = models.BooleanField( default = False )
  tags        = models.CharField( max_length = 200, blank = True )

  def next_id( self ) :
    try :
      next = Post.objects.filter( date_posted__gt = self.date_posted ).only( "id" ).earliest( "date_posted" )
      return next.id
    except :
      return None

  def prev_id( self ) :
    try :
      next = Post.objects.filter( date_posted__lt = self.date_posted ).only( "id" ).latest( "date_posted" )
      return next.id
    except :
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

    # Parse out mentions & replies
    for mention in re.finditer( "@([\w\.-]+)", self.raw_content ) :
      # If we're actually a reply, link to the replied content
      if isinstance( self, Reply ) and mention.group( 1 ) == self.display_name :
        self.raw_content = self.raw_content.replace( mention.group( 0 ), "<a href=\"" + self.profile + "\">" + mention.group( 0 ) + "</a>", 1 )

      # TODO: Search contacts (make contacts)

      # TODO: Search silos

      # If the mentioned person is a valid domain anyway, link to that
      elif valid_domain( mention.group( 1 ) ) :
        self.raw_content = self.raw_content.replace( mention.group( 0 ), "<a href=\"http://" + mention.group( 1 ) + "\">" + mention.group( 0 ) + "</a>", 1 )


    Post.save( self )

class Reply ( Note ) :
  """
    A reply is a special kind of note that replies to some link.
  """

  reply_url     = models.URLField()
  display_name  = models.CharField( max_length = 100 )
  profile       = models.URLField()

  def save ( self ) :
    if not ("@" + self.display_name) in self.content :
      # The reply target name is not referenced in the post, we'll insert it
      self.content = "@" + self.display_name + " " + self.content

    # Find the "profile" to link to

    # TODO: Search contacts

    # TODO: Search silos

    # If the display name is a valid domain, that's their profile
    if valid_domain( self.display_name ) :
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
