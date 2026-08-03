import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/mova_chat_recommendation.dart';
import 'mova_chat_controller.dart';

class MovaChatScreen extends ConsumerStatefulWidget {
  const MovaChatScreen({super.key});

  @override
  ConsumerState<MovaChatScreen> createState() => _MovaChatScreenState();
}

class _MovaChatScreenState extends ConsumerState<MovaChatScreen> {
  final _messageController = TextEditingController();

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  void _send() {
    final message = _messageController.text;
    ref.read(movaChatControllerProvider.notifier).sendMessage(message);
    _messageController.clear();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(movaChatControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('mova 추천 챗')),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(child: _buildBody(state)),
            _buildInputBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(MovaChatState state) {
    switch (state.status) {
      case MovaChatStatus.idle:
        return const Center(child: Text('영화 취향을 말해보세요'));
      case MovaChatStatus.loading:
        return const Center(child: CircularProgressIndicator());
      case MovaChatStatus.error:
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              state.errorMessage ?? '오류가 발생했습니다.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.red),
            ),
          ),
        );
      case MovaChatStatus.success:
        final response = state.response!;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(response.reply, style: const TextStyle(fontSize: 15)),
            const SizedBox(height: 16),
            ...response.recommendations.map(
              (rec) => _RecommendationCard(recommendation: rec),
            ),
          ],
        );
    }
  }

  Widget _buildInputBar() {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              decoration: const InputDecoration(
                hintText: '예: 잔잔한 힐링 영화 추천해줘',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _send(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(icon: const Icon(Icons.send), onPressed: _send),
        ],
      ),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  final MovaChatRecommendation recommendation;

  const _RecommendationCard({required this.recommendation});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                width: 72,
                height: 108,
                child: recommendation.poster.isEmpty
                    ? _posterFallback()
                    : Image.network(
                        recommendation.poster,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => _posterFallback(),
                        loadingBuilder: (context, child, progress) {
                          if (progress == null) return child;
                          return const Center(
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          );
                        },
                      ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    recommendation.year.isEmpty
                        ? recommendation.title
                        : '${recommendation.title} (${recommendation.year})',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    recommendation.hook.isNotEmpty
                        ? recommendation.hook
                        : recommendation.synopsis,
                    style: const TextStyle(fontSize: 13),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _posterFallback() {
    return Container(
      color: Colors.grey.shade300,
      child: const Icon(Icons.movie, color: Colors.grey),
    );
  }
}
