import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { User, UserCreate } from "@/api/users"

const userSchema = z.object({
  email: z.email().max(320),
  password: z.string().min(8).max(128).optional().or(z.literal("")),
  first_name: z.string().min(1, "Required").max(100),
  last_name: z.string().min(1, "Required").max(100),
  role: z.enum(["msp_super_admin", "msp_tech", "tenant_admin", "tenant_manager", "tenant_user"]).default("tenant_user"),
  language: z.string().default("en"),
})

type FormValues = z.infer<typeof userSchema>

interface UserFormProps {
  user?: User | null
  onSubmit: (data: UserCreate) => void
  isLoading: boolean
}

export function UserForm({ user, onSubmit, isLoading }: UserFormProps) {
  const { t } = useTranslation()
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(userSchema) as any,
    defaultValues: {
      email: user?.email ?? "",
      password: "",
      first_name: user?.first_name ?? "",
      last_name: user?.last_name ?? "",
      role: (user?.role as FormValues["role"]) ?? "tenant_user",
      language: (user as any)?.language ?? "en",
    },
  })

  const submitHandler = (values: FormValues) => {
    const data: any = { ...values }
    if (!data.password) delete data.password
    onSubmit(data)
  }

  return (
    <form onSubmit={handleSubmit(submitHandler)} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name" required>{t('users.form.firstName')}</Label>
          <Input id="first_name" placeholder="John" {...register("first_name")} />
          {errors.first_name && <p className="text-xs text-destructive">{errors.first_name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name" required>{t('users.form.lastName')}</Label>
          <Input id="last_name" placeholder="Smith" {...register("last_name")} />
          {errors.last_name && <p className="text-xs text-destructive">{errors.last_name.message}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="email" required>{t('users.form.email')}</Label>
        <Input id="email" type="email" placeholder={t('users.form.emailPlaceholder')} {...register("email")} />
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>

      {!user && (
        <div className="space-y-2">
          <Label htmlFor="password" required>{t('users.form.password')}</Label>
          <Input id="password" type="password" placeholder={t('users.form.passwordPlaceholder')} {...register("password")} />
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>
      )}

      <div className="space-y-2">
        <Label>{t('users.form.role')}</Label>
        <Select value={watch("role")} onValueChange={(v) => setValue("role", v as FormValues["role"])}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="tenant_user">{t('users.roles.tenant_user')}</SelectItem>
            <SelectItem value="tenant_manager">{t('users.roles.tenant_manager')}</SelectItem>
            <SelectItem value="tenant_admin">{t('users.roles.tenant_admin')}</SelectItem>
            <SelectItem value="msp_tech">{t('users.roles.msp_tech')}</SelectItem>
            <SelectItem value="msp_super_admin">{t('users.roles.msp_super_admin')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>{t('users.form.language')}</Label>
        <Select value={watch("language")} onValueChange={(v) => setValue("language", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="en">{t('languages.en')}</SelectItem>
            <SelectItem value="es">{t('languages.es')}</SelectItem>
            <SelectItem value="fr">{t('languages.fr')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button type="submit" disabled={isLoading}>
        {isLoading ? t('common.saving') : user ? t('users.form.updateButton') : t('users.form.createButton')}
      </Button>
    </form>
  )
}
