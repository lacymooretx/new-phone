/// SMS-related data models.

/// Represents an SMS conversation between a local DID and a remote number.
class SmsConversation {
  final String id;
  final String tenantId;
  final String didNumber;
  final String remoteNumber;
  final String state;
  final int unreadCount;
  final String? lastMessagePreview;
  final DateTime? lastMessageAt;
  final String? assignedToName;

  const SmsConversation({
    required this.id,
    required this.tenantId,
    required this.didNumber,
    required this.remoteNumber,
    this.state = 'open',
    this.unreadCount = 0,
    this.lastMessagePreview,
    this.lastMessageAt,
    this.assignedToName,
  });

  factory SmsConversation.fromJson(Map<String, dynamic> json) =>
      SmsConversation(
        id: json['id'] as String,
        tenantId: json['tenant_id'] as String,
        didNumber: json['did_number'] as String? ?? '',
        remoteNumber: json['remote_number'] as String,
        state: json['state'] as String? ?? 'open',
        unreadCount: json['unread_count'] as int? ?? 0,
        lastMessagePreview: json['last_message_preview'] as String?,
        lastMessageAt: json['last_message_at'] != null
            ? DateTime.parse(json['last_message_at'] as String)
            : null,
        assignedToName: json['assigned_to_name'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'tenant_id': tenantId,
        'did_number': didNumber,
        'remote_number': remoteNumber,
        'state': state,
        'unread_count': unreadCount,
        'last_message_preview': lastMessagePreview,
        'last_message_at': lastMessageAt?.toIso8601String(),
        'assigned_to_name': assignedToName,
      };

  SmsConversation copyWith({
    String? id,
    String? tenantId,
    String? didNumber,
    String? remoteNumber,
    String? state,
    int? unreadCount,
    String? lastMessagePreview,
    DateTime? lastMessageAt,
    String? assignedToName,
    bool clearAssignedToName = false,
  }) =>
      SmsConversation(
        id: id ?? this.id,
        tenantId: tenantId ?? this.tenantId,
        didNumber: didNumber ?? this.didNumber,
        remoteNumber: remoteNumber ?? this.remoteNumber,
        state: state ?? this.state,
        unreadCount: unreadCount ?? this.unreadCount,
        lastMessagePreview: lastMessagePreview ?? this.lastMessagePreview,
        lastMessageAt: lastMessageAt ?? this.lastMessageAt,
        assignedToName:
            clearAssignedToName ? null : (assignedToName ?? this.assignedToName),
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SmsConversation &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'SmsConversation(id: $id, remote: $remoteNumber, unread: $unreadCount)';
}

/// Represents a single SMS message within a conversation.
class SmsMessage {
  final String id;
  final String conversationId;
  final String direction;
  final String fromNumber;
  final String toNumber;
  final String body;
  final String status;
  final DateTime createdAt;
  final String? sentByName;

  const SmsMessage({
    required this.id,
    required this.conversationId,
    required this.direction,
    required this.fromNumber,
    required this.toNumber,
    required this.body,
    this.status = 'sent',
    required this.createdAt,
    this.sentByName,
  });

  factory SmsMessage.fromJson(Map<String, dynamic> json) => SmsMessage(
        id: json['id'] as String,
        conversationId: json['conversation_id'] as String,
        direction: json['direction'] as String,
        fromNumber: json['from_number'] as String,
        toNumber: json['to_number'] as String,
        body: json['body'] as String,
        status: json['status'] as String? ?? 'sent',
        createdAt: DateTime.parse(json['created_at'] as String),
        sentByName: json['sent_by_name'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'conversation_id': conversationId,
        'direction': direction,
        'from_number': fromNumber,
        'to_number': toNumber,
        'body': body,
        'status': status,
        'created_at': createdAt.toIso8601String(),
        'sent_by_name': sentByName,
      };

  SmsMessage copyWith({
    String? id,
    String? conversationId,
    String? direction,
    String? fromNumber,
    String? toNumber,
    String? body,
    String? status,
    DateTime? createdAt,
    String? sentByName,
    bool clearSentByName = false,
  }) =>
      SmsMessage(
        id: id ?? this.id,
        conversationId: conversationId ?? this.conversationId,
        direction: direction ?? this.direction,
        fromNumber: fromNumber ?? this.fromNumber,
        toNumber: toNumber ?? this.toNumber,
        body: body ?? this.body,
        status: status ?? this.status,
        createdAt: createdAt ?? this.createdAt,
        sentByName:
            clearSentByName ? null : (sentByName ?? this.sentByName),
      );

  /// Whether this message was sent outbound.
  bool get isOutbound => direction == 'outbound';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SmsMessage &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'SmsMessage(id: $id, direction: $direction, status: $status)';
}
