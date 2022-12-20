from django.contrib.auth.models import User
from django.db import models
import datetime
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

# Create your models here.

class EolForumNotifications(models.Model):
    HOW_OFTEN_CHOICES = (("never", "never"), ("always", "always"), ("weekly", "weekly"), ("monthly", "monthly"))
    class Meta:
        index_together = [
            ["discussion_id", "user"],
        ]
        unique_together = [
            ["discussion_id", "user"],
        ]
    
    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    discussion_id = models.CharField(blank=False, max_length=255, db_index=True)
    course_id = CourseKeyField(max_length=255)
    how_often = models.TextField(choices=HOW_OFTEN_CHOICES, default='never')
    sent_at = models.DateTimeField(default=datetime.date.today)
    comment_created = models.BooleanField(default=False)
    thread_created = models.BooleanField(default=False)
    own_comment_created = models.BooleanField(default=False)