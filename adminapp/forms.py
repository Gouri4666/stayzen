import re
from django import forms
from .models import Room,Service,Package,FoodItem
from .models import event_hall,Activity,ActivitySession,StaffUser,RestaurantTable,RegisteredUser,Department,Role

class RoomForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        room_type_choices = list(self.fields['room_type'].choices)

        if room_type_choices:
            room_type_choices[0] = ('', 'Select Room Type')
            self.fields['room_type'].choices = room_type_choices

    # Validation Methods

    def clean_room_number(self):
        room_number = self.cleaned_data['room_number']

        if Room.objects.filter(
                room_number=room_number
        ).exclude(pk=self.instance.pk).exists():

            raise forms.ValidationError(
                "This room number already exists."
            )

        return room_number

    def clean_max_adults(self):
        adults = self.cleaned_data['max_adults']

        if adults < 1:
            raise forms.ValidationError(
                "Max adults must be at least 1."
            )

        return adults

    def clean_max_children(self):
        children = self.cleaned_data['max_children']

        if children < 0:
            raise forms.ValidationError(
                "Max children cannot be negative."
            )

        return children

    def clean_price(self):
        price = self.cleaned_data['price']

        if price <= 0:
            raise forms.ValidationError(
                "Price must be greater than 0."
            )

        return price

    class Meta:
        model = Room
        fields = [
            'room_number',
            'room_type',
            'description',
            'max_adults',
            'max_children',
            'price',
            'image',
            'image2',
            'image3',
            'status',
        ]

        widgets = {
            'room_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Room Number'
            }),

            'room_type': forms.Select(attrs={
                'class': 'form-select'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control room-description',
                'rows': 5,
                'placeholder': 'Enter room description'
            }),

            'max_adults': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'max_children': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price per night'
            }),

            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'image2': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'image3': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class EventHallForm(forms.ModelForm):
    class Meta:
        model = event_hall
        fields = [
            'hall_name',
            'hall_type',
            'hall_description',
            'hall_capacity',
            'hall_price',
            'hall_image',
            'hall_image2',
            'hall_image3',
            'hall_status'
        ]

        widgets = {
            'hall_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Hall Name'
            }),

            'hall_type': forms.Select(attrs={
                'class': 'form-control'
            }),

            'hall_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter Hall Description'
            }),

            'hall_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Capacity'
            }),

            'hall_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Price'
            }),

            'hall_image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'hall_image2': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'hall_image3': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'hall_status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            'service_name',
            'service_price'
        ]
        widgets = {
            'service_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Service Name'
                }
            ),
            'service_price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Service Price'
                }
            ),
        }
class PackageForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    class Meta:
        model = Package
        fields = [
            'package_name',
            'package_type',
            'package_description',
            'guest_capacity',
            'hall',
            'services',
            'status'
        ]
        widgets = {
            'package_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Package Name'
                }
            ),
            'package_type': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'package_description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter Package Description'
                }
            ),
            'guest_capacity': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Guest Capacity'
                }
            ),
            'hall': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'status': forms.Select(
                attrs={'class': 'form-select'}
            ),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hall'].queryset = event_hall.objects.all()
        self.fields['services'].queryset = Service.objects.all()


class FoodItemForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Better safe placeholder handling
        self.fields['category'].empty_label = "Select Category"
        self.fields['dietary_status'].empty_label = "Select Dietary Status"

    # Validation: unique item name
    def clean_item_name(self):
        item_name = self.cleaned_data['item_name']

        if FoodItem.objects.filter(
            item_name=item_name
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This food item already exists.")

        return item_name

    # Validation: price must be positive
    def clean_price(self):
        price = self.cleaned_data['price']

        if price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")

        return price

    # Validation: quantity must not be negative
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']

        if quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")

        return quantity

    class Meta:
        model = FoodItem
        fields = [
            'item_name',
            'category',
            'cuisine',
            'dietary_status',
            'description',
            'price',
            'quantity',   # ✅ IMPORTANT ADDED
            'image',
            'status',
        ]

        widgets = {
            'item_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Item Name'
            }),

            'category': forms.Select(attrs={
                'class': 'form-select'
            }),

            'cuisine': forms.Select(attrs={
                'class': 'form-select'
            }),

            'dietary_status': forms.Select(attrs={
                'class': 'form-select'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter description'
            }),

            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price'
            }),

            'quantity': forms.NumberInput(attrs={   # ✅ NEW FIELD UI
                'class': 'form-control',
                'placeholder': 'Available Quantity'
            }),

            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

class ActivityForm(forms.ModelForm):

    class Meta:

        model = Activity

        fields = [
            'activity_name',
            'activity_type',
            'price',
            'activity_image',
            'description',
            'status'
        ]

        widgets = {

            'activity_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter activity name'
                }
            ),

            'activity_type': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter activity price'
                }
            ),

            'activity_image': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control'
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Enter activity description'
                }
            ),

            'status': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('Price must be greater than 0.')
        return price


class ActivitySessionForm(forms.ModelForm):

    class Meta:
        model = ActivitySession
        fields = [
            'start_time',
            'end_time',
            'capacity',
            'status'
        ]
        widgets = {
            'start_time': forms.TimeInput(
                attrs={'class': 'form-control', 'type': 'time'}
            ),
            'end_time': forms.TimeInput(
                attrs={'class': 'form-control', 'type': 'time'}
            ),
            'capacity': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1}
            ),
            'status': forms.Select(
                attrs={'class': 'form-control'}
            ),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity is not None and capacity < 1:
            raise forms.ValidationError('Capacity must be at least 1.')
        return capacity
    

