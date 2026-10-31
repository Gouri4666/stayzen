from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from adminapp.models import Room

class RoomBookingButtonTest(TestCase):
    def setUp(self):
        # Create rooms
        self.available_room = Room.objects.create(
            room_number="101",
            room_type="Single",
            description="Nice single room",
            max_adults=2,
            max_children=1,
            price=1500.00,
            status="Available"
        )
        self.not_available_room = Room.objects.create(
            room_number="102",
            room_type="Double",
            description="Double room",
            max_adults=4,
            max_children=2,
            price=2500.00,
            status="Not Available"
        )
        self.reserved_room = Room.objects.create(
            room_number="103",
            room_type="Suite",
            description="Luxury suite",
            max_adults=4,
            max_children=2,
            price=5000.00,
            status="Reserved"
        )
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword",
            email="test@example.com"
        )

    def test_guest_rooms_page_buttons(self):
        c = Client()
        response = c.get(reverse('rooms'))
        self.assertEqual(response.status_code, 200)
        
        # Available room and Reserved room should have active "Book Now" buttons/links
        self.assertContains(response, f'data-room="{self.available_room.id}"')
        self.assertContains(response, f'data-room="{self.reserved_room.id}"')
        
        self.assertContains(response, 'Not Available')
        
        # Reserved room status badge/text should be shown
        self.assertContains(response, 'Reserved')

    def test_dashboard_rooms_page_buttons(self):
        c = Client()
        c.login(username="testuser", password="testpassword")
        response = c.get(reverse('rooms_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Available room and Reserved room should have active "Book Now" links
        self.assertContains(response, f'href="/booking/room-booking-dashboard/?room_id={self.available_room.id}"')
        self.assertContains(response, f'href="/booking/room-booking-dashboard/?room_id={self.reserved_room.id}"')
        
        # Not Available room booking link should be disabled
        self.assertNotContains(response, f'href="/booking/room-booking-dashboard/?room_id={self.not_available_room.id}"')
        self.assertContains(response, 'disabled style="background-color: #cbd5e1 !important; color: #64748b !important; border: none !important; cursor: not-allowed !important; pointer-events: none; width: 100%; text-align: center;">Not Available</button>')

        # Room 102 status badge should be status-not-available
        self.assertContains(response, 'status-not-available')

    def test_room_booking_dashboard_dropdown(self):
        c = Client()
        c.login(username="testuser", password="testpassword")
        response = c.get(reverse('room_booking_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Dropdown options for unavailable/reserved rooms should be disabled
        self.assertContains(response, f'value="{self.not_available_room.id}" data-price="{self.not_available_room.price:.2f}" disabled')
        self.assertContains(response, f'value="{self.reserved_room.id}" data-price="{self.reserved_room.price:.2f}" disabled')
        # Dropdown options for available rooms should not be disabled
        self.assertContains(response, f'value="{self.available_room.id}" data-price="{self.available_room.price:.2f}" ')


from adminapp.models import event_hall

class EventBookingButtonTest(TestCase):
    def setUp(self):
        # Create event halls
        self.available_hall = event_hall.objects.create(
            hall_name="Grand Ballroom",
            hall_type="wedding",
            hall_description="Beautiful ballroom",
            hall_capacity=500,
            hall_price=50000.00,
            hall_status="available"
        )
        self.booked_hall = event_hall.objects.create(
            hall_name="Conference Room A",
            hall_type="conference",
            hall_description="Nice room A",
            hall_capacity=50,
            hall_price=10000.00,
            hall_status="booked"
        )
        self.maintenance_hall = event_hall.objects.create(
            hall_name="Banquet Hall B",
            hall_type="banquet",
            hall_description="Under renovation",
            hall_capacity=200,
            hall_price=20000.00,
            hall_status="maintenance"
        )
        # Create user
        self.user = User.objects.create_user(
            username="testuser_event",
            password="testpassword",
            email="test_event@example.com"
        )

    def test_guest_event_page_buttons(self):
        c = Client()
        response = c.get(reverse('event'))
        self.assertEqual(response.status_code, 200)
        
        # Available and Booked halls should have active "Book Now" buttons/links
        self.assertContains(response, f'data-hall-id="{self.available_hall.hall_id}"')
        self.assertContains(response, f'data-hall-id="{self.booked_hall.hall_id}"')
        
        # Maintenance hall booking button should be disabled
        self.assertContains(response, 'Maintenance')

    def test_dashboard_event_halls_page_buttons(self):
        c = Client()
        c.login(username="testuser_event", password="testpassword")
        response = c.get(reverse('event_halls_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Available and Booked halls should have active "Book Now" links
        self.assertContains(response, f'href="/booking/event-booking-dashboard/?hall_id={self.available_hall.hall_id}"')
        self.assertContains(response, f'href="/booking/event-booking-dashboard/?hall_id={self.booked_hall.hall_id}"')
        
        # Maintenance hall booking link should be disabled
        self.assertContains(response, 'disabled style="background-color: #cbd5e1 !important; color: #64748b !important; border: none !important; cursor: not-allowed !important; pointer-events: none; flex: 1; text-align: center; text-transform: capitalize;">maintenance</button>')

    def test_event_booking_dashboard_dropdown(self):
        c = Client()
        c.login(username="testuser_event", password="testpassword")
        response = c.get(reverse('event_booking_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Dropdown option for maintenance hall should be disabled
        self.assertContains(response, f'value="{self.maintenance_hall.hall_id}" data-price="{self.maintenance_hall.hall_price:.2f}" disabled')
        # Dropdown options for available and booked halls should not be disabled
        self.assertContains(response, f'value="{self.available_hall.hall_id}" data-price="{self.available_hall.hall_price:.2f}"')
        self.assertContains(response, f'value="{self.booked_hall.hall_id}" data-price="{self.booked_hall.hall_price:.2f}"')


from bookingapp.models import RoomBooking
class RoomBookingSubmissionTest(TestCase):
    def setUp(self):
        self.room = Room.objects.create(
            room_number="201",
            room_type="Single",
            description="A clean quiet room",
            max_adults=2,
            max_children=1,
            price=2000.00,
            status="Available"
        )

    def test_guest_room_booking_submission(self):
        client = Client()
        # Post request to perform booking as a guest (no user logged in)
        response = client.post(reverse('room_booking'), {
            'room_id': self.room.id,
            'check_in': '2026-07-01',
            'check_out': '2026-07-05',
            'adults': 1,
            'children': 0,
            'guest_name': 'Guest User',
            'guest_phone': '9876543210',
            'guest_email': 'guest@example.com'
        })
        # Check that we got 200 OK rendering the payment checkout page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        # Verify that the booking was actually created in the DB and has default/synced values set
        booking = RoomBooking.objects.filter(guest_email='guest@example.com').first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.room, self.room)
        self.assertEqual(booking.advance_amount, 2000.00)
        
        # Simulating payment callback via POST
        callback_response = client.post(reverse('razorpay_callback'), {
            'booking_id': booking.id,
            'booking_type': 'room',
            'razorpay_payment_id': 'pay_test123'
        }, content_type='application/json')
        self.assertEqual(callback_response.status_code, 200)
        data = callback_response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('room_booking_confirmation', kwargs={'booking_id': booking.id}))

        # Check that the confirmation page loads successfully after payment confirmation redirect
        confirm_response = client.get(data['redirect_url'])
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, "Room Booked Successfully!")
        self.assertContains(confirm_response, booking.long_order_id)
        self.assertContains(confirm_response, "Payment Confirmed")


class EventBookingSubmissionTest(TestCase):
    def setUp(self):
        from adminapp.models import event_hall
        self.hall = event_hall.objects.create(
            hall_name="Grand Ballroom",
            hall_type="wedding",
            hall_description="Beautiful ballroom",
            hall_capacity=500,
            hall_price=50000.00,
            hall_status="available"
        )

    def test_guest_event_booking_submission(self):
        client = Client()
        response = client.post(reverse('event_booking'), {
            'hall_id': self.hall.hall_id,
            'event_name': 'Grand Gala Party',
            'event_type': 'Other',
            'start_date': '2026-10-01',
            'end_date': '2026-10-02',
            'start_time': '10:00:00',
            'end_time': '22:00:00',
            'food_preference': 'Both',
            'guest_count': 150,
            'special_request': 'Premium audio setup required',
            'guest_name': 'Guest Planner',
            'guest_phone': '9876543210',
            'guest_email': 'planner@example.com'
        })
        # Check that we got 200 OK rendering the payment checkout page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")

        # Verify that the booking was created in the DB
        from bookingapp.models import EventBooking
        booking = EventBooking.objects.filter(guest_email='planner@example.com').first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.hall, self.hall)
        self.assertEqual(booking.advance_amount, 25000.00) # 50000 * 2 days = 100000. 25% = 25000.

        # Simulating payment callback via POST
        callback_response = client.post(reverse('razorpay_callback'), {
            'booking_id': booking.id,
            'booking_type': 'event',
            'razorpay_payment_id': 'pay_event123'
        }, content_type='application/json')
        self.assertEqual(callback_response.status_code, 200)
        data = callback_response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('event_booking_confirmation', kwargs={'booking_id': booking.id}))

        # Check that the confirmation page loads successfully after payment confirmation redirect
        confirm_response = client.get(data['redirect_url'])
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, "Event Hall Booked Successfully!")
        self.assertContains(confirm_response, booking.long_order_id)
        self.assertContains(confirm_response, "Payment Confirmed")


class GuestActivitiesFilteringTest(TestCase):
    def setUp(self):
        from adminapp.models import Activity
        # Create an available activity
        self.available_activity = Activity.objects.create(
            activity_name="Yoga Wellness",
            activity_type="Yoga",
            price=600.00,
            description="Relaxing yoga session",
            status="Available"
        )
        # Create an unavailable activity
        self.unavailable_activity = Activity.objects.create(
            activity_name="Private Spa Massage",
            activity_type="Spa",
            price=2000.00,
            description="Luxury spa massage",
            status="Unavailable"
        )

    def test_activities_list_filters_out_unavailable(self):
        client = Client()
        response = client.get(reverse('activity'))
        self.assertEqual(response.status_code, 200)
        
        # Available activity should be in response
        self.assertContains(response, "Yoga Wellness")
        # Unavailable activity should NOT be in response
        self.assertNotContains(response, "Private Spa Massage")

    def test_activity_detail_status_check(self):
        client = Client()
        
        # Available activity detail page should load
        detail_url = reverse('activity_detail', kwargs={'id': self.available_activity.id})
        response = client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yoga Wellness")
        self.assertContains(response, "Booking Restricted for Guests") # should show guest warning

        # Unavailable activity detail page should return 404
        unavailable_url = reverse('activity_detail', kwargs={'id': self.unavailable_activity.id})
        response_un = client.get(unavailable_url)
        self.assertEqual(response_un.status_code, 404)

class GuestFoodOrderCheckoutTest(TestCase):
    def setUp(self):
        from adminapp.models import FoodItem
        self.food_item = FoodItem.objects.create(
            item_name="Spicy Paneer Tikka",
            category="Starter",
            price=300.00,
            quantity=10,
            status="Available",
            description="Delicious grilled paneer"
        )

    def test_guest_food_order_submission(self):
        client = Client()
        
        # Set up cart in session
        session = client.session
        session['cart'] = {str(self.food_item.id): 2}
        session.save()

        # Submit checkout form as guest
        response = client.post(reverse('food_order'), {
            'order_type': 'Delivery',
            'delivery_address': 'Room 302, StayZen Resort',
            'phone': '9876543210',
            'customer_name': 'Guest Foodie'
        })
        
        # Check that we got 200 OK rendering the payment page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import Order
        order = Order.objects.filter(customer_phone='9876543210').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.customer_name, 'Guest Foodie')
        self.assertEqual(order.order_type, 'Delivery')
        self.assertIsNone(order.user)
        
        # Simulating payment callback
        callback_response = client.post(reverse('razorpay_callback'), {
            'booking_id': order.id,
            'booking_type': 'food',
            'razorpay_payment_id': 'pay_food123'
        }, content_type='application/json')
        self.assertEqual(callback_response.status_code, 200)
        data = callback_response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('order_confirmation', kwargs={'order_id': order.id}))

        # Verify confirmation loads successfully
        confirm_response = client.get(data['redirect_url'])
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, "Order Confirmed")

    def test_guest_food_order_submission_dine_in(self):
        client = Client()
        
        # Set up cart in session
        session = client.session
        session['cart'] = {str(self.food_item.id): 1}
        session.save()

        # Submit checkout form as guest for DineIn
        response = client.post(reverse('food_order'), {
            'order_type': 'DineIn',
            'delivery_address': 'Table 5',
            'phone': '9876543212',
            'customer_name': 'Guest Diner'
        })
        
        # Check that we got 200 OK rendering the payment page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import Order
        order = Order.objects.filter(customer_phone='9876543212').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.customer_name, 'Guest Diner')
        self.assertEqual(order.order_type, 'DineIn')
        self.assertIsNone(order.user)

        # Simulating payment callback
        callback_response = client.post(reverse('razorpay_callback'), {
            'booking_id': order.id,
            'booking_type': 'food',
            'razorpay_payment_id': 'pay_food456'
        }, content_type='application/json')
        self.assertEqual(callback_response.status_code, 200)
        data = callback_response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('order_confirmation', kwargs={'order_id': order.id}))


