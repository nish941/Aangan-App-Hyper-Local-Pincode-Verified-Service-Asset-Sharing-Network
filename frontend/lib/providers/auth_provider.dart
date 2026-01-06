import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:aangan_app/services/api_service.dart';
import 'package:aangan_app/models/user_model.dart';

class AuthProvider with ChangeNotifier {
  User? _user;
  String? _accessToken;
  String? _refreshToken;
  bool _isLoading = false;
  bool _isAuthenticated = false;

  User? get user => _user;
  String? get accessToken => _accessToken;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _isAuthenticated;

  Future<void> checkLoginStatus() async {
    _isLoading = true;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access_token');
      
      if (token != null) {
        _accessToken = token;
        _refreshToken = prefs.getString('refresh_token');
        
        // Try to get user profile
        final api = ApiService();
        await api.initialize();
        
        final response = await api.getUserProfile();
        if (response.statusCode == 200) {
          _user = User.fromJson(response.data);
          _isAuthenticated = true;
        } else {
          // Token might be invalid, clear it
          await logout();
        }
      }
    } catch (e) {
      print('Error checking login status: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String phoneNumber, String password) async {
    _isLoading = true;
    notifyListeners();

    try {
      final api = ApiService();
      await api.initialize();
      
      final response = await api.login(phoneNumber, password);
      
      if (response.statusCode == 200) {
        final data = response.data;
        
        // Save tokens
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', data['access']);
        await prefs.setString('refresh_token', data['refresh']);
        
        _accessToken = data['access'];
        _refreshToken = data['refresh'];
        
        // Save user data
        _user = User.fromJson(data['user']);
        _isAuthenticated = true;
        
        return true;
      }
    } catch (e) {
      print('Login error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
    
    return false;
  }

  Future<bool> register(Map<String, dynamic> data) async {
    _isLoading = true;
    notifyListeners();

    try {
      final api = ApiService();
      await api.initialize();
      
      final response = await api.register(data);
      
      if (response.statusCode == 201) {
        final responseData = response.data;
        
        // Save tokens
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('access_token', responseData['access']);
        await prefs.setString('refresh_token', responseData['refresh']);
        
        _accessToken = responseData['access'];
        _refreshToken = responseData['refresh'];
        
        // Save user data
        _user = User.fromJson(responseData['user']);
        _isAuthenticated = true;
        
        return true;
      }
    } catch (e) {
      print('Registration error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
    
    return false;
  }

  Future<void> logout() async {
    try {
      final api = ApiService();
      await api.initialize();
      await api.logout();
    } catch (e) {
      print('Logout error: $e');
    }
    
    // Clear local data
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('refresh_token');
    
    _user = null;
    _accessToken = null;
    _refreshToken = null;
    _isAuthenticated = false;
    
    notifyListeners();
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    _isLoading = true;
    notifyListeners();

    try {
      final api = ApiService();
      await api.initialize();
      
      final response = await api.updateUserProfile(data);
      
      if (response.statusCode == 200) {
        _user = User.fromJson(response.data);
      }
    } catch (e) {
      print('Update profile error: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
