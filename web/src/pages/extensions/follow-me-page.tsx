import { useParams, useNavigate } from "react-router"
import { useTranslation } from "react-i18next"
import { useFollowMe, useUpdateFollowMe } from "@/api/follow-me"
import { useExtensions } from "@/api/extensions"
import { PageHeader } from "@/components/shared/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { FollowMeForm } from "./follow-me-form"
import { ArrowLeft } from "lucide-react"
import { toast } from "sonner"
import type { FollowMeUpdate } from "@/api/follow-me"

export function FollowMePage() {
  const { t } = useTranslation()
  const { extensionId } = useParams<{ extensionId: string }>()
  const navigate = useNavigate()
  const { data: extensions } = useExtensions()
  const { data: followMe, isLoading: followMeLoading } = useFollowMe(extensionId ?? "")
  const updateMutation = useUpdateFollowMe()

  const extension = extensions?.find((e) => e.id === extensionId)

  const handleSubmit = (data: FollowMeUpdate) => {
    if (!extensionId) return
    updateMutation.mutate(
      { extensionId, ...data },
      {
        onSuccess: () => toast.success(t('extensions.followMe.saved')),
        onError: (err) => toast.error(err.message),
      }
    )
  }

  if (!extensionId) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('extensions.followMe.title')} description={t('common.noResults')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('extensions.title'), href: "/extensions" }, { label: "Follow Me" }]}>
          <Button variant="outline" onClick={() => navigate("/extensions")}>
            <ArrowLeft className="mr-2 h-4 w-4" /> {t('extensions.title')}
          </Button>
        </PageHeader>
      </div>
    )
  }

  const extLabel = extension
    ? `${extension.extension_number}${extension.internal_cid_name ? ` - ${extension.internal_cid_name}` : ""}`
    : extensionId

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${t('extensions.followMe.title')}: ${extLabel}`}
        description={t('extensions.followMe.description', { number: extLabel })}
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: t('extensions.title'), href: "/extensions" }, { label: "Follow Me" }]}
      >
        <Button variant="outline" onClick={() => navigate("/extensions")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> {t('extensions.title')}
        </Button>
      </PageHeader>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>{t('extensions.followMe.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          {followMeLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : (
            <FollowMeForm
              initialData={followMe ?? null}
              onSubmit={handleSubmit}
              isLoading={updateMutation.isPending}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