class StaffUserForm(forms.ModelForm):

    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter Full Name'
            }
        )
    )

    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter Username'
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter Password'
            }
        )
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter Email Address'
            }
        )
    )

    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
        empty_label="-- Select Department --"
    )

    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
        empty_label="-- Select Role --"
    )

    class Meta:

        model = StaffUser

        fields = [
            'department',
            'role',
            'phone',
            'profile_image'
        ]

        widgets = {

            'phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Phone Number'
                }
            ),

            'profile_image': forms.ClearableFileInput(
            attrs={
            'class': 'form-control'
                }
            ),

        }

class RestaurantTableForm(forms.ModelForm):

    class Meta:

        model = RestaurantTable

        fields = [
            'table_number',
            'table_capacity',
            'table_image',
            'location',
            'status',
            'price',
            'description',
        ]

        widgets = {

            'table_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Table Number'
            }),

            'table_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Seating Capacity'
            }),

            'table_image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),

            'location': forms.Select(attrs={
                'class': 'form-select'
            }),

            'status': forms.Select(attrs={
                'class': 'form-select'
            }),

            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Table Price',
                'step': '0.01'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter Table Description'
            }),
        }


#Notification Form

class NotificationForm(forms.Form):
    broadcast_type = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={'class': 'broadcast-type-radio'})
    )
    
    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    staff_members = forms.ModelMultipleChoiceField(
        queryset=StaffUser.objects.none(),
        required=False, 
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )
    
    title = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notification Title'})
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your message...'})
    )

    # NEW: Add the FileField
    attachment = forms.FileField(
        required=False, 
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        # Extract the sender
        self.sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)

        # Ensure sender exists to avoid errors
        if not self.sender:
            return

        # Determine sender profile
        try:
            staff_profile = self.sender.staff_profile
            sender_role = staff_profile.role.name.lower() if staff_profile.role else 'staff'
            sender_dept = staff_profile.department
        except:
            sender_role = 'admin'
            sender_dept = None

        # Logic for field choices (same as your original)
        if self.sender.is_superuser or sender_role == 'admin':
            self.fields['broadcast_type'].choices = [
                ('all', 'All Staff'),
                ('department', 'By Department'),
                ('role', 'By Role'),
                # ('department_role', 'Role Within Department'),
                ('specific', 'Specific Staff'),
            ]
            self.fields['broadcast_type'].initial = 'all'
            self.fields['staff_members'].queryset = StaffUser.objects.filter(status=True).exclude(user=self.sender).select_related('user')

        elif sender_role == 'manager':
            dept_name = sender_dept.name if sender_dept else 'Department'
            self.fields['broadcast_type'].choices = [
                ('my_department', f'All in {dept_name}'),
                ('specific', 'Specific Staff in My Department'),
            ]
            self.fields['broadcast_type'].initial = 'my_department'
            self.fields['staff_members'].queryset = StaffUser.objects.filter(department=sender_dept, status=True).exclude(user=self.sender).select_related('user')

        else:
            self.fields['broadcast_type'].choices = [('my_manager', 'My Department Manager(s)')]
            self.fields['broadcast_type'].initial = 'my_manager'

    def clean(self):
        cleaned_data = super().clean()
        b_type = cleaned_data.get('broadcast_type')
        
        if b_type == 'department' and not cleaned_data.get('departments'):
            self.add_error('departments', 'Please select at least one department.')
        if b_type == 'role' and not cleaned_data.get('roles'):
            self.add_error('roles', 'Please select at least one role.')
        if b_type == 'specific' and not cleaned_data.get('staff_members'):
            self.add_error('staff_members', 'Please select at least one staff member.')
            
        return cleaned_data


class RegisteredUserForm(forms.ModelForm):
    """Form for admin-side staff registration (profile storage only)."""

    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
        empty_label="-- Select Department --"
    )

    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
        empty_label="-- Select Role --"
    )

    class Meta:
        model = RegisteredUser
        fields = [
            'full_name', 'username', 'email', 'phone',
            'department', 'role', 'resume', 'image',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Full Name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Email Address',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Phone Number',
            }),
            'resume': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            if not re.match(r'^\d{10}$', phone):
                raise forms.ValidationError("Enter a valid 10-digit phone number.")
        return phone

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            qs = RegisteredUser.all_objects.filter(username__iexact=username)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This username is already taken.")
        return username
    
#site settings
from .models import SiteSettings

class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = '__all__'
        widgets = {
            # Make the text areas a bit smaller so the form isn't too massive
            'index_slide1_text': forms.Textarea(attrs={'rows': 3}),
            'index_slide2_text': forms.Textarea(attrs={'rows': 3}),
            'index_slide3_text': forms.Textarea(attrs={'rows': 3}),
            'about_text': forms.Textarea(attrs={'rows': 5}),
            'about_pillar1_text': forms.Textarea(attrs={'rows': 2}),
            'about_pillar2_text': forms.Textarea(attrs={'rows': 2}),
            'about_pillar3_text': forms.Textarea(attrs={'rows': 2}),
            'about_pillar4_text': forms.Textarea(attrs={'rows': 2}),
        }
        
    def __init__(self, *args, **kwargs):
        super(SiteSettingsForm, self).__init__(*args, **kwargs)
        # Automatically add 'form-control' to every field without overwriting existing classes
        for field in self.fields.values():
            # Get existing classes, or start with an empty string if none exist
            existing_classes = field.widget.attrs.get('class', '')
            
            # Combine them ensuring there's a space
            field.widget.attrs['class'] = f"{existing_classes} form-control".strip()