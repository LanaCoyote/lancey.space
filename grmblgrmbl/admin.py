from django.contrib import admin
from .models import Note, Reply, Article

# Register your models here.

class NoteAdmin ( admin.ModelAdmin ) :
  fieldsets     = [
    ( None,               { 'fields' : ['content'] } ),
    ( "Post Information", { 'fields' : ['hidden','tags']}),
  ]

class ReplyAdmin( admin.ModelAdmin ) :
  fieldsets     = [
    ( "Reply Information",{ 'fields' : ['reply_url','display_name'] } ),
    ( None,               { 'fields' : ['content'] } ),
    ( "Post Information", { 'fields' : ['hidden','tags']}),
  ]

class ArticleAdmin ( admin.ModelAdmin ) :
  fieldsets = [
    ( None,               { 'fields' : ['title','content'] } ),
    ( "Post Information", { 'fields' : ['hidden','tags']}),
  ]

admin.site.register( Note, NoteAdmin )
admin.site.register( Reply, ReplyAdmin )
admin.site.register( Article, ArticleAdmin )