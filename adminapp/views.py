from asyncio import base_events
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
import json
import re
from .models import Room, event_hall, Service, Package, FoodItem, Activity, ActivitySession,StaffUser,NotificationStatus,NotificationBroadcast,RegisteredUser,Department,Role
from django.db.models import Q,Count
from .forms import (
    RoomForm,
    ServiceForm,
    PackageForm,
    FoodItemForm,
    ActivitySessionForm,
    EventHallForm,
    ActivityForm,
    StaffUserForm,
    NotificationForm,
    RegisteredUserForm
)
from staffapp.models import Menu, MenuPermission
from adminapp.models import StaffUser
from django.contrib import messages
from django.http import JsonResponse
from accountapp.models import Customer
from bookingapp.models import LoyaltyTransaction
from staffapp.models import Menu, SubMenu, MenuPermission
from staffapp.forms import MenuForm, SubMenuForm
from staffapp.forms_profile import StaffProfileForm
from django.contrib.auth.decorators import login_required
# def admin_dashboard(request):
#     return render(request, 'admin/index.html')


@login_required
def admin_dashboard(request):
    """
    Renders the comprehensive management analytics panel as the default dashboard.
    Forwards to reports_overall_dashboard to reuse the unified reporting logic.
    """
    return reports_overall_dashboard(request)

# @login_required
# def admin_dashboard(request):
#     """
#     Renders the comprehensive management analytics panel as the default dashboard.
#     """
#     start_date, end_date, start_datetime, end_datetime, time_filter = _get_report_dates(request)

#     # Revenue aggregations for current period
#     room_data = RoomBooking.objects.filter(check_in__gte=start_date, check_in__lte=end_date).exclude(status__in=['Pending', 'Cancelled']).aggregate(total=Count('id'), rev=Sum('final_amount'))
#     event_data = EventBooking.objects.filter(start_date__gte=start_date, start_date__lte=end_date).exclude(status__in=['Pending', 'Cancelled']).aggregate(total=Count('id'), rev=Sum('final_amount'))
#     order_data = Order.objects.filter(order_date__gte=start_datetime, order_date__lte=end_datetime).exclude(status__in=['Pending', 'Cancelled']).aggregate(total=Count('id'), rev=Sum('total_amount'))
#     table_data = TableReservation.objects.filter(reservation_date__gte=start_date, reservation_date__lte=end_date).exclude(status='Cancelled').aggregate(total=Count('id'), rev=Sum('advance_amount'))

#     # Current Revenues
#     room_rev = room_data['rev'] or Decimal('0.00')
#     event_rev = event_data['rev'] or Decimal('0.00')
#     food_rev = order_data['rev'] or Decimal('0.00')
#     table_rev = table_data['rev'] or Decimal('0.00')
#     total_revenue = room_rev + event_rev + food_rev + table_rev
#     total_profit = (room_rev * Decimal('0.85')) + (event_rev * Decimal('0.60')) + (food_rev * Decimal('0.40')) + (table_rev * Decimal('0.90'))

#     # Calculate previous period dates for trend comparison
#     time_delta = end_datetime - start_datetime
#     prev_start_datetime = start_datetime - time_delta
#     prev_start_date = prev_start_datetime.date()
    
#     prev_room_rev = RoomBooking.objects.filter(check_in__gte=prev_start_date, check_in__lt=start_date).exclude(status__in=['Pending', 'Cancelled']).aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
#     prev_event_rev = EventBooking.objects.filter(start_date__gte=prev_start_date, start_date__lt=start_date).exclude(status__in=['Pending', 'Cancelled']).aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
#     prev_order_rev = Order.objects.filter(order_date__gte=prev_start_datetime, order_date__lt=start_datetime).exclude(status__in=['Pending', 'Cancelled']).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
#     prev_table_rev = TableReservation.objects.filter(reservation_date__gte=prev_start_date, reservation_date__lt=start_date).exclude(status='Cancelled').aggregate(Sum('advance_amount'))['advance_amount__sum'] or Decimal('0.00')
    
#     prev_total_revenue = prev_room_rev + prev_event_rev + prev_order_rev + prev_table_rev

#     # Trend calculation (Percentage change)
#     if prev_total_revenue > 0:
#         revenue_trend_pct = ((total_revenue - prev_total_revenue) / prev_total_revenue) * 100
#     else:
#         revenue_trend_pct = 100 if total_revenue > 0 else 0
    
#     revenue_is_decreasing = revenue_trend_pct < 0

#     # Occupancy & Attendance
#     total_rooms = Room.objects.count() or 1
#     total_days = max((end_date - start_date).days, 1)
#     total_capacity = total_rooms * total_days
#     total_booked_nights = sum(
#         max(1, (min(rb.check_out, end_date) - max(rb.check_in, start_date)).days)
#         for rb in RoomBooking.objects.filter(check_in__lte=end_date, check_out__gte=start_date, status__in=['Confirmed', 'Checked In', 'Completed'])
#     )
#     occupancy_rate = min(100.0, (total_booked_nights / total_capacity) * 100.0) if total_capacity > 0 else 0.0

#     attendance_records = Attendance.objects.filter(date__gte=start_date, date__lte=end_date)
#     total_attendance = attendance_records.count()
#     present_attendance = attendance_records.filter(status__in=['Present', 'Late', 'Half Day', 'Checked Out']).count()
#     attendance_rate = (present_attendance / total_attendance * 100) if total_attendance > 0 else 100.0

#     from accountapp.models import Customer
#     total_guests = Customer.objects.count()

#     total_room_bookings = room_data['total'] or 0
#     total_restaurant_orders = order_data['total'] or 0
#     total_event_bookings = event_data['total'] or 0
#     total_tables = table_data['total'] or 0

#     # =========================================================================
#     # MULTI-LINE GRAPH INJECTION (Fixes the blank chart on /admin-panel/)
#     # =========================================================================
#     room_trend = RoomBooking.objects.filter(check_in__gte=start_date, check_in__lte=end_date)\
#         .exclude(status__in=['Pending', 'Cancelled']).values('check_in').annotate(rev=Sum('final_amount')).order_by('check_in')
        
#     event_trend = EventBooking.objects.filter(start_date__gte=start_date, start_date__lte=end_date)\
#         .exclude(status__in=['Pending', 'Cancelled']).values('start_date').annotate(rev=Sum('final_amount')).order_by('start_date')
        
#     food_trend = Order.objects.filter(order_date__gte=start_datetime, order_date__lte=end_datetime)\
#         .exclude(status__in=['Pending', 'Cancelled']).annotate(date=TruncDate('order_date')).values('date').annotate(rev=Sum('total_amount')).order_by('date')
        
#     table_trend = TableReservation.objects.filter(reservation_date__gte=start_date, reservation_date__lte=end_date)\
#         .exclude(status='Cancelled').values('reservation_date').annotate(rev=Sum('advance_amount')).order_by('reservation_date')

#     all_dates = set()
#     for item in room_trend:
#         if item['check_in']: all_dates.add(str(item['check_in']))
#     for item in event_trend:
#         if item['start_date']: all_dates.add(str(item['start_date']))
#     for item in food_trend:
#         if item['date']: all_dates.add(str(item['date']))
#     for item in table_trend:
#         if item['reservation_date']: all_dates.add(str(item['reservation_date']))
    
#     sorted_dates = sorted(list(all_dates))

#     room_map = {str(item['check_in']): float(item['rev'] or 0) for item in room_trend if item['check_in']}
#     event_map = {str(item['start_date']): float(item['rev'] or 0) for item in event_trend if item['start_date']}
#     food_map = {str(item['date']): float(item['rev'] or 0) for item in food_trend if item['date']}
#     table_map = {str(item['reservation_date']): float(item['rev'] or 0) for item in table_trend if item['reservation_date']}

#     # =========================================================================

#     context = {
#         'start_date': start_date, 'end_date': end_date,
#         'time_filter': time_filter,
#         'total_reservations': total_room_bookings,
#         'total_revenue': total_revenue,
#         'revenue_trend_pct': round(revenue_trend_pct, 2),
#         'revenue_is_decreasing': revenue_is_decreasing,
#         'room_revenue': room_rev,
#         'food_revenue': food_rev,
#         'event_revenue': event_rev,
#         'table_revenue': table_rev,
#         'occupancy_rate': round(occupancy_rate, 2),
#         'attendance_rate': round(attendance_rate, 2),
#         'total_guests': total_guests,
#         'total_profit': total_profit,
#         'total_events': total_event_bookings,
#         'total_tables': total_tables,
#         'total_room_bookings': total_room_bookings,
#         'total_restaurant_orders': total_restaurant_orders,
#         'total_event_bookings': total_event_bookings,
        
#         # Pass the graph arrays to the template!
#         'chart_labels_json': json.dumps(sorted_dates),
#         'room_trend_json': json.dumps([room_map.get(d, 0.0) for d in sorted_dates]),
#         'event_trend_json': json.dumps([event_map.get(d, 0.0) for d in sorted_dates]),
#         'food_trend_json': json.dumps([food_map.get(d, 0.0) for d in sorted_dates]),
#         'table_trend_json': json.dumps([table_map.get(d, 0.0) for d in sorted_dates]),
#     }
    
