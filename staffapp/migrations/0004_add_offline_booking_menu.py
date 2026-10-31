from django.db import migrations

def seed_offline_booking_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Create Offline Booking Menu
    m, created = Menu.objects.get_or_create(
        name='Offline Booking',
        defaults={'icon': 'fa-calendar-plus-o'}
    )
    
    # Create SubMenus
    SubMenu.objects.get_or_create(
        menu=m,
        name='Room & Activity',
        defaults={'url_name': 'offline_booking'}
    )
    SubMenu.objects.get_or_create(
        menu=m,
        name='Restaurant & Table',
        defaults={'url_name': 'offline_restaurant_table'}
    )
    SubMenu.objects.get_or_create(
        menu=m,
        name='Event & Package',
        defaults={'url_name': 'offline_event_booking'}
    )

def reverse_offline_booking_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Delete submenus and offline booking menu
    SubMenu.objects.filter(url_name__in=[
        'offline_booking',
        'offline_restaurant_table',
        'offline_event_booking'
    ]).delete()
    Menu.objects.filter(name='Offline Booking').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('staffapp', '0003_add_bookings_menu'),
    ]

    operations = [
        migrations.RunPython(seed_offline_booking_menu, reverse_code=reverse_offline_booking_menu),
    ]

