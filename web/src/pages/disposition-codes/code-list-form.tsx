import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { DispositionCodeList, DispositionCodeListCreate } from "@/api/disposition-codes"

const codeListSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  description: z.string().optional().or(z.literal("")),
})

type FormValues = z.infer<typeof codeListSchema>

interface CodeListFormProps {
  codeList?: DispositionCodeList | null
  onSubmit: (data: DispositionCodeListCreate) => void
  isLoading: boolean
}

export function CodeListForm({ codeList, onSubmit, isLoading }: CodeListFormProps) {
  const { t } = useTranslation()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(codeListSchema) as any,
    defaultValues: {
      name: codeList?.name ?? "",
      description: codeList?.description ?? "",
    },
  })

  const submitHandler = (values: FormValues) => {
    onSubmit({
      name: values.name,
      description: values.description || null,
    })
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">{t('dispositionCodes.form.name')} *</Label>
        <Input id="name" placeholder={t('dispositionCodes.form.namePlaceholder')} {...register("name")} />
        {errors.name && (
          <p className="text-xs text-destructive">{errors.name.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('common.description')}</Label>
        <Textarea
          id="description"
          placeholder={t('common.optional')}
          {...register("description")}
        />
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : codeList ? t('dispositionCodes.form.updateButton') : t('dispositionCodes.form.createButton')}
      </Button>
    </form>
  )
}
