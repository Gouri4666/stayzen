from staffapp.models import MenuPermission

def has_permission(user, url_name, permission_type):

    if user.is_superuser:
        return True

    try:
        permission = MenuPermission.objects.get(
            user=user,
            submenu__url_name=url_name
        )

        return getattr(permission, permission_type)

    except MenuPermission.DoesNotExist:
        return False