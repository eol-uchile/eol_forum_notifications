#!/usr/bin/env python
# -- coding: utf-8 --

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render
from opaque_keys.edx.keys import CourseKey
from django.urls import reverse
from django.http import HttpResponse
from .models import EolForumNotifications

from .utils import get_threads_by_users, reduce_data_forum, get_users_notifications, get_discussions, get_comment, check_own_comment
from datetime import timedelta
from django.utils.timezone import now
import json
import requests
import logging

logger = logging.getLogger(__name__)

def save_notification(request):
    """
        1:thread_created
        2:comment_created
        3:own_comment_created
    """
    if request.method != "POST":
        logger.error('EolForumNotification - Wrong Method: {}, only POST'.format(request.method))
        return HttpResponse(status=400)
    if 'period' not in request.POST or 'when' not in request.POST or 'discussion_id' not in request.POST or 'course_id' not in request.POST or 'user_id' not in request.POST:
        logger.error('EolForumNotification - Missing Data: {}'.format(request.POST))
        return HttpResponse(status=400)
    if request.POST.get('user_id') != str(request.user.id):
        logger.error('EolForumNotification - User Ids are differents, user id post: {}, user id resquest: {}'.format(request.POST.get('user_id'), request.user.id))
        return HttpResponse(status=400)
    comment_created = False
    thread_created = False
    own_comment_created = False
    for x in request.POST.get('when', []):
        if x == '1':
            thread_created = True
            continue
        if x == '2':
            comment_created = True
            continue
        if x == '3':
            own_comment_created = True
            continue
    with transaction.atomic():
        try:
            course_id = CourseKey.from_string(request.POST.get('course_id'))
            EolForumNotifications.objects.update_or_create(
                user=request.user,
                discussion_id=request.POST.get('discussion_id'),
                defaults={
                    'course_id': course_id,
                    'how_often': request.POST.get('period'),
                    'comment_created': comment_created,
                    'thread_created': thread_created,
                    'own_comment_created': own_comment_created
                    })
            return HttpResponse(status=200)
        except Exception as e:
            logger.error('EolForumNotification - Error to update or create EolForumNotifications, error {}, data: {}'.format(str(e), request.POST))
            return HttpResponse(status=400)

def send_notification(how_often):
    """
        Send email with threads and/or comments unreaded
    """
    from .tasks import task_send_email
    delta = 30 # how_often = monthly
    if how_often == 'weekly':
        delta = 7
    try:
        current_site = get_current_site()
        platform_name =  current_site.configuration.get_value('PLATFORM_NAME', 'EOL')
        url_site =  current_site.configuration.get_value('LMS_BASE', 'eol.uchile.cl')
    except Exception:
        logger.error('EolForumNotification - Error to get platform name and url site')
        platform_name =  'EOL'
        url_site = 'eol.uchile.cl'
    timeout = (now() - timedelta(days=delta)).strftime("%Y-%m-%d %H:%M:%S")
    discussions = get_discussions(how_often, timeout)
    for discussion in discussions:
        hilos = get_threads_by_users(discussion['discussion_id'], discussion['course_id'])
        if hilos is None:
            logger.error('EolForumNotification - Error to get get_threads_by_users, discusssion: {}, course: {}'.format(discussion['discussion_id'], discussion['course_id']))
            continue 
        if len(hilos) == 0:
            logger.info('EolForumNotification - Foro sin publicaciones')
            continue
        content_forum, student_data = reduce_data_forum(hilos)
        users_notifications = get_users_notifications(how_often, discussion['discussion_id'], timeout)
        for notification in users_notifications:
            context = {
                'comment_created': notification.comment_created,
                'thread_created': notification.thread_created,
                'own_comment_created': notification.own_comment_created,
                'user_id':notification.user.id,
                'course_id': str(discussion['course_id']),
                'platform_name': platform_name,
                'url_site': url_site
            }
            task_send_email.delay(notification.discussion_id, context, content_forum, student_data[str(notification.user.id)] if str(notification.user.id) in student_data else {})

def send_notification_always_thread(thread, user):
    """
        Send email with thread
    """
    from .tasks import task_send_single_email
    try:
        current_site = get_current_site()
        platform_name =  current_site.configuration.get_value('PLATFORM_NAME', 'EOL')
        url_site =  current_site.configuration.get_value('LMS_BASE', 'eol.uchile.cl')
    except Exception:
        logger.error('EolForumNotification - Error to get platform name and url site')
        platform_name =  'EOL'
        url_site = 'eol.uchile.cl'
    context = {
        'course_id': str(thread.course_id),
        'thread_id': thread.id,
        'thread_title': thread.title,
        'thread_author_id': thread.user_id,
        'thread_anonymous': thread.anonymous,
        'thread_author_username': thread.username,
        'thread_created_at': thread.created_at,  # comment_client models dates are already serialized
        'thread_body': thread.body,
        'discussion_id': thread.commentable_id,
        'platform_name': platform_name,
        'url_site':url_site,
        'type': 'thread'
    }
    users = EolForumNotifications.objects.filter(how_often='always', discussion_id=thread.commentable_id).exclude(user=user)
    for notif in users:
        if notif.thread_created:
            task_send_single_email.delay(context, notif.user.id)

def send_notification_always_comment(comment, user):
    """
        Send email with comment
    """
    from .tasks import task_send_single_email
    try:
        current_site = get_current_site()
        platform_name =  current_site.configuration.get_value('PLATFORM_NAME', 'EOL')
        url_site =  current_site.configuration.get_value('LMS_BASE', 'eol.uchile.cl')
    except Exception:
        logger.error('EolForumNotification - Error to get platform name and url site')
        platform_name =  'EOL'
        url_site = 'eol.uchile.cl'
    thread = comment.thread
    parent = None
    
    context = {
        'course_id': str(thread.course_id),
        'comment_id': comment.id,
        'comment_body': comment.body,
        'comment_author_id': comment.user_id,
        'comment_author_username': comment.username,
        'comment_created_at': comment.created_at,  # comment_client models dates are already serialized
        'thread_id': thread.id,
        'thread_title': thread.title,
        'thread_author_id': thread.user_id,
        'thread_author_username': thread.username,
        'thread_created_at': thread.created_at,  # comment_client models dates are already serialized
        'discussion_id': thread.commentable_id,
        'thread_anonymous': thread.anonymous,
        'platform_name': platform_name,
        'url_site':url_site,
        'type': 'comment',
        'parent': {}
    }
    if comment.parent_id is not None:
        parent = get_comment(comment.parent_id)
        context['parent']['author_id'] = parent.user_id
        context['parent']['author_username'] = parent.username
        context['parent']['body'] = parent.body
    users = EolForumNotifications.objects.filter(how_often='always', discussion_id=thread.commentable_id).exclude(user=user)
    for notif in users:
        if notif.comment_created or (notif.own_comment_created and check_own_comment(context, notif.user.id)):
            task_send_single_email.delay(context, notif.user.id)