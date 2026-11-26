{{flutter_js}}
{{flutter_build_config}}

// 첫 화면이 그려지면 index.html의 로딩 표시를 지운다(11-26)
window.addEventListener('flutter-first-frame', () => document.getElementById('loading')?.remove());
_flutter.loader.load();
