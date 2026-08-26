import { MovaChatShell } from "@/components/mova/mova-chat-shell"

export default function MovaMainPage() {
  return (
    // flex-1 + min-h-0 + overflow-hidden으로 헤더·푸터를 제외한 남은 뷰포트에
    // 고정 → 챗 리스트만 내부 스크롤, 입력창은 항상 하단에 붙어 있게 한다.
    // (헤더가 레이아웃으로 올라간 2026-08-26 이후 h-screen이면 입력창이
    // 헤더 높이만큼 뷰포트 밖으로 밀림.)
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <MovaChatShell />
    </div>
  )
}
