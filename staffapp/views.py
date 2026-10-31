from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib import messages
from adminapp.models import StaffUser
from django.utils import timezone
from datetime import datetime, time
from django.contrib.auth.decorators import login_required
from .forms_profile import StaffProfileForm
from .models import Attendance
from django.contrib.auth.models import User
import adminapp.views as adminapp_views


def staff_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        elif request.user.is_staff:
            return redirect('staff_dashboard')

    if request.method == "POST":

        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password")

        # Resolve email to username if an @ is present
        username = identifier
        if "@" in identifier:
            try:
                matched = User.objects.get(email__iexact=identifier)
                username = matched.username
            except User.DoesNotExist:
                pass  # will fail authenticate() and hit the existing error path
            except User.MultipleObjectsReturned:
                username = User.objects.filter(email__iexact=identifier).first().username

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            # Allow superusers to access the custom admin dashboard
            if user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')

            try:
                staff, _ = StaffUser.objects.get_or_create(
                    user=user,
                    defaults={'status': True}
                )

                login(request, user)

                return redirect('staff_dashboard')

            except StaffUser.DoesNotExist:

                messages.error(
                    request,
                    "Not a valid staff account"
                )

        else:
            messages.error(
                request,
                "Invalid username or password"
            )

    return render(
        request,
        'staff/login.html'
    )


@login_required(login_url='/staff/login/')

