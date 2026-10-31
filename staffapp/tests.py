from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from adminapp.models import StaffUser, Department, Role
from staffapp.models import Menu, SubMenu, MenuPermission

class StaffPermissionMiddlewareTests(TestCase):
    def setUp(self):
        # 1. Create a superuser
        self.superuser = User.objects.create_superuser(
            username="super_admin",
            password="adminpassword",
            email="admin@example.com"
        )
        
        # 2. Create a standard staff user
        self.staff_user = User.objects.create_user(
            username="staff_member",
            password="staffpassword",
            email="staff@example.com"
        )
        self.dept_front_office, _ = Department.objects.get_or_create(name='Front Office')
        self.role_staff, _ = Role.objects.get_or_create(name='Staff')
        self.staff_profile = StaffUser.objects.create(
            user=self.staff_user,
            status=True,
            department=self.dept_front_office,
            role=self.role_staff
        )

        # 3. Create menus and submenus
        self.rooms_menu = Menu.objects.create(name="Rooms", icon="fa-bed")
        
        self.submenu_room_list = SubMenu.objects.create(
            menu=self.rooms_menu,
            name="All Rooms",
            url_name="room_list"
        )
        self.submenu_add_room = SubMenu.objects.create(
            menu=self.rooms_menu,
            name="Add Room",
            url_name="add_room"
        )

    def test_superuser_bypass_middleware(self):
        """Superuser should bypass all permission checks and access page."""
        client = Client()
        client.login(username="super_admin", password="adminpassword")
        
        # Superuser accessing add room page (no explicit permission needed)
        response = client.get(reverse('add_room'))
        self.assertEqual(response.status_code, 200)

    def test_staff_direct_submenu_permission(self):
        """Staff with direct submenu 'add_room' permission (can_view=True) is allowed."""
        client = Client()
        client.login(username="staff_member", password="staffpassword")
        
        # Create MenuPermission for add_room submenu directly
        MenuPermission.objects.create(
            user=self.staff_user,
            submenu=self.submenu_add_room,
            can_view=True
        )
        
        response = client.get(reverse('add_room'))
        self.assertEqual(response.status_code, 200)

    def test_staff_mapped_permission_success(self):
        """Staff with can_add=True on 'room_list' mapped submenu is allowed access to add_room."""
        client = Client()
        client.login(username="staff_member", password="staffpassword")
        
        # Create MenuPermission for room_list with can_add=True
        MenuPermission.objects.create(
            user=self.staff_user,
            submenu=self.submenu_room_list,
            can_view=True,
            can_add=True
        )
        
        response = client.get(reverse('add_room'))
        self.assertEqual(response.status_code, 200)

    def test_staff_no_permission_redirects(self):
        """Staff with no permissions is blocked from add_room and redirected."""
        client = Client()
        client.login(username="staff_member", password="staffpassword")
        
        response = client.get(reverse('add_room'))
        self.assertRedirects(response, reverse('staff_dashboard'))
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("You do not have permission to add in this section.", str(messages[0]))

    def test_staff_administrative_page_blocked(self):
        """Staff is blocked from accessing administrative pages not in mapping/submenu table."""
        client = Client()
        client.login(username="staff_member", password="staffpassword")
        
        response = client.get(reverse('add_staff_user'))
        self.assertRedirects(response, reverse('staff_dashboard'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Access denied. Administrator privileges required.", str(messages[0]))

    def test_receptionist_dynamic_offline_booking_permission(self):
        """Receptionist/front-office staff should dynamically have access to offline booking without explicit DB MenuPermission."""
        receptionist_user = User.objects.create_user(
            username="receptionist_test",
            password="receptionistpassword",
            email="receptionist@example.com"
        )
        receptionist_role, _ = Role.objects.get_or_create(name='Receptionist')
        StaffUser.objects.create(
            user=receptionist_user,
            status=True,
            department=self.dept_front_office,
            role=receptionist_role
        )

        client = Client()
        client.login(username="receptionist_test", password="receptionistpassword")

        # Accessing offline booking page should be successful (not blocked/redirected)
        response = client.get(reverse('offline_booking'))
        self.assertEqual(response.status_code, 200)

        # Context should contain Offline Booking in menus
        menus = list(response.context.get('menus', []))
        menu_names = [m['menu'].name for m in menus]
        self.assertIn('Offline Booking', menu_names)

        # Permissions should contain offline_booking view/add/edit/delete as True
        permissions = response.context.get('permissions', {})
        self.assertTrue(permissions.get('offline_booking', {}).get('view'))

class ReportsViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="super_admin_reports",
            password="adminpassword",
            email="admin_rep@example.com"
        )
        self.client = Client()
        self.client.login(username="super_admin_reports", password="adminpassword")

        # Create some dummy records to avoid errors when querying
        # Room, event_hall, Table, etc.
        from adminapp.models import Room, event_hall, RestaurantTable
        from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
        from staffapp.models import Attendance
        import datetime

        self.room = Room.objects.create(
            room_number="101A",
            room_type="Single",
            description="Test Room",
            max_adults=1,
            max_children=0,
            price=100.00
        )
        self.hall = event_hall.objects.create(
            hall_name="Convention Hall",
            hall_type="wedding",
            hall_description="Test Hall",
            hall_capacity=100,
            hall_price=500.00
        )
        self.table = RestaurantTable.objects.create(
            table_number="5",
            table_capacity=4,
            location="Indoor"
        )

        today = datetime.date.today()
        # Create a room booking
        RoomBooking.objects.create(
            room=self.room,
            guest_name="John Doe",
            check_in=today,
            check_out=today + datetime.timedelta(days=1),
            total_amount=100.00,
            final_amount=100.00,
            status="Completed"
        )
        # Create an event booking
        EventBooking.objects.create(
            hall=self.hall,
            event_name="Wedding",
            event_type="Wedding",
            guest_count=50,
            start_date=today,
            end_date=today,
            total_amount=500.00,
            final_amount=500.00,
            status="Completed"
        )
        # Create a table reservation
        TableReservation.objects.create(
            table=self.table,
            customer_name="Jane Doe",
            reservation_date=today,
            reservation_time="19:00",
            guests=2,
            advance_amount=20.00,
            status="Completed"
        )
        # Create an order
        Order.objects.create(
            order_type="DineIn",
            total_amount=50.00,
            subtotal_amount=45.00,
            gst_amount=5.00,
            status="Completed",
            customer_name="Jane Doe"
        )
        # Create attendance
        Attendance.objects.create(
            staff=self.superuser,
            date=today,
            status="Present",
            check_in_time="09:00:00"
        )

    def test_reports_overall_dashboard_renders(self):
        response = self.client.get(reverse('reports_overall'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rooms Report")
        self.assertContains(response, "Banquets Events")

    def test_reports_rooms_renders(self):
        response = self.client.get(reverse('reports_rooms'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rooms & Reservations")
        self.assertContains(response, "John Doe")

    def test_reports_events_renders(self):
        response = self.client.get(reverse('reports_events'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Banquets & Events")
        self.assertContains(response, "Wedding")

    def test_reports_tables_renders(self):
        response = self.client.get(reverse('reports_tables'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Table Reservations")
        self.assertContains(response, "Jane Doe")

    def test_reports_payments_renders(self):
        response = self.client.get(reverse('reports_payments'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payments & Settlements")

    def test_reports_attendance_renders(self):
        response = self.client.get(reverse('reports_attendance'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Attendance")
        self.assertContains(response, "super_admin_reports")

    def test_reports_financials_renders(self):
        response = self.client.get(reverse('reports_financials'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Financial Summary")
        self.assertContains(response, "Banquets &amp; Events")

    def test_export_pdf_report(self):
        response = self.client.get(reverse('generate_advanced_pdf_report'), {'section': 'overall'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_export_csv_report(self):
        for rtype in ['rooms', 'events', 'restaurant', 'tables', 'payments', 'attendance', 'financials']:
            response = self.client.get(reverse('generate_csv_report', args=[rtype]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'text/csv')

