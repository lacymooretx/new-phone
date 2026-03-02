/// Voicemail-related data models.

/// Represents a voicemail box belonging to an extension/user.
class VoicemailBox {
  final String id;
  final String tenantId;
  final String boxNumber;
  final String name;
  final String? email;
  final bool isActive;
  final int messageCount;
  final int unreadCount;

  const VoicemailBox({
    required this.id,
    required this.tenantId,
    required this.boxNumber,
    required this.name,
    this.email,
    this.isActive = true,
    this.messageCount = 0,
    this.unreadCount = 0,
  });

  factory VoicemailBox.fromJson(Map<String, dynamic> json) => VoicemailBox(
        id: json['id'] as String,
        tenantId: json['tenant_id'] as String,
        boxNumber: json['box_number'] as String,
        name: json['name'] as String,
        email: json['email'] as String?,
        isActive: json['is_active'] as bool? ?? true,
        messageCount: json['message_count'] as int? ?? 0,
        unreadCount: json['unread_count'] as int? ?? 0,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'tenant_id': tenantId,
        'box_number': boxNumber,
        'name': name,
        'email': email,
        'is_active': isActive,
        'message_count': messageCount,
        'unread_count': unreadCount,
      };

  VoicemailBox copyWith({
    String? id,
    String? tenantId,
    String? boxNumber,
    String? name,
    String? email,
    bool? isActive,
    int? messageCount,
    int? unreadCount,
  }) =>
      VoicemailBox(
        id: id ?? this.id,
        tenantId: tenantId ?? this.tenantId,
        boxNumber: boxNumber ?? this.boxNumber,
        name: name ?? this.name,
        email: email ?? this.email,
        isActive: isActive ?? this.isActive,
        messageCount: messageCount ?? this.messageCount,
        unreadCount: unreadCount ?? this.unreadCount,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is VoicemailBox &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'VoicemailBox(id: $id, boxNumber: $boxNumber, name: $name)';
}

/// Represents a single voicemail message.
class VoicemailMessage {
  final String id;
  final String boxId;
  final String callerNumber;
  final String? callerName;
  final int duration;
  final DateTime createdAt;
  final bool isListened;
  final bool hasTranscription;
  final String? transcription;
  final String? recordingId;

  const VoicemailMessage({
    required this.id,
    required this.boxId,
    required this.callerNumber,
    this.callerName,
    required this.duration,
    required this.createdAt,
    this.isListened = false,
    this.hasTranscription = false,
    this.transcription,
    this.recordingId,
  });

  factory VoicemailMessage.fromJson(Map<String, dynamic> json) =>
      VoicemailMessage(
        id: json['id'] as String,
        boxId: json['box_id'] as String,
        callerNumber: json['caller_number'] as String,
        callerName: json['caller_name'] as String?,
        duration: json['duration'] as int,
        createdAt: DateTime.parse(json['created_at'] as String),
        isListened: json['is_listened'] as bool? ?? false,
        hasTranscription: json['has_transcription'] as bool? ?? false,
        transcription: json['transcription'] as String?,
        recordingId: json['recording_id'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'box_id': boxId,
        'caller_number': callerNumber,
        'caller_name': callerName,
        'duration': duration,
        'created_at': createdAt.toIso8601String(),
        'is_listened': isListened,
        'has_transcription': hasTranscription,
        'transcription': transcription,
        'recording_id': recordingId,
      };

  VoicemailMessage copyWith({
    String? id,
    String? boxId,
    String? callerNumber,
    String? callerName,
    int? duration,
    DateTime? createdAt,
    bool? isListened,
    bool? hasTranscription,
    String? transcription,
    String? recordingId,
  }) =>
      VoicemailMessage(
        id: id ?? this.id,
        boxId: boxId ?? this.boxId,
        callerNumber: callerNumber ?? this.callerNumber,
        callerName: callerName ?? this.callerName,
        duration: duration ?? this.duration,
        createdAt: createdAt ?? this.createdAt,
        isListened: isListened ?? this.isListened,
        hasTranscription: hasTranscription ?? this.hasTranscription,
        transcription: transcription ?? this.transcription,
        recordingId: recordingId ?? this.recordingId,
      );

  /// Human-readable caller label: name if available, otherwise number.
  String get callerLabel => callerName ?? callerNumber;

  /// Duration formatted as mm:ss.
  String get formattedDuration {
    final minutes = duration ~/ 60;
    final seconds = duration % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is VoicemailMessage &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'VoicemailMessage(id: $id, caller: $callerLabel, duration: $duration)';
}
