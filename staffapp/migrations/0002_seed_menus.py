from django.db import migrations

def seed_menus(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Clear existing to avoid duplicates
    SubMenu.objects.all().delete()
    Menu.objects.all().delete()

    # Rooms Menu
    m1 = Menu.objects.create(name='Rooms', icon='fa-bed')
    SubMenu.objects.create(menu=m1, name='All Rooms', url_name='room_list')
    SubMenu.objects.create(menu=m1, name='Add Room', url_name='add_room')

    # Event Halls Menu
    m2 = Menu.objects.create(name='Event Halls', icon='fa-building')
    SubMenu.objects.create(menu=m2, name='All Event Halls', url_name='hall_list')
    SubMenu.objects.create(menu=m2, name='Add Event Hall', url_name='add_event_hall')

    # Packages & Services Menu
    m3 = Menu.objects.create(name='Packages & Services', icon='fa-gift')
    SubMenu.objects.create(menu=m3, name='Add Package', url_name='add_package')
    SubMenu.objects.create(menu=m3, name='View Packages', url_name='package_list')

    # Food & Beverage Menu (with Table Management as submenus to match original flow)
    m4 = Menu.objects.create(name='Food & Beverage', icon='fa-cutlery')
    SubMenu.objects.create(menu=m4, name='All Items', url_name='food_item_list')
    SubMenu.objects.create(menu=m4, name='Add Item', url_name='add_food_item')
    SubMenu.objects.create(menu=m4, name='All Tables', url_name='table_list')
    SubMenu.objects.create(menu=m4, name='Add Table', url_name='add_table')

    # Activities Menu
    m5 = Menu.objects.create(name='Activities', icon='fa-heartbeat')
    SubMenu.objects.create(menu=m5, name='Add Activity', url_name='add_activity')
    SubMenu.objects.create(menu=m5, name='View Activities', url_name='activity_list')

    # Loyalty Rewards Menu
    m6 = Menu.objects.create(name='Loyalty Rewards', icon='fa-star')
    SubMenu.objects.create(menu=m6, name='Loyalty Customers', url_name='loyalty_customer_list')
    SubMenu.objects.create(menu=m6, name='Loyalty Transactions', url_name='loyalty_transaction_list')

def reverse_seed_menus(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    SubMenu.objects.all().delete()
    Menu.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('staffapp', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_menus, reverse_code=reverse_seed_menus),
    ]
