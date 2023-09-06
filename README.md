# Eol Forum Notifications

![https://github.com/eol-uchile/eol_forum_notifications/actions](https://github.com/eol-uchile/eol_forum_notifications/workflows/Python%20application/badge.svg)


# Install App

    docker-compose exec lms pip install -e /openedx/requirements/eol_forum_notifications
    docker-compose exec lms_worker pip install -e /openedx/requirements/eol_forum_notifications
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations eol_forum_notifications
    docker-compose exec lms python manage.py lms --settings=prod.production migrate eol_forum_notifications


# Commands

    > docker-compose exec lms python manage.py lms --settings=prod.production discussion_notification daily
    > docker-compose exec lms python manage.py lms --settings=prod.production discussion_notification weekly


# Install

- Edit the following file and add following code _/openedx/edx-platform/lms/djangoapps/discussion/signals/handlers.py_

        @receiver(signals.comment_created)
        def send_discussion_email_notification(sender, user, post, **kwargs):
            with transaction.atomic():
                try:
                    from eol_forum_notifications.models import EolForumNotificationsDiscussions
                    discussion = EolForumNotificationsDiscussions.objects.get(discussion_id=post.thread.commentable_id, course_id=post.thread.course_id)
                    discussion.daily_comment += 1
                    discussion.weekly_comment += 1
                    discussion.save()
                except Exception as e:
                    log.info("EolForumNotifications - Error to increment comment count. discussion_id: {}, course: {}, error: {}".format(
                        post.thread.commentable_id,
                        post.thread.course_id,
                        str(e)))
           
                return

        @receiver(signals.thread_created)
        def eol_thread_created(sender, user, post, **kwargs):
            with transaction.atomic():
                try:
                    from eol_forum_notifications.models import EolForumNotificationsDiscussions
                    discussion = EolForumNotificationsDiscussions.objects.get(discussion_id=post.commentable_id, course_id=post.course_id)
                    discussion.daily_threads += 1
                    discussion.weekly_threads += 1
                    discussion.save()
                except Exception as e:
                    log.info("EolForumNotifications - Error to increment comment count. discussion_id: {}, course: {}, error: {}".format(
                        post.commentable_id,
                        post.course_id,
                        str(e)))
            return

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/eol_forum_notifications/.github/test.sh
