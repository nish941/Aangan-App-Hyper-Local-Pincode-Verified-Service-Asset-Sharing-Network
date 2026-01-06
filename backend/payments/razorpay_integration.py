import razorpay
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Booking
import uuid

# Initialize Razorpay client
client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Create a Razorpay order for booking payment
    """
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')
    
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        
        # Create order data
        order_data = {
            'amount': int(float(amount) * 100),  # Convert to paise
            'currency': 'INR',
            'receipt': f'booking_{booking_id}',
            'payment_capture': 1,
            'notes': {
                'booking_id': str(booking_id),
                'user_id': str(request.user.id),
            }
        }
        
        # Create Razorpay order
        order = client.order.create(data=order_data)
        
        # Update booking with order ID
        booking.razorpay_order_id = order['id']
        booking.save()
        
        return Response({
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'key': settings.RAZORPAY_KEY_ID,
        })
        
    except Booking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=404
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=500
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    Verify Razorpay payment signature
    """
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')
    
    try:
        booking = Booking.objects.get(
            razorpay_order_id=razorpay_order_id,
            user=request.user
        )
        
        # Verify signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        
        # Update booking payment status
        booking.razorpay_payment_id = razorpay_payment_id
        booking.payment_status = 'paid'
        booking.save()
        
        return Response({
            'status': 'success',
            'message': 'Payment verified successfully'
        })
        
    except Booking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=404
        )
    except razorpay.errors.SignatureVerificationError:
        return Response(
            {'error': 'Invalid payment signature'},
            status=400
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=500
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_refund(request):
    """
    Initiate refund for a booking
    """
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')
    
    try:
        booking = Booking.objects.get(id=booking_id)
        
        # Check if user can initiate refund
        if booking.user != request.user and booking.service.provider != request.user:
            return Response(
                {'error': 'Not authorized to initiate refund'},
                status=403
            )
        
        # Check if payment was made
        if not booking.razorpay_payment_id:
            return Response(
                {'error': 'No payment found for this booking'},
                status=400
            )
        
        # Create refund data
        refund_data = {
            'payment_id': booking.razorpay_payment_id,
            'amount': int(float(amount) * 100),  # Convert to paise
            'notes': {
                'booking_id': str(booking_id),
                'reason': request.data.get('reason', 'Customer request')
            }
        }
        
        # Create refund
        refund = client.payment.refund(**refund_data)
        
        # Update booking
        booking.payment_status = 'refunded'
        booking.save()
        
        return Response({
            'status': 'success',
            'refund_id': refund['id'],
            'amount': refund['amount'],
            'message': 'Refund initiated successfully'
        })
        
    except Booking.DoesNotExist:
        return Response(
            {'error': 'Booking not found'},
            status=404
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=500
        )
