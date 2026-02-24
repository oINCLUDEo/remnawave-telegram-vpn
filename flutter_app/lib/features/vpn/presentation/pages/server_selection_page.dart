import 'dart:ui';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';
import '../widgets/server_tile.dart';

class _Server {
  const _Server({
    required this.name,
    required this.country,
    required this.flag,
    this.isPremium = false,
    required this.signal,
    this.category = 'all',
  });
  final String name;
  final String country;
  final String flag;
  final bool isPremium;
  final int signal;
  final String category;
}

const _servers = [
  _Server(name: 'Frankfurt #1', country: 'Германия', flag: '🇩🇪', signal: 5),
  _Server(name: 'Amsterdam #1', country: 'Нидерланды', flag: '🇳🇱', signal: 4),
  _Server(name: 'Paris #1', country: 'Франция', flag: '🇫🇷', signal: 4),
  _Server(name: 'London #1', country: 'Великобритания', flag: '🇬🇧', signal: 3, isPremium: true, category: 'premium'),
  _Server(name: 'New York #1', country: 'США', flag: '🇺🇸', signal: 3, isPremium: true, category: 'premium'),
  _Server(name: 'Tokyo #1', country: 'Япония', flag: '🇯🇵', signal: 2, isPremium: true, category: 'premium'),
  _Server(name: 'YouTube EU', country: 'Оптимизирован для YouTube', flag: '▶️', signal: 5, category: 'youtube'),
  _Server(name: 'YouTube US', country: 'Оптимизирован для YouTube', flag: '▶️', signal: 4, isPremium: true, category: 'youtube'),
  _Server(name: 'Singapore #1', country: 'Сингапур', flag: '🇸🇬', signal: 3, isPremium: true, category: 'ultra'),
  _Server(name: 'Dubai #1', country: 'ОАЭ', flag: '🇦🇪', signal: 4, isPremium: true, category: 'ultra'),
];

class ServerSelectionPage extends StatefulWidget {
  const ServerSelectionPage({super.key});

  @override
  State<ServerSelectionPage> createState() => _ServerSelectionPageState();
}

class _ServerSelectionPageState extends State<ServerSelectionPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final _searchController = TextEditingController();
  String _selectedServer = 'Frankfurt #1';
  String _query = '';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _searchController.addListener(() {
      setState(() => _query = _searchController.text.toLowerCase());
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  List<_Server> _filtered(String category) {
    final base = category == 'all'
        ? _servers
        : _servers.where((s) => s.category == category).toList();
    if (_query.isEmpty) return base;
    return base
        .where((s) =>
            s.name.toLowerCase().contains(_query) ||
            s.country.toLowerCase().contains(_query))
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
              // Search bar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: GlassCard(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
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
                            contentPadding: EdgeInsets.zero,
                            isDense: true,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              // Tab bar
              _buildTabBar(),
              const SizedBox(height: 8),
              // Server list
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: ['all', 'premium', 'ultra', 'youtube']
                      .map((cat) => _buildServerList(cat))
                      .toList(),
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
      child: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            color: AppColors.background.withValues(alpha: 0.6),
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back_ios_new_rounded,
                          color: AppColors.textPrimary, size: 20),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
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
        ),
      ),
    );
  }

  Widget _buildTabBar() {
    final tabs = ['Все', 'Premium', 'Ultra', 'YouTube'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: GlassCard(
        padding: const EdgeInsets.all(4),
        borderRadius: BorderRadius.circular(14),
        child: TabBar(
          controller: _tabController,
          indicator: BoxDecoration(
            gradient: const LinearGradient(
                colors: [AppColors.accent, AppColors.accentDark]),
            borderRadius: BorderRadius.circular(10),
          ),
          indicatorSize: TabBarIndicatorSize.tab,
          labelColor: const Color(0xFF1A1200),
          unselectedLabelColor: AppColors.textSecondary,
          labelStyle: const TextStyle(
              fontSize: 12, fontWeight: FontWeight.w600),
          unselectedLabelStyle: const TextStyle(fontSize: 12),
          dividerColor: Colors.transparent,
          tabs: tabs.map((t) => Tab(text: t, height: 36)).toList(),
        ),
      ),
    );
  }

  Widget _buildServerList(String category) {
    final servers = _filtered(category);
    if (servers.isEmpty) {
      return const Center(
        child: Text('Серверы не найдены',
            style: TextStyle(color: AppColors.textSecondary)),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      itemCount: servers.length,
      itemBuilder: (context, i) {
        final s = servers[i];
        return ServerTile(
          name: s.name,
          countryCode: s.country,
          flagEmoji: s.flag,
          isPremium: s.isPremium,
          signalLevel: s.signal,
          isSelected: _selectedServer == s.name,
          onTap: () {
            setState(() => _selectedServer = s.name);
            Future.delayed(const Duration(milliseconds: 200), () {
              if (context.mounted) {
                Navigator.of(context).pop({'name': '${s.flag} ${s.name}', 'flag': s.flag});
              }
            });
          },
        );
      },
    );
  }
}