class GuestTableReservationTest(TestCase):
    def setUp(self):
        from adminapp.models import RestaurantTable
        self.table = RestaurantTable.objects.create(
            table_number="T12",
            table_capacity=4,
            location="Indoor",
            status="Available",
            description="Nice indoor table"
        )

    def test_guest_table_reservation_submission(self):
        client = Client()
        response = client.post(reverse('table_list_guest'), {
            'table_id': self.table.id,
            'reservation_date': '2026-08-01',
            'reservation_time': '19:00',
            'end_time': '21:00',
            'guests': 3,
            'customer_name': 'Guest Table Booker',
            'phone': '9876543211'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import TableReservation
        reservation = TableReservation.objects.filter(phone='9876543211').first()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.customer_name, 'Guest Table Booker')
        self.assertEqual(reservation.guests, 3)
        self.assertEqual(reservation.duration_hours, 2)

        # Simulating payment callback
        callback_response = client.post(reverse('razorpay_callback'), {
            'booking_id': reservation.id,
            'booking_type': 'table',
            'razorpay_payment_id': 'pay_table123'
        }, content_type='application/json')
        self.assertEqual(callback_response.status_code, 200)
        data = callback_response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('table_reservation_confirmation', kwargs={'reservation_id': reservation.id}))

        # Verify confirmation loads successfully
        confirm_response = client.get(data['redirect_url'])
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, "Table Reserved")

    def test_guest_table_reservation_submission_with_seconds_time_format(self):
        client = Client()
        response = client.post(reverse('table_list_guest'), {
            'table_id': self.table.id,
            'reservation_date': '2026-08-01',
            'reservation_time': '19:00:00',
            'end_time': '22:00:00',
            'guests': 3,
            'customer_name': 'Guest Table Booker Sec',
            'phone': '9876543212'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import TableReservation
        reservation = TableReservation.objects.filter(phone='9876543212').first()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.customer_name, 'Guest Table Booker Sec')
        self.assertEqual(reservation.guests, 3)
        self.assertEqual(reservation.duration_hours, 3)

        # Simulating payment callback
        callback_response = client.post(reverse('razorpay_callback'), {
            'booking_id': reservation.id,
            'booking_type': 'table',
            'razorpay_payment_id': 'pay_table456'
        }, content_type='application/json')
        self.assertEqual(callback_response.status_code, 200)
        data = callback_response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('table_reservation_confirmation', kwargs={'reservation_id': reservation.id}))

    def test_guest_table_reservation_invalid_end_time(self):
        client = Client()
        response = client.post(reverse('table_list_guest'), {
            'table_id': self.table.id,
            'reservation_date': '2026-08-01',
            'reservation_time': '19:00',
            'end_time': '18:00',
            'guests': 3,
            'customer_name': 'Guest Invalid Booker',
            'phone': '9876543213'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('table_list_guest'))
        
        from bookingapp.models import TableReservation
        reservation_exists = TableReservation.objects.filter(phone='9876543213').exists()
        self.assertFalse(reservation_exists)


class LoyaltyPointsTest(TestCase):
    def setUp(self):
        from adminapp.models import Room
        from accountapp.models import Customer
        from bookingapp.models import RoomBooking
        from django.contrib.auth.models import User
        
        self.user = User.objects.create_user(
            username="loyaltyuser",
            password="testpassword",
            email="loyalty@example.com"
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone="1234567890",
            address="Test Address",
            gender="Male"
        )
        self.room = Room.objects.create(
            room_number="401",
            room_type="Single",
            description="Luxury room",
            max_adults=2,
            max_children=1,
            price=1500.00,
            status="Available"
        )
        self.booking = RoomBooking.objects.create(
            customer=self.customer,
            guest_name="Loyalty Guest",
            guest_phone="1234567890",
            guest_email="loyalty@example.com",
            room=self.room,
            check_in="2026-09-01",
            check_out="2026-09-03",
            adults=2,
            children=0,
            status="Pending",
            total_amount=3000.00,
            pending_payment=3000.00,
            final_amount=3000.00,
            payment_status="Pending"
        )

    def test_loyalty_earned_on_confirm(self):
        from bookingapp.models import LoyaltyTransaction

        # Confirm payment status
        self.booking.payment_status = "Confirmed"
        self.booking.save()
        
        # Verify points awarded: 3000.00 // 100 = 30 points
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.loyalty_points, 30)
        self.assertEqual(self.customer.lifetime_points_earned, 30)
        
        # Verify transaction log created
        tx = LoyaltyTransaction.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.transaction_type, LoyaltyTransaction.TRANSACTION_EARNED)
        self.assertEqual(tx.points, 30)
        
        # Verify points_earned updated in database
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.points_earned, 30)

    def test_loyalty_reversal_on_failed_payment(self):
        from accountapp.models import Customer
        
        # Confirm payment first
        self.booking.payment_status = "Confirmed"
        self.booking.save()
        
        # Change payment status to Failed
        self.booking.payment_status = "Failed"
        self.booking.save()
        
        # Verify points reversed to 0
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.loyalty_points, 0)
        self.assertEqual(self.customer.lifetime_points_earned, 0)
        
        # Verify points_earned set back to 0
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.points_earned, 0)

    def test_loyalty_reversal_on_cancellation(self):
        from accountapp.models import Customer
        
        # Confirm payment first
        self.booking.payment_status = "Confirmed"
        self.booking.save()
        
        # Cancel booking
        self.booking.status = "Cancelled"
        self.booking.save()
        
        # Verify points reversed to 0
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.loyalty_points, 0)
        self.assertEqual(self.customer.lifetime_points_earned, 0)
        
        # Verify points_earned set back to 0
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.points_earned, 0)

