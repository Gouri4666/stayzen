# guestapp/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# class Feedback(models.Model):
#     CONTACT_CHOICES = [
#         ('Enquiry', 'Enquiry'),
#         ('Feedback', 'Feedback'),
#         ('Other', 'Other'),
#     ]

#     contact_type = models.CharField(max_length=20, choices=CONTACT_CHOICES, default='Enquiry')
#     name = models.CharField(max_length=100)
#     email = models.EmailField()
#     message = models.TextField()
    
#     # Made null/blank true so 'Enquiry' submissions don't crash the database
#     rating = models.IntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(5)],
#         null=True, 
#         blank=True
#     )
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.contact_type} from {self.name}"


from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class ContactMessage(models.Model):
    INQUIRY_CHOICES = [
        ('general', 'General Enquiry'),
        ('feedback', 'Leave Feedback / Rating'),
        ('other', 'Other'),
    ]
    SERVICE_CHOICES = [
        ('room_service', 'Room Service'),
        ('restaurant', 'Restaurant'),
        ('event_hall', 'Event Hall'),
        ('activities', 'Activities'),
        ('website_experience', 'Website Experience'),
        ('staff_behaviour', 'Staff Behaviour'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    # Your database already has this column, we are just making sure it matches
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_CHOICES, default='general')
    service_type = models.CharField(max_length=50, choices=SERVICE_CHOICES, null=True, blank=True)
    is_registered = models.BooleanField(default=False)
    message = models.TextField()
    
    # NEW: Add the rating field here
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.inquiry_type} - {self.name}"

    @property
    def star_display(self):
        if self.rating is None:
            return []
        return [('★', True) if i < self.rating else ('☆', False) for i in range(5)]