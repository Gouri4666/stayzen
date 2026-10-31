from datetime import datetime, timedelta
from .models import TableReservation

def is_table_available(table, date, time, duration_hours=2):

    # 🔥 FIX: convert string → datetime objects
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return False  # Invalid date format, return not available

    if isinstance(time, str):
        try:
            time = datetime.strptime(time, "%H:%M").time()
        except ValueError:
            try:
                time = datetime.strptime(time, "%H:%M:%S").time()
            except ValueError:
                return False

    new_start = datetime.combine(date, time)
    new_end = new_start + timedelta(hours=duration_hours)

    bookings = TableReservation.objects.filter(
        table=table,
        status__in=["Pending", "Confirmed"]
    )

    for b in bookings:
        existing_start = datetime.combine(
            b.reservation_date,
            b.reservation_time
        )
        existing_end = existing_start + timedelta(hours=b.duration_hours)

        if new_start < existing_end and new_end > existing_start:
            return False

    return True

def calculate_duration_hours(start_time_str, end_time_str):
    import math
    if not start_time_str or not end_time_str:
        return 2
    try:
        try:
            start_t = datetime.strptime(start_time_str, "%H:%M").time()
        except ValueError:
            start_t = datetime.strptime(start_time_str, "%H:%M:%S").time()
            
        try:
            end_t = datetime.strptime(end_time_str, "%H:%M").time()
        except ValueError:
            end_t = datetime.strptime(end_time_str, "%H:%M:%S").time()
            
        dummy_date = datetime.now().date()
        start_dt = datetime.combine(dummy_date, start_t)
        end_dt = datetime.combine(dummy_date, end_t)
        
        if end_dt <= start_dt:
            # Assume crossing midnight if end time is before start time
            end_dt += timedelta(days=1)
            
        diff_seconds = (end_dt - start_dt).total_seconds()
        return max(1, int(math.ceil(diff_seconds / 3600.0)))
    except Exception:
        return 2


def validate_email_phone_mapping(email, phone):
    if not email and not phone:
        return True, ""
        
    from accountapp.models import Customer
    from django.contrib.auth import get_user_model
    from bookingapp.models import RoomBooking, EventBooking
    
    User = get_user_model()
    
    email = email.strip() if email else ""
    phone = phone.strip() if phone else ""
    
    if email:
        users = User.objects.filter(email=email)
        for u in users:
            customer = Customer.objects.filter(user=u).first()
            if customer and customer.phone and phone and customer.phone != phone:
                return False, f"Email {email} is already registered with a different phone number."
                
        rb_email = RoomBooking.objects.filter(guest_email=email).exclude(guest_phone="").first()
        if rb_email and phone and rb_email.guest_phone != phone:
            return False, f"Email {email} has been used with a different phone number in past bookings."
            
        eb_email = EventBooking.objects.filter(guest_email=email).exclude(guest_phone="").first()
        if eb_email and phone and eb_email.guest_phone != phone:
            return False, f"Email {email} has been used with a different phone number in past bookings."

    if phone:
        customers = Customer.objects.filter(phone=phone)
        for c in customers:
            if c.user.email and email and c.user.email != email:
                return False, f"Phone number {phone} is already registered with a different email."
                
        rb_phone = RoomBooking.objects.filter(guest_phone=phone).exclude(guest_email="").first()
        if rb_phone and email and rb_phone.guest_email != email:
            return False, f"Phone number {phone} has been used with a different email in past bookings."
            
        eb_phone = EventBooking.objects.filter(guest_phone=phone).exclude(guest_email="").first()
        if eb_phone and email and eb_phone.guest_email != email:
            return False, f"Phone number {phone} has been used with a different email in past bookings."

    return True, ""


def schedule_pending_booking_deletion(booking_id, booking_type):
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, ActivityBooking
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if booking_type == 'room':
            booking = RoomBooking.objects.get(id=booking_id)
        elif booking_type == 'event':
            booking = EventBooking.objects.get(id=booking_id)
        elif booking_type == 'table':
            booking = TableReservation.objects.get(id=booking_id)
        elif booking_type == 'activity':
            booking = ActivityBooking.objects.get(id=booking_id)
        else:
            return

        if booking.status == 'Pending':
            # Also restore redeemed points if any
            if getattr(booking, 'points_redeemed', 0) > 0 and booking.customer_id:
                from accountapp.models import Customer
                customer = Customer.objects.get(id=booking.customer_id)
                customer.loyalty_points += booking.points_redeemed
                customer.save(update_fields=['loyalty_points'])
            
            # Additional cleanup for specific booking types (e.g., reverting room status)
            if booking_type == 'room' and booking.room:
                # Room status might need to be reverted if it was set to pending/maintenance
                # Generally, creating a pending booking doesn't change room status, but just in case
                pass
                
            booking.delete()
            logger.info(f"{booking_type.capitalize()} Booking {booking_id} deleted due to pending status after 10 minutes.")
    except Exception as e:
        logger.error(f"Error in schedule_pending_booking_deletion: {e}")
