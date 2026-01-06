import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from core.models import ChatRoom, Message
from datetime import datetime

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user has access to this chat room
        if not await self.has_access_to_room():
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send join message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': f'{self.user.username} joined the chat'
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'message':
            await self.handle_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        elif message_type == 'read_receipt':
            await self.handle_read_receipt(data)
    
    async def handle_message(self, data):
        content = data['content']
        message_type = data.get('message_type', 'text')
        
        # Save message to database
        message = await self.save_message(content, message_type)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message.id),
                'sender_id': str(self.user.id),
                'sender_username': self.user.username,
                'content': content,
                'message_type': message_type,
                'timestamp': message.created_at.isoformat(),
            }
        )
    
    async def handle_typing(self, data):
        # Broadcast typing indicator
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': data.get('is_typing', False),
            }
        )
    
    async def handle_read_receipt(self, data):
        # Mark messages as read
        message_id = data.get('message_id')
        if message_id:
            await self.mark_as_read(message_id)
        
        # Broadcast read receipt
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'message_id': message_id,
            }
        )
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'content': event['content'],
            'message_type': event['message_type'],
            'timestamp': event['timestamp'],
        }))
    
    async def typing_indicator(self, event):
        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing'],
        }))
    
    async def read_receipt(self, event):
        # Send read receipt
        await self.send(text_data=json.dumps({
            'type': 'read',
            'user_id': event['user_id'],
            'username': event['username'],
            'message_id': event.get('message_id'),
        }))
    
    @database_sync_to_async
    def has_access_to_room(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return self.user == room.user1 or self.user == room.user2
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content, message_type):
        room = ChatRoom.objects.get(id=self.room_id)
        receiver = room.user2 if self.user == room.user1 else room.user1
        
        message = Message.objects.create(
            room=room,
            sender=self.user,
            receiver=receiver,
            content=content,
            message_type=message_type
        )
        
        # Update room's last message
        room.last_message = content[:100]  # Store first 100 chars
        room.last_message_time = message.created_at
        
        # Update unread count
        if self.user == room.user1:
            room.unread_count_user2 += 1
        else:
            room.unread_count_user1 += 1
        
        room.save()
        
        return message
    
    @database_sync_to_async
    def mark_as_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id, receiver=self.user)
            message.is_read = True
            message.read_at = datetime.now()
            message.save()
            
            # Update unread count in room
            room = message.room
            if self.user == room.user1:
                room.unread_count_user1 = max(0, room.unread_count_user1 - 1)
            else:
                room.unread_count_user2 = max(0, room.unread_count_user2 - 1)
            room.save()
        except Message.DoesNotExist:
            pass
