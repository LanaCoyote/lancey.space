import re
import requests
from django.contrib.auth.models import User

class IndieAuthBackend ( object ) :
  
  def authenticate ( self, code = None, destination = "https://indieauth.com/auth" ) :
    data = {
      "code"          : code,
      "redirect_uri"  : "http://lancey.space/auth",
      "client_id"     : "http://lancey.space",
    }
    headers = {
      "Content-Type"  : "application/x-www-form-urlencoded",
      "charset"       : "UTF-8",
    }

    # Make an authentication request to indieauth
    r = requests.post( destination, data = data, headers = headers, verify = False )

    if r.status_code == 200 : # Good request
      try:
        me = re.search( r"me=http%3A%2F%2F([\w\.-]+)", r.content ).group( 1 )
        try :
          user = User.objects.get( username = me )
        except User.DoesNotExist :
          user = User( username = me, password = 'IndieAuth' )
          user.save()
        return user
      except Exception as e :
        return None
    else :
      return None

  def get_user(self, user_id):
    try:
      return User.objects.get(pk=user_id)
    except User.DoesNotExist:
      return None
