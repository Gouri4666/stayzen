import os
import sys
import datetime
from decimal import Decimal
import django
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stayzen.settings')
django.setup()

from django.contrib.auth.models import User
from accountapp.models import Customer
from adminapp.models import Room, event_hall, RestaurantTable, FoodItem
from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order, OrderItem, LoyaltyTransaction
from staffapp.models import Attendance

def seed_data():
    print("Deleting old reports data...")
    # Clear out transactional data to ensure a clean state
    RoomBooking.objects.all().delete()
    EventBooking.objects.all().delete()
    TableReservation.objects.all().delete()
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    LoyaltyTransaction.objects.all().delete()
    Attendance.objects.all().delete()

    print("Fetching or creating static entities...")
    # 1. Admin/User
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin', 'admin@stayzen.com', 'admin123')
    
    # 2. Customers
    cust_user1, _ = User.objects.get_or_create(username='cust_alex', email='alex@gmail.com', defaults={'first_name': 'Alex', 'last_name': 'Jones'})
    cust1, _ = Customer.objects.get_or_create(user=cust_user1, defaults={'phone': '9876543210', 'address': '123 Pine St', 'gender': 'Male'})
    
    cust_user2, _ = User.objects.get_or_create(username='cust_jane', email='jane@gmail.com', defaults={'first_name': 'Jane', 'last_name': 'Smith'})
    cust2, _ = Customer.objects.get_or_create(user=cust_user2, defaults={'phone': '9876543211', 'address': '456 Oak St', 'gender': 'Female'})

    # Update date_joined for customers to test user count in timeframes
    # We will set cust_user1 date_joined to today (within 1h), and cust_user2 to last year.
    now = timezone.now()
    cust_user1.date_joined = now - datetime.timedelta(minutes=30)
    cust_user1.save()
    cust_user2.date_joined = now - datetime.timedelta(days=370)
    cust_user2.save()

    # 3. Rooms
    room1, _ = Room.objects.get_or_create(room_number='101', defaults={'room_type': 'Single', 'description': 'Single Deluxe Room', 'max_adults': 1, 'max_children': 0, 'price': Decimal('1500.00'), 'status': 'Available'})
    room2, _ = Room.objects.get_or_create(room_number='102', defaults={'room_type': 'Double', 'description': 'Double Queen Room', 'max_adults': 2, 'max_children': 1, 'price': Decimal('2500.00'), 'status': 'Available'})
    room3, _ = Room.objects.get_or_create(room_number='103', defaults={'room_type': 'Deluxe', 'description': 'Premium Deluxe Suite', 'max_adults': 2, 'max_children': 2, 'price': Decimal('4000.00'), 'status': 'Available'})
    room4, _ = Room.objects.get_or_create(room_number='104', defaults={'room_type': 'Suite', 'description': 'Presidential Luxury Suite', 'max_adults': 4, 'max_children': 2, 'price': Decimal('8000.00'), 'status': 'Available'})

    # 4. Event Halls
    hall1, _ = event_hall.objects.get_or_create(hall_name='Plaza Hall', defaults={'hall_type': 'banquet', 'hall_description': 'Grand Banquet Hall', 'hall_capacity': 200, 'hall_price': Decimal('15000.00'), 'hall_status': 'available'})
    hall2, _ = event_hall.objects.get_or_create(hall_name='Summit Room', defaults={'hall_type': 'conference', 'hall_description': 'Business Conference Room', 'hall_capacity': 50, 'hall_price': Decimal('8000.00'), 'hall_status': 'available'})

    # 5. Restaurant Tables
    table1, _ = RestaurantTable.objects.get_or_create(table_number='T1', defaults={'table_capacity': 2, 'location': 'Indoor', 'status': 'Available'})
    table2, _ = RestaurantTable.objects.get_or_create(table_number='T2', defaults={'table_capacity': 4, 'location': 'Window Side', 'status': 'Available'})
    table3, _ = RestaurantTable.objects.get_or_create(table_number='T3', defaults={'table_capacity': 6, 'location': 'Rooftop', 'status': 'Available'})

    # 6. Food Items
    food1, _ = FoodItem.objects.get_or_create(item_name='Paneer Butter Masala', defaults={'category': 'Main Course', 'cuisine': 'Indian', 'dietary_status': 'Veg', 'description': 'Paneer cooked in butter gravy', 'price': Decimal('280.00'), 'quantity': 100, 'status': 'Available'})
    food2, _ = FoodItem.objects.get_or_create(item_name='Chicken Biryani', defaults={'category': 'Main Course', 'cuisine': 'Indian', 'dietary_status': 'Non-Veg', 'description': 'Fragrant biryani rice with spiced chicken', 'price': Decimal('350.00'), 'quantity': 80, 'status': 'Available'})
    food3, _ = FoodItem.objects.get_or_create(item_name='Mojito', defaults={'category': 'Beverage', 'cuisine': 'Continental', 'dietary_status': 'Veg', 'description': 'Refreshing mint lime mojito', 'price': Decimal('150.00'), 'quantity': 50, 'status': 'Available'})

    # Today is 2026-06-21. Let's seed bookings for different timeframes relative to this.
    today = timezone.localdate()
    yesterday = today - datetime.timedelta(days=1)
    last_week_start = today - datetime.timedelta(days=today.weekday() + 7) # Start of last week
    next_week_start = today + datetime.timedelta(days=7) # Next week
    last_month_day = today - datetime.timedelta(days=30)
    last_year_day = today - datetime.timedelta(days=370)

    print("Seeding Room Bookings...")
    # Room bookings
    # 1. Today (Within 24 Hours / This Week / This Month / This Year)
    rb1 = RoomBooking.objects.create(
        customer=cust1, guest_name='Alex Jones', guest_phone='9876543210', guest_email='alex@gmail.com',
        room=room3, check_in=today, check_out=today + datetime.timedelta(days=2), status='Confirmed',
        total_amount=Decimal('8000.00'), discount_amount=Decimal('500.00'), final_amount=Decimal('7500.00'),
        payment_status='Confirmed', advance_amount=Decimal('2000.00'), payment_method='Card'
    )
    # 2. Next week (future booking - should display in This Month / This Year)
    rb2 = RoomBooking.objects.create(
        customer=cust1, guest_name='Alex Jones', room=room2, check_in=next_week_start, check_out=next_week_start + datetime.timedelta(days=3),
        status='Confirmed', total_amount=Decimal('7500.00'), discount_amount=Decimal('0.00'), final_amount=Decimal('7500.00'),
        payment_status='Pending', advance_amount=Decimal('0.00'), payment_method='Cash'
    )
    # 3. Last Year (Last Year / This Year - depending on dates, strictly Last Year 2025)
    rb3 = RoomBooking.objects.create(
        customer=cust2, guest_name='Jane Smith', room=room1, check_in=last_year_day, check_out=last_year_day + datetime.timedelta(days=5),
        status='Completed', total_amount=Decimal('7500.00'), discount_amount=Decimal('1000.00'), final_amount=Decimal('6500.00'),
        payment_status='Fully Paid', advance_amount=Decimal('6500.00'), payment_method='Cash'
    )

    print("Seeding Event Bookings...")
    # Event bookings
    # 1. Today (This Month / This Year)
    eb1 = EventBooking.objects.create(
        customer=cust1, hall=hall1, event_name='Alex Birthday', guest_name='Alex Jones', guest_count=50,
        event_type='Birthday', start_date=today, end_date=today, total_amount=Decimal('15000.00'),
        discount_amount=Decimal('1000.00'), final_amount=Decimal('14000.00'), payment_status='Confirmed',
        status='Confirmed', advance_amount=Decimal('5000.00'), payment_method='Card'
    )
    # 2. Last year (Last Year)
    eb2 = EventBooking.objects.create(
        customer=cust2, hall=hall2, event_name='Corporate Seminar', guest_name='Jane Smith', guest_count=30,
        event_type='Corporate', start_date=last_year_day, end_date=last_year_day, total_amount=Decimal('8000.00'),
        discount_amount=Decimal('0.00'), final_amount=Decimal('8000.00'), payment_status='Fully Paid',
        status='Completed', advance_amount=Decimal('8000.00'), payment_method='Card'
    )

    print("Seeding Table Reservations...")
    # Table Reservations
    # 1. Today (This Month / This Year)
    tr1 = TableReservation.objects.create(
        table=table2, customer_name='Alex Jones', phone='9876543210', reservation_date=today,
        reservation_time=datetime.time(19, 0), guests=4, status='Confirmed', advance_amount=Decimal('500.00'),
        payment_method='UPI', payment_status='Paid'
    )
    # 2. Last Year (Last Year)
    tr2 = TableReservation.objects.create(
        table=table1, customer_name='Jane Smith', phone='9876543211', reservation_date=last_year_day,
        reservation_time=datetime.time(13, 0), guests=2, status='Completed', advance_amount=Decimal('0.00'),
        payment_method='Cash', payment_status='Pending'
    )

    print("Seeding Orders and Order Items...")
    # Orders and OrderItems (requires datetime and using .update() for auto_now_add field order_date)
    # 1. Within 1 Hour (1h / 24h / This Week / This Month / This Year)
    o1 = Order.objects.create(
        order_type='RoomService', total_amount=Decimal('780.00'), subtotal_amount=Decimal('700.00'),
        discount_amount=Decimal('20.00'), gst_amount=Decimal('100.00'), status='Completed', customer_name='Alex Jones'
    )
    OrderItem.objects.create(order=o1, food=food1, quantity=2) # Paneer Butter Masala: 280*2 = 560
    OrderItem.objects.create(order=o1, food=food3, quantity=1) # Mojito: 150*1 = 150
    Order.objects.filter(pk=o1.pk).update(order_date=now - datetime.timedelta(minutes=15))

    # 2. Yesterday (24h / This Week / This Month / This Year)
    o2 = Order.objects.create(
        order_type='DineIn', total_amount=Decimal('350.00'), subtotal_amount=Decimal('350.00'),
        discount_amount=Decimal('0.00'), gst_amount=Decimal('0.00'), status='Completed', customer_name='Walk-in'
    )
    OrderItem.objects.create(order=o2, food=food2, quantity=1) # Chicken Biryani: 350*1 = 350
    Order.objects.filter(pk=o2.pk).update(order_date=now - datetime.timedelta(hours=12))

    # 3. Last Year (Last Year)
    o3 = Order.objects.create(
        order_type='DineIn', total_amount=Decimal('850.00'), subtotal_amount=Decimal('850.00'),
        discount_amount=Decimal('50.00'), gst_amount=Decimal('50.00'), status='Completed', customer_name='Jane Smith'
    )
    OrderItem.objects.create(order=o3, food=food2, quantity=2) # Chicken Biryani: 350*2 = 700
    OrderItem.objects.create(order=o3, food=food3, quantity=1) # Mojito: 150
    Order.objects.filter(pk=o3.pk).update(order_date=now - datetime.timedelta(days=370))

    print("Seeding Loyalty Transactions...")
    # Loyalty Transactions (using .update() for auto_now_add field created_at)
    # 1. Earned today
    lt1 = LoyaltyTransaction.objects.create(
        customer=cust1, booking_reference=f'RES-ADV-{rb1.id}', transaction_type='Earned', points=75, amount=Decimal('7500.00')
    )
    LoyaltyTransaction.objects.filter(pk=lt1.pk).update(created_at=now - datetime.timedelta(minutes=20))

    # 2. Redeemed today
    lt2 = LoyaltyTransaction.objects.create(
        customer=cust1, booking_reference=f'RES-ADV-{rb1.id}', transaction_type='Redeemed', points=20, amount=Decimal('200.00')
    )
    LoyaltyTransaction.objects.filter(pk=lt2.pk).update(created_at=now - datetime.timedelta(minutes=10))

    # 3. Earned last year
    lt3 = LoyaltyTransaction.objects.create(
        customer=cust2, booking_reference=f'RES-ADV-{rb3.id}', transaction_type='Earned', points=65, amount=Decimal('6500.00')
    )
    LoyaltyTransaction.objects.filter(pk=lt3.pk).update(created_at=now - datetime.timedelta(days=370))

    print("Seeding Staff Attendance...")
    # Attendance records
    staff_user = User.objects.filter(is_staff=True, is_superuser=False).first()
    if not staff_user:
        staff_user, _ = User.objects.get_or_create(username='arun', defaults={'first_name': 'Arun', 'is_staff': True})
    
    # Attendance for today
    Attendance.objects.create(
        staff=staff_user, date=today, check_in_time=datetime.time(9, 0), check_out_time=datetime.time(17, 0),
        status='Present', working_hours=datetime.timedelta(hours=8)
    )
    # Attendance for yesterday
    Attendance.objects.create(
        staff=staff_user, date=yesterday, check_in_time=datetime.time(9, 15), check_out_time=datetime.time(17, 0),
        status='Late', working_hours=datetime.timedelta(hours=7, minutes=45)
    )

    print("Verification counts:")
    print(f"RoomBookings: {RoomBooking.objects.count()}")
    print(f"EventBookings: {EventBooking.objects.count()}")
    print(f"TableReservations: {TableReservation.objects.count()}")
    print(f"Orders: {Order.objects.count()}")
    print(f"LoyaltyTransactions: {LoyaltyTransaction.objects.count()}")
    print(f"Attendance: {Attendance.objects.count()}")
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_data()
