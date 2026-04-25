from .models import Notification, VaccineRequest
def notifications_processor(request):
    if not request.user.is_authenticated:
        return {
            'unread_notif_count': 0,
            'latest_notifications': [],
            'pending_request_count': 0,
            'area_pending_count': 0,
        }
    # Unread notification count
    unread_notif_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()
    # Latest 5 notifications (dropdown এ দেখাবে)
    latest_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    # User এর pending vaccine requests
    pending_request_count = VaccineRequest.objects.filter(
        user=request.user, status='Pending'
    ).count()
    # Admin এর area-based pending requests
    area_pending_count = 0
    if request.user.is_staff or request.user.is_superuser:
        if request.user.is_superuser:
            area_pending_count = VaccineRequest.objects.filter(status='Pending').count()
        else:
            area_pending_count = VaccineRequest.objects.filter(
                assigned_admin=request.user, status='Pending'
            ).count()
    return {
        'unread_notif_count':    unread_notif_count,
        'latest_notifications':  latest_notifications,
        'pending_request_count': pending_request_count,
        'area_pending_count':    area_pending_count,
    }
