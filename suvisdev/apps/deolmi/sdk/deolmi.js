/*
 * 덜미(deolmi) SDK — 고객 페이지에 심어 사람의 행동 신호를 모아 채점 서버로 보낸다.
 *
 *   <script src="https://api.suvisdev.cloud/api/deolmi/sdk.js"></script>
 *   <script>
 *     const dm = Deolmi.init({ endpoint: "https://api.suvisdev.cloud", siteKey: "pk_..." });
 *     // 폼 제출 직전:
 *     const { token, verdict } = await dm.score();
 *     // token을 폼에 담아 보내면, 고객 서버가 /api/deolmi/verify로 점수를 확인한다.
 *   </script>
 *
 * 수집하는 것은 '어떻게 움직였나'(리듬·궤적)이지 '무엇을 입력했나'가 아니다.
 * 키 값 자체는 보지 않는다 — 간격(타이밍)만 본다.
 */
(function (global) {
  "use strict";

  function mean(a) { return a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0; }
  function std(a) {
    if (a.length < 2) return 0;
    const m = mean(a);
    return Math.sqrt(mean(a.map((x) => (x - m) ** 2)));
  }
  function intervals(times) {
    const iv = [];
    for (let i = 1; i < times.length; i++) iv.push(times[i] - times[i - 1]);
    return iv;
  }

  function init(opts) {
    const endpoint = (opts.endpoint || "").replace(/\/$/, "");
    const siteKey = opts.siteKey;
    const startTs = performance.now();

    let moveCount = 0;
    let pathPx = 0;
    let first = null, last = null, prev = null;   // 직선성 계산용 좌표
    const clickTimes = [];
    const keyTimes = [];

    document.addEventListener("mousemove", (e) => {
      moveCount++;
      const p = { x: e.clientX, y: e.clientY };
      if (!first) first = p;
      last = p;
      if (prev) pathPx += Math.hypot(p.x - prev.x, p.y - prev.y);
      prev = p;
    }, { passive: true });
    document.addEventListener("click", () => clickTimes.push(performance.now()), { passive: true });
    // e.key는 보지 않는다(타이밍만)
    document.addEventListener("keydown", () => keyTimes.push(performance.now()), { passive: true });

    function features() {
      // 직선성: 시작~끝 직선거리 / 실제 경로. 1에 가까우면 '자로 그은' 직선.
      let straightness = 0;
      if (first && last && pathPx > 0) {
        straightness = Math.min(Math.hypot(last.x - first.x, last.y - first.y) / pathPx, 1);
      }
      const clickIv = intervals(clickTimes);
      const keyIv = intervals(keyTimes);
      return {
        move_count: moveCount,
        path_px: Math.round(pathPx),
        straightness: Number(straightness.toFixed(3)),
        click_count: clickTimes.length,
        click_iv_mean: Math.round(mean(clickIv)),
        click_iv_std: Math.round(std(clickIv)),
        key_count: keyTimes.length,
        key_iv_std: Math.round(std(keyIv)),
        dwell_ms: Math.round(performance.now() - startTs),
      };
    }

    async function score() {
      const res = await fetch(endpoint + "/api/deolmi/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site_key: siteKey, signals: features() }),
      });
      if (!res.ok) throw new Error("deolmi score failed: " + res.status);
      return res.json();   // { token, verdict }
    }

    return { score, features };   // features는 디버깅용으로 노출
  }

  global.Deolmi = { init };
})(window);
