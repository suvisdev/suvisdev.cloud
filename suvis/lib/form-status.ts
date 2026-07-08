/** @see suvis/_claude/REACT_RULES.md — FormStatus.message에 formProps·비밀번호 넣지 않음 (§6) */

import type { Dispatch, SetStateAction } from "react"

export type FormStatus = {
  errors: Record<string, string>
  submitting: boolean
  message: string | null
}

export const initialFormStatus: FormStatus = {
  errors: {},
  submitting: false,
  message: null,
}

export function isSuccessMessage(message: string) {
  return /성공|완료|가입/.test(message)
}

export function patchState<T extends object>(
  setter: Dispatch<SetStateAction<T>>,
  patch: Partial<T>,
) {
  setter((prev) => ({ ...prev, ...patch }))
}
