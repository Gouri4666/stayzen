from django.db import migrations

def seed_checkout_settlement_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Create Checkout & Settlement Menu
    m, created = Menu.objects.get_or_create(
        name='Checkout & Settlement',
        defaults={'icon': 'fa-credit-card'}
    )
    
    # Create SubMenu
    SubMenu.objects.get_or_create(
        menu=m,
        name='Manage Checkout',
        defaults={'url_name': 'receptionist_checkout_settlement'}
    )

def reverse_checkout_settlement_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    # Delete SubMenu and Menu
    SubMenu.objects.filter(url_name='receptionist_checkout_settlement').delete()
    Menu.objects.filter(name='Checkout & Settlement').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('staffapp', '0006_alter_attendance_status'),
    ]

    operations = [
        migrations.RunPython(seed_checkout_settlement_menu, reverse_code=reverse_checkout_settlement_menu),
    ]
