import { MovaChatShell } from "@/components/mova/mova-chat-shell"
import { MovaHeader } from "@/components/mova/mova-header"

export default function MovaMainPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <MovaHeader />
      <MovaChatShell />
    </div>
  )
}
