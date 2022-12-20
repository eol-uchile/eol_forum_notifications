
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.conf import settings

from celery import task
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError
from django.template.loader import render_to_string
from .models import EolForumNotifications
from .utils import reduce_threads
from django.utils.timezone import now
import logging
logger = logging.getLogger(__name__)

EMAIL_DEFAULT_RETRY_DELAY = 30
EMAIL_MAX_RETRIES = 5

@task(
    queue='edx.lms.core.low',
    default_retry_delay=EMAIL_DEFAULT_RETRY_DELAY,
    max_retries=EMAIL_MAX_RETRIES)
def task_send_email(discussion_id, context, content_forum, student_data):
    """
        Send mail to specific user
    """
    subject = 'Notificaciones Resumen Foro'
    user_notif = EolForumNotifications.objects.get(user__id=context['user_id'], discussion_id=discussion_id)
    emails = [user_notif.user.email]
    hilos = reduce_threads(discussion_id, context)
    if hilos is None:
        return None
    context['hilos'] = hilos #can be None
    context['content_forum'] = content_forum
    context['student_data'] = student_data
    html_message = render_to_string('eol_forum_notifications/email.txt', context)
    plain_message = strip_tags(html_message)
    from_email = configuration_helpers.get_value(
        'email_from_address',
        settings.BULK_EMAIL_DEFAULT_FROM_EMAIL
    )
    mail = send_mail(
        subject,
        plain_message,
        from_email,
        emails,
        fail_silently=False,
        html_message=html_message)
    user_notif.sent_at = now()
    user_notif.save()
    return mail

@task(
    queue='edx.lms.core.low',
    default_retry_delay=EMAIL_DEFAULT_RETRY_DELAY,
    max_retries=EMAIL_MAX_RETRIES)
def task_send_single_email(context, user_id):
    subject = 'Notificaciones Foro'
    user_notif = EolForumNotifications.objects.get(user__id=user_id, discussion_id=context['discussion_id'])
    emails = [user_notif.user.email]
    if context['type'] == 'thread':
        html_message = render_to_string('eol_forum_notifications/email.txt', context)
    if context['type'] == 'comment':
        html_message = render_to_string('eol_forum_notifications/email.txt', context)
    plain_message = strip_tags(html_message)
    from_email = configuration_helpers.get_value(
        'email_from_address',
        settings.BULK_EMAIL_DEFAULT_FROM_EMAIL
    )
    mail = send_mail(
        subject,
        plain_message,
        from_email,
        emails,
        fail_silently=False,
        html_message=html_message)
    user_notif.sent_at = now()
    user_notif.save()
    return mail
