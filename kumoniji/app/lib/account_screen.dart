import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import 'auth.dart';
import 'auth_screens.dart' show authMessage;
import 'l10n/app_localizations.dart';
import 'web_nav.dart';

/// 계정 설정: 비밀번호·이메일·2단계 인증·구글·로그아웃·삭제.
/// 민감한 작업은 서버가 "최근 인증"을 요구하면(403 reauth) 비밀번호를 다시 묻고 한 번 더 시도한다.
/// 비밀번호가 없는(구글로만 가입한) 계정은 구글로 다시 인증하고 돌아와 다시 누른다.
class AccountScreen extends StatelessWidget {
  final String? notice; // 'linked' | 'reauthed'
  const AccountScreen({super.key, this.notice});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    if (notice != null) {
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => _toast(context, notice == 'linked' ? t.googleLinked : t.reauthedTryAgain),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(t.account), backgroundColor: Colors.transparent),
      body: ValueListenableBuilder(
        valueListenable: Auth.me,
        builder: (context, me, _) {
          if (me == null) return const SizedBox.shrink();
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: ListView(
                children: [
                  ListTile(
                    leading: const Icon(Icons.person),
                    title: Text(me.nickname),
                    subtitle: Text(me.email ?? t.notSet),
                  ),
                  const Divider(),
                  if (me.hasPassword) _tile(Icons.password, t.changePassword, () => _changePassword(context, me)),
                  _tile(Icons.alternate_email, t.changeEmail, () => _changeEmail(context, me)),
                  if (me.mfaEnabled) ...[
                    _tile(Icons.key_off, t.mfaOff, () => _mfaOff(context, me)),
                    _tile(Icons.list_alt, t.newRecoveryCodes, () => _newCodes(context, me)),
                  ] else
                    _tile(Icons.key, t.mfaOn, () => _mfaOn(context, me)),
                  if (me.hasGoogle)
                    _tile(Icons.link_off, t.unlinkGoogle, () => _ok(context, me, Auth.unlinkGoogle))
                  else if (kIsWeb && me.hasPassword)
                    _tile(Icons.link, t.linkGoogle, () => _linkGoogle(context)),
                  const Divider(),
                  _tile(Icons.logout, t.logout, () => _out(context, false)),
                  _tile(Icons.devices, t.logoutAll, () => _out(context, true)),
                  const Divider(),
                  ListTile(
                    leading: const Icon(Icons.delete_forever, color: Color(0xFFB3261E)),
                    title: Text(t.deleteAccount, style: const TextStyle(color: Color(0xFFB3261E))),
                    onTap: () => _delete(context, me),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _tile(IconData icon, String label, VoidCallback onTap) =>
      ListTile(leading: Icon(icon), title: Text(label), onTap: onTap);
}

void _toast(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

/// 글자 하나를 묻는 창. 취소하면 null.
Future<String?> _ask(BuildContext context, String title, String label, {bool secret = false, String? body}) {
  final c = TextEditingController();
  final t = AppLocalizations.of(context)!;
  return showDialog<String>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (body != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: SelectableText(body)),
          TextField(
            key: const ValueKey('ask'),
            controller: c,
            obscureText: secret,
            autofocus: true,
            decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
            onSubmitted: (v) => Navigator.pop(d, v),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d), child: Text(t.cancel)),
        FilledButton(onPressed: () => Navigator.pop(d, c.text), child: Text(t.confirm)),
      ],
    ),
  );
}

/// 민감 작업 실행. 최근 인증이 필요하면 다시 인증하고 한 번 더. 결과(성공 시 값)를 돌려준다.
Future<T?> _sensitive<T>(BuildContext context, Me me, Future<T> Function() act) async {
  final t = AppLocalizations.of(context)!;
  try {
    try {
      return await act();
    } on AuthError catch (e) {
      if (e.status != 403 || e.code != 'reauth') rethrow;
      if (!me.hasPassword) {
        goTo(Auth.googleStart(reauth: true)); // 돌아오면 계정 화면에서 다시 누른다
        return null;
      }
      if (!context.mounted) return null;
      final pw = await _ask(context, t.reauthTitle, t.password, secret: true, body: t.reauthBody);
      if (pw == null) return null;
      await Auth.reauth(pw);
      return await act();
    }
  } catch (e) {
    if (context.mounted) _toast(context, authMessage(t, e));
    return null;
  }
}

/// 값 없는 민감 작업 — 끝까지 성공했으면 true.
Future<bool> _ok(BuildContext context, Me me, Future<void> Function() act) async =>
    await _sensitive(context, me, () async {
      await act();
      return true;
    }) ==
    true;

Future<void> _changePassword(BuildContext context, Me me) async {
  final t = AppLocalizations.of(context)!;
  final pw = await _ask(context, t.changePassword, t.newPassword, secret: true, body: t.passwordHint);
  if (pw == null || !context.mounted) return;
  if (await _ok(context, me, () => Auth.changePassword(pw)) && context.mounted) _toast(context, t.passwordChanged);
}

Future<void> _changeEmail(BuildContext context, Me me) async {
  final t = AppLocalizations.of(context)!;
  final email = await _ask(context, t.changeEmail, t.email);
  if (email == null || !context.mounted) return;
  if (await _ok(context, me, () => Auth.changeEmail(email)) && context.mounted) _toast(context, t.checkEmail);
}

Future<void> _showCodes(BuildContext context, List<String> codes) {
  final t = AppLocalizations.of(context)!;
  return showDialog(
    context: context,
    barrierDismissible: false,
    builder: (d) => AlertDialog(
      title: Text(t.recoveryCodes),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(t.recoveryCodesHint),
          const SizedBox(height: 12),
          SelectableText(codes.join('\n'), style: const TextStyle(fontFamily: 'monospace', fontSize: 16)),
        ],
      ),
      actions: [FilledButton(onPressed: () => Navigator.pop(d), child: Text(t.confirm))],
    ),
  );
}

