import { MovaChatShell } from "@/components/mova/mova-chat-shell"
import { MovaHeader } from "@/components/mova/mova-header"

export default function MovaMainPage() {
  return (
    // h-screen + overflow-hidden으로 뷰포트에 고정 → 챗 리스트만 내부 스크롤,
    // 입력창은 항상 하단에 붙어 있게 한다(min-h-screen이면 콘텐츠가 길 때
    // 페이지 전체가 스크롤되며 입력창이 뷰포트 밖으로 밀림).
    <div className="flex h-screen flex-col overflow-hidden">
      <MovaHeader />
      <MovaChatShell />
    </div>
  )
}
