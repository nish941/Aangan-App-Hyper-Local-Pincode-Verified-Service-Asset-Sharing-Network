import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:aangan_app/providers/auth_provider.dart';
import 'package:aangan_app/providers/location_provider.dart';
import 'package:aangan_app/providers/chat_provider.dart';
import 'package:aangan_app/screens/auth/login_screen.dart';
import 'package:aangan_app/screens/home/home_screen.dart';
import 'package:aangan_app/utils/theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AanganApp());
}

class AanganApp extends StatelessWidget {
  const AanganApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => LocationProvider()),
        ChangeNotifierProvider(create: (_) => ChatProvider()),
      ],
      child: MaterialApp(
        title: 'Aangan',
        theme: AppTheme.lightTheme,
        darkTheme: AppTheme.darkTheme,
        debugShowCheckedModeBanner: false,
        home: const AppWrapper(),
      ),
    );
  }
}

class AppWrapper extends StatefulWidget {
  const AppWrapper({super.key});

  @override
  State<AppWrapper> createState() => _AppWrapperState();
}

class _AppWrapperState extends State<AppWrapper> {
  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final locationProvider = Provider.of<LocationProvider>(context, listen: false);
    
    // Check if user is logged in
    await authProvider.checkLoginStatus();
    
    // Request location permission and get current location
    await locationProvider.requestPermission();
    await locationProvider.getCurrentLocation();
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final locationProvider = Provider.of<LocationProvider>(context);

    // Show loading screen while initializing
    if (authProvider.isLoading || locationProvider.isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    // Redirect based on authentication status
    return authProvider.isAuthenticated ? const HomeScreen() : const LoginScreen();
  }
}
