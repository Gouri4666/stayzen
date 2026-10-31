import re
from django.shortcuts import render, redirect, get_object_or_404
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from adminapp.models import Room,event_hall,Package,Activity,ActivitySession,RestaurantTable
from accountapp.models import Customer
from .models import RoomBooking,EventBooking,ActivityBooking,TableReservation,Order,OrderItem
from .loyalty import award_points_for_booking, calculate_membership_discount, normalize_redeem_points, redeem_points_for_booking
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .utils import is_table_available
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

def room_booking(request):

    if request.method == "POST":
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'

        room_id = request.POST.get("room_id")

        if not room_id or not room_id.isdigit():
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Please select a valid room."})
            messages.error(request, "Please select a valid room.")
            return redirect("rooms")

        room = get_object_or_404(Room, id=room_id)

        if room.status == 'Not Available':
            if is_ajax:
                return JsonResponse({'success': False, 'message': "This room is currently not available for booking."})
            messages.error(request, "This room is currently not available for booking.")
            return redirect("rooms")

        check_in = parse_date(request.POST.get("check_in"))
        check_out = parse_date(request.POST.get("check_out"))

        try:
            adults = int(request.POST.get("adults", 1))
            children = int(request.POST.get("children", 0))
        except (TypeError, ValueError):
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Adults and children must be valid numbers."})
            messages.error(request, "Adults and children must be valid numbers.")
            return redirect("rooms")

        # -------------------------
        # VALIDATION: ROOM LIMITS
        # -------------------------
        if adults < 1:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Adults must be at least 1."})
            messages.error(request, "Adults must be at least 1.")
            return redirect("rooms")

        if children < 0:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Children cannot be negative."})
            messages.error(request, "Children cannot be negative.")
            return redirect("rooms")

        if adults > room.max_adults:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f"Max adults allowed is {room.max_adults}"})
            messages.error(request, f"Max adults allowed is {room.max_adults}")
            return redirect("rooms")

        if children > room.max_children:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f"Max children allowed is {room.max_children}"})
            messages.error(request, f"Max children allowed is {room.max_children}")
            return redirect("rooms")

        total_guests = adults + children
        room_capacity = room.max_adults + room.max_children
        if total_guests > room_capacity:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f"Total guests cannot exceed room capacity of {room_capacity}."})
            messages.error(request, f"Total guests cannot exceed room capacity of {room_capacity}.")
            return redirect("rooms")

        # -------------------------
        # VALIDATION: DATES
        # -------------------------
        if not check_in or not check_out:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Invalid dates selected."})
            messages.error(request, "Invalid dates selected.")
            return redirect("rooms")

        if check_in < timezone.localdate():
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Check-in date cannot be in the past."})
            messages.error(request, "Check-in date cannot be in the past.")
            return redirect("rooms")

        if check_out < check_in:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Check-out date must be on or after check-in date."})
            messages.error(request, "Check-out date must be on or after check-in date.")
            return redirect("rooms")

        # -------------------------
        # VALIDATION: OVERLAP CHECK
        # -------------------------
        overlap = RoomBooking.objects.filter(
            room=room,
            check_in__lt=check_out,
            check_out__gt=check_in
        ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).exists()

        if overlap:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Room already booked for selected dates."})
            messages.error(request, "Room already booked for selected dates.")
            return redirect("rooms")

        # -------------------------
        # CUSTOMER (REGISTERED USER) AND GUEST DATA
        # -------------------------
        customer = None
        guest_name = request.POST.get("guest_name")
        guest_phone = request.POST.get("guest_phone")
        guest_email = request.POST.get("guest_email")

        # Validation
        if guest_email:
            try:
                validate_email(guest_email)
            except ValidationError:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Enter a valid guest email address"})
                messages.error(request, "Enter a valid guest email address")
                return redirect("rooms")
        if guest_phone:
            if not re.match(r'^\d{10}$', guest_phone):
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Enter a valid 10-digit phone number"})
                messages.error(request, "Enter a valid 10-digit phone number")
                return redirect("rooms")

        if not request.user.is_authenticated and guest_email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(email=guest_email).exists():
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "This email is already with  registered . Please log in to book."})
                messages.error(request, "This email is already registered. Please log in to book.")
                return redirect("rooms")

        if request.user.is_authenticated:
            try:
                customer = Customer.objects.get(user=request.user)
                guest_name = guest_name or (customer.user.get_full_name() or customer.user.username)
                guest_phone = guest_phone or customer.phone
                guest_email = guest_email or customer.user.email
            except:
                customer = None
                guest_name = guest_name or (request.user.get_full_name() or request.user.username)
                guest_phone = guest_phone or ""
                guest_email = guest_email or request.user.email

        from .utils import validate_email_phone_mapping
        is_valid_mapping, mapping_err = validate_email_phone_mapping(guest_email, guest_phone)
        if not is_valid_mapping:
            if is_ajax:
                return JsonResponse({'success': False, 'message': mapping_err})
            messages.error(request, mapping_err)
            return redirect("rooms")

        # -------------------------
        # CALCULATE BILL
        # -------------------------
        try:
            days = (check_out - check_in).days
            if days < 1:
                days = 1
        except Exception:
            days = 1

        from decimal import Decimal
        total_amount = Decimal(days) * Decimal(room.price)
        requested_points = request.POST.get("redeem_points", 0)
        points_redeemed = 0
        membership_discount = Decimal('0.00')
        discount_amount = Decimal('0.00')
        final_amount = total_amount
        amount_after_membership = total_amount

        if customer:
            apply_discount = request.POST.get("apply_discount") in ["on", "true", "1", "True"]
            if apply_discount:
                membership_discount = calculate_membership_discount(customer, total_amount)
                amount_after_membership = total_amount - membership_discount
            try:
                requested_points_int = int(requested_points or 0)
            except (TypeError, ValueError):
                requested_points_int = 0

            max_redeemable = normalize_redeem_points(
                customer,
                requested_points_int,
                amount_after_membership
            )
            if requested_points_int > customer.loyalty_points:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Redeemed points cannot exceed your available points."})
                messages.error(request, "Redeemed points cannot exceed your available points.")
                return redirect("rooms")

            points_redeemed = max_redeemable
            discount_amount = membership_discount + Decimal(points_redeemed)
            final_amount = total_amount - discount_amount

        # Both guest and registered user online payment flows require 25% prepayment
        advance_amount = final_amount * Decimal('0.25')
        pending_payment = final_amount * Decimal('0.75')
        payment_status = "Pending"

        # -------------------------
        # CREATE BOOKING
        # -------------------------
        with transaction.atomic():
            locked_room = Room.objects.select_for_update().get(id=room.id)
            overlap = RoomBooking.objects.select_for_update().filter(
                room=locked_room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).exists()

            if overlap:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Room already booked for selected dates."})
                messages.error(request, "Room already booked for selected dates.")
                return redirect("rooms")

            booking = RoomBooking.objects.create(
                customer=customer,
                guest_name=guest_name,
                guest_phone=guest_phone,
                guest_email=guest_email,
                room=locked_room,
                check_in=check_in,
                check_out=check_out,
                adults=adults,
                children=children,
                status="Pending",
                total_amount=total_amount,
                pending_payment=pending_payment,
                points_redeemed=points_redeemed,
                discount_amount=discount_amount,
                final_amount=final_amount,
                advance_amount=advance_amount,
                payment_status=payment_status,
                booking_source="Online"
            )
            if customer and points_redeemed:
                redeem_points_for_booking(
                    customer,
                    booking,
                    points_redeemed,
                    amount_after_membership
                )
        review_context = _review_context(
            booking_type='room',
            booking_id=booking.id,
            service_name=getattr(room, 'room_type', f"Room {room.room_number}"),
            name=booking.guest_name,
            email=booking.guest_email,
            phone=booking.guest_phone,
            amount=booking.advance_amount,
            service_details=[
                ('Room', room.room_number),
                ('Check-in', check_in),
                ('Check-out', check_out),
                ('Guests', f"{adults} Adults, {children} Children"),
                ('Nights', days),
            ],
            summary_details=[
                ('Subtotal', f"₹{total_amount}"),
                ('Discount', f"-₹{discount_amount}"),
                ('Advance Due Now', f"₹{advance_amount}"),
                ('Final Amount', f"₹{advance_amount}"),
            ],
        )
        if is_ajax:
            return JsonResponse({'success': True, 'review': True, **review_context})
        return render(request, "guest/payment_review.html", review_context)

    return redirect("rooms")


# -----------------------------
# ACTIVITY BOOKING
# -----------------------------
def book_activity_session(request, activity_id):

    if request.method != "POST":
        return redirect("activity")

    if not request.user.is_authenticated:
        messages.error(request, "Login required")
        return redirect("login")

    session_id = request.POST.get("session_id")

    if not session_id:
        messages.error(request, "Please select a session.")
        return redirect("activity_detail", id=activity_id)

    activity = get_object_or_404(Activity, id=activity_id)
    session = get_object_or_404(ActivitySession, id=session_id)

    if session.status != 'Available' or session.capacity <= 0:
        messages.error(request, "This activity session is full or cancelled.")
        return redirect("activity_detail", id=activity_id)

    customer = Customer.objects.filter(user=request.user).first()

    room_booking = None
    if customer:
        room_booking = RoomBooking.objects.filter(customer=customer, status="Checked In").last()
        if not room_booking:
            room_booking = RoomBooking.objects.filter(customer=customer, status__in=["Confirmed", "Reserved"]).last()

    if not room_booking and request.user.email:
        room_booking = RoomBooking.objects.filter(guest_email=request.user.email, status="Checked In").last()
        if not room_booking:
            room_booking = RoomBooking.objects.filter(guest_email=request.user.email, status__in=["Confirmed", "Reserved"]).last()
        if room_booking and customer:
            room_booking.customer = customer
            room_booking.save()

    if not room_booking:
        messages.error(request, "You must book a room first.")
        return redirect("rooms")

    if room_booking.status not in ["Confirmed", "Reserved", "Checked In"]:
        messages.error(request, "You must confirm your room booking before booking activities.")
        return redirect("activity")

    ActivityBooking.objects.create(
        room_booking=room_booking,
        activity=activity,
        session=session,
        status="Booked"
    )

    # Accumulate activity cost safely in RoomBooking so it can be paid at checkout day
    from decimal import Decimal
    price = Decimal(activity.price)
    room_booking.total_amount += price
    room_booking.final_amount += price
    room_booking.pending_payment += price
    room_booking.save()

    messages.success(request, "Activity booked successfully!")
    return redirect("my_bookings")


# -----------------------------
# BOOKED DATES API (CALENDAR)
# -----------------------------
def booked_dates(request, room_id):

    bookings = RoomBooking.objects.filter(
        room_id=room_id
    ).exclude(status__in=['Cancelled', 'Completed', 'Pending'])

    reserved = []
    not_available = []

    for b in bookings:
        current = b.check_in
        dates_list = []
        while current < b.check_out:
            dates_list.append(str(current))
            current += timedelta(days=1)

        if b.status in ['Reserved', 'Checked In'] or b.payment_status == 'Confirmed':
            reserved.extend(dates_list)
        else:
            not_available.extend(dates_list)

    # Check for active Freshup booking today
    from .models import FreshUpRoomBooking
    from django.utils import timezone
    now = timezone.now()
    today = timezone.localdate()
    
    active_freshups = FreshUpRoomBooking.objects.filter(
        room_id=room_id
    ).exclude(payment_status='Cancelled')
    
    has_active_freshup = False
    for b in active_freshups:
        if not b.booking_datetime:
            continue
        # Convert booking_datetime to local date in Python
        date_str = timezone.localtime(b.booking_datetime).date()
        if date_str != today:
            continue
        if b.payment_status == 'Pending' and now - b.booking_datetime > timedelta(minutes=15):
            continue
        expiration_time = b.booking_datetime + timedelta(hours=b.hours_required) + timedelta(minutes=30)
        if now < expiration_time:
            has_active_freshup = True
            break
            
    if has_active_freshup:
        not_available.append(str(today))

    return JsonResponse({
        "booked": list(set(reserved + not_available)),
        "reserved": list(set(reserved)),
        "not_available": list(set(not_available))
    })

def hall_booked_dates(request, hall_id):
    bookings = EventBooking.objects.filter(
        hall_id=hall_id
    ).exclude(status__in=['Cancelled', 'Completed', 'Pending'])

    reserved = []
    not_available = []

    for b in bookings:
        if not b.start_date or not b.end_date:
            continue
        current = b.start_date
        dates_list = []
        while current <= b.end_date:
            dates_list.append(str(current))
            current += timedelta(days=1)

        if b.status in ['Confirmed', 'Checked In'] or b.payment_status == 'Confirmed':
            reserved.extend(dates_list)
        else:
            not_available.extend(dates_list)

    return JsonResponse({
        "booked": reserved + not_available,
        "reserved": reserved,
        "not_available": not_available
    })

def table_booked_dates(request, table_id):
    reservations = TableReservation.objects.filter(
        table_id=table_id
    ).exclude(status='Cancelled').exclude(payment_status='Pending')

    from collections import defaultdict
    booked_slots = defaultdict(list)
    time_slots = {
        '08:00:00': 'Breakfast',
        '12:00:00': 'Lunch',
        '19:00:00': 'Dinner',
        '08:00': 'Breakfast',
        '12:00': 'Lunch',
        '19:00': 'Dinner'
    }

    for r in reservations:
        date_str = str(r.reservation_date)
        time_str = r.reservation_time.strftime('%H:%M')
        slot = time_slots.get(time_str) or time_slots.get(f"{time_str}:00")
        if slot:
            booked_slots[date_str].append(slot)

    booked_dates = [date_str for date_str, slots in booked_slots.items() if len(slots) >= 3]

    return JsonResponse({
        "booked": booked_dates,
        "reserved": booked_dates,
        "booked_slots": dict(booked_slots),
        "not_available": []
    })


