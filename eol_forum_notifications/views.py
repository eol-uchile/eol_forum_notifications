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
from .models import EolForumNotificationsUser, EolForumNotificationsDiscussions

from .utils import get_users_notifications, get_courses_onlive, get_block_info
import json
import requests
import logging

logger = logging.getLogger(__name__)

def save_notification(request):
    """
        .
    """
    if request.method != "POST":
        logger.error('EolForumNotification - Wrong Method: {}, only POST'.format(request.method))
        return HttpResponse(status=400)
    if 'period' not in request.POST or 'discussion_id' not in request.POST or 'course_id' not in request.POST or 'user_id' not in request.POST:
        logger.error('EolForumNotification - Missing Data: {}'.format(request.POST))
        return HttpResponse(status=400)
    if request.POST.get('user_id') != str(request.user.id):
        logger.error('EolForumNotification - User Ids are differents, user id post: {}, user id resquest: {}'.format(request.POST.get('user_id'), request.user.id))
        return HttpResponse(status=400)
    if request.POST.get('period') not in ['never', 'daily', 'weekly']:
        logger.error('EolForumNotification - Period not in (never, weekly, daily), Data: {}'.format(request.POST))
        return HttpResponse(status=400)
    with transaction.atomic():
        try:
            course_id = CourseKey.from_string(request.POST.get('course_id'))
            discussion = EolForumNotificationsDiscussions.objects.get(discussion_id=request.POST.get('discussion_id'), course_id=course_id)
            EolForumNotificationsUser.objects.update_or_create(
                user=request.user,
                discussion=discussion,
                defaults={
                    'how_often': request.POST.get('period')
                    })
            return HttpResponse(status=200)
        except Exception as e:
            logger.error('EolForumNotification - Error to update or create EolForumNotificationsUser, error {}, data: {}'.format(str(e), request.POST))
            return HttpResponse(status=400)

def send_notification(how_often):
    """
        Send email with threads and/or comments unreaded
    """
    from .tasks import task_send_single_email
    delta = 7 # how_often = weekly
    if how_often == 'daily':
        delta = 1
    try:
        current_site = get_current_site()
        platform_name =  current_site.configuration.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
        url_site =  current_site.configuration.get_value('LMS_BASE', settings.LMS_ROOT_URL)
    except Exception:
        logger.error('EolForumNotification - Error to get platform name and url site')
        platform_name =  settings.PLATFORM_NAME
        url_site = settings.LMS_ROOT_URL
    courses_data = get_courses_onlive()
    for course in courses_data:
        for discussion in courses_data[course]['discussions']:
            users_notifications = get_users_notifications(how_often, discussion['discussion_id'], course)
            block = get_block_info(discussion['block_key'])
            for user in users_notifications:
                context = {
                    'user_id':user['user__id'],
                    'email': user['user__email'],
                    'course_name': courses_data[course]['course_name'],
                    'image': courses_data[course]['image'],
                    'platform_name': platform_name,
                    'url_site': url_site,
                    'how_often': how_often,
                    'discussion_name': block['display_name'],
                    'parent': block['parent'],
                    'course_id': course
                }
                context.update(discussion)
                context.pop('block_key')
                task_send_single_email.delay(discussion['discussion_id'], course, context)
        with transaction.atomic():
            discussion_model = EolForumNotificationsDiscussions.objects.get(discussion_id=discussion['discussion_id'], course_id=CourseKey.from_string(course))
            if how_often == 'daily':
                discussion_model.daily_threads = 0
                discussion_model.daily_comment = 0
            else:
                discussion_model.weekly_threads = 0
                discussion_model.weekly_comment = 0
            discussion_model.save()
    
