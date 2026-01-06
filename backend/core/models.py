from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.geos import Point
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

class User(AbstractUser):
    """
    Custom User model with additional fields for Aangan app
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    location = models.PointField(geography=True, null=True, blank=True)
    current_pincode = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_transactions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Identity verification fields
    id_proof_front = models.ImageField(upload_to='verification/', null=True, blank=True)
    id_proof_back = models.ImageField(upload_to='verification/', null=True, blank=True)
    address_proof = models.ImageField(upload_to='verification/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.username} - {self.phone_number}"

class PincodeBoundary(models.Model):
    """
    Stores pincode boundaries for geo-fencing
    """
    pincode = models.CharField(max_length=10, unique=True)
    boundary = models.PolygonField(geography=True)
    center_point = models.PointField(geography=True)
    area_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    population = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['pincode']),
            models.Index(fields=['boundary']),
        ]
    
    def __str__(self):
        return f"{self.pincode} - {self.area_name}"

class ServiceCategory(models.Model):
    """
    Categories for services (e.g., Tools, Books, Skills, etc.)
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Service(models.Model):
    """
    Main service/asset model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True)
    
    # Service type
    SERVICE_TYPE_CHOICES = [
        ('asset', 'Asset Sharing'),
        ('skill', 'Skill/Service'),
    ]
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES)
    
    # Pricing
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Location
    location = models.PointField(geography=True)
    pincode = models.CharField(max_length=10)
    address = models.TextField()
    
    # Availability
    is_available = models.BooleanField(default=True)
    available_from = models.TimeField(null=True, blank=True)
    available_to = models.TimeField(null=True, blank=True)
    
    # Ratings and stats
    average_rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_bookings = models.IntegerField(default=0)
    
    # Images
    images = models.JSONField(default=list)  # Store list of image URLs
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['pincode', 'is_available']),
            models.Index(fields=['location']),
            models.Index(fields=['provider', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.provider.username}"

class Booking(models.Model):
    """
    Service booking model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    
    # Booking details
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    total_hours = models.IntegerField(null=True, blank=True)
    total_days = models.IntegerField(null=True, blank=True)
    
    # Pricing
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Ratings
    user_rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    provider_rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    user_review = models.TextField(null=True, blank=True)
    provider_review = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['service', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Booking #{self.id.hex[:8]} - {self.service.title}"

class Review(models.Model):
    """
    Reviews for services and users
    """
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    reviewed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['booking', 'reviewer']
    
    def __str__(self):
        return f"Review by {self.reviewer.username} - {self.rating}/5"

class ChatRoom(models.Model):
    """
    Chat room between two users
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatrooms_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatrooms_as_user2')
    last_message = models.TextField(null=True, blank=True)
    last_message_time = models.DateTimeField(null=True, blank=True)
    unread_count_user1 = models.IntegerField(default=0)
    unread_count_user2 = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user1', 'user2']
        indexes = [
            models.Index(fields=['user1', 'updated_at']),
            models.Index(fields=['user2', 'updated_at']),
        ]
    
    def __str__(self):
        return f"Chat: {self.user1.username} - {self.user2.username}"

class Message(models.Model):
    """
    Chat messages
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    
    # Message types
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('booking', 'Booking'),
    ]
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    
    # Metadata
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender', 'receiver', 'created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username}: {self.content[:50]}"
