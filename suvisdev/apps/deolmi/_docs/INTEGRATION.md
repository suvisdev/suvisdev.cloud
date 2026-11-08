# 덜미 연동 가이드 (고객용)

웹페이지 입구(로그인·회원가입·예매 등)에 덜미를 붙여 매크로와 봇을 걸러내는 방법. 네 단계면 끝난다.

```text
[1] 키 받기 → [2] 페이지에 SDK 한 줄 → [3] 제출 직전 점수 받기 → [4] 고객 서버에서 검증
```

**공개 키(`pk_`)는 브라우저에 둬도 되지만, 비밀 키(`sk_`)는 절대 브라우저에 두지 말고 서버에만 둔다.**

## 1. 키 받기

덜미에서 키 한 쌍과 허용 도메인(예: `ticket.example.com`, 서브도메인 포함)을 등록받는다.
비밀 키는 발급 때 한 번만 보여 주므로 바로 서버 환경변수에 저장한다.

## 2. SDK 넣기

```html
<script src="https://api.suvisdev.cloud/api/deolmi/sdk.js"></script>
<script>
  const dm = Deolmi.init({ endpoint: "https://api.suvisdev.cloud", siteKey: "pk_..." });
</script>
```

SDK는 마우스 움직임, 터치 횟수, 클릭·키 입력의 리듬, 머문 시간만 모은다. **입력한 글자는 보지 않는다.**
휴대폰(터치)과 키보드만 쓰는 사람(Tab·Enter로 제출)도 따로 구분해 차단하지 않는다.

## 3. 제출 직전에 점수 받기

```js
async function onSubmit() {
  const { token, verdict } = await dm.score();
  document.getElementById("deolmi_token").value = token;  // 폼과 함께 서버로
  form.submit();
}
```

브라우저의 `verdict`는 참고용이다(조작 가능). 통과·차단 판단은 4단계에서 한다.

## 4. 고객 서버에서 검증

토큰은 **1회용, 2분 안에** 써야 한다.

```bash
curl -X POST https://api.suvisdev.cloud/api/deolmi/verify \
  -H "Content-Type: application/json" \
  -d '{"secret":"sk_...","token":"받은_토큰"}'
```

```python
r = requests.post("https://api.suvisdev.cloud/api/deolmi/verify",
                  json={"secret": os.environ["DEOLMI_SECRET"], "token": token})
if r.json()["verdict"] == "block":
    reject()
```

응답 예:

```json
{"score": 0.95, "verdict": "block", "rule_score": 0.95, "model_score": null,
 "decided_by": "rule", "reasons": ["키 입력 간격이 거의 일정함(자동 입력/붙여넣기 의심)"]}
```

| verdict | 뜻 | 권장 대응 |
|---------|-----|-----------|
| allow | 사람일 가능성 높음 | 통과 |
| challenge | 애매함 | 캡차 등 한 번 더 확인 |
| block | 매크로 가능성 높음 | 추가 확인 또는 차단(자동 차단보다 확인 권장) |

`reasons`는 이의 제기 대응과 로그 분석에 쓴다.

처음 붙일 때는 **관찰부터** 권한다: 한동안 verdict로 막지 말고 기록만 해서, 우리 사이트의 실제 사용자에게 어떤 값이 나오는지
본 뒤 challenge·block 대응을 켠다.

## 판정을 어떻게 믿어야 하나 (중요)

verdict는 **위험 신호**이지 "사람이 맞다"는 증명이 아니다.

- 신호는 방문자 브라우저가 보내는 값이라, SDK를 흉내 내 사람다운 숫자를 지어 보내는 정교한 공격은 allow를 받을 수 있다.
  덜미가 잡는 것은 흔한 매크로·자동 입력·폭주이고, 위조를 작정한 공격을 완전히 막지는 못한다.
- 그러니 **자체 통제와 함께** 쓴다: 로그인 필수, 1인·1기기 구매 수량 제한, 결제 단계 검증, 같은 계정·카드의 반복 시도 감시 등.
  allow라고 해서 이런 검사를 건너뛰지 않는다.
- 같은 IP에서 요청이 몰리는 것만으로는 block을 주지 않는다(PC방·회사처럼 IP 하나를 여럿이 쓰는 곳이 있어서) — 최대 challenge.

앞으로 서버측 교차검증, 고객 서버가 발급한 세션 값(nonce)을 토큰에 묶는 기능, 작업증명을 더할 계획이다.

## 오류 코드

| 코드 | 원인 |
|------|------|
| 401 | 모르는 공개 키 / 틀린 비밀 키 / 위조된 토큰 |
| 403 | 등록하지 않은 도메인에서 호출 |
| 400 | 만료됐거나 이미 쓴 토큰 |
| 422 | 신호 값이 범위를 벗어남(음수·무한대·비현실적으로 큰 값) |
| 503 | 덜미 쪽 일시 장애(토큰 1회용 확인 불가 등) — 잠시 뒤 재시도하거나, 이 경우 처리 방침(통과/보류)을 미리 정해 둔다 |
