from django.db import models
from django.conf import settings
from adminapp.models import Room,event_hall,Package,ActivitySession,Activity,RestaurantTable,FoodItem
from accountapp.models import Customer
# Create your models here.

class RoomBooking(models.Model):

    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_phone = models.CharField(max_length=15, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    check_in = models.DateField()
    check_out = models.DateField()

    status = models.CharField(max_length=20, default="Pending")

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    pending_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    points_earned = models.PositiveIntegerField(default=0)
    points_redeemed = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Confirmed', 'Confirmed'),
            ('Failed', 'Failed'),
            ('Fully Paid', 'Fully Paid')
        ],
        default='Pending'
    )

    long_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_reference = models.CharField(max_length=50, default='', blank=True)
    booking_source = models.CharField(max_length=20, default='', blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_room_bookings')
    guest_address = models.TextField(null=True, blank=True)
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=30, null=True, blank=True)
    special_request = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_room_bookings')
    cancelled_by = models.CharField(max_length=50, null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_status = models.CharField(max_length=20, default='Pending')
    
    actual_checkout_at = models.DateTimeField(null=True, blank=True)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.check_out and self.check_in and self.check_out < self.check_in:
            raise ValidationError('Check-out date must be greater than or equal to check-in date.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_status = self.status


    def save(self, *args, **kwargs):
        self.clean()  # Enforce model-level validation on every save
        if not self.long_order_id:
            import datetime, uuid
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            while True:
                suffix = uuid.uuid4().hex[:6].upper()
                candidate = f"STAYZEN-{date_str}-{suffix}"
                if not RoomBooking.objects.filter(long_order_id=candidate).exists():
                    self.long_order_id = candidate
                    break
        if self.final_amount == 0 and self.total_amount:
            self.final_amount = self.total_amount - self.discount_amount

        # Check for checkout (status changed to Completed)
        is_checkout = False
        old_status = None
        if self.pk:
            try:
                orig = RoomBooking.objects.get(pk=self.pk)
                old_status = orig.status
                if orig.status != 'Completed' and self.status == 'Completed':
                    is_checkout = True
            except Exception:
                pass

        if is_checkout:
            from decimal import Decimal
            initial_paid = self.advance_amount
            remaining_paid = self.pending_payment
            
            # If this is a Cash/Card check-out and pending_payment is still > 0, auto-collect
            if self.pending_payment > 0:
                self.advance_amount = self.final_amount
                self.pending_payment = Decimal('0.00')
                self.payment_status = 'Fully Paid'
            else:
                # Razorpay checkout sets pending_payment to 0 first, so orig.pending_payment holds the collected amount
                remaining_paid = orig.pending_payment
                initial_paid = self.final_amount - remaining_paid
            
            # Query booked activities
            activities = self.activitybooking_set.filter(status="Booked")

            # Generate automatic invoice text file
            import os
            from django.conf import settings
            
            invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
            os.makedirs(invoice_dir, exist_ok=True)
            invoice_filename = f'invoice_{self.id}.txt'
            invoice_path = os.path.join(invoice_dir, invoice_filename)
            
            with open(invoice_path, 'w', encoding='utf-8') as f:
                f.write("=========================================\n")
                f.write("               STAYZEN HOTEL             \n")
                f.write("             INVOICE & RECEIPT           \n")
                f.write("=========================================\n")
                f.write(f"Invoice ID: STAYZEN-INV-{self.long_order_id}\n")
                f.write(f"Booking Reference: {self.long_order_id}\n")
                f.write(f"Guest Name: {self.guest_name}\n")
                f.write(f"Phone     : {self.guest_phone or '-'}\n")
                f.write(f"Email     : {self.guest_email or '-'}\n")
                f.write(f"Room      : Room {self.room.room_number} ({self.room.room_type})\n")
                f.write(f"Stay Dates: {self.check_in} to {self.check_out}\n")
                if activities.exists():
                    f.write("-----------------------------------------\n")
                    f.write("Booked Activities:\n")
                    for act in activities:
                        f.write(f"  - {act.activity.activity_name}: INR {act.activity.price:.2f}\n")
                f.write("-----------------------------------------\n")
                f.write(f"Total Amount:         INR {self.total_amount:.2f}\n")
                f.write(f"Discount:             INR {self.discount_amount:.2f}\n")
                f.write(f"Final Amount:         INR {self.final_amount:.2f}\n")
                f.write(f"Initial Paid:         INR {initial_paid:.2f}\n")
                f.write(f"Remaining Paid:       INR {remaining_paid:.2f}\n")
                f.write("-----------------------------------------\n")
                f.write("Payment Status:       PAID IN FULL\n")
                f.write(f"Payment Method:       {self.payment_method or 'Cash/Card (At Desk)'}\n")
                f.write("=========================================\n")
                f.write("       Thank you for staying with us!    \n")
                f.write("=========================================\n")

        if self.payment_status == 'Confirmed' and self.status == 'Pending':
            self.status = 'Reserved'
        if self.status == 'Completed':
            self.payment_status = 'Fully Paid'
            
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.status == 'Pending':
            from bookingapp.utils import schedule_pending_booking_deletion
            import threading
            threading.Timer(600, schedule_pending_booking_deletion, args=[self.pk, 'room']).start()

    def send_confirmation_email(self):
        from django.core.mail import send_mail
        from django.conf import settings
        
        guest_name_str = self.guest_name or (self.customer.user.get_full_name() if self.customer else 'Guest')
        message = f"""Dear {guest_name_str},

Thank you for choosing StayZen .

Your room booking has been successfully confirmed.

## Reservation Details:

Reservation ID : {self.long_order_id}
Guest Name     : {guest_name_str}
Check-in Date : {self.check_in}
Check-out Date : {self.check_out}
Number of Guests : {self.adults + self.children} (Adults: {self.adults}, Children: {self.children})
Room Details : Room {self.room.room_number} ({self.room.room_type})
Special Requests : {self.special_request or 'None'}

Status : Confirmed

Track Your Booking:
http://127.0.0.1:8000/booking/track/{self.long_order_id}/

Need to cancel?
http://127.0.0.1:8000/booking/cancel/{self.long_order_id}/

If you need to modify your reservation, please contact us.

Thank you for staying with StayZen.

Warm regards,

StayZen Reception Team
Email: support@stayzen.com
Phone: contact number"""

        email_to = self.guest_email or (self.customer.user.email if self.customer else None)
        if email_to:
            try:
                send_mail(
                    subject=f"StayZen Room Booking Confirmed - {self.long_order_id}",
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@stayzen.com'),
                    recipient_list=[email_to],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending confirmation email: {e}")

        # Commented out to prevent making the room globally unavailable when booked on specific dates.
        # The calendar (flatpickr) correctly handles date-level unavailability.
        # if self.status == 'Checked In':
        #     target_status = 'Occupied'
        # elif self.status in ['Cancelled', 'Completed']:
        #     target_status = 'Available'
        # elif self.status == 'Reserved' or self.payment_status == 'Confirmed':
        #     target_status = 'Reserved'
        # else:
        #     target_status = 'Not Available'
        #     
        # if self.room.status != target_status:
        #     self.room.status = target_status
        #     self.room.save(update_fields=['status'])

    def __str__(self):
        return f"{self.room} - {self.check_in}"

    @property
    def is_guest(self):
        return self.customer is None

    @property
    def stay_days(self):
        if self.check_out and self.check_in:
            diff = (self.check_out - self.check_in).days
            return diff if diff > 0 else 1
        return 1

class ActivityBooking(models.Model):

    room_booking = models.ForeignKey(RoomBooking, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    session = models.ForeignKey(ActivitySession, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=(
            ('Booked', 'Booked'),
            ('Cancelled', 'Cancelled')
        ),
        default='Booked'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.activity.activity_name} - {self.session}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            try:
                old_status = ActivityBooking.objects.get(pk=self.pk).status
            except ActivityBooking.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if is_new:
            if self.status == 'Booked':
                if self.session.capacity > 0:
                    self.session.capacity -= 1
                    if self.session.capacity == 0:
                        self.session.status = 'Full'
                    self.session.save(update_fields=['capacity', 'status'])
        else:
            if old_status == 'Booked' and self.status == 'Cancelled':
                self.session.capacity += 1
                if self.session.status == 'Full':
                    self.session.status = 'Available'
                self.session.save(update_fields=['capacity', 'status'])
            elif old_status == 'Cancelled' and self.status == 'Booked':
                if self.session.capacity > 0:
                    self.session.capacity -= 1
                    if self.session.capacity == 0:
                        self.session.status = 'Full'
                    self.session.save(update_fields=['capacity', 'status'])
    
class EventBooking(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Checked In', 'Checked In'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    ]

    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    hall = models.ForeignKey(
        event_hall,
        on_delete=models.CASCADE
    )

    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    EVENT_TYPES = [
        ('Wedding', 'Wedding'),
        ('Corporate', 'Corporate'),
        ('Birthday', 'Birthday'),
        ('Reception', 'Reception'),
        ('Other', 'Other'),
    ]

    FOOD_PREFERENCES = [
        ('Vegetarian', 'Vegetarian'),
        ('Non-Vegetarian', 'Non-Vegetarian'),
        ('Both', 'Both'),
        ('None', 'None Required'),
    ]

    event_name = models.CharField(max_length=100)
    guest_name = models.CharField(max_length=100, blank=True, null=True)
    guest_phone = models.CharField(max_length=15, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='Other')
    food_preference = models.CharField(max_length=50, choices=FOOD_PREFERENCES, default='None')

    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)

    guest_count = models.PositiveIntegerField()

    special_request = models.TextField(
        blank=True,
        null=True
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    pending_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Failed', 'Failed'),
        ('Fully Paid', 'Fully Paid'),
    ]

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    points_earned = models.PositiveIntegerField(default=0)
    points_redeemed = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    notification_shown = models.BooleanField(
        default=False
    )

    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_reference = models.CharField(max_length=50, default='', blank=True)
    booking_source = models.CharField(max_length=20, default='', blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_event_bookings')
    guest_address = models.TextField(null=True, blank=True)
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=30, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_event_bookings')

    long_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    cancelled_by = models.CharField(max_length=50, null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_status = models.CharField(max_length=20, default='Pending')
    
    actual_checkout_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError('End date must be greater than or equal to start date.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_status = self.status

    def save(self, *args, **kwargs):
        self.clean()  # Enforce model-level validation on every save
        if not self.long_order_id:
            import datetime, uuid
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            while True:
                suffix = uuid.uuid4().hex[:6].upper()
                candidate = f"STAYZEN-{date_str}-{suffix}"
                if not EventBooking.objects.filter(long_order_id=candidate).exists():
                    self.long_order_id = candidate
                    break
        if self.final_amount == 0 and self.total_amount:
            self.final_amount = self.total_amount - self.discount_amount

        # Check for checkout (status changed to Completed)
        is_checkout = False
        old_status = None
        if self.pk:
            try:
                orig = EventBooking.objects.get(pk=self.pk)
                old_status = orig.status
                if orig.status != 'Completed' and self.status == 'Completed':
                    is_checkout = True
            except Exception:
                pass

        if is_checkout and self.pending_payment > 0:
            from decimal import Decimal
            initial_paid = self.advance_amount
            remaining_paid = self.pending_payment
            
            # Auto-collect remaining amount
            self.advance_amount = self.final_amount
            self.pending_payment = Decimal('0.00')
            self.payment_status = 'Fully Paid'
            
            # Generate automatic invoice text file
            import os
            from django.conf import settings
            
            invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
            os.makedirs(invoice_dir, exist_ok=True)
            invoice_filename = f'event_invoice_{self.id}.txt'
            invoice_path = os.path.join(invoice_dir, invoice_filename)
            
            with open(invoice_path, 'w', encoding='utf-8') as f:
                f.write("=========================================\n")
                f.write("               STAYZEN HOTEL             \n")
                f.write("          EVENT HALL INVOICE & RECEIPT   \n")
                f.write("=========================================\n")
                f.write(f"Invoice ID: STAYZEN-INV-{self.long_order_id}\n")
                f.write(f"Booking Reference: {self.long_order_id}\n")
                f.write(f"Guest Name: {self.guest_name}\n")
                f.write(f"Phone     : {self.guest_phone or '-'}\n")
                f.write(f"Email     : {self.guest_email or '-'}\n")
                f.write(f"Hall      : {self.hall.hall_name}\n")
                f.write(f"Dates     : {self.start_date} to {self.end_date}\n")
                f.write("-----------------------------------------\n")
                f.write(f"Total Amount:         INR {self.total_amount:.2f}\n")
                f.write(f"Discount:             INR {self.discount_amount:.2f}\n")
                f.write(f"Final Amount:         INR {self.final_amount:.2f}\n")
                f.write(f"Initial Paid:         INR {initial_paid:.2f}\n")
                f.write(f"Remaining Paid:       INR {remaining_paid:.2f}\n")
                f.write("-----------------------------------------\n")
                f.write("Payment Status:       PAID IN FULL\n")
                f.write("Payment Method:       Cash/Card (At Desk)\n")
                f.write("=========================================\n")
                f.write("       Thank you for choosing StayZen!   \n")
                f.write("=========================================\n")

        if self.payment_status == 'Confirmed' and self.status == 'Pending':
            self.status = 'Confirmed'
        if self.status == 'Completed':
            self.payment_status = 'Fully Paid'
            
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.status == 'Pending':
            from bookingapp.utils import schedule_pending_booking_deletion
            import threading
            threading.Timer(600, schedule_pending_booking_deletion, args=[self.pk, 'event']).start()
        
        # Commented out to prevent making the hall globally unavailable when booked on specific dates.
        # if self.status in ['Confirmed', 'Checked In']:
        #     target_status = 'booked'
        # elif self.status in ['Cancelled', 'Completed']:
        #     target_status = 'available'
        # else:
        #     target_status = 'available'
        #     
        # if self.hall.hall_status != target_status:
        #     self.hall.hall_status = target_status
        #     self.hall.save(update_fields=['hall_status'])

    def send_confirmation_email(self):
        from django.core.mail import send_mail
        from django.conf import settings
        
        guest_name_str = self.guest_name or (self.customer.user.get_full_name() if self.customer else 'Guest')
        start_time_obj = self.start_time
        if isinstance(start_time_obj, str):
            from datetime import datetime as _dt
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    start_time_obj = _dt.strptime(start_time_obj, fmt).time()
                    break
                except ValueError:
                    pass
        start_time_str = start_time_obj.strftime('%I:%M %p') if hasattr(start_time_obj, 'strftime') else (str(start_time_obj) if start_time_obj else '')

        end_time_obj = self.end_time
        if isinstance(end_time_obj, str):
            from datetime import datetime as _dt
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    end_time_obj = _dt.strptime(end_time_obj, fmt).time()
                    break
                except ValueError:
                    pass
        end_time_str = end_time_obj.strftime('%I:%M %p') if hasattr(end_time_obj, 'strftime') else (str(end_time_obj) if end_time_obj else '')
        
        message = f"""Dear {guest_name_str},

Thank you for choosing StayZen .

Your event hall booking has been successfully confirmed.

## Reservation Details:

Reservation ID : {self.long_order_id}
Event Name     : {self.event_name}
Guest Name     : {guest_name_str}
Event Date     : {self.start_date} to {self.end_date}
Event Time     : {start_time_str} to {end_time_str}
Number of Guests : {self.guest_count}
Hall Name      : {self.hall.hall_name}
Event Type     : {self.event_type}
Special Requests : {self.special_request or 'None'}

Status : Confirmed

Track Your Booking:
http://127.0.0.1:8000/booking/track/{self.long_order_id}/

Need to cancel?
http://127.0.0.1:8000/booking/cancel/{self.long_order_id}/

If you need to modify your reservation, please contact us.

Thank you for celebrating with StayZen.

Warm regards,

StayZen Events Team
Email: support@stayzen.com
Phone: contact number"""

        email_to = self.guest_email or (self.customer.user.email if self.customer else None)
        if email_to:
            try:
                send_mail(
                    subject=f"StayZen Event Booking Confirmed - {self.long_order_id}",
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@stayzen.com'),
                    recipient_list=[email_to],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending confirmation email: {e}")

    def __str__(self):
        return f"{self.event_name} - {self.hall}"

    @property
    def stay_days(self):
        if self.end_date and self.start_date:
            diff = (self.end_date - self.start_date).days
            return diff if diff > 0 else 1
        return 1


class LoyaltyTransaction(models.Model):
    TRANSACTION_EARNED = 'Earned'
    TRANSACTION_REDEEMED = 'Redeemed'

    TRANSACTION_CHOICES = [
        (TRANSACTION_EARNED, 'Earned'),
        (TRANSACTION_REDEEMED, 'Redeemed'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='loyalty_transactions'
    )
    booking_reference = models.CharField(max_length=100)
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_CHOICES
    )
    points = models.PositiveIntegerField()
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer} - {self.transaction_type} {self.points} points"


class TableReservation(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    ]

    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.CASCADE
    )

    customer_name = models.CharField(max_length=100)

    phone = models.CharField(max_length=20)

    email = models.EmailField(
        blank=True,
        null=True
    )

    reservation_date = models.DateField()

    reservation_time = models.TimeField()

    duration_hours = models.PositiveIntegerField(default=2)

    guests = models.PositiveIntegerField()

    special_request = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    long_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    address = models.TextField(blank=True, null=True)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_reference = models.CharField(max_length=50, default='', blank=True)
    booking_source = models.CharField(max_length=20, default='', blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_table_reservations')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=30, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='Pending')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_table_reservations')
    cancelled_by = models.CharField(max_length=50, null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_status = models.CharField(max_length=20, default='Pending')

    @property
    def end_time(self):
        import datetime
        if self.reservation_time and self.duration_hours:
            dt = datetime.datetime.combine(datetime.date.today(), self.reservation_time)
            return (dt + datetime.timedelta(hours=self.duration_hours)).time()
        return None

    def save(self, *args, **kwargs):
        if not self.long_order_id:
            import datetime, uuid
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            while True:
                suffix = uuid.uuid4().hex[:6].upper()
                candidate = f"STAYZEN-{date_str}-{suffix}"
                if not TableReservation.objects.filter(long_order_id=candidate).exists():
                    self.long_order_id = candidate
                    break
                    
        old_status = None
        if self.pk:
            try:
                old_status = TableReservation.objects.get(pk=self.pk).status
            except TableReservation.DoesNotExist:
                pass
                
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.status == 'Confirmed':
            self.table.status = 'Reserved'
            self.table.save(update_fields=['status'])
            
        if is_new and self.status == 'Pending':
            from bookingapp.utils import schedule_pending_booking_deletion
            import threading
            threading.Timer(600, schedule_pending_booking_deletion, args=[self.pk, 'table']).start()

    def send_confirmation_email(self):
        from django.core.mail import send_mail
        from django.conf import settings
        
        res_time_obj = self.reservation_time
        if isinstance(res_time_obj, str):
            from datetime import datetime as _dt
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    res_time_obj = _dt.strptime(res_time_obj, fmt).time()
                    break
                except ValueError:
                    pass
        res_time = res_time_obj.strftime('%I:%M %p') if hasattr(res_time_obj, 'strftime') else (str(res_time_obj) if res_time_obj else '')
        
        message = f"""Dear {self.customer_name},

Thank you for choosing StayZen .

Your restaurant reservation has been successfully confirmed.

## Reservation Details:

Reservation ID : {self.long_order_id}
Guest Name     : {self.customer_name}
Reservation Date : {self.reservation_date}
Reservation Time : {res_time}
Number of Guests : {self.guests}
Restaurant Name : StayZen Restaurant
Special Requests : {self.special_request or 'None'}

Status : Confirmed

Track Your Booking:
http://127.0.0.1:8000/booking/track/{self.long_order_id}/

Need to cancel?
http://127.0.0.1:8000/booking/cancel/{self.long_order_id}/

Please arrive 10–15 minutes before your reserved time. If you need to modify your reservation, please contact us.

Thank you for dining with StayZen.

Warm regards,

StayZen Restaurant Team
Email: support@stayzen.com
Phone: +91 XXXXX XXXXX"""

        if self.email:
            try:
                send_mail(
                    subject=f"StayZen Restaurant Reservation Confirmed - {self.long_order_id}",
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@stayzen.com'),
                    recipient_list=[self.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending confirmation email: {e}")

    def __str__(self):
        return f"{self.customer_name} - Table {self.table.table_number}"
    
from django.db import models
from django.conf import settings

class Order(models.Model):

    ORDER_TYPE_CHOICES = [
        ('DineIn', 'Dine In'),
        ('RoomService', 'Room Service'),
        ('Delivery', 'Delivery'),
        ('Takeaway', 'Takeaway'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Preparing', 'Preparing'),
        ('ReadyForPickup', 'Ready for Pickup'),
        ('Assigned', 'Assigned'),
        ('OutForDelivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    SERVING_STATUS_CHOICES = [
        ('Preparing', 'Preparing'),
        ('Delivered', 'Delivered'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    serving_status = models.CharField(max_length=20, choices=SERVING_STATUS_CHOICES, default='Preparing')

    booking_source = models.CharField(max_length=20, default='', blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_reference = models.CharField(max_length=50, default='', blank=True)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    long_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_orders')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_orders')
    table_reservation = models.ForeignKey(TableReservation, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_email = models.EmailField(blank=True, null=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=50, null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    refund_status = models.CharField(max_length=20, default='Pending')
    delivery_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_deliveries'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='delivery_assignments_made'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_status = self.status

    def save(self, *args, **kwargs):
        if not self.long_order_id:
            import datetime, uuid
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            while True:
                suffix = uuid.uuid4().hex[:6].upper()
                candidate = f"STAYZEN-{date_str}-{suffix}"
                if not Order.objects.filter(long_order_id=candidate).exists():
                    self.long_order_id = candidate
                    break
        old_status = None
        if self.pk:
            try:
                old_status = Order.objects.get(pk=self.pk).status
            except Order.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def send_confirmation_email(self):
        from django.core.mail import send_mail
        from django.conf import settings
        
        items_str = "\n".join([f"- {item.quantity}x {item.food.item_name} (₹{item.get_total()})" for item in self.items.all()])
        guest_name_str = self.customer_name or (self.user.get_full_name() if self.user else 'Guest')
        
        # Hardcoding the base URL for local development for now as per plan
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        tracking_url = f"{base_url}/track-food/{self.long_order_id}/"
        
        message = f"""Dear {guest_name_str},

Thank you for choosing StayZen.

Your restaurant order has been successfully confirmed.

## Order Details:

Order ID       : {self.long_order_id}
Guest Name     : {guest_name_str}
Order Date     : {self.order_date.strftime('%Y-%m-%d %I:%M %p') if self.order_date else ''}
Order Type     : {self.get_order_type_display()}
Items          : 
{items_str}

Total Amount   : ₹{self.total_amount}
Status : Confirmed

Track Your Booking:
http://127.0.0.1:8000/booking/track/{self.long_order_id}/

Need to cancel?
http://127.0.0.1:8000/booking/cancel/{self.long_order_id}/

Thank you for dining with StayZen.

Warm regards,

StayZen Restaurant Team
Email: support@stayzen.com
Phone: contact number"""

        email_to = self.customer_email or (self.user.email if self.user else None)
        if email_to:
            try:
                send_mail(
                    subject=f"StayZen Food Order Confirmed - {self.long_order_id}",
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@stayzen.com'),
                    recipient_list=[email_to],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending confirmation email: {e}")

    def send_status_update_email(self):
        """Send email only when order is Delivered. All other status changes are silent."""
        if self.status != 'Delivered':
            return  # Only notify customer on delivery

        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings

        guest_name_str = self.customer_name or (self.user.get_full_name() if self.user else 'Guest')
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        tracking_url = f"{base_url}/restaurant/track/{self.long_order_id}/"

        subject = f"Your StayZen Order #{self.long_order_id} has been Delivered! 🍽️"

        text_content = (
            f"Dear {guest_name_str},\n\n"
            f"Great news! Your order has been delivered. Enjoy your meal!\n\n"
            f"Order ID: {self.long_order_id}\nTotal: \u20b9{self.total_amount}\n\n"
            f"Thank you for choosing StayZen."
        )

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <div style="background: linear-gradient(135deg, #7c3aed, #a855f7); border-radius: 8px 8px 0 0; padding: 24px; text-align: center;">
                <h2 style="color: #fff; margin: 0; font-size: 22px;">StayZen Restaurant</h2>
                <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0; font-size: 14px;">Your order has arrived!</p>
            </div>

            <div style="padding: 28px 24px;">
                <p style="font-size: 16px; color: #1e293b;">Dear <strong>{guest_name_str}</strong>,</p>
                <p style="font-size: 15px; color: #374151; line-height: 1.6;">
                    🎉 Your order has been <strong>successfully delivered</strong>. We hope you enjoy your meal!
                </p>

                <div style="background: #f8fafc; border-left: 4px solid #22c55e; border-radius: 6px; padding: 14px 18px; margin: 20px 0;">
                    <p style="margin: 4px 0; font-size: 13px; color: #475569;"><strong>Order ID:</strong> {self.long_order_id}</p>
                    <p style="margin: 4px 0; font-size: 13px; color: #475569;"><strong>Total Amount:</strong> &#8377;{self.total_amount}</p>
                    {"<p style='margin: 4px 0; font-size: 13px; color: #475569;'><strong>Delivered By:</strong> " + (self.delivery_staff.get_full_name() or self.delivery_staff.username) + "</p>" if self.delivery_staff else ""}
                </div>
            </div>

            <div style="border-top: 1px solid #e2e8f0; padding: 16px 24px; text-align: center;">
                <p style="font-size: 12px; color: #94a3b8; margin: 0;">
                    StayZen Restaurant Team &bull; support@stayzen.com
                </p>
            </div>
        </div>
        """

        email_to = self.customer_email or (self.user.email if self.user else None)
        if email_to:
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@stayzen.com'),
                    to=[email_to],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=True)
            except Exception as e:
                print(f"Error sending delivery email: {e}")

    def __str__(self):
        return f"Order #{self.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def get_total(self):
        return self.food.price * self.quantity

class FreshUpRoomBooking(models.Model):
    customer = models.ForeignKey('accountapp.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)
    customer_email = models.EmailField(blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    hours_required = models.PositiveIntegerField()
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='Pending')
    payment_method = models.CharField(max_length=30, blank=True, null=True)
    booking_datetime = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    long_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    booking_reference = models.CharField(max_length=100, null=True, blank=True)

    actual_checkout_at = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_payment_status = self.payment_status

    def save(self, *args, **kwargs):
        if not self.long_order_id:
            import datetime, uuid
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            while True:
                suffix = uuid.uuid4().hex[:6].upper()
                candidate = f"STAYZEN-FR-{date_str}-{suffix}"
                if not FreshUpRoomBooking.objects.filter(long_order_id=candidate).exists():
                    self.long_order_id = candidate
                    break
                    
        old_payment_status = None
        if self.pk:
            try:
                old_payment_status = FreshUpRoomBooking.objects.get(pk=self.pk).payment_status
            except FreshUpRoomBooking.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)

    def send_confirmation_email(self):
        from django.core.mail import send_mail
        from django.conf import settings
        
        guest_name_str = self.customer_name or (self.customer.user.get_full_name() if self.customer else 'Guest')
        
        message = f"""Dear {guest_name_str},

Thank you for choosing StayZen .

Your fresh-up room booking has been successfully confirmed.

## Reservation Details:

Reservation ID : {self.long_order_id}
Guest Name     : {guest_name_str}
Booking Date   : {self.booking_datetime.date() if self.booking_datetime else ''}
Hours Required : {self.hours_required}
Room Details   : Room {self.room.room_number} ({self.room.room_type})

Status : Confirmed

If you need to modify or cancel your reservation, please contact us.

Thank you for staying with StayZen.

Warm regards,

StayZen Reception Team
Email: [@stayzen@gmail.com](mailto:support@stayzen.com)
Phone: contact number"""

        email_to = self.customer_email or (self.customer.user.email if self.customer else None)
        if email_to:
            try:
                send_mail(
                    subject=f"StayZen Fresh-Up Booking Confirmed - {self.long_order_id}",
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@stayzen.com'),
                    recipient_list=[email_to],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending confirmation email: {e}")

    def __str__(self):
        return f"Fresh-Up {self.room.room_number} - {self.customer_name}"
