import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

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

      if (user == null) {
        debugPrint('⚠️ FirebaseAuthInterceptor: no signed-in Firebase user.');
        handler.next(options);
        return;
      }

      // Prefer cached token first. Force-refresh only as fallback.
      String? idToken = await user.getIdToken();
      idToken ??= await user.getIdToken(true);

      if (idToken != null && idToken.isNotEmpty) {
        debugPrint('FIREBASE_ID_TOKEN: $idToken');
        options.headers['Authorization'] = 'Bearer $idToken';
      } else {
        debugPrint('⚠️ FirebaseAuthInterceptor: token fetch returned empty.');
      }
    } on FirebaseAuthException catch (e) {
      // If token fetch fails, let the request proceed without the token.
      // The backend will return 401 and the app can handle re-auth.
      debugPrint(
        '⚠️ FirebaseAuthInterceptor: FirebaseAuthException '
        '${e.code} — ${e.message}',
      );
    } catch (e) {
      debugPrint('⚠️ FirebaseAuthInterceptor: failed to get ID token — $e');
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
