# This Python file uses the following encoding: utf-8
import re
import requests
import tweepy
from bs4 import BeautifulSoup
from grmblgrmbl.models import Note, Reply, Article
from .models import PosseData
from .twitter_utils import get_selfauthed_api_handler, get_status_id_from_url, PATTERN_TWEET_ID

TWEET_MAX_LENGTH  = 140
TWEET_END_BUFFER  = 26

PATTERN_TWIT_HNDL = r"twitter.com/([\w]+)"
PATTERN_HASHTAG   = r"#\w[\w-]+"
PATTERN_ATREF     = r"@\w[\w.-]+"

ELLIPSIS_SUFFIX   = u"… "

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
  if isinstance( post, Note ) :
    tweet = assemble_tweet( post.content, post.pk )
  elif isinstance( post, Article ) :
    tweet = assemble_tweet( post.title + ": ", post.pk, always_link = True )
  
  # for replies, find a valid twitter reply context, or just directly link the thing we're replying to
  reply_id = None
  if post.kind() == "Reply" :
    if "twitter.com" in post.note.reply.reply_url :
      reply_id = get_status_id_from_url( post.note.reply.reply_url )
    else :
      # see if the thing we're linking to has been syndicated to twitter
      soup = BeautifulSoup( requests.get( post.note.reply.reply_url ).text )

      for relsynd in soup.find_all( rel = "syndication" ) :
        if "twitter.com" in relsynd['href'] :
          match = re.search( PATTERN_TWEET_ID, relsynd['href'] )

          if match:
            reply_id = match.group( 0 )
            break
      # TODO: check for u-syndication objects

  api = get_selfauthed_api_handler()
  if reply_id :
    status = api.update_status( status = tweet, in_reply_to_status_id = reply_id )
  else :
    status = api.update_status( status = tweet )

  # Get or create our post's POSSE data
  posse, created  = PosseData.objects.get_or_create( post_id = post.pk )
  posse.twitter   = "http://twitter.com/{}/status/{}".format( status.author.screen_name, status.id_str )
  posse.save()

def delete_post( post ) :
  api       = get_selfauthed_api_handler()
  status_id = get_status_id_from_url( post.posse_data.twitter )

  if status_id :
    api.destroy_status( int( status_id ) )