Future<void> _mfaOn(BuildContext context, Me me) async {
  final t = AppLocalizations.of(context)!;
  final setup = await _sensitive(context, me, Auth.mfaSetup);
  if (setup == null || !context.mounted) return;
  final code = await _ask(context, t.mfaOn, t.mfaCode, body: '${t.mfaSetupHint}\n\n${setup['secret']}');
  if (code == null || !context.mounted) return;
  try {
    final codes = await Auth.mfaEnable(code.trim());
    if (context.mounted) await _showCodes(context, codes);
  } catch (e) {
    if (context.mounted) _toast(context, e is AuthError && e.code == 'credentials' ? t.errMfaCode : authMessage(t, e));
  }
}

Future<void> _mfaOff(BuildContext context, Me me) async {
  final t = AppLocalizations.of(context)!;
  final code = await _ask(context, t.mfaOff, t.mfaCode);
  if (code == null || !context.mounted) return;
  await _ok(context, me, () => Auth.mfaDisable(code.trim()));
}

Future<void> _newCodes(BuildContext context, Me me) async {
  final codes = await _sensitive(context, me, Auth.newRecoveryCodes);
  if (codes != null && context.mounted) await _showCodes(context, codes);
}

/// 구글 연결은 구글로 이동하기 전에 비밀번호로 다시 인증해 둔다(서버가 최근 인증을 요구).
Future<void> _linkGoogle(BuildContext context) async {
  final t = AppLocalizations.of(context)!;
  final pw = await _ask(context, t.reauthTitle, t.password, secret: true, body: t.reauthBody);
  if (pw == null) return;
  try {
    await Auth.reauth(pw);
    goTo(Auth.googleStart(link: true));
  } catch (e) {
    if (context.mounted) _toast(context, authMessage(t, e));
  }
}

Future<void> _out(BuildContext context, bool everywhere) async {
  await Auth.logout(everywhere: everywhere);
  if (context.mounted) Navigator.of(context).popUntil((r) => r.isFirst);
}

Future<void> _delete(BuildContext context, Me me) async {
  final t = AppLocalizations.of(context)!;
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(t.deleteAccount),
      content: Text(t.deleteConfirm),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: Text(t.cancel)),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFB3261E)),
          onPressed: () => Navigator.pop(d, true),
          child: Text(t.deleteAccount),
        ),
      ],
    ),
  );
  if (ok != true || !context.mounted) return;
  await _ok(context, me, Auth.deleteAccount);
  if (Auth.me.value == null && context.mounted) Navigator.of(context).popUntil((r) => r.isFirst);
}
