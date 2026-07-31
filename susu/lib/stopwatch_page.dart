import 'dart:async';
import 'package:flutter/material.dart';

class StopwatchPage extends StatefulWidget {
  const StopwatchPage({super.key});

  @override
  State<StopwatchPage> createState() => _StopwatchPageState();
}

class _StopwatchPageState extends State<StopwatchPage> {
  final Stopwatch _stopwatch = Stopwatch();
  Timer? _ticker;

  // 랩별 소요 시간(누적이 아닌 개별 구간). 최근 랩이 리스트 맨 앞에 오도록 insert(0, ...) 사용.
  final List<Duration> _laps = [];
  Duration _lastLapMark = Duration.zero;

  bool get _isRunning => _stopwatch.isRunning;

  void _toggleStartStop() {
    setState(() {
      if (_isRunning) {
        _stopwatch.stop();
        _ticker?.cancel();
      } else {
        _stopwatch.start();
        _ticker = Timer.periodic(const Duration(milliseconds: 30), (_) {
          setState(() {});
        });
      }
    });
  }

  void _lapOrReset() {
    setState(() {
      if (_isRunning) {
        final elapsed = _stopwatch.elapsed;
        _laps.insert(0, elapsed - _lastLapMark);
        _lastLapMark = elapsed;
      } else {
        _stopwatch.reset();
        _laps.clear();
        _lastLapMark = Duration.zero;
      }
    });
  }

  String _format(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    final hundredths =
        (d.inMilliseconds.remainder(1000) ~/ 10).toString().padLeft(2, '0');
    return '$minutes:$seconds.$hundredths';
  }

  // 애플 스톱워치처럼 랩이 3개 이상일 때만 가장 빠른/느린 랩을 색으로 구분.
  int? get _fastestLapIndex {
    if (_laps.length < 3) return null;
    var index = 0;
    for (var i = 1; i < _laps.length; i++) {
      if (_laps[i] < _laps[index]) index = i;
    }
    return index;
  }

  int? get _slowestLapIndex {
    if (_laps.length < 3) return null;
    var index = 0;
    for (var i = 1; i < _laps.length; i++) {
      if (_laps[i] > _laps[index]) index = i;
    }
    return index;
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final fastest = _fastestLapIndex;
    final slowest = _slowestLapIndex;

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 40),
            Text(
              _format(_stopwatch.elapsed),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 56,
                fontWeight: FontWeight.w300,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
            const SizedBox(height: 32),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _RoundButton(
                  label: _isRunning ? '랩' : '재설정',
                  color: Colors.white24,
                  onPressed: (_isRunning || _laps.isNotEmpty) ? _lapOrReset : null,
                ),
                _RoundButton(
                  label: _isRunning ? '중단' : '시작',
                  color: _isRunning
                      ? Colors.red.withValues(alpha: 0.2)
                      : Colors.green.withValues(alpha: 0.2),
                  textColor: _isRunning ? Colors.red : Colors.green,
                  onPressed: _toggleStartStop,
                ),
              ],
            ),
            const SizedBox(height: 24),
            const Divider(color: Colors.white24, height: 1),
            Expanded(
              child: ListView.separated(
                itemCount: _laps.length,
                separatorBuilder: (_, _) =>
                    const Divider(color: Colors.white24, height: 1),
                itemBuilder: (context, index) {
                  final lapNumber = _laps.length - index;
                  Color color = Colors.white;
                  if (index == fastest) color = Colors.green;
                  if (index == slowest) color = Colors.red;

                  return Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('랩 $lapNumber', style: TextStyle(color: color)),
                        Text(
                          _format(_laps[index]),
                          style: TextStyle(
                            color: color,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RoundButton extends StatelessWidget {
  final String label;
  final Color color;
  final Color? textColor;
  final VoidCallback? onPressed;

  const _RoundButton({
    required this.label,
    required this.color,
    this.textColor,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 72,
      height: 72,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          shape: const CircleBorder(),
          backgroundColor: color,
          disabledBackgroundColor: color.withValues(alpha: color.a * 0.5),
        ),
        child: Text(
          label,
          style: TextStyle(color: textColor ?? Colors.white54),
        ),
      ),
    );
  }
}
