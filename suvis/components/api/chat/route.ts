import { GoogleGenerativeAI } from "@google/generative-ai"
import type { NextRequest} from "next/server";
import { NextResponse } from "next/server"

type ModelKey = "flash" | "flash15" | "pro"

const GEMINI_MODEL_MAP: Record<ModelKey, string> = {
  flash: "gemini-3.1-flash-lite",
  flash15: "gemini-3.1-flash-lite",
  pro: "gemini-3.1-pro-preview",
}

function resolveModelId(model?: string): string {
  if (model && model in GEMINI_MODEL_MAP) {
    return GEMINI_MODEL_MAP[model as ModelKey]
  }
  return GEMINI_MODEL_MAP.flash15
}

function errorMessage(error: unknown): string {
  const err = error instanceof Error ? error.message : String(error)
  if (/429|quota|resource_exhausted/i.test(err)) {
    return "Gemini 사용 한도에 도달했습니다. 잠시 후 다시 시도해 주세요."
  }
  if (/404|not found/i.test(err)) {
    return "요청한 Gemini 모델을 찾을 수 없습니다. 다른 모델로 바꿔 주세요."
  }
  return "서버 오류가 발생했습니다."
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      prompt?: string
      message?: string
      model?: string
    }

    const prompt = (body.message ?? body.prompt ?? "").trim()
    if (!prompt) {
      return NextResponse.json({ error: "메시지가 비어 있습니다." }, { status: 400 })
    }

    const apiKey = process.env.GEMINI_API_KEY
    if (!apiKey) {
      return NextResponse.json({ error: "API 키가 설정되지 않았습니다." }, { status: 500 })
    }

    const genAI = new GoogleGenerativeAI(apiKey)
    const model = genAI.getGenerativeModel({ model: resolveModelId(body.model) })

    const result = await model.generateContent(prompt)
    const responseText = result.response.text()

    return NextResponse.json({ reply: responseText, text: responseText })
  } catch (error) {
    const message = errorMessage(error)
    const status = /한도|429|quota/i.test(message) ? 429 : 500
    return NextResponse.json({ error: message }, { status })
  }
}
