import re
import requests
import tweepy
from django.conf import settings

PATTERN_TWEET_ID  = r"\d+$"

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

def resolve_tco_url( url ) :
  try :
    return requests.get( url ).url
  except :
    return None

def twitter_len( s ) :
  words   = s.split( " " )
  length  = s.count( " " )

  for word in words :
    # this is probably not the best way to parse out links
    if "." in word and len( word ) > 21 and not ( word.startswith( "." ) or word.endswith( "." ) ) :
      length += 21
    # for ordinary words, just add the word length
    else :
      length += len( word )

  return length