#!/bin/dash

pip install -e /openedx/requirements/eol_forum_notifications

cd /openedx/requirements/eol_forum_notifications
cp /openedx/edx-platform/setup.cfg .
mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .

cd /openedx/requirements/eol_forum_notifications

DJANGO_SETTINGS_MODULE=lms.envs.test EDXAPP_TEST_MONGO_HOST=mongodb pytest eol_forum_notifications/tests.py
