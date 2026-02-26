import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/di/injection.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../servers/domain/entities/server_category_entity.dart';
import '../../../servers/domain/entities/server_entity.dart';
import '../../../servers/presentation/cubit/selected_server_cubit.dart';
import '../../../servers/presentation/cubit/server_cubit.dart';
import '../../../servers/presentation/cubit/server_state.dart';
import '../widgets/premium_badge.dart';
import '../widgets/signal_indicator.dart';

// ── Page ────────────────────────────────────────────────────────────────────

/// Wraps the real view with a [ServerCubit] from the DI container and
/// triggers the initial data load.
class ServerSelectionPage extends StatelessWidget {
  const ServerSelectionPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<ServerCubit>(
      create: (_) => sl<ServerCubit>()..loadServers(),
      child: const _ServerSelectionView(),
    );
  }
}

// ── Internal view ────────────────────────────────────────────────────────────

class _ServerSelectionView extends StatefulWidget {
  const _ServerSelectionView();

  @override
  State<_ServerSelectionView> createState() => _ServerSelectionViewState();
}

class _ServerSelectionViewState extends State<_ServerSelectionView> {
  final _searchController = TextEditingController();
  String _selectedServer = '';
  String _query = '';

  /// Tracks expanded state per category id. Defaults to expanded.
  final Map<String, bool> _expanded = {};

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() {
      setState(() => _query = _searchController.text.toLowerCase());
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<ServerEntity> _filteredServers(List<ServerEntity> servers) {
    if (_query.isEmpty) return servers;
    return servers
        .where((s) =>
            s.name.toLowerCase().contains(_query) ||
            (s.countryCode?.toLowerCase().contains(_query) ?? false))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: _buildAppBar(context),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.background, AppColors.backgroundDark],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const SizedBox(height: 12),
              // ── Search bar ──
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1C2340),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                  child: Row(
                    children: [
                      const Icon(Icons.search_rounded,
                          color: AppColors.textSecondary, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _searchController,
                          style: const TextStyle(
                              color: AppColors.textPrimary, fontSize: 15),
                          decoration: const InputDecoration(
                            hintText: 'Поиск серверов...',
                            hintStyle: TextStyle(
                                color: AppColors.textHint, fontSize: 15),
                            border: InputBorder.none,
                            filled: false,
                            contentPadding:
                                EdgeInsets.symmetric(vertical: 10),
                            isDense: true,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // ── Category list (dynamic) ──
              Expanded(
                child: BlocBuilder<ServerCubit, ServerState>(
                  builder: (context, state) {
                    if (state is ServerInitial || state is ServerLoading) {
                      return const Center(
                        child: CircularProgressIndicator(
                          color: AppColors.accent,
                          strokeWidth: 2,
                        ),
                      );
                    }

                    if (state is ServerError) {
                      return Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.wifi_off_rounded,
                                color: AppColors.textSecondary, size: 40),
                            const SizedBox(height: 12),
                            Padding(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 32),
                              child: Text(
                                state.message,
                                style: const TextStyle(
                                    color: AppColors.textSecondary,
                                    fontSize: 14),
                                textAlign: TextAlign.center,
                              ),
                            ),
                            const SizedBox(height: 16),
                            TextButton(
                              onPressed: () =>
                                  context.read<ServerCubit>().loadServers(),
                              child: const Text('Повторить',
                                  style:
                                      TextStyle(color: AppColors.accent)),
                            ),
                          ],
                        ),
                      );
                    }

                    if (state is ServerLoaded) {
                      final categories = state.categories;
                      if (categories.isEmpty) {
                        return const Center(
                          child: Text(
                            'Нет доступных серверов',
                            style: TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 14),
                          ),
                        );
                      }
                      return ListView.builder(
                        padding:
                            const EdgeInsets.fromLTRB(20, 0, 20, 20),
                        itemCount: categories.length,
                        itemBuilder: (context, index) =>
                            _buildCategory(categories[index]),
                      );
                    }

                    return const SizedBox.shrink();
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    return PreferredSize(
      preferredSize: const Size.fromHeight(56),
      child: Container(
        color: Colors.transparent,
        child: SafeArea(
          bottom: false,
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Row(
              children: [
                if (Navigator.canPop(context))
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios_new_rounded,
                        color: AppColors.textPrimary, size: 20),
                    onPressed: () => Navigator.maybePop(context),
                  )
                else
                  const SizedBox(width: 48),
                const Expanded(
                  child: Text(
                    'Выбор сервера',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: 48),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCategory(ServerCategoryEntity cat) {
    final servers = _filteredServers(cat.servers);
    final isExpanded = _expanded[cat.id] ?? true;

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Category header ──
          GestureDetector(
            onTap: () => setState(
                () => _expanded[cat.id] = !(_expanded[cat.id] ?? true)),
            behavior: HitTestBehavior.opaque,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          cat.name,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          cat.subtitle,
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    '${servers.length}',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(width: 6),
                  AnimatedRotation(
                    turns: isExpanded ? 0.25 : 0.0,
                    duration: const Duration(milliseconds: 200),
                    child: const Icon(
                      Icons.chevron_right_rounded,
                      color: AppColors.textSecondary,
                      size: 22,
                    ),
                  ),
                ],
              ),
            ),
          ),
          // ── Servers container ──
          AnimatedCrossFade(
            firstChild: servers.isEmpty
                ? const SizedBox.shrink()
                : _buildServersBox(servers),
            secondChild: const SizedBox.shrink(),
            crossFadeState: isExpanded
                ? CrossFadeState.showFirst
                : CrossFadeState.showSecond,
            duration: const Duration(milliseconds: 220),
          ),
        ],
      ),
    );
  }

  Widget _buildServersBox(List<ServerEntity> servers) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF141B2D),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: List.generate(servers.length, (i) {
          final s = servers[i];
          final isLast = i == servers.length - 1;
          return _buildServerRow(s, showDivider: !isLast);
        }),
      ),
    );
  }

  Widget _buildServerRow(ServerEntity s, {required bool showDivider}) {
    final isSelected = _selectedServer == s.name;
    final isPremium = s.category == 'premium';

    return GestureDetector(
      onTap: () {
        setState(() => _selectedServer = s.name);
        final serverName = s.flag.isNotEmpty ? '${s.flag} ${s.name}' : s.name;
        // Update shared cubit (available when pushed with BlocProvider.value)
        try {
          context
              .read<SelectedServerCubit>()
              .select(serverName, s.flag.isEmpty ? '🌐' : s.flag);
        } catch (_) {}
        Future.delayed(const Duration(milliseconds: 180), () {
          if (!mounted) return;
          if (Navigator.of(context).canPop()) {
            Navigator.of(context)
                .pop({'name': serverName, 'flag': s.flag});
          }
        });
      },
      behavior: HitTestBehavior.opaque,
      child: Column(
        children: [
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
            child: Row(
              children: [
                // Flag box
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E2940),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Center(
                    child:
                        Text(s.flag, style: const TextStyle(fontSize: 20)),
                  ),
                ),
                const SizedBox(width: 12),
                // Name + country
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              s.name,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                          if (isPremium) ...[
                            const SizedBox(width: 6),
                            const PremiumBadge(),
                          ],
                        ],
                      ),
                      if (s.countryCode != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          s.countryCode!,
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                // Signal indicator
                SignalIndicator(level: s.qualityLevel),
                if (isSelected) ...[
                  const SizedBox(width: 8),
                  const Icon(Icons.check_circle_rounded,
                      color: AppColors.accent, size: 18),
                ],
              ],
            ),
          ),
          if (showDivider)
            const Divider(
              height: 1,
              thickness: 0.5,
              color: Color(0xFF1E2940),
              indent: 16,
              endIndent: 16,
            ),
        ],
      ),
    );
  }
}
