#!/usr/bin/env python
# -- coding: utf-8 --

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponse
import openedx.core.djangoapps.django_comment_common.comment_client as cc
from openedx.core.djangoapps.django_comment_common.utils import ThreadContext
from .models import EolForumNotifications


from datetime import timedelta
from django.utils.timezone import now
import json
import requests
import logging

logger = logging.getLogger(__name__)


def check_own_comment(data, user_id):
    """
        check if author threar/comment is the same as the current user
    """
    if data['thread_author_id'] == user_id:
        return True
    if data['parent'] is not None and data['parent']['author_id'] == user_id:
        return True
    return False

def get_comment(comment_id):
    """
        Return comment based on comment_id
    """
    comment = cc.Comment.find(id=comment_id).retrieve()
    return comment

def get_users_notifications(how_often, discussion_id, timeout):
    """
        return all user based on params
    """
    notifications = EolForumNotifications.objects.filter(how_often=how_often, discussion_id=discussion_id, sent_at__lte=timeout)
    return list(notifications)

def get_discussions(how_often, timeout):
    """
        return all discussion id based in params
    """
    discussions = EolForumNotifications.objects.filter(how_often=how_often, sent_at__lte=timeout).values('discussion_id', 'course_id').distinct()
    return list(discussions)

def get_user_data(discussion_id, user):
    """
        return user notification data
    """
    try:
        aux = EolForumNotifications.objects.get(discussion_id=discussion_id, user=user)
        return json.dumps({
            'how_often': aux.how_often,
            'comment_created': aux.comment_created,
            'thread_created': aux.thread_created,
            'own_comment_created': aux.own_comment_created
        })
    except EolForumNotifications.DoesNotExist:
        logger.info('EolForumNotification - Error to get notif model, discussion {}, user: {}'.format(discussion_id, user))
        return '{}'

def get_threads_by_users(discussion_id, course_id, user_id=None):
    """
        get all threads
    """
    query_params = {
        'page': 1,
        'per_page': 1000,
        'sort_key': 'activity',
        'course_id': str(course_id),
        'context': ThreadContext.COURSE,
        'commentable_id': discussion_id
    }
    if user_id:
        query_params['user_id'] = user_id
    try:
        paginated_results = cc.Thread.search(query_params)
    except cc.utils.CommentClientRequestError:
        logger.info(
            'EolForumNotification - Error en obtener las publicaciones id_forum: {}'.format(discussion_id))
        return None
    return paginated_results.collection

def find_thread(thread_id, resp_init, resp_limit):
    """
        sort_key_mapper = {
        "date" => :created_at,
        "activity" => :last_activity_at,
        "votes" => :"votes.point",
        "comments" => :comment_count,
        }
    Finds the discussion thread with the specified ID.
    """
    import openedx.core.djangoapps.django_comment_common.comment_client as cc
    try:
        thread = cc.Thread.find(thread_id).retrieve(
            with_responses=True,
            recursive=True,
            response_skip=resp_init,
            response_limit=resp_limit)
    except cc.utils.CommentClientRequestError:
        logger.info(
            'EolForumNotification - Error en obtener la publicacion thread_id: {}'.format(thread_id))
        return None

    return thread

def reduce_data_forum(hilos):
    """
        Get comments for each thread
    """
    content_forum = {}
    student_data = {}
    for hilo in hilos:
        aux_thread = {
            'id': hilo['id'],
            'user_id': hilo['user_id'],
            'username': hilo['username'],
            'anonymous': hilo['anonymous'],
            'thread_type': hilo['thread_type'],
            'type': hilo['type'],
            'endorsed': hilo['endorsed'],
            'title': hilo['title'],
            'body': hilo['body'],
            'comments_count': hilo['comments_count'],
            'children': [],
            'url_thread': reverse('single_thread', kwargs={'course_id':hilo['course_id'],'discussion_id':hilo['commentable_id'], 'thread_id':hilo['id']})
        }
        lista_comentarios, resp_total = get_all_comments_thread(hilo['id'])
        aux_thread['resp_total'] = resp_total
        for comment in lista_comentarios:
            aux_thread['children'].append(comment['id'])
            aux_comment = {
                'id': comment['id'],
                'username': comment['username'],
                'user_id': comment['user_id'],
                'body': comment['body'],
                'parent_id': comment['thread_id'],
                'type': comment['type'],
                'children': [],
                'endorsed': comment['endorsed']
            }
            for sub_comment in comment['children']:
                aux_comment['children'].append(sub_comment['id'])
                aux_sub_comment = {
                    'id': sub_comment['id'],
                    'username': sub_comment['username'],
                    'user_id': sub_comment['user_id'],
                    'body': sub_comment['body'],
                    'parent_id': sub_comment['thread_id'],
                    'type': sub_comment['type'],
                    'children': [],
                    'endorsed': sub_comment['endorsed']
                }
                content_forum[sub_comment['id']] = aux_sub_comment
                if hilo['user_id'] != sub_comment['user_id'] and comment['user_id'] != sub_comment['user_id']:
                    if sub_comment['user_id'] not in student_data:
                        student_data[sub_comment['user_id']] = {}
                    if hilo['id'] not in student_data[sub_comment['user_id']]:
                        student_data[sub_comment['user_id']
                                        ][hilo['id']] = {}
                    if comment['id'] not in student_data[sub_comment['user_id']][hilo['id']]:
                        student_data[sub_comment['user_id']
                                        ][hilo['id']][comment['id']] = []

                    student_data[sub_comment['user_id']][hilo['id']
                                                            ][comment['id']].append(sub_comment['id'])
            ##END FOR###############################################
            content_forum[comment['id']] = aux_comment
            if hilo['user_id'] != comment['user_id']:
                if comment['user_id'] not in student_data:
                    student_data[comment['user_id']] = {}
                if hilo['id'] not in student_data[comment['user_id']]:
                    student_data[comment['user_id']][hilo['id']] = {}
                student_data[comment['user_id']
                                ][hilo['id']][comment['id']] = []

        ##END FOR###################################################
        content_forum[hilo['id']] = aux_thread
        if hilo['user_id'] not in student_data:
            student_data[hilo['user_id']] = {}
        student_data[hilo['user_id']][hilo['id']] = {}

    return content_forum, student_data

def get_all_comments_thread(id_thread):
    """
        Get all comments for id_thread
    """
    children = []
    endorsed_responses = []
    non_endorsed_responses = []
    limit = 200
    skip = 0
    aux = -1
    resp_total = 0

    while aux < resp_total:
        resp_hilo = find_thread(id_thread, skip, limit)
        if resp_hilo is not None:
            thread = resp_hilo.attributes
            resp_total = thread['resp_total']
            if thread['thread_type'] == 'discussion':
                children.extend(thread['children'])
            elif thread['thread_type'] == 'question':
                endorsed_responses.extend(thread['endorsed_responses'])
                non_endorsed_responses.extend(thread['non_endorsed_responses'])
        aux = limit
        skip = limit
        limit = limit + 200

    list_comment = children + endorsed_responses + non_endorsed_responses
    return list_comment, resp_total

def reduce_threads(discussion_id, data):
    threads = []
    hilos = get_threads_by_users(discussion_id, data['course_id'], data['user_id'])
    if hilos is None:
        return None
    if len(hilos) == 0:
        return threads
    threads = [x['id'] for x in hilos if x['read'] is False or x['unread_comments_count'] > 0]
    return threads

    