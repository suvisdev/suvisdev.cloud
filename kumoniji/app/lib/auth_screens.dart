import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import 'account_screen.dart';
import 'auth.dart';
import 'home_screen.dart';
import 'l10n/app_localizations.dart';
import 'settings.dart';
import 'web_nav.dart';

const _ink = Color(0xFF42384C);

/// 서버 거절 이유 → 문구.
String authMessage(AppLocalizations t, Object e) {
  if (e is! AuthError) return t.serverError;
  return switch (e.code) {
    'credentials' => t.errCredentials,
    'wait' => t.errWait(e.seconds),
    'captcha' => t.errCaptcha,
    'email' => t.errEmail,
    'nickname' => t.errNickname,
    'password_short' => t.errPasswordShort,
    'password_long' => t.errPasswordLong,
    'password_personal' => t.errPasswordPersonal,
    'password_breached' => t.errPasswordBreached,
    'password_unavailable' => t.errPasswordUnavailable,
    'token' => t.linkInvalid,
    'email_taken' => t.errEmailTaken,
    'busy' => t.errBusy,
    'last_method' => t.errLastMethod,
    'session' => t.errSession,
    _ when e.status == 401 && e.code == null => t.errSession,
    _ => t.serverError,
  };
}

/// 시작 화면을 고른다: 메일 링크 → 링크 화면, 로그인 안 됨 → 로그인, MFA 전 → 코드, 그 외 → 첫 화면.
/// 로그인 상태(Auth.me)가 바뀌면 다시 고른다 — 로그아웃·세션 만료 때 저절로 로그인 화면으로 간다.
class AuthGate extends StatefulWidget {
  /// 테스트용(기본은 지금 주소)
  final Uri? start;
  const AuthGate({super.key, this.start});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool checked = false;
  (String, String)? link; // (종류, 토큰)
  String? notice; // 구글에서 돌아온 결과
  bool forgot = false; // "이미 가입된 주소" 메일의 /forgot 링크로 들어옴
  int? shown; // 지금 보여 주는 계정 — 로그아웃되거나 다른 계정으로 바뀌거나 2단계 인증 대기가 된 순간 위에 쌓인 화면을 걷는다

  @override
  void initState() {
    super.initState();
    final u = widget.start ?? Uri.base;
    final kind = u.pathSegments.isEmpty ? '' : u.pathSegments.first;
    final token = u.queryParameters['token'];
    if (const {'verify', 'reset', 'email', 'protect'}.contains(kind) && token != null) link = (kind, token);
    forgot = kind == 'forgot';
    if (forgot) WidgetsBinding.instance.addPostFrameCallback((_) => cleanUrl());
    notice = u.queryParameters.containsKey('auth_error')
        ? 'google_error'
        : u.queryParameters.containsKey('linked')
        ? 'linked'
        : u.queryParameters.containsKey('reauthed')
        ? 'reauthed'
        : null;
    // 메일 링크의 토큰이 주소창·방문 기록에 남지 않게 지운다. Flutter가 웹 기록을 준비한 뒤(첫 프레임 후)에.
    if (u.hasQuery) WidgetsBinding.instance.addPostFrameCallback((_) => cleanUrl());
    // 로그인 확인과 동시에(차례로면 로그인 화면이 한 번 더 기다린다). 메일 링크 화면으로 들어오면 미리 받지 않는다 — 링크 화면에
    // 머무는 사이 설정이 오래돼, 그 뒤 로그인 화면이 옛 캡차 키를 쓰게 된다(리뷰 3차)
    if (link == null) Auth.prefetchConfig();
    Auth.load().whenComplete(() => mounted ? setState(() => checked = true) : null);
  }

