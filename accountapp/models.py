from django.db import models
from django.contrib.auth.models import User
from adminapp.models import FoodItem   # or your correct app
from django.conf import settings
# Create your models here.
class Customer(models.Model):
    MEMBERSHIP_BRONZE = 'Bronze'
    MEMBERSHIP_SILVER = 'Silver'
    MEMBERSHIP_GOLD = 'Gold'
    MEMBERSHIP_PLATINUM = 'Platinum'

    MEMBERSHIP_CHOICES = [
        (MEMBERSHIP_BRONZE, 'Bronze'),
        (MEMBERSHIP_SILVER, 'Silver'),
        (MEMBERSHIP_GOLD, 'Gold'),
        (MEMBERSHIP_PLATINUM, 'Platinum'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=15)
    address = models.TextField()
    gender = models.CharField(max_length=10)
    loyalty_points = models.PositiveIntegerField(default=0)
    membership_status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_CHOICES,
        default=MEMBERSHIP_BRONZE
    )
    lifetime_points_earned = models.PositiveIntegerField(default=0)

    image = models.ImageField(
        upload_to='customer_images/',
        blank=True,
        null=True
    )

    verification_status = models.BooleanField(default=False)
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_document = models.CharField(max_length=255, blank=True, null=True)
    
    @staticmethod
    def calculate_membership_status(points):
        if points >= 3000:
            return Customer.MEMBERSHIP_PLATINUM
        if points >= 1500:
            return Customer.MEMBERSHIP_GOLD
        if points >= 500:
            return Customer.MEMBERSHIP_SILVER
        return Customer.MEMBERSHIP_BRONZE

    @property
    def next_membership_tier(self):
        if self.lifetime_points_earned < 500:
            return Customer.MEMBERSHIP_SILVER
        if self.lifetime_points_earned < 1500:
            return Customer.MEMBERSHIP_GOLD
        if self.lifetime_points_earned < 3000:
            return Customer.MEMBERSHIP_PLATINUM
        return None

    @property
    def points_needed_for_next_tier(self):
        if self.lifetime_points_earned < 500:
            return 500 - self.lifetime_points_earned
        if self.lifetime_points_earned < 1500:
            return 1500 - self.lifetime_points_earned
        if self.lifetime_points_earned < 3000:
            return 3000 - self.lifetime_points_earned
        return 0

    @property
    def membership_progress_percent(self):
        points = self.lifetime_points_earned
        if points >= 3000:
            return 100
        if points >= 1500:
            return int(((points - 1500) / 1500) * 100)
        if points >= 500:
            return int(((points - 500) / 1000) * 100)
        return int((points / 500) * 100)

    def save(self, *args, **kwargs):
        self.membership_status = self.calculate_membership_status(
            self.lifetime_points_earned
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username
    
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    food = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'food')