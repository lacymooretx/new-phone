import { useTranslation } from "react-i18next"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"

interface KeyboardShortcutsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function KeyboardShortcutsDialog({ open, onOpenChange }: KeyboardShortcutsDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t('shortcuts.title')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <ShortcutSection title={t('shortcuts.navigation')}>
            <Shortcut keys={["\u2318", "K"]} description={t('shortcuts.openSearch')} />
            <Shortcut keys={["\u2318", "?"]} description={t('shortcuts.showShortcuts')} />
            <Shortcut keys={["Esc"]} description={t('shortcuts.closeDialog')} />
          </ShortcutSection>
          <ShortcutSection title={t('shortcuts.commandPalette')}>
            <Shortcut keys={["\u2191", "\u2193"]} description={t('shortcuts.navigateResults')} />
            <Shortcut keys={["Enter"]} description={t('shortcuts.goToSelected')} />
          </ShortcutSection>
          <ShortcutSection title={t('shortcuts.dataTables')}>
            <Shortcut keys={["Click"]} description={t('shortcuts.sortByColumn')} />
          </ShortcutSection>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function ShortcutSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-medium mb-2">{title}</h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function Shortcut({ keys, description }: { keys: string[]; description: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{description}</span>
      <div className="flex items-center gap-1">
        {keys.map((key, i) => (
          <kbd key={i} className="inline-flex h-5 min-w-5 items-center justify-center rounded border bg-muted px-1 font-mono text-xs">
            {key}
          </kbd>
        ))}
      </div>
    </div>
  )
}
