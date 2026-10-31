from django import forms
from .models import ContactMessage

class ContactMessageForm(forms.ModelForm):
    RATING_CHOICES = [
        (5, '5 Stars'),
        (4, '4 Stars'),
        (3, '3 Stars'),
        (2, '2 Stars'),
        (1, '1 Star'),
    ]
    
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        empty_value=None,
        widget=forms.RadioSelect,
        required=False 
    )

    class Meta:
        model = ContactMessage
        fields = ['inquiry_type', 'service_type', 'name', 'email', 'message', 'rating']

    def clean(self):
        cleaned_data = super().clean()
        inquiry_type = cleaned_data.get('inquiry_type')
        rating = cleaned_data.get('rating')

        if inquiry_type == 'feedback' and not rating:
            self.add_error('rating', 'Rating is required for feedback.')
        if inquiry_type == 'feedback' and not cleaned_data.get('service_type'):
            self.add_error('service_type', 'Service type is required for feedback.')
        elif inquiry_type != 'feedback':
            cleaned_data['rating'] = None
            cleaned_data['service_type'] = None

        return cleaned_data