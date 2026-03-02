/// Contact / extension directory model.

/// Represents a contact from the company directory (extensions list).
class Contact {
  final String id;
  final String extensionNumber;
  final String displayName;
  final String? email;
  final String? avatar;
  final bool isOnline;
  final ContactStatus status;

  const Contact({
    required this.id,
    required this.extensionNumber,
    required this.displayName,
    this.email,
    this.avatar,
    this.isOnline = false,
    this.status = ContactStatus.offline,
  });

  factory Contact.fromJson(Map<String, dynamic> json) => Contact(
        id: json['id'] as String,
        extensionNumber: json['extension_number'] as String? ??
            json['number'] as String? ??
            '',
        displayName: json['display_name'] as String? ??
            json['name'] as String? ??
            json['extension_number'] as String? ??
            'Unknown',
        email: json['email'] as String?,
        avatar: json['avatar'] as String?,
        isOnline: json['is_online'] as bool? ?? false,
        status: ContactStatus.fromString(
          json['status'] as String? ?? 'offline',
        ),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'extension_number': extensionNumber,
        'display_name': displayName,
        'email': email,
        'avatar': avatar,
        'is_online': isOnline,
        'status': status.name,
      };

  Contact copyWith({
    String? id,
    String? extensionNumber,
    String? displayName,
    String? email,
    String? avatar,
    bool? isOnline,
    ContactStatus? status,
  }) =>
      Contact(
        id: id ?? this.id,
        extensionNumber: extensionNumber ?? this.extensionNumber,
        displayName: displayName ?? this.displayName,
        email: email ?? this.email,
        avatar: avatar ?? this.avatar,
        isOnline: isOnline ?? this.isOnline,
        status: status ?? this.status,
      );

  /// Initials derived from the display name for avatar fallback.
  String get initials {
    final parts = displayName.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    if (displayName.isNotEmpty) {
      return displayName[0].toUpperCase();
    }
    return '?';
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Contact && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'Contact(id: $id, ext: $extensionNumber, name: $displayName)';
}

/// Online/presence status for a contact.
enum ContactStatus {
  available,
  away,
  dnd,
  offline;

  static ContactStatus fromString(String value) => switch (value) {
        'available' => ContactStatus.available,
        'away' => ContactStatus.away,
        'dnd' => ContactStatus.dnd,
        'busy' => ContactStatus.dnd,
        _ => ContactStatus.offline,
      };

  String get label => switch (this) {
        ContactStatus.available => 'Available',
        ContactStatus.away => 'Away',
        ContactStatus.dnd => 'Do Not Disturb',
        ContactStatus.offline => 'Offline',
      };
}
