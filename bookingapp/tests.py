from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from adminapp.models import Room, event_hall, Package, Service
from bookingapp.models import RoomBooking, EventBooking
from decimal import Decimal
import datetime

class CheckinCheckoutTestCase(TestCase):
    def setUp(self):
        # Create a superuser
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='admin', password='password123')
        
        # Create a Room
        self.room = Room.objects.create(
            room_number='101',
            room_type='Deluxe',
            description='A deluxe room',
            price=Decimal('100.00'),
            max_adults=2,
            max_children=1,
            status='Available'
        )
        
        # Create a Room Booking
        self.room_booking = RoomBooking.objects.create(
            guest_name='John Doe',
            guest_phone='1234567890',
            guest_email='john@example.com',
            room=self.room,
            check_in=datetime.date.today(),
            check_out=datetime.date.today() + datetime.timedelta(days=2),
            adults=2,
            children=0,
            status='Confirmed',
            total_amount=Decimal('200.00'),
            final_amount=Decimal('200.00'),
            advance_amount=Decimal('50.00'),
            pending_payment=Decimal('150.00'),
            payment_status='Pending'
        )

        # Create an Event Hall
        self.hall = event_hall.objects.create(
            hall_name='Grand Ballroom',
            hall_type='banquet',
            hall_description='A grand ballroom',
            hall_capacity=500,
            hall_price=Decimal('1000.00'),
            hall_status='available',
            hall_image='event_hall/ballroom.jpg'
        )
        
        # Create an Event Booking
        self.event_booking = EventBooking.objects.create(
            event_name='Wedding Reception',
            guest_name='Jane Doe',
            guest_phone='0987654321',
            guest_email='jane@example.com',
            hall=self.hall,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=1),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(18, 0),
            guest_count=100,
            status='Confirmed',
            total_amount=Decimal('1000.00'),
            final_amount=Decimal('1000.00'),
            advance_amount=Decimal('250.00'),
            pending_payment=Decimal('750.00'),
            payment_status='Pending'
        )

    def test_receptionist_checkin_page(self):
        # Access the check-in dashboard page
        response = self.client.get(reverse('receptionist_checkin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Doe')

    def test_process_room_checkin(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Process room check-in with ID details and file upload
        url = reverse('process_room_checkin', kwargs={'booking_id': self.room_booking.id})
        id_document = SimpleUploadedFile("passport.pdf", b"test content", content_type="application/pdf")
        response = self.client.post(url, {
            'id_type': 'Passport',
            'id_document': id_document
        })
        self.assertEqual(response.status_code, 302) # Redirects
        
        # Refresh from db
        self.room_booking.refresh_from_db()
        self.room.refresh_from_db()
        
        self.assertEqual(self.room_booking.status, 'Checked In')
        self.assertEqual(self.room_booking.id_type, 'Passport')
        self.assertTrue('checkin_ids/' in self.room_booking.id_number)
        self.assertEqual(self.room.status, 'Occupied')

    def test_process_event_checkin(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Process event check-in with ID details and file upload
        url = reverse('process_event_checkin', kwargs={'booking_id': self.event_booking.id})
        id_document = SimpleUploadedFile("id_card.png", b"test content", content_type="image/png")
        response = self.client.post(url, {
            'id_type': 'Aadhaar Card',
            'id_document': id_document
        })
        self.assertEqual(response.status_code, 302) # Redirects
        
        # Refresh from db
        self.event_booking.refresh_from_db()
        self.hall.refresh_from_db()
        
        self.assertEqual(self.event_booking.status, 'Checked In')
        self.assertEqual(self.event_booking.id_type, 'Aadhaar Card')
        self.assertTrue('checkin_ids/' in self.event_booking.id_number)
        self.assertEqual(self.hall.hall_status, 'booked')

    def test_receptionist_checkout_settlement_page(self):
        # Set Room Booking and Event Booking to Checked In
        self.room_booking.status = 'Checked In'
        self.room_booking.save()
        self.event_booking.status = 'Checked In'
        self.event_booking.save()
        
        # Access checkout & settlement dashboard
        response = self.client.get(reverse('receptionist_checkout_settlement'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Doe')

    def test_process_room_checkout(self):
        # Start at Checked In
        self.room_booking.status = 'Checked In'
        self.room_booking.save()
        self.room.status = 'Occupied'
        self.room.save()
        
        # Process checkout with Cash payment method
        url = reverse('process_room_checkout', kwargs={'booking_id': self.room_booking.id})
        response = self.client.post(url, {
            'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 302)
        
        # Refresh from db
        self.room_booking.refresh_from_db()
        self.room.refresh_from_db()
        
        self.assertEqual(self.room_booking.status, 'Completed')
        self.assertEqual(self.room_booking.payment_method, 'Cash')
        self.assertEqual(self.room_booking.payment_status, 'Fully Paid')
        self.assertEqual(self.room_booking.pending_payment, Decimal('0.00'))
        self.assertEqual(self.room.status, 'Available')

    def test_process_event_checkout(self):
        # Start at Checked In
        self.event_booking.status = 'Checked In'
        self.event_booking.save()
        self.hall.hall_status = 'booked'
        self.hall.save()
        
        # Process checkout with Card payment method
        url = reverse('process_event_checkout', kwargs={'booking_id': self.event_booking.id})
        response = self.client.post(url, {
            'payment_method': 'Card'
        })
        self.assertEqual(response.status_code, 302)
        
        # Refresh from db
        self.event_booking.refresh_from_db()
        self.hall.refresh_from_db()
        
        self.assertEqual(self.event_booking.status, 'Completed')
        self.assertEqual(self.event_booking.payment_method, 'Card')
        self.assertEqual(self.event_booking.payment_status, 'Fully Paid')
        self.assertEqual(self.event_booking.pending_payment, Decimal('0.00'))
        self.assertEqual(self.hall.hall_status, 'available')

    def test_long_order_id_generation(self):
        # Verify that long_order_id is automatically generated on RoomBooking save
        self.assertIsNotNone(self.room_booking.long_order_id)
        self.assertTrue(self.room_booking.long_order_id.startswith('STAYZEN-'))

        # Verify that long_order_id is automatically generated on EventBooking save
        self.assertIsNotNone(self.event_booking.long_order_id)
        self.assertTrue(self.event_booking.long_order_id.startswith('STAYZEN-'))

    def test_download_invoice_view(self):
        # Verify download invoice returns valid PDF response for RoomBooking
        url = reverse('download_invoice', kwargs={'booking_type': 'room', 'booking_id': self.room_booking.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Verify download invoice returns valid PDF response for EventBooking
        url = reverse('download_invoice', kwargs={'booking_type': 'event', 'booking_id': self.event_booking.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_offline_fresh_up_booking_cash(self):
        # Cancel the room booking from setUp to prevent overlap
        self.room_booking.status = 'Cancelled'
        self.room_booking.save()
        # Book a room for fresh-up with Cash payment method
        url = reverse('offline_fresh_up_booking')
        response = self.client.post(url, {
            'room_id': self.room.id,
            'customer_name': 'Fresh Up Guest',
            'customer_phone': '9999988888',
            'customer_address': 'Some Address',
            'hours_required': '3',
            'price_per_hour': '150.00',
            'payment_method': 'Cash'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify booking in db
        from bookingapp.models import FreshUpRoomBooking
        booking = FreshUpRoomBooking.objects.get(customer_name='Fresh Up Guest')
        self.assertEqual(booking.payment_method, 'Cash')
        self.assertEqual(booking.payment_status, 'Paid')
        
        # Room status should be set to Occupied
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'Occupied')

    def test_fresh_up_booking_blocks_room_calendar_dates(self):
        # Cancel the room booking from setUp to prevent overlap
        self.room_booking.status = 'Cancelled'
        self.room_booking.save()
        from bookingapp.models import FreshUpRoomBooking

        FreshUpRoomBooking.objects.create(
            room=self.room,
            customer_name='Calendar Guest',
            customer_phone='9999966666',
            customer_email='calendar@example.com',
            hours_required=2,
            price_per_hour=Decimal('100.00'),
            total_amount=Decimal('200.00'),
            payment_status='Paid',
        )

        response = self.client.get(reverse('booked_dates', kwargs={'room_id': self.room.id}))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn(str(datetime.date.today()), data['not_available'])

    def test_offline_fresh_up_booking_razorpay(self):
        # Cancel the room booking from setUp to prevent overlap
        self.room_booking.status = 'Cancelled'
        self.room_booking.save()
        # Book a room for fresh-up with Online (Razorpay) payment method
        url = reverse('offline_fresh_up_booking')
        response = self.client.post(url, {
            'room_id': self.room.id,
            'customer_name': 'Razorpay Guest',
            'customer_phone': '9999977777',
            'customer_address': 'Some Address 2',
            'hours_required': '2',
            'price_per_hour': '200.00',
            'payment_method': 'Razorpay'
        })
        self.assertEqual(response.status_code, 200) # Renders payment confirmation page or context
        
        # Verify booking in db (initially Pending)
        from bookingapp.models import FreshUpRoomBooking
        booking = FreshUpRoomBooking.objects.get(customer_name='Razorpay Guest')
        self.assertEqual(booking.payment_method, 'Razorpay')
        self.assertEqual(booking.payment_status, 'Pending')
        
        # Room status should not be Occupied yet
        self.room.refresh_from_db()
        self.assertNotEqual(self.room.status, 'Occupied')

        # Simulate Razorpay callback
        callback_url = reverse('razorpay_callback')
        import json
        callback_response = self.client.post(
            callback_url,
            json.dumps({
                'booking_id': booking.id,
                'booking_type': 'freshup',
                'razorpay_payment_id': 'pay_TEST12345'
            }),
            content_type='application/json'
        )
        self.assertEqual(callback_response.status_code, 200)
        
        # Check details after callback
        booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(booking.payment_status, 'Paid')
        self.assertEqual(booking.payment_method, 'Razorpay')
        self.assertEqual(booking.booking_reference, 'pay_TEST12345')
        self.assertEqual(self.room.status, 'Occupied')