import { useForm, useFieldArray } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useExtensions } from "@/api/extensions"
import { Plus, Trash2 } from "lucide-react"
import type { PageGroup, PageGroupCreate } from "@/api/page-groups"

const pageGroupSchema = z.object({
  name: z.string().min(1, "Required").max(100),
  page_number: z.string().min(1, "Required").max(20),
  description: z.string().optional().or(z.literal("")),
  page_mode: z.string().default("one_way"),
  timeout: z.coerce.number().min(1).max(300).default(60),
  members: z.array(z.object({
    extension_id: z.string().min(1, "Required"),
    position: z.coerce.number().min(0).max(100).default(0),
  })).default([]),
})

type FormValues = z.infer<typeof pageGroupSchema>

interface PageGroupFormProps {
  pageGroup?: PageGroup | null
  onSubmit: (data: PageGroupCreate) => void
  isLoading: boolean
}

export function PageGroupForm({ pageGroup, onSubmit, isLoading }: PageGroupFormProps) {
  const { t } = useTranslation()
  const { data: extensions } = useExtensions()

  const { register, handleSubmit, setValue, watch, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(pageGroupSchema) as any,
    defaultValues: {
      name: pageGroup?.name ?? "",
      page_number: pageGroup?.page_number ?? "",
      description: pageGroup?.description ?? "",
      page_mode: pageGroup?.page_mode ?? "one_way",
      timeout: pageGroup?.timeout ?? 60,
      members: pageGroup?.members?.map((m) => ({
        extension_id: m.extension_id,
        position: m.position,
      })) ?? [],
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: "members" })

  const submitHandler = (values: FormValues) => {
    const data: PageGroupCreate = {
      ...values,
      description: values.description || undefined,
    }
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">{t('paging.form.name')} *</Label>
          <Input id="name" placeholder={t('paging.form.namePlaceholder')} {...register("name")} />
          {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="page_number">{t('paging.form.pageNumber')} *</Label>
          <Input id="page_number" placeholder={t('paging.form.pageNumberPlaceholder')} {...register("page_number")} />
          {errors.page_number && <p className="text-xs text-destructive">{errors.page_number.message}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">{t('common.description')}</Label>
        <Textarea id="description" placeholder={t('common.optional')} {...register("description")} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>{t('common.type')}</Label>
          <Select value={watch("page_mode")} onValueChange={(v) => setValue("page_mode", v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="one_way">One Way</SelectItem>
              <SelectItem value="two_way">Two Way</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="timeout">{t('ivrMenus.form.timeout')}</Label>
          <Input id="timeout" type="number" min={1} max={300} {...register("timeout")} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>{t('common.members')}</Label>
          <Button type="button" variant="outline" size="sm" onClick={() => append({ extension_id: "", position: fields.length })}>
            <Plus className="mr-1 h-3 w-3" /> {t('queues.form.addMember')}
          </Button>
        </div>
        <div className="max-h-64 overflow-y-auto rounded border p-2 space-y-2">
          {fields.length === 0 && (
            <p className="text-xs text-muted-foreground py-2 text-center">{t('queues.form.noMembers')}</p>
          )}
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <div className="flex-1">
                <Select
                  value={watch(`members.${index}.extension_id`)}
                  onValueChange={(v) => setValue(`members.${index}.extension_id`, v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={t('queues.form.selectExtension')} />
                  </SelectTrigger>
                  <SelectContent>
                    {extensions?.map((ext) => (
                      <SelectItem key={ext.id} value={ext.id}>
                        {ext.extension_number} {ext.internal_cid_name ? `- ${ext.internal_cid_name}` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Input
                type="number"
                min={0}
                max={100}
                className="w-20"
                placeholder="Pos"
                {...register(`members.${index}.position`)}
              />
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : pageGroup ? t('paging.form.updateButton') : t('paging.form.createButton')}
      </Button>
    </form>
  )
}
