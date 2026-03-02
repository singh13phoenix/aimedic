from .models import Notification

def portal_counts(request):
    if not request.user.is_authenticated:
        return {}
    return {"unread_notifications": Notification.objects.filter(account=request.user, is_read=False).count()}
