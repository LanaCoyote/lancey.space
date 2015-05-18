from django import forms

# Create forms below

class ComposeForm ( forms.Form ) :
  """
    Basic form for composing new articles/notes.
    In the future I might separate out these forms based on the media type I'm making, but for now it'll determine the post type based on context.
  """

  title       = forms.CharField( label = "Title", max_length = 100, required = False, help_text = "Leave blank for notes." )
  content     = forms.CharField( label = "Content", widget = forms.Textarea )
  tags        = forms.CharField( label = "Tags", max_length = 200, required = False, help_text = "Separate tags with spaces. #tags will be automatically parsed from notes." )

  reply_to    = forms.URLField( label = "Reply to", max_length = 200, required = False, help_text = "URL this note is a reply to. This should be a permalink. Notes only." )
  reply_name  = forms.CharField( label = "Reply name", max_length = 100, required = False, help_text = "The name to reply to, without an @ (e.g. aaronpk). Notes only." )
  reply_prof  = forms.URLField( label = "Reply profile", max_length = 200, required = False, help_text = "The base site this reply should link to (e.g. http://aaronpareki.com). Notes only.")