  @override
  Widget build(BuildContext context) {
    if (link != null) {
      return LinkScreen(kind: link!.$1, token: link!.$2, onDone: () => setState(() => link = null));
    }
    if (!checked) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return ValueListenableBuilder(
      valueListenable: Auth.me,
      builder: (context, me, _) {
        // 판·미션·상점처럼 위에 올린 화면에서 세션이 끝나거나(401) 다른 탭이 계정을 바꾸면(비는 틈 없이 바로 B가
        // 와도) 옛 화면이 남지 않게 걷는다(리뷰 2·11차)
        if (shown != null && (shown != me?.id || me!.needsMfa)) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (context.mounted) Navigator.of(context).popUntil((r) => r.isFirst);
          });
        }
        shown = me == null || me.needsMfa ? null : me.id;
        if (me == null) {
          final open = forgot;
          forgot = false;
          return LoginScreen(googleFailed: notice == 'google_error', openForgot: open);
        }
        if (me.needsMfa) return const MfaScreen();
        final open = notice == 'linked' || notice == 'reauthed' ? notice : null;
        notice = null;
        if (open != null) WidgetsBinding.instance.addPostFrameCallback((_) => openAccount(context, open));
        return HomeScreen(key: ValueKey(me.id)); // 계정마다 새로 — 잔고 막대가 바뀐 계정의 지갑을 다시 받게
      },
    );
  }
}

/// 가운데 좁은 폭의 공통 틀.
class AuthFrame extends StatelessWidget {
  final String title;
  final List<Widget> children;
  final bool back;
  final bool logo; // 제목 자리에 글씨 대신 제목 로고(로그인 첫 화면)
  const AuthFrame({super.key, required this.title, required this.children, this.back = false, this.logo = false});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: back ? AppBar(backgroundColor: Colors.transparent) : null,
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 340),
            child: AutofillGroup(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (logo)
                    const Center(child: TitleLogo(height: 72))
                  else
                    Text(
                      title,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold, color: _ink),
                    ),
                  const SizedBox(height: 24),
                  ...children,
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

Widget field(
  TextEditingController c,
  String label, {
  Key? key,
  bool secret = false,
  String? hint,
  Iterable<String>? autofill,
  TextInputType? type,
  VoidCallback? onSubmit,
}) => Padding(
  padding: const EdgeInsets.only(bottom: 12),
  child: TextField(
    key: key,
    controller: c,
    obscureText: secret,
    keyboardType: type,
    autofillHints: autofill,
    autocorrect: false,
    enableSuggestions: !secret,
    onSubmitted: onSubmit == null ? null : (_) => onSubmit(),
    decoration: InputDecoration(labelText: label, helperText: hint, border: const OutlineInputBorder()),
  ),
);

Widget wideButton(String label, VoidCallback? onPressed, {Key? key}) => Padding(
  padding: const EdgeInsets.only(top: 4, bottom: 8),
  child: FilledButton(
    key: key,
    style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
    onPressed: onPressed,
    child: Text(label),
  ),
);

Widget message(String? text, {bool good = false}) => text == null
    ? const SizedBox.shrink()
    : Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: TextStyle(color: good ? const Color(0xFF3E7D4F) : const Color(0xFFB3261E)),
        ),
      );

/// 로그인: 이메일·비밀번호 또는 구글. 실패가 많은 IP면 서버가 Turnstile을 요구한다.
class LoginScreen extends StatefulWidget {
  final bool googleFailed, openForgot;
  const LoginScreen({super.key, this.googleFailed = false, this.openForgot = false});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController(), password = TextEditingController();
  String? error, info, captcha, siteKey;
  Widget? captchaBox; // 한 번만 만든다 — 다시 그릴 때마다 새로 만들면 확인이 처음부터 반복된다
  bool busy = false, unverified = false, google = false, captchaAsked = false;

