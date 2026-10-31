from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Customer
from bookingapp.models import RoomBooking, EventBooking, LoyaltyTransaction
from adminapp.models import Room, event_hall, Package, FoodItem
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Customer
import hashlib
import re
from django.http import JsonResponse
from django.views.decorators.http import require_POST


def register(request):
    if request.method == 'POST':
        # 1. Collect form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Optional fields
        gender = request.POST.get('gender', 'Other')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        image = request.FILES.get('image')

        # 2. Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'accounts/register.html')

        # Auto-generate unique username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # 3. Create User and Customer objects
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            Customer.objects.create(
                user=user,
                phone=phone,
                address=address,
                gender=gender,
                image=image
            )
            
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'An error occurred during registration: {e}')
            return render(request, 'accounts/register.html')

    return render(request, 'accounts/register.html')
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        elif request.user.is_staff:
            return redirect('staff_dashboard')
        return redirect('home')

    if request.method == 'POST':

        submitted_email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        next_url = request.POST.get('next', '')

        user = None
        if submitted_email:
            # Try to authenticate assuming submitted_email is a username
            user = authenticate(request, username=submitted_email, password=password)
            
            if user is None:
                # Fallback to authenticate by email
                try:
                    existing_user = User.objects.get(email=submitted_email)
                    user = authenticate(
                        request,
                        username=existing_user.username,
                        password=password
                    )
                except User.DoesNotExist:
                    user = None
                except User.MultipleObjectsReturned:
                    existing_user = User.objects.filter(email=submitted_email).first()
                    user = authenticate(
                        request,
                        username=existing_user.username,
                        password=password
                    )

        if user is not None:

            login(request, user)

            if user.is_superuser:
                return redirect('admin_dashboard')
            elif user.is_staff:
                return redirect('staff_dashboard')

            # Redirect to 'next' if provided and safe, else go to home
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('home')

        else:

            return render(
                request,
                'accounts/login.html',
                {
                    'error': 'Invalid Username or Password',
                    'next': next_url,
                }
            )

    next_url = request.GET.get('next', '')
    return render(request, 'accounts/login.html', {'next': next_url})


def cleanup_pending_bookings(customer):
    if not customer:
        return
    from django.utils import timezone
    from datetime import timedelta
    expiration_limit = timezone.now() - timedelta(minutes=10)
    RoomBooking.objects.filter(
        customer=customer,
        status="Pending",
        payment_status="Pending",
        created_at__lt=expiration_limit
    ).delete()
    EventBooking.objects.filter(
        customer=customer,
        status="Pending",
        payment_status="Pending",
        created_at__lt=expiration_limit
    ).delete()


