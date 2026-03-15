import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'dart:io';

import '../main.dart' show DS;
import '../services/app_logger.dart';
import '../services/support_api_service.dart';

// ─────────────────────────────────────────────────────────────────────────────
// SupportPage — list of user tickets + create new ticket
// ─────────────────────────────────────────────────────────────────────────────

class SupportPage extends StatefulWidget {
  const SupportPage({super.key});

  @override
  State<SupportPage> createState() => _SupportPageState();
}

class _SupportPageState extends State<SupportPage> {
  List<SupportTicket> _tickets = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    final tickets = await SupportApiService.getTickets();
    if (mounted) setState(() { _tickets = tickets; _loading = false; });
  }

  void _openCreate() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const _CreateTicketPage()),
    );
    if (created == true) _load();
  }

  void _openDetail(SupportTicket ticket) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => _TicketDetailPage(ticket: ticket)),
    );
    _load();
  }

  static String _fmtDate(int ts) {
    if (ts == 0) return '—';
    final dt = DateTime.fromMillisecondsSinceEpoch(ts * 1000).toLocal();
    final day = dt.day.toString().padLeft(2, '0');
    final mon = dt.month.toString().padLeft(2, '0');
    final yr = dt.year.toString().substring(2);
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$day.$mon.$yr $h:$m';
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: DS.surface0,
      appBar: AppBar(
        backgroundColor: DS.surface1,
        title: const Text('Поддержка', style: TextStyle(color: DS.textPrimary, fontSize: 17)),
        iconTheme: const IconThemeData(color: DS.textPrimary),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: DS.textSecondary),
            onPressed: _load,
            tooltip: 'Обновить',
          ),
          IconButton(
            icon: const Icon(Icons.add_rounded, color: DS.violet),
            onPressed: _openCreate,
            tooltip: 'Новое обращение',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: DS.violet))
          : _error != null
              ? _ErrorView(message: _error!, onRetry: _load)
              : _tickets.isEmpty
                  ? _EmptyView(onNew: _openCreate)
                  : RefreshIndicator(
                      color: DS.violet,
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        itemCount: _tickets.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) {
                          final t = _tickets[i];
                          return _TicketCard(
                            ticket: t,
                            fmtDate: _fmtDate,
                            onTap: () => _openDetail(t),
                          );
                        },
                      ),
                    ),
      floatingActionButton: _tickets.isNotEmpty
          ? FloatingActionButton.extended(
              backgroundColor: DS.violet,
              foregroundColor: DS.textPrimary,
              icon: const Icon(Icons.add_rounded),
              label: const Text('Новое обращение'),
              onPressed: _openCreate,
            )
          : null,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Ticket card
// ─────────────────────────────────────────────────────────────────────────────

class _TicketCard extends StatelessWidget {
  final SupportTicket ticket;
  final String Function(int) fmtDate;
  final VoidCallback onTap;

  const _TicketCard({required this.ticket, required this.fmtDate, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surface1,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.border),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text(
                ticket.title,
                style: const TextStyle(color: DS.textPrimary, fontWeight: FontWeight.w600, fontSize: 14),
                maxLines: 2, overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: DS.surface2,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(ticket.statusLabel,
                  style: const TextStyle(fontSize: 11, color: DS.textSecondary)),
            ),
          ]),
          const SizedBox(height: 6),
          Text(
            '#${ticket.id} · ${fmtDate(ticket.updatedAt)}',
            style: const TextStyle(color: DS.textMuted, fontSize: 11),
          ),
        ]),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Empty state
// ─────────────────────────────────────────────────────────────────────────────

