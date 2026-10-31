from django.db.models.signals import post_save
from django.dispatch import receiver

from .loyalty import award_points_for_booking
from .models import EventBooking, RoomBooking


@receiver(post_save, sender=RoomBooking)
def award_room_booking_points(sender, instance, **kwargs):
    award_points_for_booking(instance)


@receiver(post_save, sender=EventBooking)
def award_event_booking_points(sender, instance, **kwargs):
    award_points_for_booking(instance)

from .models import TableReservation, Order, FreshUpRoomBooking

@receiver(post_save, sender=RoomBooking)
def send_room_booking_email(sender, instance, created, **kwargs):
    should_send = False
    if created and instance.status in ['Confirmed', 'Reserved']:
        should_send = True
    elif not created and getattr(instance, '_initial_status', None) not in ['Confirmed', 'Reserved'] and instance.status in ['Confirmed', 'Reserved']:
        should_send = True
        
    if should_send:
        instance.send_confirmation_email()
        instance._initial_status = instance.status

@receiver(post_save, sender=EventBooking)
def send_event_booking_email(sender, instance, created, **kwargs):
    should_send = False
    if created and instance.status == 'Confirmed':
        should_send = True
    elif not created and getattr(instance, '_initial_status', None) != 'Confirmed' and instance.status == 'Confirmed':
        should_send = True
        
    if should_send:
        instance.send_confirmation_email()
        instance._initial_status = instance.status

@receiver(post_save, sender=TableReservation)
def send_table_reservation_email(sender, instance, created, **kwargs):
    should_send = False
    if created and instance.status == 'Confirmed':
        should_send = True
    elif not created and getattr(instance, '_initial_status', None) != 'Confirmed' and instance.status == 'Confirmed':
        should_send = True
        
    if should_send:
        instance.send_confirmation_email()
        instance._initial_status = instance.status

@receiver(post_save, sender=Order)
def send_order_email(sender, instance, created, **kwargs):
    should_send = False
    if created and instance.status == 'Confirmed':
        should_send = True
    elif not created and getattr(instance, '_initial_status', None) != 'Confirmed' and instance.status == 'Confirmed':
        should_send = True
        
    if should_send:
        instance.send_confirmation_email()
        instance._initial_status = instance.status

@receiver(post_save, sender=FreshUpRoomBooking)
def send_freshup_email(sender, instance, created, **kwargs):
    should_send = False
    if created and instance.payment_status in ['Paid', 'Confirmed']:
        should_send = True
    elif not created and getattr(instance, '_initial_payment_status', None) not in ['Paid', 'Confirmed'] and instance.payment_status in ['Paid', 'Confirmed']:
        should_send = True
        
    if should_send:
        instance.send_confirmation_email()
        instance._initial_payment_status = instance.payment_status

