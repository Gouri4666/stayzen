from django.contrib import admin
from .models import Menu, SubMenu, MenuPermission,Attendance

class DebugAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        return {"view": True}

admin.site.register(Menu, DebugAdmin)
admin.site.register(SubMenu, DebugAdmin)
admin.site.register(MenuPermission, DebugAdmin)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in_time', 'check_out_time', 'status')
    list_filter = ('date', 'status')
    search_fields = ('staff__username', 'staff__first_name')