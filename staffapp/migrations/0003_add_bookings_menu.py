from django.db import migrations

def seed_bookings_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Create Bookings Menu
    m = Menu.objects.create(name='Bookings', icon='fa-calendar')
    
    # Create SubMenus
    SubMenu.objects.create(menu=m, name='Room Bookings', url_name='receptionist_room_bookings')
    SubMenu.objects.create(menu=m, name='Hall Bookings', url_name='receptionist_hall_bookings')
    SubMenu.objects.create(menu=m, name='Activity Bookings', url_name='receptionist_activity_bookings')
    SubMenu.objects.create(menu=m, name='Table Reservations', url_name='receptionist_table_reservations')
    SubMenu.objects.create(menu=m, name='Restaurant Orders', url_name='receptionist_restaurant_orders')

def reverse_bookings_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Delete submenus and bookings menu
    SubMenu.objects.filter(url_name__in=[
        'receptionist_room_bookings',
        'receptionist_hall_bookings',
        'receptionist_activity_bookings',
        'receptionist_table_reservations',
        'receptionist_restaurant_orders'
    ]).delete()
    Menu.objects.filter(name='Bookings').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('staffapp', '0002_seed_menus'),
    ]

    operations = [
        migrations.RunPython(seed_bookings_menu, reverse_code=reverse_bookings_menu),
    ]
