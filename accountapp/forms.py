from django import forms
from django.contrib.auth.models import User
from .models import Customer

class UserUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class CustomerUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
    class Meta:
        model = Customer
        fields = ['phone', 'address', 'gender', 'image']