  @override
  void initState() {
    super.initState();
    if (widget.openForgot) {
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => Navigator.push(context, MaterialPageRoute(builder: (_) => const ForgotScreen())),
      );
    }
    Auth.config().then((c) {
      if (!mounted) return;
      setState(() {
        google = c['google'] == true;
        siteKey = c['turnstile_site'] as String?;
      });
    }, onError: (_) {});
  }

  Future<void> _login() async {
    final t = AppLocalizations.of(context)!;
    setState(() {
      busy = true;
      error = null;
      info = null;
    });
    try {
      final r = await Auth.login(email.text, password.text, captcha: captcha);
      // 기다리는 사이 뒤에서 세션이 복구돼 이 화면이 걷혔을 수 있다(리뷰 65차)
      if (r['verified'] == false && mounted) {
        setState(() {
          unverified = true;
          info = t.unverified;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        error = authMessage(t, e);
        captcha = null;
        captchaBox = null; // 쓴 확인 토큰은 다시 못 쓴다 → 다음 시도에 새 위젯
        captchaAsked = e is AuthError && e.code == 'captcha';
      });
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _resend() async {
    final t = AppLocalizations.of(context)!;
    try {
      await Auth.resend(email.text);
      if (mounted) setState(() => info = t.checkEmail);
    } catch (e) {
      if (mounted) setState(() => error = authMessage(t, e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final needCaptcha = captchaAsked && hasTurnstile && (siteKey ?? '').isNotEmpty;
    return AuthFrame(
      title: t.title,
      logo: true,
      children: [
        message(widget.googleFailed && error == null && info == null ? t.errGoogle : null),
        message(error),
        message(info, good: true),
        field(
          email,
          t.email,
          key: const ValueKey('email'),
          autofill: const [AutofillHints.email],
          type: TextInputType.emailAddress,
        ),
        field(
          password,
          t.password,
          key: const ValueKey('password'),
          secret: true,
          autofill: const [AutofillHints.password],
          onSubmit: _login,
        ),
        if (needCaptcha) captchaBox ??= turnstile(siteKey!, (tok) => setState(() => captcha = tok)),
        wideButton(t.login, busy || (needCaptcha && captcha == null) ? null : _login, key: const ValueKey('login')),
        if (unverified) TextButton(onPressed: _resend, child: Text(t.resend)),
        if (google && kIsWeb)
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            onPressed: () => goTo(Auth.googleStart()),
            icon: const Icon(Icons.g_mobiledata, size: 28),
            label: Text(t.continueWithGoogle),
          ),
        const SizedBox(height: 8),
        TextButton(
          key: const ValueKey('to-signup'),
          onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SignupScreen())),
          child: Text(t.signup),
        ),
        TextButton(
          onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ForgotScreen())),
          child: Text(t.forgotPassword),
        ),
      ],
    );
  }
}

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final email = TextEditingController(), nickname = TextEditingController(), password = TextEditingController();
  String? error;
  bool busy = false, sent = false;

  Future<void> _go() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await Auth.signup(email.text, password.text, nickname.text);
      setState(() => sent = true);
    } catch (e) {
      if (mounted) setState(() => error = authMessage(AppLocalizations.of(context)!, e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return AuthFrame(
      title: t.signup,
      back: true,
      children: sent
          ? [
              message(t.checkEmail, good: true),
              TextButton(onPressed: () => Navigator.pop(context), child: Text(t.toLogin)),
            ]
          : [
              message(error),
              field(
                email,
                t.email,
                key: const ValueKey('su-email'),
                autofill: const [AutofillHints.email],
                type: TextInputType.emailAddress,
              ),
              field(nickname, t.nickname, key: const ValueKey('su-nick'), autofill: const [AutofillHints.nickname]),
              field(
                password,
                t.password,
                key: const ValueKey('su-pw'),
                secret: true,
                hint: t.passwordHint,
                autofill: const [AutofillHints.newPassword],
              ),
              wideButton(t.signup, busy ? null : _go, key: const ValueKey('signup')),
            ],
    );
  }
}

class ForgotScreen extends StatefulWidget {
  const ForgotScreen({super.key});

  @override
  State<ForgotScreen> createState() => _ForgotScreenState();
}

class _ForgotScreenState extends State<ForgotScreen> {
  final email = TextEditingController();
  String? error;
  bool sent = false;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return AuthFrame(
      title: t.forgotPassword,
      back: true,
      children: sent
          ? [message(t.checkEmail, good: true)]
          : [
              message(error),
              field(email, t.email, autofill: const [AutofillHints.email], type: TextInputType.emailAddress),
              wideButton(t.confirm, () async {
                try {
                  await Auth.forgot(email.text);
                  setState(() => sent = true);
                } catch (e) {
                  setState(() => error = authMessage(t, e));
                }
              }),
            ],
    );
  }
}

