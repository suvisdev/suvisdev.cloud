import 'package:flutter/material.dart';

import 'l10n/app_localizations.dart';

/// 처음 하는 사람을 위한 설명 카드(넘겨 보는 5장).
Future<void> showHelp(BuildContext context) => showDialog(context: context, builder: (_) => const _HelpCards());

class _HelpCards extends StatefulWidget {
  const _HelpCards();

  @override
  State<_HelpCards> createState() => _HelpCardsState();
}

class _HelpCardsState extends State<_HelpCards> {
  final pc = PageController();
  int page = 0;

  @override
  void dispose() {
    pc.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final cards = [
      (t.help1t, t.help1b),
      (t.help2t, t.help2b),
      (t.help3t, t.help3b),
      (t.help4t, t.help4b),
      (t.help5t, t.help5b),
    ];
    final last = page == cards.length - 1;
    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420, maxHeight: 440),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
          child: Column(
            children: [
              Text(t.help, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Expanded(
                child: PageView(
                  controller: pc,
                  onPageChanged: (i) => setState(() => page = i),
                  children: [
                    for (final (title, body) in cards)
                      SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            const SizedBox(height: 10),
                            Text(body, style: const TextStyle(fontSize: 15, height: 1.5)),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              Row(
                children: [
                  for (var i = 0; i < cards.length; i++)
                    Container(
                      margin: const EdgeInsets.only(right: 6),
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: i == page ? const Color(0xFFC9A24A) : const Color(0xFFE9DFD1),
                      ),
                    ),
                  const Spacer(),
                  FilledButton(
                    onPressed: () => last
                        ? Navigator.pop(context)
                        : pc.nextPage(duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                    child: Text(last ? t.helpDone : t.helpNext),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
