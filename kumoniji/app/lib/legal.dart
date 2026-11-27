import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'l10n/app_localizations.dart';

const _ink = Color(0xFF4A3B5C);

/// 이용약관·개인정보처리방침(11-26, 운영자 suvisdev). 원문은 assets/legal/*.md — 한국어는 ko, 나머지 언어는 영어판.
enum Legal { terms, privacy }

String legalAsset(Legal doc, String lang) => 'assets/legal/${doc.name}_${lang == 'ko' ? 'ko' : 'en'}.md';

void openLegal(BuildContext context, Legal doc) =>
    Navigator.push(context, MaterialPageRoute(builder: (_) => LegalScreen(doc: doc)));

class LegalScreen extends StatefulWidget {
  final Legal doc;
  const LegalScreen({super.key, required this.doc});

  @override
  State<LegalScreen> createState() => _LegalScreenState();
}

class _LegalScreenState extends State<LegalScreen> {
  Future<String>? _text;
  String? _lang; // 본문을 읽은 언어 — 화면을 연 채 기기 언어가 바뀌면 다시 읽는다(리뷰)

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final lang = Localizations.localeOf(context).languageCode;
    if (lang != _lang) _text = _load();
  }

  // 웹은 파일을 네트워크로 받는다 — 실패하면 오류와 다시 시도(로딩 표시만 남지 않게, 리뷰 2차). 실패한 값은 캐시하지 않는다
  Future<String> _load() {
    _lang = Localizations.localeOf(context).languageCode;
    return rootBundle.loadString(legalAsset(widget.doc, _lang!), cache: false);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final doc = widget.doc;
    return Scaffold(
      appBar: AppBar(title: Text(doc == Legal.terms ? t.terms : t.privacy), backgroundColor: Colors.transparent),
      body: FutureBuilder(
        future: _text,
        // 다시 시도 중(기다림)에도 snap은 앞 오류를 들고 있다 — 기다림을 먼저 본다
        builder: (context, snap) => snap.connectionState != ConnectionState.done
            ? const Center(child: CircularProgressIndicator())
            : snap.hasError
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(t.legalLoadFailed),
                    TextButton(
                      key: const ValueKey('legal-retry'),
                      onPressed: () => setState(() {
                        _text = _load();
                      }),
                      child: Text(t.retry),
                    ),
                  ],
                ),
              )
            : Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 720),
                  child: SelectionArea(
                    child: ListView(
                      key: const ValueKey('legal-body'),
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
                      children: markdownBlocks(snap.data!),
                    ),
                  ),
                ),
              ),
      ),
    );
  }
}

/// 문서에 쓰는 만큼만 그린다: # 제목, ## 소제목, - 목록, | 표 |, 문단.
List<Widget> markdownBlocks(String md) {
  final out = <Widget>[];
  final rows = <List<String>>[];
  void flushTable() {
    if (rows.isEmpty) return;
    out.add(
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Table(
          border: TableBorder.all(color: const Color(0x33000000)),
          children: [
            for (final (i, r) in rows.indexed)
              TableRow(
                children: [
                  for (final c in r)
                    Padding(
                      padding: const EdgeInsets.all(6),
                      child: Text(c, style: TextStyle(fontSize: 13, fontWeight: i == 0 ? FontWeight.bold : null)),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
    rows.clear();
  }

  for (final line in md.split('\n')) {
    final l = line.trimRight();
    if (l.startsWith('|')) {
      final cells = l.substring(1, l.endsWith('|') ? l.length - 1 : l.length).split('|').map((c) => c.trim()).toList();
      if (!cells.every((c) => RegExp(r'^-+$').hasMatch(c))) rows.add(cells);
      continue;
    }
    flushTable();
    if (l.isEmpty) continue;
    if (l.startsWith('# ')) {
      out.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text(
            l.substring(2),
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: _ink),
          ),
        ),
      );
    } else if (l.startsWith('## ')) {
      out.add(
        Padding(
          padding: const EdgeInsets.only(top: 16, bottom: 4),
          child: Text(
            l.substring(3),
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: _ink),
          ),
        ),
      );
    } else if (l.startsWith('- ')) {
      out.add(
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 3),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('•  '),
              Expanded(child: Text(l.substring(2), style: const TextStyle(height: 1.45))),
            ],
          ),
        ),
      );
    } else {
      out.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Text(l, style: const TextStyle(height: 1.45)),
        ),
      );
    }
  }
  flushTable();
  return out;
}

/// 로그인·가입 화면 아래: 동의 안내 + 두 문서 링크.
class LegalLinks extends StatelessWidget {
  const LegalLinks({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    const small = TextStyle(fontSize: 12, color: Color(0xFF7A6C8C));
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        children: [
          Text(t.agreeNote, textAlign: TextAlign.center, style: small),
          Wrap(
            alignment: WrapAlignment.center,
            children: [
              TextButton(
                key: const ValueKey('legal-terms'),
                onPressed: () => openLegal(context, Legal.terms),
                child: Text(t.terms, style: small.copyWith(decoration: TextDecoration.underline)),
              ),
              TextButton(
                key: const ValueKey('legal-privacy'),
                onPressed: () => openLegal(context, Legal.privacy),
                child: Text(t.privacy, style: small.copyWith(decoration: TextDecoration.underline)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