def event_booking(request):
    from django.http import Http404

    hall_id = request.GET.get("hall_id")
    hall = None

    if hall_id:
        if hall_id.isdigit():
            hall = get_object_or_404(event_hall, hall_id=hall_id)
        else:
            raise Http404("Invalid Hall ID")

    if request.method == "POST":
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'

        hall_id = request.POST.get("hall_id")
        if not hall_id or not hall_id.isdigit():
            raise Http404("Invalid Hall ID")
        hall = get_object_or_404(event_hall, hall_id=hall_id)

        event_name = request.POST.get("event_name")
        event_type = request.POST.get("event_type", "Other")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        food_preference = request.POST.get("food_preference", "None")
        guest_count = request.POST.get("guest_count")
        special_request = request.POST.get("special_request")
        package_id = request.POST.get("package")

        # -------------------------
        # VALIDATION: DATES
        # -------------------------
        if not start_date or not end_date:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Invalid dates selected."})
            messages.error(request, "Invalid dates selected.")
            return redirect("event")

        if start_date > end_date:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Start date cannot be after end date."})
            messages.error(request, "Start date cannot be after end date.")
            return redirect("event")

        # -------------------------
        # VALIDATION: OVERLAP CHECK
        # -------------------------
        overlap = EventBooking.objects.filter(
            hall=hall,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).exists()

        if overlap:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Event hall is already booked for the selected dates."})
            messages.error(request, "Event hall is already booked for the selected dates.")
            return redirect("event")

        package = None
        if package_id:
            package = get_object_or_404(Package, package_id=package_id)

        guest_name = request.POST.get("guest_name")
        guest_phone = request.POST.get("guest_phone")
        guest_email = request.POST.get("guest_email")

        # Validation
        if guest_email:
            try:
                validate_email(guest_email)
            except ValidationError:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Enter a valid guest email address"})
                messages.error(request, "Enter a valid guest email address")
                return redirect("event")
        if guest_phone:
            if not re.match(r'^\d{10}$', guest_phone):
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Enter a valid 10-digit phone number"})
                messages.error(request, "Enter a valid 10-digit phone number")
                return redirect("event")

        # Calculate total bill
        from datetime import datetime
        try:
            d1 = datetime.strptime(start_date, "%Y-%m-%d")
            d2 = datetime.strptime(end_date, "%Y-%m-%d")
            days = max(1, (d2 - d1).days + 1)
        except Exception:
            days = 1

        package_price = 0
        if package:
            package_price = sum(service.service_price for service in package.services.all())

        from decimal import Decimal
        total_amount = Decimal((days * hall.hall_price) + package_price)

        customer = None
        if request.user.is_authenticated:
            try:
                customer = Customer.objects.get(user=request.user)
                # Auto-populate details from customer profile if fields are empty
                guest_name = guest_name or (customer.user.get_full_name() or customer.user.username)
                guest_phone = guest_phone or customer.phone
                guest_email = guest_email or customer.user.email
            except:
                customer = None
                guest_name = guest_name or (request.user.get_full_name() or request.user.username)
                guest_phone = guest_phone or ""
                guest_email = guest_email or request.user.email

        from .utils import validate_email_phone_mapping
        is_valid_mapping, mapping_err = validate_email_phone_mapping(guest_email, guest_phone)
        if not is_valid_mapping:
            if is_ajax:
                return JsonResponse({'success': False, 'message': mapping_err})
            messages.error(request, mapping_err)
            return redirect("event")

        requested_points = request.POST.get("redeem_points", 0)
        points_redeemed = 0
        membership_discount = Decimal('0.00')
        discount_amount = Decimal('0.00')
        final_amount = total_amount
        amount_after_membership = total_amount

        if customer:
            apply_discount = request.POST.get("apply_discount") in ["on", "true", "1", "True"]
            if apply_discount:
                membership_discount = calculate_membership_discount(customer, total_amount)
                amount_after_membership = total_amount - membership_discount
            try:
                requested_points_int = int(requested_points or 0)
            except (TypeError, ValueError):
                requested_points_int = 0

            max_redeemable = normalize_redeem_points(
                customer,
                requested_points_int,
                amount_after_membership
            )
            if requested_points_int > customer.loyalty_points:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Redeemed points cannot exceed your available points."})
                messages.error(request, "Redeemed points cannot exceed your available points.")
                return redirect("event")

            points_redeemed = max_redeemable
            discount_amount = membership_discount + Decimal(points_redeemed)
            final_amount = total_amount - discount_amount

        # Both guest and registered user online payment flows require 25% prepayment
        advance_amount = final_amount * Decimal('0.25')
        pending_payment = final_amount * Decimal('0.75')
        payment_status = 'Pending'

        booking = EventBooking.objects.create(
            customer=customer,
            guest_name=guest_name,
            guest_phone=guest_phone,
            guest_email=guest_email,
            hall=hall,
            package=package,
            event_name=event_name,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            food_preference=food_preference,
            guest_count=guest_count,
            special_request=special_request,
            total_amount=total_amount,
            pending_payment=pending_payment,
            points_redeemed=points_redeemed,
            discount_amount=discount_amount,
            final_amount=final_amount,
            advance_amount=advance_amount,
            payment_status=payment_status,
            status="Pending",
            booking_source="Online"
        )
        if customer and points_redeemed:
            redeem_points_for_booking(
                customer,
                booking,
                points_redeemed,
                amount_after_membership
            )
        review_context = _review_context(
            booking_type='event',
            booking_id=booking.id,
            service_name=getattr(hall, 'hall_name', f"Hall {hall.hall_id}"),
            name=booking.guest_name,
            email=booking.guest_email,
            phone=booking.guest_phone,
            amount=booking.advance_amount,
            service_details=[
                ('Hall', getattr(hall, 'hall_name', hall.hall_id)),
                ('Event Date', f"{start_date} to {end_date}"),
                ('Duration', f"{days} day(s)"),
                ('Guests', guest_count),
            ],
            summary_details=[
                ('Subtotal', f"₹{total_amount}"),
                ('Discount', f"-₹{discount_amount}"),
                ('Advance Due Now', f"₹{advance_amount}"),
                ('Final Amount', f"₹{advance_amount}"),
            ],
        )
        if is_ajax:
            return JsonResponse({'success': True, 'review': True, **review_context})
        return render(request, "guest/payment_review.html", review_context)

    packages = Package.objects.all()
    for p in packages:
        p.services_price = sum(s.service_price for s in p.services.all())

    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            customer = None

    return render(request, "booking/event_booking.html", {
        "hall": hall,
        "halls": event_hall.objects.all(),
        "packages": packages,
        "customer": customer
    })
@login_required
def room_booking_dashboard(request):
    room_id = request.GET.get('room_id')
    room = get_object_or_404(Room, id=room_id) if room_id and room_id.isdigit() else None
    rooms = Room.objects.all()
    customer = Customer.objects.filter(user=request.user).first()
    return render(request, 'accounts/room_booking.html', {
        'room': room,
        'rooms': rooms,
        'customer': customer
    })

@login_required
def event_booking_dashboard(request):
    hall_id = request.GET.get('hall_id')
    hall = get_object_or_404(event_hall, hall_id=hall_id) if hall_id and hall_id.isdigit() else None
    customer = None
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        pass
        
    packages = Package.objects.all()
    for p in packages:
        p.services_price = sum(s.service_price for s in p.services.all())

    event_bookings = []
    if customer:
        event_bookings = EventBooking.objects.filter(customer=customer).order_by('-created_at')

    return render(request, 'accounts/event_booking.html', {
        'selected_hall': hall,
        'halls': event_hall.objects.all(),
        'packages': packages,
        'customer': customer,
        'event_bookings': event_bookings
    })

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from adminapp.models import FoodItem
from .models import Order, OrderItem


def food_order(request):

    cart = request.session.get('cart', {})

    cart_items = []
    total = Decimal('0.00')

    for food_id, quantity in cart.items():

        try:
            food = FoodItem.objects.get(id=food_id)

            subtotal = food.price * quantity
            total += subtotal

            cart_items.append({
                'food': food,
                'quantity': quantity,
                'subtotal': subtotal
            })

        except FoodItem.DoesNotExist:
            pass

    gst = total * Decimal('0.05')
    delivery_fee = Decimal('40.00')
    grand_total = total + gst + delivery_fee

    if request.method == "POST":

        order_type = request.POST.get("order_type")
        location_info = request.POST.get("delivery_address", "")
        phone = request.POST.get("phone", "")
        customer_name = request.POST.get("customer_name", "")

        # Validation
        if phone:
            if not re.match(r'^\d{10}$', phone):
                messages.error(request, "Enter a valid 10-digit phone number")
                return redirect('view_cart')

        user = request.user if request.user.is_authenticated else None
        customer = None
        if user:
            customer_name = customer_name or (user.get_full_name() or user.username)
            try:
                customer = Customer.objects.get(user=user)
            except Customer.DoesNotExist:
                pass

        customer_email = request.POST.get('email') or (user.email if user else '')
        from .utils import validate_email_phone_mapping
        is_valid_mapping, mapping_err = validate_email_phone_mapping(customer_email, phone)
        if not is_valid_mapping:
            messages.error(request, mapping_err)
            return redirect('view_cart')

        apply_discount = request.POST.get("apply_discount") in ["on", "true", "1", "True"]
        discount_amount = Decimal('0.00')
        if customer and apply_discount:
            discount_amount = calculate_membership_discount(customer, total)

        discounted_subtotal = total - discount_amount
        gst = discounted_subtotal * Decimal('0.05')
        grand_total = discounted_subtotal + gst + delivery_fee

        request.session['pending_food_order'] = {
            'order_type': order_type,
            'delivery_address': location_info,
            'total_amount': float(grand_total),
            'subtotal_amount': float(total),
            'gst_amount': float(gst),
            'discount_amount': float(discount_amount),
            'customer_phone': phone,
            'customer_name': customer_name,
            'customer_email': request.POST.get('email'),
        }
        request.session.modified = True

        from django.conf import settings
        context = {
            'booking_id': 'pending',
            'booking_type': 'food',
            'amount': float(grand_total),
            'name': customer_name or 'Guest User',
            'email': request.POST.get('email') or (user.email if user else ''),
            'phone': phone,
            'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
        }
        return render(request, "guest/razorpay_payment.html", context)

    return render(
        request,
        'booking/food_order.html',
        {
            'cart_items': cart_items,
            'total': total,
            'gst': gst,
            'delivery_fee': delivery_fee,
            'grand_total': grand_total,
        }
    )

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from adminapp.models import FoodItem
from .models import Order, OrderItem


@login_required
def food_order_dashboard(request):

    if request.method == "POST":
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1'

        cart = request.session.get('cart', {})

        if not cart:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Cart is empty"})
            messages.error(request, "Cart is empty")
            return redirect('view_cart_dashboard')

        order_type = request.POST.get('order_type')
        delivery_address = request.POST.get('delivery_address', '')

        total = Decimal('0.00')

        for food_id, qty in cart.items():
            food = FoodItem.objects.get(id=food_id)
            total += food.price * qty

        gst = total * Decimal('0.05')
        delivery_fee = Decimal('40.00')
        grand_total = total + gst + delivery_fee

        request.session['pending_food_order'] = {
            'order_type': order_type,
            'delivery_address': delivery_address,
            'total_amount': float(grand_total),
            'subtotal_amount': float(total),
            'gst_amount': float(gst),
            'discount_amount': 0.0,
            'customer_phone': getattr(getattr(request.user, "customer", None), "phone", ""),
            'customer_name': request.user.get_full_name() or request.user.username,
            'customer_email': request.user.email,
        }
        request.session.modified = True

        from django.conf import settings
        context = {
            'booking_id': 'pending',
            'booking_type': 'food',
            'amount': float(grand_total),
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'phone': getattr(getattr(request.user, "customer", None), "phone", ""),
            'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
        }
        if is_ajax:
            return JsonResponse({'success': True, 'razorpay': True, **context})
        return render(request, "guest/razorpay_payment.html", context)

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-order_date')

    return render(
        request,
        'accounts/food_menu_dashboard.html',
        {
            'orders': orders
        }
    )
def order_confirmation(request, order_id):

    if request.user.is_authenticated:
        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user
        )
    else:
        order = get_object_or_404(
            Order,
            id=order_id,
            user__isnull=True
        )

    return render(
        request,
        'guest/order_confirmation.html',
        {'order': order}
    )

@login_required
def order_confirmation_dashboard(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
        request,
        'accounts/order_confirmation_dashboard.html',
        {
            'order': order
        }
    )

@login_required
def table_reservation(request):

    if request.method == "POST":

        table_id = request.POST.get("table_id")
        reservation_date = request.POST.get("reservation_date")
        reservation_time = request.POST.get("reservation_time")
        reservation_slot = request.POST.get("reservation_slot")

        if not reservation_time and reservation_slot:
            slot_times = {
                'Breakfast': '08:00',
                'Lunch': '12:00',
                'Dinner': '19:00'
            }
            reservation_time = slot_times.get(reservation_slot)
        guests = request.POST.get("guests")
        special_request = request.POST.get("special_request")

        table = get_object_or_404(
            RestaurantTable,
            id=table_id
        )

        # -------------------------
        # VALIDATION: TIME ALREADY PASSED
        # -------------------------
        current_local_date = timezone.localdate()
        current_local_time = timezone.localtime().time()
        if reservation_date and reservation_time:
            from datetime import datetime as _dt
            try:
                parsed_reservation_date = _dt.strptime(reservation_date, "%Y-%m-%d").date()
                try:
                    booking_res_time = _dt.strptime(reservation_time, "%H:%M").time()
                except ValueError:
                    booking_res_time = _dt.strptime(reservation_time, "%H:%M:%S").time()
                if parsed_reservation_date == current_local_date and booking_res_time <= current_local_time:
                    messages.error(request, "Cannot book a slot for a time that has already started or passed.")
                    return redirect('restaurant_tables')
            except (ValueError, TypeError):
                pass

        available = is_table_available(
            table,
            reservation_date,
            reservation_time,
            duration_hours=2
        )

        if not available:

            messages.error(
                request,
                "This table is already reserved for the selected time."
            )

            return redirect('restaurant_tables')

        TableReservation.objects.create(
            table=table,
            customer_name=request.user.username,
            phone=getattr(getattr(request.user, "customer", None), "phone", ""),
            email=request.user.email,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            guests=guests,
            special_request=special_request,
            status='Confirmed'
        )

        messages.success(
            request,
            "Table reserved successfully!"
        )

        return redirect(
            'table_reservation_dashboard'
        )

    tables = RestaurantTable.objects.filter(
        status='Available'
    )

    return render(
        request,
        'accounts/table_reservation.html',
        {
            'tables': tables
        }
    )

@login_required
def table_reservation_dashboard(request):

    reservations = TableReservation.objects.filter(
        customer_name=request.user.username
    ).exclude(status='Pending').order_by('-created_at')

    return render(
        request,
        'accounts/table_reservation_dashboard.html',
        {
            'reservations': reservations
        }
    )


def table_reservation_confirmation(request, reservation_id):

    reservation = get_object_or_404(
        TableReservation,
        id=reservation_id
    )

    return render(
        request,
        'guest/table_confirmation.html',
        {
            'reservation': reservation
        }
    )
@login_required
def table_confirmation(request, reservation_id):

    reservation = get_object_or_404(TableReservation, id=reservation_id)

    return render(request, "guest/table_confirmation.html", {
        "reservation": reservation
    })

def room_booking_confirmation(request, booking_id):
    booking = get_object_or_404(RoomBooking, id=booking_id)
    # Calculate nights
    try:
        nights = (booking.check_out - booking.check_in).days
        if nights < 1:
            nights = 1
    except Exception:
        nights = 1
    
    return render(
        request,
        'guest/room_confirmation.html',
        {
            'booking': booking,
            'nights': nights,
        }
    )


def event_booking_confirmation(request, booking_id):
    booking = get_object_or_404(EventBooking, id=booking_id)
    try:
        days = (booking.end_date - booking.start_date).days + 1
        if days < 1:
            days = 1
    except Exception:
        days = 1
    
    return render(
        request,
        'guest/event_confirmation.html',
        {
            'booking': booking,
            'days': days,
        }
    )


