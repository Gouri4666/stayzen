from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.staff_login, name='staff_login'),
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('profile/', views.staff_profile, name='staff_profile'),
    path('attendance/check-in/', views.staff_check_in, name='staff_check_in'),
    path('attendance/check-out/', views.staff_check_out, name='staff_check_out'),
    path('admin/attendance/', views.admin_attendance_dashboard, name='admin_attendance_dashboard'),
    path('admin/attendance/shifts/', views.admin_shift_settings, name='admin_shift_settings'),
    path('admin/attendance/shifts/delete/<int:shift_id>/', views.delete_shift, name='delete_shift'),
    path('admin/attendance/shifts/edit/<int:shift_id>/', views.edit_shift, name='edit_shift'),
    path('calendar-dashboard/', views.calendar_dashboard_view, name='calendar_dashboard'),
    path('api/calendar/', views.calendar_api, name='calendar_api'),

    # Notification Center (staff-scoped wrappers around adminapp's views)
    path('api/notifications/list/', views.staff_api_get_notifications, name='staff_api_get_notifications'),
    path('api/notifications/read/<int:id>/', views.staff_api_mark_notification_read, name='staff_api_mark_notification_read'),
    path('api/notifications/delete/<int:id>/', views.staff_api_delete_notification, name='staff_api_delete_notification'),
    path('api/notifications/clear/', views.staff_api_clear_notifications, name='staff_api_clear_notifications'),
    path('api/notifications/sent/', views.staff_api_get_sent_notifications, name='staff_api_get_sent_notifications'),
    path('api/notifications/sent/delete/<int:id>/', views.staff_api_delete_sent_notification, name='staff_api_delete_sent_notification'),
    path('api/notifications/sent/clear/', views.staff_api_clear_sent_notifications, name='staff_api_clear_sent_notifications'),
    path('api/notifications/staff/', views.staff_api_active_staff, name='staff_api_active_staff'),
    path('api/notifications/compose/', views.staff_api_compose_notification, name='staff_api_compose_notification'),
]