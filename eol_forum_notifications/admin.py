from django.contrib import admin
from .models import EolForumNotifications
# Register your models here.
class EolForumNotificationsAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'discussion_id', 'course_id')
    search_fields = ['user__username', 'discussion_id', 'course_id']

admin.site.register(EolForumNotifications, EolForumNotificationsAdmin)
