from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class Menu(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name


class SubMenu(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="submenus")
    name = models.CharField(max_length=100)

    # IMPORTANT: this will match your django url name
    url_name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.menu.name} -> {self.name}"


class MenuPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    submenu = models.ForeignKey(SubMenu, on_delete=models.CASCADE)

    can_view = models.BooleanField(default=True)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'submenu')

    def __str__(self):
        return f"{self.user.username} - {self.submenu.name}"
    
class Attendance(models.Model):

    STATUS_CHOICES = (

        ('Present', 'Present'),

        ('Late', 'Late'),

        ('Half Day', 'Half Day'),

        ('Absent', 'Absent'),

        ('Checked Out', 'Checked Out'),

    )

    staff = models.ForeignKey(User, on_delete=models.CASCADE)

    date = models.DateField(default=timezone.now)

    check_in_time = models.TimeField(null=True, blank=True)

    check_out_time = models.TimeField(null=True, blank=True)

    working_hours = models.DurationField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Absent')



    class Meta:

        unique_together = ('staff', 'date')



    def __str__(self):

        return f"{self.staff.username} - {self.date} - {self.status}"





class Shift(models.Model):

    name = models.CharField(max_length=100)

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='custom_shift')

    department = models.CharField(max_length=50, null=True, blank=True)

    is_global = models.BooleanField(default=False)

    start_time = models.TimeField()

    end_time = models.TimeField()

    grace_time_minutes = models.IntegerField(default=15)



    def __str__(self):

        return self.name 

