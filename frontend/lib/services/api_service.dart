import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:aangan_app/utils/constants.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  late Dio _dio;
  String? _accessToken;

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString('access_token');

    _dio = Dio(BaseOptions(
      baseUrl: ApiConstants.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        options.headers['Content-Type'] = 'application/json';
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Token expired, try to refresh
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry the request
            final request = error.requestOptions;
            request.headers['Authorization'] = 'Bearer $_accessToken';
            return handler.resolve(await _dio.fetch(request));
          }
        }
        return handler.next(error);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final refreshToken = prefs.getString('refresh_token');
      
      if (refreshToken == null) return false;

      final response = await Dio().post(
        '${ApiConstants.baseUrl}/api/token/refresh/',
        data: {'refresh': refreshToken},
      );

      if (response.statusCode == 200) {
        _accessToken = response.data['access'];
        await prefs.setString('access_token', _accessToken!);
        return true;
      }
    } catch (e) {
      print('Token refresh failed: $e');
    }
    return false;
  }

  // Auth endpoints
  Future<Response> login(String phoneNumber, String password) async {
    return await _dio.post(
      '/api/auth/login/',
      data: {'phone_number': phoneNumber, 'password': password},
    );
  }

  Future<Response> register(Map<String, dynamic> data) async {
    return await _dio.post(
      '/api/auth/register/',
      data: data,
    );
  }

  Future<Response> logout() async {
    return await _dio.post('/api/auth/logout/');
  }

  // Services endpoints
  Future<Response> getServices({
    String? pincode,
    String? category,
    String? serviceType,
    double? minPrice,
    double? maxPrice,
    String? search,
    int page = 1,
  }) async {
    final params = {
      'pincode': pincode,
      'category': category,
      'service_type': serviceType,
      'min_price': minPrice,
      'max_price': maxPrice,
      'search': search,
      'page': page,
    };
    
    params.removeWhere((key, value) => value == null);
    
    return await _dio.get('/api/services/', queryParameters: params);
  }

  Future<Response> getNearbyServices() async {
    return await _dio.get('/api/services/nearby/');
  }

  Future<Response> createService(Map<String, dynamic> data) async {
    return await _dio.post('/api/services/', data: data);
  }

  Future<Response> bookService(String serviceId, Map<String, dynamic> data) async {
    return await _dio.post('/api/services/$serviceId/book/', data: data);
  }

  // Bookings endpoints
  Future<Response> getBookings({String? status}) async {
    final params = {'status': status};
    params.removeWhere((key, value) => value == null);
    
    return await _dio.get('/api/bookings/', queryParameters: params);
  }

  Future<Response> confirmBooking(String bookingId) async {
    return await _dio.post('/api/bookings/$bookingId/confirm/');
  }

  Future<Response> completeBooking(String bookingId) async {
    return await _dio.post('/api/bookings/$bookingId/complete/');
  }

  Future<Response> reviewBooking(String bookingId, double rating, String? comment) async {
    return await _dio.post(
      '/api/bookings/$bookingId/review/',
      data: {'rating': rating, 'comment': comment},
    );
  }

  // Chat endpoints
  Future<Response> getChatRooms() async {
    return await _dio.get('/api/chat/rooms/');
  }

  Future<Response> startChat(String userId) async {
    return await _dio.post('/api/chat/start_chat/', data: {'user_id': userId});
  }

  // User endpoints
  Future<Response> getUserProfile() async {
    return await _dio.get('/api/users/profile/');
  }

  Future<Response> updateUserProfile(Map<String, dynamic> data) async {
    return await _dio.patch('/api/users/profile/', data: data);
  }

  Future<Response> uploadVerificationDocuments(
    String idFrontPath,
    String idBackPath,
    String addressProofPath,
  ) async {
    final formData = FormData.fromMap({
      'id_proof_front': await MultipartFile.fromFile(idFrontPath),
      'id_proof_back': await MultipartFile.fromFile(idBackPath),
      'address_proof': await MultipartFile.fromFile(addressProofPath),
    });
    
    return await _dio.post('/api/users/verify/', data: formData);
  }
}