def download_invoice(request, booking_type, booking_id):
    from django.http import FileResponse, Http404
    from django.shortcuts import get_object_or_404
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
    
    # Authorization & Retrieval
    if booking_type == 'room':
        booking = get_object_or_404(RoomBooking, id=booking_id)
        if booking.customer and booking.customer.user != request.user and not request.user.is_superuser:
            raise Http404("Permission denied")
        title = "Room Booking Invoice"
        filename = f"Invoice_Room_{booking.long_order_id}.pdf"
    elif booking_type == 'event':
        booking = get_object_or_404(EventBooking, id=booking_id)
        if booking.customer and booking.customer.user != request.user and not request.user.is_superuser:
            raise Http404("Permission denied")
        title = "Event Hall Booking Invoice"
        filename = f"Invoice_Event_{booking.long_order_id}.pdf"
    elif booking_type == 'table':
        booking = get_object_or_404(TableReservation, id=booking_id)
        if booking.customer and booking.customer.user != request.user and not request.user.is_superuser:
            raise Http404("Permission denied")
        title = "Table Reservation Invoice"
        filename = f"Invoice_Table_{booking.long_order_id}.pdf"
    elif booking_type == 'food':
        booking = get_object_or_404(Order, id=booking_id)
        if booking.user and booking.user != request.user and not request.user.is_superuser:
            raise Http404("Permission denied")
        title = "Food Order Invoice"
        filename = f"Invoice_Food_{booking.long_order_id}.pdf"
    else:
        raise Http404("Invalid booking type")

    buffer = io.BytesIO()
    # Receipt size (approx 3.15 inches wide)
    doc = SimpleDocTemplate(buffer, pagesize=(240, 800), rightMargin=10, leftMargin=10, topMargin=15, bottomMargin=15)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=colors.black,
        spaceAfter=5,
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.black,
        spaceAfter=15,
        alignment=1
    )
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=5,
        alignment=1
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.black,
        leading=10
    )
    cell_bold_style = ParagraphStyle(
        'CellBoldText',
        parent=styles['Normal'],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.black,
        alignment=1,
        leading=10
    )
    header_cell_style = ParagraphStyle(
        'HeaderCellText',
        parent=styles['Normal'],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=colors.black,
        alignment=0,
        leading=10
    )

    # Header
    story.append(Paragraph("STAYZEN", title_style))
    story.append(Paragraph("Elegant Hospitality & Premium Gastronomy<br/>Invoice & Receipt", subtitle_style))
    story.append(Paragraph("-" * 50, cell_bold_style))
    
    # Build details depending on type
    table_data = []
    
    if booking_type == 'room':
        try:
            nights = (booking.check_out - booking.check_in).days
            if nights < 1:
                nights = 1
        except Exception:
            nights = 1
            
        table_data = [
            [Paragraph("Parameter", header_cell_style), Paragraph("Value", header_cell_style)],
            ["Ref", booking.long_order_id or "-"],
            ["Guest", booking.guest_name or "Walk-in Guest"],
            ["Phone", booking.guest_phone or "-"],
            ["Email", booking.guest_email or "-"],
            ["Room", f"Room {booking.room.room_number} ({booking.room.room_type})"],
            ["Stay", f"{booking.check_in} to {booking.check_out} ({nights} nights)"],
            ["Base Cost", f"INR {booking.total_amount:.2f}"],
            ["Discount", f"INR {booking.discount_amount:.2f}"],
            ["Grand Total", f"INR {booking.final_amount:.2f}"],
            ["Advance", f"INR {booking.advance_amount:.2f}"],
            ["Balance", f"INR {booking.pending_payment:.2f}"],
            ["Payment", booking.payment_status],
            ["Method", booking.payment_method or "At Desk"],
            ["Status", booking.status]
        ]
        
    elif booking_type == 'event':
        try:
            days = (booking.end_date - booking.start_date).days + 1
            if days < 1:
                days = 1
        except Exception:
            days = 1
            
        table_data = [
            [Paragraph("Parameter", header_cell_style), Paragraph("Value", header_cell_style)],
            ["Ref", booking.long_order_id or "-"],
            ["Event", f"{booking.event_name} ({booking.event_type})"],
            ["Guest", booking.guest_name or "-"],
            ["Contact", f"{booking.guest_phone or '-'} / {booking.guest_email or '-'}"],
            ["Hall", booking.hall.hall_name],
            ["Schedule", f"{booking.start_date} to {booking.end_date} ({days} days, {booking.start_time}-{booking.end_time})"],
            ["Guests", f"{booking.guest_count}"],
            ["Food", booking.get_food_preference_display()],
            ["Package", booking.package.package_name if booking.package else "None"],
            ["Hire Cost", f"INR {booking.total_amount:.2f}"],
            ["Discount", f"INR {booking.discount_amount:.2f}"],
            ["Grand Total", f"INR {booking.final_amount:.2f}"],
            ["Advance", f"INR {booking.advance_amount:.2f}"],
            ["Balance", f"INR {booking.pending_payment:.2f}"],
            ["Payment", booking.payment_status],
            ["Method", booking.payment_method or "At Desk"],
            ["Status", booking.status]
        ]
        
    elif booking_type == 'table':
        table_data = [
            [Paragraph("Parameter", header_cell_style), Paragraph("Value", header_cell_style)],
            ["Ref", booking.long_order_id or "-"],
            ["Guest", booking.customer_name],
            ["Phone", booking.phone or "-"],
            ["Email", booking.email or "-"],
            ["Table", f"Table {booking.table.table_number} ({booking.table.location})"],
            ["Schedule", f"{booking.reservation_date} at {booking.reservation_time} ({booking.duration_hours} hrs)"],
            ["Guests", f"{booking.guests}"],
            ["Request", booking.special_request or "None"],
            ["Deposit", f"INR {booking.advance_amount:.2f}"],
            ["Payment", booking.payment_status],
            ["Method", booking.payment_method or "Online"],
            ["Status", booking.status]
        ]
        
    elif booking_type == 'food':
        table_data = [
            [Paragraph("Parameter", header_cell_style), Paragraph("Value", header_cell_style)],
            ["Ref", booking.long_order_id or "-"],
            ["Guest", booking.customer_name or "Walk-in Guest"],
            ["Phone", booking.customer_phone or "-"],
            ["Type", booking.get_order_type_display()],
            ["Date", booking.order_date.strftime('%Y-%m-%d %I:%M %p')],
            ["Details", booking.delivery_address or "Dining In-House"],
            ["Subtotal", f"INR {booking.subtotal_amount:.2f}"],
            ["GST (5%)", f"INR {booking.gst_amount:.2f}"],
            ["Discount", f"INR {booking.discount_amount:.2f}"],
            ["Grand Total", f"INR {booking.total_amount:.2f}"],
            ["Payment", "Fully Paid" if booking.status == "Completed" or booking.invoice_reference else "Paid/Pending"],
            ["Gateway", booking.invoice_reference or "Cash/Card"],
            ["Status", booking.status]
        ]
        
        items = booking.items.select_related('food').all()
        if items.exists():
            food_items_data = [
                [Paragraph("Item", header_cell_style), Paragraph("Qty", header_cell_style), Paragraph("Price", header_cell_style), Paragraph("Subtotal", header_cell_style)]
            ]
            for item in items:
                food_items_data.append([
                    Paragraph(item.food.item_name, cell_style),
                    str(item.quantity),
                    f"{item.food.price:.2f}",
                    f"{item.get_total():.2f}"
                ])
            
    formatted_data = []
    formatted_data.append(table_data[0])
    for row in table_data[1:]:
        formatted_data.append([
            Paragraph(f"<b>{row[0]}</b>", cell_style),
            Paragraph(str(row[1]), cell_style)
        ])
        
    t = Table(formatted_data, colWidths=[70, 150])
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black),
    ]))
    story.append(t)
    
    if booking_type == 'food' and items.exists():
        story.append(Spacer(1, 10))
        story.append(Paragraph("-" * 50, cell_bold_style))
        story.append(Paragraph("Food Items", section_heading))
        t_food = Table(food_items_data, colWidths=[90, 30, 45, 55])
        t_food.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black),
        ]))
        story.append(t_food)
        
    story.append(Spacer(1, 15))
    story.append(Paragraph("-" * 50, cell_bold_style))
    story.append(Paragraph("<b>Thank you for choosing<br/>StayZen!</b>", cell_bold_style))
    
    doc.build(story)
    buffer.seek(0)
    
    return FileResponse(buffer, as_attachment=True, filename=filename)


from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def razorpay_callback(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        booking_id = data.get("booking_id")
        booking_type = data.get("booking_type")
        payment_id = data.get("razorpay_payment_id")

        if not booking_id or not booking_type:
            return JsonResponse({"success": False, "message": "Missing booking ID or type."})

        try:
            from django.urls import reverse
            if booking_type == "room":
                with transaction.atomic():
                    booking = get_object_or_404(RoomBooking.objects.select_for_update(), id=booking_id)
                    if booking.customer_id and booking.points_redeemed:
                        customer = Customer.objects.select_for_update().get(pk=booking.customer_id)
                        redeemable_amount = booking.final_amount + booking.points_redeemed
                        redeem_points_for_booking(
                            customer,
                            booking,
                            booking.points_redeemed,
                            redeemable_amount
                        )
                    booking.payment_status = "Confirmed"
                    booking.status = "Confirmed"
                    booking.payment_method = "Razorpay"
                    booking.booking_reference = payment_id or ""
                    booking.save()
                details = {
                    "id": f"SZ-RM-{booking.id}",
                    "type": "Room Booking",
                    "item": f"Room {booking.room.room_number}",
                    "amount": f"₹{booking.advance_amount:.2f}",
                    "message": "Your room booking is confirmed!"
                }
                if booking.booking_source == 'Offline':
                    redirect_url = reverse('receptionist_room_bookings')
                elif booking.customer:
                    redirect_url = f"{reverse('dashboard')}?booking_confirmed=true&type=Room+Booking&ref=SZ-RM-{booking.id}&amt={booking.advance_amount:.2f}"
                else:
                    redirect_url = reverse('room_booking_confirmation', kwargs={'booking_id': booking.id})
            elif booking_type == "event":
                with transaction.atomic():
                    booking = get_object_or_404(EventBooking.objects.select_for_update(), id=booking_id)
                    if booking.customer_id and booking.points_redeemed:
                        customer = Customer.objects.select_for_update().get(pk=booking.customer_id)
                        redeemable_amount = booking.final_amount + booking.points_redeemed
                        redeem_points_for_booking(
                            customer,
                            booking,
                            booking.points_redeemed,
                            redeemable_amount
                        )
                    booking.payment_status = "Confirmed"
                    booking.status = "Confirmed"
                    booking.payment_method = "Razorpay"
                    booking.booking_reference = payment_id or ""
                    booking.save()
                details = {
                    "id": f"SZ-EV-{booking.id}",
                    "type": "Event Hall Booking",
                    "item": f"{booking.hall.hall_name}",
                    "amount": f"₹{booking.advance_amount:.2f}",
                    "message": "Your event hall booking is confirmed!"
                }
                if booking.booking_source == 'Offline':
                    redirect_url = reverse('receptionist_hall_bookings')
                elif booking.customer:
                    redirect_url = f"{reverse('dashboard')}?booking_confirmed=true&type=Event+Hall+Booking&ref=SZ-EV-{booking.id}&amt={booking.advance_amount:.2f}"
                else:
                    redirect_url = reverse('event_booking_confirmation', kwargs={'booking_id': booking.id})
            elif booking_type == "room_checkout":
                booking = get_object_or_404(RoomBooking, id=booking_id)
                with transaction.atomic():
                    booking.payment_status = "Fully Paid"
                    booking.status = "Completed"
                    booking.payment_method = "Razorpay"
                    booking.booking_reference = payment_id or ""
                    booking.advance_amount = booking.final_amount
                    booking.pending_payment = 0
                    booking.save()
                    # Make room available
                    room = booking.room
                    room.status = 'Available'
                    room.save(update_fields=['status'])
                details = {
                    "id": f"SZ-RM-{booking.id}",
                    "type": "Room Checkout",
                    "item": f"Room {booking.room.room_number}",
                    "amount": f"₹{booking.advance_amount:.2f}",
                    "message": "Room checkout completed successfully!"
                }
                redirect_url = reverse('receptionist_checkout_settlement')
            elif booking_type == "event_checkout":
                booking = get_object_or_404(EventBooking, id=booking_id)
                with transaction.atomic():
                    booking.payment_status = "Fully Paid"
                    booking.status = "Completed"
                    booking.payment_method = "Razorpay"
                    booking.booking_reference = payment_id or ""
                    booking.advance_amount = booking.final_amount
                    booking.pending_payment = 0
                    booking.save()
                    # Make hall available
                    hall = booking.hall
                    hall.hall_status = 'available'
                    hall.save(update_fields=['hall_status'])
                details = {
                    "id": f"SZ-EV-{booking.id}",
                    "type": "Event Checkout",
                    "item": f"{booking.hall.hall_name}",
                    "amount": f"₹{booking.advance_amount:.2f}",
                    "message": "Event checkout completed successfully!"
                }
                redirect_url = reverse('receptionist_checkout_settlement')
            elif booking_type == "food":
                pending_order = request.session.get('pending_food_order')
                if str(booking_id) == 'pending' and pending_order:
                    cart = request.session.get('cart', {})
                    order = Order.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        order_type=pending_order['order_type'],
                        delivery_address=pending_order['delivery_address'],
                        total_amount=pending_order['total_amount'],
                        subtotal_amount=pending_order['subtotal_amount'],
                        gst_amount=pending_order['gst_amount'],
                        discount_amount=pending_order['discount_amount'],
                        status="Confirmed",
                        customer_phone=pending_order['customer_phone'],
                        customer_name=pending_order['customer_name'],
                        customer_email=pending_order.get('customer_email'),
                        invoice_reference=payment_id or ""
                    )
                    for food_id, qty in cart.items():
                        try:
                            food = FoodItem.objects.get(id=food_id)
                            OrderItem.objects.create(order=order, food=food, quantity=qty)
                            food.quantity = max(0, food.quantity - qty)
                            if food.quantity == 0:
                                food.status = 'Unavailable'
                            food.save()
                        except FoodItem.DoesNotExist:
                            pass
                    
                    request.session['cart'] = {}
                    request.session['pending_food_order'] = None
                    request.session.modified = True
                    order.send_confirmation_email()
                else:
                    order = get_object_or_404(Order, id=booking_id)
                    order.status = "Confirmed"
                    order.invoice_reference = payment_id or ""
                    order.save()
                    if order.table_reservation:
                        res = order.table_reservation
                        res.payment_status = "Confirmed"
                        res.status = "Confirmed"
                        res.payment_method = "Razorpay"
                        res.booking_reference = payment_id or ""
                        res.save()
                        if res.table:
                            res.table.status = 'Reserved'
                            res.table.save()

                details = {
                    "id": f"{order.long_order_id}",
                    "type": "Food Order",
                    "item": f"{order.get_order_type_display()}",
                    "amount": f"₹{order.total_amount:.2f}",
                    "message": "Your food order is confirmed!"
                }
                
                if order.booking_source == 'Offline':
                    redirect_url = reverse('receptionist_restaurant_orders')
                elif order.user:
                    redirect_url = f"{reverse('dashboard')}?booking_confirmed=true&type=Food+Order&ref={order.long_order_id}&amt={order.total_amount:.2f}"
                else:
                    redirect_url = reverse('order_confirmation', kwargs={'order_id': order.id})
            elif booking_type == "table":
                reservation = get_object_or_404(TableReservation, id=booking_id)
                reservation.payment_status = "Confirmed"
                reservation.status = "Confirmed"
                reservation.payment_method = "Razorpay"
                reservation.booking_reference = payment_id or ""
                reservation.save()
                if reservation.table:
                    reservation.table.status = 'Reserved'
                    reservation.table.save()
                details = {
                    "id": f"SZ-TB-{reservation.id}",
                    "type": "Table Reservation",
                    "item": f"Table {reservation.table.table_number}",
                    "amount": f"₹{reservation.advance_amount:.2f}",
                    "message": "Your table reservation is confirmed!"
                }
                if reservation.booking_source == 'Offline':
                    redirect_url = reverse('receptionist_table_reservations')
                elif reservation.customer:
                    redirect_url = f"{reverse('dashboard')}?booking_confirmed=true&type=Table+Reservation&ref=SZ-TB-{reservation.id}&amt={reservation.advance_amount:.2f}"
                else:
                    redirect_url = reverse('table_reservation_confirmation', kwargs={'reservation_id': reservation.id})
            elif booking_type == "freshup":
                from .models import FreshUpRoomBooking
                booking = get_object_or_404(FreshUpRoomBooking, id=booking_id)
                with transaction.atomic():
                    booking.payment_status = "Paid"
                    booking.payment_method = "Razorpay"
                    booking.booking_reference = payment_id or ""
                    booking.save()
                    # Occupy the room
                    room = booking.room
                    room.status = 'Occupied'
                    room.save(update_fields=['status'])
                details = {
                    "id": f"SZ-FR-{booking.id}",
                    "type": "Fresh-Up Booking",
                    "item": f"Room {booking.room.room_number}",
                    "amount": f"₹{booking.total_amount:.2f}",
                    "message": "Your hourly fresh-up room booking is confirmed!"
                }
                redirect_url = reverse('receptionist_room_bookings')
            else:
                return JsonResponse({"success": False, "message": "Invalid booking type."})
                
            return JsonResponse({"success": True, "details": details, "redirect_url": redirect_url})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "POST request required."})

# Receptionist Bookings Views
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required

@login_required
def receptionist_room_bookings(request):
    release_expired_freshup_bookings()
    from .models import FreshUpRoomBooking, RoomBooking 

    query = RoomBooking.objects.select_related(
        'customer', 'customer__user', 'room'
    ).prefetch_related(
        'activitybooking_set', 'activitybooking_set__activity'
    ).exclude(status='Pending').order_by('-created_at')

    # Get filter parameters (Replaced 'name' and 'phone' with 'search')
    search_query = request.GET.get('search', '').strip()
    room_no = request.GET.get('room_no', '').strip()
    room_type = request.GET.get('room_type', '').strip()
    status = request.GET.get('status', '').strip()
    membership = request.GET.get('membership', '').strip()

    # Apply unified Search Filter
    if search_query:
        query = query.filter(
            Q(guest_name__icontains=search_query) | 
            Q(customer__user__username__icontains=search_query) | 
            Q(customer__user__first_name__icontains=search_query) | 
            Q(customer__user__last_name__icontains=search_query) |
            Q(guest_phone__icontains=search_query) | 
            Q(customer__phone__icontains=search_query)
        )

    if room_no:
        query = query.filter(room__room_number__icontains=room_no)
    
    if room_type:
        query = query.filter(room__room_type__iexact=room_type)
        
    if status:
        query = query.filter(status__iexact=status)
        
    if membership:
        if membership == 'Registered':
            query = query.filter(customer__isnull=False)
        elif membership == 'Guest':
            query = query.filter(customer__isnull=True)
        else:
            query = query.filter(customer__membership_status__iexact=membership)

    # Base QuerySet for Fresh-Up Bookings
    fresh_query = FreshUpRoomBooking.objects.select_related(
        'room', 'customer', 'customer__user'
    ).order_by('-booking_datetime')

    # Apply unified Search Filter to Fresh-Up Bookings
    if search_query:
        fresh_query = fresh_query.filter(
            Q(customer_name__icontains=search_query) | 
            Q(customer__user__first_name__icontains=search_query) | 
            Q(customer__user__last_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) | 
            Q(customer__phone__icontains=search_query)
        )

    if room_no:
        fresh_query = fresh_query.filter(room__room_number__icontains=room_no)

    if room_type:
        fresh_query = fresh_query.filter(room__room_type__iexact=room_type)

    # status intentionally NOT applied to fresh_query — RoomBooking.status
    # values (Pending/Confirmed/Reserved/Checked In/Cancelled) don't map to
    # FreshUpRoomBooking's fields, so the Status dropdown only affects the
    # main room bookings table.

    if membership:
        if membership == 'Registered':
            fresh_query = fresh_query.filter(customer__isnull=False)
        elif membership == 'Guest':
            fresh_query = fresh_query.filter(customer__isnull=True)
        else:
            fresh_query = fresh_query.filter(customer__membership_status__iexact=membership)

    paginator = Paginator(query, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'fresh_bookings': fresh_query,

        # Pass the unified search string back to the template
        'search': search_query,
        'room_no': room_no,
        'room_type': room_type,
        'status': status,
        'membership': membership,
    }

    return render(request, 'admin/bookings/room_bookings.html', context)

