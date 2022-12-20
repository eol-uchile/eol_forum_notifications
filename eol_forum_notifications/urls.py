

from django.conf.urls import url
from django.conf import settings

from .views import save_notification

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

urlpatterns = (
    url(
        r'^save',
        login_required(save_notification),
        name='save',
    ),
)
