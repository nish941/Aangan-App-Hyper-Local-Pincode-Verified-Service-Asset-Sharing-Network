import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:aangan_app/utils/constants.dart';

class WebSocketService {
  static final WebSocketService _instance = WebSocketService._internal();
  factory WebSocketService() => _instance;
  WebSocketService._internal();

  WebSocketChannel? _channel;
  String? _accessToken;
  final Map<String, Function(Map<String, dynamic>)> _listeners = {};

  Future<void> connect(String roomId) async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString('access_token');
    
    final wsUrl = '${ApiConstants.wsUrl}/ws/chat/$roomId/?token=$_accessToken';
    
    try {
      _channel = IOWebSocketChannel.connect(wsUrl);
      
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
      );
      
      print('WebSocket connected to room $roomId');
    } catch (e) {
      print('WebSocket connection failed: $e');
      // Retry after 3 seconds
      await Future.delayed(const Duration(seconds: 3));
      connect(roomId);
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }

  void sendMessage(String content, {String type = 'message'}) {
    if (_channel != null) {
      final message = {
        'type': type,
        'content': content,
        'timestamp': DateTime.now().toIso8601String(),
      };
      _channel!.sink.add(json.encode(message));
    }
  }

  void sendTyping(bool isTyping) {
    if (_channel != null) {
      final typing = {
        'type': 'typing',
        'is_typing': isTyping,
      };
      _channel!.sink.add(json.encode(typing));
    }
  }

  void sendReadReceipt(String messageId) {
    if (_channel != null) {
      final receipt = {
        'type': 'read_receipt',
        'message_id': messageId,
      };
      _channel!.sink.add(json.encode(receipt));
    }
  }

  void addListener(String event, Function(Map<String, dynamic>) callback) {
    _listeners[event] = callback;
  }

  void removeListener(String event) {
    _listeners.remove(event);
  }

  void _handleMessage(dynamic data) {
    try {
      final message = json.decode(data);
      final type = message['type'];
      
      if (_listeners.containsKey(type)) {
        _listeners[type]!(message);
      }
      
      // Handle system messages
      if (type == 'system') {
        print('System: ${message['message']}');
      }
    } catch (e) {
      print('Error handling message: $e');
    }
  }

  void _handleError(dynamic error) {
    print('WebSocket error: $error');
    // Try to reconnect
    if (_channel != null) {
      // Extract room ID from URL
      final url = _channel!.toString();
      final roomIdMatch = RegExp(r'chat/([^/]+)').firstMatch(url);
      if (roomIdMatch != null) {
        final roomId = roomIdMatch.group(1);
        connect(roomId!);
      }
    }
  }

  void _handleDisconnect() {
    print('WebSocket disconnected');
    // Try to reconnect after delay
    Future.delayed(const Duration(seconds: 5), () {
      if (_channel != null) {
        final url = _channel!.toString();
        final roomIdMatch = RegExp(r'chat/([^/]+)').firstMatch(url);
        if (roomIdMatch != null) {
          final roomId = roomIdMatch.group(1);
          connect(roomId!);
        }
      }
    });
  }

  bool get isConnected => _channel != null;
}