@login_required
def receptionist_hall_bookings(request):
    # Base QuerySet
    query = EventBooking.objects.select_related(
        'customer', 'customer__user', 'hall', 'package'
    ).prefetch_related('package__services').exclude(status='Pending').order_by('-created_at')
    
    # Get filters
    search = request.GET.get('search', '').strip()
    hall_name = request.GET.get('hall_name', '').strip()
    hall_type = request.GET.get('hall_type', '').strip()
    status = request.GET.get('status', '').strip()
    membership = request.GET.get('membership', '').strip()
    
    if search:
        query = query.filter(
            Q(guest_name__icontains=search) | 
            Q(customer__user__username__icontains=search) | 
            Q(customer__user__first_name__icontains=search) | 
            Q(customer__user__last_name__icontains=search) |
            Q(guest_phone__icontains=search) | 
            Q(customer__phone__icontains=search)
        )
    if hall_name:
        query = query.filter(hall__hall_name__icontains=hall_name)
    if hall_type:
        query = query.filter(hall__hall_type=hall_type)
    if status:
        query = query.filter(status__iexact=status)
    if membership:
        if membership == 'Guest': query = query.filter(customer__isnull=True)
        elif membership == 'Registered': query = query.filter(customer__isnull=False)
        else: query = query.filter(customer__membership_status=membership)

    paginator = Paginator(query, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'admin/bookings/hall_bookings.html', {
        'page_obj': page_obj,
        'search': search, 'hall_name': hall_name, 'hall_type': hall_type,
        'status': status, 'membership': membership
    })

@login_required
def receptionist_activity_bookings(request):
    # Base Query
    query = ActivityBooking.objects.select_related(
        'room_booking', 'room_booking__customer', 'room_booking__customer__user', 'room_booking__room', 'activity', 'session'
    ).exclude(status='Pending').order_by('-created_at')
    
    # Capture GET parameters
    search = request.GET.get('search', '').strip()
    room_booking_id = request.GET.get('room_booking_id', '').strip()
    room_no = request.GET.get('room_no', '').strip()
    activity_name = request.GET.get('activity_name', '').strip()
    activity_type = request.GET.get('activity_type', '').strip() # Added
    status = request.GET.get('status', '').strip()
    membership = request.GET.get('membership', '').strip()
    
    if search:
        query = query.filter(
            Q(room_booking__guest_name__icontains=search) | 
            Q(room_booking__guest_phone__icontains=search) |
            Q(room_booking__customer__user__first_name__icontains=search) |
            Q(room_booking__customer__user__last_name__icontains=search) |
            Q(room_booking__customer__phone__icontains=search)
        )
    
    if room_booking_id:
        query = query.filter(room_booking__id=room_booking_id)
        
    if room_no:
        query = query.filter(room_booking__room__room_number__icontains=room_no)
        
    if activity_name:
        query = query.filter(activity__activity_name__icontains=activity_name)

    if activity_type: # Added Filter
        query = query.filter(activity__activity_type=activity_type)
        
    if status:
        query = query.filter(status__iexact=status)
        
    if membership:
        if membership == 'Guest':
            query = query.filter(room_booking__customer__isnull=True)
        elif membership == 'Registered':
            query = query.filter(room_booking__customer__isnull=False)
        else:
            query = query.filter(room_booking__customer__membership_status__iexact=membership)
            
    paginator = Paginator(query, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'room_booking_id': room_booking_id,
        'room_no': room_no,
        'activity_name': activity_name,
        'activity_type': activity_type, # Added
        'status': status,
        'membership': membership
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'admin/bookings/activity_bookings.html', context)
        
    return render(request, 'admin/bookings/activity_bookings.html', context)

@login_required
def receptionist_table_reservations(request):
    query = TableReservation.objects.select_related('table').exclude(status='Pending').order_by('-created_at')
    
    search = request.GET.get('search', '').strip()
    table_no = request.GET.get('table_no', '').strip()
    date_filter = request.GET.get('date', '').strip()
    location = request.GET.get('location', '').strip()
    status = request.GET.get('status', '').strip()
    membership = request.GET.get('membership', '').strip()
    
    if search:
        query = query.filter(Q(phone__icontains=search) | Q(customer_name__icontains=search))
    if table_no:
        query = query.filter(table__table_number__icontains=table_no)
    if date_filter:
        query = query.filter(reservation_date=date_filter)
    if location:
        query = query.filter(table__location=location)
    if status:
        query = query.filter(status=status)
        
    if membership:
        customers = Customer.objects.select_related('user').all()
        if membership == 'Guest':
            cust_phones = [c.phone for c in customers if c.phone]
            cust_usernames = [c.user.username for c in customers]
            query = query.exclude(phone__in=cust_phones).exclude(customer_name__in=cust_usernames)
        elif membership == 'Registered':
            cust_phones = [c.phone for c in customers if c.phone]
            cust_usernames = [c.user.username for c in customers]
            query = query.filter(Q(phone__in=cust_phones) | Q(customer_name__in=cust_usernames))
            
    paginator = Paginator(query, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    res_list = list(page_obj.object_list)
    phones = [r.phone for r in res_list if r.phone]
    names = [r.customer_name for r in res_list if r.customer_name]
    
    customers_map = {}
    for c in Customer.objects.filter(Q(phone__in=phones) | Q(user__username__in=names)).select_related('user'):
        customers_map[c.phone] = c
        customers_map[c.user.username] = c
        
    for r in res_list:
        c = customers_map.get(r.phone) or customers_map.get(r.customer_name)
        if c:
            r.resolved_membership = c.membership_status
            r.is_guest = False
            r.display_name = c.user.get_full_name() or c.user.username
        else:
            r.resolved_membership = 'Guest'
            r.is_guest = True
            r.display_name = r.customer_name

    return render(request, 'admin/bookings/table_reservations.html', {
        'page_obj': page_obj,
        'search': search,
        'table_no': table_no,
        'date': date_filter,
        'location': location,
        'status': status,
        'membership': membership
    })

@login_required
def receptionist_restaurant_orders(request):
    # Retrieve all active orders that need preparation or are being prepared
    query = Order.objects.select_related(
        'user', 'user__customer'
    ).prefetch_related('items__food').filter(
        status__in=['Confirmed', 'Preparing', 'ReadyForPickup', 'Assigned', 'OutForDelivery', 'Completed', 'Delivered']
    ).order_by('-order_date')
    
    phone = request.GET.get('phone', '').strip()
    name = request.GET.get('name', '').strip()
    membership = request.GET.get('membership', '').strip()
    
    if phone:
        query = query.filter(user__customer__phone__icontains=phone)
    if name:
        query = query.filter(Q(user__username__icontains=name) | Q(user__first_name__icontains=name) | Q(user__last_name__icontains=name))
    if membership:
        if membership == 'Guest':
            query = query.filter(user__customer__isnull=True)
        elif membership == 'Registered':
            query = query.filter(user__customer__isnull=False)
        else:
            query = query.filter(user__customer__membership_status=membership)
            
    paginator = Paginator(query, 9999)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for order in page_obj.object_list:
        if order.user:
            customer = getattr(order.user, 'customer', None)
            if customer:
                order.display_name = order.user.get_full_name() or order.user.username
                order.display_phone = customer.phone
                order.resolved_membership = customer.membership_status
                order.is_guest = False
            else:
                order.display_name = order.user.get_full_name() or order.user.username
                order.display_phone = '-'
                order.resolved_membership = 'Registered'
                order.is_guest = True
        else:
            order.display_name = order.customer_name or 'Guest User'
            order.display_phone = order.customer_phone or '-'
            order.resolved_membership = 'Guest'
            order.is_guest = True
    
    return render(request, 'admin/bookings/restaurant_orders.html', {
        'page_obj': page_obj,
        'phone': phone,
        'name': name,
        'membership': membership
    })
    

@login_required
def api_search_customer(request):
    phone = request.GET.get('phone', '').strip()
    if not phone:
        return JsonResponse({'success': False, 'message': 'Phone number is required.'})
    
    try:
        customer = Customer.objects.select_related('user').get(phone=phone)
        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'username': customer.user.username,
                'name': customer.user.get_full_name() or customer.user.username,
                'email': customer.user.email,
                'phone': customer.phone,
                'membership_status': customer.membership_status,
                'loyalty_points': customer.loyalty_points,
            }
        })
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer not found.'})

@login_required
def api_check_guest_email(request):
    email = request.GET.get('email', '').strip()
    if not email:
        return JsonResponse({'exists': False})
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    exists = User.objects.filter(email=email).exists()
    return JsonResponse({'exists': exists})


def _parse_non_negative_int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def release_expired_freshup_bookings():
    from django.utils import timezone
    from datetime import timedelta
    from .models import FreshUpRoomBooking
    from adminapp.models import Room

    now = timezone.now()
    active_freshups = FreshUpRoomBooking.objects.filter(room__status='Occupied')
    for b in active_freshups:
        # prescribed hour + 30 minutes grace period
        expiration_time = b.booking_datetime + timedelta(hours=b.hours_required) + timedelta(minutes=30)
        if now >= expiration_time:
            room = b.room
            other_active = FreshUpRoomBooking.objects.filter(
                room=room,
                booking_datetime__gt=b.booking_datetime
            ).exclude(id=b.id).exists()
            if not other_active:
                room.status = 'Available'
                room.save(update_fields=['status'])


def _build_room_status_payload(room, room_bookings, check_in, check_out):
    from django.utils import timezone
    room_name = f"{room.room_type} Room"
    total_capacity = room.max_adults + room.max_children

    status_key = 'available'
    status_label = 'Available'
    current_status = 'Available'
    selectable = True

    from datetime import timedelta
    today = timezone.localdate()
    now = timezone.now()
    
    is_maintenance = False
    completed_bookings = [b for b in room_bookings if b.status == 'Completed' and b.actual_checkout_at]
    if completed_bookings:
        latest_checkout = max(b.actual_checkout_at for b in completed_bookings)
        if now <= latest_checkout + timedelta(minutes=30):
            is_maintenance = True

    active_bookings = [b for b in room_bookings if b.status not in ['Cancelled', 'Completed']]

    strict_overlaps = [b for b in active_bookings if b.check_in < check_out and b.check_out > check_in]
    has_checkout_on_checkin = any(b.check_out == check_in for b in active_bookings)

    has_active_freshup = False
    if check_in <= today < check_out:
        from .models import FreshUpRoomBooking
        active_freshups = FreshUpRoomBooking.objects.filter(
            room=room
        ).exclude(payment_status='Cancelled')
        for b in active_freshups:
            if not b.booking_datetime:
                continue
            # Convert booking_datetime to local date in Python
            date_str = timezone.localtime(b.booking_datetime).date()
            if date_str != today:
                continue
            if b.payment_status == 'Pending' and now - b.booking_datetime > timedelta(minutes=15):
                continue
            expiration_time = b.booking_datetime + timedelta(hours=b.hours_required) + timedelta(minutes=30)
            if now < expiration_time:
                has_active_freshup = True
                break

    if room.status == 'Not Available':
        status_key = 'blocked'
        status_label = 'Not Available'
        current_status = 'Not Available'
        selectable = False
    elif strict_overlaps or has_active_freshup:
        status_key = 'occupied'
        status_label = 'Occupied / Reserved'
        current_status = 'Occupied'
        selectable = False
    elif is_maintenance and check_in == today:
        status_key = 'cleaning'
        status_label = 'Under Cleaning'
        current_status = 'Maintenance'
        selectable = False
    elif has_checkout_on_checkin:
        status_key = 'checkout'
        status_label = 'Checkout'
        current_status = 'Checkout Today'
        selectable = False
    else:
        status_key = 'available'
        status_label = 'Available'
        current_status = 'Available'
        selectable = True

    return {
        'id': room.id,
        'room_number': room.room_number,
        'room_name': room_name,
        'room_type': room.room_type,
        'capacity': total_capacity,
        'max_adults': room.max_adults,
        'max_children': room.max_children,
        'price': float(room.price),
        'status_key': status_key,
        'status_label': status_label,
        'current_status': current_status,
        'selectable': selectable,
    }


def _build_hall_status_payload(hall, hall_bookings, start_date=None):
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.localdate()
    now = timezone.now()
    
    status_key = 'available'
    status_label = 'Available'
    current_status = 'Available'
    selectable = True
    
    is_maintenance = False
    completed_bookings = [b for b in hall_bookings if b.status == 'Completed' and b.actual_checkout_at]
    if completed_bookings:
        latest_checkout = max(b.actual_checkout_at for b in completed_bookings)
        if now <= latest_checkout + timedelta(minutes=30):
            is_maintenance = True
            
    active_bookings = [b for b in hall_bookings if b.status not in ['Cancelled', 'Completed']]

    if is_maintenance and (start_date is None or start_date <= today):
        status_key = 'cleaning'
        status_label = 'Under Cleaning'
        current_status = 'Maintenance'
        selectable = True
    elif any(b.status == 'Checked In' for b in active_bookings):
        status_key = 'ongoing'
        status_label = 'Ongoing Event'
        current_status = 'Ongoing Event'
        selectable = False
    elif any(b.status == 'Confirmed' or b.payment_status == 'Confirmed' for b in active_bookings):
        status_key = 'booked'
        status_label = 'Booked'
        current_status = 'Booked'
        selectable = False
    elif hall.hall_status == 'booked' or active_bookings:
        status_key = 'blocked'
        status_label = 'Reserved / Blocked'
        current_status = 'Blocked'
        selectable = False

    return {
        'hall_id': hall.hall_id,
        'hall_number': f"H{hall.hall_id:03d}",
        'hall_name': hall.hall_name,
        'hall_type': hall.hall_type,
        'hall_type_display': hall.get_hall_type_display(),
        'hall_capacity': hall.hall_capacity,
        'hall_price': float(hall.hall_price),
        'status_key': status_key,
        'status_label': status_label,
        'current_status': current_status,
        'selectable': selectable,
    }


@login_required
def api_available_rooms(request):
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    adults = _parse_non_negative_int(request.GET.get('adults'), 1)
    children = _parse_non_negative_int(request.GET.get('children'), 0)
    total_guests = adults + children
    
    if not check_in_str or not check_out_str:
        return JsonResponse({'success': False, 'message': 'Both check-in and check-out dates are required.'})
    
    try:
        check_in = parse_date(check_in_str)
        check_out = parse_date(check_out_str)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid date format.'})
        
    release_expired_freshup_bookings()
        
    if not check_in or not check_out:
        return JsonResponse({'success': False, 'message': 'Invalid dates.'})
        
    if check_in > check_out:
        return JsonResponse({'success': False, 'message': 'Check-in date cannot be after check-out date.'})
        
    from django.utils import timezone
    from datetime import timedelta
    
    if check_in == check_out:
        check_out = check_in + timedelta(days=1)
        
    now = timezone.now()
    maintenance_cutoff = now - timedelta(minutes=30)
    
    active_bookings = RoomBooking.objects.filter(
        check_in__lt=check_out,
        check_out__gte=check_in
    ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).select_related('room')
    
    maintenance_bookings = RoomBooking.objects.filter(
        status='Completed',
        actual_checkout_at__gte=maintenance_cutoff
    ).select_related('room')
    
    from itertools import chain
    overlapping_bookings = list(chain(active_bookings, maintenance_bookings))

    bookings_by_room = {}
    for booking in overlapping_bookings:
        bookings_by_room.setdefault(booking.room_id, []).append(booking)

    requested_room_id = request.GET.get('requested_room_id', '').strip()
    try:
        req_room_id = int(requested_room_id)
    except (ValueError, TypeError):
        req_room_id = None

    filtered_rooms = []
    for room in Room.objects.all().order_by('room_number'):
        if req_room_id and room.id == req_room_id:
            filtered_rooms.append(room)
            continue
        room_capacity = room.max_adults + room.max_children
        if room.max_adults < adults or room.max_children < children or room_capacity < total_guests:
            continue
        filtered_rooms.append(room)

    rooms_list = []
    all_rooms = []
    summary = {
        'available': 0,
        'occupied': 0,
        'checkout': 0,
        'cleaning': 0,
        'blocked': 0,
    }

    for room in filtered_rooms:
        room_data = _build_room_status_payload(room, bookings_by_room.get(room.id, []), check_in, check_out)
        if req_room_id and room.id == req_room_id:
            room_data['selectable'] = True
        all_rooms.append(room_data)
        summary[room_data['status_key']] += 1

        if room_data['selectable']:
            rooms_list.append({
                'id': room_data['id'],
                'room_number': room_data['room_number'],
                'room_name': room_data['room_name'],
                'room_type': room_data['room_type'],
                'capacity': room_data['capacity'],
                'price': room_data['price'],
                'max_adults': room_data['max_adults'],
                'max_children': room_data['max_children'],
                'status_key': room_data['status_key'],
                'status_label': room_data['status_label'],
                'current_status': room_data['current_status'],
            })

    return JsonResponse({
        'success': True,
        'rooms': rooms_list,
        'all_rooms': all_rooms,
        'summary': summary,
        'stay_nights': max(1, (check_out - check_in).days),
        'selected': {
            'check_in': str(check_in),
            'check_out': str(check_out),
            'adults': adults,
            'children': children,
        }
    })


