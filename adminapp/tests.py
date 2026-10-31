from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from bookingapp.models import RoomBooking
from adminapp.models import Room
from decimal import Decimal
import datetime

class RefundStatusTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.client = Client()
        self.client.login(username='admin', password='password123')
        
        # Create Room and Booking
        self.room = Room.objects.create(
            room_number='102',
            room_type='Deluxe',
            price=Decimal('100.00'),
            max_adults=2,
            max_children=1,
            status='Available'
        )
        
        self.booking = RoomBooking.objects.create(
            long_order_id='TESTTOKEN123',
            guest_name='John Doe',
            guest_phone='1234567890',
            guest_email='john@example.com',
            room=self.room,
            check_in=datetime.date.today(),
            check_out=datetime.date.today() + datetime.timedelta(days=2),
            adults=2,
            children=0,
            status='Cancelled',
            total_amount=Decimal('200.00'),
            final_amount=Decimal('200.00'),
            advance_amount=Decimal('50.00'),
            pending_payment=Decimal('150.00'),
            payment_status='Pending',
            refund_status='Pending'
        )

    def test_update_refund_status_to_refunded(self):
        # Change status to Refunded
        url = reverse('admin_update_refund', kwargs={'token': self.booking.long_order_id})
        response = self.client.post(url, {'refund_status': 'Refunded'})
        self.assertEqual(response.status_code, 302)
        
        # Verify database update
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.refund_status, 'Refunded')

    def test_prevent_further_actions_after_refunded(self):
        # First set status to Refunded
        self.booking.refund_status = 'Refunded'
        self.booking.save()
        
        # Now try to update it to Approved
        url = reverse('admin_update_refund', kwargs={'token': self.booking.long_order_id})
        response = self.client.post(url, {'refund_status': 'Approved'})
        self.assertEqual(response.status_code, 302)
        
        # Check messages for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already been refunded" in str(m) for m in messages))
        
        # Verify it remains Refunded in database
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.refund_status, 'Refunded')

    def test_cancellations_page_disables_button(self):
        # Set status to Refunded
        self.booking.refund_status = 'Refunded'
        self.booking.save()
        
        response = self.client.get(reverse('admin_manage_cancellations'))
        self.assertEqual(response.status_code, 200)
        
        # Verify button has disabled attribute and doesn't render dropdown menu items
        content = response.content.decode('utf-8')
        self.assertIn('disabled', content)
