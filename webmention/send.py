import requests
from bs4 import BeautifulSoup

class WebmentionSend () :
  def __init__( self, source, target, vouch = None ) :
    self.source = source
    self.target = target
    self.vouch  = vouch

  def __eq__( self, other ) :
    if isinstance( other, WebmentionSend ) :
      if self.target == other.target and self.source == other.source :
        return True
    return False

  def get_webmention_endpoint( self ) :
    r = requests.get( self.target )
    dest_link = None

    # Try to find a rel-webmention link
    if not dest_link :
      soup = BeautifulSoup( r.text )
      dest_link = soup.find( rel = "webmention" )

      if not dest_link :
        dest_link = soup.find( rel = "http://webmention.org/" )

    if dest_link :
      return dest_link['href']
    else :
      return None

  def send( self, endpoint = None ) :
    print "-- Sending webmention : {} -> {}".format( self.source, self.target )
    if not endpoint :
      endpoint = self.get_webmention_endpoint()

      if not endpoint :
        print "Webmention endpoint not found"
        return

    r = requests.post( endpoint, { "source" : self.source, "target" : self.target }, headers = { "Content-Type" : "application/x-www-url-form-encoded" } )

    if r.status_code < 300 :
      print "Webmention posted successfully"
    else :
      print "Webmention returned status {} : {}".format( r.status_code, r.text )


def send_webmentions_from_post( post ) :
  webmentions = []

  # If post is a reply, prepare a webmention for the in-reply-to URL
  if post.kind() == "Reply" :
    webmentions.append( WebmentionSend( "http://lancey.space/posts/" + str( post.pk ), post.note.reply.reply_url ) )

  # Parse the content of post and prep webmentions for any referenced URLs

  # Send them all out! ( TODO: make this asynchronous )
  for wm in webmentions :
    wm.send()