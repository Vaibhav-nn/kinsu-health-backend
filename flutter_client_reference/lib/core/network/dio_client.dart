import 'package:dio/dio.dart';
import 'firebase_auth_interceptor.dart';

/// Factory class that creates and configures the [Dio] HTTP client
/// for communicating with the Kinsu Health backend.
///
/// Usage:
/// ```dart
/// final dio = DioClient.create(baseUrl: 'https://your-api.com');
/// final response = await dio.post('/api/v1/auth/login');
/// ```
class DioClient {
  DioClient._(); // Prevent instantiation

  /// Create a fully configured [Dio] instance.
  ///
  /// [baseUrl] — The backend API base URL (e.g. `http://10.0.2.2:8000`
  /// for Android emulator or `http://localhost:8000` for iOS simulator).
  static Dio create({
    required String baseUrl,
    Duration connectTimeout = const Duration(seconds: 15),
    Duration receiveTimeout = const Duration(seconds: 15),
  }) {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: connectTimeout,
        receiveTimeout: receiveTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // ── Interceptors (order matters) ────────────────────
    // 1. Firebase Auth — attaches Bearer token to every request
    dio.interceptors.add(FirebaseAuthInterceptor());

    // 2. Logging — useful during development
    dio.interceptors.add(
      LogInterceptor(
        requestBody: true,
        responseBody: true,
        logPrint: (obj) => print('🌐 DIO: $obj'),
      ),
    );

    return dio;
  }
}
