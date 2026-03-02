/// Call Detail Record (CDR) data models.

/// Direction of a call.
enum CdrDirection {
  inbound,
  outbound,
  internal;

  static CdrDirection fromString(String value) => switch (value) {
        'inbound' => CdrDirection.inbound,
        'outbound' => CdrDirection.outbound,
        'internal' => CdrDirection.internal,
        _ => CdrDirection.inbound,
      };
}

/// Disposition (outcome) of a call.
enum CdrDisposition {
  answered,
  missed,
  voicemail,
  busy,
  failed;

  static CdrDisposition fromString(String value) => switch (value) {
        'answered' => CdrDisposition.answered,
        'missed' => CdrDisposition.missed,
        'voicemail' => CdrDisposition.voicemail,
        'busy' => CdrDisposition.busy,
        'failed' => CdrDisposition.failed,
        _ => CdrDisposition.missed,
      };
}

/// Represents a single Call Detail Record.
class Cdr {
  final String id;
  final String tenantId;
  final String callId;
  final CdrDirection direction;
  final String callerNumber;
  final String? callerName;
  final String calledNumber;
  final CdrDisposition disposition;
  final int duration;
  final int ringDuration;
  final DateTime startTime;
  final DateTime? answerTime;
  final DateTime endTime;
  final bool hasRecording;

  const Cdr({
    required this.id,
    required this.tenantId,
    required this.callId,
    required this.direction,
    required this.callerNumber,
    this.callerName,
    required this.calledNumber,
    required this.disposition,
    required this.duration,
    this.ringDuration = 0,
    required this.startTime,
    this.answerTime,
    required this.endTime,
    this.hasRecording = false,
  });

  factory Cdr.fromJson(Map<String, dynamic> json) => Cdr(
        id: json['id'] as String,
        tenantId: json['tenant_id'] as String,
        callId: json['call_id'] as String,
        direction: CdrDirection.fromString(json['direction'] as String),
        callerNumber: json['caller_number'] as String,
        callerName: json['caller_name'] as String?,
        calledNumber: json['called_number'] as String,
        disposition: CdrDisposition.fromString(json['disposition'] as String),
        duration: json['duration'] as int? ?? 0,
        ringDuration: json['ring_duration'] as int? ?? 0,
        startTime: DateTime.parse(json['start_time'] as String),
        answerTime: json['answer_time'] != null
            ? DateTime.parse(json['answer_time'] as String)
            : null,
        endTime: DateTime.parse(json['end_time'] as String),
        hasRecording: json['has_recording'] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'tenant_id': tenantId,
        'call_id': callId,
        'direction': direction.name,
        'caller_number': callerNumber,
        'caller_name': callerName,
        'called_number': calledNumber,
        'disposition': disposition.name,
        'duration': duration,
        'ring_duration': ringDuration,
        'start_time': startTime.toIso8601String(),
        'answer_time': answerTime?.toIso8601String(),
        'end_time': endTime.toIso8601String(),
        'has_recording': hasRecording,
      };

  /// The display name/number for the other party, depending on direction.
  String get remotePartyLabel {
    if (direction == CdrDirection.outbound) {
      return calledNumber;
    }
    return callerName ?? callerNumber;
  }

  /// The remote party number.
  String get remotePartyNumber {
    if (direction == CdrDirection.outbound) {
      return calledNumber;
    }
    return callerNumber;
  }

  /// Duration formatted as mm:ss or h:mm:ss.
  String get formattedDuration {
    final hours = duration ~/ 3600;
    final minutes = (duration % 3600) ~/ 60;
    final seconds = duration % 60;

    if (hours > 0) {
      return '$hours:${minutes.toString().padLeft(2, '0')}:'
          '${seconds.toString().padLeft(2, '0')}';
    }
    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  /// Whether this call was missed (not answered by the user).
  bool get isMissed =>
      disposition == CdrDisposition.missed ||
      disposition == CdrDisposition.failed;

  Cdr copyWith({
    String? id,
    String? tenantId,
    String? callId,
    CdrDirection? direction,
    String? callerNumber,
    String? callerName,
    String? calledNumber,
    CdrDisposition? disposition,
    int? duration,
    int? ringDuration,
    DateTime? startTime,
    DateTime? answerTime,
    DateTime? endTime,
    bool? hasRecording,
  }) =>
      Cdr(
        id: id ?? this.id,
        tenantId: tenantId ?? this.tenantId,
        callId: callId ?? this.callId,
        direction: direction ?? this.direction,
        callerNumber: callerNumber ?? this.callerNumber,
        callerName: callerName ?? this.callerName,
        calledNumber: calledNumber ?? this.calledNumber,
        disposition: disposition ?? this.disposition,
        duration: duration ?? this.duration,
        ringDuration: ringDuration ?? this.ringDuration,
        startTime: startTime ?? this.startTime,
        answerTime: answerTime ?? this.answerTime,
        endTime: endTime ?? this.endTime,
        hasRecording: hasRecording ?? this.hasRecording,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Cdr && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'Cdr(id: $id, direction: $direction, '
      'caller: $callerNumber, called: $calledNumber)';
}

/// A paginated page of CDR records.
class CdrPage {
  final List<Cdr> items;
  final int total;
  final int page;
  final int pageSize;

  const CdrPage({
    required this.items,
    required this.total,
    this.page = 1,
    this.pageSize = 50,
  });

  factory CdrPage.fromJson(Map<String, dynamic> json) => CdrPage(
        items: (json['items'] as List<dynamic>)
            .map((e) => Cdr.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: json['total'] as int,
        page: json['page'] as int? ?? 1,
        pageSize: json['page_size'] as int? ?? 50,
      );

  /// Whether there are more pages available.
  bool get hasMore => page * pageSize < total;

  /// The total number of pages.
  int get totalPages => (total / pageSize).ceil();

  @override
  String toString() => 'CdrPage(items: ${items.length}, '
      'total: $total, page: $page/$totalPages)';
}
