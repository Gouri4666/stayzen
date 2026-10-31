import re
from django.shortcuts import render, redirect, get_object_or_404
from adminapp.models import Room
from adminapp.models import Activity,event_hall,Package
from accountapp.models import Customer
# from .models import Feedback
# Create your views here.


from adminapp.models import SiteSettings  # Add this import at the top!

def home(request):
    from .models import ContactMessage
    
    # 1. Fetch the dynamic settings from the database
    site_settings = SiteSettings.load()
    
    # 2. Your existing feedback logic
    feedbacks = ContactMessage.objects.filter(
        inquiry_type='feedback'
    ).exclude(rating__isnull=True).order_by('-rating', '-created_at')[:3]
    
    # 3. Add BOTH feedbacks and settings to the context
    context = {
        'feedbacks': feedbacks,
        'settings': site_settings,  # This is the magic word your HTML is looking for
    }
    
    return render(request, 'guest/index.html', context)



# def contact(request):
#     return render(request, 'guest/contact.html')


def services(request):
    return render(request, 'guest/services.html')

def gallery(request):
    return render(request, 'guest/gallery.html')

def rooms(request):
    from bookingapp.models import RoomBooking
    from django.utils.dateparse import parse_date

    rooms_list = Room.objects.all()

    # --- UPDATED FILTER PARAMETERS (check-in/out + guest counts only) ---
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    adults_str = request.GET.get('adults', '').strip()
    children_str = request.GET.get('children', '').strip()

    adults_val = 0
    children_val = 0
    try:
        adults_val = int(adults_str) if adults_str else 0
    except ValueError:
        pass
    try:
        children_val = int(children_str) if children_str else 0
    except ValueError:
        pass

    total_guests = adults_val + children_val

    # --- DATE-BASED AVAILABILITY FILTER (same overlap logic as api_available_rooms) ---
    if check_in_str and check_out_str:
        check_in = parse_date(check_in_str)
        check_out = parse_date(check_out_str)
        if check_in and check_out and check_in <= check_out:
            overlapping_ids = RoomBooking.objects.filter(
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(status__in=['Cancelled', 'Completed']).exclude(payment_status='Pending').values_list('room_id', flat=True)
            rooms_list = rooms_list.exclude(id__in=overlapping_ids)

    # --- CAPACITY FILTERS ---
    if adults_val > 0:
        rooms_list = rooms_list.filter(max_adults__gte=adults_val)
    if children_val > 0:
        rooms_list = rooms_list.filter(max_children__gte=children_val)

    booking_success = False
    if request.method == 'POST':
        booking_success = True

    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            pass

    return render(request, 'guest/rooms.html', {
        'rooms': rooms_list,
        'booking_success': booking_success,
        'filter_check_in': check_in_str,
        'filter_check_out': check_out_str,
        'filter_adults': adults_str,
        'filter_children': children_str,
        'filter_total_guests': total_guests,
        'customer': customer,
    })


def room_detail(request, room_id):
    """Dedicated Room Detail page with image gallery, amenities and inline booking form."""
    from bookingapp.models import RoomBooking
    from django.utils.dateparse import parse_date

    room = get_object_or_404(Room, id=room_id)

    # Preserve filter context passed from the search page
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    adults_str = request.GET.get('adults', '').strip()
    children_str = request.GET.get('children', '').strip()

    # Determine date-specific availability
    is_available = room.status not in ['Not Available', 'Maintenance']

    if is_available and check_in_str and check_out_str:
        check_in = parse_date(check_in_str)
        check_out = parse_date(check_out_str)
        if check_in and check_out and check_in <= check_out:
            overlap = RoomBooking.objects.filter(
                room=room,
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(status__in=['Cancelled', 'Completed']).exclude(payment_status='Pending').exists()
            if overlap:
                is_available = False

    # Loyalty points for registered users
    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Exception:
            pass

    # Parse description by newlines to show bullet points on detail page
    description_points = [line.strip() for line in room.description.split('\n') if line.strip()]

    return render(request, 'guest/room_detail.html', {
        'room': room,
        'description_points': description_points,
        'is_available': is_available,
        'filter_check_in': check_in_str,
        'filter_check_out': check_out_str,
        'filter_adults': adults_str,
        'filter_children': children_str,
        'customer': customer,
    })


def event(request):
    from bookingapp.models import EventBooking
    from django.utils.dateparse import parse_date

    halls = event_hall.objects.all()

    # --- FILTER PARAMETERS (matching Rooms) ---
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    guest_count_str = request.GET.get('guest_count', '').strip()

    guest_count_val = 0
    try:
        guest_count_val = int(guest_count_str) if guest_count_str else 0
    except ValueError:
        pass

    # --- DATE-BASED AVAILABILITY FILTER (overlap checking) ---
    if check_in_str and check_out_str:
        check_in = parse_date(check_in_str)
        check_out = parse_date(check_out_str)
        if check_in and check_out and check_in <= check_out:
            overlapping_ids = EventBooking.objects.filter(
                start_date__lte=check_out,
                end_date__gte=check_in
            ).exclude(status='Cancelled').exclude(payment_status='Pending').values_list('hall_id', flat=True)
            halls = halls.exclude(hall_id__in=overlapping_ids).exclude(hall_status='maintenance')

    # --- CAPACITY FILTER ---
    if guest_count_val > 0:
        halls = halls.filter(hall_capacity__gte=guest_count_val)

    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            customer = None

    packages = Package.objects.all()
    for p in packages:
        p.services_price = sum(s.service_price for s in p.services.all())

    return render(request, 'guest/event.html', {
        'halls': halls,
        'packages': packages,
        'customer': customer,
        'filter_check_in': check_in_str,
        'filter_check_out': check_out_str,
        'filter_guest_count': guest_count_str,
    })

def activity(request):
    has_reservation = False
    if request.user.is_authenticated:
        from accountapp.models import Customer
        from bookingapp.models import RoomBooking
        customer = Customer.objects.filter(user=request.user).first()
        if customer:
            has_reservation = RoomBooking.objects.filter(
                customer=customer,
                status__in=["Confirmed", "Reserved", "Checked In"]
            ).exists()
        if not has_reservation and request.user.email:
            has_reservation = RoomBooking.objects.filter(
                guest_email=request.user.email,
                status__in=["Confirmed", "Reserved", "Checked In"]
            ).exists()

    activities = Activity.objects.filter(status='Available')

    search = request.GET.get('search')
    category = request.GET.get('category')
    price = request.GET.get('price')

    if search:
        activities = activities.filter(activity_name__icontains=search)

    if category:
        activities = activities.filter(activity_type=category)

    if price == "low":
        activities = activities.filter(price__lt=500)

    elif price == "mid":
        activities = activities.filter(price__gte=500, price__lte=1500)

    elif price == "high":
        activities = activities.filter(price__gt=1500)

    booking_success = request.GET.get("booking") == "success"

    return render(request, "guest/activities.html", {
        "activities": activities,
        "booking_success": booking_success,
        "has_reservation": has_reservation
    })

def activity_detail(request, id):
    has_reservation = False
    if request.user.is_authenticated:
        from accountapp.models import Customer
        from bookingapp.models import RoomBooking
        customer = Customer.objects.filter(user=request.user).first()
        if customer:
            has_reservation = RoomBooking.objects.filter(
                customer=customer,
                status__in=["Confirmed", "Reserved", "Checked In"]
            ).exists()
        if not has_reservation and request.user.email:
            has_reservation = RoomBooking.objects.filter(
                guest_email=request.user.email,
                status__in=["Confirmed", "Reserved", "Checked In"]
            ).exists()

    activity = get_object_or_404(Activity, id=id, status='Available')
    sessions = activity.sessions.all()   # VERY IMPORTANT

    return render(request, 'guest/activity_detail.html', {
        'activity': activity,
        'sessions': sessions,
        'has_reservation': has_reservation
    })

#food-menu
from adminapp.models import FoodItem


#hall_packages and services
from adminapp.models import event_hall, Package

def hall_packages(request, hall_id):
    from bookingapp.models import EventBooking
    from django.utils.dateparse import parse_date

    hall = get_object_or_404(event_hall, hall_id=hall_id)
    packages = Package.objects.filter(hall=hall)

    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    guest_count_str = request.GET.get('guest_count', '').strip()

    is_available = True
    if check_in_str and check_out_str:
        check_in = parse_date(check_in_str)
        check_out = parse_date(check_out_str)
        if check_in and check_out and check_in <= check_out:
            overlap = EventBooking.objects.filter(
                hall=hall,
                start_date__lte=check_out,
                end_date__gte=check_in
            ).exclude(status='Cancelled').exclude(payment_status='Pending').exists()
            if overlap or hall.hall_status == 'maintenance':
                is_available = False

    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            customer = None

    context = {
        'hall': hall,
        'packages': packages,
        'customer': customer,
        'is_available': is_available,
        'filter_check_in': check_in_str,
        'filter_check_out': check_out_str,
        'filter_guest_count': guest_count_str,
    }

    return render(
        request,
        'guest/package.html',
        context
    )


# def food_menu(request):

#     food_items = FoodItem.objects.filter(status='Available')

#     category = request.GET.get('category')
#     cuisine = request.GET.get('cuisine')
#     dietary = request.GET.get('dietary')
#     max_price = request.GET.get('price')

#     if category:
#         food_items = food_items.filter(category=category)

#     if cuisine:
#         food_items = food_items.filter(cuisine=cuisine)

#     if dietary:
#         food_items = food_items.filter(dietary_status=dietary)

#     if max_price:
#         food_items = food_items.filter(price__lte=max_price)

#     cart = request.session.get('cart', {})

#     return render(request, 'guest/restaurant.html', {
#         'food_items': food_items,

#         'selected_category': category,
#         'selected_cuisine': cuisine,
#         'selected_dietary': dietary,
#         'selected_price': max_price,

#         'categories': FoodItem.CATEGORY_CHOICES,
#         'cuisines': FoodItem.CUISINE_CHOICES,
#         'dietary_choices': FoodItem.DIETARY_CHOICES,

#         'cart': cart,
#     })

from django.shortcuts import render
from django.db.models import Case, When, IntegerField
from adminapp.models import FoodItem

def food_menu(request):
    # 1. Start with available food items
    food_items = FoodItem.objects.filter(status='Available')

    # 2. Extract filter parameters from the URL
    category = request.GET.get('category')
    cuisine = request.GET.get('cuisine')
    dietary = request.GET.get('dietary')
    max_price = request.GET.get('price')

    # 3. Apply active filters dynamically
    if category:
        food_items = food_items.filter(category=category)

    if cuisine:
        food_items = food_items.filter(cuisine=cuisine)

    if dietary:
        food_items = food_items.filter(dietary_status=dietary)

    if max_price:
        try:
            food_items = food_items.filter(price__lte=float(max_price))
        except ValueError:
            pass  # Handles edge cases where invalid input is typed into the price box

    # 4. Apply the custom display sorting logic using database conditional statements
    food_items = food_items.order_by(
        Case(
            When(category='Starter', then=1),
            When(category='Main Course', then=2),
            When(category='Dessert', then=3),
            When(category='Alcohol', then=4),
            default=5,  # Fallback rule for any other categories (e.g., Beverages)
            output_field=IntegerField(),
        )
    )

    # 5. Fetch current session cart contents
    cart = request.session.get('cart', {})

    # 6. Render page context definitions
    return render(request, 'guest/restaurant.html', {
        'food_items': food_items,

        'selected_category': category,
        'selected_cuisine': cuisine,
        'selected_dietary': dietary,
        'selected_price': max_price,

        'categories': FoodItem.CATEGORY_CHOICES,
        'cuisines': FoodItem.CUISINE_CHOICES,
        'dietary_choices': FoodItem.DIETARY_CHOICES,

        'cart': cart,
    })


def add_to_cart(request, food_id):

    food = get_object_or_404(FoodItem, id=food_id)

    cart = request.session.get('cart', {})

    key = str(food_id)

    if key not in cart:

        if food.quantity > 0:
            cart[key] = 1

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('view_cart')   # redirect to cart page

def order_now(request, food_id):

    food = get_object_or_404(FoodItem, id=food_id)

    cart = request.session.get('cart', {})

    key = str(food_id)

    if key not in cart and food.quantity > 0:
        cart[key] = 1

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('view_cart')

def increase_cart(request, food_id):

    food = get_object_or_404(FoodItem, id=food_id)

    cart = request.session.get('cart', {})

    key = str(food_id)

    current_qty = cart.get(key, 0)

    if current_qty < food.quantity:
        cart[key] = current_qty + 1

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('view_cart')

def decrease_cart(request, food_id):

    cart = request.session.get('cart', {})

    key = str(food_id)

    if key in cart:

        cart[key] -= 1

        if cart[key] <= 0:
            del cart[key]

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('view_cart')
from decimal import Decimal


def remove_from_cart(request, food_id):

    cart = request.session.get('cart', {})

    key = str(food_id)

    if key in cart:
        del cart[key]

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('view_cart')
from django.http import JsonResponse

def cart_update(request, food_id, action):

    cart = request.session.get('cart', {})

    key = str(food_id)

    if action == 'increase':
        cart[key] = cart.get(key, 0) + 1

    elif action == 'decrease':
        if key in cart:
            cart[key] -= 1

            if cart[key] <= 0:
                del cart[key]

    request.session['cart'] = cart

    return JsonResponse({
        'success': True
    })
from decimal import Decimal

def view_cart(request):

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

    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            pass

    return render(
        request,
        'guest/cart.html',
        {
            'cart_items': cart_items,
            'total': total,
            'gst': gst,
            'delivery_fee': delivery_fee,
            'grand_total': grand_total,
            'customer': customer,
        }
    )

from django.contrib import messages

from adminapp.models import RestaurantTable
from bookingapp.models import TableReservation
from bookingapp.utils import is_table_available
from accountapp.models import Customer

def table_list_guest(request):

    tables = RestaurantTable.objects.all()

    customer = None
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user=request.user)
        except:
            customer = None

    table_type = request.GET.get("table_type")
    capacity = request.GET.get("capacity")
    filter_date = request.GET.get("date")
    filter_time = request.GET.get("time")
    filter_end_time = request.GET.get("end_time")

    if table_type:
        tables = tables.filter(location=table_type)

    if capacity:
        tables = tables.filter(table_capacity__gte=capacity)

    if filter_date and filter_time and filter_end_time:
        from bookingapp.utils import calculate_duration_hours
        duration_hours = calculate_duration_hours(filter_time, filter_end_time)

        available_ids = [
            t.id for t in tables
            if is_table_available(t, filter_date, filter_time, duration_hours)
        ]
        tables = tables.filter(id__in=available_ids)

    if request.method == "POST":

        table_id = request.POST.get("table_id")
        date = request.POST.get("reservation_date")
        time = request.POST.get("reservation_time")
        end_time = request.POST.get("end_time")
        guests = request.POST.get("guests")

        table = get_object_or_404(RestaurantTable, id=table_id)

        # FIXED AUTO-FILL
        if request.user.is_authenticated:
            customer_name = request.user.username
            phone = getattr(getattr(request.user, "customer", None), "phone", "")
            email = request.user.email
        else:
            customer_name = request.POST.get("customer_name")
            phone = request.POST.get("phone")
            email = request.POST.get("email")

        # Validation
        if email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Enter a valid email address.")
                return redirect("table_list_guest")

        if phone:
            import re
            if not re.match(r'^\+?1?\d{9,15}$', phone):
                messages.error(request, "Enter a valid phone number (9-15 digits)")
                return redirect("table_list_guest")

        # NEW: Guests validation against table capacity
        try:
            guests_int = int(guests)
        except (TypeError, ValueError):
            messages.error(request, "Enter a valid number of guests.")
            return redirect("table_list_guest")

        if guests_int < 1:
            messages.error(request, "Number of guests must be at least 1.")
            return redirect("table_list_guest")

        if guests_int > table.table_capacity:
            messages.error(
                request,
                f"This table allows a maximum of {table.table_capacity} guests."
            )
            return redirect("table_list_guest")

        duration_hours = 2
        if time and end_time:
            from datetime import datetime
            try:
                try:
                    start_t = datetime.strptime(time, "%H:%M").time()
                except ValueError:
                    start_t = datetime.strptime(time, "%H:%M:%S").time()
                try:
                    end_t = datetime.strptime(end_time, "%H:%M").time()
                except ValueError:
                    end_t = datetime.strptime(end_time, "%H:%M:%S").time()

                if end_t <= start_t:
                    messages.error(request, "End time must be after start time.")
                    return redirect("table_list_guest")
            except Exception:
                pass

            from bookingapp.utils import calculate_duration_hours
            duration_hours = calculate_duration_hours(time, end_time)

        if not is_table_available(table, date, time, duration_hours):
            messages.error(request, "This table is already booked for selected time.")
            return redirect("table_list_guest")

        from decimal import Decimal
        total_price = table.price * Decimal(str(duration_hours))

        reservation = TableReservation.objects.create(
            table=table,
            customer_name=customer_name,
            phone=phone,
            email=email,
            reservation_date=date,
            reservation_time=time,
            duration_hours=duration_hours,
            guests=guests_int,
            status="Pending",
            payment_status="Pending",
            advance_amount=total_price,
            booking_source="Online"
        )

        from django.conf import settings
        context = {
            'booking_id': reservation.id,
            'booking_type': 'table',
            'amount': float(reservation.advance_amount),
            'name': reservation.customer_name,
            'email': request.user.email if request.user.is_authenticated else '',
            'phone': reservation.phone,
            'razorpay_key': getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_wxea3fAMOes5IK'),
        }
        return render(request, "guest/razorpay_payment.html", context)

    return render(request, "guest/table.html", {
        "tables": tables,
        "customer": customer
    })

from bookingapp.models import TableReservation
from adminapp.models import RestaurantTable

def reserve_table(request, table_id):

    table = get_object_or_404(
        RestaurantTable,
        id=table_id
    )

    if request.method == "POST":
        phone = request.POST.get('phone')
        if phone:
            if not re.match(r'^\+?1?\d{9,15}$', phone):
                messages.error(request, "Enter a valid phone number (9-15 digits)")
                return render(request, 'guest/reserve_table.html', {'table': table})

        email = request.POST.get('email')
        if email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Enter a valid email address.")
                return render(request, 'guest/reserve_table.html', {'table': table})

        # -------------------------
        # VALIDATION: TIME ALREADY PASSED
        # -------------------------
        res_date = request.POST.get('date')
        res_time = request.POST.get('time')
        if res_date and res_time:
            from django.utils import timezone as _tz
            from datetime import datetime as _dt
            current_local_date = _tz.localdate()
            current_local_time = _tz.localtime().time()
            try:
                parsed_res_date = _dt.strptime(res_date, "%Y-%m-%d").date()
                try:
                    booking_time = _dt.strptime(res_time, "%H:%M").time()
                except ValueError:
                    booking_time = _dt.strptime(res_time, "%H:%M:%S").time()
                if parsed_res_date == current_local_date and booking_time <= current_local_time:
                    messages.error(request, "Cannot book a slot for a time that has already started or passed.")
                    return render(request, 'guest/reserve_table.html', {'table': table})
            except (ValueError, TypeError):
                pass

        TableReservation.objects.create(
            table=table,
            customer_name=request.POST.get('name'),
            phone=phone,
            email=email,
            reservation_date=res_date,
            reservation_time=res_time,
            guests=request.POST.get('guests')
        )

        return redirect('table_list_guest')

    return render(
        request,
        'guest/reserve_table.html',
        {
            'table': table
        }
    )

def category_detail(request, category_name):
    # Get all available items for the selected category
    food_items = FoodItem.objects.filter(status='Available', category=category_name)

    # Filter parameters
    search_query = request.GET.get('search')
    cuisine = request.GET.get('cuisine')
    dietary = request.GET.get('dietary')
    max_price = request.GET.get('price')

    # Apply filters if they exist
    if search_query:
        food_items = food_items.filter(item_name__icontains=search_query)
    if cuisine:
        food_items = food_items.filter(cuisine=cuisine)
    if dietary:
        food_items = food_items.filter(dietary_status=dietary)
    if max_price:
        food_items = food_items.filter(price__lte=max_price)

    cart = request.session.get('cart', {})

    return render(request, 'guest/category_detail.html', {
        'category_name': category_name,
        'food_items': food_items,
        
        # Pass back selected filters
        'selected_search': search_query,
        'selected_cuisine': cuisine,
        'selected_dietary': dietary,
        'selected_price': max_price,

        # Choices for dropdowns
        'cuisines': FoodItem.CUISINE_CHOICES,
        'dietary_choices': FoodItem.DIETARY_CHOICES,
        
        'cart': cart,
    })


#FEEDBACK
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactMessage  # Correct import
from .forms import ContactMessageForm


def about(request):
    from adminapp.models import SiteSettings
    # Ensure this matches the 'value' in INQUIRY_CHOICES
    # Choices: ('feedback', 'Leave Feedback / Rating')
    feedbacks = ContactMessage.objects.filter(
        inquiry_type='feedback'
    ).exclude(rating__isnull=True).order_by('-created_at') # Only get feedback with ratings
    
    return render(request, 'guest/about.html', {
        'feedbacks': feedbacks,
        'settings': SiteSettings.load()
    })

def contact(request):
    from adminapp.models import SiteSettings
    feedbacks = ContactMessage.objects.filter(
        inquiry_type='feedback'
    ).exclude(rating__isnull=True).order_by('-created_at')

    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you! Your message has been submitted successfully.")
            return redirect('contact')
    else:
        form = ContactMessageForm()
    return render(request, 'guest/contact.html', {
        'form': form, 
        'feedbacks': feedbacks,
        'settings': SiteSettings.load()
    })


def track_food_order(request, long_order_id):
    from bookingapp.models import Order
    order = get_object_or_404(Order, long_order_id=long_order_id)
    items = order.items.all()
    guest_name = order.customer_name or (order.user.get_full_name() if order.user else 'Guest')
    
    return render(request, 'guest/track_food_order.html', {
        'order': order,
        'items': items,
        'guest_name': guest_name,
        'settings': SiteSettings.load()
    })

def track_booking(request, tracking_token):
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
    from adminapp.models import SiteSettings
    
    order = Order.objects.filter(long_order_id=tracking_token).first()
    if order:
        return redirect('track_food_order', long_order_id=tracking_token)
        
    room_booking = RoomBooking.objects.filter(long_order_id=tracking_token).first()
    if room_booking:
        return render(request, 'guest/track_booking.html', {'booking': room_booking, 'type': 'Room', 'settings': SiteSettings.load()})
        
    event_booking = EventBooking.objects.filter(long_order_id=tracking_token).first()
    if event_booking:
        return render(request, 'guest/track_booking.html', {'booking': event_booking, 'type': 'Event', 'settings': SiteSettings.load()})
        
    table_reservation = TableReservation.objects.filter(long_order_id=tracking_token).first()
    if table_reservation:
        return render(request, 'guest/track_booking.html', {'booking': table_reservation, 'type': 'Table', 'settings': SiteSettings.load()})
        
    messages.error(request, "Invalid or expired tracking link.")
    return redirect('home')

def cancel_booking(request, tracking_token):
    from bookingapp.models import RoomBooking, EventBooking, TableReservation, Order
    from django.utils import timezone
    from adminapp.models import SiteSettings
    from datetime import date
    
    booking = None
    booking_type = None
    
    order = Order.objects.filter(long_order_id=tracking_token).first()
    if order:
        # Check if food order is cancellable: must be Pending/Confirmed and not yet Prepared
        if order.status not in ['Pending', 'Confirmed', 'Preparing']:
            messages.error(request, f"Order {order.long_order_id} cannot be cancelled in its current state.")
            return redirect('track_food_order', long_order_id=tracking_token)
        
        booking = order
        booking_type = 'Order'
    
    if not booking:
        booking = RoomBooking.objects.filter(long_order_id=tracking_token).first()
        if booking: booking_type = 'Room'
        
    if not booking:
        booking = EventBooking.objects.filter(long_order_id=tracking_token).first()
        if booking: booking_type = 'Event'
        
    if not booking:
        booking = TableReservation.objects.filter(long_order_id=tracking_token).first()
        if booking: booking_type = 'Table'
        
    if not booking:
        messages.error(request, "Invalid or expired cancellation link.")
        return redirect('home')
        
    if booking.status == 'Cancelled':
        messages.info(request, "This booking is already cancelled.")
        return redirect('track_booking', tracking_token=tracking_token)
        
    can_cancel = False
    if booking_type == 'Room':
        if booking.status in ['Pending', 'Reserved', 'Confirmed']:
            can_cancel = True
    elif booking_type == 'Event':
        if booking.status in ['Pending', 'Confirmed'] and booking.start_date and booking.start_date > date.today():
            can_cancel = True
    elif booking_type == 'Table':
        if booking.status in ['Pending', 'Confirmed']:
            can_cancel = True
    elif booking_type == 'Order':
        # Allow cancellation if it's still in initial stages
        if booking.status in ['Pending', 'Confirmed', 'Preparing']:
            can_cancel = True
            
    if not can_cancel:
        messages.error(request, "This booking cannot be cancelled at this stage.")
        return redirect('track_booking', tracking_token=tracking_token)
        
    if request.method == 'POST':
        reason = request.POST.get('reason')
        if reason:
            booking.cancellation_reason = reason
            booking.status = 'Cancelled'
            booking.cancelled_by = 'Guest'
            booking.cancelled_at = timezone.now()
            
            if booking_type == 'Event' and booking.hall:
                booking.hall.hall_status = 'available'
                booking.hall.save()
            elif booking_type == 'Table' and booking.table:
                booking.table.status = 'Available'
                booking.table.save()
                
            booking.save()
            messages.success(request, "Your booking has been cancelled successfully.")
            return redirect('track_booking', tracking_token=tracking_token)
            
    return render(request, 'guest/cancel_booking.html', {
        'booking': booking,
        'type': booking_type,
        'settings': SiteSettings.load()
    })

from django.contrib.auth.decorators import login_required
@login_required
def feedback_view(request):
    from .forms import ContactMessageForm
    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.is_registered = True
            feedback.save()
            messages.success(request, 'Thank you! Your feedback has been submitted successfully.')
            return redirect('feedback')
    else:
        form = ContactMessageForm()
    return render(request, 'accounts/feedback.html', {'form': form})

from django.http import JsonResponse
from accountapp.models import Customer

from django.views.decorators.cache import never_cache

@never_cache
def api_check_phone(request):
    phone = request.GET.get('phone', '').strip()
    if not phone:
        return JsonResponse({'exists': False})
    exists = Customer.objects.filter(phone=phone).exists()
    return JsonResponse({'exists': exists})