class _EmptyView extends StatelessWidget {
  final VoidCallback onNew;
  const _EmptyView({required this.onNew});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.support_agent_rounded, color: DS.textMuted, size: 56),
          const SizedBox(height: 16),
          const Text('Обращений пока нет',
              style: TextStyle(color: DS.textPrimary, fontSize: 17, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Создайте новое обращение\nи мы поможем вам.',
              textAlign: TextAlign.center,
              style: TextStyle(color: DS.textSecondary, fontSize: 14)),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(backgroundColor: DS.violet),
            onPressed: onNew,
            icon: const Icon(Icons.add_rounded, color: DS.textPrimary),
            label: const Text('Новое обращение',
                style: TextStyle(color: DS.textPrimary)),
          ),
        ]),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Error view
// ─────────────────────────────────────────────────────────────────────────────

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.error_outline_rounded, color: DS.rose, size: 48),
          const SizedBox(height: 12),
          Text(message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: DS.textSecondary, fontSize: 14)),
          const SizedBox(height: 16),
          TextButton(onPressed: onRetry, child: const Text('Повторить')),
        ]),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Create ticket page
// ─────────────────────────────────────────────────────────────────────────────

class _CreateTicketPage extends StatefulWidget {
  const _CreateTicketPage();

  @override
  State<_CreateTicketPage> createState() => _CreateTicketPageState();
}

class _CreateTicketPageState extends State<_CreateTicketPage> {
  final _titleCtrl = TextEditingController();
  final _msgCtrl = TextEditingController();
  bool _sending = false;
  bool _attachDiag = false;

  @override
  void dispose() {
    _titleCtrl.dispose();
    _msgCtrl.dispose();
    super.dispose();
  }

  Future<String> _collectDiagnostics() async {
    final info = StringBuffer();
    try {
      final plugin = DeviceInfoPlugin();
      if (Platform.isAndroid) {
        final d = await plugin.androidInfo;
        info.write('Platform: Android ${d.version.release} (SDK ${d.version.sdkInt})\n');
        info.write('Device: ${d.manufacturer} ${d.model}\n');
      } else if (Platform.isIOS) {
        final d = await plugin.iosInfo;
        info.write('Platform: iOS ${d.systemVersion}\n');
        info.write('Device: ${d.utsname.machine}\n');
      } else {
        info.write('Platform: ${Platform.operatingSystem}\n');
      }
    } catch (_) {
      info.write('Device info: unavailable\n');
    }

    // Append recent app logs (up to 200 entries)
    final entries = appLogger.logsNotifier.value;
    if (entries.isNotEmpty) {
      info.write('\n--- App Logs ---\n');
      final recent = entries.length > 200 ? entries.sublist(entries.length - 200) : entries;
      for (final e in recent) {
        info.write('${e.formatted}\n');
      }
    }

    return info.toString().trim();
  }