@login_required
def api_room_calendar_status(request):
    room_id_str = request.GET.get('room_id', '').strip()
    start_str = request.GET.get('start', '').strip()
    end_str = request.GET.get('end', '').strip()

    if not room_id_str or not room_id_str.isdigit():
        return JsonResponse({'success': False, 'message': 'Valid room_id is required.'})

    start_date = parse_date(start_str) if start_str else None
    end_date = parse_date(end_str) if end_str else None

    if not start_date or not end_date:
        return JsonResponse({'success': False, 'message': 'Valid start and end dates are required.'})

    if start_date > end_date:
        return JsonResponse({'success': False, 'message': 'Start date cannot be after end date.'})

    release_expired_freshup_bookings()

    room = get_object_or_404(Room, id=int(room_id_str))
    end_exclusive = end_date + timedelta(days=1)

    reserved = set()
    not_available = set()
    maintenance = set()

    from django.utils import timezone
    today = timezone.localdate()
    now = timezone.now()
    
    completed_bookings = RoomBooking.objects.filter(
        room_id=room.id, status='Completed', actual_checkout_at__isnull=False
    ).order_by('-actual_checkout_at')[:1]
    
    if completed_bookings:
        latest = completed_bookings[0]
        if now <= latest.actual_checkout_at + timedelta(minutes=30):
            if start_date <= today <= end_date:
                maintenance.add(str(today))
    elif room.status == 'Not Available':
        current = start_date
        while current <= end_date:
            not_available.add(str(current))
            current += timedelta(days=1)

    bookings = RoomBooking.objects.filter(
        room_id=room.id,
        check_in__lt=end_exclusive,
        check_out__gt=start_date,
    ).exclude(status__in=['Cancelled', 'Completed', 'Pending'])

    for b in bookings:
        current = max(b.check_in, start_date)
        stop = min(b.check_out, end_exclusive)
        dates_list = []
        while current < stop:
            dates_list.append(str(current))
            current += timedelta(days=1)

        if b.status in ['Reserved', 'Checked In'] or b.payment_status == 'Confirmed':
            reserved.update(dates_list)
        else:
            not_available.update(dates_list)

    booked = sorted(reserved | not_available | maintenance)
    return JsonResponse({
        'success': True,
        'booked': booked,
        'reserved': sorted(reserved),
        'not_available': sorted(not_available),
        'maintenance': sorted(maintenance),
    })


@login_required
def offline_booking(request):
    from decimal import Decimal
    if request.method == "POST":
        is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        customer_type = request.POST.get('customer_type', 'guest')
        customer_id = request.POST.get('customer_id')
        
        guest_first_name = request.POST.get('guest_first_name', '').strip()
        guest_last_name = request.POST.get('guest_last_name', '').strip()
        guest_gender = request.POST.get('guest_gender', '').strip()
        guest_name = f"{guest_first_name} {guest_last_name}".strip()
        if not guest_name:
            guest_name = request.POST.get('guest_name', '').strip()
        guest_phone = request.POST.get('guest_phone', '').strip()
        guest_email = request.POST.get('guest_email', '').strip()
        guest_address = request.POST.get('guest_address', '').strip()
        
        # Validation
        if not customer_id:
            if guest_email:
                try:
                    validate_email(guest_email)
                except ValidationError:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Enter a valid guest email address"})
                    messages.error(request, "Enter a valid guest email address")
                    return redirect('offline_booking')
            if guest_phone:
                if not re.match(r'^\d{10}$', guest_phone):
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Enter a valid 10-digit phone number"})
                    messages.error(request, "Enter a valid 10-digit phone number")
                    return redirect('offline_booking')

            from .utils import validate_email_phone_mapping
            is_valid_mapping, mapping_err = validate_email_phone_mapping(guest_email, guest_phone)
            if not is_valid_mapping:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': mapping_err})
                messages.error(request, mapping_err)
                return redirect('offline_booking')

        room_id = request.POST.get('room_id')
        check_in_str = request.POST.get('check_in')
        check_out_str = request.POST.get('check_out')
        
        adults = int(request.POST.get('adults', 1))
        children = int(request.POST.get('children', 0))
        
        selected_sessions = request.POST.getlist('activities')
        
        payment_method = request.POST.get('payment_method', 'Cash')
        payment_status = request.POST.get('payment_status', 'Pending')
        
        try:
            advance_amount = Decimal(request.POST.get('advance_amount') or '0.00')
        except Exception:
            advance_amount = Decimal('0.00')
            
        status = request.POST.get('status', 'Pending')
        
        # Validation
        if not room_id or not check_in_str or not check_out_str:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Room, check-in, and check-out dates are required."})
            messages.error(request, "Room, check-in, and check-out dates are required.")
            return redirect('offline_booking')
            
        room = get_object_or_404(Room, id=room_id)
        check_in = parse_date(check_in_str)
        check_out = parse_date(check_out_str)
        
        if not check_in or not check_out:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Invalid dates entered."})
            messages.error(request, "Invalid dates entered.")
            return redirect('offline_booking')
            
        if check_in > check_out:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Check-in cannot be after check-out."})
            messages.error(request, "Check-in cannot be after check-out.")
            return redirect('offline_booking')
            
        # Overlap check
        overlap = RoomBooking.objects.filter(
            room=room,
            check_in__lt=check_out,
            check_out__gt=check_in
        ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).exists()
        
        if overlap:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Room is already booked for these dates."})
            messages.error(request, "Room is already booked for these dates.")
            return redirect('offline_booking')
            
        # Calculations
        days = max(1, (check_out - check_in).days)
        room_cost = Decimal(days) * room.price
        
        customer = None
        if customer_type == 'guest':
            from django.utils.crypto import get_random_string
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            first_name = guest_first_name or (guest_name.split(' ')[0] if guest_name else "")
            last_name = guest_last_name or (guest_name.split(' ', 1)[1] if len(guest_name.split(' ', 1)) > 1 else "")
            
            username = guest_phone if guest_phone else get_random_string(10)
            
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.first_name = first_name
                user.last_name = last_name
                if guest_email:
                    user.email = guest_email
                user.set_password(get_random_string(12))
                user.save()
                
            if not created and not user.first_name:
                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=['first_name', 'last_name'])

            customer, cust_created = Customer.objects.get_or_create(
                user=user,
                defaults={
                    'phone': guest_phone,
                    'address': guest_address,
                    'gender': guest_gender,
                    'membership_status': 'Bronze'
                }
            )
            if not cust_created and guest_gender and not customer.gender:
                customer.gender = guest_gender
                customer.save(update_fields=['gender'])
        elif customer_type == 'registered' and customer_id:
            customer = Customer.objects.filter(id=customer_id).select_related('user').first()

        if customer_type == 'registered' and customer is None:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Please select and verify a registered customer."})
            messages.error(request, "Please select and verify a registered customer.")
            return redirect('offline_booking')

        activities_cost = Decimal('0.00')
        sessions = ActivitySession.objects.none()
        if customer and selected_sessions:
            sessions = ActivitySession.objects.filter(
                id__in=selected_sessions,
                status='Available',
                activity__status='Available'
            ).select_related('activity')
            activities_cost = sum(s.activity.price for s in sessions)
            
        total_amount = room_cost + activities_cost
        
        points_redeemed = 0
        membership_discount = Decimal('0.00')
        discount_amount = Decimal('0.00')
        
        if customer:
            membership_discount = calculate_membership_discount(customer, room_cost)
            amount_after_membership = total_amount - membership_discount
            try:
                requested_points = int(request.POST.get('redeem_points') or 0)
            except (TypeError, ValueError):
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Redeemed points must be a valid number."})
                messages.error(request, "Redeemed points must be a valid number.")
                return redirect('offline_booking')
            if requested_points < 0:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Redeemed points cannot be negative."})
                messages.error(request, "Redeemed points cannot be negative.")
                return redirect('offline_booking')

            max_redeemable = normalize_redeem_points(customer, requested_points, amount_after_membership)
            if requested_points > customer.loyalty_points:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': f"Cannot redeem more than {customer.loyalty_points} points."})
                messages.error(request, f"Cannot redeem more than {customer.loyalty_points} points.")
                return redirect('offline_booking')
            if requested_points > int(amount_after_membership):
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Redeemed points cannot exceed the payable amount."})
                messages.error(request, "Redeemed points cannot exceed the payable amount.")
                return redirect('offline_booking')
            points_redeemed = max_redeemable
            discount_amount = membership_discount + Decimal(points_redeemed)
                
        final_amount = total_amount - discount_amount
        if payment_method == 'Razorpay':
            advance_amount = final_amount * Decimal('0.25')
            pending_payment = final_amount - advance_amount
            payment_status = 'Pending'
            status = 'Pending'
        else:
            pending_payment = max(Decimal('0.00'), final_amount - advance_amount)
            status = 'Confirmed'
            if advance_amount >= final_amount and final_amount > 0:
                payment_status = 'Fully Paid'
            elif advance_amount > 0:
                payment_status = 'Confirmed'
            else:
                payment_status = 'Pending'
        
        with transaction.atomic():
            if customer:
                customer = Customer.objects.select_for_update().select_related('user').get(pk=customer.pk)
                if points_redeemed > customer.loyalty_points:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': f"Cannot redeem more than {customer.loyalty_points} points."})
                    messages.error(request, f"Cannot redeem more than {customer.loyalty_points} points.")
                    return redirect('offline_booking')

            booking = RoomBooking.objects.create(
                customer=customer,
                guest_name=customer.user.get_full_name() or customer.user.username if customer else guest_name,
                guest_phone=customer.phone if customer else guest_phone,
                guest_email=customer.user.email if customer else guest_email,
                guest_address=customer.address if customer else guest_address,
                room=room,
                check_in=check_in,
                check_out=check_out,
                adults=adults,
                children=children,
                status=status,
                total_amount=total_amount,
                pending_payment=pending_payment,
                points_redeemed=points_redeemed,
                discount_amount=discount_amount,
                final_amount=final_amount,
                payment_status=payment_status,
                payment_method=payment_method,
                advance_amount=advance_amount,
                created_by=request.user,
                booking_source='Offline'
            )
            
            # Razorpay deductions happen in the payment callback; counter bookings deduct only after confirmed payment.
            booking_successful = payment_status in ['Confirmed', 'Fully Paid'] or status in ['Confirmed', 'Reserved']
            if customer and points_redeemed and payment_method != 'Razorpay' and booking_successful:
                redeem_points_for_booking(customer, booking, points_redeemed, total_amount - membership_discount)
            
            if customer and payment_method != 'Razorpay' and booking_successful:
                award_points_for_booking(booking)
                
            # Create Activity Bookings
            for session in sessions:
                ActivityBooking.objects.create(
                    room_booking=booking,
                    activity=session.activity,
                    session=session,
                    status='Booked'
                )
            
        if payment_method == 'Razorpay':
            from django.conf import settings
            context = {
                'booking_id': booking.id,
                'booking_type': 'room',
                'amount': float(booking.advance_amount),
                'name': booking.guest_name,
                'email': booking.guest_email or 'guest@example.com',
                'phone': booking.guest_phone,
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'razorpay': True,
                    'context': context
                })
            return render(request, "guest/razorpay_payment.html", context)

        if is_ajax:
            from django.urls import reverse
            return JsonResponse({
                'success': True,
                'razorpay': False,
                'redirect_url': reverse('receptionist_room_bookings'),
                'message': f"Offline booking #{booking.id} created successfully for {booking.guest_name}!"
            })

        messages.success(request, f"Offline booking #{booking.id} created successfully for {booking.guest_name}!")
        return redirect('receptionist_room_bookings')
        
    # GET Request
    activity_sessions = ActivitySession.objects.filter(
        status='Available',
        activity__status='Available'
    ).select_related('activity').order_by('start_time')
    
    rooms = Room.objects.all()
    
    return render(request, 'admin/bookings/offline_booking.html', {
        'activity_sessions': activity_sessions,
        'rooms': rooms
    })


@login_required
def api_available_halls(request):
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    guest_count = max(1, _parse_non_negative_int(request.GET.get('guest_count'), 1))
    
    if not start_date_str or not end_date_str:
        return JsonResponse({'success': False, 'message': 'Both start date and end date are required.'})
        
    try:
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid date format.'})
        
    if not start_date or not end_date:
        return JsonResponse({'success': False, 'message': 'Invalid dates.'})
        
    if start_date > end_date:
        return JsonResponse({'success': False, 'message': 'Start date cannot be after end date.'})
        
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    maintenance_cutoff = now - timedelta(minutes=30)
    
    active_bookings = EventBooking.objects.filter(
        start_date__lte=end_date,
        end_date__gte=start_date
    ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).select_related('hall')
    
    maintenance_bookings = EventBooking.objects.filter(
        status='Completed',
        actual_checkout_at__gte=maintenance_cutoff
    ).select_related('hall')
    
    from itertools import chain
    overlapping_bookings = list(chain(active_bookings, maintenance_bookings))

    bookings_by_hall = {}
    for booking in overlapping_bookings:
        bookings_by_hall.setdefault(booking.hall_id, []).append(booking)

    halls_list = []
    all_halls = []
    summary = {
        'available': 0,
        'booked': 0,
        'ongoing': 0,
        'cleaning': 0,
        'blocked': 0,
    }

    requested_hall_id = request.GET.get('requested_hall_id', '').strip()
    from django.db.models import Q
    try:
        req_id = int(requested_hall_id)
    except (ValueError, TypeError):
        req_id = None

    if req_id:
        filtered_halls = event_hall.objects.filter(
            Q(hall_capacity__gte=guest_count) | Q(hall_id=req_id)
        ).order_by('hall_name')
    else:
        filtered_halls = event_hall.objects.filter(hall_capacity__gte=guest_count).order_by('hall_name')

    for hall in filtered_halls:
        hall_data = _build_hall_status_payload(hall, bookings_by_hall.get(hall.hall_id, []), start_date)
        if req_id and hall.hall_id == req_id:
            hall_data['selectable'] = True
        all_halls.append(hall_data)
        summary[hall_data['status_key']] += 1

        if hall_data['selectable']:
            halls_list.append({
                'hall_id': hall_data['hall_id'],
                'hall_number': hall_data['hall_number'],
                'hall_name': hall_data['hall_name'],
                'hall_type': hall_data['hall_type'],
                'hall_type_display': hall_data['hall_type_display'],
                'hall_capacity': hall_data['hall_capacity'],
                'hall_price': hall_data['hall_price'],
                'status_key': hall_data['status_key'],
                'status_label': hall_data['status_label'],
                'current_status': hall_data['current_status'],
            })

    return JsonResponse({
        'success': True,
        'halls': halls_list,
        'all_halls': all_halls,
        'summary': summary,
        'event_days': max(1, (end_date - start_date).days + 1),
        'selected': {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'guest_count': guest_count,
        }
    })


