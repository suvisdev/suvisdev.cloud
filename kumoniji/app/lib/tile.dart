import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// 패 한 장. code는 서버 표기(예: s3, c13) 또는 'back'.
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
      child: SizedBox(
        width: width,
        height: width * 4 / 3,
        child: SvgPicture.asset('assets/tiles/$code.svg', fit: BoxFit.contain),
      ),
    ),
  );
}
