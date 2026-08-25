"use client"

import { useEffect, useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

type MovaConfirmDialogProps = {
  open: boolean
  title: string
  description?: string
  confirmLabel?: string
  /** null이면 취소 버튼 없는 알림 모드 */
  cancelLabel?: string | null
  destructive?: boolean
  /** 지정하면 텍스트 입력을 요구하고 onConfirm에 입력값을 넘긴다 (탈퇴 아이디 재입력 등) */
  inputPlaceholder?: string
  onConfirm: (inputValue?: string) => void
  onClose: () => void
}

/** window.confirm/alert 대체 — Mova 토큰으로 스타일한 공용 확인 다이얼로그. */
export function MovaConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "확인",
  cancelLabel = "취소",
  destructive = false,
  inputPlaceholder,
  onConfirm,
  onClose,
}: MovaConfirmDialogProps) {
  const [value, setValue] = useState("")

  useEffect(() => {
    if (open) setValue("")
  }, [open])

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      {/* Dialog는 body로 포털되므로 .mova-app 토큰 스코프를 직접 부여해야 한다 */}
      <DialogContent className="mova-app max-w-sm border-mova-border bg-mova-bg text-mova-text">
        <DialogHeader>
          <DialogTitle className="text-mova-text">{title}</DialogTitle>
          {description ? (
            <DialogDescription className="whitespace-pre-line text-mova-muted">
              {description}
            </DialogDescription>
          ) : null}
        </DialogHeader>
        {inputPlaceholder ? (
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={inputPlaceholder}
            autoFocus
            className="w-full rounded-lg border border-mova-border bg-mova-surface-2 px-3 py-2 text-sm text-mova-text outline-none focus:border-mova-accent/60"
          />
        ) : null}
        <div className="flex justify-end gap-2">
          {cancelLabel !== null ? (
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-mova-border bg-mova-surface-2 px-4 py-2 text-sm font-medium text-mova-muted transition-colors hover:text-mova-text"
            >
              {cancelLabel}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => onConfirm(inputPlaceholder ? value : undefined)}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
              destructive
                ? "bg-rose-600 text-white hover:bg-rose-500"
                : "bg-mova-accent text-white hover:opacity-90",
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