@login_required
def api_available_tables(request):
    date_str = request.GET.get('date', '').strip()
    time_str = request.GET.get('time', '').strip()
    end_time_str = request.GET.get('end_time', '').strip()
    guests_str = request.GET.get('guests', '1').strip()
    
    if not date_str or not time_str:
        return JsonResponse({'success': False, 'message': 'Both date and time are required.'})
        
    try:
        guests = int(guests_str)
    except ValueError:
        guests = 1

    # Calculate dynamic duration between start and end time
    duration_hours = 2
    if time_str and end_time_str:
        from datetime import datetime as _dt
        try:
            start_t = _dt.strptime(time_str, "%H:%M").time()
            end_t = _dt.strptime(end_time_str, "%H:%M").time()
            diff = (end_t.hour * 60 + end_t.minute) - (start_t.hour * 60 + start_t.minute)
            if diff <= 0:
                diff += 24 * 60
            duration_hours = max(1, diff // 60)
        except (ValueError, TypeError):
            pass
            
    try:
        available_tables = []
        tables = RestaurantTable.objects.exclude(status='Maintenance')
        
        for t in tables:
            # First, check if the table capacity can hold the requested number of guests
            if t.table_capacity >= guests:
                # Then check if it is available for that dynamic duration
                if is_table_available(t, date_str, time_str, duration_hours=duration_hours):
                    available_tables.append({
                        'id': t.id,
                        'table_number': t.table_number,
                        'table_capacity': t.table_capacity,
                        'location': t.location,
                        'price': float(t.price) if getattr(t, 'price', None) else 0.0,
                    })
                    
        return JsonResponse({
            'success': True,
            'tables': available_tables
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    
@login_required
def offline_event_booking(request):
    from decimal import Decimal
    from datetime import datetime
    if request.method == "POST":
        is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        customer_type = request.POST.get('customer_type', 'guest')
        customer_id = request.POST.get('customer_id')
        
        guest_first_name = request.POST.get('guest_first_name', '').strip()
        guest_last_name = request.POST.get('guest_last_name', '').strip()
        guest_gender = request.POST.get('guest_gender', '').strip()
        guest_name = f"{guest_first_name} {guest_last_name}".strip()
        if not guest_name:
            guest_name = request.POST.get('guest_name', '').strip()
        guest_phone = request.POST.get('guest_phone', '').strip()
        guest_email = request.POST.get('guest_email', '').strip()
        guest_address = request.POST.get('guest_address', '').strip()
        
        # Validation
        if not customer_id:
            if guest_email:
                try:
                    validate_email(guest_email)
                except ValidationError:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Enter a valid guest email address"})
                    messages.error(request, "Enter a valid guest email address")
                    return redirect('offline_event_booking')
            if guest_phone:
                if not re.match(r'^\d{10}$', guest_phone):
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Enter a valid 10-digit phone number"})
                    messages.error(request, "Enter a valid 10-digit phone number")
                    return redirect('offline_event_booking')

            from .utils import validate_email_phone_mapping
            is_valid_mapping, mapping_err = validate_email_phone_mapping(guest_email, guest_phone)
            if not is_valid_mapping:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': mapping_err})
                messages.error(request, mapping_err)
                return redirect('offline_event_booking')

        hall_id = request.POST.get('hall_id')
        event_name = request.POST.get('event_name', '').strip()
        event_type = request.POST.get('event_type', 'Other')
        food_preference = request.POST.get('food_preference', 'None')
        
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        guest_count = int(request.POST.get('guest_count', 1))
        package_id = request.POST.get('package_id')
        special_request = request.POST.get('special_request', '').strip()
        
        status = request.POST.get('status', 'Pending')
        payment_status = request.POST.get('payment_status', 'Pending')
        payment_method = request.POST.get('payment_method', 'Cash')
        
        try:
            advance_amount = Decimal(request.POST.get('advance_amount') or '0.00')
        except Exception:
            advance_amount = Decimal('0.00')
            
        # Validation
        if not hall_id or not start_date_str or not end_date_str:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Hall, start date, and end date are required."})
            messages.error(request, "Hall, start date, and end date are required.")
            return redirect('offline_event_booking')
            
        hall = get_object_or_404(event_hall, hall_id=hall_id)
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        
        if not start_date or not end_date:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Invalid dates entered."})
            messages.error(request, "Invalid dates entered.")
            return redirect('offline_event_booking')
            
        if start_date > end_date:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Start date cannot be after end date."})
            messages.error(request, "Start date cannot be after end date.")
            return redirect('offline_event_booking')
            
        # Overlap check
        overlap = EventBooking.objects.filter(
            hall=hall,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).exists()
        
        if overlap:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Event hall is already booked for these dates."})
            messages.error(request, "Event hall is already booked for these dates.")
            return redirect('offline_event_booking')
            
        # Calculations
        days = max(1, (end_date - start_date).days + 1)
        hall_cost = Decimal(days) * hall.hall_price
        
        package = None
        package_cost = Decimal('0.00')
        if package_id:
            package = Package.objects.filter(
                package_id=package_id,
                hall=hall,
                status='available'
            ).first()
            if package is None:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "The selected package is not available for this event hall."})
                messages.error(request, "The selected package is not available for this event hall.")
                return redirect('offline_event_booking')
            package_cost = sum(s.service_price for s in package.services.all())
                
        total_amount = hall_cost + package_cost
        
        customer = None
        if customer_type == 'guest':
            from django.utils.crypto import get_random_string
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            first_name = guest_first_name or (guest_name.split(' ')[0] if guest_name else "")
            last_name = guest_last_name or (guest_name.split(' ', 1)[1] if len(guest_name.split(' ', 1)) > 1 else "")
            
            username = guest_phone if guest_phone else get_random_string(10)
            
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.first_name = first_name
                user.last_name = last_name
                if guest_email:
                    user.email = guest_email
                user.set_password(get_random_string(12))
                user.save()
                
            if not created and not user.first_name:
                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=['first_name', 'last_name'])

            customer, cust_created = Customer.objects.get_or_create(
                user=user,
                defaults={
                    'phone': guest_phone,
                    'address': guest_address,
                    'gender': guest_gender,
                    'membership_status': 'Bronze'
                }
            )
            if not cust_created and guest_gender and not customer.gender:
                customer.gender = guest_gender
                customer.save(update_fields=['gender'])

        points_redeemed = 0
        membership_discount = Decimal('0.00')
        discount_amount = Decimal('0.00')
        if customer_type == 'registered':
            if not customer_id:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Please select and verify a registered customer."})
                messages.error(request, "Please select and verify a registered customer.")
                return redirect('offline_event_booking')
            try:
                customer = Customer.objects.get(id=customer_id)
                membership_discount = calculate_membership_discount(customer, total_amount)
                amount_after_membership = total_amount - membership_discount
                requested_points = int(request.POST.get('redeem_points') or 0)
                max_redeemable = normalize_redeem_points(customer, requested_points, amount_after_membership)
                if requested_points > customer.loyalty_points:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': f"Cannot redeem more than {customer.loyalty_points} points."})
                    messages.error(request, f"Cannot redeem more than {customer.loyalty_points} points.")
                    return redirect('offline_event_booking')
                if requested_points > int(amount_after_membership):
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Redeemed points cannot exceed the payable amount."})
                    messages.error(request, "Redeemed points cannot exceed the payable amount.")
                    return redirect('offline_event_booking')
                points_redeemed = max_redeemable
                discount_amount = membership_discount + Decimal(points_redeemed)
            except (Customer.DoesNotExist, ValueError):
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Please select and verify a registered customer."})
                messages.error(request, "Please select and verify a registered customer.")
                return redirect('offline_event_booking')
                
        final_amount = total_amount - discount_amount
        if payment_method == 'Razorpay':
            advance_amount = final_amount * Decimal('0.25')
            pending_payment = final_amount - advance_amount
            payment_status = 'Pending'
            status = 'Pending'
        else:
            pending_payment = max(Decimal('0.00'), final_amount - advance_amount)
            status = 'Confirmed'
            if advance_amount >= final_amount and final_amount > 0:
                payment_status = 'Fully Paid'
            elif advance_amount > 0:
                payment_status = 'Confirmed'
            else:
                payment_status = 'Pending'
        
        # Create Booking
        booking = EventBooking.objects.create(
            customer=customer,
            guest_name=customer.user.get_full_name() or customer.user.username if customer else guest_name,
            guest_phone=customer.phone if customer else guest_phone,
            guest_email=customer.user.email if customer else guest_email,
            guest_address=customer.address if customer else guest_address,
            hall=hall,
            package=package,
            event_name=event_name,
            event_type=event_type,
            food_preference=food_preference,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time or None,
            end_time=end_time or None,
            guest_count=guest_count,
            special_request=special_request,
            total_amount=total_amount,
            pending_payment=pending_payment,
            points_redeemed=points_redeemed,
            discount_amount=discount_amount,
            final_amount=final_amount,
            payment_status=payment_status,
            payment_method=payment_method,
            advance_amount=advance_amount,
            status=status,
            booking_source='Offline',
            created_by=request.user
        )
        
        # Razorpay deductions happen in the payment callback; non-Razorpay offline bookings are completed here.
        if customer and points_redeemed and payment_method != 'Razorpay':
            redeem_points_for_booking(customer, booking, points_redeemed, total_amount - membership_discount)
            
        if payment_method == 'Razorpay':
            from django.conf import settings
            context = {
                'booking_id': booking.id,
                'booking_type': 'event',
                'amount': float(booking.advance_amount),
                'name': booking.guest_name,
                'email': booking.guest_email or 'guest@example.com',
                'phone': booking.guest_phone,
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'razorpay': True,
                    'context': context
                })
            return render(request, "guest/razorpay_payment.html", context)

        if is_ajax:
            from django.urls import reverse
            return JsonResponse({
                'success': True,
                'razorpay': False,
                'redirect_url': reverse('receptionist_hall_bookings'),
                'message': f"Offline event booking #{booking.id} created successfully for {booking.guest_name}!"
            })

        messages.success(request, f"Offline event booking #{booking.id} created successfully for {booking.guest_name}!")
        return redirect('receptionist_hall_bookings')
        
    # GET Request
    packages = Package.objects.filter(status='available').select_related('hall')
    for p in packages:
        p.services_price = sum(s.service_price for s in p.services.all())
        
    halls = event_hall.objects.all()
    
    return render(request, 'admin/bookings/offline_event_booking.html', {
        'packages': packages,
        'halls': halls
    })


@login_required
def offline_restaurant_table(request):
    from decimal import Decimal
    from django.db import transaction
    
    if request.method == "POST":
        is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        customer_type = request.POST.get('customer_type', 'guest')
        customer_id = request.POST.get('customer_id')
        
        guest_name = request.POST.get('guest_name', '').strip()
        guest_phone = request.POST.get('guest_phone', '').strip()
        guest_email = request.POST.get('guest_email', '').strip()
        guest_address = request.POST.get('guest_address', '').strip()
        
        # Validation
        if not customer_id:
            if guest_email:
                try:
                    validate_email(guest_email)
                except ValidationError:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Enter a valid guest email address"})
                    messages.error(request, "Enter a valid guest email address")
                    return redirect('offline_restaurant_table')
            if guest_phone:
                if not re.match(r'^\d{10}$', guest_phone):
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': "Enter a valid 10-digit phone number"})
                    messages.error(request, "Enter a valid 10-digit phone number")
                    return redirect('offline_restaurant_table')

            from .utils import validate_email_phone_mapping
            is_valid_mapping, mapping_err = validate_email_phone_mapping(guest_email, guest_phone)
            if not is_valid_mapping:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': mapping_err})
                messages.error(request, mapping_err)
                return redirect('offline_restaurant_table')

        book_table = request.POST.get('book_table') == 'on'
        place_order = request.POST.get('place_order') == 'on'
        
        # Table Reservation fields
        table_id = request.POST.get('table_id')
        reservation_date = request.POST.get('reservation_date')
        reservation_time = request.POST.get('reservation_time')
        end_time_str = request.POST.get('end_time')  # Capture end time
        guests = int(request.POST.get('guests', 1))
        
        # Calculate dynamic duration
        duration_hours = 2
        if reservation_time and end_time_str:
            from datetime import datetime as _dt
            try:
                start_t = _dt.strptime(reservation_time, "%H:%M").time()
                end_t = _dt.strptime(end_time_str, "%H:%M").time()
                diff = (end_t.hour * 60 + end_t.minute) - (start_t.hour * 60 + start_t.minute)
                if diff <= 0:
                    diff += 24 * 60
                duration_hours = max(1, diff // 60)
            except (ValueError, TypeError):
                pass
        table_special_request = request.POST.get('table_special_request', '').strip()
        table_status = request.POST.get('table_status', 'Pending')
        table_payment_status = request.POST.get('table_payment_status', 'Pending')
        table_payment_method = request.POST.get('table_payment_method', 'Cash')
        try:
            table_advance_amount = Decimal(request.POST.get('table_advance_amount') or '0.00')
        except Exception:
            table_advance_amount = Decimal('0.00')
            
        # Food Order fields
        order_type = request.POST.get('order_type', 'DineIn')
        delivery_address = request.POST.get('delivery_address', '').strip()
        order_status = request.POST.get('order_status', 'Pending')
        
        # Validation
        if not book_table and not place_order:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "You must select at least Table Reservation or Food Order."})
            messages.error(request, "You must select at least Table Reservation or Food Order.")
            return redirect('offline_restaurant_table')
            
        customer = None
        if customer_type == 'registered':
            if not customer_id:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Please select and verify a registered customer."})
                messages.error(request, "Please select and verify a registered customer.")
                return redirect('offline_restaurant_table')
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': "Please select and verify a registered customer."})
                messages.error(request, "Please select and verify a registered customer.")
                return redirect('offline_restaurant_table')
                
        name = customer.user.get_full_name() or customer.user.username if customer else guest_name
        phone = customer.phone if customer else guest_phone
        email = customer.user.email if customer else guest_email
        address = customer.address if customer else guest_address
        
        if not name or not phone:
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Customer name and phone number are required."})
            messages.error(request, "Customer name and phone number are required.")
            return redirect('offline_restaurant_table')
            
        try:
            with transaction.atomic():
                reservation = None
                
                # Check if Razorpay is selected
                is_razorpay = (table_payment_method == 'Razorpay')
                
                # Force status to Confirmed for Cash, Pending for Razorpay
                actual_table_status = 'Pending' if is_razorpay else 'Confirmed'
                actual_table_payment_status = 'Pending' if is_razorpay else table_payment_status

                # 1. Create Table Reservation
                if book_table:
                    if not table_id or not reservation_date or not reservation_time:
                        raise ValueError("Table, date, and time are required for table reservation.")
                        
                    table = get_object_or_404(RestaurantTable, id=table_id)
                    
                    if not is_table_available(table, reservation_date, reservation_time, duration_hours=duration_hours):
                        raise ValueError(f"Table {table.table_number} is already reserved for the selected date and time.")
                    reservation = TableReservation.objects.create(
                        table=table,
                        customer=customer,
                        customer_name=name,
                        phone=phone,
                        email=email,
                        address=address,
                        reservation_date=reservation_date,
                        reservation_time=reservation_time,
                        guests=guests,
                        special_request=table_special_request,
                        status=actual_table_status,
                        payment_status=actual_table_payment_status,
                        payment_method=table_payment_method,
                        advance_amount=table_advance_amount,
                        booking_source='Offline',
                        created_by=request.user
                    )
                    
                    if actual_table_status == 'Confirmed':
                        table.status = 'Reserved'
                        table.save(update_fields=['status'])
                
                # 2. Create Food Order
                order = None
                if place_order:
                    # Fetch ordered items
                    ordered_items = []
                    for food in FoodItem.objects.filter(status='Available'):
                        qty = int(request.POST.get(f'food_qty_{food.id}', 0))
                        if qty > 0:
                            if food.quantity < qty:
                                  raise ValueError(f"Not enough stock for food item '{food.item_name}'. Available: {food.quantity}")
                            ordered_items.append((food, qty))
                            
                    if not ordered_items:
                        raise ValueError("You must select at least one food item with quantity > 0 for a food order.")
                        
                    subtotal = sum(food.price * qty for food, qty in ordered_items)
                    gst = subtotal * Decimal('0.05')
                    delivery_fee = Decimal('40.00') if order_type == 'Delivery' else Decimal('0.00')
                    total_amount = subtotal + gst + delivery_fee
                    
                    points_redeemed = 0
                    discount_amount = Decimal('0.00')
                    
                    if customer_type == 'registered' and customer:
                        requested_points = int(request.POST.get('redeem_points') or 0)
                        max_redeemable = normalize_redeem_points(customer, requested_points, total_amount)
                        if requested_points > customer.loyalty_points:
                            raise ValueError(f"Cannot redeem more than {customer.loyalty_points} points.")
                        points_redeemed = max_redeemable
                        discount_amount = Decimal(points_redeemed)
                        
                    final_amount = total_amount - discount_amount

                    # --- FIX: mirror the table-status logic above.
                    # Previously this read the raw `order_status` POST value, which the
                    # form always sends as 'Pending' via a hidden input — so every
                    # offline CASH order was silently created with status='Pending' and
                    # excluded from the Restaurant Orders page's status__in filter.
                    actual_order_status = 'Pending' if is_razorpay else 'Confirmed'
                    
                    # Create Order
                    order = Order.objects.create(
                        user=customer.user if customer else None,
                        order_type=order_type,
                        delivery_address=delivery_address or (f"Table {reservation.table.table_number}" if (reservation and order_type == 'DineIn') else ''),
                        total_amount=final_amount,
                        subtotal_amount=subtotal,
                        gst_amount=gst,
                        discount_amount=discount_amount,
                        status=actual_order_status,
                        booking_source='Offline',
                        created_by=request.user,
                        table_reservation=reservation,
                        customer_name=name,
                        customer_phone=phone,
                        customer_email=request.POST.get('email')
                    )
                    
                    # Add items
                    for food, qty in ordered_items:
                        OrderItem.objects.create(
                            order=order,
                            food=food,
                            quantity=qty
                        )
                        food.quantity -= qty
                        if food.quantity == 0:
                            food.status = 'Unavailable'
                        food.save()
                        
                    # Apply loyalty point deduction
                    if customer and points_redeemed:
                        redeem_points_for_booking(customer, order, points_redeemed, total_amount)
            
            # If Razorpay, render checkout template
            if is_razorpay:
                from django.conf import settings
                if place_order and order:
                    pay_amount = float(order.total_amount) + float(table_advance_amount if book_table else 0)
                    context = {
                        'booking_id': order.id,
                        'booking_type': 'food',
                        'amount': pay_amount,
                        'name': name,
                        'email': email or 'guest@example.com',
                        'phone': phone,
                        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
                    }
                else:
                    context = {
                        'booking_id': reservation.id,
                        'booking_type': 'table',
                        'amount': float(table_advance_amount),
                        'name': name,
                        'email': email or 'guest@example.com',
                        'phone': phone,
                        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
                    }
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'razorpay': True,
                        'context': context
                    })
                return render(request, "guest/razorpay_payment.html", context)

            success_msg = "Offline booking successfully created! "
            if book_table:
                success_msg += f"Table reservation #{reservation.id} registered. "
            if place_order and order:
                success_msg += f"Restaurant order #{order.id} placed."
            
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'razorpay': False,
                    'redirect_url': reverse('receptionist_table_reservations') if book_table else reverse('receptionist_restaurant_orders'),
                    'message': success_msg
                })
            
            messages.success(request, success_msg)
            
            if book_table:
                return redirect('receptionist_table_reservations')
            else:
                return redirect('receptionist_restaurant_orders')
                
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f"Error creating booking: {str(e)}"
                })
            messages.error(request, f"Error creating booking: {str(e)}")
            return redirect('offline_restaurant_table')
            
    # GET Request
    food_items = FoodItem.objects.filter(status='Available')
    categories = food_items.values_list('category', flat=True).distinct()
    cuisines = food_items.values_list('cuisine', flat=True).distinct()
    tables = RestaurantTable.objects.exclude(status='Maintenance')
    
    return render(request, 'admin/bookings/offline_restaurant_table.html', {
        'food_items': food_items,
        'categories': categories,
        'cuisines': cuisines,
        'tables': tables
    })


