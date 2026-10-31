from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from bookingapp import views as booking_views
def _lr(view):
    return login_required(view, login_url='/staff/login/')


urlpatterns = [
    path('', _lr(views.admin_dashboard), name='admin_dashboard'),
    path('profile/', _lr(views.admin_profile), name='admin_profile'),
    path('add-room/', _lr(views.add_room), name='add_room'),    
    path('room-list/', _lr(views.room_list), name='room_list'),
    path('edit-room/<int:id>/', _lr(views.edit_room), name='edit_room'),
    path('delete-room/<int:id>/', _lr(views.delete_room), name='delete_room'),
    path('restore-room/<int:id>/', _lr(views.restore_room), name='restore_room'),
    path("validate-unique-item/",views.validate_unique_item,name="validate_unique_item"),
    path('add-event-hall/',_lr(views.add_event_hall),name='add_event_hall'),

    path('edit-event-hall/<int:id>/',_lr(views.edit_event_hall),name='hall_edit'),
    path('hall-list/', _lr(views.hall_list), name='hall_list'),
    #path('hall-edit/<int:id>/', _lr(views.hall_edit), name='hall_edit'),
    path('hall-delete/<int:id>/', _lr(views.hall_delete), name='hall_delete'),
    path('hall-restore/<int:id>/', _lr(views.restore_event_hall), name='restore_event_hall'),


    
    path('packages/', _lr(views.package_list), name='package_list'),
    path('add-package/', _lr(views.add_package), name='add_package'),
    # Single package view handles edit/update/delete (no separate edit/delete pages)
    path('package/<int:id>/', _lr(views.view_package), name='view_package'),
    path('package/<int:id>/restore/', _lr(views.restore_package), name='restore_package'),
    #services
    # Service management (package-scoped endpoints only)
    path('package/<int:package_id>/service/add/', _lr(views.add_service), name='package_add_service'),
    path('package/<int:package_id>/service/<int:id>/edit/', _lr(views.edit_service), name='package_edit_service'),
    path('package/<int:package_id>/service/<int:id>/delete/', _lr(views.delete_service), name='package_delete_service'),
    path('package/<int:package_id>/service/<int:id>/restore/', _lr(views.restore_service), name='package_restore_service'),

    # food items
    path('add-food-item/', _lr(views.add_food_item), name='add_food_item'),
    path('food-item-list/', _lr(views.food_item_list), name='food_item_list'),
    path('edit-food-item/<int:id>/', _lr(views.edit_food_item), name='edit_food_item'),
    path('delete-food-item/<int:id>/', _lr(views.delete_food_item), name='delete_food_item'),
    path('restore-food-item/<int:id>/', _lr(views.restore_food_item), name='restore_food_item'),
    
    #activity
    path('add-activity/', _lr(views.add_activity), name='add_activity'),
    path('activity-list/', _lr(views.activity_list), name='activity_list'),
    path('activity/<int:id>/', _lr(views.view_activity), name='view_activity'),
    path('activity/<int:activity_id>/add-session/', _lr(views.add_session), name='add_session'),
    path('session/<int:id>/edit/', _lr(views.edit_session), name='edit_session'),
    path('session/<int:id>/delete/', _lr(views.delete_session), name='delete_session'),
    path('session/<int:id>/restore/', _lr(views.restore_session), name='restore_session'),
    path('edit-activity/<int:id>/', _lr(views.edit_activity), name='edit_activity'),
    path('delete-activity/<int:id>/', _lr(views.delete_activity), name='delete_activity'),
    path('restore-activity/<int:id>/', _lr(views.restore_activity), name='restore_activity'),

    #table management
    path('table-list/', _lr(views.table_list), name='table_list'),
    path('add-table/', _lr(views.add_table), name='add_table'),
    path('edit-table/<int:id>/', _lr(views.edit_table), name='edit_table'),
    path('delete-table/<int:id>/', _lr(views.delete_table), name='delete_table'), 
    path('restore-table/<int:id>/', _lr(views.restore_table), name='restore_table'),

    # loyalty rewards
    path('loyalty/customers/', _lr(views.loyalty_customer_list), name='loyalty_customer_list'),
    path('loyalty/customer/<int:id>/edit/', _lr(views.edit_loyalty_points), name='edit_loyalty_points'),
    path('loyalty/transactions/', _lr(views.loyalty_transaction_list), name='loyalty_transaction_list'),
    path('loyalty/customer/<int:id>/transactions/', _lr(views.customer_loyalty_transactions), name='customer_loyalty_transactions'),

    #user access
    path('add-staff-user/', _lr(views.add_staff_user), name='add_staff_user'),
    path('staff-user-list/', _lr(views.staff_user_list), name='staff_user_list'),
    path('delete-staff-user/<int:id>/', _lr(views.delete_staff_user), name='delete_staff_user'),
    path('restore-staff-user/<int:id>/', _lr(views.restore_staff_user), name='restore_staff_user'),
    path('edit-staff-user/<int:id>/', _lr(views.edit_staff_user), name='edit_staff_user'),
    path('staff/<int:id>/permissions/', _lr(views.manage_permissions), name='manage_permissions'),
    path('menus/',_lr(views.menu_list),name='menu_list'),
    path('menus/add/',_lr(views.add_menu),name='add_menu'),
    path('submenus/',_lr(views.submenu_list),name='submenu_list'),
    path('submenus/add/',_lr(views.add_submenu),name='add_submenu'),
    path('menu/delete/<int:id>/', _lr(views.delete_menu), name='delete_menu'),
    path('submenu/delete/<int:id>/', _lr(views.delete_submenu), name='delete_submenu'),
    

    # Receptionist Bookings
    path('bookings/rooms/', _lr(booking_views.receptionist_room_bookings), name='receptionist_room_bookings'),
    path('bookings/halls/', _lr(booking_views.receptionist_hall_bookings), name='receptionist_hall_bookings'),
    path('bookings/activities/', _lr(booking_views.receptionist_activity_bookings), name='receptionist_activity_bookings'),
    path('bookings/tables/', _lr(booking_views.receptionist_table_reservations), name='receptionist_table_reservations'),
    path('bookings/orders/', _lr(booking_views.receptionist_restaurant_orders), name='receptionist_restaurant_orders'),
    path('bookings/checkout-settlement/', _lr(booking_views.receptionist_checkout_settlement), name='receptionist_checkout_settlement'),
    path('bookings/rooms/checkout/<int:booking_id>/', _lr(booking_views.process_room_checkout), name='process_room_checkout'),
    path('bookings/halls/checkout/<int:booking_id>/', _lr(booking_views.process_event_checkout), name='process_event_checkout'),
    path('bookings/checkin/', _lr(booking_views.receptionist_checkin), name='receptionist_checkin'),
    path('bookings/rooms/checkin/<int:booking_id>/', _lr(booking_views.process_room_checkin), name='process_room_checkin'),
    path('bookings/halls/checkin/<int:booking_id>/', _lr(booking_views.process_event_checkin), name='process_event_checkin'),
    path('api/room-status/', views.api_room_calendar_status, name='api_room_calendar_status'),
    # Offline Bookings
    path('offline-booking/', _lr(booking_views.offline_booking), name='offline_booking'),
    path('offline-event-booking/', _lr(booking_views.offline_event_booking), name='offline_event_booking'),
    path('offline-fresh-up-booking/', _lr(booking_views.offline_fresh_up_booking), name='offline_fresh_up_booking'),
    path('offline-restaurant-table/', _lr(booking_views.offline_restaurant_table), name='offline_restaurant_table'),
    path('api/search-customer/', _lr(booking_views.api_search_customer), name='api_search_customer'),
    path('api/check-guest-email/', _lr(booking_views.api_check_guest_email), name='api_check_guest_email'),
    path('api/available-rooms/', _lr(booking_views.api_available_rooms), name='api_available_rooms'),
    path('api/available-halls/', _lr(booking_views.api_available_halls), name='api_available_halls'),
    path('api/available-tables/', _lr(booking_views.api_available_tables), name='api_available_tables'),

    #Notification
    path('notifications/compose/', _lr(views.compose_notification), name='compose_notification'),
    path('notifications/inbox/', _lr(views.inbox), name='inbox'),
    path('notifications/read/<int:id>/', _lr(views.mark_notification_read), name='mark_notification_read'),
    path('notifications/view/<int:id>/', _lr(views.view_notification), name='view_notification'),
    path('notifications/sent/', _lr(views.sent_notifications), name='sent_notifications'),
    path('notifications/sent/view/<int:id>/', _lr(views.view_sent_notification), name='view_sent_notification'),
    
    # API endpoints for notification dropdown & popup
    path('api/notifications/staff/', _lr(views.api_active_staff), name='api_active_staff'),
    path('api/notifications/compose/', _lr(views.api_compose_notification), name='api_compose_notification'),
    path('api/notifications/read/<int:id>/', _lr(views.api_mark_notification_read), name='api_mark_notification_read'),
    path('api/notifications/list/', _lr(views.api_get_notifications), name='api_get_notifications'),
    path('api/notifications/sent/', _lr(views.api_get_sent_notifications), name='api_get_sent_notifications'),
    path('api/notifications/sent/delete/<int:id>/', _lr(views.api_delete_sent_notification), name='api_delete_sent_notification'),
    path('api/notifications/sent/clear/', _lr(views.api_clear_sent_notifications), name='api_clear_sent_notifications'),
    path('api/notifications/delete/<int:id>/', _lr(views.api_delete_notification), name='api_delete_notification'),
    path('api/notifications/clear/', _lr(views.api_clear_notifications), name='api_clear_notifications'),

    # Operational Management Reports & Analytics Endpoints
    # Operational Management Reports & Analytics Endpoints
    # path('reports/', _lr(views.reports_dashboard), name='reports_dashboard'),
    # path('reports/pdf-summary/', _lr(views.generate_hotel_pdf_report), name='generate_hotel_pdf_report'),
    # path('reports/export/<str:report_type>/', _lr(views.generate_csv_report), name='generate_csv_report'), # <-- ADD THIS LINE

    # # High-fidelity Visual Reporting Suite Routing
    # # path('analytics/', _lr(views.reports_overall_dashboard), name='reports_overall'),
    # # path('analytics/section/<str:section_name>/', _lr(views.reports_section_detail), name='reports_section_detail'),

    # path('analytics/download-pdf/', _lr(views.generate_advanced_pdf_report), name='generate_advanced_pdf_report'),
    # path('reports/dashboard/', _lr(views.reports_overall_dashboard), name='reports_overall'),
    # path('reports/dashboard/section/<str:section_name>/', _lr(views.reports_section_detail), name='reports_section_detail'),
    # path('reports/dashboard/rooms/', _lr(views.reports_rooms), name='reports_rooms'),
    # path('reports/dashboard/events/', _lr(views.reports_events), name='reports_events'),
    # path('reports/dashboard/tables/', _lr(views.reports_tables), name='reports_tables'),
    # path('reports/dashboard/payments/', _lr(views.reports_payments), name='reports_payments'),
    # path('reports/dashboard/attendance/', _lr(views.reports_attendance), name='reports_attendance'),
    # path('reports/dashboard/financials/', _lr(views.reports_financials), name='reports_financials'),


    # path('reports/tables/graph-data/', views.table_reservation_graph_data, name='table_graph_data'),
    # ==========================================
    # High-Fidelity Visual Reporting Suite Routing
    # ==========================================
    path('reports/', _lr(views.reports_overall_dashboard), name='reports_overall'),
    
    # Export Engines (PDF & CSV)
    path('reports/download-pdf/', _lr(views.generate_advanced_pdf_report), name='generate_advanced_pdf_report'),
    path('reports/export-csv/<str:report_type>/', _lr(views.generate_csv_report), name='generate_csv_report'),
    
    # Catch-all for dynamic sections (Handles the 404 error)
    path('reports/dashboard/<str:section_name>/', _lr(views.reports_section_detail), name='reports_section_detail'),
    
    # Explicit shortcuts used by the main dashboard UI
    path('reports/', _lr(views.reports_overall_dashboard), name='reports_overall'),
    
    # Export Engines (PDF & CSV)
    path('reports/download-pdf/', _lr(views.generate_advanced_pdf_report), name='generate_advanced_pdf_report'),
    path('reports/export-csv/<str:report_type>/', _lr(views.generate_csv_report), name='generate_csv_report'),
    
    # Catch-all for dynamic sections (Handles the 404 error)
    path('reports/dashboard/<str:section_name>/', _lr(views.reports_section_detail), name='reports_section_detail'),
    
    # Explicit shortcuts used by the main dashboard UI
    path('reports/detail/rooms/', _lr(views.reports_rooms), name='reports_rooms'),
    path('reports/detail/events/', _lr(views.reports_events), name='reports_events'),
    path('reports/detail/tables/', _lr(views.reports_tables), name='reports_tables'),
    path('reports/detail/payments/', _lr(views.reports_payments), name='reports_payments'),
    path('reports/detail/attendance/', _lr(views.reports_attendance), name='reports_attendance'),
    path('reports/detail/financials/', _lr(views.reports_financials), name='reports_financials'),
    
    path('export/pdf/', views.generate_advanced_pdf_report, name='export_report_pdf'),
    path('export/csv/<str:report_type>/', views.generate_csv_report, name='export_report_csv'),
    
    # Shortcuts
    path('detail/rooms/', views.reports_rooms, name='reports_rooms'),
    path('detail/events/', views.reports_events, name='reports_events'),
    path('detail/tables/', views.reports_tables, name='reports_tables'),
    path('detail/dining/', views.reports_dining, name='reports_dining'),
    path('detail/activities/', views.reports_activities, name='reports_activities'),
    path('detail/packages/', views.reports_packages, name='reports_packages'),
    path('detail/customers/', views.reports_customers, name='reports_customers'),
    path('detail/payments/', views.reports_payments, name='reports_payments'),
    path('detail/attendance/', views.reports_attendance, name='reports_attendance'),
    path('detail/financials/', views.reports_financials, name='reports_financials'),
    path('detail/bi/', views.reports_bi, name='reports_bi'),
    path('detail/<str:section_name>/', views.reports_section_detail, name='reports_section_detail'),
    

    path('feedback-list/', views.admin_feedback_view, name='admin_feedback_list'),
    path('feedback/delete/<int:id>/', views.delete_feedback, name='delete_feedback'),
    # Staff Registration (Admin-only)
    path('staff-registration/', _lr(views.staff_registration), name='staff_registration'),
    path('staff-registration-list/', _lr(views.staff_registration_list), name='staff_registration_list'),
    path('staff-registration/delete/<int:id>/', _lr(views.delete_registered_user), name='delete_registered_user'),
    path('staff-registration/restore/<int:id>/', _lr(views.restore_registered_user), name='restore_registered_user'),
    
    # Dynamic Masters Management (Departments and Roles)
    path('masters/manage/', _lr(views.manage_masters), name='manage_masters'),
    path('masters/departments/delete/<int:id>/', _lr(views.department_delete), name='department_delete'),
    path('masters/roles/delete/<int:id>/', _lr(views.role_delete), name='role_delete'),

    path('api/get-staff-details/<int:user_id>/', _lr(views.get_staff_details), name='get_staff_details'),
    
    #site settings
    path('settings/', views.site_settings_view, name='site_settings'),
    path('cancellations/', views.manage_cancellations, name='admin_manage_cancellations'),
    path('cancellations/update/<str:token>/', views.update_refund_status, name='admin_update_refund'),
    
    # Home Deliveries
    path('bookings/home-deliveries/', _lr(views.home_deliveries_view), name='admin_home_deliveries'),
    path('bookings/home-deliveries/eligible-staff/', _lr(views.get_eligible_delivery_staff), name='get_eligible_delivery_staff'),
    path('bookings/home-deliveries/<int:order_id>/assign/', _lr(views.assign_delivery_staff), name='assign_delivery_staff'),
    path('bookings/home-deliveries/<int:order_id>/update-status/', _lr(views.update_delivery_status), name='update_delivery_status'),
    path('bookings/my-deliveries/', _lr(views.staff_my_deliveries), name='staff_my_deliveries'),
]