def staff_dashboard(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    staff,_ = StaffUser.objects.get_or_create(user=request.user,defaults={'status': True})

    local_now = timezone.localtime(timezone.now())
    today = local_now.date()

    open_attendance = Attendance.objects.filter(staff=request.user,check_out_time__isnull=True).order_by('-date').first()
    if open_attendance:
        attendance = open_attendance
    else:
        attendance = Attendance.objects.filter(staff=request.user,date=today).first()



    # Resolve shift for display

    from .models import Shift

    shift = None

    if hasattr(request.user,'custom_shift'):

        try:

            shift = request.user.custom_shift

        except Shift.DoesNotExist:

            shift = None



    if not shift and hasattr(request.user,'staff_profile'):

        try:

            department = request.user.staff_profile.department

            shift = Shift.objects.filter(department=department).first()

        except Exception:

            pass



    if not shift:

        shift = Shift.objects.filter(is_global=True).first()

    can_check_in = False
    if shift:
        now_time = local_now.time()
        # Check if the shift crosses midnight
        if shift.start_time <= shift.end_time:
            # Normal shift, e.g., 09:00 to 17:00
            if shift.start_time <= now_time <= shift.end_time:
                can_check_in = True
        else:
            # Night shift crossing midnight, e.g., 22:00 to 06:00
            if now_time >= shift.start_time or now_time <= shift.end_time:
                can_check_in = True
    else:
        can_check_in = True

    # Compute formatted working hours

    working_hours_display = None

    if attendance and attendance.working_hours:

        total_seconds = int(attendance.working_hours.total_seconds())

        hours = total_seconds // 3600

        minutes = (total_seconds % 3600) // 60

        working_hours_display = f"{hours}h {minutes}m"



    return render(request,'staff/dashboard.html',{

        'staff': staff,

        'attendance': attendance,

        'shift': shift,

        'working_hours_display': working_hours_display,
        
        'can_check_in': can_check_in,

    })


@login_required(login_url='/staff/login/')
def staff_profile(request):
    """Allow staff to view and update their own profile."""
    if request.user.is_superuser:
        return redirect('admin_dashboard')

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
            elif len(new_password) < 5:
                messages.error(request, "New password must be at least 5 characters long.")
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
            # Keep the session valid after email/password-adjacent changes
            update_session_auth_hash(request, request.user)
            messages.success(request, "Profile updated successfully.")
            return redirect('staff_profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StaffProfileForm(instance=staff, user=request.user)

    return render(request, 'staff/profile.html', {
        'form': form,
        'staff': staff,
    })


# attendance


@login_required(login_url='/staff/login/')

def staff_check_in(request):

    if request.method == "POST":

        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        now_time = local_now.time()

        # Prevent check-in if there's already an open attendance
        open_attendance = Attendance.objects.filter(staff=request.user,check_out_time__isnull=True).first()
        if open_attendance:
            messages.error(request,"You must check out from your previous shift first.")
            return redirect('staff_dashboard')

        # Prevent duplicate check-in today
        existing_today = Attendance.objects.filter(staff=request.user,date=today).first()
        if existing_today:
            messages.error(request,"You have already completed your attendance today.")
            return redirect('staff_dashboard')



        # Resolve shift: user-specific → department → global → auto-create

        from .models import Shift

        shift = None

        if hasattr(request.user,'custom_shift'):

            try:

                shift = request.user.custom_shift

            except Shift.DoesNotExist:

                shift = None



        if not shift and hasattr(request.user,'staff_profile'):

            try:

                department = request.user.staff_profile.department

                shift = Shift.objects.filter(department=department).first()

            except Exception:

                pass



        if not shift:

            shift = Shift.objects.filter(is_global=True).first()



        if not shift:

            from datetime import time as dt_time

            shift = Shift.objects.create(

                name="Default Global",is_global=True,

                start_time=dt_time(9,0),end_time=dt_time(17,0)

            )



        # Determine status based on grace time

        from datetime import timedelta

        shift_start_dt = datetime.combine(today,shift.start_time)

        grace_deadline_dt = shift_start_dt + timedelta(minutes=shift.grace_time_minutes)

        check_in_dt = datetime.combine(today,now_time)



        if check_in_dt <= grace_deadline_dt:

            status = 'Present'

        else:

            status = 'Late'



        Attendance.objects.create(

            staff=request.user,

            date=today,

            check_in_time=now_time,

            status=status,

        )

        messages.success(request,"Checked in successfully.")

    return redirect('staff_dashboard')




@login_required(login_url='/staff/login/')

def staff_check_out(request):

    if request.method == "POST":

        local_now = timezone.localtime(timezone.now())
        today = local_now.date()

        attendance = Attendance.objects.filter(staff=request.user,check_out_time__isnull=True).order_by('-date').first()

        if not attendance:
            messages.error(request,"You must check in first.")
        elif attendance.check_out_time:
            messages.error(request,"You have already checked out.")

        else:

            now_time = timezone.localtime(timezone.now()).time()
            attendance.check_out_time = now_time

            from datetime import timedelta
            check_in_dt = datetime.combine(attendance.date,attendance.check_in_time)
            check_out_dt = datetime.combine(today,now_time)
            
            # Ensure check_out_dt is strictly after check_in_dt for overnight shifts
            if check_out_dt < check_in_dt:
                check_out_dt += timedelta(days=1)

            delta = check_out_dt - check_in_dt
            attendance.working_hours = delta



            # Re-evaluate status based on total working hours

            hours_worked = delta.total_seconds() / 3600

            if hours_worked >= 8:

                pass  # Keep the original Present/Late status from check-in

            elif hours_worked >= 4:

                attendance.status = 'Half Day'

            else:

                attendance.status = 'Absent'



            attendance.save()

            messages.success(request,"Checked out successfully.")



    return redirect('staff_dashboard')



@login_required(login_url='/staff/login/')

def admin_attendance_dashboard(request):

    if not request.user.is_superuser:

        messages.error(request,"Unauthorized access.")

        return redirect('staff_dashboard')

        

    attendances = Attendance.objects.all().order_by('-date')

    

    staff_id = request.GET.get('staff_id')

    filter_date = request.GET.get('date')

    filter_month = request.GET.get('month')

    

    if staff_id:

        attendances = attendances.filter(staff_id=staff_id)

    if filter_date:

        attendances = attendances.filter(date=filter_date)

    if filter_month:

        try:

            year,month = filter_month.split('-')

            attendances = attendances.filter(date__year=year,date__month=month)

        except ValueError:

            pass

        

    total_present = attendances.filter(status='Present').count()

    total_absent = attendances.filter(status='Absent').count()

    total_late = attendances.filter(status='Late').count()

    total_half_day = attendances.filter(status='Half Day').count()

    

    users = User.objects.filter(staff_profile__isnull=False).distinct()

    from .models import Shift
    for record in attendances:
        if record.working_hours:
            total_seconds = int(record.working_hours.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            record.display_hours = f"{hours}hr {minutes}min {seconds}sec"
        else:
            record.display_hours = "-"
            
        shift = None
        if hasattr(record.staff, 'custom_shift'):
            shift = record.staff.custom_shift
        if not shift and hasattr(record.staff, 'staff_profile'):
            shift = Shift.objects.filter(department=record.staff.staff_profile.department).first()
        if not shift:
            shift = Shift.objects.filter(is_global=True).first()
        record.display_shift = shift.name if shift else "Default"
    
    return render(request,'admin/admin_attendance_dashboard.html',{

        'attendances': attendances,

        'users': users,

        'total_present': total_present,

        'total_absent': total_absent,

        'total_late': total_late,

        'total_half_day': total_half_day,

    })





@login_required(login_url='/staff/login/')

def admin_shift_settings(request):

    if not request.user.is_superuser:

        messages.error(request,"Unauthorized access.")

        return redirect('staff_dashboard')

        

    from .models import Shift

    

    if request.method == 'POST':

        name = request.POST.get('name')

        start_time_str = request.POST.get('start_time')

        end_time_str = request.POST.get('end_time')

        grace_time_str = request.POST.get('grace_time_minutes')

        user_id = request.POST.get('user_id')

        department = request.POST.get('department')

        is_global = request.POST.get('is_global') == 'on'

        

        try:

            start_time = datetime.strptime(start_time_str,'%H:%M').time()

            end_time = datetime.strptime(end_time_str,'%H:%M').time()

            grace_time = int(grace_time_str)

            

            shift = Shift(

                name=name,

                start_time=start_time,

                end_time=end_time,

                grace_time_minutes=grace_time,

                is_global=is_global

            )

            

            if user_id:

                user = User.objects.get(id=user_id)

                shift.user = user

            elif department:

                shift.department = department

                

            shift.save()

            messages.success(request,"Shift created successfully.")

        except Exception as e:

            error_msg = str(e)
            if "Duplicate entry" in error_msg and "user_id" in error_msg:
                messages.error(request, "Duplicate entry. A shift is already assigned to this staff!.")
            else:
                messages.error(request,f"Error creating shift: {e}")

            

        return redirect('admin_shift_settings')

        

    shifts = Shift.objects.all()

    users = User.objects.filter(staff_profile__isnull=False)

    

    try:
        from adminapp.models import Department
        departments = [(dept.name,dept.name) for dept in Department.objects.all()]
    except:
        departments = []

        

    return render(request,'admin/admin_shift_settings.html',{

        'shifts': shifts,

        'users': users,

        'departments': departments

    })



@login_required(login_url='/staff/login/')

def delete_shift(request,shift_id):

    if not request.user.is_superuser:

        return redirect('staff_dashboard')

    from .models import Shift

    try:

        Shift.objects.get(id=shift_id).delete()

        messages.success(request,"Shift deleted successfully.")

    except Shift.DoesNotExist:

        messages.error(request,"Shift not found.")

    return redirect('admin_shift_settings')



@login_required(login_url='/staff/login/')

def edit_shift(request,shift_id):

    if not request.user.is_superuser:

        return redirect('staff_dashboard')

        

    from .models import Shift

    from django.shortcuts import get_object_or_404

    shift = get_object_or_404(Shift,id=shift_id)

    

    if request.method == 'POST':

        name = request.POST.get('name')

        start_time_str = request.POST.get('start_time')

        end_time_str = request.POST.get('end_time')

        grace_time_str = request.POST.get('grace_time_minutes')

        user_id = request.POST.get('user_id')

        department = request.POST.get('department')

        is_global = request.POST.get('is_global') == 'on'

        

        try:

            # Handle start_time parsing (supports format with or without seconds)

            try:

                shift.start_time = datetime.strptime(start_time_str,'%H:%M').time()

            except ValueError:

                shift.start_time = datetime.strptime(start_time_str,'%H:%M:%S').time()

                

            # Handle end_time parsing

            try:

                shift.end_time = datetime.strptime(end_time_str,'%H:%M').time()

            except ValueError:

                shift.end_time = datetime.strptime(end_time_str,'%H:%M:%S').time()

                

            shift.name = name

            shift.grace_time_minutes = int(grace_time_str)

            shift.is_global = is_global

            

            if user_id:

                user = User.objects.get(id=user_id)

                shift.user = user

                shift.department = None

            elif department:

                shift.department = department

                shift.user = None

            else:

                shift.user = None

                shift.department = None

                

            shift.save()

            messages.success(request,"Shift updated successfully.")

            return redirect('admin_shift_settings')

        except Exception as e:

            error_msg = str(e)
            if "Duplicate entry" in error_msg and "user_id" in error_msg:
                messages.error(request, "Duplicate assigning can't be done. A shift is already assigned to this user.")
            else:
                messages.error(request,f"Error updating shift: {e}")

            

    users = User.objects.filter(staff_profile__isnull=False)

    try:
        from adminapp.models import Department
        departments = [(dept.name,dept.name) for dept in Department.objects.all()]
    except:
        departments = []

        

    return render(request,'admin/admin_edit_shift.html',{

        'shift': shift,

        'users': users,

        'departments': departments

    }) 




# --- Staff Calendar Integration ---
from django.http import JsonResponse
from adminapp.models import Room,event_hall
from bookingapp.models import RoomBooking, FreshUpRoomBooking, EventBooking
from django.contrib.auth.decorators import login_required

@login_required(login_url='/staff/login/')
def calendar_dashboard_view(request):
    return render(request,'staff/calendar_dashboard.html')

@login_required(login_url='/staff/login/')
def calendar_api(request):
    from bookingapp.views import release_expired_freshup_bookings
    from django.utils import timezone
    release_expired_freshup_bookings()
    filter_type = request.GET.get('filter','all')
    try:
        month = int(request.GET.get('month', timezone.localdate().month))
        year  = int(request.GET.get('year', timezone.localdate().year))
    except (ValueError,TypeError):
        month = timezone.localdate().month
        year  = timezone.localdate().year

    print(f"[DEBUG] Fetching calendar data from database - Filter: {filter_type}, Month: {month}, Year: {year}")

    resources = []
    events = []

    def add_resource(id_val,title,r_type, status='Available'):
        resources.append({"id": f"{r_type}_{id_val}","title": title,"type": r_type, "status": status})

    def add_event(booking_id,resource_id,title,start_date,end_date,status,guest_name,b_type,checkin_str,checkout_str):
        if not start_date or not end_date:
            return
        events.append({
            "id":         f"{b_type}_{booking_id}",
            "resourceId": resource_id,
            "title":      title,
            "start":      str(start_date),
            "end":        str(end_date),
            "status":     status,
            "guest_name": guest_name or "",
            "type":       b_type,
            "check_in":   checkin_str,
            "check_out":  checkout_str,
        })

    # ── Resources ──────────────────────────────────────────────
    if filter_type in ['all','rooms','freshup']:
        now = timezone.now()
        from datetime import timedelta
        for room in Room.objects.all():
            status = room.status
            completed_bookings = RoomBooking.objects.filter(
                room_id=room.id, status='Completed', actual_checkout_at__isnull=False
            ).order_by('-actual_checkout_at')[:1]
            if completed_bookings:
                latest = completed_bookings[0]
                if now <= latest.actual_checkout_at + timedelta(minutes=30):
                    status = 'Maintenance'
            add_resource(room.id,f"Room {room.room_number} ({room.get_room_type_display()})","room", status)

    if filter_type in ['all','event','events']:
        now = timezone.now()
        from datetime import timedelta
        for hall in event_hall.objects.all():
            status = hall.hall_status
            completed_bookings = EventBooking.objects.filter(
                hall_id=hall.hall_id, status='Completed', actual_checkout_at__isnull=False
            ).order_by('-actual_checkout_at')[:1]
            if completed_bookings:
                latest = completed_bookings[0]
                if now <= latest.actual_checkout_at + timedelta(minutes=30):
                    status = 'maintenance'
            add_resource(hall.hall_id,hall.hall_name,"hall", status)
    # ── Room Bookings ──────────────────────────────────────────
    if filter_type in ['all','rooms']:
        for b in RoomBooking.objects.exclude(status__in=['Cancelled','Completed','Pending']).select_related('room'):
            checkin_str  = b.check_in.strftime('%d %b %Y') if b.check_in else ''
            checkout_str = b.check_out.strftime('%d %b %Y') if b.check_out else ''
            add_event(
                b.id, f"room_{b.room_id}",
                f"Stay – {b.guest_name}",
                b.check_in, b.check_out,
                b.status, b.guest_name, "rooms",
                checkin_str, checkout_str
            )


    # ── FreshUp Bookings (show today's freshup events) ─────────
    if filter_type in ['all','rooms','freshup']:
        from datetime import timedelta
        now = timezone.now()
        for b in FreshUpRoomBooking.objects.select_related('room').order_by('-booking_datetime'):
            if not b.booking_datetime:
                continue
            date_str = timezone.localtime(b.booking_datetime).date()
            if date_str.year != year or date_str.month != month:
                continue
            
            # If we are in the 'rooms' tab, we only include active freshup bookings
            if filter_type == 'rooms':
                if b.payment_status == 'Cancelled':
                    continue
                if b.payment_status == 'Pending' and now - b.booking_datetime > timedelta(minutes=15):
                    continue
                expiration_time = b.booking_datetime + timedelta(hours=b.hours_required) + timedelta(minutes=30)
                if now >= expiration_time:
                    continue

            status_label = "Reserved"
            add_event(
                b.id, f"room_{b.room_id}",
                f"FreshUp – {b.customer_name}",
                date_str, date_str,
                status_label, b.customer_name, "freshup",
                date_str.strftime('%d %b %Y'), date_str.strftime('%d %b %Y')
            )

        # ── Stay Room bookings shown as BLOCKED in Fresh-up view ──
        # Rooms under active Stay bookings must appear occupied so staff
        # can see they are unavailable for Fresh-up on those dates.
        for b in RoomBooking.objects.exclude(
                status__in=['Cancelled','Completed']).select_related('room'):
            if not b.check_in or not b.check_out:
                continue
            checkin_str  = b.check_in.strftime('%d %b %Y')
            checkout_str = b.check_out.strftime('%d %b %Y')
            add_event(
                f"stay_{b.id}", f"room_{b.room_id}",
                f"Stay (Blocked) – {b.guest_name or ''}",
                b.check_in, b.check_out,
                "stay_blocked", b.guest_name or "", "stay_block",
                checkin_str, checkout_str
            )

    # ── Event Bookings ─────────────────────────────────────────
    if filter_type in ['all','event','events']:
        for b in EventBooking.objects.exclude(status__in=['Cancelled','Completed','Pending']).select_related('hall'):
            checkin_str  = b.start_date.strftime('%d %b %Y') if b.start_date else ''
            checkout_str = b.end_date.strftime('%d %b %Y')   if b.end_date   else ''
            add_event(
                b.id,f"hall_{b.hall_id}",
                f"Event – {b.guest_name}",
                b.start_date,b.end_date,
                b.status,b.guest_name,"event",
                checkin_str,checkout_str
            )

    return JsonResponse({"resources": resources,"events": events})

@login_required(login_url='/staff/login/')
def staff_api_get_notifications(request):
    return adminapp_views.api_get_notifications(request)

@login_required(login_url='/staff/login/')
def staff_api_mark_notification_read(request, id):
    return adminapp_views.api_mark_notification_read(request, id)

@login_required(login_url='/staff/login/')
def staff_api_delete_notification(request, id):
    return adminapp_views.api_delete_notification(request, id)

@login_required(login_url='/staff/login/')
def staff_api_clear_notifications(request):
    return adminapp_views.api_clear_notifications(request)

@login_required(login_url='/staff/login/')
def staff_api_get_sent_notifications(request):
    return adminapp_views.api_get_sent_notifications(request)

@login_required(login_url='/staff/login/')
def staff_api_delete_sent_notification(request, id):
    return adminapp_views.api_delete_sent_notification(request, id)

@login_required(login_url='/staff/login/')
def staff_api_clear_sent_notifications(request):
    return adminapp_views.api_clear_sent_notifications(request)

@login_required(login_url='/staff/login/')
def calendar_date_bookings_api(request):
    """
    Returns all bookings for a specific date across booking types.
    GET params:
        date  — required, YYYY-MM-DD
        tab   — optional: 'rooms' (default), 'events', 'freshup', 'restaurant', 'all'
    Response: { bookings: [...], date: 'YYYY-MM-DD', count: N }
    """
    from django.http import JsonResponse
    from django.utils.dateparse import parse_date
    from django.utils import timezone
    from datetime import timedelta
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, FreshUpRoomBooking

    date_str = request.GET.get('date', '').strip()
    tab = request.GET.get('tab', 'all').strip()

    if not date_str:
        return JsonResponse({'error': 'date parameter is required'}, status=400)

    target_date = parse_date(date_str)
    if not target_date:
        return JsonResponse({'error': 'Invalid date format, expected YYYY-MM-DD'}, status=400)

    bookings = []

    def status_label(raw_status):
        """Normalise DB status values into display labels and CSS classes."""
        s = (raw_status or '').strip()
        mapping = {
            'Booked':     ('Booked',      'booked'),
            'Reserved':   ('Booked',      'booked'),
            'Confirmed':  ('Booked',      'booked'),
            'Pending':    ('Pending',     'pending'),
            'Checked In': ('Checked In',  'checkedin'),
            'Completed':  ('Checked Out', 'checkedout'),
            'Cancelled':  ('Cancelled',   'cancelled'),
        }
        return mapping.get(s, (s, 'pending'))

    # ── Room bookings (check_in <= date < check_out) ─────────────────────────
    if tab in ('rooms', 'all'):
        try:
            room_qs = (
                RoomBooking.objects
                .select_related('room', 'customer', 'customer__user')
                .filter(check_in__lte=target_date, check_out__gt=target_date)
                .exclude(status='Cancelled')
                .order_by('check_in')
            )
            # Also include same-day (check_in == check_out == date)
            same_day_room = (
                RoomBooking.objects
                .select_related('room', 'customer', 'customer__user')
                .filter(check_in=target_date, check_out=target_date)
                .exclude(status='Cancelled')
            )
            seen_ids = set()
            for b in list(room_qs) + list(same_day_room):
                if b.id in seen_ids:
                    continue
                seen_ids.add(b.id)
                lbl, css = status_label(b.status)
                guest = b.guest_name or (
                    b.customer.user.get_full_name() if b.customer else 'Guest'
                )
                bookings.append({
                    'id': b.id,
                    'booking_ref': b.long_order_id or f'RB-{b.id}',
                    'type': 'Room',
                    'type_css': 'room',
                    'guest_name': guest,
                    'guest_phone': b.guest_phone or '',
                    'guest_email': b.guest_email or '',
                    'unit': f'Room {b.room.room_number}',
                    'unit_type': b.room.room_type or '',
                    'check_in': str(b.check_in),
                    'check_out': str(b.check_out),
                    'status': lbl,
                    'status_css': css,
                    'raw_status': b.status,
                    'amount': str(b.final_amount or b.total_amount or 0),
                    'adults': b.adults,
                    'children': b.children,
                    'payment_status': b.payment_status or '',
                    'created_at': b.created_at.strftime('%d %b %Y, %H:%M') if b.created_at else '',
                })
        except Exception as e:
            pass  # Don't break the whole response if one type fails

    # ── Event bookings (start_date <= date <= end_date) ──────────────────────
    if tab in ('events', 'all'):
        try:
            event_qs = (
                EventBooking.objects
                .select_related('hall', 'customer', 'customer__user')
                .filter(start_date__lte=target_date, end_date__gte=target_date)
                .exclude(status='Cancelled')
                .order_by('start_date')
            )
            for b in event_qs:
                lbl, css = status_label(b.status)
                guest = b.guest_name or (
                    b.customer.user.get_full_name() if b.customer else 'Guest'
                )
                bookings.append({
                    'id': b.id,
                    'booking_ref': b.long_order_id or f'EB-{b.id}',
                    'type': 'Event',
                    'type_css': 'event',
                    'guest_name': guest,
                    'guest_phone': b.guest_phone or '',
                    'guest_email': b.guest_email or '',
                    'unit': b.hall.hall_name,
                    'unit_type': b.event_type or '',
                    'check_in': str(b.start_date),
                    'check_out': str(b.end_date),
                    'status': lbl,
                    'status_css': css,
                    'raw_status': b.status,
                    'amount': str(b.final_amount or b.total_amount or 0),
                    'adults': b.guest_count,
                    'children': 0,
                    'payment_status': b.payment_status or '',
                    'created_at': b.created_at.strftime('%d %b %Y, %H:%M') if b.created_at else '',
                })
        except Exception as e:
            pass

    # ── Fresh-up bookings (same-day) ─────────────────────────────────────────
    if tab in ('freshup', 'all'):
        try:
            freshup_qs = (
                FreshUpRoomBooking.objects
                .select_related('room', 'customer', 'customer__user')
                .filter(booking_datetime__date=target_date)
                .exclude(payment_status='Cancelled')
                .order_by('booking_datetime')
            )
            now = timezone.now()
            for b in freshup_qs:
                expiry = b.booking_datetime + timedelta(hours=b.hours_required) + timedelta(minutes=30)
                if b.payment_status == 'Cancelled':
                    raw_s = 'Cancelled'
                elif b.payment_status == 'Pending' and now - b.booking_datetime > timedelta(minutes=15):
                    raw_s = 'Cancelled'
                elif now < expiry:
                    raw_s = 'Checked In'
                else:
                    raw_s = 'Completed'
                lbl, css = status_label(raw_s)
                bookings.append({
                    'id': b.id,
                    'booking_ref': b.long_order_id or f'FU-{b.id}',
                    'type': 'Fresh-up',
                    'type_css': 'freshup',
                    'guest_name': b.customer_name or 'Guest',
                    'guest_phone': b.customer_phone or '',
                    'guest_email': '',
                    'unit': f'Room {b.room.room_number}',
                    'unit_type': f'{b.hours_required}h Fresh-up',
                    'check_in': str(target_date),
                    'check_out': str(target_date),
                    'status': lbl,
                    'status_css': css,
                    'raw_status': raw_s,
                    'amount': str(b.total_amount or 0),
                    'adults': 1,
                    'children': 0,
                    'payment_status': b.payment_status or '',
                    'created_at': b.booking_datetime.strftime('%d %b %Y, %H:%M') if b.booking_datetime else '',
                })
        except Exception as e:
            pass

    # ── Table reservations ───────────────────────────────────────────────────
    if tab in ('restaurant', 'all'):
        try:
            table_qs = (
                TableReservation.objects
                .select_related('table', 'customer', 'customer__user')
                .filter(reservation_date=target_date)
                .exclude(status='Cancelled')
                .order_by('reservation_time')
            )
            for b in table_qs:
                lbl, css = status_label(b.status)
                bookings.append({
                    'id': b.id,
                    'booking_ref': b.long_order_id or f'TR-{b.id}',
                    'type': 'Table',
                    'type_css': 'table',
                    'guest_name': b.customer_name or 'Guest',
                    'guest_phone': b.phone or '',
                    'guest_email': b.email or '',
                    'unit': f'Table {b.table.table_number}',
                    'unit_type': str(b.reservation_time) if b.reservation_time else '',
                    'check_in': str(b.reservation_date),
                    'check_out': str(b.reservation_date),
                    'status': lbl,
                    'status_css': css,
                    'raw_status': b.status,
                    'amount': '0',
                    'adults': b.guests,
                    'children': 0,
                    'payment_status': b.payment_status or '',
                    'created_at': b.created_at.strftime('%d %b %Y, %H:%M') if b.created_at else '',
                })
        except Exception as e:
            pass

    return JsonResponse({
        'bookings': bookings,
        'date': date_str,
        'count': len(bookings),
    })
@login_required(login_url='/staff/login/')
def staff_api_active_staff(request):
    return adminapp_views.api_active_staff(request)

@login_required(login_url='/staff/login/')
def staff_api_compose_notification(request):
    return adminapp_views.api_compose_notification(request)