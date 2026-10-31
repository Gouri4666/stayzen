from adminapp.models import StaffUser, NotificationStatus, Department, Role
from .models import Menu, MenuPermission, SubMenu

def menu_permissions(request):
    if not request.user.is_authenticated:
        return {}

    # Fetch unread count and recent notifications
    unread_count = NotificationStatus.objects.filter(recipient=request.user, is_read=False).count()
    recent_notifications = NotificationStatus.objects.filter(recipient=request.user)\
        .select_related('broadcast')[:5]
    
    notification_context = {
        'unread_count': unread_count,
        'recent_notifications': recent_notifications
    }

    # ==========================
    # ADMIN (Full Access)
    # ==========================
    if request.user.is_superuser:
        dept, _ = Department.objects.get_or_create(name='Administration')
        role, _ = Role.objects.get_or_create(name='Manager')
        staff, _ = StaffUser.objects.get_or_create(
            user=request.user,
            defaults={'status': True, 'department': dept, 'role': role}
        )
        all_menus = Menu.objects.prefetch_related('submenus').all()
        menu_data = []
        for menu in all_menus:
            menu_data.append({'menu': menu, 'submenus': menu.submenus.all()})
        
        return {
            'menus': menu_data,
            'staff': staff,
            'permissions': {},
            **notification_context
        }

    # ==========================
    # STAFF / MANAGERS
    # ==========================
    try:
        staff = StaffUser.objects.get(user=request.user, status=True)

        # 1. Get explicit permissions
        menu_permissions = MenuPermission.objects.filter(
            user=request.user, can_view=True
        ).select_related('submenu', 'submenu__menu')

        menu_data = {}
        for p in menu_permissions:
            menu = p.submenu.menu
            if menu.id not in menu_data:
                menu_data[menu.id] = {'menu': menu, 'submenus': []}
            menu_data[menu.id]['submenus'].append(p.submenu)

        # --- FIX: ALWAYS ADD NOTIFICATION MENU FOR STAFF/MANAGERS ---
        # Adjust 'Notifications' string if your Menu name in database is different
        notif_menu = Menu.objects.filter(name__iexact='Notifications').prefetch_related('submenus').first()
        if notif_menu:
            if notif_menu.id not in menu_data:
                menu_data[notif_menu.id] = {'menu': notif_menu, 'submenus': []}
            
            # Add all submenus under Notifications to the user's view
            for sub in notif_menu.submenus.all():
                if sub not in menu_data[notif_menu.id]['submenus']:
                    menu_data[notif_menu.id]['submenus'].append(sub)

        # --- FIX: ALWAYS ADD OFFLINE BOOKING MENU FOR RECEPTIONIST/FRONT OFFICE ---
        if (staff.role and staff.role.name.lower() == 'receptionist') or (staff.department and staff.department.name.lower() == 'front office'):
            offline_menu = Menu.objects.filter(name__iexact='Offline Booking').prefetch_related('submenus').first()
            if offline_menu:
                if offline_menu.id not in menu_data:
                    menu_data[offline_menu.id] = {'menu': offline_menu, 'submenus': []}
                for sub in offline_menu.submenus.all():
                    if sub not in menu_data[offline_menu.id]['submenus']:
                        menu_data[offline_menu.id]['submenus'].append(sub)

        # --- FIX: ALWAYS ADD MY DELIVERIES MENU FOR STAFF WHO HAVE HOME DELIVERIES VIEW PERMISSION ---
        has_delivery_access = False
        for p in menu_permissions:
            if p.submenu.url_name == 'admin_home_deliveries':
                has_delivery_access = True
                break
        
        if has_delivery_access:
            my_deliv_submenu = SubMenu.objects.filter(url_name='staff_my_deliveries').first()
            if my_deliv_submenu:
                menu = my_deliv_submenu.menu
                if menu.id not in menu_data:
                    menu_data[menu.id] = {'menu': menu, 'submenus': []}
                if my_deliv_submenu not in menu_data[menu.id]['submenus']:
                    menu_data[menu.id]['submenus'].append(my_deliv_submenu)

        # 2. Map all permissions for template usage (including notification perms)
        permissions = {}
        all_permissions = MenuPermission.objects.filter(user=request.user).select_related('submenu')
        
        print("USER:", request.user.username)
        print("SUPERUSER:", request.user.is_superuser)
        print("PERMISSION COUNT:", all_permissions.count())
        print("MENUS GENERATED:", len(menu_data))
        
        for p in all_permissions:
            permissions[p.submenu.url_name] = {
                'view': p.can_view,
                'add': p.can_add,
                'edit': p.can_edit,
                'delete': p.can_delete,
            }
        
        # Add default permission for Notification views so they don't get blocked
        # (This assumes the URLs are: inbox, view_notification, etc.)
        for sub in notif_menu.submenus.all() if notif_menu else []:
            if sub.url_name not in permissions:
                permissions[sub.url_name] = {'view': True, 'add': False, 'edit': False, 'delete': False}

        # Add default permission for Offline Booking views so they don't get blocked
        if (staff.role and staff.role.name.lower() == 'receptionist') or (staff.department and staff.department.name.lower() == 'front office'):
            offline_menu = Menu.objects.filter(name__iexact='Offline Booking').prefetch_related('submenus').first()
            if offline_menu:
                for sub in offline_menu.submenus.all():
                    if sub.url_name not in permissions:
                        permissions[sub.url_name] = {'view': True, 'add': True, 'edit': True, 'delete': True}

        # Add default permission for My Deliveries view so it doesn't get blocked
        if has_delivery_access or 'admin_home_deliveries' in permissions:
            permissions['staff_my_deliveries'] = {'view': True, 'add': False, 'edit': True, 'delete': False}



        return {
            'menus': menu_data.values(),
            'staff': staff,
            'permissions': permissions,
            **notification_context
        }

    except StaffUser.DoesNotExist:
        return {
            'menus': [],
            'staff': None,
            'permissions': {},
            **notification_context
        }