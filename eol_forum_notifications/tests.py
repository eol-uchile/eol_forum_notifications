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
from .models import EolForumNotificationsUser, EolForumNotificationsDiscussions
from opaque_keys.edx.keys import UsageKey
import urllib.parse
from urllib.parse import parse_qs
from datetime import timedelta
from django.utils.timezone import now
from .views import send_notification

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

class TestNotifiactionsDiscussion(UrlResetMixin, ModuleStoreTestCase):

    def setUp(self):
        super(TestNotifiactionsDiscussion, self).setUp()
        self.course = CourseFactory.create(org='foo', course='baz', run='bar')
        self.block_key = UsageKey.from_string('block-v1:eol+test100+2021_1+type@eoldiscussion+block@5c13942678184cab9a5345b660292c6e')
        self.discussion = EolForumNotificationsDiscussions.objects.create(
            discussion_id= "1234567890",
            course_id= self.course.id,
            block_key=self.block_key
            )
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

    def test_save_notifications(self):
        """
            save_notifications() normal process
        """
        post_data = {
            'period': "daily",
            'discussion_id': self.discussion.discussion_id,
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        notif = EolForumNotificationsUser.objects.get(user=self.student, discussion=self.discussion)
        self.assertEqual(notif.how_often, post_data['period'])

    def test_save_notifications_anonymous(self):
        """
            save_notifications() when user is anonymous
        """
        post_data = {
            'period': "daily",
            'discussion_id': self.discussion.discussion_id,
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        client_anonymous = Client()
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = client_anonymous.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())

    def test_save_notifications_wrong_method(self):
        """
            save_notifications() when request method is not post
        """
        post_data = {
            'period': "daily",
            'discussion_id': self.discussion.discussion_id,
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = self.client.get(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())

    def test_save_notifications_wrong_params(self):
        """
            save_notifications() when missing a params request
        """
        post_data = {
            'discussion_id': 'ecedb9f8c633496d3fc4bd014ee30a65c75796f2',
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())

    def test_save_notifications_wrong_user(self):
        """
            save_notifications() when request user is different post user
        """
        post_data = {
            'period': "daily",
            'discussion_id': self.discussion.discussion_id,
            'course_id': str(self.course.id),
            'user_id': '123'
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())

    def test_save_notifications_wrong_course(self):
        """
            save_notifications() when course id is wrong
        """
        post_data = {
            'period': "daily",
            'discussion_id': self.discussion.discussion_id,
            'course_id': 'asdasdsadas',
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())

    def test_save_notifications_wrong_period(self):
        """
            save_notifications() when course id is wrong
        """
        post_data = {
            'period': "monthly",
            'discussion_id': self.discussion.discussion_id,
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=self.discussion).exists())

    def test_save_notifications_wrong_no_discussion(self):
        """
            save_notifications() when course id is wrong
        """
        post_data = {
            'period': "daily",
            'discussion_id': '321654987',
            'course_id': str(self.course.id),
            'user_id': str(self.student.id)
        }
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=post_data['discussion_id']).exists())
        response = self.client.post(
            reverse('eol_discussion_notification:save'), post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EolForumNotificationsUser.objects.filter(user=self.student, discussion=post_data['discussion_id']).exists())
    
    @override_settings(PLATFORM_NAME='Test')
    @override_settings(LMS_ROOT_URL='https://test.ts')
    @patch('eol_forum_notifications.utils.get_block_info')
    @patch('eol_forum_notifications.utils.course_image_url')
    @patch('eol_forum_notifications.utils.get_course_by_id')
    def test_send_notifications_daily(self, course_mock, image_mock, block_mock):
        course_mock.side_effect = [namedtuple("Course", ["display_name_with_default", "end"])("this is a display name", None)]
        image_mock.return_value = '/assets/image.jpg'
        block_mock.return_value = {'display_name':'Test discussion xblock', 'parent': 'asdadssa'}
        user_notif = EolForumNotificationsUser.objects.create(discussion=self.discussion, user=self.student, how_often="daily")
        self.discussion.daily_threads = 3
        self.discussion.daily_comment = 3
        self.discussion.weekly_threads = 3
        self.discussion.weekly_comment = 3
        self.discussion.save()
        self.assertEqual(self.discussion.daily_threads, 3)
        self.assertEqual(self.discussion.daily_comment, 3)
        self.assertEqual(self.discussion.weekly_threads, 3)
        self.assertEqual(self.discussion.weekly_comment, 3)
        send_notification('daily')
        aux = EolForumNotificationsDiscussions.objects.get(id=self.discussion.id)
        self.assertEqual(aux.daily_threads, 0)
        self.assertEqual(aux.daily_comment, 0)
        self.assertEqual(aux.weekly_threads, 3)
        self.assertEqual(aux.weekly_comment, 3)

    @override_settings(PLATFORM_NAME='Test')
    @override_settings(LMS_ROOT_URL='https://test.ts')
    @patch('eol_forum_notifications.utils.course_image_url')
    @patch('eol_forum_notifications.utils.get_course_by_id')
    def test_send_notifications_weekly(self, course_mock, image_mock):
        course_mock.side_effect = [namedtuple("Course", ["display_name_with_default", "end"])("this is a display name", None)]
        image_mock.return_value = '/assets/image.jpg'
        user_notif = EolForumNotificationsUser.objects.create(discussion=self.discussion, user=self.student, how_often="daily")
        self.discussion.daily_threads = 3
        self.discussion.daily_comment = 3
        self.discussion.weekly_threads = 3
        self.discussion.weekly_comment = 3
        self.discussion.save()
        self.assertEqual(self.discussion.daily_threads, 3)
        self.assertEqual(self.discussion.daily_comment, 3)
        self.assertEqual(self.discussion.weekly_threads, 3)
        self.assertEqual(self.discussion.weekly_comment, 3)
        send_notification('weekly')
        aux = EolForumNotificationsDiscussions.objects.get(id=self.discussion.id)
        self.assertEqual(aux.daily_threads, 3)
        self.assertEqual(aux.daily_comment, 3)
        self.assertEqual(aux.weekly_threads, 0)
        self.assertEqual(aux.weekly_comment, 0)

    @override_settings(PLATFORM_NAME='Test')
    @override_settings(LMS_ROOT_URL='https://test.ts')
    @patch('eol_forum_notifications.utils.course_image_url')
    @patch('eol_forum_notifications.utils.get_course_by_id')
    def test_send_notifications_daily_no_users(self, course_mock, image_mock):
        course_mock.side_effect = [namedtuple("Course", ["display_name_with_default", "end"])("this is a display name", None)]
        image_mock.return_value = '/assets/image.jpg'
        self.discussion.daily_threads = 3
        self.discussion.daily_comment = 3
        self.discussion.weekly_threads = 3
        self.discussion.weekly_comment = 3
        self.discussion.save()
        self.assertEqual(self.discussion.daily_threads, 3)
        self.assertEqual(self.discussion.daily_comment, 3)
        self.assertEqual(self.discussion.weekly_threads, 3)
        self.assertEqual(self.discussion.weekly_comment, 3)
        send_notification('daily')
        aux = EolForumNotificationsDiscussions.objects.get(id=self.discussion.id)
        self.assertEqual(aux.daily_threads, 0)
        self.assertEqual(aux.daily_comment, 0)
        self.assertEqual(aux.weekly_threads, 3)
        self.assertEqual(aux.weekly_comment, 3)