from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    User, PincodeBoundary, Service, Booking, 
    Review, ChatRoom, Message
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    ServiceSerializer, BookingSerializer, ReviewSerializer,
    ChatRoomSerializer, MessageSerializer
)
from .geospatial import is_within_pincode_boundary
import json

class AuthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Verify if location is within pincode boundary
            try:
                pincode_boundary = PincodeBoundary.objects.get(
                    pincode=request.data['pincode']
                )
                if is_within_pincode_boundary(
                    user.location,
                    pincode_boundary.boundary
                ):
                    user.is_verified = True
                    user.verification_status = 'verified'
                    user.save()
            except PincodeBoundary.DoesNotExist:
                # Pincode not in database, manual verification required
                pass
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Service.objects.filter(is_available=True)
        
        # Get user's location
        user = self.request.user
        if user.location:
            # Filter by distance (1.5 km radius)
            queryset = queryset.filter(
                location__distance_lte=(user.location, D(km=1.5))
            ).annotate(
                distance=Distance('location', user.location)
            ).order_by('distance')
        
        # Filter by pincode
        pincode = self.request.query_params.get('pincode')
        if pincode:
            queryset = queryset.filter(pincode=pincode)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by service type
        service_type = self.request.query_params.get('service_type')
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price_per_hour__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_per_hour__lte=max_price)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Get services within 1.5 km radius"""
        if not request.user.location:
            return Response(
                {'error': 'User location not set'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = Service.objects.filter(
            location__distance_lte=(request.user.location, D(km=1.5)),
            is_available=True
        ).annotate(
            distance=Distance('location', request.user.location)
        ).order_by('distance')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """Book a service"""
        service = self.get_object()
        serializer = BookingSerializer(data=request.data)
        
        if serializer.is_valid():
            # Calculate total amount
            total_amount = self.calculate_booking_amount(
                service, 
                serializer.validated_data['start_time'],
                serializer.validated_data['end_time']
            )
            
            booking = serializer.save(
                user=request.user,
                service=service,
                total_amount=total_amount
            )
            
            return Response(
                BookingSerializer(booking).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def calculate_booking_amount(self, service, start_time, end_time):
        # Simplified calculation - in real app, calculate based on hours/days
        if service.price_per_hour:
            hours = (end_time - start_time).total_seconds() / 3600
            return service.price_per_hour * hours
        elif service.price_per_day:
            days = (end_time - start_time).days
            return service.price_per_day * days
        return service.price_per_unit or 0

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.filter(
            Q(user=user) | Q(service__provider=user)
        ).select_related('service', 'user').order_by('-created_at')
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking"""
        booking = self.get_object()
        
        if booking.service.provider != request.user:
            return Response(
                {'error': 'Only service provider can confirm booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking.status = 'confirmed'
        booking.save()
        
        return Response(BookingSerializer(booking).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark booking as completed"""
        booking = self.get_object()
        
        if booking.user != request.user and booking.service.provider != request.user:
            return Response(
                {'error': 'Only involved parties can complete booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking.status = 'completed'
        booking.save()
        
        return Response(BookingSerializer(booking).data)
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Add review for booking"""
        booking = self.get_object()
        
        if booking.status != 'completed':
            return Response(
                {'error': 'Can only review completed bookings'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rating = request.data.get('rating')
        comment = request.data.get('comment')
        
        if request.user == booking.user:
            booking.user_rating = rating
            booking.user_review = comment
        elif request.user == booking.service.provider:
            booking.provider_rating = rating
            booking.provider_review = comment
        else:
            return Response(
                {'error': 'Only involved parties can review'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking.save()
        
        # Update user ratings
        self.update_user_ratings(booking.user)
        self.update_user_ratings(booking.service.provider)
        
        return Response(BookingSerializer(booking).data)
    
    def update_user_ratings(self, user):
        # Calculate average rating for user
        avg_rating = Booking.objects.filter(
            Q(user=user, user_rating__isnull=False) |
            Q(service__provider=user, provider_rating__isnull=False)
        ).aggregate(
            avg_rating=Avg('user_rating') + Avg('provider_rating')
        )['avg_rating']
        
        if avg_rating:
            user.rating = avg_rating / 2  # Divide by 2 since we summed two averages
            user.save()

class ChatViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def rooms(self, request):
        """Get all chat rooms for user"""
        rooms = ChatRoom.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ).select_related('user1', 'user2').order_by('-last_message_time')
        
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def start_chat(self, request):
        """Start a new chat with another user"""
        other_user_id = request.data.get('user_id')
        
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if users are within same pincode
        if (request.user.current_pincode and other_user.current_pincode and
            request.user.current_pincode != other_user.current_pincode):
            return Response(
                {'error': 'Can only chat with users in same pincode'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create chat room
        room, created = ChatRoom.objects.get_or_create(
            user1=min(request.user, other_user, key=lambda u: u.id),
            user2=max(request.user, other_user, key=lambda u: u.id)
        )
        
        serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(serializer.data)
