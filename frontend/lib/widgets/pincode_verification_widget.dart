import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:aangan_app/providers/location_provider.dart';
import 'package:aangan_app/services/api_service.dart';

class PincodeVerificationWidget extends StatefulWidget {
  final Function(String)? onPincodeSelected;
  
  const PincodeVerificationWidget({
    super.key,
    this.onPincodeSelected,
  });

  @override
  State<PincodeVerificationWidget> createState() => _PincodeVerificationWidgetState();
}

class _PincodeVerificationWidgetState extends State<PincodeVerificationWidget> {
  final TextEditingController _pincodeController = TextEditingController();
  List<Map<String, dynamic>> _nearbyPincodes = [];
  bool _isLoading = false;
  String? _selectedPincode;

  @override
  void initState() {
    super.initState();
    _loadNearbyPincodes();
  }

  Future<void> _loadNearbyPincodes() async {
    setState(() => _isLoading = true);
    
    final locationProvider = Provider.of<LocationProvider>(context, listen: false);
    final currentLocation = locationProvider.currentLocation;
    
    if (currentLocation != null) {
      try {
        // In production, this would call your backend API
        // For now, simulate with dummy data
        await Future.delayed(const Duration(seconds: 1));
        
        setState(() {
          _nearbyPincodes = [
            {
              'pincode': '110001',
              'area_name': 'Connaught Place',
              'city': 'New Delhi',
              'state': 'Delhi',
              'distance_km': 0.5,
            },
            {
              'pincode': '110002',
              'area_name': 'Shivaji Stadium',
              'city': 'New Delhi',
              'state': 'Delhi',
              'distance_km': 0.8,
            },
            {
              'pincode': '110003',
              'area_name': 'Gole Market',
              'city': 'New Delhi',
              'state': 'Delhi',
              'distance_km': 1.2,
            },
          ];
          _isLoading = false;
        });
      } catch (e) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Select Your Pincode',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        
        const SizedBox(height: 10),
        
        Text(
          'Choose your hyper-local community (within 1.5 km radius)',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        
        const SizedBox(height: 20),
        
        // Search Pincode
        TextField(
          controller: _pincodeController,
          decoration: InputDecoration(
            labelText: 'Search Pincode',
            hintText: 'Enter 6-digit pincode',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: IconButton(
              icon: const Icon(Icons.check_circle),
              onPressed: _verifyPincode,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
            ),
          ),
          keyboardType: TextInputType.number,
          maxLength: 6,
        ),
        
        const SizedBox(height: 20),
        
        // Nearby Pincodes
        Text(
          'Nearby Pincodes',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        
        const SizedBox(height: 10),
        
        _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _nearbyPincodes.isEmpty
                ? const Text('No nearby pincodes found')
                : Column(
                    children: _nearbyPincodes.map((pincode) {
                      return Card(
                        margin: const EdgeInsets.only(bottom: 10),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: _selectedPincode == pincode['pincode']
                                ? Theme.of(context).colorScheme.primary
                                : Colors.grey[200],
                            child: Icon(
                              Icons.location_on,
                              color: _selectedPincode == pincode['pincode']
                                  ? Colors.white
                                  : Colors.grey[600],
                            ),
                          ),
                          title: Text(pincode['area_name']),
                          subtitle: Text(
                              '${pincode['pincode']} • ${pincode['distance_km']} km away'),
                          trailing: _selectedPincode == pincode['pincode']
                              ? Icon(
                                  Icons.check_circle,
                                  color: Theme.of(context).colorScheme.primary,
                                )
                              : null,
                          onTap: () {
                            setState(() {
                              _selectedPincode = pincode['pincode'];
                            });
                            widget.onPincodeSelected?.call(pincode['pincode']);
                          },
                        ),
                      );
                    }).toList(),
                  ),
        
        const SizedBox(height: 10),
        
        if (_selectedPincode != null)
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.green[50],
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.green[200]!),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.verified,
                  color: Colors.green[600],
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Selected: $_selectedPincode\nYou can only interact with users in this pincode',
                    style: TextStyle(
                      color: Colors.green[700],
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  void _verifyPincode() {
    final pincode = _pincodeController.text.trim();
    if (pincode.length == 6) {
      // Verify pincode with backend
      setState(() {
        _selectedPincode = pincode;
      });
      widget.onPincodeSelected?.call(pincode);
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Pincode $pincode selected'),
          backgroundColor: Colors.green,
        ),
      );
    }
  }

  @override
  void dispose() {
    _pincodeController.dispose();
    super.dispose();
  }
}
