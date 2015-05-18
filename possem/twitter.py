# This Python file uses the following encoding: utf-8
import tweepy
from django.conf import settings
from grmblgrmbl.models import Note, Reply, Article
from .models import PosseData

TWEET_MAX_LENGTH  = 140
TWEET_END_BUFFER  = 24

ELLIPSIS_SUFFIX   = u"… "

def get_self_auth_handler( ) :
  auth = tweepy.OAuthHandler( settings.TWITTER_CONSUMER_TOKEN, settings.TWITTER_CONSUMER_SECRET )
  auth.set_access_token( settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_SECRET )
  return auth

def truncate_string( s, max_length ) :
  if len( s ) < max_length :
    return ( s, False )
  else :
    for i in range( len( s ), 0, -1 ) :
      if i > max_length - len( ELLIPSIS_SUFFIX ) :
        continue
      elif s[i] == " " :
        s = s[:i] + ELLIPSIS_SUFFIX
        return ( s, True )

def assemble_tweet( content, id, always_link = False ) :
  # TODO: get the twitter handles of any @-references

  # Cut down our tweet if necessary
  content, shortlink = truncate_string( content, TWEET_MAX_LENGTH - TWEET_END_BUFFER )

  if always_link or shortlink :
    # If the tweet has been truncated, add a continuation link on the end
    content += "http://lancey.space/p{}".format( id )
  else :
    # Otherwise we use a shortcitation
    content += " (lancey.space p{})".format( id )

  return content

def tweet_post( post ) :
  auth = get_self_auth_handler()

  if isinstance( post, Note ) :
    tweet = assemble_tweet( post.content, post.pk )
  elif isinstance( post, Article ) :
    tweet = assemble_tweet( post.title, post.pk, always_link = True )
  
  # TODO : for replies, find a valid twitter reply context, or just directly link the thing we're replying to

  api = tweepy.API( auth )
  status = api.update_status( status = tweet )

  # Get or create our post's POSSE data
  posse, created  = PosseData.objects.get_or_create( post_id = post.pk )
  posse.twitter   = "http://twitter.com/{}/status/{}".format( status.author.screen_name, status.id_str )
  posse.save()