#     return render(request, 'admin/reports_overall.html', context)
@login_required(login_url='/staff/login/')
def admin_profile(request):
    """
    Render and process the shared profile form for Admin users.
    Uses the same StaffUser model and StaffProfileForm as staff_profile.
    """
    staff, _ = StaffUser.objects.get_or_create(
        user=request.user,
        defaults={'status': True}
    )
    if request.method == 'POST':
        action = request.POST.get('action')

        # --- Password Change ---
        if action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif not new_password:
                messages.error(request, "New password cannot be empty.")
            elif len(new_password) < 8:
                messages.error(request, "New password must be at least 8 characters long.")
            elif new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password changed successfully!")

            form = StaffProfileForm(instance=staff, user=request.user)
            return render(request, 'staff/profile.html', {'form': form, 'staff': staff})

        # --- Profile Update ---
        form = StaffProfileForm(
            request.POST,
            request.FILES,
            instance=staff,
            user=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('admin_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = StaffProfileForm(instance=staff, user=request.user)

    return render(request, 'staff/profile.html', {'form': form, 'staff': staff})


def add_room(request):

    if request.method == 'POST':

        form = RoomForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            room.save()
            form.save_m2m()
            messages.success(request, "Room added successfully!")
            return redirect('room_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = RoomForm()
    return render(
        request,
        'admin/add_room.html',
        {'form': form}
    )

def validate_unique_item(request):
    item_type = request.GET.get("item_type")
    value = request.GET.get("value", "").strip()

    exists = False

    if item_type == "room":
        exists = Room.objects.filter(room_number__iexact=value).exists()

    elif item_type == "event":
        exists = event_hall.objects.filter(hall_name__iexact=value).exists()

    elif item_type == "table":
        exists = RestaurantTable.objects.filter(table_number__iexact=value).exists()

    elif item_type == "package":
        exists = Package.objects.filter(package_name__iexact=value).exists()

    elif item_type == "food":
        exists = FoodItem.objects.filter(item_name__iexact=value).exists()

    elif item_type == "staff_username":
        from django.contrib.auth.models import User
        exists = RegisteredUser.objects.filter(username__iexact=value).exists() or User.objects.filter(username__iexact=value).exists()

    elif item_type == "staff_email":
        from django.contrib.auth.models import User
        exists = RegisteredUser.objects.filter(email__iexact=value).exists() or User.objects.filter(email__iexact=value).exists()
        
    elif item_type == "staff_phone":
        from accountapp.models import Customer
        exists = RegisteredUser.objects.filter(phone__iexact=value).exists() or StaffUser.objects.filter(phone__iexact=value).exists() or Customer.objects.filter(phone__iexact=value).exists()

    return JsonResponse({"exists": exists})


def room_list(request):
    rooms = Room.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        rooms = rooms.filter(room_number__icontains=q)
    if category:
        rooms = rooms.filter(room_type=category)

    from django.core.paginator import Paginator
    paginator = Paginator(rooms, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'admin/room_list.html',
        {
            'rooms': page_obj,
            'page_obj': page_obj,
            'q': q,
            'category': category,
        }
    )


def edit_room(request, id):

    room = get_object_or_404(Room.all_objects, id=id)

    if request.method == 'POST':

        form = RoomForm(
            request.POST,
            request.FILES,
            instance=room
        )

        if form.is_valid():
            room = form.save(commit=False)
            room.edited_by = request.user
            room.save()
            form.save_m2m()
            messages.success(request, "Room updated successfully!")
            return redirect('room_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = RoomForm(instance=room)
    return render(
        request,
        'admin/edit_room.html',
        {'form': form}
    )


def delete_room(request, id):

    room = get_object_or_404(Room.all_objects, id=id)

    if request.method == 'POST':
        room.delete()
        messages.success(request, "Room deleted successfully!")

    return redirect('room_list')


def restore_room(request, id):
    room = get_object_or_404(Room.all_objects, id=id)
    if request.method == 'POST':
        room.is_deleted = False
        room.deleted_at = None
        room.deleted_by = None
        room.save()
        messages.success(request, "Room restored successfully!")
    return redirect('room_list')

def add_event_hall(request):
    if request.method == 'POST':
        form = EventHallForm(request.POST, request.FILES)
        if form.is_valid():
            hall = form.save(commit=False)
            hall.created_by = request.user
            hall.save()
            form.save_m2m()
            messages.success(request, "Event Hall added successfully!")
            return redirect('hall_list')
    else:
        form = EventHallForm()

    return render(request, 'admin/add_event_hall.html', {'form': form})


def hall_list(request):
    halls = event_hall.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        halls = halls.filter(hall_name__icontains=q)
    if category:
        halls = halls.filter(hall_type=category)

    from django.core.paginator import Paginator
    paginator = Paginator(halls, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'admin/hall_list.html',
        {
            'halls': page_obj,
            'page_obj': page_obj,
            'q': q,
            'category': category,
        }
    )


def hall_delete(request, id):
    hall = get_object_or_404(event_hall.all_objects, hall_id=id)
    if request.method == 'POST':
        hall.delete()
        messages.success(request, "Event Hall deleted successfully!")
    return redirect('hall_list')


def edit_event_hall(request, id):
    hall = get_object_or_404(event_hall.all_objects, hall_id=id)

    if request.method == 'POST':
        form = EventHallForm(
            request.POST,
            request.FILES,
            instance=hall
        )

        if form.is_valid():
            hall = form.save(commit=False)
            hall.edited_by = request.user
            hall.save()
            form.save_m2m()
            messages.success(request, "Event Hall updated successfully!")
            return redirect('hall_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

    else:
        form = EventHallForm(instance=hall)

    return render(request,
                  'admin/edit_event_hall.html',
                  {'form': form})


def restore_event_hall(request, id):
    hall = get_object_or_404(event_hall.all_objects, hall_id=id)
    if request.method == 'POST':
        hall.is_deleted = False
        hall.deleted_at = None
        hall.deleted_by = None
        hall.save()
        messages.success(request, "Event Hall restored successfully!")
    return redirect('hall_list')

def add_service(request, package_id=None):
    package = None
    if package_id:
        package = get_object_or_404(Package.all_objects, package_id=package_id)

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.created_by = request.user
            service.save()
            form.save_m2m()
            if package:
                package.services.add(service)
            # If AJAX request, return JSON (avoid full page reload)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'service': {
                        'id': service.service_id,
                        'name': service.service_name,
                        'price': str(service.service_price)
                    }
                })
            messages.success(request, "Service added successfully!")
            if package:
                return redirect('view_package', id=package.package_id)
            return redirect('package_list')
        else:
            # If AJAX and invalid, return form errors
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ServiceForm()

    return render(request, 'admin/add_service.html', {'form': form, 'package': package})


def service_list(request):
    services = Service.objects.all()
    return render(
        request,
        'admin/service_list.html',
        {'services': services}
    )


def edit_service(request, package_id, id):
    # package_id passed first by URL
    package = get_object_or_404(Package.all_objects, package_id=package_id)
    service = get_object_or_404(Service.all_objects, service_id=id)

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save(commit=False)
            service.edited_by = request.user
            service.save()
            form.save_m2m()
            # if AJAX, return JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'service': {'id': service.service_id, 'name': service.service_name, 'price': str(service.service_price)}})
            messages.success(request, "Service updated successfully!")
            return redirect('view_package', id=package.package_id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ServiceForm(instance=service)

    return render(request, 'admin/edit_service.html', {'form': form, 'package': package})


def delete_service(request, package_id, id):
    package = get_object_or_404(Package.all_objects, package_id=package_id)
    service = get_object_or_404(Service.all_objects, service_id=id)

    # allow POST or AJAX DELETE
    if request.method in ('POST', 'DELETE') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        service.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'id': id})
        messages.success(request, "Service deleted successfully!")
        return redirect('view_package', id=package.package_id)

    # fallback: if GET, redirect back
    return redirect('view_package', id=package.package_id)


def restore_service(request, package_id, id):
    package = get_object_or_404(Package.all_objects, package_id=package_id)
    service = get_object_or_404(Service.all_objects, service_id=id)
    if request.method == 'POST':
        service.is_deleted = False
        service.deleted_at = None
        service.deleted_by = None
        service.save()
        messages.success(request, "Service restored successfully!")
    return redirect('view_package', id=package.package_id)
def add_package(request):
    # SAVE PACKAGE with inline services (similar to activity sessions flow)
    service_values = [
        {
            'service_name': '',
            'service_price': ''
        }
    ]

    if request.method == 'POST':
        form = PackageForm(request.POST)

        service_name_list = request.POST.getlist('service_name[]')
        service_price_list = request.POST.getlist('service_price[]')

        service_values = []
        service_errors = []
        all_services_valid = True

        row_count = max(len(service_name_list), len(service_price_list), 1)

        for index in range(row_count):
            sname = service_name_list[index] if index < len(service_name_list) else ''
            sprice = service_price_list[index] if index < len(service_price_list) else ''
            service_values.append({'service_name': sname, 'service_price': sprice})
            # basic validation
            if sname and sprice:
                try:
                    float(sprice)
                except Exception:
                    all_services_valid = False
                    service_errors.append({'index': index, 'error': 'Invalid price'})
            elif sname or sprice:
                all_services_valid = False
                service_errors.append({'index': index, 'error': 'Both name and price required'})

        if form.is_valid() and all_services_valid:
            package = form.save(commit=False)
            package.created_by = request.user
            package.save()
            try:
                form.save_m2m()
            except Exception:
                pass

            # create new services and associate
            for s in service_values:
                if s['service_name'] and s['service_price']:
                    try:
                        srv = Service.objects.create(
                            service_name=s['service_name'],
                            service_price=s['service_price'],
                            created_by=request.user
                        )
                        package.services.add(srv)
                    except Exception:
                        # skip failing service creation
                        pass

            messages.success(request, 'Package added successfully.')
            return redirect('package_list')

    else:
        form = PackageForm()

    return render(request, 'admin/add_package.html', {'form': form, 'service_values': service_values, 'service_errors': service_errors if request.method == 'POST' else []})

def package_list(request):
    packages = Package.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        packages = packages.filter(package_name__icontains=q)
    if category:
        packages = packages.filter(package_type=category)

    from django.core.paginator import Paginator
    paginator = Paginator(packages, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'admin/package_list.html',
        {
            'packages': page_obj,
            'page_obj': page_obj,
            'q': q,
            'category': category,
        }
    )

def edit_package(request, id):
    package = get_object_or_404(Package.all_objects, package_id=id)
    if request.method == 'POST':
        form = PackageForm(
            request.POST,
            instance=package
        )
        if form.is_valid():
            package = form.save(commit=False)
            package.edited_by = request.user
            package.save()
            form.save_m2m()
            messages.success(
                request,
                "Package updated successfully!"
            )
            return redirect('package_list')
    else:
        form = PackageForm(instance=package)
    service_form = ServiceForm()
    services = package.services.all()

    return render(
        request,
        'admin/edit_package.html',
        {
            'form': form,
            'package': package,
            'services': services,
            'service_form': service_form
        }
    )


def view_package(request, id):
    # Single page for viewing and editing a package (handles updates and delete)
    package = get_object_or_404(Package.all_objects, package_id=id)
    if request.method == 'POST':
        # handle delete action
        if request.POST.get('action') == 'delete':
            package.delete()
            messages.success(request, 'Package deleted successfully.')
            return redirect('package_list')

        # otherwise treat as update
        form = PackageForm(request.POST, instance=package)
        if form.is_valid():
            package = form.save(commit=False)
            package.edited_by = request.user
            package.save()
            form.save_m2m()
            messages.success(request, 'Package updated successfully!')
            return redirect('package_list')
    else:
        form = PackageForm(instance=package)

    service_form = ServiceForm()
    services = package.services.all()

    return render(request, 'admin/edit_package.html', {
        'form': form,
        'package': package,
        'services': services,
        'service_form': service_form
    })


def restore_package(request, id):
    package = get_object_or_404(Package.all_objects, package_id=id)
    if request.method == 'POST':
        package.is_deleted = False
        package.deleted_at = None
        package.deleted_by = None
        package.save()
        messages.success(request, "Package restored successfully!")
    return redirect('package_list')



def add_food_item(request):
    if request.method == 'POST':
        form = FoodItemForm(
            request.POST,
            request.FILES
        )
        if form.is_valid():
            food = form.save(commit=False)
            food.created_by = request.user
            food.save()
            form.save_m2m()
            messages.success(request, "Food/Beverage item added successfully!")
            return redirect('food_item_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = FoodItemForm()

    return render(
        request,
        'admin/add_food_item.html',
        {'form': form}
    )


def food_item_list(request):
    food_items = FoodItem.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        food_items = food_items.filter(item_name__icontains=q)
    if category:
        food_items = food_items.filter(category=category)

    from django.core.paginator import Paginator
    paginator = Paginator(food_items, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'admin/food_item_list.html',
        {
            'food_items': page_obj,
            'page_obj': page_obj,
            'q': q,
            'category': category,
        }
    )


def edit_food_item(request, id):
    food_item = get_object_or_404(FoodItem.all_objects, id=id)
    if request.method == 'POST':
        form = FoodItemForm(
            request.POST,
            request.FILES,
            instance=food_item
        )
        if form.is_valid():
            food = form.save(commit=False)
            food.edited_by = request.user
            food.save()
            form.save_m2m()
            messages.success(request, "Food/Beverage item updated successfully!")
            return redirect('food_item_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = FoodItemForm(instance=food_item)

    return render(
        request,
        'admin/edit_food_item.html',
        {'form': form}
    )


def delete_food_item(request, id):
    food_item = get_object_or_404(FoodItem.all_objects, id=id)
    if request.method == 'POST':
        food_item.delete()
        messages.success(request, "Food/Beverage item deleted successfully!")
    return redirect('food_item_list')


def restore_food_item(request, id):
    food_item = get_object_or_404(FoodItem.all_objects, id=id)
    if request.method == 'POST':
        food_item.is_deleted = False
        food_item.deleted_at = None
        food_item.deleted_by = None
        food_item.save()
        messages.success(request, "Food item restored successfully!")
    return redirect('food_item_list')


def activity_list(request):
    activities = Activity.objects.all()
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        activities = activities.filter(activity_name__icontains=q)
    if category:
        activities = activities.filter(activity_type=category)

    from django.core.paginator import Paginator
    paginator = Paginator(activities, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'admin/activity_list.html',
        {
            'activities': page_obj,
            'page_obj': page_obj,
            'q': q,
            'category': category,
        }
    )

def add_activity(request):

    session_values = [
        {
            'start_time': '',
            'end_time': '',
            'capacity': '',
            'status': 'Available'
        }
    ]

    if request.method == 'POST':

        activity_form = ActivityForm(
            request.POST,
            request.FILES
        )

        start_time_list = request.POST.getlist('start_time[]')
        end_time_list = request.POST.getlist('end_time[]')
        capacity_list = request.POST.getlist('capacity[]')
        status_list = request.POST.getlist('session_status[]')

        session_values = []
        session_errors = []
        all_sessions_valid = True
        session_forms = []

        row_count = max(
            len(start_time_list),
            len(end_time_list),
            len(capacity_list),
            len(status_list),
            1
        )

        for index in range(row_count):
            session_data = {
                'start_time': start_time_list[index] if index < len(start_time_list) else '',
                'end_time': end_time_list[index] if index < len(end_time_list) else '',
                'capacity': capacity_list[index] if index < len(capacity_list) else '',
                'status': status_list[index] if index < len(status_list) else 'Available'
            }

            session_values.append(session_data)
            session_form = ActivitySessionForm(session_data)
            session_forms.append(session_form)

            if not session_form.is_valid():
                all_sessions_valid = False
                session_errors.append(session_form.errors)

        if activity_form.is_valid() and all_sessions_valid:
            activity = activity_form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            activity_form.save_m2m()

            for session_form in session_forms:
                session = session_form.save(commit=False)
                session.activity = activity
                session.created_by = request.user
                session.save()
                session_form.save_m2m()

            messages.success(request, 'Activity added successfully!')
            return redirect('activity_list')
        else:
            for field, errors in activity_form.errors.items():
                for error in errors:
                    messages.error(request, f"Activity {field.replace('_', ' ').title()}: {error}")
            for i, s_form in enumerate(session_forms):
                if not s_form.is_valid():
                    for field, errors in s_form.errors.items():
                        for error in errors:
                            messages.error(request, f"Session {i+1} {field.replace('_', ' ').title()}: {error}")

    else:
        activity_form = ActivityForm()
        session_forms = [ActivitySessionForm()]

    return render(
        request,
        'admin/add_activity.html',
        {
            'activity_form': activity_form,
            'session_values': session_values,
            'session_forms': session_forms,
            'session_errors': session_errors if request.method == 'POST' else []
        }
    )


def view_activity(request, id):
    activity = get_object_or_404(Activity.all_objects, id=id)
    sessions = ActivitySession.all_objects.filter(activity=activity)
    return render(
        request,
        'admin/view_activity.html',
        {
            'activity': activity,
            'sessions': sessions
        }
    )


def add_session(request, activity_id):
    activity = get_object_or_404(Activity.all_objects, id=activity_id)
    if request.method == 'POST':
        form = ActivitySessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.activity = activity
            session.created_by = request.user
            session.save()
            form.save_m2m()
            messages.success(request, 'Session added successfully.')
            return redirect('edit_activity', id=activity.id)
    else:
        form = ActivitySessionForm()

    return render(
        request,
        'admin/add_session.html',
        {
            'activity': activity,
            'form': form
        }
    )


def edit_session(request, id):
    session = get_object_or_404(ActivitySession.all_objects, id=id)
    activity = session.activity
    if request.method == 'POST':
        form = ActivitySessionForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save(commit=False)
            session.edited_by = request.user
            session.save()
            form.save_m2m()
            messages.success(request, 'Session updated successfully.')
            return redirect('edit_activity', id=activity.id)
    else:
        form = ActivitySessionForm(instance=session)

    return render(
        request,
        'admin/edit_session.html',
        {
            'activity': activity,
            'session': session,
            'form': form
        }
    )


def delete_session(request, id):
    session = get_object_or_404(ActivitySession.all_objects, id=id)
    activity = session.activity
    if request.method == 'POST':
        session.delete()
        messages.success(request, 'Session deleted successfully.')
    return redirect('edit_activity', id=activity.id)


def restore_session(request, id):
    session = get_object_or_404(ActivitySession.all_objects, id=id)
    activity = session.activity
    if request.method == 'POST':
        session.is_deleted = False
        session.deleted_at = None
        session.deleted_by = None
        session.save()
        messages.success(request, 'Session restored successfully.')
    return redirect('edit_activity', id=activity.id)


def edit_activity(request, id):

    activity = get_object_or_404(
        Activity.all_objects,
        id=id
    )

    if request.method == 'POST':

        form = ActivityForm(
            request.POST,
            request.FILES,
            instance=activity
        )

        if form.is_valid():
            act = form.save(commit=False)
            act.edited_by = request.user
            act.save()
            form.save_m2m()
            messages.success(request, "Activity updated successfully!")
            return redirect('activity_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

    else:

        form = ActivityForm(
            instance=activity
        )

    sessions = ActivitySession.all_objects.filter(activity=activity)

    return render(
        request,
        'admin/edit_activity.html',
        {
            'form': form,
            'activity': activity,
            'sessions': sessions
        }
    )

def delete_activity(request, id):

    activity = get_object_or_404(
        Activity.all_objects,
        id=id
    )

    if request.method == 'POST':
        activity.delete()
        messages.success(request, "Activity deleted successfully!")

    return redirect('activity_list')


def restore_activity(request, id):
    activity = get_object_or_404(Activity.all_objects, id=id)
    if request.method == 'POST':
        activity.is_deleted = False
        activity.deleted_at = None
        activity.deleted_by = None
        activity.save()
        messages.success(request, "Activity restored successfully!")
    return redirect('activity_list')

def add_staff_user(request):

    from staffapp.models import Menu, SubMenu
    from .models import RegisteredUser

    VIEW_ONLY_MODULES = [
        "Reports Dashboard",
        "Financial Summary",
        "Loyalty Transactions",
        "Attendance Report",
        "Payments Report",
        "Events Report",
        "Rooms Report",
        "Tables Report",
        "Attendance Reports",
        "Payments Reports",
        "Event Reports",
        "Room Reports",
        "Table Reports",
    ]

    NO_DELETE_MODULES = [
        "Room Bookings",
        "Hall Bookings",
        "Activity Bookings",
        "Table Reservations",
        "Restaurant Orders",
        "Offline Booking",
    ]

    all_menus = Menu.objects.prefetch_related('submenus').all()
    permission_menus = []
    for menu in all_menus:
        submenus = []
        for sub in menu.submenus.all():
            sub.is_view_only = sub.name in VIEW_ONLY_MODULES
            sub.is_no_delete = sub.name in NO_DELETE_MODULES
            submenus.append(sub)
        permission_menus.append({
            'menu': menu,
            'submenus': submenus
        })
    registered_staff = RegisteredUser.objects.all()

    print(f"Menu count: {Menu.objects.count()}")
    print(f"SubMenu count: {SubMenu.objects.count()}")
    print(f"permission_menus length: {len(permission_menus)}")

    from django.db.models import Exists, OuterRef

    already_staff = StaffUser.objects.filter(user__username=OuterRef('username'))
    registered_staff = RegisteredUser.objects.filter(
        user_type='staff'
    ).annotate(
        is_already_staff=Exists(already_staff)
    ).filter(
        is_already_staff=False
    )

    if request.method == "POST":
        form = StaffUserForm(request.POST, request.FILES)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            phone = form.cleaned_data['phone']
            department = form.cleaned_data['department']
            role = form.cleaned_data['role']
            email = form.cleaned_data.get('email', '')

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return render(request, 'admin/add_staff_user.html', {
                    'form': form,
                    'permission_menus': permission_menus,
                    'registered_staff': registered_staff
                })
                return render(request, 'admin/add_staff_user.html', {'form': form, 'registered_staff': registered_staff})

            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=full_name,
                email=email, 
                is_staff=True
            )

            # Find the registered user to sync their data if available
            registered = RegisteredUser.objects.filter(username=username).first()

            staff_user = StaffUser.objects.create(
                user=user,
                department=department,
                role=role,
                phone=phone,
                created_by=request.user
            )

            # Sync image and resume from the registration flow
            if registered:
                if registered.image:
                    staff_user.profile_image = registered.image
                if registered.resume:
                    staff_user.resume = registered.resume
            
            # If the admin uploaded a specific image directly in this form, override
            if 'profile_image' in request.FILES:
                staff_user.profile_image = request.FILES['profile_image']
            
            staff_user.save()

            # ==========================
            # SAVE PERMISSIONS
            # ==========================
            # Bypass RETURNING clause for MariaDB compatibility
            from django.db import connection
            connection.features.can_return_columns_from_insert = False

            for submenu in SubMenu.objects.all():

                can_view = f"view_{submenu.id}" in request.POST
                can_add = f"add_{submenu.id}" in request.POST
                can_edit = f"edit_{submenu.id}" in request.POST
                can_delete = f"delete_{submenu.id}" in request.POST

                if can_add or can_edit or can_delete:
                    can_view = True

                # Save only if at least one permission selected
                if can_view or can_add or can_edit or can_delete:
                    MenuPermission.objects.create(
                        user=user,
                        submenu=submenu,
                        can_view=can_view,
                        can_add=can_add,
                        can_edit=can_edit,
                        can_delete=can_delete
                    )

            messages.success(request, "Staff User Created Successfully")
            return redirect('staff_user_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

    else:

        form = StaffUserForm()

    return render(
        request,
        'admin/add_staff_user.html',
        {
            'form': form,
            'permission_menus': permission_menus,
            'registered_staff': registered_staff
        }
    )
def staff_user_list(request):

    staff_users = StaffUser.objects.select_related(
        'user'
    ).order_by('id')

    return render(
        request,
        'admin/staff_user_list.html',
        {
            'staff_users': staff_users
        }
    )


def delete_staff_user(request, id):

    staff = get_object_or_404(
        StaffUser.all_objects,
        id=id
    )

    username = staff.user.username

    if request.method == 'POST':
        user = staff.user
        staff.delete()
        user.delete()

        messages.success(
            request,
            f"Staff User '{username}' deleted successfully."
        )

    return redirect(
        'staff_user_list'
    )
def edit_staff_user(request, id):

    staff = get_object_or_404(
        StaffUser.all_objects,
        id=id
    )

    if request.method == "POST":
        full_name = request.POST.get('full_name')
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation
        if phone:
            if not re.match(r'^\d{10}$', phone):
                messages.error(request, "Enter a valid 10-digit phone number")
                return render(request, 'admin/edit_staff_user.html', {
                    'staff': staff,
                    'departments': Department.objects.all(),
                    'roles': Role.objects.all()
                })

        if User.objects.filter(username=username).exclude(pk=staff.user.pk).exists():
            messages.error(request, "Username already exists")
            return render(request, 'admin/edit_staff_user.html', {
                'staff': staff,
                'departments': Department.objects.all(),
                'roles': Role.objects.all()
            })

        # --- Change Password (Optional) ---
        # If both fields are empty, the existing password is left untouched.
        # If either field is filled, both must be filled, valid, and matching.
        change_password = bool(new_password or confirm_password)
        if change_password:
            if not new_password or not confirm_password:
                messages.error(request, "Enter and confirm the new password, or leave both blank to keep the current password.")
                return render(request, 'admin/edit_staff_user.html', {
                    'staff': staff,
                    'departments': Department.objects.all(),
                    'roles': Role.objects.all()
                })
            if len(new_password) < 8:
                messages.error(request, "New password must be at least 8 characters long.")
                return render(request, 'admin/edit_staff_user.html', {
                    'staff': staff,
                    'departments': Department.objects.all(),
                    'roles': Role.objects.all()
                })
            if new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
                return render(request, 'admin/edit_staff_user.html', {
                    'staff': staff,
                    'departments': Department.objects.all(),
                    'roles': Role.objects.all()
                })

        staff.user.first_name = full_name
        staff.user.username = username
        if email:
            staff.user.email = email
        staff.phone = phone
        
        dept_id = request.POST.get('department')
        role_id = request.POST.get('role')
        staff.department = Department.objects.filter(id=dept_id).first() if dept_id else None
        staff.role = Role.objects.filter(id=role_id).first() if role_id else None

        staff.status = request.POST.get(
            'status'
        ) == "True"

        staff.user.is_staff = True

        if change_password:
            staff.user.set_password(new_password)

        staff.user.save()
        staff.edited_by = request.user
        staff.save()

        if change_password and staff.user.pk == request.user.pk:
            # Admin edited their own account on this page -- keep them logged in
            # rather than invalidating the current session's auth hash.
            update_session_auth_hash(request, staff.user)

        if change_password:
            messages.success(request, "Staff User Updated Successfully. Password changed.")
        else:
            messages.success(request, "Staff User Updated Successfully")
        return redirect('staff_user_list')
    
    # If there were errors (e.g. from manual validation in view)
    # Note: edit_staff_user currently doesn't use a Form object for POST, 
    # it uses request.POST.get directly. If it fails, we should add messages.

    return render(
        request,
        'admin/edit_staff_user.html',
        {
            'staff': staff,
            'departments': Department.objects.all(),
            'roles': Role.objects.all()
        }
    )
def restore_staff_user(request, id):
    staff = get_object_or_404(StaffUser.all_objects, id=id)
    if request.method == 'POST':
        staff.is_deleted = False
        staff.deleted_at = None
        staff.deleted_by = None
        staff.save()
        
        staff.user.is_active = True
        staff.user.save()
        
        messages.success(request, f"Staff User '{staff.user.username}' restored successfully.")
    return redirect('staff_user_list')


def manage_permissions(request, id):

    staff = get_object_or_404(StaffUser, id=id)

    # ==========================
    # GET ALL MENUS + SUBMENUS
    # ==========================
    all_menus = Menu.objects.prefetch_related('submenus').all()

    VIEW_ONLY_MODULES = [
        "Reports Dashboard",
        "Financial Summary",
        "Loyalty Transactions",
        "Attendance Report",
        "Payments Report",
        "Events Report",
        "Rooms Report",
        "Tables Report",
        "Attendance Reports",
        "Payments Reports",
        "Event Reports",
        "Room Reports",
        "Table Reports",
    ]

    NO_DELETE_MODULES = [
        "Room Bookings",
        "Hall Bookings",
        "Activity Bookings",
        "Table Reservations",
        "Restaurant Orders",
        "Offline Booking",
    ]

    menus = []
    for menu in all_menus:
        submenus = []
        for sub in menu.submenus.all():
            sub.is_view_only = sub.name in VIEW_ONLY_MODULES
            sub.is_no_delete = sub.name in NO_DELETE_MODULES
            submenus.append(sub)
        menus.append({
            'menu': menu,
            'submenus': submenus
        })

    # ==========================
    # SAVE PERMISSIONS
    # ==========================
    if request.method == "POST":

        print("POST RECEIVED")

        # Bypass RETURNING clause for MariaDB compatibility (e.g. MariaDB 10.4)
        from django.db import connection
        connection.features.can_return_columns_from_insert = False

        # Delete old permissions
        MenuPermission.objects.filter(user=staff.user).delete()

        print("POST DATA:", request.POST)
        print("SUBMENU COUNT:", SubMenu.objects.count())

        for submenu in SubMenu.objects.all():

            can_view = f"view_{submenu.id}" in request.POST
            can_add = f"add_{submenu.id}" in request.POST
            can_edit = f"edit_{submenu.id}" in request.POST
            can_delete = f"delete_{submenu.id}" in request.POST

            if can_add or can_edit or can_delete:
                can_view = True

            # Save only if at least one permission selected
            if can_view or can_add or can_edit or can_delete:

                MenuPermission.objects.create(
                    user=staff.user,
                    submenu=submenu,
                    can_view=can_view,
                    can_add=can_add,
                    can_edit=can_edit,
                    can_delete=can_delete
                )

        messages.success(request, "Permissions updated successfully")

        return redirect('admin_dashboard')

    # ==========================
    # LOAD EXISTING PERMISSIONS
    # ==========================

    existing_view = list(
        MenuPermission.objects.filter(
            user=staff.user,
            can_view=True
        ).values_list('submenu_id', flat=True)
    )

    existing_add = list(
        MenuPermission.objects.filter(
            user=staff.user,
            can_add=True
        ).values_list('submenu_id', flat=True)
    )

    existing_edit = list(
        MenuPermission.objects.filter(
            user=staff.user,
            can_edit=True
        ).values_list('submenu_id', flat=True)
    )

    existing_delete = list(
        MenuPermission.objects.filter(
            user=staff.user,
            can_delete=True
        ).values_list('submenu_id', flat=True)
    )

    # ==========================
    # SEND TO TEMPLATE
    # ==========================
    return render(
        request,
        'admin/manage_permissions.html',
        {
            'staff': staff,
            'menus': menus,
            'existing_view': existing_view,
            'existing_add': existing_add,
            'existing_edit': existing_edit,
            'existing_delete': existing_delete,
        }
    )
def menu_list(request):

    all_menus = Menu.objects.prefetch_related('submenus').all()
    
    menu_data = []
    for menu in all_menus:
        menu_data.append({
            'menu': menu,
            'submenus': menu.submenus.all()
        })

    return render(
        request,
        'admin/menu_list.html',
        {
            'menus': menu_data
        }
    )


def add_menu(request):

    if request.method == "POST":

        form = MenuForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('menu_list')

    else:

        form = MenuForm()

    return render(
        request,
        'admin/add_menu.html',
        {
            'form': form
        }
    )
def submenu_list(request):

    submenus = SubMenu.objects.select_related(
        'menu'
    )

    return render(
        request,
        'admin/submenu_list.html',
        {
            'submenus': submenus
        }
    )
def add_submenu(request):

    if request.method == "POST":

        form = SubMenuForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect('submenu_list')

    else:

        form = SubMenuForm()

    menu_list = Menu.objects.all()

    return render(
        request,
        'admin/add_submenu.html',
        {
            'form': form,
            'menu_list': menu_list
        }
    )

def get_user_menus(user):
    from staffapp.models import Menu, SubMenu

    if user.is_superuser:
        return {
            menu: menu.submenus.all()
            for menu in Menu.objects.prefetch_related('submenus')
        }

    permitted_submenus = SubMenu.objects.filter(
        menupermission__user=user,
        menupermission__can_view=True
    ).select_related('menu')

    menus = {}

    for sub in permitted_submenus:
        if sub.menu not in menus:
            menus[sub.menu] = []
        menus[sub.menu].append(sub)

    return menus

def delete_menu(request, id):

    if request.method == "POST":
        menu = get_object_or_404(Menu, id=id)
        menu.delete()
        messages.success(request, "Module deleted successfully")

    return redirect('menu_list')


def delete_submenu(request, id):

    if request.method == "POST":
        submenu = get_object_or_404(SubMenu, id=id)
        submenu.delete()
        messages.success(request, "SubMenu deleted successfully")

    return redirect('submenu_list')


from .models import RestaurantTable
from .forms import RestaurantTableForm


# LIST TABLES

# TABLE LIST
def table_list(request):
    tables = RestaurantTable.objects.all().order_by('table_number')
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if q:
        tables = tables.filter(table_number__icontains=q)
    if category:
        tables = tables.filter(location=category)

    from django.core.paginator import Paginator
    paginator = Paginator(tables, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'admin/table_list.html',
        {
            'tables': page_obj,
            'page_obj': page_obj,
            'q': q,
            'category': category,
        }
    )


# ADD TABLE
def add_table(request):

    if request.method == 'POST':

        form = RestaurantTableForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            table = form.save(commit=False)
            table.created_by = request.user
            table.save()
            form.save_m2m()

            messages.success(
                request,
                'Restaurant table added successfully.'
            )

            return redirect('table_list')

    else:

        form = RestaurantTableForm()

    return render(
        request,
        'admin/add_table.html',
        {
            'form': form
        }
    )


# EDIT TABLE
def edit_table(request, id):

    table = get_object_or_404(
        RestaurantTable.all_objects,
        id=id
    )

    if request.method == 'POST':

        form = RestaurantTableForm(
            request.POST,
            request.FILES,
            instance=table
        )

        if form.is_valid():

            table = form.save(commit=False)
            table.edited_by = request.user
            table.save()
            form.save_m2m()

            messages.success(
                request,
                'Restaurant table updated successfully.'
            )

            return redirect('table_list')

    else:

        form = RestaurantTableForm(
            instance=table
        )

    return render(
        request,
        'admin/edit_table.html',
        {
            'form': form
        }
    )


# DELETE TABLE
def delete_table(request, id):

    table = get_object_or_404(
        RestaurantTable.all_objects,
        id=id
    )

    if request.method == 'POST':
        table.delete()

        messages.success(
            request,
            'Restaurant table deleted successfully.'
        )

    return redirect('table_list')


def restore_table(request, id):
    table = get_object_or_404(RestaurantTable.all_objects, id=id)
    if request.method == 'POST':
        table.is_deleted = False
        table.deleted_at = None
        table.deleted_by = None
        table.save()
        messages.success(request, "Table restored successfully!")
    return redirect('table_list')


def loyalty_customer_list(request):

    customers = Customer.objects.select_related(
        'user'
    ).order_by(
        'user__username'
    )

    return render(
        request,
        'admin/loyalty_customer_list.html',
        {
            'customers': customers
        }
    )


def edit_loyalty_points(request, id):

    customer = get_object_or_404(
        Customer.objects.select_related('user'),
        id=id
    )

    if request.method == 'POST':

        action = request.POST.get('action')

        try:
            points = int(request.POST.get('points', 0))
        except (TypeError, ValueError):
            points = 0

        points = max(points, 0)

        if points <= 0:
            messages.error(
                request,
                'Please enter points greater than zero.'
            )
            return redirect(
                'edit_loyalty_points',
                id=customer.id
            )

        if action == 'add':
            customer.loyalty_points += points
            customer.lifetime_points_earned += points
            customer.save(update_fields=[
                'loyalty_points',
                'lifetime_points_earned',
                'membership_status'
            ])

            LoyaltyTransaction.objects.create(
                customer=customer,
                booking_reference='Manual admin adjustment',
                transaction_type=LoyaltyTransaction.TRANSACTION_EARNED,
                points=points,
                amount=0
            )

            messages.success(
                request,
                'Loyalty points added successfully.'
            )

        elif action == 'remove':
            points_to_remove = min(
                customer.loyalty_points,
                points
            )

            if points_to_remove <= 0:
                messages.error(
                    request,
                    'This customer has no points to remove.'
                )
                return redirect(
                    'edit_loyalty_points',
                    id=customer.id
                )

            customer.loyalty_points -= points_to_remove
            customer.save(update_fields=[
                'loyalty_points',
                'membership_status'
            ])

            LoyaltyTransaction.objects.create(
                customer=customer,
                booking_reference='Manual admin adjustment',
                transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED,
                points=points_to_remove,
                amount=0
            )

            messages.success(
                request,
                'Loyalty points removed successfully.'
            )

        else:
            messages.error(
                request,
                'Invalid loyalty action.'
            )

        return redirect(
            'loyalty_customer_list'
        )

    return render(
        request,
        'admin/edit_loyalty_points.html',
        {
            'customer': customer
        }
    )


def loyalty_transaction_list(request):

    transactions = LoyaltyTransaction.objects.select_related(
        'customer',
        'customer__user'
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'admin/loyalty_transaction_list.html',
        {
            'transactions': transactions,
            'selected_customer': None
        }
    )


def customer_loyalty_transactions(request, id):

    customer = get_object_or_404(
        Customer.objects.select_related('user'),
        id=id
    )

    transactions = LoyaltyTransaction.objects.filter(
        customer=customer
    ).select_related(
        'customer',
        'customer__user'
    ).order_by(
        '-created_at'
    )

    return render(
        request,
        'admin/loyalty_transaction_list.html',
        {
            'transactions': transactions,
            'selected_customer': customer
        }
    )

# ==========================
# NOTIFICATION SYSTEM
# ==========================

def _redirect_to_dashboard(request, tab=None, extra_params=None):
    url_name = 'admin_dashboard'
    try:
        if not (request.user.is_superuser or (request.user.staff_profile.role and request.user.staff_profile.role.name.lower() == 'admin')):
            url_name = 'staff_dashboard'
    except:
        pass
    
    from django.urls import reverse
    url = reverse(url_name)
    params = []
    if tab:
        params.append(f"notif_tab={tab}")
    if extra_params:
        for k, v in extra_params.items():
            params.append(f"{k}={v}")
            
    if params:
        url += "?" + "&".join(params)
    return redirect(url)

#COMPOSE NOTICATION
def compose_notification(request):
    return _redirect_to_dashboard(request, tab='compose')

def inbox(request):
    return _redirect_to_dashboard(request, tab='inbox')

#MARK_NOTIFICATION
def mark_notification_read(request, id):
    status_record = get_object_or_404(NotificationStatus, id=id, recipient=request.user)
    status_record.is_read = True
    status_record.save()
    messages.success(request, "Marked as read.")
    return _redirect_to_dashboard(request, tab='inbox')

#VIEW NOTIFICATION
def view_notification(request, id):
    status_record = get_object_or_404(NotificationStatus, id=id, recipient=request.user)
    if not status_record.is_read:
        status_record.is_read = True
        status_record.save()
    return _redirect_to_dashboard(request, tab='inbox', extra_params={'notif_id': status_record.id})

#SENT NOTIFICATION
def sent_notifications(request):
    return _redirect_to_dashboard(request, tab='sent')

#VIEW SENT NOTIFICATION
def view_sent_notification(request, id):
    broadcast = get_object_or_404(NotificationBroadcast, id=id, sender=request.user)
    return _redirect_to_dashboard(request, tab='sent', extra_params={'sent_id': broadcast.id})


# ==========================================
# AJAX NOTIFICATION API ENDPOINTS
# ==========================================
from django.http import JsonResponse

def api_active_staff(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    staff = StaffUser.objects.filter(status=True).exclude(user=request.user).select_related('user', 'department', 'role')
    
    sender_profile = getattr(request.user, 'staff_profile', None)
    if sender_profile:
        sender_role = sender_profile.role.name.lower() if sender_profile.role else ''
        sender_dept = sender_profile.department
    else:
        sender_role = 'admin'
        sender_dept = None
        
    if not request.user.is_superuser and sender_role != 'admin':
        if sender_role == 'manager':
            staff = staff.filter(department=sender_dept)
        else:
            staff = staff.none()
            
    staff_data = [{'id': s.pk, 'name': str(s.user), 'department': s.department.name if s.department else '', 'role': s.role.name if s.role else ''} for s in staff]
    
    departments = [{'id': d.pk, 'name': d.name} for d in Department.objects.all()]
    roles = [{'id': r.pk, 'name': r.name} for r in Role.objects.all()]
    
    return JsonResponse({'success': True, 'staff': staff_data, 'departments': departments, 'roles': roles})

def api_compose_notification(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    sender_profile = getattr(request.user, 'staff_profile', None)
    if not request.user.is_superuser and not sender_profile:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES, sender=request.user)
        if form.is_valid():
            b_type = form.cleaned_data['broadcast_type']
            recipients = set()
            active_staff = StaffUser.objects.filter(status=True).exclude(user=request.user)
            
            if b_type == 'all':
                recipients.update([s.user for s in active_staff])
            elif b_type == 'admin':
                from django.contrib.auth.models import User
                recipients.update(User.objects.filter(is_superuser=True))
            elif b_type == 'department':
                recipients.update([s.user for s in active_staff.filter(department__in=form.cleaned_data.get('departments', []))])
            elif b_type == 'role':
                recipients.update([s.user for s in active_staff.filter(role__in=form.cleaned_data.get('roles', []))])
            elif b_type == 'specific':
                recipients.update([s.user for s in form.cleaned_data.get('staff_members', [])])
            elif b_type == 'my_department' and sender_profile:
                recipients.update([s.user for s in active_staff.filter(department=sender_profile.department)])
            elif b_type == 'my_manager' and sender_profile:
                managers = active_staff.filter(department=sender_profile.department, role__name__iexact='manager')
                recipients.update([m.user for m in managers])

            if recipients:
                broadcast = NotificationBroadcast.objects.create(
                    sender=request.user,
                    title=form.cleaned_data['title'],
                    message=form.cleaned_data['message'],
                    attachment=form.cleaned_data.get('attachment')
                )
                NotificationStatus.objects.bulk_create([
                    NotificationStatus(broadcast=broadcast, recipient=user) for user in recipients
                ])
                return JsonResponse({'success': True, 'message': f'Notification sent to {len(recipients)} user(s).'})
            else:
                return JsonResponse({'success': False, 'error': 'No users found matching those criteria.'})
        else:
            errors = {field: error_list[0] for field, error_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors})
    return JsonResponse({'success': False, 'error': 'Invalid method.'}, status=400)

def api_mark_notification_read(request, id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    status_record = get_object_or_404(NotificationStatus, id=id, recipient=request.user)
    status_record.is_read = True
    status_record.save()
    return JsonResponse({'success': True})

def api_get_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    unread_count = NotificationStatus.objects.filter(recipient=request.user, is_read=False).count()
    recent = NotificationStatus.objects.filter(
        recipient=request.user
    ).select_related(
        'broadcast', 
        'broadcast__sender'
    ).order_by('-broadcast__created_at')[:20]
    
    recent_data = []
    for n in recent:
        sender_name = "Administrator" if n.broadcast.sender.is_superuser else (n.broadcast.sender.get_full_name() or n.broadcast.sender.username)
        attachment_url = n.broadcast.attachment.url if n.broadcast.attachment else None
        recent_data.append({
            'id': n.id,
            'sender': sender_name,
            'username': n.broadcast.sender.username,
            'title': n.broadcast.title,
            'message': n.broadcast.message,
            'date_str': n.broadcast.created_at.strftime('%b %d, %Y %I:%M %p'),
            'date_short': n.broadcast.created_at.strftime('%b %d, %Y'),
            'attachment': attachment_url,
            'is_read': n.is_read
        })
        
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
        'notifications': recent_data
    })

def api_get_sent_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    
    sent = NotificationBroadcast.objects.filter(sender=request.user).order_by('-created_at')[:15]
    sent_data = []
    for s in sent:
        statuses = NotificationStatus.objects.filter(broadcast=s)
        total = statuses.count()
        read = statuses.filter(is_read=True).count()
        attachment_url = s.attachment.url if (s.attachment and s.attachment.name) else None
        
        sent_data.append({
            'id': s.id,
            'title': s.title,
            'message': s.message,
            'date_str': s.created_at.strftime('%b %d, %Y %I:%M %p'),
            'date_short': s.created_at.strftime('%b %d, %Y'),
            'attachment': attachment_url,
            'read_recipients': read,
            'total_recipients': total
        })
        
    return JsonResponse({
        'success': True,
        'sent_notifications': sent_data
    })

#DELETE SINGLE SENT NOTIFICATION (used for auto-clear on read)
def api_delete_sent_notification(request, id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    broadcast = get_object_or_404(NotificationBroadcast, id=id, sender=request.user)
    broadcast.delete()
    return JsonResponse({'success': True})

#CLEAR ALL SENT NOTIFICATIONS
def api_clear_sent_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    deleted_count, _ = NotificationBroadcast.objects.filter(sender=request.user).delete()
    return JsonResponse({'success': True, 'deleted_count': deleted_count})

#DELETE SINGLE INBOX NOTIFICATION (used for auto-clear on read)
#Only removes the recipient's own NotificationStatus row; the broadcast
#itself and other recipients' copies are left untouched.
def api_delete_notification(request, id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    status_record = get_object_or_404(NotificationStatus, id=id, recipient=request.user)
    status_record.delete()
    return JsonResponse({'success': True})

#CLEAR ALL INBOX NOTIFICATIONS (for the current recipient only)
def api_clear_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    deleted_count, _ = NotificationStatus.objects.filter(recipient=request.user).delete()
    return JsonResponse({'success': True, 'deleted_count': deleted_count})


# ==========================================
# OFFLINE BOOKING & API VIEWS
# ==========================================
from django.contrib.auth.decorators import login_required

@login_required
def api_room_calendar_status(request):
    """
    API endpoint for fetching room availability for the offline booking calendar.
    """
    # This is a baseline setup. You will add database logic here later to fetch real booked dates.
    data = {
        "status": "success",
        "message": "API is online",
        "booked_dates": []
    }
    return JsonResponse(data)

@login_required
def offline_booking(request):
    """View for manual Room bookings"""
    from bookingapp.views import release_expired_freshup_bookings
    release_expired_freshup_bookings()
    available_rooms = Room.objects.all() 
    return render(request, 'admin/bookings/offline_booking.html', {
        'available_rooms': available_rooms
    })

@login_required
def offline_event_booking(request):
    """View for manual Event Hall bookings"""
    halls = event_hall.objects.all()
    return render(request, 'admin/bookings/offline_event_booking.html', {
        'halls': halls
    })

@login_required
def offline_restaurant_table(request):
    """View for manual Restaurant Table bookings"""
    tables = RestaurantTable.objects.all()
    return render(request, 'admin/bookings/offline_restaurant_table.html', {
        'tables': tables
    })



#FEEDBACK

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from guestapp.models import ContactMessage
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from guestapp.models import ContactMessage

@staff_member_required
def admin_feedback_view(request):
    current_type = request.GET.get('type', 'all')
    feedbacks = ContactMessage.objects.all().order_by('-created_at')
    
    if current_type == 'general':
        feedbacks = feedbacks.filter(inquiry_type='general')
    elif current_type == 'feedback':
        feedbacks = feedbacks.filter(inquiry_type='feedback')
        
    return render(request, 'admin/feedback_list.html', {
        'feedbacks': feedbacks,
        'current_type': current_type
    })
@staff_member_required
def delete_feedback(request, id):
    feedback = get_object_or_404(ContactMessage, id=id)
    feedback.delete()
    messages.success(request, "Feedback deleted successfully.")
    return redirect('admin_feedback_list')


def staff_registration(request):
    """Admin page to register new staff profiles (not auth accounts)."""
    if request.method == 'POST':
        form = RegisteredUserForm(request.POST, request.FILES)
        if form.is_valid():
            registered = form.save(commit=False)
            registered.user_type = 'staff'
            registered.created_by = request.user
            registered.save()
            form.save_m2m()
            messages.success(request, f"Staff '{registered.full_name}' registered successfully!")
            return redirect('staff_registration_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = RegisteredUserForm()

    return render(request, 'admin/staff_registration.html', {'form': form})


def staff_registration_list(request):
    """List all registered staff profiles."""
    registered_users = RegisteredUser.objects.filter(user_type='staff').order_by('-created_at')
    return render(request, 'admin/staff_registration_list.html', {'registered_users': registered_users})


def delete_registered_user(request, id):
    user = get_object_or_404(RegisteredUser.all_objects, id=id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "Staff registration profile deleted successfully.")
    return redirect('staff_registration_list')


def restore_registered_user(request, id):
    user = get_object_or_404(RegisteredUser.all_objects, id=id)
    if request.method == 'POST':
        user.is_deleted = False
        user.deleted_at = None
        user.deleted_by = None
        user.save()
        messages.success(request, "Staff registration profile restored successfully.")
    return redirect('staff_registration_list')


def get_staff_details(request, user_id):
    """AJAX endpoint: return registered staff details as JSON."""
    try:
        staff = RegisteredUser.all_objects.get(id=user_id, user_type='staff')
    except RegisteredUser.DoesNotExist:
        return JsonResponse({'error': 'Staff not found'}, status=404)

    data = {
        'full_name': staff.full_name,
        'username': staff.username,
        'email': staff.email,
        'phone': staff.phone,
        'department': staff.department.id if staff.department else '',
        'role': staff.role.id if staff.role else '',
        'image_url': staff.image.url if staff.image else '',
        'resume_url': staff.resume.url if staff.resume else '',
    }
    return JsonResponse(data)


#-------------------------------------------------------------------------#
# STAYZEN OPERATIONAL REPORTING & BUSINESS INTELLIGENCE ENGINE
#-------------------------------------------------------------------------#
import csv
import json
import logging
import datetime
from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.db.models import Count, Sum, F, Q, Avg, ExpressionWrapper, fields
from django.db.models.functions import (
    ExtractHour, ExtractMinute, ExtractWeekDay, TruncDate, 
    TruncMonth, ExtractYear, ExtractMonth, Cast
)
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

# Import your models
from guestapp.models import ContactMessage
from bookingapp.models import (
    TableReservation, Order, OrderItem, RoomBooking, 
    EventBooking, LoyaltyTransaction, ActivityBooking
)
from adminapp.models import Room, event_hall, RestaurantTable, RegisteredUser, Package, Activity
from accountapp.models import Customer
from staffapp.models import Attendance

# ReportLab PDF Libraries
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def _lr(view):
    """Shorthand login required decorator."""
    return login_required(view, login_url='/staff/login/')

def _get_report_dates(request):
    """Standardizes global timeframe parameters for all report filtering."""
    import datetime as dt_module
    datetime_class = getattr(dt_module, 'datetime', dt_module)
    time_min = getattr(dt_module, 'time', None).min if hasattr(dt_module, 'time') else dt_module.datetime.min.time()
    time_max = getattr(dt_module, 'time', None).max if hasattr(dt_module, 'time') else dt_module.datetime.max.time()

    time_filter = request.GET.get('time_filter', 'this_month')
    now = timezone.now()
    today = timezone.localdate()
    
    if time_filter == '1h':
        start_datetime = now - dt_module.timedelta(hours=1)
        end_datetime = now
        start = start_datetime.date()
        end = end_datetime.date()
    elif time_filter == '24h':
        start_datetime = now - dt_module.timedelta(hours=24)
        end_datetime = now
        start = start_datetime.date()
        end = end_datetime.date()
    elif time_filter == 'this_week':
        start = today - dt_module.timedelta(days=today.weekday())
        end = start + dt_module.timedelta(days=6)
        start_datetime = timezone.make_aware(datetime_class.combine(start, time_min))
        end_datetime = timezone.make_aware(datetime_class.combine(end, time_max))
    elif time_filter == 'this_month':
        import calendar
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = today.replace(day=last_day)
        start_datetime = timezone.make_aware(datetime_class.combine(start, time_min))
        end_datetime = timezone.make_aware(datetime_class.combine(end, time_max))
    elif time_filter == 'this_year':
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
        start_datetime = timezone.make_aware(datetime_class.combine(start, time_min))
        end_datetime = timezone.make_aware(datetime_class.combine(end, time_max))
    elif time_filter == 'last_year':
        start = dt_module.date(today.year - 1, 1, 1)
        end = dt_module.date(today.year - 1, 12, 31)
        start_datetime = timezone.make_aware(datetime_class.combine(start, time_min))
        end_datetime = timezone.make_aware(datetime_class.combine(end, time_max))
    else:
        start_str = request.GET.get('custom_start')
        end_str = request.GET.get('custom_end')
        start = parse_date(start_str) if start_str else today.replace(day=1)
        end = parse_date(end_str) if end_str else today
        start_datetime = timezone.make_aware(datetime_class.combine(start, time_min))
        end_datetime = timezone.make_aware(datetime_class.combine(end, time_max))
        time_filter = 'custom'
        
    return start, end, start_datetime, end_datetime, time_filter

def calculate_trend(current, previous):
    """Calculate percentage trend between current and previous period."""
    curr = Decimal(str(current or 0))
    prev = Decimal(str(previous or 0))
    if prev == Decimal('0'):
        return 100.0 if curr > Decimal('0') else 0.0
    trend = ((curr - prev) / prev) * Decimal('100.0')
    return float(round(trend, 1))

def _apply_report_filters(request, queryset, date_field):
    """Applies date range, custom overrides (month, year), status, category, customer type, and payment method filters."""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    
    # Detect if date_field is datetime
    is_datetime = False
    if date_field in ('order_date', 'created_at', 'updated_at', 'date_joined', 'user__date_joined'):
        is_datetime = True
        
    if is_datetime:
        queryset = queryset.filter(**{f"{date_field}__range": [start_dt, end_dt]})
    else:
        queryset = queryset.filter(**{f"{date_field}__range": [start_date, end_date]})
        
    # Year & Month overrides
    year = request.GET.get('year')
    month = request.GET.get('month')
    if year:
        queryset = queryset.filter(**{f"{date_field}__year": year})
    if month:
        queryset = queryset.filter(**{f"{date_field}__month": month})
        
    # Booking Status
    status = request.GET.get('status')
    if status and hasattr(queryset.model, 'status'):
        queryset = queryset.filter(status=status)
        
    # Room Category
    room_category = request.GET.get('room_category')
    if room_category:
        if hasattr(queryset.model, 'room'):
            queryset = queryset.filter(room__room_type=room_category)
            
    # Customer Type (Registered vs Guest)
    customer_type = request.GET.get('customer_type')
    if customer_type:
        if hasattr(queryset.model, 'customer'):
            if customer_type == 'Registered':
                queryset = queryset.filter(customer__isnull=False)
            elif customer_type == 'Guest':
                queryset = queryset.filter(customer__isnull=True)
                
    # Payment Method
    payment_method = request.GET.get('payment_method')
    if payment_method:
        if hasattr(queryset.model, 'payment_method'):
            queryset = queryset.filter(payment_method=payment_method)
            
    return queryset

def _apply_non_date_filters(request, queryset):
    """Applies status, category, customer type, and payment method filters without date slicing."""
    # Booking Status
    status = request.GET.get('status')
    if status and hasattr(queryset.model, 'status'):
        queryset = queryset.filter(status=status)
        
    # Room Category
    room_category = request.GET.get('room_category')
    if room_category:
        if hasattr(queryset.model, 'room'):
            queryset = queryset.filter(room__room_type=room_category)
            
    # Customer Type (Registered vs Guest)
    customer_type = request.GET.get('customer_type')
    if customer_type:
        if hasattr(queryset.model, 'customer'):
            if customer_type == 'Registered':
                queryset = queryset.filter(customer__isnull=False)
            elif customer_type == 'Guest':
                queryset = queryset.filter(customer__isnull=True)
                
    # Payment Method
    payment_method = request.GET.get('payment_method')
    if payment_method:
        if hasattr(queryset.model, 'payment_method'):
            queryset = queryset.filter(payment_method=payment_method)
            
    return queryset



def get_cancellation_metrics(queryset, total_field='final_amount', is_order=False, is_activity=False):
    """Calculate standard cancellation metrics for a queryset."""
    total_count = queryset.count()
    cancelled_qs = queryset.filter(status='Cancelled')
    cancelled_count = cancelled_qs.count()
    rate = round((cancelled_count / total_count * 100), 1) if total_count > 0 else 0.0
    
    if is_activity:
        revenue_lost = cancelled_qs.aggregate(s=Sum('activity__price'))['s'] or Decimal('0.00')
    elif is_order:
        revenue_lost = cancelled_qs.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    else:
        revenue_lost = cancelled_qs.aggregate(s=Sum(total_field))['s'] or Decimal('0.00')
        
    return {
        'total': total_count,
        'cancelled': cancelled_count,
        'rate': rate,
        'revenue_lost': revenue_lost
    }

# ==========================================
# 2. REPORTS OVERALL DASHBOARD
# ==========================================

@_lr
def reports_overall_dashboard(request):
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)

    # Base querysets dynamically filtered
    room_bookings = _apply_report_filters(request, RoomBooking.objects.all(), 'check_in')
    event_bookings = _apply_report_filters(request, EventBooking.objects.all(), 'start_date')
    table_reservations = _apply_report_filters(request, TableReservation.objects.all(), 'reservation_date')
    orders = _apply_report_filters(request, Order.objects.all(), 'order_date')
    activity_bookings = _apply_report_filters(request, ActivityBooking.objects.all(), 'session__session_date')
    package_bookings = event_bookings.filter(package__isnull=False)


    # Confirmed lists
    confirmed_rooms = room_bookings.exclude(status='Cancelled')
    confirmed_events = event_bookings.exclude(status='Cancelled')
    confirmed_tables = table_reservations.exclude(status='Cancelled')
    confirmed_orders = orders.exclude(status='Cancelled')
    confirmed_activities = activity_bookings.filter(status='Booked')
    confirmed_packages = package_bookings.exclude(status='Cancelled')

    # Revenue
    room_rev = confirmed_rooms.aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    event_rev = confirmed_events.aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    table_rev = confirmed_tables.aggregate(s=Sum('advance_amount'))['s'] or Decimal('0.00')
    order_rev = confirmed_orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    activity_rev = confirmed_activities.aggregate(s=Sum('activity__price'))['s'] or Decimal('0.00')
    package_rev = confirmed_packages.aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    curr_total_rev = room_rev + event_rev + table_rev + order_rev + activity_rev

    # Bookings count
    curr_bookings = room_bookings.count()
    total_bookings = room_bookings.count() + event_bookings.count() + table_reservations.count() + orders.count()

    # Customer Stats dynamically filtered
    total_customers = _apply_non_date_filters(request, Customer.objects.all()).count()
    new_customers = _apply_report_filters(request, Customer.objects.all(), 'user__date_joined').count()
    returning_customers = _apply_non_date_filters(request, Customer.objects.filter(user__date_joined__lt=start_dt)).count()


    # Occupancy Rate
    total_rooms_count = Room.objects.count() or 1
    occupied_rooms_count = confirmed_rooms.values('room').distinct().count()
    occ_rate = round((occupied_rooms_count / total_rooms_count) * 100, 1)

    # cancellation rate
    all_booked = room_bookings.count() + event_bookings.count() + table_reservations.count() + orders.count()
    all_cancelled = (room_bookings.filter(status='Cancelled').count() + 
                     event_bookings.filter(status='Cancelled').count() + 
                     table_reservations.filter(status='Cancelled').count() + 
                     orders.filter(status='Cancelled').count())
    cancel_rate = round((all_cancelled / all_booked * 100), 1) if all_booked > 0 else 0.0

    # Trend comparison (previous period)
    period_days = (end_date - start_date).days + 1
    prev_start_date = start_date - timedelta(days=period_days)
    prev_end_date = start_date - timedelta(days=1)
    prev_start_dt = timezone.make_aware(datetime.datetime.combine(prev_start_date, datetime.time.min))
    prev_end_dt = timezone.make_aware(datetime.datetime.combine(prev_end_date, datetime.time.max))

    prev_room_bookings = _apply_non_date_filters(request, RoomBooking.objects.filter(check_in__range=[prev_start_date, prev_end_date]))
    prev_event_bookings = _apply_non_date_filters(request, EventBooking.objects.filter(start_date__range=[prev_start_date, prev_end_date]))
    prev_table_reservations = _apply_non_date_filters(request, TableReservation.objects.filter(reservation_date__range=[prev_start_date, prev_end_date]))
    prev_orders = _apply_non_date_filters(request, Order.objects.filter(order_date__range=[prev_start_dt, prev_end_dt]))


    prev_room_rev = prev_room_bookings.exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    prev_event_rev = prev_event_bookings.exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    prev_table_rev = prev_table_reservations.exclude(status='Cancelled').aggregate(s=Sum('advance_amount'))['s'] or Decimal('0.00')
    prev_order_rev = prev_orders.exclude(status='Cancelled').aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    prev_total_rev = prev_room_rev + prev_event_rev + prev_table_rev + prev_order_rev

    t_book = calculate_trend(room_bookings.count(), prev_room_bookings.count())
    t_rev = calculate_trend(curr_total_rev, prev_total_rev)
    avg_booking_val = confirmed_rooms.aggregate(avg=Avg('final_amount'))['avg'] or Decimal('0')
    prev_avg_booking_val = prev_room_bookings.exclude(status='Cancelled').aggregate(avg=Avg('final_amount'))['avg'] or Decimal('0')
    t_avg = calculate_trend(avg_booking_val, prev_avg_booking_val)

    # Room Performance
    room_perf_list = list(
        confirmed_rooms.values('room__room_type')
        .annotate(b_count=Count('id'), total_income=Sum('final_amount'))
        .order_by('-total_income')
    )

    # Overview KPI Cards data
    room_canc = room_bookings.filter(status='Cancelled').count()
    event_canc = event_bookings.filter(status='Cancelled').count()
    table_canc = table_reservations.filter(status='Cancelled').count()
    order_canc = orders.filter(status='Cancelled').count()
    activity_canc = activity_bookings.filter(status='Cancelled').count()
    package_canc = package_bookings.filter(status='Cancelled').count()

    room_kpi = {'total_bookings': room_bookings.count(), 'revenue': room_rev, 'occupancy': occ_rate, 'cancellations': room_canc}
    event_kpi = {'total_bookings': event_bookings.count(), 'revenue': event_rev, 'cancellations': event_canc}
    table_kpi = {'total_bookings': table_reservations.count(), 'revenue': table_rev, 'cancellations': table_canc}
    food_kpi = {'total_bookings': orders.count(), 'revenue': order_rev, 'cancellations': order_canc}
    activity_kpi = {'total_bookings': activity_bookings.count(), 'revenue': activity_rev, 'cancellations': activity_canc}
    package_kpi = {'total_bookings': package_bookings.count(), 'revenue': package_rev, 'cancellations': package_canc}
    customer_kpi = {'total_customers': total_customers, 'returning_customers': returning_customers, 'new_customers': new_customers}

    # 1. Revenue Trend (Line Chart)
    from collections import defaultdict
    room_daily_rev = confirmed_rooms.values('check_in').annotate(s=Sum('final_amount'))
    event_daily_rev = confirmed_events.values('start_date').annotate(s=Sum('final_amount'))
    table_daily_rev = confirmed_tables.values('reservation_date').annotate(s=Sum('advance_amount'))
    activity_daily_rev = confirmed_activities.values('session__session_date').annotate(s=Sum('activity__price'))

    rev_by_date = {}
    for r in room_daily_rev:
        d = r['check_in']
        if d: rev_by_date[d] = rev_by_date.get(d, 0) + float(r['s'] or 0)
    for r in event_daily_rev:
        d = r['start_date']
        if d: rev_by_date[d] = rev_by_date.get(d, 0) + float(r['s'] or 0)
    for r in table_daily_rev:
        d = r['reservation_date']
        if d: rev_by_date[d] = rev_by_date.get(d, 0) + float(r['s'] or 0)
    for r in activity_daily_rev:
        d = r['session__session_date']
        if d: rev_by_date[d] = rev_by_date.get(d, 0) + float(r['s'] or 0)

    # Food orders daily revenue aggregated in python
    for o in confirmed_orders:
        if o.order_date:
            d = timezone.localtime(o.order_date).date()
            rev_by_date[d] = rev_by_date.get(d, 0) + float(o.total_amount)

    sorted_dates = sorted(rev_by_date.keys())
    chart_labels = [d.strftime('%d %b') for d in sorted_dates]
    revenue_trend = [rev_by_date[d] for d in sorted_dates]

    # 2. Monthly Booking Trend (Area Chart)
    room_daily_cnt = room_bookings.values('check_in').annotate(c=Count('id'))
    event_daily_cnt = event_bookings.values('start_date').annotate(c=Count('id'))
    table_daily_cnt = table_reservations.values('reservation_date').annotate(c=Count('id'))

    cnt_by_date = {}
    for c in room_daily_cnt:
        d = c['check_in']
        if d: cnt_by_date[d] = cnt_by_date.get(d, 0) + c['c']
    for c in event_daily_cnt:
        d = c['start_date']
        if d: cnt_by_date[d] = cnt_by_date.get(d, 0) + c['c']
    for c in table_daily_cnt:
        d = c['reservation_date']
        if d: cnt_by_date[d] = cnt_by_date.get(d, 0) + c['c']

    # Food orders daily count in python
    for o in orders:
        if o.order_date:
            d = timezone.localtime(o.order_date).date()
            cnt_by_date[d] = cnt_by_date.get(d, 0) + 1

    sorted_dates_cnt = sorted(cnt_by_date.keys())
    booking_trend_labels = [d.strftime('%d %b') for d in sorted_dates_cnt]
    booking_trend_values = [cnt_by_date[d] for d in sorted_dates_cnt]

    # 3. Booking Source Analysis (Bar Chart)
    sources = {}
    for qs in [room_bookings, event_bookings, table_reservations, orders]:
        src_counts = qs.values('booking_source').annotate(c=Count('id'))
        for sc in src_counts:
            src = sc['booking_source'] or 'Walk-in/Other'
            sources[src] = sources.get(src, 0) + sc['c']
    source_labels = list(sources.keys())
    source_values = list(sources.values())

    # 4. Revenue by Section (Horizontal Bar)
    section_labels = ['Rooms', 'Events', 'Tables', 'Food Orders', 'Activities', 'Packages']
    section_values = [float(room_rev), float(event_rev), float(table_rev), float(order_rev), float(activity_rev), float(package_rev)]

    # 5. Cancellation Trend (Line Chart)
    room_canc_daily = room_bookings.filter(status='Cancelled').values('check_in').annotate(c=Count('id'))
    event_canc_daily = event_bookings.filter(status='Cancelled').values('start_date').annotate(c=Count('id'))
    table_canc_daily = table_reservations.filter(status='Cancelled').values('reservation_date').annotate(c=Count('id'))

    canc_by_date = {}
    for c in room_canc_daily:
        d = c['check_in']
        if d: canc_by_date[d] = canc_by_date.get(d, 0) + c['c']
    for c in event_canc_daily:
        d = c['start_date']
        if d: canc_by_date[d] = canc_by_date.get(d, 0) + c['c']
    for c in table_canc_daily:
        d = c['reservation_date']
        if d: canc_by_date[d] = canc_by_date.get(d, 0) + c['c']

    for o in orders.filter(status='Cancelled'):
        if o.order_date:
            d = timezone.localtime(o.order_date).date()
            canc_by_date[d] = canc_by_date.get(d, 0) + 1

    sorted_dates_canc = sorted(canc_by_date.keys())
    canc_trend_labels = [d.strftime('%d %b') for d in sorted_dates_canc]
    canc_trend_values = [canc_by_date[d] for d in sorted_dates_canc]

    # 6. Customer Growth Trend (Line Chart)
    cust_growth_dict = defaultdict(int)
    for c in Customer.objects.filter(user__date_joined__range=[start_dt, end_dt]):
        if c.user.date_joined:
            d = timezone.localtime(c.user.date_joined).date()
            cust_growth_dict[d] += 1
    sorted_cust = sorted(cust_growth_dict.items())
    cust_labels = [d.strftime('%d %b') for d, val in sorted_cust]
    cust_values = [val for d, val in sorted_cust]

    # 7. Occupancy Trend (Area Chart)
    occ_trend = confirmed_rooms.values('check_in').annotate(c=Count('id')).order_by('check_in')

    occ_labels = [item['check_in'].strftime('%d %b') for item in occ_trend if item['check_in']]
    occ_values = [item['c'] for item in occ_trend if item['check_in']]

    # 8. Top Performing Categories (Bar Chart)
    cat_labels = []
    cat_values = []
    if room_perf_list:
        cat_labels.append(room_perf_list[0]['room__room_type'] or 'Rooms')
        cat_values.append(float(room_perf_list[0]['total_income'] or 0))
    # Top event type
    top_event = confirmed_events.values('event_type').annotate(s=Sum('final_amount')).order_by('-s').first()
    if top_event:
        cat_labels.append(top_event['event_type'])
        cat_values.append(float(top_event['s'] or 0))
    # Top food category
    top_food = OrderItem.objects.filter(order__status__in=['Completed', 'Confirmed']).values('food__category').annotate(s=Sum(F('quantity') * F('food__price'))).order_by('-s').first()
    if top_food:
        cat_labels.append(top_food['food__category'])
        cat_values.append(float(top_food['s'] or 0))

    # Weekly Booking Distribution
    weekly_bookings = room_bookings.annotate(day=ExtractWeekDay("check_in")).values("day").annotate(total=Count("id"))
    wb_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    wb_values = [0] * 7
    for item in weekly_bookings:
        if item["day"]:
            wb_values[item["day"] - 1] = item["total"]

    # Department Performance
    department_data = {
        "Event": event_bookings.count(),
        "Table": table_reservations.count(),
        "Room": room_bookings.count(),
        "Food": orders.count(),
    }
    best_department = max(department_data, key=department_data.get) if any(department_data.values()) else "Room"
    worst_department = min(department_data, key=department_data.get) if any(department_data.values()) else "Food"

    # Dynamic Insights
    top_room_cat_name = room_perf_list[0]['room__room_type'] if room_perf_list else "Deluxe"
    rev_direction = "up" if t_rev >= 0 else "down"
    rev_insight = f"Total revenue is ₹{curr_total_rev:,.0f} — {'up' if t_rev >= 0 else 'down'} {abs(t_rev):.1f}% compared to the prior period."
    occ_insight = f"Room occupancy is at {occ_rate}% — {'excellent' if occ_rate >= 80 else 'healthy' if occ_rate >= 60 else 'moderate — consider promotions'}."
    cancel_insight = f"Cancellation rate is {cancel_rate}% — {'⚠️ elevated, review cancellation policy' if cancel_rate > 20 else 'within acceptable thresholds'}."
    insights = [
        rev_insight,
        occ_insight,
        f"{top_room_cat_name} rooms are the highest-revenue hospitality category this period.",
        cancel_insight,
        f"Best performing department: {best_department} — consider cross-selling opportunities.",
    ]

    # Feedback Overview
    feedback_queryset = ContactMessage.objects.filter(inquiry_type='feedback', created_at__range=[start_dt, end_dt])
    total_feedbacks = feedback_queryset.count()
    avg_rating = feedback_queryset.aggregate(avg=Avg('rating'))['avg'] or 0
    rating_5 = feedback_queryset.filter(rating=5).count()
    rating_4 = feedback_queryset.filter(rating=4).count()
    rating_3 = feedback_queryset.filter(rating=3).count()
    rating_2 = feedback_queryset.filter(rating=2).count()
    rating_1 = feedback_queryset.filter(rating=1).count()
    latest_feedbacks = feedback_queryset.order_by('-created_at')[:5]

    context = {
        "time_filter": time_filter,
        "total_customers": total_customers,
        "curr_bookings": curr_bookings,
        "total_bookings": total_bookings,
        "curr_total_rev": curr_total_rev,
        "avg_booking_val": avg_booking_val,
        "occ_rate": occ_rate,
        "cancel_rate": cancel_rate,
        "t_book": t_book,
        "t_rev": t_rev,
        "t_avg": t_avg,

        # KPI details
        "room_kpi": room_kpi,
        "event_kpi": event_kpi,
        "table_kpi": table_kpi,
        "food_kpi": food_kpi,
        "activity_kpi": activity_kpi,
        "package_kpi": package_kpi,
        "customer_kpi": customer_kpi,

        # 8 Charts
        "chart1_labels": json.dumps(chart_labels),
        "chart1_values": json.dumps(revenue_trend),
        "chart2_labels": json.dumps(booking_trend_labels),
        "chart2_values": json.dumps(booking_trend_values),
        "chart3_labels": json.dumps(source_labels),
        "chart3_values": json.dumps(source_values),
        "chart4_labels": json.dumps(section_labels),
        "chart4_values": json.dumps(section_values),
        "chart5_labels": json.dumps(canc_trend_labels),
        "chart5_values": json.dumps(canc_trend_values),
        "chart6_labels": json.dumps(cust_labels),
        "chart6_values": json.dumps(cust_values),
        "chart7_labels": json.dumps(occ_labels),
        "chart7_values": json.dumps(occ_values),
        "chart8_labels": json.dumps(cat_labels),
        "chart8_values": json.dumps(cat_values),

        # Feedbacks
        "total_feedbacks": total_feedbacks,
        "avg_rating": round(avg_rating, 1),
        "rating_5": rating_5,
        "rating_4": rating_4,
        "rating_3": rating_3,
        "rating_2": rating_2,
        "rating_1": rating_1,
        "latest_feedbacks": latest_feedbacks,

        # Insights
        "insights": insights,
        "best_department": best_department,
        "worst_department": worst_department,
        "wb_labels": json.dumps(wb_labels),
        "wb_values": json.dumps(wb_values),
        "dept_labels": json.dumps(list(department_data.keys())),
        "dept_values": json.dumps(list(department_data.values())),
        "room_performance": room_perf_list,
    }

    return render(request, "admin/reports_overall.html", context)

# ==========================================
# 3. DETAILED SECTION VIEWS
# ==========================================

@_lr
def reports_rooms(request):
    """Rooms Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    bookings = _apply_report_filters(request, RoomBooking.objects.all(), 'check_in').select_related('room').order_by('-check_in')

    # Base calculations
    total_bookings = bookings.count()
    cancelled_bookings = bookings.filter(status='Cancelled').count()
    completed_bookings = bookings.filter(status='Completed').count()
    confirmed_bookings = bookings.exclude(status='Cancelled')
    revenue = confirmed_bookings.aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    revenue_lost = bookings.filter(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    total_rooms = Room.objects.count() or 1
    occupied_rooms = confirmed_bookings.values('room').distinct().count()
    occupancy_rate = round((occupied_rooms / total_rooms) * 100, 1)

    # 1. Occupancy Trend (Area)
    occ_trend = confirmed_bookings.values('check_in').annotate(c=Count('id')).order_by('check_in')
    occ_labels = [item['check_in'].strftime('%d %b') for item in occ_trend if item['check_in']]
    occ_values = [item['c'] for item in occ_trend if item['check_in']]

    # 2. Booking Trend (Bar)
    booking_trend = bookings.values('check_in').annotate(c=Count('id')).order_by('check_in')
    booking_labels = [item['check_in'].strftime('%d %b') for item in booking_trend if item['check_in']]
    booking_values = [item['c'] for item in booking_trend if item['check_in']]

    # 3. Room Category Performance (Horizontal Bar)
    room_perf = confirmed_bookings.values('room__room_type').annotate(c=Count('id'), r=Sum('final_amount')).order_by('-c')
    room_labels = [item['room__room_type'] or 'Standard' for item in room_perf]
    room_values = [item['c'] for item in room_perf]

    # 4. Revenue Trend (Line)
    rev_trend = confirmed_bookings.values('check_in').annotate(s=Sum('final_amount')).order_by('check_in')
    rev_labels = [item['check_in'].strftime('%d %b') for item in rev_trend if item['check_in']]
    rev_values = [float(item['s'] or 0) for item in rev_trend if item['check_in']]

    # 5. Cancellation Trend (Line)
    canc_trend = bookings.filter(status='Cancelled').values('check_in').annotate(c=Count('id')).order_by('check_in')
    canc_labels = [item['check_in'].strftime('%d %b') for item in canc_trend if item['check_in']]
    canc_values = [item['c'] for item in canc_trend if item['check_in']]

    # 6. Room Utilization Analysis (Stacked Bar)
    # Online vs Offline sources by Room Type
    room_types = list(Room.objects.values_list('room_type', flat=True).distinct())
    online_data = []
    offline_data = []
    for rt in room_types:
        online_data.append(confirmed_bookings.filter(room__room_type=rt, booking_source='Online').count())
        offline_data.append(confirmed_bookings.filter(room__room_type=rt, booking_source='Offline').count())

    # Dynamic Insights
    top_category = room_labels[0] if room_labels else "N/A"
    insights = [
        f"Room occupancy has stabilized at {occupancy_rate}%.",
        f"Deluxe rooms generated highest revenue this period.",
        f"Cancellation rate for rooms is at {cancellation_rate}%."
    ]

    context = {
        'time_filter': time_filter,
        'records': bookings[:25],  # paginated or limited
        'total_count': total_bookings,
        'completed_count': completed_bookings,
        'cancelled_count': cancelled_bookings,
        'cancellation_rate': cancellation_rate,
        'total_rev': revenue,
        'revenue_lost': revenue_lost,
        'occupancy_rate': occupancy_rate,
        'insights': insights,

        # Chart JSONs
        'chart_occ_labels': json.dumps(occ_labels),
        'chart_occ_values': json.dumps(occ_values),
        'chart_book_labels': json.dumps(booking_labels),
        'chart_book_values': json.dumps(booking_values),
        'chart_room_labels': json.dumps(room_labels),
        'chart_room_values': json.dumps(room_values),
        'chart_rev_labels': json.dumps(rev_labels),
        'chart_rev_values': json.dumps(rev_values),
        'chart_canc_labels': json.dumps(canc_labels),
        'chart_canc_values': json.dumps(canc_values),
        'room_labels_util': json.dumps(room_types),
        'online_data': json.dumps(online_data),
        'offline_data': json.dumps(offline_data),
    }
    return render(request, "admin/sections/reports_rooms.html", context)

@_lr
def reports_events(request):
    """Events Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    bookings = _apply_report_filters(request, EventBooking.objects.all(), 'start_date').select_related('hall', 'package').order_by('-start_date')

    # Calculations
    total_bookings = bookings.count()
    cancelled_bookings = bookings.filter(status='Cancelled').count()
    completed_bookings = bookings.filter(status='Completed').count()
    confirmed_bookings = bookings.exclude(status='Cancelled')
    revenue = confirmed_bookings.aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    revenue_lost = bookings.filter(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    # Charts
    trend = confirmed_bookings.values('start_date').annotate(c=Count('id'), s=Sum('final_amount')).order_by('start_date')
    trend_labels = [item['start_date'].strftime('%d %b') for item in trend if item['start_date']]
    trend_values = [item['c'] for item in trend if item['start_date']]
    rev_values = [float(item['s'] or 0) for item in trend if item['start_date']]

    popular_types = confirmed_bookings.values('event_type').annotate(c=Count('id')).order_by('-c')
    type_labels = [item['event_type'] for item in popular_types]
    type_values = [item['c'] for item in popular_types]

    canc_trend = bookings.filter(status='Cancelled').values('start_date').annotate(c=Count('id')).order_by('start_date')
    canc_labels = [item['start_date'].strftime('%d %b') for item in canc_trend if item['start_date']]
    canc_values = [item['c'] for item in canc_trend if item['start_date']]

    # Package Performance (Stacked Bar)
    pkg_performance = confirmed_bookings.filter(package__isnull=False).values('package__package_name').annotate(c=Count('id'), s=Sum('final_amount')).order_by('-c')
    pkg_labels = [p['package__package_name'] for p in pkg_performance]
    pkg_counts = [p['c'] for p in pkg_performance]

    # Dynamic Insights
    top_event = type_labels[0] if type_labels else "N/A"
    insights = [
        f"Popular event type this period is {top_event}.",
        f"Banquet events generated a total revenue of ₹{revenue:,.2f}.",
        f"Event cancellation rate is stable at {cancellation_rate}%."
    ]

    context = {
        'time_filter': time_filter,
        'records': bookings[:25],
        'total_count': total_bookings,
        'completed_count': completed_bookings,
        'cancelled_count': cancelled_bookings,
        'cancellation_rate': cancellation_rate,
        'total_rev': revenue,
        'revenue_lost': revenue_lost,
        'insights': insights,

        # Chart JSONs
        'chart_trend_labels': json.dumps(trend_labels),
        'chart_trend_values': json.dumps(trend_values),
        'chart_rev_values': json.dumps(rev_values),
        'chart_type_labels': json.dumps(type_labels),
        'chart_type_values': json.dumps(type_values),
        'chart_canc_labels': json.dumps(canc_labels),
        'chart_canc_values': json.dumps(canc_values),
        'pkg_labels': json.dumps(pkg_labels),
        'pkg_counts': json.dumps(pkg_counts),
    }
    return render(request, "admin/sections/reports_events.html", context)

@_lr
def reports_tables(request):
    """Tables Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    reservations = _apply_report_filters(request, TableReservation.objects.all(), 'reservation_date').select_related('table').order_by('-reservation_date')

    # Calculations
    total_bookings = reservations.count()
    cancelled_bookings = reservations.filter(status='Cancelled').count()
    completed_bookings = reservations.filter(status='Completed').count()
    confirmed_bookings = reservations.exclude(status='Cancelled')
    revenue = confirmed_bookings.aggregate(s=Sum('advance_amount'))['s'] or Decimal('0.00')
    revenue_lost = reservations.filter(status='Cancelled').aggregate(s=Sum('advance_amount'))['s'] or Decimal('0.00')
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    # Trend
    trend = confirmed_bookings.values('reservation_date').annotate(c=Count('id')).order_by('reservation_date')
    trend_labels = [item['reservation_date'].strftime('%d %b') for item in trend if item['reservation_date']]
    trend_values = [item['c'] for item in trend if item['reservation_date']]

    # Table Utilization by Location
    util = confirmed_bookings.values('table__location').annotate(c=Count('id')).order_by('-c')
    util_labels = [item['table__location'] or 'Indoor' for item in util]
    util_values = [item['c'] for item in util]

    # Peak Times
    peak_times = confirmed_bookings.annotate(hr=ExtractHour('reservation_time')).values('hr').annotate(c=Count('id')).order_by('hr')
    time_labels = [f"{item['hr']:02d}:00" for item in peak_times]
    time_values = [item['c'] for item in peak_times]

    # Cancellation Trend
    canc_trend = reservations.filter(status='Cancelled').values('reservation_date').annotate(c=Count('id')).order_by('reservation_date')
    canc_labels = [item['reservation_date'].strftime('%d %b') for item in canc_trend if item['reservation_date']]
    canc_values = [item['c'] for item in canc_trend if item['reservation_date']]

    insights = [
        f"Peak table reservation times are at evening hours.",
        f"Rooftop area remains the most popular location.",
        f"Table reservation cancellation rate is {cancellation_rate}%."
    ]

    context = {
        'time_filter': time_filter,
        'records': reservations[:25],
        'total_count': total_bookings,
        'completed_count': completed_bookings,
        'cancelled_count': cancelled_bookings,
        'cancellation_rate': cancellation_rate,
        'total_rev': revenue,
        'revenue_lost': revenue_lost,
        'insights': insights,

        # Chart JSONs
        'chart_trend_labels': json.dumps(trend_labels),
        'chart_trend_values': json.dumps(trend_values),
        'chart_util_labels': json.dumps(util_labels),
        'chart_util_values': json.dumps(util_values),
        'chart_time_labels': json.dumps(time_labels),
        'chart_time_values': json.dumps(time_values),
        'chart_canc_labels': json.dumps(canc_labels),
        'chart_canc_values': json.dumps(canc_values),
    }
    return render(request, "admin/sections/reports_tables.html", context)

@_lr
def reports_dining(request):
    """Food Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    records = _apply_report_filters(request, Order.objects.all(), 'order_date').order_by('-order_date')

    # Calculations
    total_bookings = records.count()
    cancelled_bookings = records.filter(status='Cancelled').count()
    completed_bookings = records.filter(status='Completed').count()
    confirmed_bookings = records.exclude(status='Cancelled')
    revenue = confirmed_bookings.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    revenue_lost = records.filter(status='Cancelled').aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    # Trend in python
    from collections import defaultdict
    trend_dict = defaultdict(lambda: {'c': 0, 's': Decimal('0.00')})
    for item in confirmed_bookings:
        if item.order_date:
            d = timezone.localtime(item.order_date).date()
            trend_dict[d]['c'] += 1
            trend_dict[d]['s'] += item.total_amount
            
    sorted_trend = sorted(trend_dict.items())
    trend_labels = [d.strftime('%d %b') for d, data in sorted_trend]
    trend_values = [data['c'] for d, data in sorted_trend]
    rev_values = [float(data['s']) for d, data in sorted_trend]

    # Popular categories
    order_items = OrderItem.objects.filter(order__order_date__range=[start_dt, end_dt], order__status__in=['Completed', 'Confirmed'])
    cats = order_items.values('food__category').annotate(c=Sum('quantity')).order_by('-c')
    cat_labels = [c['food__category'] for c in cats]
    cat_values = [c['c'] for c in cats]

    # Top Selling
    top_selling = order_items.values('food__item_name').annotate(c=Sum('quantity')).order_by('-c')[:10]
    top_labels = [t['food__item_name'] for t in top_selling]
    top_values = [t['c'] for t in top_selling]

    # Cancellation Trend in python
    canc_dict = defaultdict(int)
    for item in records.filter(status='Cancelled'):
        if item.order_date:
            d = timezone.localtime(item.order_date).date()
            canc_dict[d] += 1
            
    sorted_canc = sorted(canc_dict.items())
    canc_labels = [d.strftime('%d %b') for d, c in sorted_canc]
    canc_values = [c for d, c in sorted_canc]

    insights = [
        f"Top selling food item is {top_labels[0] if top_labels else 'N/A'}.",
        f"Dining services generated ₹{revenue:,.2f} this period.",
        f"Food order cancellation rate stands at {cancellation_rate}%."
    ]

    context = {
        'time_filter': time_filter,
        'records': records[:25],
        'total_count': total_bookings,
        'completed_count': completed_bookings,
        'cancelled_count': cancelled_bookings,
        'cancellation_rate': cancellation_rate,
        'total_rev': revenue,
        'revenue_lost': revenue_lost,
        'insights': insights,

        # Charts
        'chart_trend_labels': json.dumps(trend_labels),
        'chart_trend_values': json.dumps(trend_values),
        'chart_rev_values': json.dumps(rev_values),
        'chart_cat_labels': json.dumps(cat_labels),
        'chart_cat_values': json.dumps(cat_values),
        'chart_top_labels': json.dumps(top_labels),
        'chart_top_values': json.dumps(top_values),
        'chart_canc_labels': json.dumps(canc_labels),
        'chart_canc_values': json.dumps(canc_values),
    }
    return render(request, "admin/sections/reports_dining.html", context)

@_lr
def reports_activities(request):
    """Activities Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    bookings = _apply_report_filters(request, ActivityBooking.objects.all(), 'session__session_date').select_related('activity', 'session').order_by('-created_at')

    # Calculations
    total_bookings = bookings.count()
    cancelled_bookings = bookings.filter(status='Cancelled').count()
    completed_bookings = bookings.filter(status='Booked').count()  # Treat Booked as confirmed
    revenue = bookings.filter(status='Booked').aggregate(s=Sum('activity__price'))['s'] or Decimal('0.00')
    revenue_lost = bookings.filter(status='Cancelled').aggregate(s=Sum('activity__price'))['s'] or Decimal('0.00')
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    # Trend
    trend = bookings.filter(status='Booked').values('session__session_date').annotate(c=Count('id'), s=Sum('activity__price')).order_by('session__session_date')
    trend_labels = [item['session__session_date'].strftime('%d %b') for item in trend if item['session__session_date']]
    trend_values = [item['c'] for item in trend if item['session__session_date']]
    rev_values = [float(item['s'] or 0) for item in trend if item['session__session_date']]

    # Popular activities
    popular = bookings.filter(status='Booked').values('activity__activity_name').annotate(c=Count('id')).order_by('-c')
    pop_labels = [item['activity__activity_name'] for item in popular]
    pop_values = [item['c'] for item in popular]

    # Cancellation Trend
    canc_trend = bookings.filter(status='Cancelled').values('session__session_date').annotate(c=Count('id')).order_by('session__session_date')
    canc_labels = [item['session__session_date'].strftime('%d %b') for item in canc_trend if item['session__session_date']]
    canc_values = [item['c'] for item in canc_trend if item['session__session_date']]

    insights = [
        f"Spa massage and yoga activities generate steady guest engagement.",
        f"Activity booking revenue is at ₹{revenue:,.2f}.",
        f"Activity booking cancellation rate is {cancellation_rate}%."
    ]

    context = {
        'time_filter': time_filter,
        'records': bookings[:25],
        'total_count': total_bookings,
        'completed_count': completed_bookings,
        'cancelled_count': cancelled_bookings,
        'cancellation_rate': cancellation_rate,
        'total_rev': revenue,
        'revenue_lost': revenue_lost,
        'insights': insights,

        # Charts
        'chart_trend_labels': json.dumps(trend_labels),
        'chart_trend_values': json.dumps(trend_values),
        'chart_rev_values': json.dumps(rev_values),
        'chart_pop_labels': json.dumps(pop_labels),
        'chart_pop_values': json.dumps(pop_values),
        'chart_canc_labels': json.dumps(canc_labels),
        'chart_canc_values': json.dumps(canc_values),
    }
    return render(request, "admin/sections/reports_activities.html", context)

@_lr
def reports_packages(request):
    """Packages Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    bookings = _apply_report_filters(request, EventBooking.objects.all(), 'start_date').filter(package__isnull=False).select_related('package', 'hall').order_by('-start_date')

    # Calculations
    total_bookings = bookings.count()
    cancelled_bookings = bookings.filter(status='Cancelled').count()
    completed_bookings = bookings.filter(status='Completed').count()
    confirmed_bookings = bookings.exclude(status='Cancelled')
    revenue = confirmed_bookings.aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    revenue_lost = bookings.filter(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    cancellation_rate = round((cancelled_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0.0

    # Trend
    trend = confirmed_bookings.values('start_date').annotate(c=Count('id'), s=Sum('final_amount')).order_by('start_date')
    trend_labels = [item['start_date'].strftime('%d %b') for item in trend if item['start_date']]
    trend_values = [item['c'] for item in trend if item['start_date']]
    rev_values = [float(item['s'] or 0) for item in trend if item['start_date']]

    # Popularity
    popular = bookings.values('package__package_name').annotate(c=Count('id')).order_by('-c')
    pop_labels = [item['package__package_name'] or 'Standard Package' for item in popular]
    pop_values = [item['c'] for item in popular]

    # Cancellation Trend
    canc_trend = bookings.filter(status='Cancelled').values('start_date').annotate(c=Count('id')).order_by('start_date')
    canc_labels = [item['start_date'].strftime('%d %b') for item in canc_trend if item['start_date']]
    canc_values = [item['c'] for item in canc_trend if item['start_date']]

    insights = [
        f"Special packages outperform custom banquet setups in profitability.",
        f"Package sales contributed ₹{revenue:,.2f} to event revenues.",
        f"Cancellation rate for packages is stable at {cancellation_rate}%."
    ]

    context = {
        'time_filter': time_filter,
        'records': bookings[:25],
        'total_count': total_bookings,
        'completed_count': completed_bookings,
        'cancelled_count': cancelled_bookings,
        'cancellation_rate': cancellation_rate,
        'total_rev': revenue,
        'revenue_lost': revenue_lost,
        'insights': insights,

        # Charts
        'chart_trend_labels': json.dumps(trend_labels),
        'chart_trend_values': json.dumps(trend_values),
        'chart_rev_values': json.dumps(rev_values),
        'chart_pop_labels': json.dumps(pop_labels),
        'chart_pop_values': json.dumps(pop_values),
        'chart_canc_labels': json.dumps(canc_labels),
        'chart_canc_values': json.dumps(canc_values),
    }
    return render(request, "admin/sections/reports_packages.html", context)

@_lr
def reports_customers(request):
    """Customer Report Details"""
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    records_qs = _apply_report_filters(request, Customer.objects.all(), 'user__date_joined').order_by('-user__date_joined')

    # Calculations
    total_customers = _apply_non_date_filters(request, Customer.objects.all()).count()
    new_customers = records_qs.count()
    returning_customers = _apply_non_date_filters(request, Customer.objects.filter(user__date_joined__lt=start_dt)).count()
    retention_rate = round((returning_customers / total_customers * 100), 1) if total_customers > 0 else 0.0
    returning_pct = retention_rate

    # Customer Growth (chart_labels / chart_values expected by template) in python
    from collections import defaultdict
    growth_dict = defaultdict(int)
    for c in records_qs:
        if c.user.date_joined:
            d = timezone.localtime(c.user.date_joined).date()
            growth_dict[d] += 1
    sorted_growth = sorted(growth_dict.items())
    growth_labels = [d.strftime('%d %b') for d, val in sorted_growth]
    growth_values = [val for d, val in sorted_growth]

    # Booking Frequency (freq_labels / freq_values expected by template)
    freq = _apply_non_date_filters(request, RoomBooking.objects.filter(customer__isnull=False)).values('customer').annotate(c=Count('id')).values('c').annotate(count=Count('customer')).order_by('c')
    freq_labels_list = [f"{item['c']} Booking(s)" for item in freq]
    freq_values_list = [item['count'] for item in freq]

    # Revenue by segment (registered vs walk-in)
    registered_rev = RoomBooking.objects.filter(customer__isnull=False, status__in=['Confirmed', 'Completed']).aggregate(s=Sum('final_amount'))['s'] or Decimal('0')
    walkin_rev = RoomBooking.objects.filter(customer__isnull=True, status__in=['Confirmed', 'Completed']).aggregate(s=Sum('final_amount'))['s'] or Decimal('0')
    segment_data = [('Registered Guests', float(registered_rev)), ('Walk-in Guests', float(walkin_rev))]
    segment_labels = json.dumps([s[0] for s in segment_data])
    segment_values = json.dumps([s[1] for s in segment_data])
    valuable_segment = 'Registered Guests' if registered_rev >= walkin_rev else 'Walk-in Guests'

    # Repeat booking rate (customers who booked more than once)
    repeat_bookers = RoomBooking.objects.filter(customer__isnull=False).values('customer').annotate(c=Count('id')).filter(c__gt=1).count()
    all_bookers = RoomBooking.objects.filter(customer__isnull=False).values('customer').distinct().count()
    repeat_booking_rate = round((repeat_bookers / all_bookers * 100), 1) if all_bookers > 0 else 0.0

    # Peak acquisition month
    peak_month_qs = Customer.objects.annotate(m=ExtractMonth('user__date_joined')).values('m').annotate(c=Count('id')).order_by('-c').first()
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    peak_acq_month = month_names[peak_month_qs['m']] if peak_month_qs and peak_month_qs.get('m') else 'N/A'

    # Enriched customer records for the template table
    enriched_records = []
    for cust in records_qs[:25]:
        booking_count = RoomBooking.objects.filter(customer=cust).count()
        total_spend = RoomBooking.objects.filter(customer=cust, status__in=['Confirmed', 'Completed']).aggregate(s=Sum('final_amount'))['s'] or Decimal('0')
        has_loyalty = LoyaltyTransaction.objects.filter(customer=cust).exists()
        enriched_records.append({
            'name': cust.user.get_full_name() or cust.user.username,
            'email': cust.user.email,
            'nationality': getattr(cust, 'nationality', '\u2014'),
            'joined': cust.user.date_joined,
            'booking_count': booking_count,
            'total_spend': total_spend,
            'is_loyalty': has_loyalty,
        })

    insights = [
        f"Registered guests generated \u20b9{float(registered_rev):,.0f} in room revenue this period.",
        f"New customer acquisitions this period: {new_customers}.",
        f"Repeat booking rate stands at {repeat_booking_rate}% — indicating strong guest loyalty.",
        f"Peak customer acquisition month is {peak_acq_month}.",
    ]

    # --- Comparison calculations (Registered vs Guest) ---
    total_reg_customers = Customer.objects.count()

    # Get unique unregistered guest counts across RoomBooking, EventBooking, TableReservation
    room_guest_emails = set(RoomBooking.objects.filter(customer__isnull=True).exclude(guest_email__isnull=True).values_list('guest_email', flat=True).distinct())
    event_guest_emails = set(EventBooking.objects.filter(customer__isnull=True).exclude(guest_email__isnull=True).values_list('guest_email', flat=True).distinct())
    table_guest_emails = set(TableReservation.objects.filter(customer__isnull=True).exclude(email__isnull=True).values_list('email', flat=True).distinct())

    room_guest_phones = set(RoomBooking.objects.filter(customer__isnull=True).exclude(guest_phone__isnull=True).values_list('guest_phone', flat=True).distinct())
    event_guest_phones = set(EventBooking.objects.filter(customer__isnull=True).exclude(guest_phone__isnull=True).values_list('guest_phone', flat=True).distinct())
    table_guest_phones = set(TableReservation.objects.filter(customer__isnull=True).exclude(phone__isnull=True).values_list('phone', flat=True).distinct())

    guest_emails_set = room_guest_emails.union(event_guest_emails).union(table_guest_emails)
    guest_phones_set = room_guest_phones.union(event_guest_phones).union(table_guest_phones)
    total_guest_customers = len(guest_emails_set.union(guest_phones_set))

    if total_guest_customers == 0:
        total_guest_customers = RoomBooking.objects.filter(customer__isnull=True).count() + EventBooking.objects.filter(customer__isnull=True).count()

    # Room bookings
    reg_room_bookings = RoomBooking.objects.filter(check_in__range=[start_date, end_date], customer__isnull=False).count()
    gst_room_bookings = RoomBooking.objects.filter(check_in__range=[start_date, end_date], customer__isnull=True).count()
    total_room_bookings = reg_room_bookings + gst_room_bookings

    reg_room_bookings_pct = round((reg_room_bookings / total_room_bookings) * 100, 1) if total_room_bookings > 0 else 0.0
    gst_room_bookings_pct = round((gst_room_bookings / total_room_bookings) * 100, 1) if total_room_bookings > 0 else 0.0

    # Event bookings
    reg_event_bookings = EventBooking.objects.filter(start_date__range=[start_date, end_date], customer__isnull=False).count()
    gst_event_bookings = EventBooking.objects.filter(start_date__range=[start_date, end_date], customer__isnull=True).count()
    total_event_bookings = reg_event_bookings + gst_event_bookings

    reg_event_bookings_pct = round((reg_event_bookings / total_event_bookings) * 100, 1) if total_event_bookings > 0 else 0.0
    gst_event_bookings_pct = round((gst_event_bookings / total_event_bookings) * 100, 1) if total_event_bookings > 0 else 0.0

    # Offline bookings
    reg_room_off = RoomBooking.objects.filter(check_in__range=[start_date, end_date], customer__isnull=False, booking_source='Offline').count()
    gst_room_off = RoomBooking.objects.filter(check_in__range=[start_date, end_date], customer__isnull=True, booking_source='Offline').count()

    reg_event_off = EventBooking.objects.filter(start_date__range=[start_date, end_date], customer__isnull=False, booking_source='Offline').count()
    gst_event_off = EventBooking.objects.filter(start_date__range=[start_date, end_date], customer__isnull=True, booking_source='Offline').count()

    reg_table_off = TableReservation.objects.filter(reservation_date__range=[start_date, end_date], customer__isnull=False, booking_source='Offline').count()
    gst_table_off = TableReservation.objects.filter(reservation_date__range=[start_date, end_date], customer__isnull=True, booking_source='Offline').count()

    reg_offline_bookings = reg_room_off + reg_event_off + reg_table_off
    gst_offline_bookings = gst_room_off + gst_event_off + gst_table_off
    total_offline_bookings = reg_offline_bookings + gst_offline_bookings

    reg_offline_bookings_pct = round((reg_offline_bookings / total_offline_bookings) * 100, 1) if total_offline_bookings > 0 else 0.0
    gst_offline_bookings_pct = round((gst_offline_bookings / total_offline_bookings) * 100, 1) if total_offline_bookings > 0 else 0.0

    # Revenue
    reg_room_rev_period = RoomBooking.objects.filter(check_in__range=[start_date, end_date], customer__isnull=False).exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0')
    gst_room_rev_period = RoomBooking.objects.filter(check_in__range=[start_date, end_date], customer__isnull=True).exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0')

    reg_event_rev_period = EventBooking.objects.filter(start_date__range=[start_date, end_date], customer__isnull=False).exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0')
    gst_event_rev_period = EventBooking.objects.filter(start_date__range=[start_date, end_date], customer__isnull=True).exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0')

    reg_table_rev_period = TableReservation.objects.filter(reservation_date__range=[start_date, end_date], customer__isnull=False).exclude(status='Cancelled').aggregate(s=Sum('advance_amount'))['s'] or Decimal('0')
    gst_table_rev_period = TableReservation.objects.filter(reservation_date__range=[start_date, end_date], customer__isnull=True).exclude(status='Cancelled').aggregate(s=Sum('advance_amount'))['s'] or Decimal('0')

    reg_revenue = reg_room_rev_period + reg_event_rev_period + reg_table_rev_period
    gst_revenue = gst_room_rev_period + gst_event_rev_period + gst_table_rev_period
    total_revenue_period = reg_revenue + gst_revenue

    reg_revenue_pct = round((reg_revenue / total_revenue_period) * 100, 1) if total_revenue_period > 0 else 0.0
    gst_revenue_pct = round((gst_revenue / total_revenue_period) * 100, 1) if total_revenue_period > 0 else 0.0

    context = {
        'time_filter': time_filter,
        'records': enriched_records,
        'total_count': total_customers,
        'new_count': new_customers,
        'returning_customers': returning_customers,
        'retention_rate': retention_rate,
        'returning_pct': returning_pct,
        'repeat_booking_rate': repeat_booking_rate,
        'valuable_segment': valuable_segment,
        'peak_acq_month': peak_acq_month,
        'segment_data': segment_data,
        'segment_labels': segment_labels,
        'segment_values': segment_values,
        'insights': insights,

        # Chart variable names as expected by the customers template
        'chart_labels': json.dumps(growth_labels),
        'chart_values': json.dumps(growth_values),
        'freq_labels': json.dumps(freq_labels_list),
        'freq_values': json.dumps(freq_values_list),

        # Registered vs Guest comparison variables
        'total_reg_customers': total_reg_customers,
        'total_guest_customers': total_guest_customers,
        'reg_cust_pct': round((total_reg_customers / (total_reg_customers + total_guest_customers) * 100), 1) if (total_reg_customers + total_guest_customers) > 0 else 0.0,
        'gst_cust_pct': round((total_guest_customers / (total_reg_customers + total_guest_customers) * 100), 1) if (total_reg_customers + total_guest_customers) > 0 else 0.0,

        'reg_room_bookings': reg_room_bookings,
        'gst_room_bookings': gst_room_bookings,
        'total_room_bookings': total_room_bookings,
        'reg_room_bookings_pct': reg_room_bookings_pct,
        'gst_room_bookings_pct': gst_room_bookings_pct,

        'reg_event_bookings': reg_event_bookings,
        'gst_event_bookings': gst_event_bookings,
        'total_event_bookings': total_event_bookings,
        'reg_event_bookings_pct': reg_event_bookings_pct,
        'gst_event_bookings_pct': gst_event_bookings_pct,

        'reg_offline_bookings': reg_offline_bookings,
        'gst_offline_bookings': gst_offline_bookings,
        'total_offline_bookings': total_offline_bookings,
        'reg_offline_bookings_pct': reg_offline_bookings_pct,
        'gst_offline_bookings_pct': gst_offline_bookings_pct,

        'reg_revenue': float(reg_revenue),
        'gst_revenue': float(gst_revenue),
        'total_revenue_period': float(total_revenue_period),
        'reg_revenue_pct': reg_revenue_pct,
        'gst_revenue_pct': gst_revenue_pct,

        # Chart serializations
        'chart_comp_labels': json.dumps(['Room Bookings', 'Event Bookings', 'Offline Bookings']),
        'chart_comp_reg_values': json.dumps([reg_room_bookings, reg_event_bookings, reg_offline_bookings]),
        'chart_comp_guest_values': json.dumps([gst_room_bookings, gst_event_bookings, gst_offline_bookings]),
        'chart_comp_rev_labels': json.dumps(['Registered Customers', 'Guest Customers']),
        'chart_comp_rev_values': json.dumps([float(reg_revenue), float(gst_revenue)]),
    }
    return render(request, "admin/sections/reports_customers.html", context)

@_lr
def reports_section_detail(request, section_name):
    """Fallback router and page renderer for reports detailed sections."""
    if section_name == 'reservations':
        return reports_rooms(request)
    elif section_name == 'dining':
        return reports_dining(request)
    elif section_name == 'events':
        return reports_events(request)
    elif section_name == 'tables':
        return reports_tables(request)
    elif section_name == 'activities':
        return reports_activities(request)
    elif section_name == 'packages':
        return reports_packages(request)
    elif section_name == 'customers':
        return reports_customers(request)
    else:
        # Default fallback context for generic or other sections
        start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
        context = {
            'section_name': section_name,
            'time_filter': time_filter,
            'total_count': 0,
            'completed_count': 0,
            'cancelled_count': 0,
            'total_rev': Decimal('0.00'),
            'cancellation_rate': 0.0,
            'insights': ["No active telemetry detected for this section. Configure database hooks."]
        }
        return render(request, 'admin/sections/reports_generic.html', context)

# ==========================================
# 4. EXPORT FUNCTIONS (CSV/PDF)
# ==========================================

@_lr
def generate_advanced_pdf_report(request):
    """Assembles a comprehensive, modern business intelligence document package."""
    section_scope = request.GET.get('section', 'overall')
    start_date, end_date, start_datetime, end_datetime, time_filter = _get_report_dates(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="StayZen_{section_scope.title()}_Report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', fontName='Helvetica-Bold', fontSize=24, leading=30, 
        textColor=colors.HexColor("#111827"), spaceAfter=6
    )
    meta_style = ParagraphStyle(
        'Meta', fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#6B7280"), spaceAfter=35
    )
    h1_style = ParagraphStyle(
        'H1', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#1F2937"), 
        spaceBefore=25, spaceAfter=12
    )
    insight_text_style = ParagraphStyle(
        'InsightText', fontName='Helvetica', fontSize=9.5, leading=15, textColor=colors.HexColor("#1E3A8A")
    )

    def get_modern_table_style():
        return TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F2937")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('TOPPADDING', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8.5),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.HexColor("#374151")),
            ('TOPPADDING', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,1), (-1,-1), 8),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ])

    def create_insight_box(text):
        p = Paragraph(f"<b>💡 Operational Insight:</b> {text}", insight_text_style)
        t = Table([[p]], colWidths=['100%'])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
            ('LINEABOVE', (0,0), (-1,-1), 1.5, colors.HexColor("#BFDBFE")),
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor("#BFDBFE")),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
            ('LEFTPADDING', (0,0), (-1,-1), 14),
            ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ]))
        return t

    story.append(Paragraph("StayZen Hotel Management System<br/>Comprehensive Report", title_style))
    story.append(Paragraph(f"<b>Scope:</b> {section_scope.upper()} | <b>Timeline:</b> {start_date} to {end_date}", meta_style))

    if section_scope in ['overall', 'reservations']:
        story.append(Paragraph("1. Reservation & Front-Desk Performance", h1_style))
        bookings = RoomBooking.objects.filter(check_in__gte=start_date, check_in__lte=end_date).exclude(status__in=['Pending', 'Cancelled']).select_related('room').order_by('-check_in')

        total_b = bookings.count()
        top_room = bookings.values('room__room_type').annotate(c=Count('id')).order_by('-c').first()
        top_room_str = f" The most popular room category was <b>{top_room['room__room_type']}</b>." if top_room else ""

        table_data = [['Res ID', 'Guest Name', 'Room', 'Check In', 'Check Out', 'Amount', 'Status']]
        for b in bookings[:10]:
            table_data.append([f"RES#{b.id}", str(b.guest_name or 'Walk-in')[:15], b.room.room_number, b.check_in.strftime('%Y-%m-%d'), b.check_out.strftime('%Y-%m-%d'), f"INR {b.final_amount}", b.status])

        t = Table(table_data, colWidths=[60, 110, 50, 75, 75, 70, 70])
        t.setStyle(get_modern_table_style())
        story.append(t)
        story.append(Spacer(1, 15))
        story.append(create_insight_box(f"Recorded {total_b} confirmed/completed room bookings.{top_room_str}"))

    if section_scope == 'overall': story.append(PageBreak())

    if section_scope in ['overall', 'dining']:
        story.append(Paragraph("2. Point of Sale (POS) Restaurant Analytics", h1_style))
        orders = Order.objects.filter(order_date__gte=start_datetime, order_date__lte=end_datetime).exclude(status__in=['Pending', 'Cancelled']).order_by('-order_date')
        total_f_rev = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        top_food = OrderItem.objects.filter(order__in=orders).values('food__item_name').annotate(qty=Sum('quantity')).order_by('-qty').first()
        top_food_str = f" The highest velocity culinary item was <b>{top_food['food__item_name']}</b> (ordered {top_food['qty']} times)." if top_food else ""

        table_data = [['Order ID', 'Customer Name', 'Service Type', 'Subtotal', 'Tax', 'Total']]
        for o in orders[:10]:
            table_data.append([f"ORD#{o.id}", str(o.customer_name or 'Walk-in')[:15], o.order_type, f"INR {o.subtotal_amount}", f"INR {o.gst_amount}", f"INR {o.total_amount}"])

        t = Table(table_data, colWidths=[70, 130, 90, 75, 70, 75])
        t.setStyle(get_modern_table_style())
        story.append(t)
        story.append(Spacer(1, 15))
        story.append(create_insight_box(f"F&B operations generated <b>INR {total_f_rev:,.2f}</b>.{top_food_str}"))

    if section_scope == 'overall': story.append(PageBreak())

    if section_scope in ['overall', 'events']:
        story.append(Paragraph("3. Banquet & Event Space Intelligence", h1_style))
        events = EventBooking.objects.filter(start_date__gte=start_date, start_date__lte=end_date).exclude(status__in=['Pending', 'Cancelled']).select_related('hall').order_by('-start_date')
        total_e_rev = events.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')

        top_hall = events.values('hall__hall_name').annotate(c=Count('id')).order_by('-c').first()
        top_hall_str = f" The most frequently reserved space was <b>{top_hall['hall__hall_name']}</b>." if top_hall else ""

        table_data = [['Event ID', 'Event Name', 'Venue', 'Type', 'Start Date', 'Amount']]
        for e in events[:10]:
            table_data.append([f"EV#{e.id}", str(e.event_name)[:15], e.hall.hall_name, e.event_type, e.start_date.strftime('%Y-%m-%d'), f"INR {e.final_amount}"])

        t = Table(table_data, colWidths=[65, 120, 100, 75, 75, 75])
        t.setStyle(get_modern_table_style())
        story.append(t)
        story.append(Spacer(1, 15))
        story.append(create_insight_box(f"Event bookings cleared <b>INR {total_e_rev:,.2f}</b> in gross revenue.{top_hall_str}"))

    if section_scope == 'overall': story.append(PageBreak())

    if section_scope in ['overall', 'tables']:
        story.append(Paragraph("4. Restaurant Table Reservations", h1_style))
        tables = TableReservation.objects.filter(reservation_date__gte=start_date, reservation_date__lte=end_date).exclude(status='Cancelled').select_related('table').order_by('-reservation_date')
        total_t_adv = tables.aggregate(Sum('advance_amount'))['advance_amount__sum'] or Decimal('0.00')

        top_loc = tables.values('table__location').annotate(c=Count('id')).order_by('-c').first()
        top_loc_str = f" Guests showed a high preference for <b>{top_loc['table__location']}</b> seating." if top_loc else ""

        table_data = [['Res ID', 'Customer Name', 'Table', 'Date', 'Time', 'Advance']]
        for t_res in tables[:10]:
            table_data.append([f"TBL#{t_res.id}", str(t_res.customer_name)[:15], f"T-{t_res.table.table_number}", t_res.reservation_date.strftime('%Y-%m-%d'), t_res.reservation_time.strftime('%H:%M'), f"INR {t_res.advance_amount}"])

        t = Table(table_data, colWidths=[70, 130, 60, 80, 80, 75])
        t.setStyle(get_modern_table_style())
        story.append(t)
        story.append(Spacer(1, 15))
        story.append(create_insight_box(f"Processed <b>{tables.count()}</b> active reservations. Advanced deposits totaled INR {total_t_adv:,.2f}.{top_loc_str}"))

    if section_scope == 'overall': story.append(PageBreak())

    if section_scope in ['overall', 'financials']:
        story.append(Paragraph("5. Consolidated Financial Performance", h1_style))
        
        room_rev = RoomBooking.objects.filter(check_in__gte=start_date, check_in__lte=end_date).exclude(status__in=['Pending', 'Cancelled']).aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        event_rev = EventBooking.objects.filter(start_date__gte=start_date, start_date__lte=end_date).exclude(status__in=['Pending', 'Cancelled']).aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        order_rev = Order.objects.filter(order_date__gte=start_datetime, order_date__lte=end_datetime).exclude(status__in=['Pending', 'Cancelled']).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        table_rev = TableReservation.objects.filter(reservation_date__gte=start_date, reservation_date__lte=end_date).exclude(status='Cancelled').aggregate(Sum('advance_amount'))['advance_amount__sum'] or Decimal('0.00')

        room_p = room_rev * Decimal('0.85')
        event_p = event_rev * Decimal('0.60')
        dining_p = order_rev * Decimal('0.40')
        table_p = table_rev * Decimal('0.90')

        total_r = room_rev + event_rev + order_rev + table_rev
        total_p = room_p + event_p + dining_p + table_p

        table_data = [
            ['Operational Department', 'Gross Revenue', 'Est. Cost', 'Est. Net Profit', 'Margin'],
            ['Hospitality & Rooms', f"INR {room_rev:,.2f}", f"INR {room_rev * Decimal('0.15'):,.2f}", f"INR {room_p:,.2f}", '85%'],
            ['Banquets & Event Halls', f"INR {event_rev:,.2f}", f"INR {event_rev * Decimal('0.40'):,.2f}", f"INR {event_p:,.2f}", '60%'],
            ['Dining (Restaurant)', f"INR {order_rev:,.2f}", f"INR {order_rev * Decimal('0.60'):,.2f}", f"INR {dining_p:,.2f}", '40%'],
            ['Table Reservations', f"INR {table_rev:,.2f}", f"INR {table_rev * Decimal('0.10'):,.2f}", f"INR {table_p:,.2f}", '90%'],
            ['CONSOLIDATED OVERALL', f"INR {total_r:,.2f}", f"INR {(total_r - total_p):,.2f}", f"INR {total_p:,.2f}", f"{((total_p/total_r*100) if total_r > 0 else 0):.1f}%"]
        ]

        t = Table(table_data, colWidths=[150, 95, 95, 95, 60])
        fin_style = get_modern_table_style()
        fin_style.add('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E5E7EB"))
        fin_style.add('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor("#111827"))
        fin_style.add('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')
        t.setStyle(fin_style)
        
        story.append(t)
        story.append(Spacer(1, 15))

        profit_dict = {'Hospitality & Rooms': room_p, 'Banquets': event_p, 'Dining': dining_p, 'Tables': table_p}
        best = max(profit_dict.items(), key=lambda x: x[1])
        story.append(create_insight_box(f"The <b>{best[0]}</b> department is the primary driver of net profit, capturing <b>INR {best[1]:,.2f}</b> during this timeframe."))

    doc.build(story)
    return response

# def generate_advanced_pdf_report(request):
#     """Assembles a comprehensive business intelligence document package."""
#     section_scope = request.GET.get('section', 'overall')
#     start_date, end_date, start_datetime, end_datetime, time_filter = _get_report_dates(request)
    
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="StayZen_{section_scope.title()}_Report.pdf"'
    
#     doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
#     story = []
    
#     styles = getSampleStyleSheet()
#     title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor("#0F172A"), spaceAfter=4)
#     meta_style = ParagraphStyle('Meta', fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#64748B"), spaceAfter=15)

#     story.append(Paragraph("StayZen Hotel Management System — Reports", title_style))
#     story.append(Paragraph(f"Scope: {section_scope.upper()} ({start_date} to {end_date})", meta_style))
        
#     doc.build(story)
#     return response

@_lr
def generate_csv_report(request, report_type):
    """Streams targeted raw data CSV files for separate hotel operations."""
    start_date, end_date, start_datetime, end_datetime, time_filter = _get_report_dates(request)
    response = HttpResponse(content_type='text/csv')
    writer = csv.writer(response)

    if report_type in ['rooms', 'reservations']:
        response['Content-Disposition'] = 'attachment; filename="rooms_breakdown.csv"'
        writer.writerow(['Booking ID', 'Guest Name', 'Room Number', 'Check In', 'Check Out', 'Amount', 'Status'])
        queryset = RoomBooking.objects.select_related('room').filter(check_in__gte=start_date, check_out__lte=end_date).order_by('-check_in')
        for b in queryset.iterator():
            writer.writerow([f"#SZ-{b.id}", b.guest_name or 'Walk-in', b.room.room_number, b.check_in, b.check_out, b.final_amount, b.status])

    return response

# ==========================================
# 5. ROUTING SHORTCUTS
# ==========================================

@_lr
def reports_payments(request): 
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    transactions = []
    bookings_qs = _apply_report_filters(request, RoomBooking.objects.all(), 'check_in')
    for rb in bookings_qs.iterator():
        if rb.advance_amount > 0:
            transactions.append([f"RES-ADV-{rb.id}", rb.created_at.date(), 'Room Advance', rb.guest_name or 'Walk-in', rb.advance_amount, rb.payment_method or 'Cash/Card', 'Paid'])
    context = {
        'time_filter': time_filter,
        'records': transactions[:25],
        'total_count': len(transactions),
        'total_rev': sum(tx[4] for tx in transactions)
    }
    return render(request, 'admin/sections/reports_payments.html', context)

@_lr
def reports_attendance(request): 
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    records = _apply_report_filters(request, Attendance.objects.all(), 'date').select_related('staff').order_by('-date')
    context = {
        'time_filter': time_filter,
        'records': records[:25],
        'total_count': records.count(),
        'present_count': records.filter(status='Present').count(),
        'late_count': records.filter(status='Late').count(),
        'absent_count': records.filter(status='Absent').count()
    }
    return render(request, 'admin/sections/reports_attendance.html', context)

@_lr
def reports_financials(request): 
    start_date, end_date, start_dt, end_dt, time_filter = _get_report_dates(request)
    room_rev = _apply_report_filters(request, RoomBooking.objects.all(), 'check_in').exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    event_rev = _apply_report_filters(request, EventBooking.objects.all(), 'start_date').exclude(status='Cancelled').aggregate(s=Sum('final_amount'))['s'] or Decimal('0.00')
    dining_rev = _apply_report_filters(request, Order.objects.all(), 'order_date').exclude(status='Cancelled').aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    table_rev = _apply_report_filters(request, TableReservation.objects.all(), 'reservation_date').exclude(status='Cancelled').aggregate(s=Sum('advance_amount'))['s'] or Decimal('0.00')

    def _dept(name, rev, cost_rate, color):
        cost = (rev * cost_rate).quantize(Decimal('0.01'))
        profit = (rev - cost).quantize(Decimal('0.01'))
        margin = round(float(profit / rev * 100), 1) if rev else 0.0
        return {'department': name, 'revenue': rev, 'cost': cost, 'profit': profit, 'margin': margin, 'color': color}

    dept_rows = [
        _dept('Hospitality & Rooms', room_rev, Decimal('0.15'), '#3b82f6'),
        _dept('Banquets & Events', event_rev, Decimal('0.40'), '#10b981'),
        _dept('F&B Dining', dining_rev, Decimal('0.30'), '#f59e0b'),
        _dept('Table Reservations', table_rev, Decimal('0.10'), '#8b5cf6'),
    ]
    context = {
        'time_filter': time_filter,
        'records': dept_rows,
        'total_count': len(dept_rows),
        'total_rev': (room_rev + event_rev + dining_rev + table_rev).quantize(Decimal('0.01')),
        'total_profit': sum(d['profit'] for d in dept_rows),
        'most_profitable_name': max(dept_rows, key=lambda d: d['profit'])['department'] if dept_rows else "Hospitality & Rooms"
    }
    return render(request, 'admin/sections/reports_financials.html', context)

@_lr
def reports_bi(request): 
    return reports_section_detail(request, 'bi')

#-------------------------------------------------------------------------#
# DYNAMIC DEPARTMENTS & ROLES CRUD
#-------------------------------------------------------------------------#

@_lr
def manage_masters(request):
    edit_dept_id = request.GET.get('edit_dept')
    edit_role_id = request.GET.get('edit_role')
    
    edit_dept = Department.objects.filter(id=edit_dept_id).first() if edit_dept_id else None
    edit_role = Role.objects.filter(id=edit_role_id).first() if edit_role_id else None
    
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'save_department':
            dept_id = request.POST.get('dept_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, "Department name is required.")
            elif Department.objects.filter(name__iexact=name).exclude(id=dept_id).exists():
                messages.error(request, f"Department '{name}' already exists.")
            else:
                if dept_id:
                    dept = Department.objects.filter(id=dept_id).first()
                    if dept:
                        dept.name = name
                        dept.description = description
                        dept.edited_by = request.user
                        dept.save()
                        messages.success(request, "Department updated successfully.")
                else:
                    Department.objects.create(
                        name=name,
                        description=description,
                        created_by=request.user
                    )
                    messages.success(request, "Department created successfully.")
                return redirect('manage_masters')
                
        elif action == 'save_role':
            role_id = request.POST.get('role_id')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, "Role name is required.")
            elif Role.objects.filter(name__iexact=name).exclude(id=role_id).exists():
                messages.error(request, f"Role '{name}' already exists.")
            else:
                if role_id:
                    r = Role.objects.filter(id=role_id).first()
                    if r:
                        r.name = name
                        r.description = description
                        r.edited_by = request.user
                        r.save()
                        messages.success(request, "Role updated successfully.")
                else:
                    Role.objects.create(
                        name=name,
                        description=description,
                        created_by=request.user
                    )
                    messages.success(request, "Role created successfully.")
                return redirect('manage_masters')

    departments = Department.objects.all()
    roles = Role.objects.all()
    
    return render(request, 'admin/masters/manage_masters.html', {
        'departments': departments,
        'roles': roles,
        'edit_dept': edit_dept,
        'edit_role': edit_role,
    })

@_lr
def department_delete(request, id):
    department = get_object_or_404(Department, id=id)
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department deleted successfully.")
    return redirect('manage_masters')

@_lr
def role_delete(request, id):
    role = get_object_or_404(Role, id=id)
    if request.method == "POST":
        role.delete()
        messages.success(request, "Role deleted successfully.")
    return redirect('manage_masters')
#---------------
#site settings
#----------------
from .models import SiteSettings
from .forms import SiteSettingsForm
def site_settings_view(request):
    # Fetch the one and only settings object
    settings = SiteSettings.load()

    if request.method == 'POST':
        form = SiteSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Website content updated successfully!')
            return redirect('site_settings') # Redirect back to the same page
    else:
        form = SiteSettingsForm(instance=settings)

    context = {'form': form}
    # Create a simple template for this in your admin templates folder
    return render(request, 'admin/site_settings.html', context)

@_lr
def manage_cancellations(request):
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
    from django.utils import timezone
    from django.core.paginator import Paginator
    
    cancellations = []
    
    for rb in RoomBooking.objects.filter(status='Cancelled'):
        cb = rb.cancelled_by or 'System'
        if cb.lower() == 'guest':
            category = 'Guest Initiative'
        elif cb.lower() == 'system':
            category = 'System Release'
        else:
            category = 'Staff Action'
        cancellations.append({
            'id': rb.long_order_id,
            'type': 'Room',
            'category': category,
            'guest': rb.guest_name or (rb.customer.user.username if rb.customer else 'Guest'),
            'amount': rb.final_amount,
            'cancelled_by': rb.cancelled_by,
            'reason': rb.cancellation_reason,
            'date': rb.cancelled_at or rb.created_at,
            'refund_status': rb.refund_status
        })
        
    for eb in EventBooking.objects.filter(status='Cancelled'):
        cb = eb.cancelled_by or 'System'
        if cb.lower() == 'guest':
            category = 'Guest Initiative'
        elif cb.lower() == 'system':
            category = 'System Release'
        else:
            category = 'Staff Action'
        cancellations.append({
            'id': eb.long_order_id,
            'type': 'Event',
            'category': category,
            'guest': eb.guest_name or (eb.customer.user.username if eb.customer else 'Guest'),
            'amount': eb.final_amount,
            'cancelled_by': eb.cancelled_by,
            'reason': eb.cancellation_reason,
            'date': eb.cancelled_at or eb.created_at,
            'refund_status': eb.refund_status
        })
        
    for tr in TableReservation.objects.filter(status='Cancelled'):
        cb = tr.cancelled_by or 'System'
        if cb.lower() == 'guest':
            category = 'Guest Initiative'
        elif cb.lower() == 'system':
            category = 'System Release'
        else:
            category = 'Staff Action'
        cancellations.append({
            'id': tr.long_order_id,
            'type': 'Table',
            'category': category,
            'guest': tr.customer_name or (tr.customer.user.username if tr.customer else 'Guest'),
            'amount': tr.advance_amount,
            'cancelled_by': tr.cancelled_by,
            'reason': tr.cancellation_reason,
            'date': tr.cancelled_at or tr.created_at,
            'refund_status': tr.refund_status
        })
        
    for o in Order.objects.filter(status='Cancelled'):
        cb = o.cancelled_by or 'System'
        if cb.lower() == 'guest':
            category = 'Guest Initiative'
        elif cb.lower() == 'system':
            category = 'System Release'
        else:
            category = 'Staff Action'
        cancellations.append({
            'id': o.long_order_id,
            'type': 'Food Order',
            'category': category,
            'guest': o.customer_name or (o.user.username if o.user else 'Guest'),
            'amount': o.total_amount,
            'cancelled_by': o.cancelled_by,
            'reason': o.cancellation_reason,
            'date': o.cancelled_at or o.order_date,
            'refund_status': o.refund_status
        })
        
    cancellations.sort(key=lambda x: x['date'] if x['date'] else timezone.now(), reverse=True)
    
    paginator = Paginator(cancellations, 7)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin/admin_manage_cancellations.html', {'page_obj': page_obj})

@_lr
def update_refund_status(request, token):
    if request.method == 'POST':
        from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
        status = request.POST.get('refund_status')
        
        booking = RoomBooking.objects.filter(long_order_id=token).first()
        if not booking: booking = EventBooking.objects.filter(long_order_id=token).first()
        if not booking: booking = TableReservation.objects.filter(long_order_id=token).first()
        if not booking: booking = Order.objects.filter(long_order_id=token).first()
        
        if booking:
            if booking.refund_status == 'Refunded':
                messages.error(request, "This booking has already been refunded. No further action allowed.")
            else:
                booking.refund_status = status
                booking.save()
                messages.success(request, f"Refund status updated to {status}.")
        else:
            messages.error(request, "Booking not found.")
            
    return redirect('admin_manage_cancellations')


# ─────────────────────────────────────────────────────────────────────────────
# HOME DELIVERIES – Admin & Staff Views
# ─────────────────────────────────────────────────────────────────────────────

DELIVERY_STATUS_FLOW = [
    'Confirmed',
    'Preparing',
    'ReadyForPickup',
    'Assigned',
    'OutForDelivery',
    'Delivered',
    'Completed',
]

def _has_delivery_access(user):
    """Return True if user is superuser, staff with the Home Deliveries submenu permission,
    or a delivery staff member."""
    if user.is_superuser or user.is_staff:
        return True
    try:
        from staffapp.models import SubMenu, MenuPermission
        submenu = SubMenu.objects.get(url_name='admin_home_deliveries')
        return MenuPermission.objects.filter(user=user, submenu=submenu, can_view=True).exists()
    except Exception:
        return False

def _has_my_deliveries_access(user):
    """Return True if user is superuser, staff with the My Deliveries submenu permission."""
    if user.is_superuser or user.is_staff:
        return True
    try:
        from staffapp.models import SubMenu, MenuPermission
        submenu = SubMenu.objects.get(url_name='staff_my_deliveries')
        if MenuPermission.objects.filter(user=user, submenu=submenu, can_view=True).exists():
            return True
        return _has_delivery_access(user)
    except Exception:
        return False

def _can_assign(user):
    """Manager / superuser / is_staff can assign delivery staff."""
    if user.is_superuser or user.is_staff:
        return True
    try:
        from staffapp.models import SubMenu, MenuPermission
        submenu = SubMenu.objects.get(url_name='admin_home_deliveries')
        return MenuPermission.objects.filter(user=user, submenu=submenu, can_edit=True).exists()
    except Exception:
        return False

def _is_delivery_staff_only(user):
    """True if the user has access but cannot assign (pure delivery staff role)."""
    return (_has_delivery_access(user) or getattr(user, 'is_staff', False) == False and _has_my_deliveries_access(user)) and not _can_assign(user)

@login_required
def home_deliveries_view(request):
    from bookingapp.models import Order
    from django.core.paginator import Paginator
    from django.utils.dateparse import parse_date

    if not _has_delivery_access(request.user):
        return JsonResponse({'error': 'Access Denied'}, status=403)

    orders = Order.objects.filter(order_type='Delivery').select_related(
        'delivery_staff', 'assigned_by'
    ).prefetch_related('items__food')

    # Delivery staff only see their own assigned orders
    if _is_delivery_staff_only(request.user):
        orders = orders.filter(delivery_staff=request.user)

    # ── Filters ────────────────────────────────────────────────────────────────
    status_filter   = request.GET.get('status', '').strip()
    search          = request.GET.get('q', '').strip()
    date_from_str   = request.GET.get('date_from', '').strip()
    date_to_str     = request.GET.get('date_to', '').strip()

    if status_filter:
        orders = orders.filter(status=status_filter)

    if search:
        orders = orders.filter(
            Q(long_order_id__icontains=search) |
            Q(customer_name__icontains=search)  |
            Q(customer_phone__icontains=search)
        )

    if date_from_str:
        df = parse_date(date_from_str)
        if df:
            orders = orders.filter(order_date__date__gte=df)

    if date_to_str:
        dt = parse_date(date_to_str)
        if dt:
            orders = orders.filter(order_date__date__lte=dt)

    orders = orders.order_by('-order_date')

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Delivery staff list for assign modal (managers only)
    delivery_staff_list = []
    if _can_assign(request.user):
        # We want to show staff who are in the restaurant department or have delivery roles
        from adminapp.models import StaffUser
        delivery_staff_list = User.objects.filter(
            is_active=True,
            staff_profile__isnull=False
        ).order_by('first_name', 'username')

    context = {
        'page_obj':             page_obj,
        'status_filter':        status_filter,
        'search':               search,
        'date_from':            date_from_str,
        'date_to':              date_to_str,
        'can_assign':           _can_assign(request.user),
        'is_delivery_only':     _is_delivery_staff_only(request.user),
        'delivery_staff_list':  delivery_staff_list,
        'status_flow':          DELIVERY_STATUS_FLOW,
        'all_statuses': [
            ('Confirmed',      'Confirmed'),
            ('Preparing',      'Preparing'),
            ('ReadyForPickup', 'Ready for Pickup'),
            ('Assigned',       'Assigned'),
            ('OutForDelivery', 'Out for Delivery'),
            ('Delivered',      'Delivered'),
            ('Completed',      'Completed'),
            ('Cancelled',      'Cancelled'),
        ],
    }
    return render(request, 'admin/bookings/home_deliveries.html', context)


@login_required
def get_eligible_delivery_staff(request):
    """AJAX endpoint: returns on-duty staff who have the Home Deliveries submenu permission."""
    if not _can_assign(request.user):
        return JsonResponse({'success': False, 'message': 'Access Denied'}, status=403)

    from bookingapp.models import Order
    from staffapp.models import SubMenu, MenuPermission, Attendance
    from adminapp.models import StaffUser
    from django.utils import timezone
    import datetime

    today = timezone.localdate()

    # 1) Find the Home Deliveries and My Deliveries submenus
    submenu_urls = ['admin_home_deliveries', 'staff_my_deliveries']
    submenus = SubMenu.objects.filter(url_name__in=submenu_urls)

    # 2) Users who have can_view on either submenu = eligible delivery staff
    if submenus.exists():
        eligible_user_ids = MenuPermission.objects.filter(
            submenu__in=submenus, can_view=True
        ).values_list('user_id', flat=True)
    else:
        eligible_user_ids = []

    # 3) Those who are checked in TODAY and not yet checked out
    checked_in_today = Attendance.objects.filter(
        date=today,
        status__in=['Present', 'Late', 'Half Day'],  # not 'Checked Out' or 'Absent'
        check_in_time__isnull=False,
        check_out_time__isnull=True   # still on duty
    ).values_list('staff_id', flat=True)

    # 4) Intersect: eligible + on duty + active
    on_duty_ids = set(eligible_user_ids) & set(checked_in_today)
    on_duty_users = User.objects.filter(
        id__in=on_duty_ids, is_active=True
    ).order_by('first_name', 'username')

    staff_data = []
    for u in on_duty_users:
        # StaffUser profile
        profile = getattr(u, 'staff_profile', None)
        photo_url = ''
        if profile and profile.profile_image:
            photo_url = request.build_absolute_uri(profile.profile_image.url)

        dept_name = ''
        role_name = ''
        if profile:
            dept_name = profile.department.name if profile.department else ''
            role_name = profile.role.name if profile.role else ''

        # Attendance today
        try:
            att = Attendance.objects.get(staff=u, date=today)
            check_in_str = att.check_in_time.strftime('%I:%M %p') if att.check_in_time else '—'
        except Attendance.DoesNotExist:
            check_in_str = '—'

        # Active deliveries count
        active_count = Order.objects.filter(
            delivery_staff=u,
            order_type='Delivery',
            status__in=['Assigned', 'OutForDelivery']
        ).count()

        staff_data.append({
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'username': u.username,
            'photo': photo_url,
            'department': dept_name,
            'role': role_name,
            'check_in': check_in_str,
            'active_deliveries': active_count,
        })

    return JsonResponse({'success': True, 'staff': staff_data})


@login_required
def assign_delivery_staff(request, order_id):
    if not _can_assign(request.user):
        return JsonResponse({'success': False, 'message': 'Access Denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    from bookingapp.models import Order
    from django.utils import timezone
    order = get_object_or_404(Order, id=order_id, order_type='Delivery')

    staff_id = request.POST.get('staff_id')
    if not staff_id:
        return JsonResponse({'success': False, 'message': 'No staff selected'})

    try:
        staff_user = User.objects.get(id=staff_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Staff user not found'})

    # Status gate: only allow assignment when the order is prepared (Ready for Pickup) or already active in delivery
    if order.status not in ('ReadyForPickup', 'Assigned', 'OutForDelivery'):
        return JsonResponse({
            'success': False,
            'message': 'Cannot assign delivery staff until the order is prepared (Ready for Pickup).'
        })

    # If already assigned to the same person, prevent duplicate
    if order.delivery_staff_id and order.delivery_staff_id == int(staff_id):
        return JsonResponse({'success': False, 'message': 'This staff member is already assigned to this order.'})

    order.delivery_staff = staff_user
    order.assigned_by = request.user
    order.assigned_at = timezone.now()
    # Advance status to Assigned if it was ReadyForPickup
    if order.status == 'ReadyForPickup':
        order.status = 'Assigned'
    order.save(update_fields=['delivery_staff', 'assigned_by', 'assigned_at', 'status', 'updated_at'])


    profile = getattr(staff_user, 'staff_profile', None)
    photo_url = ''
    if profile and profile.profile_image:
        photo_url = request.build_absolute_uri(profile.profile_image.url)

    return JsonResponse({
        'success': True,
        'staff_name': staff_user.get_full_name() or staff_user.username,
        'new_status': order.get_status_display(),
        'staff_photo': photo_url,
        'assigned_by': request.user.get_full_name() or request.user.username,
        'assigned_at': order.assigned_at.strftime('%d %b %Y, %I:%M %p'),
    })


@login_required
def update_delivery_status(request, order_id):
    if not (_has_delivery_access(request.user) or _has_my_deliveries_access(request.user)):
        return JsonResponse({'success': False, 'message': 'Access Denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    from bookingapp.models import Order
    order = get_object_or_404(Order, id=order_id, order_type='Delivery')

    # Delivery-staff-only: can only update their own assigned orders
    if _is_delivery_staff_only(request.user) and order.delivery_staff != request.user:
        return JsonResponse({'success': False, 'message': 'You can only update your own deliveries'}, status=403)

    new_status = request.POST.get('status', '').strip()

    # Delivery staff are restricted to: Assigned → OutForDelivery → Delivered
    ALLOWED_TRANSITIONS = {
        'Confirmed':      ['Preparing'],
        'Preparing':      ['ReadyForPickup'],
        'ReadyForPickup': ['Assigned'],
        'Assigned':       ['OutForDelivery'],
        'OutForDelivery': ['Delivered'],
        'Delivered':      ['Completed'],
        'Completed':      [],
        'Cancelled':      [],
    }

    STAFF_ALLOWED_FROM = ('Assigned', 'OutForDelivery')

    if _is_delivery_staff_only(request.user):
        if order.status not in STAFF_ALLOWED_FROM:
            return JsonResponse({'success': False, 'message': f'You cannot update from status: {order.get_status_display()}'})
        allowed = ALLOWED_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            return JsonResponse({'success': False, 'message': f'Invalid transition: {order.status} → {new_status}'})
    else:
        # Manager can also cancel, but otherwise must follow the flow
        if new_status == 'Cancelled':
            pass  # Managers can cancel at any point
        else:
            allowed = ALLOWED_TRANSITIONS.get(order.status, [])
            if new_status not in allowed:
                return JsonResponse({'success': False, 'message': f'Invalid transition: {order.get_status_display()} → {new_status}'})

    order.status = new_status
    update_fields = ['status', 'updated_at']
    if new_status in ('Delivered', 'Completed') and not order.invoice_reference:
        order.invoice_reference = 'Paid on Delivery'
        update_fields.append('invoice_reference')
    elif new_status == 'Cancelled':
        from django.utils import timezone
        order.cancelled_at = timezone.now()
        order.cancelled_by = request.user.get_full_name() or request.user.username
        update_fields.extend(['cancelled_at', 'cancelled_by'])
    order.save(update_fields=update_fields)

    try:
        order.send_status_update_email()
    except Exception as e:
        print(f"Error sending email in update_delivery_status: {e}")

    return JsonResponse({'success': True, 'new_status': order.get_status_display()})


@login_required
def staff_my_deliveries(request):
    from bookingapp.models import Order
    from django.core.paginator import Paginator

    if not _has_my_deliveries_access(request.user):
        return render(request, '403.html', status=403)

    orders = Order.objects.filter(order_type='Delivery', delivery_staff=request.user).select_related(
        'delivery_staff', 'assigned_by'
    ).prefetch_related('items__food')

    # Filters
    status_filter = request.GET.get('status', '').strip()
    search        = request.GET.get('q', '').strip()

    if status_filter:
        orders = orders.filter(status=status_filter)

    if search:
        orders = orders.filter(
            Q(long_order_id__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search)
        )

    orders = orders.order_by('-order_date')

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj':      page_obj,
        'status_filter': status_filter,
        'search':        search,
        'status_flow':   DELIVERY_STATUS_FLOW,
        'all_statuses': [
            ('Assigned',       'Assigned'),
            ('OutForDelivery', 'Out for Delivery'),
            ('Delivered',      'Delivered'),
            ('Completed',      'Completed'),
        ],
    }
    return render(request, 'admin/bookings/my_deliveries.html', context)