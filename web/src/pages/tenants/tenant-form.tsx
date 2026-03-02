import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import type { Tenant } from "@/api/tenants"

const tenantSchema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z
    .string()
    .min(1, "Slug is required")
    .regex(/^[a-z0-9-]+$/, "Slug must be lowercase alphanumeric with hyphens"),
  domain: z.string().nullable().optional(),
  sip_domain: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  default_language: z.string().default("en"),
})

export type TenantFormValues = z.infer<typeof tenantSchema>

interface TenantFormProps {
  tenant: Tenant | null
  onSubmit: (data: TenantFormValues) => void
  isLoading: boolean
}

function nameToSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

export function TenantForm({ tenant, onSubmit, isLoading }: TenantFormProps) {
  const { t } = useTranslation()
  const isEdit = !!tenant

  const form = useForm<TenantFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(tenantSchema) as any,
    defaultValues: {
      name: tenant?.name ?? "",
      slug: tenant?.slug ?? "",
      domain: tenant?.domain ?? "",
      sip_domain: tenant?.sip_domain ?? "",
      notes: tenant?.notes ?? "",
      default_language: (tenant as any)?.default_language ?? "en",
    },
  })

  const submitHandler = (values: TenantFormValues) => {
    const data: TenantFormValues = {
      ...values,
      domain: values.domain || null,
      sip_domain: values.sip_domain || null,
      notes: values.notes || null,
    }
    onSubmit(data)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(submitHandler)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>{t('tenants.form.name')}</FormLabel>
              <FormControl>
                <Input
                  placeholder={t('tenants.form.namePlaceholder')}
                  {...field}
                  onChange={(e) => {
                    field.onChange(e)
                    if (!isEdit) {
                      form.setValue("slug", nameToSlug(e.target.value))
                    }
                  }}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="slug"
          render={({ field }) => (
            <FormItem>
              <FormLabel required>{t('tenants.form.slug')}</FormLabel>
              <FormControl>
                <Input placeholder={t('tenants.form.slugPlaceholder')} {...field} className="font-mono" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="domain"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tenants.form.domain')}</FormLabel>
              <FormControl>
                <Input placeholder={t('tenants.form.domainPlaceholder')} {...field} value={field.value ?? ""} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="sip_domain"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tenants.form.sipDomain')}</FormLabel>
              <FormControl>
                <Input placeholder={t('tenants.form.sipDomainPlaceholder')} {...field} value={field.value ?? ""} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tenants.form.notes')}</FormLabel>
              <FormControl>
                <Textarea placeholder={t('tenants.form.notesPlaceholder')} {...field} value={field.value ?? ""} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="default_language"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('tenants.form.defaultLanguage')}</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="en">{t('languages.en')}</SelectItem>
                  <SelectItem value="es">{t('languages.es')}</SelectItem>
                  <SelectItem value="fr">{t('languages.fr')}</SelectItem>
                </SelectContent>
              </Select>
              <FormDescription>{t('tenants.form.defaultLanguageDescription')}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={isLoading}>
          {isLoading ? t('common.saving') : isEdit ? t('common.saveChanges') : t('tenants.createTenant')}
        </Button>
      </form>
    </Form>
  )
}
