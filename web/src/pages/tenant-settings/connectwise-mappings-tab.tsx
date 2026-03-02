import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useForm } from "react-hook-form"
import { z } from "zod/v4"
import { zodResolver } from "@hookform/resolvers/zod"
import { useCWCompanySearch } from "@/api/connectwise"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { TabsContent } from "@/components/ui/tabs"

// Mapping form schema
const mappingSchema = z.object({
  cw_company_id: z.coerce.number().int().min(1, "Company is required"),
  cw_company_name: z.string().min(1, "Company name is required"),
  extension_id: z.string().nullable().optional(),
  did_id: z.string().nullable().optional(),
})

type MappingFormValues = z.infer<typeof mappingSchema>

interface CWCompanyMapping {
  id: string
  cw_company_id: number
  cw_company_name: string
  extension_id: string | null
  did_id: string | null
}

interface ConnectWiseMappingsTabProps {
  mappings: CWCompanyMapping[] | undefined
  onAddMapping: (data: {
    cw_company_id: number
    cw_company_name: string
    extension_id: string | null
    did_id: string | null
  }) => Promise<void>
  isAddingMapping: boolean
  onDeleteMapping: (mappingId: string) => Promise<void>
  isDeletingMapping: boolean
}

export function ConnectWiseMappingsTab({
  mappings,
  onAddMapping,
  isAddingMapping,
  onDeleteMapping,
  isDeletingMapping,
}: ConnectWiseMappingsTabProps) {
  const { t } = useTranslation()
  const [showAddMapping, setShowAddMapping] = useState(false)
  const [companySearchQuery, setCompanySearchQuery] = useState("")
  const { data: companyResults } = useCWCompanySearch(companySearchQuery)

  const mappingForm = useForm<MappingFormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(mappingSchema) as any,
    defaultValues: {
      cw_company_id: 0,
      cw_company_name: "",
      extension_id: null,
      did_id: null,
    },
  })

  const handleAddMapping = async (data: MappingFormValues) => {
    await onAddMapping({
      cw_company_id: data.cw_company_id,
      cw_company_name: data.cw_company_name,
      extension_id: data.extension_id || null,
      did_id: data.did_id || null,
    })
    mappingForm.reset()
    setShowAddMapping(false)
    setCompanySearchQuery("")
  }

  return (
    <TabsContent value="mappings" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">{t("connectwise.companyMappings")}</h4>
          <p className="text-sm text-muted-foreground">{t("connectwise.companyMappingsDescription")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowAddMapping(!showAddMapping)}>
          {showAddMapping ? t("common.cancel") : t("connectwise.addMapping")}
        </Button>
      </div>

      {showAddMapping && (
        <Form {...mappingForm}>
          <form onSubmit={mappingForm.handleSubmit(handleAddMapping)} className="space-y-3 rounded-lg border p-4">
            <div className="space-y-2">
              <FormLabel>{t("connectwise.searchCompany")}</FormLabel>
              <Input
                placeholder={t("connectwise.searchCompanyPlaceholder")}
                value={companySearchQuery}
                onChange={(e) => setCompanySearchQuery(e.target.value)}
              />
              {companyResults && companyResults.length > 0 && (
                <div className="max-h-40 overflow-y-auto rounded border">
                  {companyResults.map((company) => (
                    <button
                      key={company.id}
                      type="button"
                      className="w-full text-left px-3 py-2 hover:bg-accent text-sm"
                      onClick={() => {
                        mappingForm.setValue("cw_company_id", company.id)
                        mappingForm.setValue("cw_company_name", company.name)
                        setCompanySearchQuery(company.name)
                      }}
                    >
                      <span className="font-medium">{company.name}</span>
                      <span className="text-muted-foreground ml-2">({company.identifier})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={mappingForm.control}
                name="extension_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("connectwise.extension")}</FormLabel>
                    <FormControl>
                      <Input {...field} value={field.value ?? ""} placeholder={t("connectwise.extensionPlaceholder")} />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={mappingForm.control}
                name="did_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("connectwise.did")}</FormLabel>
                    <FormControl>
                      <Input {...field} value={field.value ?? ""} placeholder={t("connectwise.didPlaceholder")} />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>
            <Button type="submit" size="sm" disabled={isAddingMapping}>
              {t("connectwise.addMapping")}
            </Button>
          </form>
        </Form>
      )}

      {mappings && mappings.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("connectwise.cwCompany")}</TableHead>
              <TableHead>{t("connectwise.extension")}</TableHead>
              <TableHead>{t("connectwise.did")}</TableHead>
              <TableHead className="w-[80px]">{t("common.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mappings.map((mapping) => (
              <TableRow key={mapping.id}>
                <TableCell>
                  <span className="font-medium">{mapping.cw_company_name}</span>
                  <span className="text-muted-foreground ml-1 text-xs">#{mapping.cw_company_id}</span>
                </TableCell>
                <TableCell>{mapping.extension_id || "\u2014"}</TableCell>
                <TableCell>{mapping.did_id || "\u2014"}</TableCell>
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
        <p className="text-sm text-muted-foreground">{t("connectwise.noMappings")}</p>
      )}
    </TabsContent>
  )
}
