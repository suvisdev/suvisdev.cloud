import { authHeader } from "@/lib/suvis-session"
import { safeApiErrorMessage } from "@/lib/user-facing-error"

/** suvisdev/apps/media/router.py — GET /api/media/photos/ocr. require_admin
 * (HS256, viewer 로그인) 필요 — Authorization 헤더는 authHeader()가 싣는다. */
export type OcrPhotoItem = {
  image_url: string
  extracted_text: string
  user_id: string
}

type ApiErrorBody = { detail?: string | unknown }

export async function getPhotosWithOcr(): Promise<OcrPhotoItem[]> {
  const res = await fetch("/api/media/photos/ocr", { headers: authHeader() })
  const data = (await res.json()) as OcrPhotoItem[] & ApiErrorBody
  if (!res.ok) {
    throw new Error(safeApiErrorMessage(data.detail, "사진을 불러오지 못했습니다.", res.status))
  }
  return data
}
