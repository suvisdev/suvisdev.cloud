import { MovaAiChatBar } from "@/components/mova/mova-ai-chat-bar"
import { MovaHeader } from "@/components/mova/mova-header"

export default function MovaMainPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <MovaHeader />
      <MovaAiChatBar />
    </div>
  )
}
