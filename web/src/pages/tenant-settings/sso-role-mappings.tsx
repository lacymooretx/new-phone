import { useState } from "react"
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
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ROLES } from "./sso-settings-card"

const roleMappingSchema = z.object({
  external_group_id: z.string().min(1, "Group ID is required"),
  external_group_name: z.string().optional(),
  pbx_role: z.string().min(1, "Role is required"),
})

type RoleMappingFormValues = z.infer<typeof roleMappingSchema>

interface RoleMapping {
  id: string
  external_group_id: string
  external_group_name: string | null
  pbx_role: string
}

interface SSORoleMappingsProps {
  roleMappings: RoleMapping[] | undefined
  onAddMapping: (data: RoleMappingFormValues) => Promise<void>
  isAddingMapping: boolean
  onDeleteMapping: (mappingId: string) => Promise<void>
  isDeletingMapping: boolean
}

export function SSORoleMappings({
  roleMappings,
  onAddMapping,
  isAddingMapping,
  onDeleteMapping,
  isDeletingMapping,
}: SSORoleMappingsProps) {
  const { t } = useTranslation()
  const [showAddMapping, setShowAddMapping] = useState(false)

  const mappingForm = useForm<RoleMappingFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(roleMappingSchema) as any,
    defaultValues: {
      external_group_id: "",
      external_group_name: "",
      pbx_role: "tenant_user",
    },
  })

  const handleAddMapping = async (data: RoleMappingFormValues) => {
    await onAddMapping(data)
    mappingForm.reset()
    setShowAddMapping(false)
  }

  return (
    <div className="space-y-4 pt-4 border-t">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">{t("sso.roleMappings")}</h4>
          <p className="text-sm text-muted-foreground">{t("sso.roleMappingsDescription")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowAddMapping(!showAddMapping)}>
          {showAddMapping ? t("common.cancel") : t("sso.addMapping")}
        </Button>
      </div>

      {showAddMapping && (
        <Form {...mappingForm}>
          <form onSubmit={mappingForm.handleSubmit(handleAddMapping)} className="flex gap-2 items-end">
            <FormField
              control={mappingForm.control}
              name="external_group_id"
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormLabel>{t("sso.groupId")}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={t("sso.groupIdPlaceholder")} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={mappingForm.control}
              name="external_group_name"
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormLabel>{t("sso.groupName")}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={t("sso.groupNamePlaceholder")} />
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={mappingForm.control}
              name="pbx_role"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sso.role")}</FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger className="w-[160px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((role) => (
                          <SelectItem key={role.value} value={role.value}>
                            {role.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                </FormItem>
              )}
            />
            <Button type="submit" size="sm" disabled={isAddingMapping}>
              {t("sso.addMapping")}
            </Button>
          </form>
        </Form>
      )}

      {roleMappings && roleMappings.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("sso.groupId")}</TableHead>
              <TableHead>{t("sso.groupName")}</TableHead>
              <TableHead>{t("sso.role")}</TableHead>
              <TableHead className="w-[80px]">{t("common.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roleMappings.map((mapping) => (
              <TableRow key={mapping.id}>
                <TableCell className="font-mono text-sm">{mapping.external_group_id}</TableCell>
                <TableCell>{mapping.external_group_name || "\u2014"}</TableCell>
                <TableCell>{ROLES.find((r) => r.value === mapping.pbx_role)?.label || mapping.pbx_role}</TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDeleteMapping(mapping.id)}
                    disabled={isDeletingMapping}
                  >
                    {t("common.delete")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-muted-foreground">{t("sso.noMappings")}</p>
      )}
    </div>
  )
}
