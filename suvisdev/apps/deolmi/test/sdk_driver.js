// SDK(sdk/deolmi.js)를 node에서 그대로 돌려 features()를 뽑는다 — test_sdk_signals.py가 부른다.
// 브라우저가 실제로 내는 이벤트 순서(시나리오 JSON)를 SDK 리스너에 그대로 흘려 보낸다.
// 사용: node sdk_driver.js <sdk 경로> '<[{"t":ms,"type":"keydown",...}, ...]>' <끝 시각 ms>
"use strict";

const [sdkPath, eventsJson, endMs] = process.argv.slice(2);
const listeners = {};
let clock = 0;

globalThis.window = globalThis;
globalThis.document = {
  // 브라우저처럼 { signal }이 abort되면 그 리스너는 더 불리지 않는다(SDK stop()).
  addEventListener(type, fn, opts) {
    (listeners[type] = listeners[type] || []).push((ev) => { if (!opts?.signal?.aborted) fn(ev); });
  },
};
Object.defineProperty(globalThis, "performance", { value: { now: () => clock }, configurable: true });

require(sdkPath);
const dm = globalThis.Deolmi.init({ endpoint: "http://x", siteKey: "pk_test" });

for (const ev of JSON.parse(eventsJson)) {
  clock = ev.t;
  if (ev.type === "stop") { dm.stop(); continue; }   // 시나리오 안에서 dm.stop() 호출
  for (const fn of listeners[ev.type] || []) fn(ev);   // 리스너가 없는 이벤트(mousemove 등)는 무시된다
}
clock = Number(endMs);
process.stdout.write(JSON.stringify(dm.features()));
