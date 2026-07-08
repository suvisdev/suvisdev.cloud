import { GoogleGenerativeAI } from "@google/generative-ai"
import { NextResponse } from "next/server"

const MODEL_IDS: Record<string, string> = {
  flash: "gemini-3.1-flash-lite",
  flash15: "gemini-3.1-flash-lite",
  pro: "gemini-3.1-pro-preview",
}

type ChatMessage = { role: "user" | "assistant"; content: string }

function resolveModelId(key: string | undefined): string {
  if (key && key in MODEL_IDS) {
    return MODEL_IDS[key]!
  }
  return MODEL_IDS.flash!
}

export async function POST(request: Request) {
  const apiKey = process.env.GEMINI_API_KEY
  if (!apiKey) {
    return NextResponse.json(
      { error: "서버에 GEMINI_API_KEY가 설정되어 있지 않습니다." },
      { status: 503 },
    )
  }

  let body: { messages?: ChatMessage[]; model?: string; systemInstruction?: string }
  try {
    body = (await request.json()) as { messages?: ChatMessage[]; model?: string; systemInstruction?: string }
  } catch {
    return NextResponse.json({ error: "잘못된 요청 본문입니다." }, { status: 400 })
  }

  const messages = body.messages
  if (!Array.isArray(messages) || messages.length === 0) {
    return NextResponse.json({ error: "메시지가 비어 있습니다." }, { status: 400 })
  }

  const last = messages[messages.length - 1]
  if (!last || last.role !== "user" || typeof last.content !== "string") {
    return NextResponse.json(
      { error: "마지막 메시지는 사용자 텍스트여야 합니다." },
      { status: 400 },
    )
  }

  const trimmed = last.content.trim()
  if (!trimmed) {
    return NextResponse.json({ error: "입력이 비어 있습니다." }, { status: 400 })
  }

  const prior = messages.slice(0, -1)
  const rawHistory = prior.map((m) => ({
    role: m.role === "assistant" ? ("model" as const) : ("user" as const),
    parts: [{ text: m.content }],
  }))
  const firstUserIdx = rawHistory.findIndex((h) => h.role === "user")
  const history = firstUserIdx >= 0 ? rawHistory.slice(firstUserIdx) : []

  const modelId = resolveModelId(body.model)

  try {
    const genAI = new GoogleGenerativeAI(apiKey)
    const model = genAI.getGenerativeModel({
      model: modelId,
      ...(body.systemInstruction ? { systemInstruction: body.systemInstruction } : {}),
    })
    const chat = model.startChat({ history })
    const result = await chat.sendMessage(trimmed)
    const text = result.response.text()
    return NextResponse.json({ reply: text })
  } catch (e) {
    const message = e instanceof Error ? e.message : "답변을 가져오지 못했습니다."
    return NextResponse.json({ error: message }, { status: 502 })
  }
}
