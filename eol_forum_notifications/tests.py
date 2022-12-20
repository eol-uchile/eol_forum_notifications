# -*- coding: utf-8 -*-


from mock import patch, Mock, PropertyMock
from collections import namedtuple

import json

from django.test import TestCase, Client
from django.urls import reverse

from common.djangoapps.util.testing import UrlResetMixin
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from xmodule.modulestore.tests.factories import CourseFactory
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
from xblock.field_data import DictFieldData
from opaque_keys.edx.keys import CourseKey
from common.djangoapps.student.roles import CourseStaffRole
from django.test.utils import override_settings
from .models import EolForumNotifications
import urllib.parse
from urllib.parse import parse_qs
from datetime import timedelta
from django.utils.timezone import now
from .views import send_notification, send_notification_always_thread, send_notification_always_comment
from .utils import get_discussions

class TestRequest(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None
    params = None
    headers = None

class FakeThread(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    course_id= None
    id= None
    title= None
    user_id= None
    anonymous= None
    username= None
    created_at= None
    body= None
    commentable_id= None

class FakeComment(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    course_id= None
    id= None
    title= None
    user_id= None
    anonymous= None
    username= None
    created_at= None
    body= None
    commentable_id= None
    thread = None
    parent_id = None

class TestNotifiactionsDiscussion(UrlResetMixin, ModuleStoreTestCase):

    def setUp(self):
        super(TestNotifiactionsDiscussion, self).setUp()
        self.course = CourseFactory.create(org='foo', course='baz', run='bar')

        with patch('common.djangoapps.student.models.cc.User.save'):
            # Create the student
            self.student = UserFactory(
                username='student',
                password='test',
                email='student@edx.org')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)
            self.client = Client()
            self.client.login(username='student', password='test')
            self.student2 = UserFactory(
                username='student2',
                password='test',
                email='student2@edx.org')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student2, course_id=self.course.id)
            # Create staff user
            self.staff_user = UserFactory(
                username='staff_user',
                password='test',
                email='staff@edx.org')
            CourseEnrollmentFactory(
                user=self.staff_user,
                course_id=self.course.id)
            CourseStaffRole(self.course.id).add_users(self.staff_user)
            collection = [
                {
                    "comments_count": 5,
                    "user_id": str(self.staff_user.id),
                    "created_at": "2020-11-10T18:51:04Z",
                    "username": "test1",
                    "unread_comments_count": 1,
                    "commentable_id": "course",
                    "anonymous_to_peers": False,
                    "closed": False,
                    "pinned": False,
                    "updated_at": "2020-11-23T15:44:49Z",
                    "course_id": "course-v1:eol+test101+2020",
                    "id": "5faae1182f1f5e001b09d32a",
                    "anonymous": False,
                    "context": "course",
                    "title": "asdasd",
                    "votes": {},
                    "abuse_flaggers": [],
                    "read":False,
                    "type":"thread",
                    "thread_type":"question",
                    "at_position_list":[],
                    "endorsed":True,
                    "last_activity_at":"2020-11-23T15:44:49Z",
                    "body":"asdasd"
                },
                {
                    "comments_count": 0,
                    "user_id": str(self.student.id),
                    "created_at": "2020-11-23T14:54:32Z",
                    "username": "test2",
                    "unread_comments_count": 0,
                    "commentable_id": "course",
                    "anonymous_to_peers": False,
                    "closed": False,
                    "pinned": False,
                    "updated_at": "2020-11-23T14:54:32Z",
                    "course_id": "course-v1:eol+test101+2020",
                    "id": "5fbbcd282f1f5e001a0740c4",
                    "anonymous": True,
                    "context": "course",
                    "title": "asdasd",
                    "votes": {},
                    "abuse_flaggers": [],
                    "read":True,
                    "type":"thread",
                    "thread_type":"discussion",
                    "at_position_list":[],
                    "endorsed":False,
                    "last_activity_at":"2020-11-23T14:54:32Z",
                    "body":"asdaseda"
                }]
            self.data_all_thread = {"page": 1, "num_pages": 1, "collection": collection}
            self.data_thread_1 = {
                "comments_count": 3,
                "non_endorsed_resp_total": 1,
                "user_id": str(self.staff_user.id),
                "non_endorsed_responses": [
                    {
                        "anonymous": False,
                        "body": "asd",
                        "user_id": str(self.student.id),
                        "thread_id": "5faae1182f1f5e001b09d32a",
                        "username": "test2",
                        "children": [
                                {
                                    "anonymous": False,
                                    "body": "o mantequilla",
                                    "parent_id": "5faae14a2f1f5e001b09d32d",
                                    "user_id": str(self.staff_user.id),
                                    "created_at": "2020-11-10T18:52:01Z",
                                    "username": "test1",
                                    "children": [],
                                    "depth":1,
                                    "commentable_id":"course",
                                    "anonymous_to_peers":False,
                                    "closed":False,
                                    "votes":{},
                                    "updated_at": "2020-11-10T18:52:01Z",
                                    "at_position_list": [],
                                    "endorsed":False,
                                    "course_id":"course-v1:eol+test101+2020",
                                    "abuse_flaggers":[],
                                    "thread_id":"5faae1182f1f5e001b09d32a",
                                    "id":"5faae1512f1f5e001b09d32e",
                                    "type":"comment"
                                }
                        ],
                        "depth":0,
                        "commentable_id":"course",
                        "anonymous_to_peers":False,
                        "closed":False,
                        "votes":{},
                        "updated_at": "2020-11-10T18:51:54Z",
                        "at_position_list": [],
                        "endorsed":False,
                        "course_id":"course-v1:eol+test101+2020",
                        "abuse_flaggers":[],
                        "created_at":"2020-11-10T18:51:54Z",
                        "id":"5faae14a2f1f5e001b09d32d",
                        "type":"comment"
                    }
                ],
                "resp_limit": 200,
                "created_at": "2020-11-10T18:51:04Z",
                "username": "test1",
                "unread_comments_count": 0,
                "commentable_id": "ecedb9f8c633496d3fc4bd014ee30a65c75796f2",
                "anonymous_to_peers": False,
                "closed": False,
                "pinned": False,
                "updated_at": "2020-11-23T15:44:49Z",
                "resp_total": 2,
                "course_id": "course-v1:eol+test101+2020",
                "id": "5faae1182f1f5e001b09d32a",
                "anonymous": False,
                "body": "d1",
                "endorsed_responses": [
                    {
                        "anonymous": False,
                        "body": "asdf",
                        "user_id": str(self.student.id),
                        "thread_id": "5faae1182f1f5e001b09d32a",
                        "username": "test2",
                        "children": [
                            {
                                "anonymous": False,
                                "body": "o asdasd",
                                "parent_id": "5faae1392f1f5e001b09d32b",
                                "user_id": str(self.staff_user.id),
                                "created_at": "2020-11-10T18:51:45Z",
                                "username": "test1",
                                "children": [],
                                "depth":1,
                                "commentable_id":"course",
                                "anonymous_to_peers":False,
                                "closed":False,
                                "votes":{},
                                "updated_at": "2020-11-10T18:51:45Z",
                                "at_position_list": [],
                                "endorsed":False,
                                "course_id":"course-v1:eol+test101+2020",
                                "abuse_flaggers":[],
                                "thread_id":"5faae1182f1f5e001b09d32a",
                                "id":"5faae1412f1f5e001b09d32c",
                                "type":"comment"
                            },
                            {
                                "anonymous": False,
                                "body": "ola soy test2",
                                "parent_id": "5faae1392f1f5e001b09d32b",
                                "user_id": str(self.student.id),
                                "created_at": "2020-11-23T15:44:49Z",
                                "username": "test2",
                                "children": [],
                                "depth":1,
                                "commentable_id":"course",
                                "anonymous_to_peers":False,
                                "closed":False,
                                "votes":{},
                                "updated_at": "2020-11-23T15:44:49Z",
                                "at_position_list": [],
                                "endorsed":False,
                                "course_id":"course-v1:eol+test101+2020",
                                "abuse_flaggers":[],
                                "thread_id":"5faae1182f1f5e001b09d32a",
                                "id":"5fbbd8f12f1f5e001a0740c5",
                                "type":"comment"
                            }
                        ],
                        "depth":0,
                        "endorsement":{},
                        "commentable_id": "course",
                        "anonymous_to_peers": False,
                        "closed": False,
                        "votes": {},
                        "updated_at": "2020-11-10T18:58:28Z",
                        "at_position_list": [],
                        "endorsed":True,
                        "course_id":"course-v1:eol+test101+2020",
                        "abuse_flaggers":[],
                        "created_at":"2020-11-10T18:51:37Z",
                        "id":"5faae1392f1f5e001b09d32b",
                        "type":"comment"
                    }
                ],
                "context": "course",
                "title": "p1",
                "votes": {},
                "abuse_flaggers": [],
                "read": True,
                "type": "thread",
                "thread_type": "question",
                "at_position_list": [],
                "endorsed": True,
                "last_activity_at": "2020-11-23T15:44:49Z",
                "resp_skip": 0
            }
            self.data_thread_2 = {
                "comments_count": 2,
                "user_id": str(self.student.id),
                "resp_limit": 200,
                "title": "p2",
                "created_at": "2020-11-16T17:49:47Z",
                "username": "test2",
                "unread_comments_count": 0,
                "commentable_id": "ecedb9f8c633496d3fc4bd014ee30a65c75796f2",
                "anonymous_to_peers": False,
                "closed": False,
                "pinned": False,
                "updated_at": "2020-11-20T14:45:06Z",
                "resp_total": 1,
                "course_id": "course-v1:eol+test101+2020",
                "id": "5fbbcd282f1f5e001a0740c4",
                "anonymous": True,
                "body": "d2",
                "context": "course",
                "children": [{"anonymous": False,
                            "body": "shajdkhsajkdhsajd",
                            "user_id": str(self.student.id),
                            "thread_id": "5fbbcd282f1f5e001a0740c4",
                            "username": "test1",
                            "children": [{"anonymous": False,
                                            "body": "hsajdhjsakd",
                                            "parent_id": "5fb71232132130019e5c0d1",
                                            "user_id": str(self.staff_user.id),
                                            "created_at": "2020-11-20T14:45:06Z",
                                            "username": "test2",
                                            "children": [],
                                            "depth":1,
                                            "commentable_id":"ecedb9f8c633496d3fc4bd014ee30a65c75796f2",
                                            "anonymous_to_peers":False,
                                            "closed":False,
                                            "votes":{},
                                            "updated_at": "2020-11-20T14:45:06Z",
                                            "at_position_list": [],
                                            "endorsed":False,
                                            "course_id":"course-v1:eol+test101+2020",
                                            "abuse_flaggers":[],
                                            "thread_id":"5fbbcd282f1f5e001a0740c4",
                                            "id":"5fb7d6214231245e0019e5c0d2",
                                            "type":"comment"}],
                            "depth":0,
                            "commentable_id":"ecedb9f8c633496d3fc4bd014ee30a65c75796f2",
                            "anonymous_to_peers":False,
                            "closed":False,
                            "votes":{},
                            "updated_at": "2020-11-20T14:44:56Z",
                            "at_position_list": [],
                            "endorsed":False,
                            "course_id":"course-v1:eol+test101+2020",
                            "abuse_flaggers":[],
                            "created_at":"2020-11-20T14:44:56Z",
                            "id":"5fb71232132130019e5c0d1",
                            "type":"comment"}],
                "votes": {},
                "abuse_flaggers": [],
                "courseware_title": "Week 1 / Topic-Level Student-Visible Label",
                "read": True,
                "type": "thread",
                "thread_type": "discussion",
                "at_position_list": [],
                "endorsed": False,
                "last_activity_at": "2020-11-20T14:45:06Z",
                "courseware_url": "/courses/course-v1:eol+test101+2020/jump_to/block-v1:eol+test101+2020+type@discussion+block@62b0a5dfbecb4738806620e2d4964a12",
                "resp_skip": 0
                }
            self.data_comment = {
                'id': '63877b099dcf4e001a47ac3f', 
                'body': 'sdsad adas dsd a', 
                'course_id': self.course.id, 
                'endorsed': False, 
                'anonymous': False, 
                'anonymous_to_peers': False, 
                'created_at': '2022-11-30T15:47:21Z', 
                'updated_at': '2022-11-30T15:47:21Z', 
                'at_position_list': [], 
                'user_id': self.staff_user.id, 
                'username': self.staff_user.username, 
                'depth': 0, 
                'closed': False, 
                'thread_id': '5faae1182f1f5e001b09d32a', 
                'parent_id': None, 
                'commentable_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2', 
                'votes': {'count': 0, 'up_count': 0, 'down_count': 0, 'point': 0}, 
                'abuse_flaggers': [], 
                'type': 'comment', 
                'child_count': 0
                }

    @patch('openedx.core.djangoapps.django_comment_common.models.ForumsConfig.current')
    @patch('requests.request')
    def test_send_notification(self, get, _):
        """
          test send_notification normal process
        """
        user_notif = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        aux_sent_at = user_notif.sent_at
        get.side_effect = [
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_all_thread),
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_thread_1),
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_thread_2), 
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_all_thread),
                ]

        send_notification('monthly')
        user_notif2 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertTrue(aux_sent_at < user_notif2.sent_at)

    def test_send_notification_no_notifications(self):
        """
          test send_notification normal process without notifications
        """
        user_notif = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now(),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        aux_sent_at = user_notif.sent_at
        send_notification('monthly')
        user_notif = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertEqual(aux_sent_at, user_notif.sent_at)

    @patch('openedx.core.djangoapps.django_comment_common.models.ForumsConfig.current')
    @patch('requests.request')
    def test_send_notification_no_threads(self, get, _):
        """
          test send_notification without threads
        """
        user_notif = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        aux_sent_at = user_notif.sent_at
        self.data_all_thread['collection'] = []
        get.side_effect = [
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_all_thread),
                ]

        send_notification('monthly')
        user_notif2 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertEqual(aux_sent_at, user_notif.sent_at)

    def test_get_discussions(self):
        """
            get_discussions normal process
        """
        EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'asdasd456456456qweqweqeqweyuiyuibvbnnbv',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = '4a5s6d45sa64d56as4d5s6a156sa4d',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=1),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'asdasdsadasdsadsadsa1312321312321321',
                course_id = self.course.id,
                how_often = 'never',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = 'asdasdsadasdsadsadsa1312321312321321',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        timeout = (now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        discussions = get_discussions('monthly', timeout)
        expect = [
            {'discussion_id':'asdasd456456456qweqweqeqweyuiyuibvbnnbv', 'course_id':self.course.id},
            {'discussion_id':'ecedb9f8c633496d3fc4bd014ee30a65c75796f2', 'course_id':self.course.id}
        ]
        self.assertEqual(expect, discussions)
        timeout = (now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        discussions = get_discussions('always', timeout)
        expect = [
            {'discussion_id':'asdasdsadasdsadsadsa1312321312321321', 'course_id':self.course.id}
        ]
        self.assertEqual(expect, discussions)

    def test_send_notification_always_thread(self):
        """
            send_notification_always_thread() normal process
        """
        user_notif_1 = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        aux_sent_at_1 = user_notif_1.sent_at
        user_notif_2 = EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =True,
                own_comment_created = False
            )
        aux_sent_at_2 = user_notif_2.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.staff_user.id
        thread.anonymous= False
        thread.username= self.staff_user.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        send_notification_always_thread(thread, self.staff_user)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        aux2 = EolForumNotifications.objects.get(user=self.student, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertTrue(aux_sent_at_2 < aux2.sent_at)
        self.assertEqual(aux_sent_at_1 , aux1.sent_at)
    
    def test_send_notification_always_thread_no_notifications(self):
        """
            send_notification_always_thread() without notifications
        """
        user_notif_1 = EolForumNotifications.objects.create(
            user = self.staff_user,
            discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            course_id = self.course.id,
            how_often = 'weekly',
            sent_at = now() - timedelta(days=35),
            comment_created = False,
            thread_created =True,
            own_comment_created = False
        )
        aux_sent_at_1 = user_notif_1.sent_at
        user_notif_2 = EolForumNotifications.objects.create(
            user = self.student,
            discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            course_id = self.course.id,
            how_often = 'always',
            sent_at = now() - timedelta(days=35),
            comment_created = True,
            thread_created = False,
            own_comment_created = False
        )
        aux_sent_at_2 = user_notif_2.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.student2.id
        thread.anonymous= False
        thread.username= self.student2.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        send_notification_always_thread(thread, self.student2)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        aux2 = EolForumNotifications.objects.get(user=self.student, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertEqual(aux_sent_at_2 , aux2.sent_at)
        self.assertEqual(aux_sent_at_1 , aux1.sent_at)
    
    def test_send_notification_always_thread_same_user(self):
        """
            send_notification_always_thread() when is the same user
        """
        user_notif_1 = EolForumNotifications.objects.create(
            user = self.staff_user,
            discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            course_id = self.course.id,
            how_often = 'always',
            sent_at = now() - timedelta(days=35),
            comment_created = False,
            thread_created =True,
            own_comment_created = False
        )
        aux_sent_at_1 = user_notif_1.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.staff_user.id
        thread.anonymous= False
        thread.username= self.staff_user.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        send_notification_always_thread(thread, self.staff_user)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertEqual(aux_sent_at_1 , aux1.sent_at)

    @patch('openedx.core.djangoapps.django_comment_common.models.ForumsConfig.current')
    @patch('requests.request')
    def test_send_notification_always_comment(self, get, _):
        """
            send_notification_always_comment() normal process
        """
        get.side_effect = [
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_comment),
                ]
        user_notif_1 = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = True,
                thread_created =True,
                own_comment_created = True
            )
        aux_sent_at_1 = user_notif_1.sent_at
        user_notif_2 = EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = True,
                thread_created =True,
                own_comment_created = True
            )
        aux_sent_at_2 = user_notif_2.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.staff_user.id
        thread.anonymous= False
        thread.username= self.staff_user.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        comment = FakeComment()
        comment.course_id= self.course.id
        comment.id= '123'
        comment.title= 'asdawqe'
        comment.user_id= self.staff_user.id
        comment.anonymous= False
        comment.username= self.staff_user.username
        comment.created_at= now()
        comment.body='asdasd'
        comment.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'
        comment.thread = thread
        comment.parent_id = '63877b099dcf4e001a47ac3f'
        send_notification_always_comment(comment, self.staff_user)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        aux2 = EolForumNotifications.objects.get(user=self.student, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertTrue(aux_sent_at_2 < aux2.sent_at)
        self.assertEqual(aux_sent_at_1 , aux1.sent_at)

    @patch('openedx.core.djangoapps.django_comment_common.models.ForumsConfig.current')
    @patch('requests.request')
    def test_send_notification_always_comment_own(self, get, _):
        """
            send_notification_always_comment() when own_comment_created is true
        """
        get.side_effect = [
            namedtuple(
                "Request", [
                    "status_code", "json"])(
                200, lambda:self.data_comment),
                ]
        user_notif_1 = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =False,
                own_comment_created = True
            )
        aux_sent_at_1 = user_notif_1.sent_at
        user_notif_2 = EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = False,
                thread_created =False,
                own_comment_created = True
            )
        aux_sent_at_2 = user_notif_2.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.student.id
        thread.anonymous= False
        thread.username= self.student.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        comment = FakeComment()
        comment.course_id= self.course.id
        comment.id= '123'
        comment.title= 'asdawqe'
        comment.user_id= self.staff_user.id
        comment.anonymous= False
        comment.username= self.staff_user.username
        comment.created_at= now()
        comment.body='asdasd'
        comment.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'
        comment.thread = thread
        comment.parent_id = '63877b099dcf4e001a47ac3f'
        send_notification_always_comment(comment, self.staff_user)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        aux2 = EolForumNotifications.objects.get(user=self.student, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertTrue(aux_sent_at_2 < aux2.sent_at)
        self.assertEqual(aux_sent_at_1 , aux1.sent_at)

    def test_send_notification_always_comment_no_notifications(self):
        """
            send_notification_always_comment() without notifications
        """
        user_notif_1 = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'monthly',
                sent_at = now() - timedelta(days=35),
                comment_created = True,
                thread_created =True,
                own_comment_created = True
            )
        aux_sent_at_1 = user_notif_1.sent_at
        user_notif_2 = EolForumNotifications.objects.create(
                user = self.student,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'weekly',
                sent_at = now() - timedelta(days=35),
                comment_created = True,
                thread_created =True,
                own_comment_created = True
            )
        aux_sent_at_2 = user_notif_2.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.staff_user.id
        thread.anonymous= False
        thread.username= self.staff_user.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        comment = FakeComment()
        comment.course_id= self.course.id
        comment.id= '123'
        comment.title= 'asdawqe'
        comment.user_id= self.staff_user.id
        comment.anonymous= False
        comment.username= self.staff_user.username
        comment.created_at= now()
        comment.body='asdasd'
        comment.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'
        comment.thread = thread
        comment.parent_id = None
        send_notification_always_comment(comment, self.staff_user)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        aux2 = EolForumNotifications.objects.get(user=self.student, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertEqual(aux_sent_at_2, aux2.sent_at)
        self.assertEqual(aux_sent_at_1, aux1.sent_at)

    def test_send_notification_always_comment_same_user(self):
        """
            send_notification_always_comment() when the comment author is the current user
        """
        user_notif_1 = EolForumNotifications.objects.create(
                user = self.staff_user,
                discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
                course_id = self.course.id,
                how_often = 'always',
                sent_at = now() - timedelta(days=35),
                comment_created = True,
                thread_created =True,
                own_comment_created = True
            )
        aux_sent_at_1 = user_notif_1.sent_at
        thread = FakeThread()
        thread.course_id= self.course.id
        thread.id= '123'
        thread.title= 'asdawqe'
        thread.user_id= self.staff_user.id
        thread.anonymous= False
        thread.username= self.staff_user.username
        thread.created_at= now()
        thread.body='asdasd'
        thread.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'

        comment = FakeComment()
        comment.course_id= self.course.id
        comment.id= '123'
        comment.title= 'asdawqe'
        comment.user_id= self.staff_user.id
        comment.anonymous= False
        comment.username= self.staff_user.username
        comment.created_at= now()
        comment.body='asdasd'
        comment.commentable_id= 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2'
        comment.thread = thread
        comment.parent_id = None
        send_notification_always_comment(comment, self.staff_user)
        aux1 = EolForumNotifications.objects.get(user=self.staff_user, discussion_id = 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2')
        self.assertEqual(aux_sent_at_1, aux1.sent_at)

    def test_save_notifications(self):
        """
            save_notifications() normal process
        """
        post_data = {
            'period': "always",
            'when': [['1','2','3']],
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        notif = EolForumNotifications.objects.get(user=self.student, discussion_id=post_data['discussion_id'])
        self.assertTrue(notif.comment_created)
        self.assertTrue(notif.thread_created)
        self.assertTrue(notif.own_comment_created)
        self.assertEqual(notif.how_often, post_data['period'])
        self.assertEqual(notif.course_id, self.course.id)

    def test_save_notifications_anonymous(self):
        """
            save_notifications() when user is anonymous
        """
        post_data = {
            'period': "always",
            'when': [['1','2','3']],
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        client_anonymous = Client()
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        response = client_anonymous.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())

    def test_save_notifications_wrong_method(self):
        """
            save_notifications() when request method is not post
        """
        post_data = {
            'period': "always",
            'when': [['1','2','3']],
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        response = self.client.get(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())

    def test_save_notifications_wrong_params(self):
        """
            save_notifications() when missing a params request
        """
        post_data = {
            'period': "always",
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())

    def test_save_notifications_wrong_user(self):
        """
            save_notifications() when request user is different post user
        """
        post_data = {
            'period': "always",
            'when': [['1','2','3']],
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': str(self.course.id),
            'user_id': '9598'
        }
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())

    def test_save_notifications_wrong_course(self):
        """
            save_notifications() when course id is wrong
        """
        post_data = {
            'period': "always",
            'when': [['1','2','3']],
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': 'asdasdsdasdsa',
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotifications.objects.filter(user=self.student, discussion_id=post_data['discussion_id']).exists())

