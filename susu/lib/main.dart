import 'package:flutter/material.dart';

void main() {
  runApp(const SuvisApp());
}

class SuvisApp extends StatelessWidget {
  const SuvisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Suvisdev',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.system,
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFE8E8E8),
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D0F14),
      ),
      home: const IntroScreen(),
    );
  }
}

class IntroScreen extends StatelessWidget {
  const IntroScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = _Colors(isDark);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: LayoutBuilder(
            builder: (context, constraints) {
              // Z Fold 7 펼친 내부 화면 ~656dp, 커버 ~390dp
              final isUnfolded = constraints.maxWidth >= 550;
              return isUnfolded
                  ? _UnfoldedLayout(colors: colors)
                  : _FoldedLayout(colors: colors);
            },
          ),
        ),
      ),
    );
  }
}

// 펼쳤을 때: 웹 데스크톱과 동일한 2컬럼
class _UnfoldedLayout extends StatelessWidget {
  final _Colors colors;
  const _UnfoldedLayout({super.key, required this.colors});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: _ContentCard(colors: colors, showCompactHero: false),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(color: colors.border),
                borderRadius: BorderRadius.circular(24),
              ),
              child: const _HeroPanel(),
            ),
          ),
        ),
      ],
    );
  }
}

// 접었을 때: 웹 모바일과 동일한 단일 카드 (히어로 카드 안에 삽입)
class _FoldedLayout extends StatelessWidget {
  final _Colors colors;
  const _FoldedLayout({super.key, required this.colors});

  @override
  Widget build(BuildContext context) {
    return _ContentCard(colors: colors, showCompactHero: true);
  }
}

class _ContentCard extends StatelessWidget {
  final _Colors colors;
  final bool showCompactHero;
  const _ContentCard({super.key, required this.colors, required this.showCompactHero});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: colors.cardBg,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: colors.border),
      ),
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 설명 + 아이콘
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      '웹·백엔드·AI를 아우르며, 확장 가능한 설계와 단순한 구현 사이의 균형을 맞춥니다. 도메인별 AI 앱을 만들고, 지속 가능한 시스템을 구축합니다.',
                      style: TextStyle(
                        color: colors.muted,
                        fontSize: 13.5,
                        height: 1.65,
                        letterSpacing: -0.1,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Icon(Icons.arrow_outward, color: colors.strong, size: 20),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Divider(color: colors.border, height: 1),
              const SizedBox(height: 20),
              // 컴팩트 히어로 (접힌 상태에서만)
              if (showCompactHero) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Container(
                    height: 160,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      border: Border.all(color: colors.border),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const _HeroPanel(),
                  ),
                ),
                const SizedBox(height: 24),
              ],
              // 한국어 헤드라인
              Text(
                '복잡함은 걷어내고,',
                style: TextStyle(
                  color: colors.muted,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  height: 1.25,
                  letterSpacing: -0.4,
                ),
              ),
              Text(
                '확장은 자유롭게.',
                style: TextStyle(
                  color: colors.strong,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  height: 1.25,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 14),
              // 영문 디스플레이 헤드라인
              RichText(
                text: TextSpan(
                  style: const TextStyle(
                    fontSize: 34,
                    fontWeight: FontWeight.w900,
                    height: 0.92,
                    letterSpacing: -0.5,
                  ),
                  children: [
                    TextSpan(text: 'SIMPLIFY ', style: TextStyle(color: colors.muted)),
                    TextSpan(text: 'COMPLEXITY,\n', style: TextStyle(color: colors.strong)),
                    TextSpan(text: 'SCALE ', style: TextStyle(color: colors.muted)),
                    TextSpan(text: 'WITHOUT LIMITS.', style: TextStyle(color: colors.strong)),
                  ],
                ),
              ),
            ],
          ),
          // CTA 버튼
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {},
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFF0DC3A),
                foregroundColor: const Color(0xFF1A1A1A),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 0,
              ),
              child: const Text(
                'Suvisdev 알아보기',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.2,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HeroPanel extends StatelessWidget {
  const _HeroPanel();

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Container(color: const Color(0xFF0D1117)),
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0x663D1760),
                Color(0x00000000),
                Color(0x26007B99),
              ],
            ),
          ),
        ),
        CustomPaint(painter: _GridPainter()),
        const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'SUVISDEV',
                style: TextStyle(
                  color: Color(0x44FFFFFF),
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 5,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'AI · Backend · Web',
                style: TextStyle(
                  color: Color(0x66FFFFFF),
                  fontSize: 12,
                  fontWeight: FontWeight.w300,
                  letterSpacing: 2,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0x0AFFFFFF)
      ..strokeWidth = 0.5;
    const step = 28.0;
    for (double x = 0; x <= size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y <= size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _Colors {
  final bool isDark;
  const _Colors(this.isDark);

  Color get cardBg => isDark ? const Color(0xFF161A24) : Colors.white;
  Color get border => isDark ? const Color(0xFF252B3B) : const Color(0xFFD4D4D4);
  Color get strong => isDark ? const Color(0xFFF2F2F2) : const Color(0xFF171717);
  Color get muted => isDark ? const Color(0xFFB3B3B3) : const Color(0xFF737373);
}
