from django.db import models
from django.contrib.auth.models import User

class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_created")
    edited_at = models.DateTimeField(auto_now=True)
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_edited")
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_deleted")
    is_deleted = models.BooleanField(default=False)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

class Room(AuditModel):

    ROOM_TYPES = [
        ('Single', 'Single'),
        ('Double', 'Double'),
        ('Deluxe', 'Deluxe'),
        ('Suite', 'Suite'),
    ]

    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Not Available', 'Not Available'),
        ('Reserved', 'Reserved'),
        ('Occupied', 'Occupied'),
        ('Maintenance', 'Maintenance'),
    ]

    room_number = models.CharField(max_length=20, unique=True)

    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPES
    )

    description = models.TextField()

    max_adults = models.IntegerField()

    max_children = models.IntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    image = models.ImageField(
        upload_to='rooms/'
    )

    image2 = models.ImageField(
        upload_to='rooms/',
        blank=True,
        null=True
    )

    image3 = models.ImageField(
        upload_to='rooms/',
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Available'
    )

    def __str__(self):
        return self.room_number
    

class event_hall(AuditModel):

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('maintenance', 'Maintenance'),
    ]
    HALL_TYPE_CHOICES = [
        ('conference', 'Conference Hall'),
        ('banquet', 'Banquet Hall'),
        ('wedding', 'Wedding Hall')
    ]
    hall_id=models.AutoField(primary_key=True)
    hall_name=models.CharField(max_length=100)
    hall_type=models.CharField(max_length=100, choices=HALL_TYPE_CHOICES,default='conference')
    hall_description=models.TextField()
    hall_capacity=models.IntegerField()
    hall_price=models.DecimalField(max_digits=10, decimal_places=2)
    hall_image=models.ImageField(upload_to='event_hall/')
    hall_image2=models.ImageField(upload_to='event_hall/', blank=True, null=True)
    hall_image3=models.ImageField(upload_to='event_hall/', blank=True, null=True)
    hall_status=models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return self.hall_name
    

class Service(AuditModel):
    service_id = models.AutoField(primary_key=True)
    service_name = models.CharField(max_length=100)
    service_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    def __str__(self):
        return self.service_name
    
# packages
class Package(AuditModel):
    PACKAGE_TYPE_CHOICES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ]
    package_id = models.AutoField(primary_key=True)
    package_name = models.CharField(max_length=100)
    package_type = models.CharField(
        max_length=20,
        choices=PACKAGE_TYPE_CHOICES,
        default='basic'
    )
    package_description = models.TextField()
    guest_capacity = models.IntegerField()
    hall = models.ForeignKey(
        event_hall,
        on_delete=models.CASCADE
    )
    services = models.ManyToManyField(
        Service,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    def __str__(self):
        return self.package_name

    @property
    def package_price(self):
        return sum(service.service_price for service in self.services.all())
    

EventHall = event_hall

class FoodItem(AuditModel):

    CATEGORY_CHOICES = [
        ('Starter', 'Starter'),
        ('Main Course', 'Main Course'),
        ('Dessert', 'Dessert'),
        ('Beverage', 'Beverage'),
        ('Alcohol', 'Alcohol'),
    ]

    DIETARY_CHOICES = [
        ('Veg', 'Veg'),
        ('Non-Veg', 'Non-Veg'),
        ('Egg', 'Egg'),
        ('N/A', 'N/A'),
    ]

    CUISINE_CHOICES = [
        ('Indian', 'Indian'),
        ('Chinese', 'Chinese'),
        ('Italian', 'Italian'),
        ('Continental', 'Continental'),
        ('Mexican', 'Mexican'),
        ('Arabic', 'Arabic'),
        ('Thai', 'Thai'),
        ('Japanese', 'Japanese'),
        ('American', 'American'),
        ('Kerala', 'Kerala'),
    ]

    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Unavailable', 'Unavailable'),
    ]

    item_name = models.CharField(
        max_length=100,
        unique=True
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='Main Course'
    )

    cuisine = models.CharField(
        max_length=50,
        choices=CUISINE_CHOICES,
        default='Indian'
    )

    dietary_status = models.CharField(
        max_length=20,
        choices=DIETARY_CHOICES,
        default='Veg'
    )

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    quantity = models.PositiveIntegerField(
        default=0,
        help_text="Available stock quantity"
    )

    image = models.ImageField(
        upload_to='food_items/'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Available'
    )

    def save(self, *args, **kwargs):

        if self.quantity <= 0:
            self.status = 'Unavailable'
        else:
            self.status = 'Available'

        super().save(*args, **kwargs)

    def __str__(self):
        return self.item_name
    


