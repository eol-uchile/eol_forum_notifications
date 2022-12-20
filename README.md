# Eol User Data

![https://github.com/eol-uchile/eol_forum_notifications/actions](https://github.com/eol-uchile/eol_forum_notifications/workflows/Python%20application/badge.svg)


# Install App

    docker-compose exec lms pip install -e /openedx/requirements/eol_forum_notifications
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations eol_forum_notifications
    docker-compose exec lms python manage.py lms --settings=prod.production migrate

try:
    from eol_forum_notifications.views import send_notification_always_comment, send_notification_always_thread
    from eol_forum_notifications.models import EolForumNotifications
    EOL_NOTIFICATION_ENABLED = True
except ImportError:
    EOL_NOTIFICATION_ENABLED = False

@receiver(signals.comment_created)
def send_discussion_email_notification(sender, user, post, **kwargs):
    if EOL_NOTIFICATION_ENABLED and EolForumNotifications.objects.filter(discussion_id=post.thread.commentable_id).exists():
        send_notification_always_comment(post, user)
    else:
        current_site = get_current_site()
        if current_site is None:
            log.info(u'Discussion: No current site, not sending notification about post: %s.', post.id)
            return

        try:
            if not current_site.configuration.get_value(ENABLE_FORUM_NOTIFICATIONS_FOR_SITE_KEY, False):
                log_message = u'Discussion: notifications not enabled for site: %s. Not sending message about post: %s.'
                log.info(log_message, current_site, post.id)
                return
        except SiteConfiguration.DoesNotExist:
            log_message = u'Discussion: No SiteConfiguration for site %s. Not sending message about post: %s.'
            log.info(log_message, current_site, post.id)
            return

        send_message(post, current_site)
    return

@receiver(signals.thread_created)
def eol_send_thread_created(sender, user, post, **kwargs):
    if EOL_NOTIFICATION_ENABLED:
        send_notification_always_thread(post, user)
    return

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/eol_forum_notifications/.github/test.sh
