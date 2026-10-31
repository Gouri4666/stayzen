import re
from django import forms
from django.core.validators import EmailValidator
from django.contrib.auth.models import User
from adminapp.models import StaffUser


class StaffProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    address = forms.CharField(max_length=255, required=False)

    class Meta:
        model = StaffUser
        fields = ['phone', 'profile_image', 'address']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            if not re.match(r'^\d{10}$', phone):
                raise forms.ValidationError("Enter a valid 10-digit phone number.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            validator = EmailValidator()
            validator(email)
            if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
                raise forms.ValidationError("This email is already in use.")
        return email

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'profile_image':
                self.fields[field].widget.attrs.update({'class': 'form-control'})
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            # Populate address if exists
            if hasattr(user, 'staff_profile'):
                self.fields['address'].initial = user.staff_profile.address

    def save(self, commit=True):
        staff_profile = super().save(commit=False)
        user = staff_profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            staff_profile.save()
        return staff_profile
