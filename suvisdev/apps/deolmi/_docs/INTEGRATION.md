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

SDK는 마우스 움직임, 클릭·키 입력의 리듬, 머문 시간만 모은다. **입력한 글자는 보지 않는다.**

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

## 오류 코드

| 코드 | 원인 |
|------|------|
| 401 | 모르는 공개 키 / 틀린 비밀 키 / 위조된 토큰 |
| 403 | 등록하지 않은 도메인에서 호출 |
| 400 | 만료됐거나 이미 쓴 토큰 |
