from .models import Notification


def unread_notifications(request):
    """
    সব template এ unread_notif_count এবং latest_notifications inject করে।
    Navbar এর notification bell এর জন্য।
    """
    if request.user.is_authenticated:
        qs = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notif_count':    qs.count(),
            'latest_notifications':  qs.order_by('-created_at')[:5],
        }
    return {
        'unread_notif_count':   0,
        'latest_notifications': [],
    }