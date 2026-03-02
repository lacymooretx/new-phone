/// Authentication-related data models.

/// Request body for POST /api/v1/auth/login.
class LoginRequest {
  final String email;
  final String password;

  const LoginRequest({
    required this.email,
    required this.password,
  });

  Map<String, dynamic> toJson() => {
        'email': email,
        'password': password,
      };
}

/// Request body for POST /api/v1/auth/mfa/challenge.
class MfaRequest {
  final String sessionToken;
  final String code;

  const MfaRequest({
    required this.sessionToken,
    required this.code,
  });

  Map<String, dynamic> toJson() => {
        'session_token': sessionToken,
        'code': code,
      };
}

/// Holds an access/refresh token pair.
class TokenPair {
  final String accessToken;
  final String refreshToken;
  final String tokenType;

  const TokenPair({
    required this.accessToken,
    required this.refreshToken,
    this.tokenType = 'bearer',
  });

  factory TokenPair.fromJson(Map<String, dynamic> json) => TokenPair(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
        tokenType: json['token_type'] as String? ?? 'bearer',
      );

  Map<String, dynamic> toJson() => {
        'access_token': accessToken,
        'refresh_token': refreshToken,
        'token_type': tokenType,
      };
}

/// Result of a login attempt. Either success with tokens or MFA required.
sealed class LoginResult {
  const LoginResult();
}

class LoginSuccess extends LoginResult {
  final TokenPair tokens;

  const LoginSuccess({required this.tokens});
}

class LoginMfaRequired extends LoginResult {
  final String mfaSessionToken;

  const LoginMfaRequired({required this.mfaSessionToken});
}