class Activity(AuditModel):

    activity_name = models.CharField(max_length=100)

    ACTIVITY_TYPES = (
        ('Yoga', 'Yoga'),
        ('Swimming', 'Swimming'),
        ('Zumba', 'Zumba'),
        ('Indoor games', 'indoor games'),
        ('Spa', 'Spa'),
        ('Fitness', 'Fitness'),
    )

    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES
    )

    status = models.CharField(
        max_length=20,
        choices=(
            ('Available', 'Available'),
            ('Unavailable', 'Unavailable')
        ),
        default='Available'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    activity_image = models.ImageField(
        upload_to='activities/'
    )

    description = models.TextField()

    def __str__(self):
        return self.activity_name
 
class ActivitySession(AuditModel):

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='sessions'
    )

    session_date = models.DateField(null=True, blank=True)

    start_time = models.TimeField()

    end_time = models.TimeField()

    capacity = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=(
            ('Available', 'Available'),
            ('Full', 'Full'),
            ('Cancelled', 'Cancelled')
        ),
        default='Available'
    )

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.activity.activity_name} - {self.start_time}-{self.end_time}"



class Department(AuditModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Role(AuditModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class StaffUser(AuditModel):

    profile_image = models.ImageField(
        upload_to='staff_profiles/',
        blank=True,
        null=True
    )
    resume = models.FileField(
        upload_to='staff_resumes_active/',
        blank=True,
        null=True
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_users')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_users')

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    status = models.BooleanField(
        default=True
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        help_text="Auto-generated on save based on department. Do not set manually."
    )

    def _generate_employee_id(self):
        """
        Builds the next sequential Employee ID for this staff member's
        department using the first 2 letters, e.g. EV001, AD001.
        Numbering is independent per department prefix and always unique.
        """
        if not self.department or not self.department.name:
            return None
            
        # Dynamic prefix: first two letters of department name, uppercase
        prefix = self.department.name[:2].upper()

        last_number = 0
        # Look at existing IDs sharing this prefix to find the next number.
        existing_ids = StaffUser.all_objects.filter(
            employee_id__startswith=prefix
        ).exclude(pk=self.pk).values_list('employee_id', flat=True)

        for existing_id in existing_ids:
            suffix = existing_id[len(prefix):]
            if suffix.isdigit():
                last_number = max(last_number, int(suffix))

        next_number = last_number + 1
        candidate = f"{prefix}{next_number:03d}"

        # Guard against any race/duplicate, just in case.
        while StaffUser.all_objects.filter(employee_id=candidate).exclude(pk=self.pk).exists():
            next_number += 1
            candidate = f"{prefix}{next_number:03d}"

        return candidate

    def save(self, *args, **kwargs):
        # Only ever generate when empty. Existing employee_id values
        # (set or NULL) are never touched here.
        if not self.employee_id and self.department_id:
            generated_id = self._generate_employee_id()
            if generated_id:
                self.employee_id = generated_id

        super().save(*args, **kwargs)

    def _str_(self):
        return f"{self.user.get_full_name() or self.user.username}"


class RestaurantTable(AuditModel):

    TABLE_STATUS = [
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('Occupied', 'Occupied'),
        ('Maintenance', 'Maintenance'),
    ]

    LOCATION_CHOICES = [
        ('Indoor', 'Indoor'),
        ('Outdoor', 'Outdoor'),
        ('Pool Side', 'Pool Side'),
        ('Window Side', 'Window Side'),
        ('Garden Side', 'Garden Side'),
        ('Rooftop', 'Rooftop'),
        ('Private Dining', 'Private Dining'),
    ]

    table_number = models.CharField(
        max_length=20,
        unique=True
    )

    table_capacity = models.PositiveIntegerField()

    table_image = models.ImageField(
        upload_to='restaurant_tables/',
        blank=True,
        null=True
    )

    location = models.CharField(
        max_length=50,
        choices=LOCATION_CHOICES,
        default='Indoor'
    )

    status = models.CharField(
        max_length=20,
        choices=TABLE_STATUS,
        default='Available'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Table {self.table_number}"
    


#staffmessage


class NotificationBroadcast(models.Model):
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_broadcasts')
    title = models.CharField(max_length=255)
    message = models.TextField()
    # New Field
    attachment = models.FileField(upload_to='notifications/attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class NotificationStatus(models.Model):
    broadcast = models.ForeignKey(NotificationBroadcast, on_delete=models.CASCADE, related_name='recipients')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    is_read = models.BooleanField(default=False)

class RegisteredUser(AuditModel):
    """
    Admin-side staff registration profile storage.
    This is NOT part of the authentication system.
    It stores pre-registered staff details that can be
    selected when creating a StaffUser account.
    """
    USER_TYPE_CHOICES = [
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    ]

    full_name = models.CharField(max_length=150)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_users')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_users')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='staff')
    resume = models.FileField(upload_to='staff_resumes/', blank=True, null=True)
    image = models.ImageField(upload_to='staff_registration_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.username})"

# -----------------------------
# -----------------------------
# -------Site settings---------
# -----------------------------
# -----------------------------
from django.db import models

class SiteSettings(models.Model):
    # --- SLIDE 1 (Rooms) ---
    index_slide1_subtitle = models.CharField(max_length=200, default="Welcome to StayZen")
    index_slide1_title = models.CharField(max_length=200, default="Luxury Rooms & Suites")
    index_slide1_text = models.TextField(default="Experience unmatched comfort and style. Our beautifully appointed rooms and suites offer a serene sanctuary for your stay.")
    index_slide1_image = models.ImageField(upload_to='site_images/index/', blank=True, null=True)

    # --- SLIDE 2 (Events) ---
    index_slide2_subtitle = models.CharField(max_length=200, default="Elegant Spaces")
    index_slide2_title = models.CharField(max_length=200, default="Premium Event & Wedding Halls")
    index_slide2_text = models.TextField(default="Host your special moments in our exquisite event halls. From grand weddings to professional conferences, we cater to every detail.")
    index_slide2_image = models.ImageField(upload_to='site_images/index/', blank=True, null=True)

    # --- SLIDE 3 (Dining) ---
    index_slide3_subtitle = models.CharField(max_length=200, default="Fine Dining")
    index_slide3_title = models.CharField(max_length=200, default="Exquisite Culinary Journeys")
    index_slide3_text = models.TextField(default="Indulge in a premium dining experience. Our master chefs combine fresh local ingredients to create sensational signature dishes.")
    index_slide3_image = models.ImageField(upload_to='site_images/index/', blank=True, null=True)

    # --- ABOUT PAGE SETTINGS ---
    about_heading = models.CharField(max_length=200, default="About StayZen")
    about_text = models.TextField(blank=True, null=True)
    about_image = models.ImageField(upload_to='site_images/about/', blank=True, null=True)

    # ... your existing About Page fields ...
    about_heading = models.CharField(max_length=200, default="About StayZen")
    about_text = models.TextField(blank=True, null=True)
    about_image = models.ImageField(upload_to='site_images/about/', blank=True, null=True)

    # =========================================
    # ABOUT PAGE: SOFT PILLARS (SERVICES)
    # =========================================
    about_pillar1_title = models.CharField(max_length=150, default="Serene Suites")
    about_pillar1_text = models.TextField(default="Unwind in light-filled rooms featuring organic textures, premium linens, and views that ground you.")
    
    about_pillar2_title = models.CharField(max_length=150, default="Conscious Dining")
    about_pillar2_text = models.TextField(default="Nourish your body with farm-to-table cuisine prepared with mindfulness and local ingredients.")
    
    about_pillar3_title = models.CharField(max_length=150, default="Holistic Spa")
    about_pillar3_text = models.TextField(default="Restore your balance with botanical therapies designed to soothe both physical and mental tension.")
    
    about_pillar4_title = models.CharField(max_length=150, default="Mindful Events")
    about_pillar4_text = models.TextField(default="Host meaningful gatherings in adaptable spaces that encourage focus, connection, and joy.")

    # Gallery
    about_gallery_subtitle = models.CharField(max_length=100, default="Visual Journey")
    about_gallery_title = models.CharField(max_length=100, default="Spaces to Breathe")
    about_gallery_img1 = models.ImageField(upload_to='site_images/about/', blank=True, null=True)
    about_gallery_caption1 = models.CharField(max_length=100, default="Minimalist Suites")
    about_gallery_img2 = models.ImageField(upload_to='site_images/about/', blank=True, null=True)
    about_gallery_caption2 = models.CharField(max_length=100, default="Organic Dining")
    about_gallery_img3 = models.ImageField(upload_to='site_images/about/', blank=True, null=True)
    about_gallery_caption3 = models.CharField(max_length=100, default="Open-Air Venues")
    # =========================================
    # FACILITIES SECTION
    # =========================================
    facilities_subtitle = models.CharField(max_length=200, default="Facilities")
    facilities_title = models.CharField(max_length=200, default="Hotel Facilities")

    # --- Facility 1 ---
    facility1_title = models.CharField(max_length=200, default="Rooms and Suites")
    facility1_text = models.TextField(default="Varied types of rooms, from standard to luxury suites, equipped with essentials like beds.")
    facility1_icon = models.FileField(upload_to='site_images/icons/', blank=True, null=True) # FileField allows SVG icons

    # --- Facility 2 ---
    facility2_title = models.CharField(max_length=200, default="24-Hour Security")
    facility2_text = models.TextField(default="On-site security personnel and best surveillance. Secure storage for valuables.")
    facility2_icon = models.FileField(upload_to='site_images/icons/', blank=True, null=True)

    # --- Facility 3 ---
    facility3_title = models.CharField(max_length=200, default="Fitness Center")
    facility3_text = models.TextField(default="Equipped with exercise machines and weights. Offering massages, facials, and other treatments.")
    facility3_icon = models.FileField(upload_to='site_images/icons/', blank=True, null=True)

    # --- Facility 4 ---
    facility4_title = models.CharField(max_length=200, default="Swimming Pool")
    facility4_text = models.TextField(default="Indoor or outdoor pools for leisure or exercise. Offering massages, facials, and other treatments")
    facility4_icon = models.FileField(upload_to='site_images/icons/', blank=True, null=True)
    

    # =========================================
    # CONTACT PAGE SETTINGS
    # =========================================
    contact_email = models.EmailField(default="stayzen@gmail.com")
    contact_phone = models.CharField(max_length=20, default="+91 452 584 9632")
    contact_address = models.TextField(default="StayZen Hotel & Resort, Kerala, India")
    social_facebook = models.URLField(blank=True, null=True)
    social_linkedin = models.URLField(blank=True, null=True)
    social_twitter = models.URLField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super(SiteSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj