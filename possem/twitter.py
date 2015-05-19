# This Python file uses the following encoding: utf-8
import re
import requests
import tweepy
from bs4 import BeautifulSoup
from django.conf import settings
from grmblgrmbl.models import Note, Reply, Article
from .models import PosseData

TWEET_MAX_LENGTH  = 140
TWEET_END_BUFFER  = 24

PATTERN_TWEET_ID  = r"\d+$"
PATTERN_TWIT_HNDL = r"twitter.com/([\w]+)"
PATTERN_HASHTAG   = r"#\w[\w-]+"
PATTERN_ATREF     = r"@\w[\w.-]+"

ELLIPSIS_SUFFIX   = u"… "

def get_self_auth_handler( ) :
  # initialize an auth handler using the tokens defined in settings
  auth = tweepy.OAuthHandler( settings.TWITTER_CONSUMER_TOKEN, settings.TWITTER_CONSUMER_SECRET )
  auth.set_access_token( settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_SECRET )
  return auth

def get_selfauthed_api_handler( ) :
  return tweepy.API( get_self_auth_handler() )

def get_status_id_from_url( url ) :
  match = re.search( PATTERN_TWEET_ID, url )

  if match :
    # the twitter id was found, returning the matched string
    return match.group( 0 )
  else :
    # no twitter id (invalid url?) returns None
    return None

def truncate_string( s, max_length ) :
  if len( s ) < max_length :
    # s is shorter than the maximum length and no truncation needs to be done
    return ( s, False )
  else :
    # extract hashtags to preserve for later
    hashtags_length = 0
    hashtags        = re.findall( PATTERN_HASHTAG, s )

    # reduce the maximum length we're allowed if the hashtag needs to be reinserted
    for tag in hashtags :
      if s.find( tag ) > max_length - len( ELLIPSIS_SUFFIX ) - hashtags_length - len( tag ) :
        hashtags_length += len( tag ) + 1 # +1 for space

    # cut down the rest of the tweet
    for i in range( len( s ), 0, -1 ) :
      if i > max_length - len( ELLIPSIS_SUFFIX ) - hashtags_length :
        continue
      elif s[i] == " " :
        s = s[:i] + ELLIPSIS_SUFFIX
        break

    # return the preserved hashtags
    for tag in hashtags :
      if not tag in s :
        s += tag + " "

    return ( s, True )

def assemble_tweet( content, id, always_link = False ) :
  # get the twitter handles of any @-references
  for atref in re.findall( PATTERN_ATREF, content ) :
    # when I add contacts, search them first

    # pull contact info from an indiewebsite's rel-me info
    try :
      # connect to and parse the atref's website
      soup = BeautifulSoup( requests.get( "http://" + atref[1:] ).text )

      for relme in soup.find_all( rel = "me" ) :
        if "twitter.com" in relme['href'] :
          # found a rel-me reference to twitter
          match = re.search( PATTERN_TWIT_HNDL, relme['href'] )

          if match.group( 1 ) :
            # replace the atref in our content with the one we found
            content = content.replace( atref, "@" + match.group( 1 ) )
            break  
    except Exception as e :
      print e

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

def delete_post( post ) :
  api   = get_selfauthed_api_handler()

  status_id = get_status_id_from_url( post.posse_data.twitter )

  if status_id :
    api.destroy_status( int( status_id ) )