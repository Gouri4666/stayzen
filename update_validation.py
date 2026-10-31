import re

with open('f:/project/StayZen/bookingapp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update table_reservation to also block past dates
table_res_pattern = r'''(parsed_reservation_date = _dt\.strptime\(reservation_date, "%Y-%m-%d"\)\.date\(\)\n\s+try:\n\s+booking_res_time = _dt\.strptime\(reservation_time, "%H:%M"\)\.time\(\)\n\s+except ValueError:\n\s+booking_res_time = _dt\.strptime\(reservation_time, "%H:%M:%S"\)\.time\(\)\n\s+if )parsed_reservation_date == current_local_date and booking_res_time <= current_local_time:'''

content = re.sub(table_res_pattern, r'\g<1>parsed_reservation_date < current_local_date or (parsed_reservation_date == current_local_date and booking_res_time <= current_local_time):', content)

# 2. Update event_booking to also block past dates
event_booking_pattern = r'''(current_local_date = timezone\.localdate\(\)\n\s+current_local_time = timezone\.localtime\(\)\.time\(\)\n\s+if )start_date == str\(current_local_date\) and start_time:'''

content = re.sub(event_booking_pattern, r'''\g<1>(start_date < str(current_local_date)) or (start_date == str(current_local_date) and start_time):
            if start_date < str(current_local_date):
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Cannot book a slot for a date in the past."})
                messages.error(request, "Cannot book a slot for a date in the past.")
                return redirect("event")''', content)

# 3. Add to book_activity_session
activity_pattern = r'''(session = get_object_or_404\(ActivitySession, id=session_id\)\n\n\s+if session\.status != 'Available' or session\.capacity <= 0:\n\s+messages\.error\(request, "This activity session is full or cancelled\."\)\n\s+return redirect\("activity_detail", id=activity_id\))'''
activity_insert = r'''\g<1>
    
    from django.utils import timezone
    current_local_date = timezone.localdate()
    current_local_time = timezone.localtime().time()
    
    if session.date < current_local_date or (session.date == current_local_date and session.start_time <= current_local_time):
        messages.error(request, "Cannot book a session that has already started or passed.")
        return redirect("activity_detail", id=activity_id)'''

content = re.sub(activity_pattern, activity_insert, content)


# 4. Add to offline_booking
offline_booking_pattern = r'''(check_in = parse_date\(check_in_str\)\n\s+check_out = parse_date\(check_out_str\)\n\s+if not check_in or not check_out:\n\s+if is_ajax:\n\s+return JsonResponse\(\{'success': False, 'message': "Invalid dates entered\."\}\)\n\s+messages\.error\(request, "Invalid dates entered\."\)\n\s+return redirect\("receptionist_room_bookings"\)\n\n\s+if check_in > check_out:)'''

offline_booking_insert = r'''\g<1>
        
        from django.utils import timezone
        if check_in < timezone.localdate():
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Check-in date cannot be in the past."})
            messages.error(request, "Check-in date cannot be in the past.")
            return redirect("receptionist_room_bookings")'''

content = re.sub(offline_booking_pattern, offline_booking_insert, content)


# 5. Add to offline_event_booking
offline_event_pattern = r'''(start_date = parse_date\(start_date_str\)\n\s+end_date = parse_date\(end_date_str\)\n\s+if not start_date or not end_date:\n\s+if is_ajax:\n\s+return JsonResponse\(\{'success': False, 'message': "Invalid dates entered\."\}\)\n\s+messages\.error\(request, "Invalid dates entered\."\)\n\s+return redirect\("receptionist_hall_bookings"\)\n\n\s+if start_date > end_date:)'''

offline_event_insert = r'''\g<1>
        
        from django.utils import timezone
        if start_date < timezone.localdate():
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Start date cannot be in the past."})
            messages.error(request, "Start date cannot be in the past.")
            return redirect("receptionist_hall_bookings")'''
            
content = re.sub(offline_event_pattern, offline_event_insert, content)


# 6. Add to offline_restaurant_table
offline_table_pattern = r'''(reservation_date = request\.POST\.get\('reservation_date'\)\n\s+reservation_time = request\.POST\.get\('reservation_time'\)\n\n\s+try:\n\s+with transaction\.atomic\(\):)'''

offline_table_insert = r'''\g<1>
                    from django.utils import timezone
                    current_local_date = timezone.localdate()
                    current_local_time = timezone.localtime().time()
                    
                    if reservation_date and reservation_time:
                        from datetime import datetime as _dt
                        parsed_reservation_date = _dt.strptime(reservation_date, "%Y-%m-%d").date()
                        try:
                            booking_res_time = _dt.strptime(reservation_time, "%H:%M").time()
                        except ValueError:
                            booking_res_time = _dt.strptime(reservation_time, "%H:%M:%S").time()
                        
                        if parsed_reservation_date < current_local_date or (parsed_reservation_date == current_local_date and booking_res_time <= current_local_time):
                            raise ValueError("Cannot book a slot for a time that has already passed.")'''

content = re.sub(offline_table_pattern, offline_table_insert, content)


with open('f:/project/StayZen/bookingapp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Validation updates written successfully.")
