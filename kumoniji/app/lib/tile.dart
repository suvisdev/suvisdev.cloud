import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

Future<void>? _ready;

bool _skipPrecache = false;

/// 테스트용: 그림 파일 읽기가 가짜 시간 안에서 끝나지 않으므로 미리 불러오기를 건너뛴다.
@visibleForTesting
void markTilesReady() => _skipPrecache = true;

/// 패 그림 53장·뒷면·무늬 아이콘을 미리 받아 둔다(앱 시작 때 한 번).
/// 웹은 그림을 처음 그릴 때 서버에서 한 장씩 받아서, 봇이 처음 보는 패를 내면 5장이 따로따로 뜨거나
/// 자리에 이전 패 그림이 남아 있다가 바뀌었다(11-21 사용자 제보, 브라우저 요청 기록으로 확인).
/// 실패해도 게임은 진행한다 — 그때그때 받는 원래 방식으로 돌아갈 뿐.
Future<void> precacheTiles() async => _skipPrecache
    ? null
    : _ready ??= Future.wait([
        for (final s in ['m', 's', 'l', 'c'])
          for (var n = 1; n <= 13; n++) SvgAssetLoader('assets/tiles/$s$n.svg').loadBytes(null),
        SvgAssetLoader('assets/tiles/back.svg').loadBytes(null),
        for (final s in ['m', 's', 'l', 'c']) SvgAssetLoader('assets/icons/suit_$s.svg').loadBytes(null),
      ]).then((_) {}, onError: (_) {});

/// 패 한 장. code는 서버 표기(예: s3, c13) 또는 'back'.
/// 2.5D: 두께는 그림(오른쪽 아래 테두리)에 있고, 여기서는 바닥 그림자만 깐다. 고르면 떠오르며 그림자가 퍼진다.
class TileView extends StatelessWidget {
  final String code;
  final bool selected;
  final VoidCallback? onTap;
  final double width;
  const TileView({super.key, required this.code, this.selected = false, this.onTap, this.width = 52});

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: AnimatedSlide(
      offset: selected ? const Offset(0, -0.18) : Offset.zero,
      duration: const Duration(milliseconds: 120),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 120),
        width: width,
        height: width * 4 / 3,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(width * .16),
          boxShadow: [
            BoxShadow(
              color: Color(selected ? 0x30000000 : 0x38000000),
              blurRadius: width * (selected ? .3 : .1),
              offset: Offset(width * .03, width * (selected ? .26 : .06)),
            ),
          ],
        ),
        child: SvgPicture.asset('assets/tiles/$code.svg', fit: BoxFit.contain),
      ),
    ),
  );
}
