from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, Resolver404
from staffapp.models import SubMenu, MenuPermission
from adminapp.models import StaffUser

URL_PERMISSION_MAP = {
    # ─── Rooms ───
    'room_list': ('room_list', 'view'),
    'add_room': ('room_list', 'add'),
    'edit_room': ('room_list', 'edit'),
    'delete_room': ('room_list', 'delete'),

    # ─── Event Halls ───
    'hall_list': ('hall_list', 'view'),
    'add_event_hall': ('hall_list', 'add'),
    'hall_edit': ('hall_list', 'edit'),
    'hall_delete': ('hall_list', 'delete'),

    # ─── Packages & Services ───
    'package_list': ('package_list', 'view'),
    'add_package': ('package_list', 'add'),
    'view_package': ('package_list', 'view'), 
    'package_add_service': ('package_list', 'add'),
    'package_edit_service': ('package_list', 'edit'),
    'package_delete_service': ('package_list', 'delete'),

    # ─── Food & Beverage ───
    'food_item_list': ('food_item_list', 'view'),
    'add_food_item': ('food_item_list', 'add'),
    'edit_food_item': ('food_item_list', 'edit'),
    'delete_food_item': ('food_item_list', 'delete'),
    
    # ─── Table Management ───
    'table_list': ('table_list', 'view'),
    'add_table': ('table_list', 'add'),
    'edit_table': ('table_list', 'edit'),
    'delete_table': ('table_list', 'delete'),

    # ─── Activities ───
    'activity_list': ('activity_list', 'view'),
    'add_activity': ('activity_list', 'add'),
    'view_activity': ('activity_list', 'view'),
    'edit_activity': ('activity_list', 'edit'),
    'delete_activity': ('activity_list', 'delete'),
    'add_session': ('activity_list', 'add'),
    'edit_session': ('activity_list', 'edit'),
    'delete_session': ('activity_list', 'delete'),

    # ─── Loyalty Rewards ───
    'loyalty_customer_list': ('loyalty_customer_list', 'view'),
    'edit_loyalty_points': ('loyalty_customer_list', 'edit'),
    'loyalty_transaction_list': ('loyalty_customer_list', 'view'),
    'customer_loyalty_transactions': ('loyalty_customer_list', 'view'),

    # ─── Bookings ───
    'receptionist_room_bookings': ('receptionist_room_bookings', 'view'),
    'receptionist_hall_bookings': ('receptionist_hall_bookings', 'view'),
    'receptionist_activity_bookings': ('receptionist_activity_bookings', 'view'),
    'receptionist_table_reservations': ('receptionist_table_reservations', 'view'),
    'receptionist_restaurant_orders': ('receptionist_restaurant_orders', 'view'),
    'receptionist_checkout_settlement': ('receptionist_checkout_settlement', 'view'),
    'process_room_checkout': ('receptionist_checkout_settlement', 'edit'),
    'process_event_checkout': ('receptionist_checkout_settlement', 'edit'),
    'receptionist_checkin': ('receptionist_checkin', 'view'),
    'process_room_checkin': ('receptionist_checkin', 'edit'),
    'process_event_checkin': ('receptionist_checkin', 'edit'),

    # ─── Offline Bookings ───
    'offline_booking': ('offline_booking', 'view'),
    'offline_restaurant_table': ('offline_restaurant_table', 'view'),
    'offline_event_booking': ('offline_event_booking', 'view'),
    'api_search_customer': ('offline_booking', 'view'),
    'api_available_rooms': ('offline_booking', 'view'),
    'api_available_halls': ('offline_booking', 'view'),
    'api_available_tables': ('offline_booking', 'view'),
    'api_freshup_available_rooms': ('offline_fresh_up_booking', 'view'),

    # ─── Notification ───
    'inbox': ('inbox', 'view'),
    'view_notification': ('inbox', 'view'),
    'mark_notification_read': ('inbox', 'edit'),
    'sent_notifications': ('sent_notifications', 'view'),
    'view_sent_notification': ('sent_notifications', 'view'),
    'compose_notification': ('compose_notification', 'add'),

    # ─── Reports & Analytics ───
    'reports_rooms': ('reports_overall', 'view'),
    'reports_events': ('reports_overall', 'view'),
    'reports_tables': ('reports_overall', 'view'),
    'reports_payments': ('reports_overall', 'view'),
    'reports_attendance': ('reports_overall', 'view'),
    'reports_financials': ('reports_overall', 'view'),
    'reports_section_detail': ('reports_overall', 'view'),
    'generate_advanced_pdf_report': ('reports_overall', 'view'),
    'generate_csv_report': ('reports_overall', 'view'),

    # ─── Home Deliveries (AJAX endpoints) ───
    'admin_home_deliveries': ('admin_home_deliveries', 'view'),
    'get_eligible_delivery_staff': ('admin_home_deliveries', 'view'),
    'assign_delivery_staff': ('admin_home_deliveries', 'edit'),
    'update_delivery_status': ('admin_home_deliveries', 'edit'),
}

class StaffPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        if path.startswith('/admin-panel/'):
            if path.rstrip('/').endswith('/logout'):
                return self.get_response(request)

            if not request.user.is_authenticated:
                messages.error(request, "Please log in to access the admin panel.")
                return redirect('staff_login')

            if request.user.is_superuser:
                return self.get_response(request)
            
            try:
                staff = StaffUser.objects.get(user=request.user, status=True)
            except StaffUser.DoesNotExist:
                messages.error(request, "Access denied. You do not have staff privileges.")
                return redirect('staff_login')
            
            try:
                resolver_match = resolve(path)
            except Resolver404:
                resolver_match = None

            if resolver_match and resolver_match.url_name:
                url_name = resolver_match.url_name
                
                # --- START: NOTIFICATION BYPASS ---
                # Allow all staff to access notification system by default
                notification_urls = [
                    'inbox', 'view_notification', 'mark_notification_read', 
                    'sent_notifications', 'view_sent_notification', 'compose_notification'
                ]
                if url_name in notification_urls:
                    return self.get_response(request)
                # --- END: NOTIFICATION BYPASS ---

                # --- START: DELIVERY AJAX BYPASS ---
                # These AJAX endpoints handle their own fine-grained auth internally.
                # Delivery staff have can_view on admin_home_deliveries — allow any
                # staff with that view permission to reach these endpoints.
                delivery_ajax_urls = [
                    'update_delivery_status', 'get_eligible_delivery_staff',
                    'assign_delivery_staff', 'staff_my_deliveries'
                ]
                if url_name in delivery_ajax_urls:
                    try:
                        submenus = SubMenu.objects.filter(url_name__in=['admin_home_deliveries', 'staff_my_deliveries'])
                        if MenuPermission.objects.filter(
                            user=request.user, submenu__in=submenus, can_view=True
                        ).exists():
                            return self.get_response(request)
                    except Exception:
                        pass
                # --- END: DELIVERY AJAX BYPASS ---

                # --- START: OFFLINE BOOKING DYNAMIC BYPASS FOR RECEPTIONIST/FRONT OFFICE ---
                offline_booking_urls = [
                    'offline_booking', 'offline_restaurant_table', 'offline_event_booking',
                    'offline_fresh_up_booking',
                    'api_search_customer', 'api_available_rooms', 'api_available_halls',
                    'api_available_tables', 'api_freshup_available_rooms'
                ]
                if url_name in offline_booking_urls:
                    if (staff.role and staff.role.name.lower() == 'receptionist') or (staff.department and staff.department.name.lower() == 'front office'):
                        return self.get_response(request)
                # --- END: OFFLINE BOOKING DYNAMIC BYPASS ---

                # Offline Booking APIs are now governed by URL_PERMISSION_MAP and the database
                
                if url_name == 'admin_dashboard':
                    return self.get_response(request)
                
                is_valid_submenu = SubMenu.objects.filter(url_name=url_name).exists()
                
                if is_valid_submenu or url_name in URL_PERMISSION_MAP:
                    has_perm = False
                    action = 'view'
                    
                    if is_valid_submenu:
                        try:
                            direct_perm = MenuPermission.objects.get(
                                user=request.user, submenu__url_name=url_name
                            )
                            if direct_perm.can_view:
                                has_perm = True
                        except MenuPermission.DoesNotExist:
                            pass
                    
                    if not has_perm and url_name in URL_PERMISSION_MAP:
                        submenu_url_name, action = URL_PERMISSION_MAP[url_name]
                        
                        if url_name == 'view_package' and request.method == 'POST':
                            if request.POST.get('action') == 'delete':
                                action = 'delete'
                            else:
                                action = 'edit'
                        
                        try:
                            perm = MenuPermission.objects.get(
                                user=request.user, submenu__url_name=submenu_url_name
                            )
                            if (action == 'view' and perm.can_view) or \
                               (action == 'add' and perm.can_add) or \
                               (action == 'edit' and perm.can_edit) or \
                               (action == 'delete' and perm.can_delete):
                                has_perm = True
                        except MenuPermission.DoesNotExist:
                            pass
                    
                    if has_perm:
                        return self.get_response(request)
                    
                    messages.error(request, f"You do not have permission to {action} in this section.")
                    return redirect('staff_dashboard')
                
                else:
                    messages.error(request, "Access denied. Administrator privileges required.")
                    return redirect('staff_dashboard')
                    
        return self.get_response(request)

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response

class UserDashboardRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        user = request.user
        if user.is_authenticated:
            is_staff_user = user.is_staff or user.is_superuser
            if not is_staff_user:
                try:
                    is_staff_user = StaffUser.objects.filter(user=user, status=True).exists()
                except:
                    is_staff_user = False
            if is_staff_user:
                if (path.startswith('/accounts/dashboard/') or path.startswith('/booking/')) and \
                   not path.startswith('/booking/razorpay-callback/') and \
                   not path.startswith('/booking/invoice/download/') and \
                   not path.startswith('/booking/orders/toggle-serving-status/') and \
                   not path.startswith('/booking/booked-dates/'):
                    if user.is_superuser:
                        return redirect('admin_dashboard')
                    else:
                        return redirect('staff_dashboard')
            else:
                if path.startswith('/admin-panel/') or (path.startswith('/staff/') and path != '/staff/login/'):
                    return redirect('dashboard')
        return self.get_response(request)