@login_required
def dashboard(request):
    customer = None
    notifications = []
    try:
        customer = Customer.objects.get(user=request.user)
        cleanup_pending_bookings(customer)
        
        # Get active room bookings
        room_bookings = RoomBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for rb in room_bookings:
            if rb.status in ['Cancelled', 'Completed']:
                continue
            
            if rb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Room Booking',
                    'title': f"Room {rb.room.room_number} Payment Pending ⌛",
                    'message': f"Pending 25% downpayment of ₹{rb.pending_payment} (Total: ₹{rb.final_amount}). Please pay to confirm.",
                    'date': rb.created_at
                })
            elif rb.status in ['Reserved', 'Confirmed'] or rb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Room Booking',
                    'title': f"Room {rb.room.room_number} Confirmed 🎉",
                    'message': f"Your stay is confirmed from {rb.check_in.strftime('%d %b %Y')} to {rb.check_out.strftime('%d %b %Y')}.",
                    'date': rb.created_at
                })
            elif rb.status == 'Checked In':
                notifications.append({
                    'type': 'info',
                    'category': 'Room Booking',
                    'title': f"Checked In to Room {rb.room.room_number} 🔑",
                    'message': f"Enjoy your stay! Scheduled checkout is on {rb.check_out.strftime('%d %b %Y')}.",
                    'date': rb.created_at
                })

        # Get active event bookings
        event_bookings = EventBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for eb in event_bookings:
            if eb.status in ['Cancelled', 'Completed']:
                continue

            if eb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' in {eb.hall.hall_name} Payment Pending ⌛",
                    'message': f"Pending 25% downpayment of ₹{eb.pending_payment} (Total: ₹{eb.final_amount}). Please pay to confirm.",
                    'date': eb.created_at
                })
            elif eb.status == 'Confirmed' or eb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' in {eb.hall.hall_name} Confirmed 🎉",
                    'message': f"Your event '{eb.event_name}' is confirmed for {eb.start_date.strftime('%d %b %Y')}.",
                    'date': eb.created_at
                })
            elif eb.status == 'Checked In':
                notifications.append({
                    'type': 'info',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' In Progress 🏛️",
                    'message': f"Enjoy your event at {eb.hall.hall_name}.",
                    'date': eb.created_at
                })
    except Customer.DoesNotExist:
        pass

    if notifications:
        notifications.sort(key=lambda x: x['date'], reverse=True)

    latest_booking = None
    loyalty_summary = None
    if customer:
        latest_booking = RoomBooking.objects.filter(customer=customer).last()
        last_earned = LoyaltyTransaction.objects.filter(
            customer=customer,
            transaction_type=LoyaltyTransaction.TRANSACTION_EARNED
        ).first()
        last_redeemed = LoyaltyTransaction.objects.filter(
            customer=customer,
            transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED
        ).first()
        loyalty_summary = {
            'current_points': customer.loyalty_points,
            'membership_status': customer.membership_status,
            'lifetime_points_earned': customer.lifetime_points_earned,
            'last_earned_points': last_earned.points if last_earned else 0,
            'last_redeemed_points': last_redeemed.points if last_redeemed else 0,
            'next_membership_tier': customer.next_membership_tier,
            'points_needed_for_next_tier': customer.points_needed_for_next_tier,
            'progress_percent': customer.membership_progress_percent,
        }

    is_confirmed = latest_booking is not None and latest_booking.status in ['Confirmed', 'Reserved', 'Checked In']

    return render(
        request,
        'accounts/dashboard.html',
        {
            'notifications': notifications,
            'latest_booking': latest_booking,
            'is_confirmed': is_confirmed,
            'customer': customer,
            'loyalty_summary': loyalty_summary
        }
    )


@login_required
def my_bookings(request):
    from bookingapp.models import TableReservation, Order

    try:
        customer = Customer.objects.get(user=request.user)
        cleanup_pending_bookings(customer)
        room_bookings = RoomBooking.objects.filter(customer=customer)\
            .select_related('room')\
            .prefetch_related('activitybooking_set__activity', 'activitybooking_set__session')\
            .order_by('-created_at')
        event_bookings = EventBooking.objects.filter(customer=customer)\
            .select_related('hall', 'package')\
            .prefetch_related('package__services')\
            .order_by('-created_at')
            
        from django.utils import timezone
        from datetime import timedelta
        limit = timezone.now() - timedelta(minutes=10)
        for b in room_bookings:
            b.is_resumable = (b.status == 'Pending' and b.payment_status == 'Pending' and b.created_at >= limit)
        for b in event_bookings:
            b.is_resumable = (b.status == 'Pending' and b.payment_status == 'Pending' and b.created_at >= limit)
    except Customer.DoesNotExist:
        room_bookings = []
        event_bookings = []

    table_reservations = TableReservation.objects.filter(
        customer_name=request.user.username
    ).select_related('table').order_by('-created_at')

    food_orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items__food').order_by('-order_date')
    
    return render(request, 'accounts/my_bookings.html', {
        'room_bookings': room_bookings,
        'event_bookings': event_bookings,
        'table_reservations': table_reservations,
        'food_orders': food_orders
    })

