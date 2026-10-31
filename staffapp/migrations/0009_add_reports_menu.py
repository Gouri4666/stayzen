from django.db import migrations

def seed_reports_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    StaffUser = apps.get_model('adminapp', 'StaffUser')
    MenuPermission = apps.get_model('staffapp', 'MenuPermission')
    
    # Create main menu
    m, created = Menu.objects.get_or_create(
        name='Reports',
        defaults={'icon': 'fa-bar-chart'}
    )
        
    # Create SubMenus
    sub_overall, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Reports Dashboard',
        defaults={'url_name': 'reports_overall'}
    )
    sub_rooms, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Rooms Report',
        defaults={'url_name': 'reports_rooms'}
    )
    sub_events, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Events Report',
        defaults={'url_name': 'reports_events'}
    )
    sub_tables, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Tables Report',
        defaults={'url_name': 'reports_tables'}
    )
    sub_payments, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Payments Report',
        defaults={'url_name': 'reports_payments'}
    )
    sub_attendance, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Attendance Report',
        defaults={'url_name': 'reports_attendance'}
    )
    sub_financials, _ = SubMenu.objects.get_or_create(
        menu=m,
        name='Financial Summary',
        defaults={'url_name': 'reports_financials'}
    )
        
    # Grant permissions to all managers
    staff_managers = StaffUser.objects.filter(role__name__iexact='manager', status=True)
    submenus_list = [sub_overall, sub_rooms, sub_events, sub_tables, sub_payments, sub_attendance, sub_financials]
    for staff in staff_managers:
        user = staff.user
        for sub in submenus_list:
            MenuPermission.objects.get_or_create(
                user=user,
                submenu=sub,
                defaults={'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True}
            )

def reverse_reports_menu(apps, schema_editor):
    Menu = apps.get_model('staffapp', 'Menu')
    SubMenu = apps.get_model('staffapp', 'SubMenu')
    
    SubMenu.objects.filter(url_name__in=[
        'reports_overall',
        'reports_rooms',
        'reports_events',
        'reports_tables',
        'reports_payments',
        'reports_attendance',
        'reports_financials'
    ]).delete()
    Menu.objects.filter(name='Reports').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('staffapp', '0008_add_checkin_submenu'),
    ]

    operations = [
        migrations.RunPython(seed_reports_menu, reverse_code=reverse_reports_menu),
    ]
