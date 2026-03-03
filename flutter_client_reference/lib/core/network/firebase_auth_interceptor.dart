import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

/// Dio [Interceptor] that automatically attaches the current Firebase
/// user's ID token to every outgoing request.
///
/// Usage:
/// ```dart
/// final dio = Dio();
/// dio.interceptors.add(FirebaseAuthInterceptor());
/// ```
class FirebaseAuthInterceptor extends Interceptor {
  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    try {
      final user = FirebaseAuth.instance.currentUser;

      if (user != null) {
        // Force-refresh if the token is about to expire
        final idToken = await user.getIdToken(true);
        options.headers['Authorization'] = 'Bearer $idToken';
      }
    } catch (e) {
      // If token fetch fails, let the request proceed without the token.
      // The backend will return 401 and the app can handle re-auth.
      print('⚠️ FirebaseAuthInterceptor: failed to get ID token — $e');
    }

    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.response?.statusCode == 401) {
      // Token expired or invalid — the app should navigate to login.
      print('🔒 Received 401 — user should re-authenticate.');
    }

    handler.next(err);
  }
}