@login_required
def my_profile(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = None
    
    return render(request, 'accounts/my_profile.html', {
        'customer': customer
    })

from django.contrib.auth import update_session_auth_hash
from django.contrib import messages

@login_required
def edit_profile(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = Customer(user=request.user)
        
    if request.method == 'POST':
        # 1. Update the built-in Django User model
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # 2. Update your custom Customer model
        customer.phone = request.POST.get('phone', '')
        customer.address = request.POST.get('address', '')
        customer.gender = request.POST.get('gender', '')
        
        # Handle the image file upload
        if 'image' in request.FILES:
            customer.image = request.FILES['image']
            
        customer.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('my_profile')
        
    return render(request, 'accounts/edit_profile.html', {
        'customer': customer
    })
@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(old_password):
            messages.error(request, 'Incorrect old password.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('my_profile')
            
    return render(request, 'accounts/change_password.html')

@login_required
def event_halls_dashboard(request):
    return redirect('event')

@login_required
def rooms_dashboard(request):
    return redirect('rooms')

@login_required
def room_detail_dashboard(request, room_id):
    return redirect('room_detail', room_id=room_id)






@login_required
def activities_dashboard(request):
    return redirect('activity')


@login_required
def activity_detail_dashboard(request, id):
    return redirect('activity_detail', id=id)


@login_required
def gallery_dashboard(request):
    from adminapp.models import Room, event_hall, FoodItem, Activity
    
    gallery_items = []
    
    for r in Room.objects.all():
        if r.image:
            gallery_items.append({'url': r.image.url, 'title': f"Room {r.room_number}", 'category': 'Rooms'})
            
    for h in event_hall.objects.all():
        if h.hall_image:
            gallery_items.append({'url': h.hall_image.url, 'title': h.hall_name, 'category': 'Event Halls'})
            
    for f in FoodItem.objects.all():
        if f.image:
            gallery_items.append({'url': f.image.url, 'title': f.item_name, 'category': 'Dining'})
            
    for a in Activity.objects.all():
        if a.activity_image:
            gallery_items.append({'url': a.activity_image.url, 'title': a.activity_name, 'category': 'Activities'})

    return render(request, 'accounts/gallery.html', {
        'gallery_items': gallery_items
    })

@login_required
def food_menu_dashboard(request):
    return redirect('food_menu')



@login_required
def view_cart_dashboard(request):
    cart = request.session.get('cart', {})

    cart_items = []
    total = 0

    for food_id, qty in cart.items():
        try:
            food = FoodItem.objects.get(id=food_id)
            item_total = food.price * qty
            total += item_total

            cart_items.append({
                'food': food,
                'qty': qty,
                'subtotal': item_total
            })
        except FoodItem.DoesNotExist:
            pass

    return render(request, 'accounts/view_cart.html', {
        'cart_items': cart_items,
        'total': total
    })

from django.shortcuts import redirect, get_object_or_404
from adminapp.models import FoodItem

@login_required
def add_to_cart_dashboard(request, food_id):
    cart = request.session.get('cart', {})

    food_id = str(food_id)
    cart[food_id] = cart.get(food_id, 0) + 1

    request.session['cart'] = cart
    request.session.modified = True

    next_url = request.POST.get('next') or request.GET.get('next')

    if next_url:
        return redirect(next_url)

    return redirect('food_menu_dashboard')
@login_required
def increase_cart_dashboard(request, food_id):
    cart = request.session.get('cart', {})

    cart[str(food_id)] = cart.get(str(food_id), 0) + 1
    request.session['cart'] = cart

    next_url = request.GET.get('next')
    return redirect(next_url if next_url else 'food_menu_dashboard')

@login_required
def decrease_cart_dashboard(request, food_id):
    cart = request.session.get('cart', {})

    food_id = str(food_id)

    if food_id in cart:
        cart[food_id] -= 1

        if cart[food_id] <= 0:
            del cart[food_id]

    request.session['cart'] = cart

    next_url = request.GET.get('next')
    return redirect(next_url if next_url else 'food_menu_dashboard')

@login_required
def remove_from_cart_dashboard(request, food_id):
    cart = request.session.get('cart', {})

    food_id = str(food_id)

    if food_id in cart:
        del cart[food_id]

    request.session['cart'] = cart

    return redirect('view_cart_dashboard')

def logout_view(request):

    logout(request)
    messages.success(request, 'Logged out successfully', extra_tags='logout-success')

    return redirect('home')


@login_required
def notifications_view(request):
    notifications = []
    try:
        customer = Customer.objects.get(user=request.user)

        room_bookings = RoomBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for rb in room_bookings:
            if rb.status in ['Cancelled', 'Completed']:
                continue
            if rb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Room Booking',
                    'title': f"Room {rb.room.room_number} Payment Pending ⌛",
                    'message': f"Pending 25% downpayment of ₹{rb.pending_payment} (Total: ₹{rb.final_amount}). Please pay to confirm.",
                    'date': rb.created_at
                })
            elif rb.status in ['Reserved', 'Confirmed'] or rb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Room Booking',
                    'title': f"Room {rb.room.room_number} Confirmed 🎉",
                    'message': f"Your stay is confirmed from {rb.check_in.strftime('%d %b %Y')} to {rb.check_out.strftime('%d %b %Y')}.",
                    'date': rb.created_at
                })
            elif rb.status == 'Checked In':
                notifications.append({
                    'type': 'info',
                    'category': 'Room Booking',
                    'title': f"Checked In to Room {rb.room.room_number} 🔑",
                    'message': f"Enjoy your stay! Scheduled checkout is on {rb.check_out.strftime('%d %b %Y')}.",
                    'date': rb.created_at
                })

        event_bookings = EventBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for eb in event_bookings:
            if eb.status in ['Cancelled', 'Completed']:
                continue
            if eb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' Payment Pending ⌛",
                    'message': f"Pending 25% downpayment of ₹{eb.pending_payment} (Total: ₹{eb.final_amount}). Please pay to confirm.",
                    'date': eb.created_at
                })
            elif eb.status == 'Confirmed' or eb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' Confirmed 🎉",
                    'message': f"Your event is confirmed for {eb.start_date.strftime('%d %b %Y')}.",
                    'date': eb.created_at
                })
            elif eb.status == 'Checked In':
                notifications.append({
                    'type': 'info',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' In Progress 🏛️",
                    'message': f"Enjoy your event at {eb.hall.hall_name}.",
                    'date': eb.created_at
                })
    except Customer.DoesNotExist:
        pass

    if notifications:
        notifications.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'accounts/notifications.html', {
        'notifications': notifications
    })


