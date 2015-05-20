# This Python file uses the following encoding: utf-8
import re
import requests
import tweepy
from bs4 import BeautifulSoup
from grmblgrmbl.models import Note, Reply, Article
from string import punctuation
from .models import PosseData
from .twitter_utils import get_selfauthed_api_handler, get_status_id_from_url, twitter_len, PATTERN_TWEET_ID

TWEET_MAX_LENGTH  = 140
TWEET_END_BUFFER  = 26

PATTERN_TWIT_HNDL = r"twitter.com/([\w]+)"
PATTERN_HASHTAG   = r"#\w[\w-]+"
PATTERN_ATREF     = r"@\w[\w.-]+"

ELLIPSIS_SUFFIX   = u"… "

def truncate_string( s, max_length ) :
  if twitter_len( s ) < max_length :
    # s is shorter than the maximum length and no truncation needs to be done
    return ( s, False )
  else :
    extra_len = len( s ) - twitter_len( s )

    # extract hashtags to preserve for later
    hashtags_length = 0
    hashtags        = re.findall( PATTERN_HASHTAG, s )

    # reduce the maximum length we're allowed if the hashtag needs to be reinserted
    for tag in hashtags :
      if s.find( tag ) > max_length - len( ELLIPSIS_SUFFIX ) - hashtags_length - len( tag ) + extra_len :
        hashtags_length += len( tag ) + 1 # +1 for space

    # cut down the rest of the tweet
    for i in range( len( s ), 0, -1 ) :
      if i > max_length - len( ELLIPSIS_SUFFIX ) - hashtags_length + extra_len :
        continue
      elif s[i] == " " :
        s = s[:i] + ELLIPSIS_SUFFIX
        break

    # return the preserved hashtags
    for tag in hashtags :
      if not tag in s :
        s += tag + " "

    return ( s, True )

def assemble_tweet( content, id, always_link = False, reply_link = None ) :
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
  reply_link_len = 0
  if reply_link :
    reply_link_len = twitter_len( reply_link ) + 1

  content, shortlink = truncate_string( content, TWEET_MAX_LENGTH - TWEET_END_BUFFER - reply_link_len )

  if reply_link :
    content += " " + reply_link

  if always_link or shortlink :
    # If the tweet has been truncated, add a continuation link on the end
    content += " lancey.space/p{}".format( id )
  else :
    # Otherwise we use a shortcitation
    content += " (lancey.space p{})".format( id )

  return content

def tweet_post( post ) :
  # for replies, find a valid twitter reply context, or just directly link the thing we're replying to
  reply_id          = None
  reply_link        = None
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
      else :
        reply_link = post.note.reply.reply_url

  if isinstance( post, Note ) :
    tweet = assemble_tweet( post.content, post.pk, reply_link = reply_link )
  elif isinstance( post, Article ) :
    content = post.title if post.title[-1] in punctuation else post.title + ":"
    tweet = assemble_tweet( content, post.pk, always_link = True, reply_link = reply_link )

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