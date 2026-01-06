from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.gis.geos import Point
from .models import (
    User, PincodeBoundary, ServiceCategory, Service, 
    Booking, Review, ChatRoom, Message
)
import phonenumbers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number',
            'first_name', 'last_name', 'profile_image',
            'is_verified', 'rating', 'total_transactions',
            'current_pincode', 'address'
        ]
        read_only_fields = ['id', 'is_verified', 'rating', 'total_transactions']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    pincode = serializers.CharField(write_only=True)
    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone_number', 'first_name', 'last_name',
            'password', 'confirm_password', 'pincode', 'latitude', 'longitude'
        ]
    
    def validate_phone_number(self, value):
        try:
            parsed_number = phonenumbers.parse(value, "IN")
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError("Invalid phone number")
        except:
            raise serializers.ValidationError("Invalid phone number format")
        return value
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Check if user with phone or email already exists
        if User.objects.filter(phone_number=data['phone_number']).exists():
            raise serializers.ValidationError("Phone number already registered")
        
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already registered")
        
        return data
    
    def create(self, validated_data):
        # Remove extra fields
        validated_data.pop('confirm_password')
        pincode = validated_data.pop('pincode')
        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        
        # Create location point
        location = Point(longitude, latitude, srid=4326)
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            location=location,
            current_pincode=pincode
        )
        
        return user

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        if phone_number and password:
            # Try to get user by phone number
            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid phone number or password")
            
            # Authenticate user
            user = authenticate(username=user.username, password=password)
            
            if not user:
                raise serializers.ValidationError("Invalid phone number or password")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
            
            data['user'] = user
        else:
            raise serializers.ValidationError("Must include phone number and password")
        
        return data

class PincodeBoundarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PincodeBoundary
        fields = ['pincode', 'area_name', 'city', 'state', 'center_point']

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon']

class ServiceSerializer(serializers.ModelSerializer):
    provider = UserSerializer(read_only=True)
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.all(),
        source='category',
        write_only=True
    )
    distance = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Service
        fields = [
            'id', 'provider', 'title', 'description', 'category', 'category_id',
            'service_type', 'price_per_hour', 'price_per_day', 'price_per_unit',
            'location', 'pincode', 'address', 'is_available', 'available_from',
            'available_to', 'average_rating', 'total_bookings', 'images',
            'created_at', 'distance'
        ]
        read_only_fields = ['id', 'provider', 'average_rating', 'total_bookings', 'created_at']
    
    def create(self, validated_data):
        validated_data['provider'] = self.context['request'].user
        return super().create(validated_data)

class BookingSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True
    )
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'service', 'service_id', 'user', 'start_time', 'end_time',
            'total_hours', 'total_days', 'total_amount', 'platform_fee',
            'status', 'payment_status', 'razorpay_order_id',
            'user_rating', 'provider_rating', 'user_review', 'provider_review',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'payment_status', 'created_at']
    
    def validate(self, data):
        # Check if service is available
        if not data['service'].is_available:
            raise serializers.ValidationError("Service is not available")
        
        # Check booking time conflicts
        conflicting_bookings = Booking.objects.filter(
            service=data['service'],
            status__in=['confirmed', 'in_progress'],
            start_time__lt=data['end_time'],
            end_time__gt=data['start_time']
        )
        
        if conflicting_bookings.exists():
            raise serializers.ValidationError("Service is already booked for this time")
        
        return data

class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)
    reviewed_user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'booking', 'reviewer', 'reviewed_user', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'reviewed_user', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'receiver', 'content', 'message_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'receiver', 'created_at']

class ChatRoomSerializer(serializers.ModelSerializer):
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)
    last_message = MessageSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'user1', 'user2', 'last_message', 'last_message_time',
                 'unread_count_user1', 'unread_count_user2', 'other_user', 'updated_at']
    
    def get_other_user(self, obj):
        request_user = self.context['request'].user
        other_user = obj.user2 if obj.user1 == request_user else obj.user1
        return UserSerializer(other_user).data