/// 메일 링크 화면. 여는 것(GET)만으로는 아무 일도 없고, 버튼을 눌러야 서버가 토큰을 쓴다.
class LinkScreen extends StatefulWidget {
  final String kind, token;
  final VoidCallback onDone;
  const LinkScreen({super.key, required this.kind, required this.token, required this.onDone});

  @override
  State<LinkScreen> createState() => _LinkScreenState();
}

class _LinkScreenState extends State<LinkScreen> {
  final password = TextEditingController();
  bool? valid;
  bool busy = false, done = false;
  String? error;

  @override
  void initState() {
    super.initState();
    Auth.linkValid(widget.kind, widget.token).then((v) => mounted ? setState(() => valid = v) : null);
  }

  Future<void> _go() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await Auth.useLink(widget.kind, widget.token, password: password.text);
      setState(() => done = true);
    } catch (e) {
      if (mounted) setState(() => error = authMessage(AppLocalizations.of(context)!, e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    final k = widget.kind;
    final (title, doneText, action) = switch (k) {
      'verify' => (t.signup, t.verified, t.confirm),
      'reset' => (t.forgotPassword, t.passwordResetDone, t.confirm),
      'email' => (t.changeEmail, t.emailChangedDone, t.confirm),
      _ => (t.protectTitle, t.lockedDone, t.protectButton),
    };
    final toLogin = TextButton(onPressed: widget.onDone, child: Text(t.toLogin));
    if (valid == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return AuthFrame(
      title: title,
      children: done
          ? [message(doneText, good: true), toLogin]
          : valid == false
          ? [message(t.linkInvalid), toLogin]
          : [
              message(error),
              if (k == 'verify') Text(t.setPassword, textAlign: TextAlign.center),
              if (k == 'email') Text(t.confirmNewEmail, textAlign: TextAlign.center),
              if (k == 'protect') Text(t.protectBody, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              if (k == 'verify' || k == 'reset')
                field(
                  password,
                  k == 'verify' ? t.password : t.newPassword,
                  key: const ValueKey('link-pw'),
                  secret: true,
                  hint: t.passwordHint,
                  autofill: const [AutofillHints.newPassword],
                ),
              wideButton(action, busy ? null : _go, key: const ValueKey('link-go')),
            ],
    );
  }
}

class MfaScreen extends StatefulWidget {
  const MfaScreen({super.key});

  @override
  State<MfaScreen> createState() => _MfaScreenState();
}

class _MfaScreenState extends State<MfaScreen> {
  final code = TextEditingController();
  String? error;

  /// 서버에 닿지 못하면 로그아웃된 척하지 않고 알린다(리뷰 38·39차)
  Future<void> _out() async {
    try {
      await Auth.logout();
    } catch (e) {
      if (mounted) setState(() => error = authMessage(AppLocalizations.of(context)!, e));
    }
  }

  Future<void> _go() async {
    final t = AppLocalizations.of(context)!;
    try {
      await Auth.mfaVerify(code.text.trim());
    } catch (e) {
      setState(() => error = e is AuthError && e.code == 'credentials' ? t.errMfaCode : authMessage(t, e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context)!;
    return AuthFrame(
      title: t.mfaTitle,
      children: [
        message(error),
        field(
          code,
          t.mfaCode,
          key: const ValueKey('mfa-code'),
          autofill: const [AutofillHints.oneTimeCode],
          onSubmit: _go,
        ),
        wideButton(t.confirm, _go),
        TextButton(onPressed: _out, child: Text(t.logout)),
      ],
    );
  }
}

/// 첫 화면에서 계정 화면으로 바로 갈 때(구글 연결·재인증 뒤).
void openAccount(BuildContext context, String? notice) =>
    Navigator.push(context, MaterialPageRoute(builder: (_) => AccountScreen(notice: notice)));