  Future<void> _send() async {
    final title = _titleCtrl.text.trim();
    final message = _msgCtrl.text.trim();

    if (title.isEmpty) {
      _snack('Укажите тему обращения');
      return;
    }
    if (message.isEmpty) {
      _snack('Опишите проблему');
      return;
    }

    setState(() => _sending = true);

    String? logs;
    if (_attachDiag) {
      logs = await _collectDiagnostics();
    }

    final ticket = await SupportApiService.createTicket(
      title: title,
      message: message,
      logs: logs,
    );
    if (!mounted) return;
    setState(() => _sending = false);

    if (ticket != null) {
      Navigator.pop(context, true);
    } else {
      _snack('Не удалось отправить обращение. Попробуйте позже.');
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: DS.surface0,
      appBar: AppBar(
        backgroundColor: DS.surface1,
        title: const Text('Новое обращение',
            style: TextStyle(color: DS.textPrimary, fontSize: 17)),
        iconTheme: const IconThemeData(color: DS.textPrimary),
        elevation: 0,
        actions: [
          TextButton(
            onPressed: _sending ? null : _send,
            child: _sending
                ? const SizedBox(
                    width: 18, height: 18,
                    child: CircularProgressIndicator(color: DS.violet, strokeWidth: 2))
                : const Text('Отправить',
                    style: TextStyle(color: DS.violet, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _label('Тема обращения'),
          const SizedBox(height: 6),
          _field(_titleCtrl, hint: 'Кратко опишите проблему', maxLines: 1),
          const SizedBox(height: 16),
          _label('Описание'),
          const SizedBox(height: 6),
          _field(_msgCtrl, hint: 'Подробно опишите ситуацию…', maxLines: 8),
          const SizedBox(height: 16),
          Container(
            decoration: BoxDecoration(
              color: DS.surface1,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: DS.border),
            ),
            child: SwitchListTile(
              dense: true,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
              title: const Text('Прикрепить диагностику',
                  style: TextStyle(color: DS.textPrimary, fontSize: 14)),
              subtitle: const Text('Платформа, модель устройства и логи приложения',
                  style: TextStyle(color: DS.textMuted, fontSize: 11)),
              value: _attachDiag,
              activeColor: DS.violet,
              onChanged: (v) => setState(() => _attachDiag = v),
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: DS.violet,
              minimumSize: const Size.fromHeight(48),
            ),
            onPressed: _sending ? null : _send,
            child: _sending
                ? const SizedBox(
                    width: 20, height: 20,
                    child: CircularProgressIndicator(color: DS.textPrimary, strokeWidth: 2))
                : const Text('Отправить обращение',
                    style: TextStyle(color: DS.textPrimary, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  Widget _label(String text) => Text(text,
      style: const TextStyle(color: DS.textSecondary, fontSize: 13, fontWeight: FontWeight.w500));

  Widget _field(TextEditingController ctrl, {required String hint, int maxLines = 1}) {
    return Container(
      decoration: BoxDecoration(
        color: DS.surface1,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.border),
      ),
      child: TextField(
        controller: ctrl,
        maxLines: maxLines,
        style: const TextStyle(color: DS.textPrimary, fontSize: 14),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: DS.textMuted),
          contentPadding: const EdgeInsets.all(14),
          border: InputBorder.none,
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Ticket detail page
// ─────────────────────────────────────────────────────────────────────────────

class _TicketDetailPage extends StatefulWidget {
  final SupportTicket ticket;
  const _TicketDetailPage({required this.ticket});

  @override
  State<_TicketDetailPage> createState() => _TicketDetailPageState();
}

class _TicketDetailPageState extends State<_TicketDetailPage> {
  SupportTicketDetail? _detail;
  bool _loading = true;
  final _replyCtrl = TextEditingController();
  bool _sending = false;
  final _scrollCtrl = ScrollController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _replyCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final detail = await SupportApiService.getTicket(widget.ticket.id);
    if (mounted) setState(() { _detail = detail; _loading = false; });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _reply() async {
    final text = _replyCtrl.text.trim();
    if (text.isEmpty) return;
    setState(() => _sending = true);
    final msg = await SupportApiService.replyToTicket(
        ticketId: widget.ticket.id, message: text);
    if (!mounted) return;
    setState(() => _sending = false);
    if (msg != null) {
      _replyCtrl.clear();
      await _load();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось отправить сообщение')));
    }
  }

  static String _fmtDate(int ts) {
    if (ts == 0) return '—';
    final dt = DateTime.fromMillisecondsSinceEpoch(ts * 1000).toLocal();
    final day = dt.day.toString().padLeft(2, '0');
    final mon = dt.month.toString().padLeft(2, '0');
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$day.$mon $h:$m';
  }

  @override
  Widget build(BuildContext context) {
    final d = _detail;
    final isClosed = widget.ticket.status == 'closed';

    return Scaffold(
      backgroundColor: DS.surface0,
      appBar: AppBar(
        backgroundColor: DS.surface1,
        title: Text(widget.ticket.title,
            style: const TextStyle(color: DS.textPrimary, fontSize: 16),
            overflow: TextOverflow.ellipsis),
        iconTheme: const IconThemeData(color: DS.textPrimary),
        elevation: 0,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Text(widget.ticket.statusLabel,
                  style: const TextStyle(color: DS.textSecondary, fontSize: 12)),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: DS.violet))
          : Column(children: [
              Expanded(
                child: d == null || d.messages.isEmpty
                    ? const Center(
                        child: Text('Нет сообщений',
                            style: TextStyle(color: DS.textMuted)))
                    : ListView.separated(
                        controller: _scrollCtrl,
                        padding: const EdgeInsets.all(16),
                        itemCount: d.messages.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _MessageBubble(
                          msg: d.messages[i],
                          fmtDate: _fmtDate,
                        ),
                      ),
              ),
              if (!isClosed)
                _ReplyBar(ctrl: _replyCtrl, sending: _sending, onSend: _reply),
              if (isClosed)
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  color: DS.surface1,
                  child: const Center(
                    child: Text('Тикет закрыт',
                        style: TextStyle(color: DS.textMuted, fontSize: 13)),
                  ),
                ),
            ]),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Message bubble
// ─────────────────────────────────────────────────────────────────────────────

class _MessageBubble extends StatelessWidget {
  final SupportTicketMessage msg;
  final String Function(int) fmtDate;

  const _MessageBubble({required this.msg, required this.fmtDate});

  @override
  Widget build(BuildContext context) {
    final isAdmin = msg.isFromAdmin;
    return Align(
      alignment: isAdmin ? Alignment.centerLeft : Alignment.centerRight,
      child: GestureDetector(
        onLongPress: () {
          Clipboard.setData(ClipboardData(text: msg.messageText));
          ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Скопировано'), duration: Duration(seconds: 1)));
        },
        child: Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: isAdmin ? DS.surface2 : DS.violet.withOpacity(0.85),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(12),
              topRight: const Radius.circular(12),
              bottomLeft: Radius.circular(isAdmin ? 2 : 12),
              bottomRight: Radius.circular(isAdmin ? 12 : 2),
            ),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (isAdmin)
              const Text('Поддержка',
                  style: TextStyle(color: DS.violet, fontSize: 11, fontWeight: FontWeight.w600)),
            Text(msg.messageText,
                style: TextStyle(
                    color: isAdmin ? DS.textPrimary : Colors.white, fontSize: 14)),
            if (msg.hasMedia) ...[
              const SizedBox(height: 6),
              Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.attach_file_rounded,
                    size: 13,
                    color: isAdmin ? DS.textMuted : Colors.white70),
                const SizedBox(width: 4),
                Text('Логи прикреплены',
                    style: TextStyle(
                        color: isAdmin ? DS.textMuted : Colors.white70,
                        fontSize: 11,
                        fontStyle: FontStyle.italic)),
              ]),
            ],
            const SizedBox(height: 4),
            Text(fmtDate(msg.createdAt),
                style: TextStyle(
                    color: isAdmin ? DS.textMuted : Colors.white70, fontSize: 10)),
          ]),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Reply bar
// ─────────────────────────────────────────────────────────────────────────────

class _ReplyBar extends StatelessWidget {
  final TextEditingController ctrl;
  final bool sending;
  final VoidCallback onSend;

  const _ReplyBar({required this.ctrl, required this.sending, required this.onSend});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: DS.surface1,
      padding: EdgeInsets.only(
        left: 12, right: 8, top: 8,
        bottom: 8 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SafeArea(
        top: false,
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: ctrl,
              maxLines: 4,
              minLines: 1,
              style: const TextStyle(color: DS.textPrimary, fontSize: 14),
              decoration: const InputDecoration(
                hintText: 'Ваш ответ…',
                hintStyle: TextStyle(color: DS.textMuted),
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              ),
            ),
          ),
          const SizedBox(width: 4),
          IconButton(
            onPressed: sending ? null : onSend,
            icon: sending
                ? const SizedBox(
                    width: 20, height: 20,
                    child: CircularProgressIndicator(color: DS.violet, strokeWidth: 2))
                : const Icon(Icons.send_rounded, color: DS.violet),
          ),
        ]),
      ),
    );
  }
}
