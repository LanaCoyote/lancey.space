from django.db import models
from .twitter_utils import get_status_id_from_url

# Create your models here.

class PosseData ( models.Model ) :

  post    = models.OneToOneField( 'grmblgrmbl.Post', related_name = 'posse_data' )
  twitter = models.URLField()

  def get_tweet_id( self ) :
    if not self.twitter :
      return None
    else :
      return get_status_id_from_url( self.twitter )