@login_required
def loyalty_points(request):
    customer = None
    transactions = []
    try:
        customer = Customer.objects.get(user=request.user)
        transactions = LoyaltyTransaction.objects.filter(customer=customer).order_by('-created_at')
    except Customer.DoesNotExist:
        pass
    return render(request, 'accounts/loyalty_points.html', {
        'customer': customer,
        'transactions': transactions,
    })


@login_required
def membership_status(request):
    customer = None
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        pass
    return render(request, 'accounts/membership_status.html', {
        'customer': customer,
    })
from django.db.models import Q # Add this import at the top

@login_required
def payment_history(request):
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
    
    room_bookings = []
    event_bookings = []
    table_reservations = []
    food_orders = []
    
    try:
        customer = Customer.objects.get(user=request.user)
        
        # Querying room and event bookings
        room_bookings = RoomBooking.objects.filter(
            customer=customer, payment_status__in=['Confirmed', 'Fully Paid', 'Paid']
        ).order_by('-created_at')
        
        event_bookings = EventBooking.objects.filter(
            customer=customer, payment_status__in=['Confirmed', 'Fully Paid', 'Paid']
        ).order_by('-created_at')
        
        # Querying Table Reservations (checking both Customer link and username match)
        table_reservations = TableReservation.objects.filter(
            Q(customer=customer) | Q(customer_name=request.user.username)
        ).filter(payment_status__in=['Confirmed', 'Fully Paid', 'Paid', 'Completed']).order_by('-created_at')
        
    except Customer.DoesNotExist:
        # If no customer profile, just check by username
        table_reservations = TableReservation.objects.filter(
            customer_name=request.user.username
        ).filter(payment_status__in=['Confirmed', 'Fully Paid', 'Paid', 'Completed']).order_by('-created_at')

    # Food Orders
    food_orders = Order.objects.filter(
        user=request.user, status__in=['Delivered', 'Confirmed', 'Completed']
    ).order_by('-order_date')

    return render(request, 'accounts/payment_history.html', {
        'room_bookings': room_bookings,
        'event_bookings': event_bookings,
        'table_reservations': table_reservations,
        'food_orders': food_orders,
    })

    
@login_required
def account_settings(request):
    from django.contrib import messages
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'deactivate':
            request.user.is_active = False
            request.user.save()
            logout(request)
            messages.success(request, 'Your account has been deactivated.')
            return redirect('home')
        messages.success(request, 'Settings saved.')
        return redirect('account_settings')
    return render(request, 'accounts/account_settings.html')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from adminapp.models import RestaurantTable
from bookingapp.models import TableReservation

@login_required
def restaurant_table_dashboard(request):
    return redirect('table_list_guest')



#last changes
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE
)


def strip_emoji(text):
    return EMOJI_PATTERN.sub('', text).strip()


def make_notif_id(title, date):
    raw = f"{title}-{date.isoformat()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

