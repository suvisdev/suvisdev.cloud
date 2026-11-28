// 생성됨: kumoniji/tools/table3d/crop.py — 손으로 고치지 않는다. 렌더 그림(assets/table3d/) 픽셀 좌표.
import 'dart:ui';

/// 세운 패 한 칸: 윗변 가운데·바닥 가운데(판 위 점)·그림 자리
class T3Slot {
  const T3Slot(this.top, this.foot, this.rect);
  final Offset top, foot;
  final Rect rect;
}

const t3Size = Size(1688, 780);

/// 펠트 윗면 네 모서리: 먼 왼쪽·먼 오른쪽·가까운 오른쪽·가까운 왼쪽
const t3Felt = [Offset(310.06, 110.24), Offset(1377.94, 110.24), Offset(1598.28, 692.9), Offset(89.72, 692.9)];

/// 펠트 깊이 / 폭(실제 탁자 비율)
const t3FeltAspect = 0.6134020618556701;

/// 자리 1·2·3의 13칸(자리 1·3은 칸 0이 먼 쪽, 자리 2는 왼쪽부터)
const t3Walls = [
  [
    T3Slot(Offset(316.64, 104.24), Offset(330.35, 146.13), Rect.fromLTWH(254, 71, 139, 151)),
    T3Slot(Offset(306.36, 131.65), Offset(320.6, 173.61), Rect.fromLTWH(242, 97, 140, 153)),
    T3Slot(Offset(295.67, 160.15), Offset(310.48, 202.16), Rect.fromLTWH(232, 124, 142, 155)),
    T3Slot(Offset(284.54, 189.81), Offset(299.95, 231.83), Rect.fromLTWH(219, 153, 144, 154)),
    T3Slot(Offset(272.96, 220.7), Offset(289.0, 262.7), Rect.fromLTWH(207, 183, 146, 156)),
    T3Slot(Offset(260.88, 252.89), Offset(277.6, 294.83), Rect.fromLTWH(195, 216, 146, 155)),
    T3Slot(Offset(248.29, 286.48), Offset(265.72, 328.31), Rect.fromLTWH(183, 248, 147, 158)),
    T3Slot(Offset(235.13, 321.55), Offset(253.34, 363.23), Rect.fromLTWH(168, 282, 150, 159)),
    T3Slot(Offset(221.39, 358.2), Offset(240.41, 399.67), Rect.fromLTWH(154, 318, 152, 162)),
    T3Slot(Offset(207.0, 396.54), Offset(226.9, 437.75), Rect.fromLTWH(140, 355, 153, 162)),
    T3Slot(Offset(191.94, 436.7), Offset(212.77, 477.57), Rect.fromLTWH(124, 397, 155, 163)),
    T3Slot(Offset(176.15, 478.8), Offset(197.99, 519.25), Rect.fromLTWH(108, 437, 157, 164)),
    T3Slot(Offset(159.57, 523.0), Offset(182.49, 562.93), Rect.fromLTWH(90, 479, 160, 166)),
  ],
  [
    T3Slot(Offset(589.39, 89.5), Offset(595.95, 131.34), Rect.fromLTWH(518, 63, 147, 134)),
    T3Slot(Offset(631.83, 89.5), Offset(637.29, 131.34), Rect.fromLTWH(561, 64, 147, 133)),
    T3Slot(Offset(674.26, 89.5), Offset(678.63, 131.34), Rect.fromLTWH(602, 63, 116, 134)),
    T3Slot(Offset(716.7, 89.5), Offset(719.97, 131.34), Rect.fromLTWH(646, 64, 141, 133)),
    T3Slot(Offset(759.13, 89.5), Offset(761.32, 131.34), Rect.fromLTWH(688, 63, 143, 136)),
    T3Slot(Offset(801.57, 89.5), Offset(802.66, 131.34), Rect.fromLTWH(731, 64, 141, 133)),
    T3Slot(Offset(844.0, 89.5), Offset(844.0, 131.34), Rect.fromLTWH(774, 64, 140, 135)),
    T3Slot(Offset(886.43, 89.5), Offset(885.34, 131.34), Rect.fromLTWH(816, 64, 140, 135)),
    T3Slot(Offset(928.87, 89.5), Offset(926.68, 131.34), Rect.fromLTWH(856, 64, 143, 135)),
    T3Slot(Offset(971.3, 89.5), Offset(968.03, 131.34), Rect.fromLTWH(898, 62, 140, 135)),
    T3Slot(Offset(1013.74, 89.5), Offset(1009.37, 131.34), Rect.fromLTWH(938, 64, 145, 135)),
    T3Slot(Offset(1056.17, 89.5), Offset(1050.71, 131.34), Rect.fromLTWH(980, 64, 147, 133)),
    T3Slot(Offset(1098.61, 89.5), Offset(1092.05, 131.34), Rect.fromLTWH(1022, 64, 147, 133)),
  ],
  [
    T3Slot(Offset(1371.36, 104.24), Offset(1357.65, 146.13), Rect.fromLTWH(1294, 71, 140, 151)),
    T3Slot(Offset(1381.64, 131.65), Offset(1367.4, 173.61), Rect.fromLTWH(1304, 97, 140, 153)),
    T3Slot(Offset(1392.33, 160.15), Offset(1377.52, 202.16), Rect.fromLTWH(1313, 124, 143, 155)),
    T3Slot(Offset(1403.46, 189.81), Offset(1388.05, 231.83), Rect.fromLTWH(1324, 153, 144, 154)),
    T3Slot(Offset(1415.04, 220.7), Offset(1399.0, 262.7), Rect.fromLTWH(1334, 183, 146, 112)),
    T3Slot(Offset(1427.12, 252.89), Offset(1410.4, 294.83), Rect.fromLTWH(1345, 216, 146, 155)),
    T3Slot(Offset(1439.71, 286.48), Offset(1422.28, 328.31), Rect.fromLTWH(1357, 248, 148, 158)),
    T3Slot(Offset(1452.87, 321.55), Offset(1434.66, 363.23), Rect.fromLTWH(1369, 284, 123, 157)),
    T3Slot(Offset(1466.61, 358.2), Offset(1447.59, 399.67), Rect.fromLTWH(1381, 319, 152, 159)),
    T3Slot(Offset(1481.0, 396.54), Offset(1461.1, 437.75), Rect.fromLTWH(1394, 355, 154, 162)),
    T3Slot(Offset(1496.06, 436.7), Offset(1475.23, 477.57), Rect.fromLTWH(1408, 397, 156, 162)),
    T3Slot(Offset(1511.85, 478.8), Offset(1490.01, 519.25), Rect.fromLTWH(1422, 438, 157, 163)),
    T3Slot(Offset(1528.43, 523.0), Offset(1505.51, 562.93), Rect.fromLTWH(1437, 479, 160, 166)),
  ],
];
