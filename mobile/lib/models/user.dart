import 'dart:convert';

/// Represents the authenticated user, decoded from a JWT access token.
class User {
  final String id;
  final String? email;
  final String? displayName;
  final String role;
  final String tenantId;

  const User({
    required this.id,
    this.email,
    this.displayName,
    required this.role,
    required this.tenantId,
  });

  /// Decode a JWT access token payload to extract user information.
  ///
  /// JWT structure: header.payload.signature
  /// The payload is base64url-encoded JSON containing:
  ///   sub (user_id), tenant_id, role, type, exp, iat
  factory User.fromJwt(String jwt) {
    final parts = jwt.split('.');
    if (parts.length != 3) {
      throw const FormatException('Invalid JWT: expected 3 parts');
    }

    final payload = parts[1];
    // Base64url decode — pad to multiple of 4
    final normalized = base64Url.normalize(payload);
    final decoded = utf8.decode(base64Url.decode(normalized));
    final claims = jsonDecode(decoded) as Map<String, dynamic>;

    return User(
      id: claims['sub'] as String,
      email: claims['email'] as String?,
      displayName: claims['display_name'] as String?,
      role: claims['role'] as String? ?? 'user',
      tenantId: claims['tenant_id'] as String,
    );
  }

  /// Check whether the JWT token is expired.
  static bool isTokenExpired(String jwt, {int thresholdSeconds = 0}) {
    try {
      final parts = jwt.split('.');
      if (parts.length != 3) return true;

      final normalized = base64Url.normalize(parts[1]);
      final decoded = utf8.decode(base64Url.decode(normalized));
      final claims = jsonDecode(decoded) as Map<String, dynamic>;

      final exp = claims['exp'] as int?;
      if (exp == null) return true;

      final expiryTime = DateTime.fromMillisecondsSinceEpoch(exp * 1000);
      final now = DateTime.now().add(Duration(seconds: thresholdSeconds));
      return now.isAfter(expiryTime);
    } catch (_) {
      return true;
    }
  }

  User copyWith({
    String? id,
    String? email,
    String? displayName,
    String? role,
    String? tenantId,
  }) =>
      User(
        id: id ?? this.id,
        email: email ?? this.email,
        displayName: displayName ?? this.displayName,
        role: role ?? this.role,
        tenantId: tenantId ?? this.tenantId,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is User &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          email == other.email &&
          displayName == other.displayName &&
          role == other.role &&
          tenantId == other.tenantId;

  @override
  int get hashCode => Object.hash(id, email, displayName, role, tenantId);

  @override
  String toString() => 'User(id: $id, email: $email, role: $role)';
}
