from django.db import models

# Create your models here.

class PosseData ( models.Model ) :

  post    = models.OneToOneField( 'grmblgrmbl.Post', related_name = 'posse_data' )
  twitter = models.URLField()
