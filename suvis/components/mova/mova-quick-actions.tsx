import { MOVA_QUICK_ACTIONS } from "@/lib/mova-mock-data"

export function MovaQuickActions() {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5 md:gap-3">
      {MOVA_QUICK_ACTIONS.map((action) => (
        <button
          key={action.id}
          type="button"
          className="flex items-center gap-2.5 rounded-lg bg-[var(--mova-surface)] px-3 py-3 text-left transition-colors hover:bg-[var(--mova-surface-2)] md:px-4 md:py-3.5"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--mova-accent-soft)] text-lg">
            {action.emoji}
          </span>
          <span className="text-sm font-medium text-[var(--mova-text)]">{action.label}</span>
        </button>
      ))}
    </div>
  )
}
