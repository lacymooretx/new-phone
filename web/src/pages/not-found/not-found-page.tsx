import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { Button } from "@/components/ui/button"
import { FileQuestion } from "lucide-react"

export function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <FileQuestion className="h-16 w-16 text-muted-foreground" />
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">{t('notFound.title')}</h1>
        <p className="text-muted-foreground">{t('notFound.description')}</p>
      </div>
      <Button asChild>
        <Link to="/">{t('notFound.goToDashboard')}</Link>
      </Button>
    </div>
  )
}
