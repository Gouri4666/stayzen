from django import forms
from .models import Menu, SubMenu

class MenuForm(forms.ModelForm):

    class Meta:
        model = Menu
        fields = '__all__'


class SubMenuForm(forms.ModelForm):

    class Meta:
        model = SubMenu
        fields = '__all__'