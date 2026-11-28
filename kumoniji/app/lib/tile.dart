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

  /// 두께(옆면)·그림자가 보이는 쪽(패 자기 좌표의 단위 벡터). 판에 누워 돌아간 패(RotatedBox)는 이걸 거꾸로 돌려 넘겨
  /// 늘 보는 사람 쪽(판 앞)으로 보이게 한다(11-28 사용자 '원근법으로 자연스럽게')
  final Offset edge;
  const TileView({
    super.key,
    required this.code,
    this.selected = false,
    this.onTap,
    this.width = 52,
    this.edge = const Offset(0, 1),
  });

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
          // 2.5D(11-25 사용자, 나중에 3D로): 앞면 아래로 패 두께(옆면)를 깔고, 그 밑에 바닥 그림자.
          // 레이아웃 크기는 그대로 두고 그림자로만 그려 손패·판 배치는 바뀌지 않는다.
          boxShadow: [
            BoxShadow(
              color: Color(selected ? 0x26000000 : 0x33000000),
              blurRadius: width * (selected ? .34 : .14),
              offset: edge * width * (selected ? .32 : .16) + Offset(edge.dy, -edge.dx) * width * .04,
            ),
            BoxShadow(color: const Color(0xFFC9B48C), offset: edge * width * .11), // 옆면 아래 가장자리
            BoxShadow(color: const Color(0xFFE6D6B5), offset: edge * width * .075), // 옆면
          ],
        ),
        child: SvgPicture.asset('assets/tiles/$code.svg', fit: BoxFit.contain),
      ),
    ),
  );
}

/// 점수 아이콘(꽃잎 petal·보너스 bonus) — 글자 줄 높이에 맞춘 작은 그림
Widget scoreIcon(String name, {double size = 14}) => Padding(
  padding: const EdgeInsets.only(right: 2),
  child: Image.asset('assets/icons/$name.png', width: size, height: size),
);
