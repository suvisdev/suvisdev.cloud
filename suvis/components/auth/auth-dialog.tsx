"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AuthForms,
  type AuthFormsMode,
} from "@/app/login/auth-forms"

type AuthDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultTab?: AuthFormsMode
  onAuthSuccess?: () => void
}

export function AuthDialog({
  open,
  onOpenChange,
  defaultTab = "login",
  onAuthSuccess,
}: AuthDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="auth-dialog-shell max-h-[min(90vh,720px)] max-w-md gap-0 overflow-hidden rounded-3xl bg-white p-0 sm:max-w-md"
        showCloseButton
      >
        <DialogTitle className="sr-only">로그인</DialogTitle>
        <DialogDescription className="sr-only">
          로그인하거나 새 계정을 만드세요
        </DialogDescription>
        <AuthForms
          mode={defaultTab}
          variant="embedded"
          onAuthSuccess={() => {
            onAuthSuccess?.()
            onOpenChange(false)
          }}
        />
      </DialogContent>
    </Dialog>
  )
}
