import requests
from django.db import models

# Create your models here.

class Webmention ( models.Model ) :
  """
    For now we just use it for abstraction, but in the future we should queue Webmentions and
    manage them asynchronously, rather than all at once.
  """

  source    = models.URLField( max_length = 200 )
  target    = models.URLField( max_length = 200 )
  vouch     = models.URLField( max_length = 200, blank = True )

  endpoint  = models.URLField( max_length = 200 )

  def send ( self ) :
    p = { "source" : self.source, "target" : self.target }
    if self.vouch and not self.vouch == "" :
      p["vouch"] = self.vouch

    r = requests.post( self.endpoint, params = p )
