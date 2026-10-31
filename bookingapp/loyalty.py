# from decimal import Decimal
# from .models import LoyaltyTransaction

# def normalize_redeem_points(customer, requested_points, booking_amount):
#     if requested_points <= 0:
#         return 0
#     points = min(requested_points, customer.loyalty_points, int(booking_amount))
#     return max(points, 0)

# def redeem_points_for_booking(customer, booking, points, amount):
#     customer.loyalty_points -= points
#     customer.save(update_fields=['loyalty_points', 'membership_status'])
#     ref = f"Redemption for Booking #{booking.id}"
#     LoyaltyTransaction.objects.create(
#         customer=customer,
#         booking_reference=ref,
#         transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED,
#         points=points,
#         amount=amount
#     )

# def award_points_for_booking(booking):
#     if not booking.customer:
#         return
#     # Do not award loyalty points for online guest-side payments
#     if getattr(booking, 'booking_source', '') == 'Online' and not booking.customer:
#         return
#     if booking.payment_status == 'Confirmed' and booking.points_earned == 0:
#         # Calculate points to award: 1 point for every 100 Rs paid
#         points = int(booking.final_amount // 100)
#         if points > 0:
#             # Update booking to mark points as earned (prevent double earning)
#             booking.points_earned = points
#             booking.__class__.objects.filter(pk=booking.pk).update(points_earned=points)
            
#             # Add points to customer
#             customer = booking.customer
#             customer.loyalty_points += points
#             customer.lifetime_points_earned += points
#             customer.save(update_fields=['loyalty_points', 'lifetime_points_earned', 'membership_status'])
            
#             # Create transaction log
#             ref = f"Earned from Booking #{booking.id}"
#             LoyaltyTransaction.objects.create(
#                 customer=customer,
#                 booking_reference=ref,
#                 transaction_type=LoyaltyTransaction.TRANSACTION_EARNED,
#                 points=points,
#                 amount=booking.final_amount
#             )
#     elif (booking.payment_status in ['Pending', 'Failed'] or booking.status == 'Cancelled') and booking.points_earned > 0:
#         points = booking.points_earned
        
#         # Update booking to mark points as 0 (prevent double deduction)
#         booking.points_earned = 0
#         booking.__class__.objects.filter(pk=booking.pk).update(points_earned=0)
        
#         # Deduct points from customer
#         customer = booking.customer
#         customer.loyalty_points = max(0, customer.loyalty_points - points)
#         customer.lifetime_points_earned = max(0, customer.lifetime_points_earned - points)
#         customer.save(update_fields=['loyalty_points', 'lifetime_points_earned', 'membership_status'])
        
#         # Create transaction log
#         ref = f"Reversed from Booking #{booking.id}"
#         LoyaltyTransaction.objects.create(
#             customer=customer,
#             booking_reference=ref,
#             transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED,
#             points=points,
#             amount=booking.final_amount
#         )



from decimal import Decimal
from .models import LoyaltyTransaction

MEMBERSHIP_DISCOUNT_RATES = {
    'Silver': Decimal('0.05'),
    'Gold': Decimal('0.10'),
    'Platinum': Decimal('0.15'),
}

def get_membership_discount_rate(customer):
    if not customer:
        return Decimal('0.00')
    return MEMBERSHIP_DISCOUNT_RATES.get(customer.membership_status, Decimal('0.00'))

def calculate_membership_discount(customer, amount):
    amount = Decimal(amount)
    return (amount * get_membership_discount_rate(customer)).quantize(Decimal('0.01'))

def normalize_redeem_points(customer, requested_points, booking_amount):
    if not customer or requested_points <= 0:
        return 0
    amount = max(Decimal('0.00'), Decimal(booking_amount))
    points = min(requested_points, customer.loyalty_points, int(amount))
    return max(points, 0)

def redeem_points_for_booking(customer, booking, points, amount):
    if not customer or points <= 0:
        return
    existing_redemption = LoyaltyTransaction.objects.filter(
        customer=customer,
        booking_reference=f"Redemption for Booking #{booking.id}",
        transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED
    ).exists()
    if existing_redemption:
        return
    if points > customer.loyalty_points:
        raise ValueError("Redeemed points cannot exceed your available points.")
    points = min(points, int(max(Decimal('0.00'), Decimal(amount))))
    if points <= 0:
        booking.__class__.objects.filter(pk=booking.pk).update(points_redeemed=0)
        return
    customer.loyalty_points -= points
    customer.save(update_fields=['loyalty_points', 'membership_status'])
    if booking.points_redeemed != points:
        booking.__class__.objects.filter(pk=booking.pk).update(points_redeemed=points)
    ref = f"Redemption for Booking #{booking.id}"
    LoyaltyTransaction.objects.create(
        customer=customer,
        booking_reference=ref,
        transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED,
        points=points,
        amount=amount
    )

def award_points_for_booking(booking):
    if not booking.customer:
        return
    if booking.payment_status in ['Confirmed', 'Fully Paid'] and booking.points_earned == 0:
        # Calculate points to award: 1 point for every 100 Rs paid
        points = int(booking.final_amount // 100)
        if points > 0:
            # Update booking to mark points as earned (prevent double earning)
            booking.points_earned = points
            booking.__class__.objects.filter(pk=booking.pk).update(points_earned=points)
            
            # Add points to customer
            customer = booking.customer
            customer.loyalty_points += points
            customer.lifetime_points_earned += points
            customer.save(update_fields=['loyalty_points', 'lifetime_points_earned', 'membership_status'])
            
            # Create transaction log
            ref = f"Earned from Booking #{booking.id}"
            LoyaltyTransaction.objects.create(
                customer=customer,
                booking_reference=ref,
                transaction_type=LoyaltyTransaction.TRANSACTION_EARNED,
                points=points,
                amount=booking.final_amount
            )
    elif (booking.payment_status in ['Pending', 'Failed'] or booking.status == 'Cancelled') and booking.points_earned > 0:
        points = booking.points_earned
        
        # Update booking to mark points as 0 (prevent double deduction)
        booking.points_earned = 0
        booking.__class__.objects.filter(pk=booking.pk).update(points_earned=0)
        
        # Deduct points from customer
        customer = booking.customer
        customer.loyalty_points = max(0, customer.loyalty_points - points)
        customer.lifetime_points_earned = max(0, customer.lifetime_points_earned - points)
        customer.save(update_fields=['loyalty_points', 'lifetime_points_earned', 'membership_status'])
        
        # Create transaction log
        ref = f"Reversed from Booking #{booking.id}"
        LoyaltyTransaction.objects.create(
            customer=customer,
            booking_reference=ref,
            transaction_type=LoyaltyTransaction.TRANSACTION_REDEEMED,
            points=points,
            amount=booking.final_amount
        )