class RegisteredUserPaymentsTest(TestCase):
    def setUp(self):
        from adminapp.models import Room, event_hall, FoodItem, RestaurantTable, Activity, ActivitySession
        from accountapp.models import Customer
        from django.contrib.auth.models import User
        
        # User & Customer Setup
        self.user = User.objects.create_user(
            username="registered_payment_user",
            password="testpassword",
            email="reg@example.com"
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone="1122334455",
            address="Registered Addr",
            gender="Male",
            loyalty_points=50
        )
        
        # Room Setup
        self.room = Room.objects.create(
            room_number="505",
            room_type="Single",
            description="Room for testing",
            max_adults=2,
            max_children=1,
            price=2000.00,
            status="Available"
        )
        
        # Event Hall Setup
        self.hall = event_hall.objects.create(
            hall_name="Reg Event Hall",
            hall_type="birthday",
            hall_description="Hall description",
            hall_capacity=100,
            hall_price=10000.00,
            hall_status="available"
        )
        
        # Restaurant Table Setup
        self.table = RestaurantTable.objects.create(
            table_number="T50",
            table_capacity=4,
            location="Outdoor",
            status="Available",
            price=250.00,
            description="Nice outdoor table"
        )
        
        # Food Item Setup
        self.food_item = FoodItem.objects.create(
            item_name="Cheese Burger",
            category="Main Course",
            price=150.00,
            quantity=20,
            status="Available"
        )
        
        # Activity Setup
        self.activity = Activity.objects.create(
            activity_name="Tennis",
            activity_type="Sports",
            price=500.00,
            description="Tennis session",
            status="Available"
        )
        from datetime import date, time
        self.session = ActivitySession.objects.create(
            activity=self.activity,
            session_date=date(2026, 8, 15),
            start_time=time(14, 0),
            end_time=time(16, 0),
            status="Available",
            capacity=10
        )

    def test_registered_room_booking_with_loyalty(self):
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        # Room booking with 50 loyalty points checked
        response = client.post(reverse('room_booking'), {
            'room_id': self.room.id,
            'check_in': '2026-08-01',
            'check_out': '2026-08-03',
            'adults': 1,
            'children': 0,
            'redeem_points': 50
        })
        # Verify redirects to Razorpay payment page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        # Check booking details in database
        from bookingapp.models import RoomBooking
        booking = RoomBooking.objects.filter(customer=self.customer).last()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.points_redeemed, 50)
        self.assertEqual(booking.discount_amount, 50.00)
        # 4000.00 total - 50 discount = 3950.00. 25% = 987.50
        self.assertEqual(booking.advance_amount, 987.50)
        self.assertEqual(booking.pending_payment, 2962.50)
        self.assertEqual(booking.status, "Pending")
        self.assertEqual(booking.payment_status, "Pending")
        
        # Verify customer points updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.loyalty_points, 0)
        
        callback_res = client.post(reverse('razorpay_callback'), {
            'booking_id': booking.id,
            'booking_type': 'room',
            'razorpay_payment_id': 'pay_reg_room_1'
        }, content_type='application/json')
        self.assertEqual(callback_res.status_code, 200)
        data = callback_res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], f"{reverse('dashboard')}?booking_confirmed=true&type=Room+Booking&ref=SZ-RM-{booking.id}&amt={booking.advance_amount:.2f}")
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, "Confirmed")
        self.assertEqual(booking.payment_status, "Confirmed")

    def test_registered_room_booking_redeem_exceeds_amount_but_within_balance(self):
        self.customer.loyalty_points = 5000
        self.customer.save()

        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        response = client.post(reverse('room_booking'), {
            'room_id': self.room.id,
            'check_in': '2026-08-01',
            'check_out': '2026-08-03',
            'adults': 1,
            'children': 0,
            'redeem_points': 4500
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import RoomBooking
        booking = RoomBooking.objects.filter(customer=self.customer).last()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.points_redeemed, 4000)
        self.assertEqual(booking.discount_amount, 4000.00)
        self.assertEqual(booking.advance_amount, 0.00)
        self.assertEqual(booking.pending_payment, 0.00)
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.loyalty_points, 1000)

    def test_registered_event_booking_no_loyalty(self):
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        response = client.post(reverse('event_booking'), {
            'hall_id': self.hall.hall_id,
            'event_name': 'Birthday Party',
            'event_type': 'Birthday',
            'start_date': '2026-09-10',
            'end_date': '2026-09-10',
            'start_time': '12:00:00',
            'end_time': '16:00:00',
            'food_preference': 'Vegetarian',
            'guest_count': 50,
            'redeem_points': 0
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import EventBooking
        booking = EventBooking.objects.filter(customer=self.customer).last()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.points_redeemed, 0)
        # 10000.00 hall cost. 25% prepayment = 2500.00
        self.assertEqual(booking.advance_amount, 2500.00)
        self.assertEqual(booking.pending_payment, 7500.00)
        self.assertEqual(booking.status, "Pending")
        self.assertEqual(booking.payment_status, "Pending")

    def test_registered_table_reservation(self):
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        # Book a table from the dashboard
        response = client.post(reverse('restaurant_table_dashboard'), {
            'table_id': self.table.id,
            'reservation_date': '2026-08-10',
            'reservation_slot': 'Lunch',
            'guests': 2,
            'special_request': 'Quiet table'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import TableReservation
        res = TableReservation.objects.filter(customer=self.customer).last()
        self.assertIsNotNone(res)
        self.assertEqual(res.advance_amount, 500.00)
        self.assertEqual(res.status, "Pending")
        self.assertEqual(res.payment_status, "Pending")
        
        # Simulate payment callback
        callback_res = client.post(reverse('razorpay_callback'), {
            'booking_id': res.id,
            'booking_type': 'table',
            'razorpay_payment_id': 'pay_reg_table_1'
        }, content_type='application/json')
        self.assertEqual(callback_res.status_code, 200)
        data = callback_res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], f"{reverse('dashboard')}?booking_confirmed=true&type=Table+Reservation&ref=SZ-TB-{res.id}&amt={res.advance_amount:.2f}")

    def test_table_reservation_payment_failure(self):
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        # Book a table to get a pending reservation
        response = client.post(reverse('restaurant_table_dashboard'), {
            'table_id': self.table.id,
            'reservation_date': '2026-08-10',
            'reservation_slot': 'Lunch',
            'guests': 2,
            'special_request': 'Quiet table'
        })
        self.assertEqual(response.status_code, 200)
        
        from bookingapp.models import TableReservation
        res = TableReservation.objects.filter(customer=self.customer).last()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "Pending")
        
        # Simulate payment failure cleanup
        failure_res = client.post(reverse('payment_failure'), {
            'booking_id': res.id,
            'booking_type': 'table',
            'reason': 'Payment Cancelled/Dismissed by user'
        }, content_type='application/json')
        self.assertEqual(failure_res.status_code, 200)
        self.assertTrue(failure_res.json()['success'])
        
        # Verify the reservation was deleted
        self.assertFalse(TableReservation.objects.filter(id=res.id).exists())

    def test_registered_food_order(self):
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        # Put item in cart
        session = client.session
        session['cart'] = {str(self.food_item.id): 2}
        session.save()
        
        response = client.post(reverse('food_order_dashboard'), {
            'order_type': 'RoomService',
            'delivery_address': 'Room 505'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")
        
        from bookingapp.models import Order
        order = Order.objects.filter(user=self.user).last()
        self.assertIsNotNone(order)
        # 300 subtotal + 15 GST (5%) + 40 delivery fee = 355.00
        self.assertEqual(order.total_amount, 355.00)
        self.assertEqual(order.status, "Pending")
        
        # Simulate payment callback
        callback_res = client.post(reverse('razorpay_callback'), {
            'booking_id': order.id,
            'booking_type': 'food',
            'razorpay_payment_id': 'pay_reg_food_1'
        }, content_type='application/json')
        self.assertEqual(callback_res.status_code, 200)
        data = callback_res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], f"{reverse('dashboard')}?booking_confirmed=true&type=Food+Order&ref=SZ-FD-{order.id}&amt={order.total_amount:.2f}")

    def test_activity_booking_accumulates_cost(self):
        from bookingapp.models import RoomBooking
        # Setup confirmed room booking first
        rb = RoomBooking.objects.create(
            customer=self.customer,
            guest_name="Registered User",
            guest_phone="1122334455",
            guest_email="reg@example.com",
            room=self.room,
            check_in="2026-08-01",
            check_out="2026-08-03",
            adults=1,
            children=0,
            status="Confirmed",
            total_amount=4000.00,
            pending_payment=3000.00,
            final_amount=4000.00,
            advance_amount=1000.00,
            payment_status="Confirmed"
        )
        
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        # Book activity session
        response = client.post(reverse('book_activity_session', kwargs={'activity_id': self.activity.id}), {
            'session_id': self.session.id
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify RoomBooking totals accumulated the activity price (500.00)
        rb.refresh_from_db()
        self.assertEqual(rb.total_amount, 4500.00)
        self.assertEqual(rb.final_amount, 4500.00)
        self.assertEqual(rb.pending_payment, 3500.00)
        
        # Perform checkout (receptionist marks Completed)
        rb.status = "Completed"
        rb.save()
        
        # Verify final invoice reflects stay & activity costs
        import os
        from django.conf import settings
        invoice_path = os.path.join(settings.MEDIA_ROOT, 'invoices', f'invoice_{rb.id}.txt')
        self.assertTrue(os.path.exists(invoice_path))
        with open(invoice_path, 'r') as f:
            content = f.read()
            self.assertIn("Tennis", content)
            self.assertIn("INR 500.00", content)
            self.assertIn("Total Amount:         INR 4500.00", content)
            self.assertIn("Remaining Paid:       INR 3500.00", content)

    def test_checked_in_guest_can_book_activity(self):
        from bookingapp.models import RoomBooking, ActivityBooking
        # Setup Checked In room booking first
        rb = RoomBooking.objects.create(
            customer=self.customer,
            guest_name="Registered User",
            guest_phone="1122334455",
            guest_email="reg@example.com",
            room=self.room,
            check_in="2026-08-01",
            check_out="2026-08-03",
            adults=1,
            children=0,
            status="Checked In",
            total_amount=4000.00,
            pending_payment=3000.00,
            final_amount=4000.00,
            advance_amount=1000.00,
            payment_status="Confirmed"
        )
        
        client = Client()
        client.login(username="registered_payment_user", password="testpassword")
        
        initial_capacity = self.session.capacity
        
        # Book activity session
        response = client.post(reverse('book_activity_session', kwargs={'activity_id': self.activity.id}), {
            'session_id': self.session.id
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify ActivityBooking was created
        ab = ActivityBooking.objects.filter(room_booking=rb, activity=self.activity).first()
        self.assertIsNotNone(ab)
        self.assertEqual(ab.status, "Booked")
        
        # Verify Session capacity decremented
        self.session.refresh_from_db()
        self.assertEqual(self.session.capacity, initial_capacity - 1)

        # Cancel the activity booking
        ab.status = "Cancelled"
        ab.save()

        # Verify Session capacity incremented back
        self.session.refresh_from_db()
        self.assertEqual(self.session.capacity, initial_capacity)

    def test_offline_room_booking_razorpay(self):
        client = Client()
        from django.contrib.auth.models import User
        super_user, _ = User.objects.get_or_create(
            username="receptionist_super",
            defaults={'is_superuser': True, 'email': 'receptionist@example.com'}
        )
        super_user.set_password("superpassword")
        super_user.save()
        client.login(username="receptionist_super", password="superpassword")

        response = client.post(reverse('offline_booking'), {
            'customer_type': 'guest',
            'guest_name': 'Offline Guest',
            'guest_phone': '1234567890',
            'guest_email': 'guest@example.com',
            'guest_address': 'Offline St',
            'room_id': self.room.id,
            'check_in': '2026-08-01',
            'check_out': '2026-08-03',
            'adults': 1,
            'children': 0,
            'payment_method': 'Razorpay',
            'payment_status': 'Pending',
            'status': 'Pending'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")

        from bookingapp.models import RoomBooking
        booking = RoomBooking.objects.filter(guest_name="Offline Guest").last()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.advance_amount, 1000.00)
        self.assertEqual(booking.pending_payment, 3000.00)
        self.assertEqual(booking.status, "Pending")
        self.assertEqual(booking.payment_status, "Pending")
        self.assertEqual(booking.booking_source, "Offline")

    def test_offline_event_booking_razorpay(self):
        client = Client()
        from django.contrib.auth.models import User
        super_user, _ = User.objects.get_or_create(
            username="receptionist_super",
            defaults={'is_superuser': True, 'email': 'receptionist@example.com'}
        )
        super_user.set_password("superpassword")
        super_user.save()
        client.login(username="receptionist_super", password="superpassword")

        response = client.post(reverse('offline_event_booking'), {
            'customer_type': 'guest',
            'guest_name': 'Offline Event Guest',
            'guest_phone': '1234567890',
            'guest_email': 'eventguest@example.com',
            'guest_address': 'Offline St',
            'hall_id': self.hall.hall_id,
            'event_name': 'Offline Conf',
            'start_date': '2026-09-01',
            'end_date': '2026-09-01',
            'payment_method': 'Razorpay',
            'payment_status': 'Pending',
            'status': 'Pending'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")

        from bookingapp.models import EventBooking
        booking = EventBooking.objects.filter(guest_name="Offline Event Guest").last()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.advance_amount, 2500.00)
        self.assertEqual(booking.pending_payment, 7500.00)
        self.assertEqual(booking.status, "Pending")
        self.assertEqual(booking.payment_status, "Pending")
        self.assertEqual(booking.booking_source, "Offline")

    def test_offline_restaurant_table_and_order_razorpay(self):
        client = Client()
        from django.contrib.auth.models import User
        super_user, _ = User.objects.get_or_create(
            username="receptionist_super",
            defaults={'is_superuser': True, 'email': 'receptionist@example.com'}
        )
        super_user.set_password("superpassword")
        super_user.save()
        client.login(username="receptionist_super", password="superpassword")

        response = client.post(reverse('offline_restaurant_table'), {
            'customer_type': 'guest',
            'guest_name': 'Offline Dining Guest',
            'guest_phone': '1234567890',
            'guest_email': 'dining@example.com',
            'guest_address': 'Offline St',
            'book_table': 'on',
            'place_order': 'on',
            'table_id': self.table.id,
            'reservation_date': '2026-10-01',
            'reservation_time': '12:00',
            'guests': 2,
            'table_advance_amount': '500.00',
            f'food_qty_{self.food_item.id}': 2,
            'table_payment_method': 'Razorpay',
            'table_payment_status': 'Pending',
            'table_status': 'Pending',
            'order_type': 'DineIn',
            'order_status': 'Pending'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "guest/razorpay_payment.html")

        from bookingapp.models import TableReservation, Order
        res = TableReservation.objects.filter(customer_name="Offline Dining Guest").last()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "Pending")
        self.assertEqual(res.payment_status, "Pending")
        self.assertEqual(res.advance_amount, 500.00)

        order = Order.objects.filter(customer_name="Offline Dining Guest").last()
        self.assertIsNotNone(order)
        self.assertEqual(order.total_amount, 315.00)
        self.assertEqual(order.status, "Pending")

        # Test callback for offline room
        from bookingapp.models import RoomBooking
        room_b = RoomBooking.objects.create(
            customer=None,
            guest_name="Offline Room Guest Callback",
            guest_phone="1234567890",
            room=self.room,
            check_in="2026-08-05",
            check_out="2026-08-06",
            advance_amount=500.00,
            booking_source="Offline",
            status="Pending"
        )
        callback_res = client.post(reverse('razorpay_callback'), {
            'booking_id': room_b.id,
            'booking_type': 'room',
            'razorpay_payment_id': 'pay_off_room_1'
        }, content_type='application/json')
        self.assertEqual(callback_res.status_code, 200)
        self.assertEqual(callback_res.json()['redirect_url'], reverse('receptionist_room_bookings'))

        # Test callback for offline food order
        callback_res = client.post(reverse('razorpay_callback'), {
            'booking_id': order.id,
            'booking_type': 'food',
            'razorpay_payment_id': 'pay_off_food_1'
        }, content_type='application/json')
        self.assertEqual(callback_res.status_code, 200)
        self.assertEqual(callback_res.json()['redirect_url'], reverse('receptionist_restaurant_orders'))
        
        order.refresh_from_db()
        res.refresh_from_db()
        self.assertEqual(order.status, "Confirmed")
        self.assertEqual(res.status, "Confirmed")
        self.assertEqual(res.payment_status, "Confirmed")
        self.assertEqual(res.payment_method, "Razorpay")
        self.assertEqual(res.booking_reference, "pay_off_food_1")
        
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, "Reserved")


class FeedbackAndContactTest(TestCase):
    def test_contact_message_star_display(self):
        from guestapp.models import ContactMessage
        # Feedback with rating 4
        msg4 = ContactMessage(inquiry_type='feedback', name='Alice', email='alice@example.com', message='Great!', rating=4)
        self.assertEqual(msg4.star_display, [('★', True), ('★', True), ('★', True), ('★', True), ('☆', False)])
        
        # Feedback with rating 5
        msg5 = ContactMessage(inquiry_type='feedback', name='Bob', email='bob@example.com', message='Amazing!', rating=5)
        self.assertEqual(msg5.star_display, [('★', True), ('★', True), ('★', True), ('★', True), ('★', True)])
        
        # General enquiry with no rating
        msg_none = ContactMessage(inquiry_type='general', name='Charlie', email='charlie@example.com', message='Question?')
        self.assertEqual(msg_none.star_display, [])

    def test_contact_form_validation(self):
        from guestapp.forms import ContactMessageForm
        
        # Valid feedback submission
        form = ContactMessageForm(data={
            'inquiry_type': 'feedback',
            'name': 'Alice',
            'email': 'alice@example.com',
            'message': 'Great!',
            'rating': 4
        })
        self.assertTrue(form.is_valid())
        
        # Feedback submission without rating (should fail validation)
        form = ContactMessageForm(data={
            'inquiry_type': 'feedback',
            'name': 'Alice',
            'email': 'alice@example.com',
            'message': 'Great!',
            'rating': ''
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
        self.assertEqual(form.errors['rating'], ['Rating is required for feedback.'])

        # General enquiry with rating (rating should be cleared to None)
        form = ContactMessageForm(data={
            'inquiry_type': 'general',
            'name': 'Bob',
            'email': 'bob@example.com',
            'message': 'Question?',
            'rating': 4
        })
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)
        self.assertIsNone(instance.rating)

        # General enquiry without rating (should succeed with rating None)
        form = ContactMessageForm(data={
            'inquiry_type': 'general',
            'name': 'Bob',
            'email': 'bob@example.com',
            'message': 'Question?',
            'rating': ''
        })
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)
        self.assertIsNone(instance.rating)

    def test_about_page_dynamic_feedback_display(self):
        from guestapp.models import ContactMessage
        # Create general enquiry and feedback
        ContactMessage.objects.create(inquiry_type='general', name='Charlie', email='charlie@example.com', message='Hi')
        f1 = ContactMessage.objects.create(inquiry_type='feedback', name='Alice', email='alice@example.com', message='Superb!', rating=4)
        f2 = ContactMessage.objects.create(inquiry_type='feedback', name='Bob', email='bob@example.com', message='Lovely!', rating=5)

        client = Client()
        response = client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        
        # Verify dynamic feedbacks are present on the about page
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'Superb!')
        self.assertContains(response, 'Bob')
        self.assertContains(response, 'Lovely!')
        # Check that general enquiry is NOT displayed on the testimonials
        self.assertNotContains(response, 'Charlie')
        self.assertNotContains(response, 'Hi')




