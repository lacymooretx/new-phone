import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTranslation } from "react-i18next"
import { useSearchDids, usePurchaseDid, type DIDSearchResult, type DIDSearchParams } from "@/api/dids"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Loader2, Search } from "lucide-react"
import { toast } from "sonner"

const searchSchema = z.object({
  area_code: z.string().regex(/^\d{3}$/, "Must be 3 digits").optional().or(z.literal("")),
  state: z.string().optional(),
  quantity: z.coerce.number().int().min(1).max(50).optional(),
  provider: z.string().optional(),
})

type SearchFormValues = z.infer<typeof searchSchema>

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC",
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function DidMarketplaceDialog({ open, onOpenChange }: Props) {
  const { t } = useTranslation()
  const purchaseMutation = usePurchaseDid()
  const [searchParams, setSearchParams] = useState<DIDSearchParams>({})
  const [searchEnabled, setSearchEnabled] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [purchasing, setPurchasing] = useState(false)

  const { data: results, isLoading: searching } = useSearchDids(searchParams, searchEnabled)

  const form = useForm<SearchFormValues>({
    resolver: zodResolver(searchSchema),
    defaultValues: { area_code: "", state: "", quantity: 10, provider: "" },
  })

  const onSearch = (data: SearchFormValues) => {
    const params: DIDSearchParams = {}
    if (data.area_code) params.area_code = data.area_code
    if (data.state) params.state = data.state
    if (data.quantity) params.quantity = data.quantity
    if (data.provider) params.provider = data.provider
    setSearchParams(params)
    setSearchEnabled(true)
    setSelected(new Set())
  }

  const toggleSelect = (number: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(number)) next.delete(number)
      else next.add(number)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (!results) return
    if (selected.size === results.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(results.map((r) => r.number)))
    }
  }

  const handlePurchase = async () => {
    if (selected.size === 0) return
    const numbers = Array.from(selected)
    setPurchasing(true)
    let successCount = 0
    let errorCount = 0

    for (const number of numbers) {
      const result = results?.find((r) => r.number === number)
      try {
        await purchaseMutation.mutateAsync({
          number,
          provider: result?.provider ?? searchParams.provider ?? "clearlyip",
        })
        successCount++
      } catch {
        errorCount++
      }
    }

    setPurchasing(false)
    if (successCount > 0) toast.success(t("dids.purchaseSuccess", { count: successCount }))
    if (errorCount > 0) toast.error(t("dids.purchaseErrors", { count: errorCount }))
    if (errorCount === 0) {
      setSelected(new Set())
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>{t("dids.marketplaceTitle")}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSearch)} className="flex items-end gap-3 flex-wrap">
            <FormField
              control={form.control}
              name="area_code"
              render={({ field }) => (
                <FormItem className="flex-1 min-w-[100px]">
                  <FormLabel>{t("dids.marketplaceAreaCode")}</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., 512" maxLength={3} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="state"
              render={({ field }) => (
                <FormItem className="flex-1 min-w-[120px]">
                  <FormLabel>{t("dids.marketplaceState")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("dids.marketplaceAnyState")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value=" ">{t("dids.marketplaceAnyState")}</SelectItem>
                      {US_STATES.map((st) => (
                        <SelectItem key={st} value={st}>{st}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="quantity"
              render={({ field }) => (
                <FormItem className="w-[100px]">
                  <FormLabel>{t("dids.marketplaceQuantity")}</FormLabel>
                  <Select onValueChange={field.onChange} value={String(field.value)}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {[5, 10, 25, 50].map((n) => (
                        <SelectItem key={n} value={String(n)}>{n}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="provider"
              render={({ field }) => (
                <FormItem className="flex-1 min-w-[120px]">
                  <FormLabel>{t("dids.marketplaceProvider")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder={t("dids.marketplaceAnyProvider")} />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value=" ">{t("dids.marketplaceAnyProvider")}</SelectItem>
                      <SelectItem value="clearlyip">ClearlyIP</SelectItem>
                      <SelectItem value="twilio">Twilio</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={searching}>
              {searching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              {t("dids.marketplaceSearch")}
            </Button>
          </form>
        </Form>

        <div className="flex-1 overflow-auto mt-4 border rounded-md">
          {searching && (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
          {!searching && results && results.length === 0 && (
            <div className="flex items-center justify-center h-32 text-muted-foreground">
              {t("dids.marketplaceNoResults")}
            </div>
          )}
          {!searching && results && results.length > 0 && (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-muted/50 border-b">
                <tr>
                  <th className="p-2 text-left w-10">
                    <Checkbox
                      checked={selected.size === results.length && results.length > 0}
                      onCheckedChange={toggleSelectAll}
                    />
                  </th>
                  <th className="p-2 text-left">{t("dids.marketplaceColNumber")}</th>
                  <th className="p-2 text-left">{t("dids.marketplaceColMonthlyCost")}</th>
                  <th className="p-2 text-left">{t("dids.marketplaceColSetupCost")}</th>
                  <th className="p-2 text-left">{t("dids.marketplaceColCapabilities")}</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r: DIDSearchResult) => (
                  <tr key={r.number} className="border-b hover:bg-muted/30 cursor-pointer" onClick={() => toggleSelect(r.number)}>
                    <td className="p-2">
                      <Checkbox checked={selected.has(r.number)} onCheckedChange={() => toggleSelect(r.number)} />
                    </td>
                    <td className="p-2 font-mono">{r.number}</td>
                    <td className="p-2">${r.monthly_cost.toFixed(2)}/mo</td>
                    <td className="p-2">${r.setup_cost.toFixed(2)}</td>
                    <td className="p-2 space-x-1">
                      {r.capabilities.map((cap) => (
                        <Badge key={cap} variant="secondary" className="text-xs">{cap}</Badge>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button onClick={handlePurchase} disabled={selected.size === 0 || purchasing}>
            {purchasing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("dids.marketplacePurchase", { count: selected.size })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