from bookingapp.models import Order
from bookingapp.models import ActivityBooking
@login_required
def notifications_view(request):
    notifications = []
    try:
        customer = Customer.objects.get(user=request.user)

        room_bookings = RoomBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for rb in room_bookings:
            if rb.status in ['Cancelled', 'Completed']:
                continue
            if rb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Room Booking',
                    'title': f"Room {rb.room.room_number} Payment Pending",
                    'message': f"Pending 25% downpayment of ₹{rb.pending_payment} (Total: ₹{rb.final_amount}). Please pay to confirm.",
                    'date': rb.created_at
                })
            elif rb.status in ['Reserved', 'Confirmed'] or rb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Room Booking',
                    'title': f"Room {rb.room.room_number} Confirmed",
                    'message': f"Your stay is confirmed from {rb.check_in.strftime('%d %b %Y')} to {rb.check_out.strftime('%d %b %Y')}.",
                    'date': rb.created_at
                })
            elif rb.status == 'Checked In':
                notifications.append({
                    'type': 'info',
                    'category': 'Room Booking',
                    'title': f"Checked In to Room {rb.room.room_number}",
                    'message': f"Enjoy your stay! Scheduled checkout is on {rb.check_out.strftime('%d %b %Y')}.",
                    'date': rb.created_at
                })

        event_bookings = EventBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for eb in event_bookings:
            if eb.status in ['Cancelled', 'Completed']:
                continue
            if eb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' Payment Pending",
                    'message': f"Pending 25% downpayment of ₹{eb.pending_payment} (Total: ₹{eb.final_amount}). Please pay to confirm.",
                    'date': eb.created_at
                })
            elif eb.status == 'Confirmed' or eb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' Confirmed",
                    'message': f"Your event is confirmed for {eb.start_date.strftime('%d %b %Y')}.",
                    'date': eb.created_at
                })
            elif eb.status == 'Checked In':
                notifications.append({
                    'type': 'info',
                    'category': 'Event Booking',
                    'title': f"Event '{eb.event_name}' In Progress",
                    'message': f"Enjoy your event at {eb.hall.hall_name}.",
                    'date': eb.created_at
                })

        # --- Table Reservation notifications ---
        table_reservations = TableReservation.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for tb in table_reservations:
            if tb.status in ['Cancelled', 'Completed']:
                continue
            if tb.payment_status == 'Pending':
                notifications.append({
                    'type': 'pending_payment',
                    'category': 'Table Reservation',
                    'title': f"Table {tb.table.table_number} Payment Pending",
                    'message': f"Pending advance payment of ₹{tb.advance_amount} for your table reservation. Please pay to confirm.",
                    'date': tb.created_at
                })
            elif tb.status == 'Confirmed' or tb.payment_status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Table Reservation',
                    'title': f"Table {tb.table.table_number} Reservation Confirmed",
                    'message': f"Your table reservation is confirmed for {tb.reservation_date.strftime('%d %b %Y')} at {tb.reservation_time.strftime('%I:%M %p')}.",
                    'date': tb.created_at
                })

        # --- Food Order notifications ---
        food_orders = Order.objects.filter(user=request.user).exclude(status='Pending').order_by('-order_date')
        for fo in food_orders:
            if fo.status == 'Confirmed':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Food Order',
                    'title': f"Food Order #{fo.id} Confirmed",
                    'message': f"Your food order has been confirmed.",
                    'date': fo.order_date
                })
            if fo.serving_status == 'Preparing':
                notifications.append({
                    'type': 'info',
                    'category': 'Food Order',
                    'title': f"Food Order #{fo.id} Preparing",
                    'message': f"Your food order is being prepared.",
                    'date': fo.order_date
                })

        # --- Activity Booking notifications ---
        activity_bookings = ActivityBooking.objects.filter(
            room_booking__customer=customer
        ).order_by('-created_at')
        for ab in activity_bookings:
            if ab.status == 'Booked':
                notifications.append({
                    'type': 'confirmed',
                    'category': 'Activity Booking',
                    'title': f"{ab.activity} Booked",
                    'message': f"Your booking for {ab.activity} has been confirmed.",
                    'date': ab.created_at
                })
    except Customer.DoesNotExist:
        pass

    # Strip any leftover emoji + assign a stable id to every notification
    for n in notifications:
        n['title'] = strip_emoji(n['title'])
        n['id'] = make_notif_id(n['title'], n['date'])

    # Hide notifications the user has already marked as read (stored in session)
    notifications.sort(key=lambda x: x['date'], reverse=True)

    read_ids = request.session.get('read_notification_ids', [])
    notifications = [n for n in notifications if n['id'] not in read_ids]

    return render(request, 'accounts/notifications.html', {
        'notifications': notifications
    })