# @login_required
# def process_room_checkout(request, booking_id):
#     from django.db import transaction
#     if request.method == "POST":
#         booking = get_object_or_404(RoomBooking, id=booking_id)
#         if booking.status != 'Checked In':
#             if booking.status in ['Completed', 'Cancelled', 'Checked Out']:
#                 msg = "This booking is already checked out, completed, or cancelled."
#             else:
#                 msg = "Cannot checkout. The guest must be Checked In first."
#             if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
#                 return JsonResponse({'success': False, 'message': msg})
#             messages.error(request, msg)
#             return redirect(request.META.get('HTTP_REFERER', 'receptionist_room_bookings'))
        
#         payment_method = request.POST.get('payment_method', 'Cash')
#         is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        
#         if payment_method == 'Online':
#             from django.conf import settings
#             pay_amount = float(booking.pending_payment)
#             context = {
#                 'booking_id': booking.id,
#                 'booking_type': 'room_checkout',
#                 'amount': pay_amount,
#                 'name': booking.guest_name,
#                 'email': booking.guest_email or 'guest@example.com',
#                 'phone': booking.guest_phone or '',
#                 'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
#             }
#             if is_ajax:
#                 return JsonResponse({
#                     'success': True,
#                     'razorpay': True,
#                     'context': context
#                 })
#             return render(request, "guest/razorpay_payment.html", context)
            
#         try:
#             with transaction.atomic():
#                 booking.payment_method = payment_method
#                 booking.status = 'Completed'
#                 booking.save()
                
#                 # Make room available
#                 room = booking.room
#                 room.status = 'Available'
#                 room.save(update_fields=['status'])
                
#             success_msg = f"Room Booking #{booking.id} checked out successfully!"
#             if is_ajax:
#                 from django.urls import reverse
#                 return JsonResponse({
#                     'success': True,
#                     'razorpay': False,
#                     'redirect_url': request.META.get('HTTP_REFERER', reverse('receptionist_room_bookings')),
#                     'message': success_msg
#                 })
#             messages.success(request, success_msg)
#         except Exception as e:
#             if is_ajax:
#                 return JsonResponse({'success': False, 'message': str(e)})
#             messages.error(request, f"Error checking out booking: {str(e)}")
            
#         return redirect(request.META.get('HTTP_REFERER', 'receptionist_room_bookings'))
    
#     return redirect('receptionist_room_bookings')

@login_required
def process_room_checkout(request, booking_id):
    from django.db import transaction
    if request.method == "POST":
        booking = get_object_or_404(RoomBooking, id=booking_id)
        if booking.status != 'Checked In':
            if booking.status in ['Completed', 'Cancelled', 'Checked Out']:
                msg = "This booking is already checked out, completed, or cancelled."
            else:
                msg = "Cannot checkout. The guest must be Checked In first."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_room_bookings'))
        
        payment_method = request.POST.get('payment_method', 'Cash')
        is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        
        if payment_method == 'Online':
            from django.conf import settings
            pay_amount = float(booking.pending_payment)
            context = {
                'booking_id': booking.id,
                'booking_type': 'room_checkout',
                'amount': pay_amount,
                'name': booking.guest_name,
                'email': booking.guest_email or 'guest@example.com',
                'phone': booking.guest_phone or '',
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'razorpay': True,
                    'context': context
                })
            return render(request, "guest/razorpay_payment.html", context)
            
        try:
            with transaction.atomic():
                booking.payment_method = payment_method
                booking.status = 'Completed'
                booking.actual_checkout_at = timezone.now()
                booking.save()
                
            success_msg = f"Room Booking #{booking.id} checked out successfully!"
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'razorpay': False,
                    'redirect_url': request.META.get('HTTP_REFERER', reverse('receptionist_room_bookings')),
                    'message': success_msg
                })
            messages.success(request, success_msg)
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
            messages.error(request, f"Error checking out booking: {str(e)}")
            
        return redirect(request.META.get('HTTP_REFERER', 'receptionist_room_bookings'))
    
    return redirect('receptionist_room_bookings')
@login_required
def process_event_checkout(request, booking_id):
    from django.db import transaction
    if request.method == "POST":
        booking = get_object_or_404(EventBooking, id=booking_id)
        if booking.status != 'Checked In':
            if booking.status in ['Completed', 'Cancelled', 'Checked Out']:
                msg = "This booking is already checked out, completed, or cancelled."
            else:
                msg = "Cannot checkout. The guest must be Checked In first."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_hall_bookings'))
        
        payment_method = request.POST.get('payment_method', 'Cash')
        is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        
        if payment_method == 'Online':
            from django.conf import settings
            pay_amount = float(booking.pending_payment)
            context = {
                'booking_id': booking.id,
                'booking_type': 'event_checkout',
                'amount': pay_amount,
                'name': booking.guest_name,
                'email': booking.guest_email or 'guest@example.com',
                'phone': booking.guest_phone or '',
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'razorpay': True,
                    'context': context
                })
            return render(request, "guest/razorpay_payment.html", context)
            
        try:
            with transaction.atomic():
                booking.payment_method = payment_method
                booking.status = 'Completed'
                booking.actual_checkout_at = timezone.now()
                booking.save()
                
            success_msg = f"Event Booking #{booking.id} checked out successfully!"
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'razorpay': False,
                    'redirect_url': request.META.get('HTTP_REFERER', reverse('receptionist_hall_bookings')),
                    'message': success_msg
                })
            messages.success(request, success_msg)
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
            messages.error(request, f"Error checking out event: {str(e)}")
            
        return redirect(request.META.get('HTTP_REFERER', 'receptionist_hall_bookings'))
        
    return redirect('receptionist_hall_bookings')


@login_required
def receptionist_checkout_settlement(request):
    active_room_bookings = RoomBooking.objects.filter(
        status='Checked In'
    ).select_related('customer', 'room').prefetch_related('activitybooking_set', 'activitybooking_set__activity').order_by('-created_at')
    
    active_event_bookings = EventBooking.objects.filter(
        status='Checked In'
    ).select_related('customer', 'hall').order_by('-created_at')
    
    room_pending_sum = sum(b.pending_payment for b in active_room_bookings)
    event_pending_sum = sum(b.pending_payment for b in active_event_bookings)
    
    return render(request, 'admin/bookings/checkout_settlement.html', {
        'room_bookings': active_room_bookings,
        'event_bookings': active_event_bookings,
        'room_pending_sum': room_pending_sum,
        'event_pending_sum': event_pending_sum,
        'total_room_count': active_room_bookings.count(),
        'total_event_count': active_event_bookings.count(),
    })


@login_required
def receptionist_checkin(request):
    # Room bookings pending check-in (Confirmed or Reserved status)
    pending_room_bookings = list(
        RoomBooking.objects.filter(
            status__in=['Confirmed', 'Reserved']
        ).select_related('customer', 'room').order_by('-created_at')
    )

    # Annotate each room booking with customer verification info
    for b in pending_room_bookings:
        if b.customer and b.customer.verification_status and b.customer.id_type:
            b.is_verified = True
            b.stored_id_type = b.customer.id_type
        else:
            b.is_verified = False
            b.stored_id_type = None

    # Event bookings pending check-in (Confirmed status)
    pending_event_bookings = EventBooking.objects.filter(
            status__in=['Confirmed']
        ).select_related('customer', 'hall').order_by('-created_at')

    return render(request, 'admin/bookings/checkin.html', {
        'room_bookings': pending_room_bookings,
        'event_bookings': pending_event_bookings,
        'total_room_count': pending_room_bookings.count(),
        'total_event_count': pending_event_bookings.count(),
    })

@login_required
def process_room_checkin(request, booking_id):
    from django.db import transaction
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    if request.method == "POST":
        booking = get_object_or_404(RoomBooking, id=booking_id)
        if booking.status not in ['Confirmed', 'Reserved']:
            messages.error(request, f"Room Booking #{booking.id} cannot be checked in. Current status: {booking.status}")
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))

        customer = booking.customer
        is_verified = customer and customer.verification_status and customer.id_type

        id_type = request.POST.get('id_type')
        id_file = request.FILES.get('id_document')

        # For verified returning customers: id_type falls back to stored value;
        # id_document upload is optional.
        if is_verified:
            id_type = id_type or customer.id_type
        else:
            # New / unverified guests must supply both fields
            if not id_type or not id_file:
                messages.error(request, "Identification Type and Document File are required.")
                return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))

        if not id_type:
            messages.error(request, "Identification Type is required.")
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))

        try:
            with transaction.atomic():
                stored_path = booking.id_number  # default: keep existing value

                if id_file:
                    file_path = f"checkin_ids/{booking.id}_{id_file.name}"
                    stored_path = default_storage.save(file_path, ContentFile(id_file.read()))
                elif is_verified and customer.id_document:
                    stored_path = customer.id_document

                booking.id_type = id_type
                booking.id_number = stored_path
                booking.status = 'Checked In'
                booking.save()

                # Persist id_type on the Customer profile and mark as verified
                if customer:
                    customer.id_type = id_type
                    customer.verification_status = True
                    if id_file:
                        customer.id_document = stored_path
                    customer.save(update_fields=['id_type', 'verification_status', 'id_document'])

                # Make room occupied
                room = booking.room
                room.status = 'Occupied'
                room.save(update_fields=['status'])

            messages.success(request, f"Guest checked in to Room {room.room_number} successfully!")
        except Exception as e:
            messages.error(request, f"Error checking in: {str(e)}")

        return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))

    return redirect('receptionist_checkin')


@login_required
def process_event_checkin(request, booking_id):
    from django.db import transaction
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    
    if request.method == "POST":
        booking = get_object_or_404(EventBooking, id=booking_id)
        if booking.status != 'Confirmed':
            messages.error(request, f"Event Booking #{booking.id} cannot be checked in. Current status: {booking.status}")
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))
            
        customer = booking.customer
        is_verified = customer and customer.verification_status and customer.id_type

        id_type = request.POST.get('id_type')
        id_file = request.FILES.get('id_document')
        
        # For verified returning customers: id_type falls back to stored value;
        # id_document upload is optional.
        if is_verified:
            id_type = id_type or customer.id_type
        else:
            if not id_type or not id_file:
                messages.error(request, "Identification Type and Document File are required.")
                return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))
                
        if not id_type:
            messages.error(request, "Identification Type is required.")
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_checkin'))
            
        try:
            with transaction.atomic():
                stored_path = booking.id_number  # default: keep existing value

                if id_file:
                    file_path = f"event_checkin_ids/{booking.id}_{id_file.name}"
                    stored_path = default_storage.save(file_path, ContentFile(id_file.read()))
                elif is_verified and customer.id_document:
                    stored_path = customer.id_document
                
                booking.id_type = id_type
                booking.id_number = stored_path
                booking.status = 'Checked In'
                booking.save()
                
                # Persist id_type on the Customer profile and mark as verified
                if customer:
                    customer.id_type = id_type
                    customer.verification_status = True
                    if id_file:
                        customer.id_document = stored_path
                    customer.save(update_fields=['id_type', 'verification_status', 'id_document'])
            
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            success_msg = f"Guest checked in to Event Hall '{booking.hall.hall_name}' successfully!"
            
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'razorpay': False,
                    'redirect_url': request.META.get('HTTP_REFERER', reverse('receptionist_hall_bookings')),
                    'message': success_msg
                })
            messages.success(request, success_msg)
        except Exception as e:
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
            messages.error(request, f"Error checking in event: {str(e)}")
            
        return redirect(request.META.get('HTTP_REFERER', 'receptionist_hall_bookings'))
    
    return redirect('receptionist_checkin')


@login_required
def process_event_checkout(request, booking_id):
    from django.db import transaction
    if request.method == "POST":
        booking = get_object_or_404(EventBooking, id=booking_id)
        if booking.status != 'Checked In':
            if booking.status in ['Completed', 'Cancelled', 'Checked Out']:
                msg = "This booking is already checked out, completed, or cancelled."
            else:
                msg = "Cannot checkout. The guest must be Checked In first."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return redirect(request.META.get('HTTP_REFERER', 'receptionist_hall_bookings'))
        
        payment_method = request.POST.get('payment_method', 'Cash')
        is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
        
        if payment_method == 'Online':
            from django.conf import settings
            pay_amount = float(booking.pending_payment)
            context = {
                'booking_id': booking.id,
                'booking_type': 'event_checkout',
                'amount': pay_amount,
                'name': booking.guest_name,
                'email': booking.guest_email or 'guest@example.com',
                'phone': booking.guest_phone or '',
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'razorpay': True,
                    'context': context
                })
            return render(request, "guest/razorpay_payment.html", context)
            
        try:
            with transaction.atomic():
                booking.payment_method = payment_method
                booking.status = 'Completed'
                from django.utils import timezone
                booking.actual_checkout_at = timezone.now()
                booking.save()
                
                # Make hall available
                hall = booking.hall
                hall.hall_status = 'available'
                hall.save(update_fields=['hall_status'])
                
            success_msg = f"Event Booking #{booking.id} checked out successfully!"
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({
                    'success': True,
                    'razorpay': False,
                    'redirect_url': request.META.get('HTTP_REFERER', reverse('receptionist_hall_bookings')),
                    'message': success_msg
                })
            messages.success(request, success_msg)
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
            messages.error(request, f"Error checking out event: {str(e)}")
            
        return redirect(request.META.get('HTTP_REFERER', 'receptionist_hall_bookings'))
        
    return redirect('receptionist_hall_bookings')


