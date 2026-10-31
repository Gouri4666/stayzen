from django.db import migrations

def seed_checkin_submenu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    StaffUser = apps.get_model('adminapp', 'StaffUser')
    MenuPermission = apps.get_model('staffapp', 'MenuPermission')
    
    # Try to find and rename main menu
    m = Menu.objects.filter(name='Checkout & Settlement').first()
    if m:
        m.name = 'Check-in & Checkout'
        m.save()
    else:
        m, created = Menu.objects.get_or_create(
            name='Check-in & Checkout',
            defaults={'icon': 'fa-exchange'}
        )
        
    # Create SubMenus
    sub_checkin, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Manage Check-in',
        defaults={'url_name': 'receptionist_checkin'}
    )
    
    sub_checkout = SubMenu.objects.filter(url_name='receptionist_checkout_settlement').first()
    if sub_checkout:
        sub_checkout.menu = m
        sub_checkout.name = 'Manage Checkout'
        sub_checkout.save()
        
    # Grant permissions to all receptionists/managers
    from django.db.models import Q
    staff_receptionists = StaffUser.objects.filter(
        Q(role__name__iexact='receptionist') | Q(role__name__iexact='manager'),
        status=True
    )
    for staff in staff_receptionists:
        user = staff.user
        for sub in [sub_checkin, sub_checkout]:
            if sub:
                MenuPermission.objects.get_or_create(
                    user=user,
                    submenu=sub,
                    defaults={'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True}
                )

def reverse_checkin_submenu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    SubMenu.objects.filter(url_name='receptionist_checkin').delete()
    m = Menu.objects.filter(name='Check-in & Checkout').first()
    if m:
        m.name = 'Checkout & Settlement'
        m.save()

class Migration(migrations.Migration):

    dependencies = [
        ('staffapp', '0007_add_checkout_settlement_menu'),
    ]

    operations = [
        migrations.RunPython(seed_checkin_submenu, reverse_code=reverse_checkin_submenu),
    ]