@login_required
@require_POST
def mark_notification_read(request, notif_id):
    read_ids = request.session.get('read_notification_ids', [])
    if notif_id not in read_ids:
        read_ids.append(notif_id)
    request.session['read_notification_ids'] = read_ids
    request.session.modified = True
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def clear_all_notifications(request):
    notifications = []
    try:
        customer = Customer.objects.get(user=request.user)
 
        room_bookings = RoomBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for rb in room_bookings:
            if rb.status in ['Cancelled', 'Completed']:
                continue
            if rb.payment_status == 'Pending':
                notifications.append({
                    'title': f"Room {rb.room.room_number} Payment Pending",
                    'date': rb.created_at
                })
            elif rb.status in ['Reserved', 'Confirmed'] or rb.payment_status == 'Confirmed':
                notifications.append({
                    'title': f"Room {rb.room.room_number} Confirmed",
                    'date': rb.created_at
                })
            elif rb.status == 'Checked In':
                notifications.append({
                    'title': f"Checked In to Room {rb.room.room_number}",
                    'date': rb.created_at
                })
 
        event_bookings = EventBooking.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for eb in event_bookings:
            if eb.status in ['Cancelled', 'Completed']:
                continue
            if eb.payment_status == 'Pending':
                notifications.append({
                    'title': f"Event '{eb.event_name}' Payment Pending",
                    'date': eb.created_at
                })
            elif eb.status == 'Confirmed' or eb.payment_status == 'Confirmed':
                notifications.append({
                    'title': f"Event '{eb.event_name}' Confirmed",
                    'date': eb.created_at
                })
            elif eb.status == 'Checked In':
                notifications.append({
                    'title': f"Event '{eb.event_name}' In Progress",
                    'date': eb.created_at
                })

        table_reservations = TableReservation.objects.filter(customer=customer).exclude(status='Pending').order_by('-created_at')
        for tb in table_reservations:
            if tb.status in ['Cancelled', 'Completed']:
                continue
            if tb.payment_status == 'Pending':
                notifications.append({
                    'title': f"Table {tb.table.table_number} Payment Pending",
                    'date': tb.created_at
                })
            elif tb.status == 'Confirmed' or tb.payment_status == 'Confirmed':
                notifications.append({
                    'title': f"Table {tb.table.table_number} Reservation Confirmed",
                    'date': tb.created_at
                })

        food_orders = Order.objects.filter(user=request.user).exclude(status='Pending').order_by('-order_date')
        for fo in food_orders:
            if fo.status == 'Confirmed':
                notifications.append({
                    'title': f"Food Order #{fo.id} Confirmed",
                    'date': fo.order_date
                })
            if fo.serving_status == 'Preparing':
                notifications.append({
                    'title': f"Food Order #{fo.id} Preparing",
                    'date': fo.order_date
                })

        activity_bookings = ActivityBooking.objects.filter(
            room_booking__customer=customer
        ).order_by('-created_at')
        for ab in activity_bookings:
            if ab.status == 'Booked':
                notifications.append({
                    'title': f"{ab.activity} Booked",
                    'date': ab.created_at
                })
    except Customer.DoesNotExist:
        pass
 
    read_ids = request.session.get('read_notification_ids', [])
    for n in notifications:
        n['title'] = strip_emoji(n['title'])
        nid = make_notif_id(n['title'], n['date'])
        if nid not in read_ids:
            read_ids.append(nid)
 
    request.session['read_notification_ids'] = read_ids
    request.session.modified = True
 
    return JsonResponse({'status': 'ok'})

def validate_field(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET request required'}, status=405)
    
    field = request.GET.get('field')
    value = request.GET.get('value', '').strip()
    
    if field == 'email':
        query = User.objects.filter(email=value)
        if request.user.is_authenticated:
            query = query.exclude(pk=request.user.pk)
        exists = query.exists()
        return JsonResponse({'exists': exists, 'message': 'Email already exists' if exists else ''})
        
    elif field == 'username':
        query = User.objects.filter(username=value)
        if request.user.is_authenticated:
            query = query.exclude(pk=request.user.pk)
        exists = query.exists()
        return JsonResponse({'exists': exists, 'message': 'Username already taken' if exists else ''})
        
    return JsonResponse({'error': 'Invalid field'}, status=400)