@login_required
def receptionist_checkout_settlement(request):
    active_room_bookings = RoomBooking.objects.filter(
        status='Checked In'
    ).select_related('customer', 'room').prefetch_related('activitybooking_set', 'activitybooking_set__activity').order_by('-created_at')
    
    active_event_bookings = EventBooking.objects.filter(
        status='Checked In'
    ).select_related('customer', 'hall').order_by('-created_at')
    
    room_pending_sum = sum(b.pending_payment for b in active_room_bookings)
    event_pending_sum = sum(b.pending_payment for b in active_event_bookings)
    
    return render(request, 'admin/bookings/checkout_settlement.html', {
        'room_bookings': active_room_bookings,
        'event_bookings': active_event_bookings,
        'room_pending_sum': room_pending_sum,
        'event_pending_sum': event_pending_sum,
        'total_room_count': active_room_bookings.count(),
        'total_event_count': active_event_bookings.count(),
    })


@login_required
def receptionist_checkin(request):
    # Room bookings pending check-in (Confirmed or Reserved status)
    pending_room_bookings = RoomBooking.objects.filter(
        status__in=['Confirmed', 'Reserved']
    ).select_related('customer', 'room').order_by('-created_at')
    
    # Event bookings pending check-in (Confirmed status)
    pending_event_bookings = EventBooking.objects.filter(
        status__in=['Confirmed']
    ).select_related('customer', 'hall').order_by('-created_at')
    
    return render(request, 'admin/bookings/checkin.html', {
        'room_bookings': pending_room_bookings,
        'event_bookings': pending_event_bookings,
        'total_room_count': pending_room_bookings.count(),
        'total_event_count': pending_event_bookings.count(),
    })



@login_required
def offline_fresh_up_booking(request):
    from decimal import Decimal
    from adminapp.models import Room
    from .models import FreshUpRoomBooking
    from django.http import JsonResponse
    from django.urls import reverse
    
    if request.method == "POST":
        room_id = request.POST.get('room_id')
        customer_id = request.POST.get('customer_id')
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        customer_address = request.POST.get('customer_address', '').strip()
        hours_required = request.POST.get('hours_required')
        price_per_hour = request.POST.get('price_per_hour')
        payment_method = request.POST.get('payment_method', 'Cash')
        
        if not all([room_id, customer_name, customer_phone, hours_required, price_per_hour]):
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            if is_ajax:
                return JsonResponse({'success': False, 'message': "All required fields must be filled."})
            messages.error(request, "All required fields must be filled.")
            return redirect('offline_fresh_up_booking')
            
        try:
            hours_required = int(hours_required)
            price_per_hour = Decimal(price_per_hour)
            total_amount = Decimal(hours_required) * price_per_hour
        except Exception:
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Invalid numeric values provided."})
            messages.error(request, "Invalid numeric values provided.")
            return redirect('offline_fresh_up_booking')
            
        room = get_object_or_404(Room, id=room_id)
        
        from django.utils import timezone
        from datetime import timedelta
        from .models import RoomBooking
        
        # Clean up expired freshup bookings first
        release_expired_freshup_bookings()
        room.refresh_from_db()
        
        today = timezone.localdate()
        now = timezone.now()
        
        # Block any room that is not actually free for a fresh-up stay.
        if room.status in ['Not Available', 'Occupied']:
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            err_msg = f"Room {room.room_number} is currently not available for fresh-up booking."
            if is_ajax:
                return JsonResponse({'success': False, 'message': err_msg})
            messages.error(request, err_msg)
            return redirect('offline_fresh_up_booking')
            
        # 1. Overlapping normal stay booking check today
        has_stay_overlap = RoomBooking.objects.filter(
            room=room,
            check_in__lte=today,
            check_out__gt=today
        ).exclude(status__in=['Cancelled', 'Completed', 'Pending']).exists()
        
        if has_stay_overlap:
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            err_msg = f"Room {room.room_number} is already booked or occupied by a normal stay booking today."
            if is_ajax:
                return JsonResponse({'success': False, 'message': err_msg})
            messages.error(request, err_msg)
            return redirect('offline_fresh_up_booking')
            
        # 2. Overlapping active fresh-up booking check today
        active_freshups = FreshUpRoomBooking.objects.filter(
            room=room,
            booking_datetime__date=today
        ).exclude(payment_status='Cancelled')
        
        has_freshup_overlap = False
        for b in active_freshups:
            # If Razorpay payment is pending, treat it as active only for the first 15 minutes
            if b.payment_status == 'Pending' and now - b.booking_datetime > timedelta(minutes=15):
                continue
            expiration_time = b.booking_datetime + timedelta(hours=b.hours_required) + timedelta(minutes=30)
            if now < expiration_time:
                has_freshup_overlap = True
                break
                
        if has_freshup_overlap:
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            err_msg = f"Room {room.room_number} is currently occupied by another active fresh-up booking."
            if is_ajax:
                return JsonResponse({'success': False, 'message': err_msg})
            messages.error(request, err_msg)
            return redirect('offline_fresh_up_booking')
            
        # 3. Dynamic Maintenance check
        completed_stays = RoomBooking.objects.filter(
            room=room, status='Completed', actual_checkout_at__isnull=False
        ).order_by('-actual_checkout_at')[:1]
        
        if completed_stays:
            latest = completed_stays[0]
            if now <= latest.actual_checkout_at + timedelta(minutes=30):
                is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
                err_msg = f"Room {room.room_number} is currently under cleaning/maintenance after a recent checkout."
                if is_ajax:
                    return JsonResponse({'success': False, 'message': err_msg})
                messages.error(request, err_msg)
                return redirect('offline_fresh_up_booking')


        customer = None
        if customer_id:
            from accountapp.models import Customer
            customer = Customer.objects.filter(id=customer_id).first()
        
        is_razorpay = (payment_method == 'Razorpay')
        actual_payment_status = 'Pending' if is_razorpay else 'Paid'
        
        try:
            booking = FreshUpRoomBooking.objects.create(
                room=room,
                customer=customer,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_address=customer_address,
                customer_email=request.POST.get('customer_email'),
                hours_required=hours_required,
                price_per_hour=price_per_hour,
                total_amount=total_amount,
                payment_status=actual_payment_status,
                payment_method=payment_method,
                created_by=request.user
            )
            
            if not is_razorpay:
                # Change room status to Occupied for Cash booking
                room.status = 'Occupied'
                room.save(update_fields=['status'])
                
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            if is_ajax:
                if is_razorpay:
                    from django.conf import settings
                    context = {
                        'booking_id': booking.id,
                        'booking_type': 'freshup',
                        'amount': float(total_amount),
                        'name': customer_name,
                        'email': (customer.user.email if (customer and customer.user) else '') or 'guest@example.com',
                        'phone': customer_phone,
                        'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
                    }
                    return JsonResponse({
                        'success': True,
                        'razorpay': True,
                        'context': context
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'razorpay': False,
                        'redirect_url': reverse('receptionist_room_bookings'),
                        'message': f"Fresh-Up Room Booked successfully! Total: INR {total_amount}"
                    })
        except Exception as e:
            import traceback
            traceback.print_exc()
            is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1')
            if is_ajax:
                return JsonResponse({'success': False, 'message': f"Internal Error: {str(e)}"})
            messages.error(request, f"Internal Error: {str(e)}")
            return redirect('offline_fresh_up_booking')
        
        if is_razorpay:
            from django.conf import settings
            context = {
                'booking_id': booking.id,
                'booking_type': 'freshup',
                'amount': float(total_amount),
                'name': customer_name,
                'email': (customer.user.email if (customer and customer.user) else '') or 'guest@example.com',
                'phone': customer_phone,
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            return render(request, "guest/razorpay_payment.html", context)
            
        messages.success(request, f"Fresh-Up Room Booked successfully! Total: INR {total_amount}")
        return redirect('receptionist_room_bookings')
        
    release_expired_freshup_bookings()

    room_id_str = request.GET.get('room_id', '').strip()
    try:
        req_room_id = int(room_id_str)
    except (ValueError, TypeError):
        req_room_id = None

    # Keep the clicked room available in the form so it can be preselected
    # from the calendar, while POST-time validation still blocks invalid bookings.
    if req_room_id:
        from django.db.models import Q
        base_rooms = Room.objects.filter(Q(status='Available') | Q(id=req_room_id))
    else:
        base_rooms = Room.objects.filter(status='Available')
        
    from django.utils import timezone
    from datetime import timedelta
    from .models import RoomBooking
    
    now = timezone.now()
    available_rooms = []
    
    for r in base_rooms:
        if req_room_id and r.id == req_room_id:
            available_rooms.append(r)
            continue
            
        completed_stays = RoomBooking.objects.filter(
            room=r, status='Completed', actual_checkout_at__isnull=False
        ).order_by('-actual_checkout_at')[:1]
        
        if completed_stays:
            latest = completed_stays[0]
            if now <= latest.actual_checkout_at + timedelta(minutes=30):
                continue
                
        available_rooms.append(r)
        
    return render(request, 'admin/bookings/offline_fresh_up_booking.html', {
        'available_rooms': available_rooms
    })


import json
from django.views.decorators.http import require_POST
from django.http import JsonResponse

@login_required
@require_POST
def toggle_serving_status(request, order_id):
    try:
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
            
        order = get_object_or_404(Order, id=order_id)
        
        is_delivery = (order.order_type == 'Delivery')

        if order.serving_status == 'Preparing':
            order.serving_status = 'Completed'
            if is_delivery:
                # For delivery orders, 'Completed' in kitchen means it's 'ReadyForPickup' for delivery staff
                order.status = 'ReadyForPickup'
            else:
                # For dine-in / takeaway, kitchen 'Completed' means the whole order is 'Completed'
                order.status = 'Completed'
        else:
            order.serving_status = 'Preparing'
            order.status = 'Preparing'
            
        order.save(update_fields=['serving_status', 'status'])
        try:
            order.send_status_update_email()
        except Exception as e:
            print(f"Error sending email on serving status update: {e}")
        
        return JsonResponse({'success': True, 'new_status': order.serving_status})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def track_restaurant_order(request, tracking_token):
    order = get_object_or_404(Order, long_order_id=tracking_token)
    items = order.items.all()
    guest_name = order.customer_name or (order.user.get_full_name() if order.user else 'Guest')
    return render(request, 'guest/track_food_order.html', {
        'order': order,
        'items': items,
        'guest_name': guest_name,
    })


@transaction.atomic
def payment_failure(request):
    if request.method == "POST":
        import json
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        booking_id = data.get("booking_id")
        booking_type = data.get("booking_type")

        if not booking_id or not booking_type:
            return JsonResponse({"success": False, "message": "Missing booking ID or type."})

        try:
            if booking_type == "room":
                booking = RoomBooking.objects.filter(id=booking_id).first()
                if booking:
                    if booking.status == "Pending" and booking.payment_status == "Pending":
                        booking.delete()
                        return JsonResponse({"success": True, "message": "Pending booking cleaned up successfully."})
                    else:
                        return JsonResponse({"success": False, "message": "Booking is not in Pending status; cleanup skipped."})
                else:
                    return JsonResponse({"success": False, "message": "Booking not found."})
            elif booking_type == "event":
                booking = EventBooking.objects.filter(id=booking_id).first()
                if booking:
                    if booking.status == "Pending" and booking.payment_status == "Pending":
                        booking.delete()
                        return JsonResponse({"success": True, "message": "Pending booking cleaned up successfully."})
                    else:
                        return JsonResponse({"success": False, "message": "Booking is not in Pending status; cleanup skipped."})
                else:
                    return JsonResponse({"success": False, "message": "Booking not found."})
            elif booking_type == "table":
                from .models import TableReservation
                booking = TableReservation.objects.filter(id=booking_id).first()
                if booking:
                    if booking.status == "Pending" and booking.payment_status == "Pending":
                        booking.delete()
                        return JsonResponse({"success": True, "message": "Pending booking cleaned up successfully."})
                    else:
                        return JsonResponse({"success": False, "message": "Booking is not in Pending status; cleanup skipped."})
                else:
                    return JsonResponse({"success": False, "message": "Booking not found."})
            else:
                return JsonResponse({"success": False, "message": "Invalid booking type for payment failure cleanup."})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error executing safe payment failure cleanup for booking {booking_id} of type {booking_type}: {e}")
            return JsonResponse({"success": False, "message": "An error occurred during payment failure cleanup."})

    return JsonResponse({"success": False, "message": "POST request required."})


@login_required
def resume_payment(request, booking_type, booking_id):
    from django.utils import timezone
    from datetime import timedelta
    from django.conf import settings
    from django.contrib import messages
    
    # 10 minutes limit
    expiration_limit = timezone.now() - timedelta(minutes=10)
    
    try:
        if booking_type == "room":
            booking = RoomBooking.objects.filter(id=booking_id).first()
            if not booking:
                messages.error(request, "Booking not found.")
                return redirect("my_bookings")
            
            if booking.status != "Pending" or booking.payment_status != "Pending":
                messages.error(request, "This booking cannot be resumed.")
                return redirect("my_bookings")
                
            if booking.created_at < expiration_limit:
                booking.delete()
                messages.error(request, "The payment window of 10 minutes has expired. Booking deleted.")
                return redirect("my_bookings")
                
            context = {
                'booking_id': booking.id,
                'booking_type': 'room',
                'amount': float(booking.advance_amount),
                'name': booking.guest_name,
                'email': booking.guest_email,
                'phone': booking.guest_phone,
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            return render(request, "guest/razorpay_payment.html", context)
            
        elif booking_type == "event":
            booking = EventBooking.objects.filter(id=booking_id).first()
            if not booking:
                messages.error(request, "Booking not found.")
                return redirect("my_bookings")
                
            if booking.status != "Pending" or booking.payment_status != "Pending":
                messages.error(request, "This booking cannot be resumed.")
                return redirect("my_bookings")
                
            if booking.created_at < expiration_limit:
                booking.delete()
                messages.error(request, "The payment window of 10 minutes has expired. Booking deleted.")
                return redirect("my_bookings")
                
            context = {
                'booking_id': booking.id,
                'booking_type': 'event',
                'amount': float(booking.advance_amount),
                'name': booking.guest_name,
                'email': booking.guest_email,
                'phone': booking.guest_phone,
                'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
            }
            return render(request, "guest/razorpay_payment.html", context)
            
        else:
            messages.error(request, "Invalid booking type.")
            return redirect("my_bookings")
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error resuming payment for booking {booking_id} of type {booking_type}: {e}")
        messages.error(request, f"Error resuming payment: {str(e)}")
        return redirect("my_bookings")



def payment_start(request, booking_type, booking_id):
    if request.method != "POST":
        return redirect("home")

    from django.conf import settings

    if booking_type == "room":
        booking = get_object_or_404(RoomBooking, id=booking_id)
        context = {
            'booking_id': booking.id,
            'booking_type': 'room',
            'amount': float(booking.advance_amount),
            'name': booking.guest_name,
            'email': booking.guest_email,
            'phone': booking.guest_phone,
            'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
        }

    elif booking_type == "event":
        booking = get_object_or_404(EventBooking, id=booking_id)
        context = {
            'booking_id': booking.id,
            'booking_type': 'event',
            'amount': float(booking.advance_amount),
            'name': booking.guest_name,
            'email': booking.guest_email,
            'phone': booking.guest_phone,
            'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
        }

    elif booking_type == "food":
        pending = request.session.get('pending_food_order')
        if not pending:
            messages.error(request, "Your order session expired. Please re-order.")
            return redirect("view_cart")
        context = {
            'booking_id': 'pending',
            'booking_type': 'food',
            'amount': pending['total_amount'],
            'name': pending['customer_name'] or 'Guest User',
            'email': pending.get('customer_email') or '',
            'phone': pending['customer_phone'],
            'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
        }

    else:
        messages.error(request, "Invalid booking type.")
        return redirect("home")

    return render(request, "guest/razorpay_payment.html", context)


def _review_context(booking_type, booking_id, service_name, name, email, phone, amount,
                     service_details=None, guest_details=None, offer_details=None, summary_details=None):
    """Builds the context dict consumed by guest/payment_review.html for any booking type."""
    return {
        'booking_type': booking_type,
        'booking_id': booking_id,
        'service_name': service_name,
        'name': name,
        'email': email,
        'phone': phone,
        'amount': amount,
        'service_details': service_details or [],
        'guest_details': guest_details or [],
        'offer_details': offer_details or [],
        'summary_details': summary_details or [],
    }


from django.views.decorators.cache import never_cache

@never_cache
def api_check_email_exists(request):
    from django.contrib.auth import get_user_model
    from django.http import JsonResponse
    User = get_user_model()
    email = request.GET.get("email", "")
    exists = User.objects.filter(email__iexact=email).exists() if email else False
    return JsonResponse({"exists": exists})
