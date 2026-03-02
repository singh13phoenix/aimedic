from django.utils import timezone
from .models import Notification

def notify(account, title, message, link_type="", link_id=None):
    Notification.objects.create(
        account=account,
        title=title,
        message=message,
        link_type=link_type,
        link_id=link_id,
        created_at=timezone.now(),
    )
