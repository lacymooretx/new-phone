import { useForm, useWatch } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTranslation } from "react-i18next"
import { useProvisionTrunk, type TrunkProvisionRequest } from "@/api/sip-trunks"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
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
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

const schema = z.object({
  provider: z.enum(["clearlyip", "twilio"]),
  product_type: z.string().min(1, "Product type is required"),
  name: z.string().min(1, "Name is required"),
  region: z.string().min(1, "Region is required"),
  channels: z.coerce.number().int().min(1).max(1000).optional(),
})

type FormValues = z.infer<typeof schema>

const REGIONS = [
  { value: "us-east", label: "US East" },
  { value: "us-west", label: "US West" },
  { value: "us-central", label: "US Central" },
  { value: "eu-west", label: "EU West" },
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ProvisionTrunkDialog({ open, onOpenChange }: Props) {
  const { t } = useTranslation()
  const provisionMutation = useProvisionTrunk()

  const form = useForm<FormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      provider: "clearlyip",
      product_type: "metered",
      name: "",
      region: "us-east",
      channels: 30,
    },
  })

  const selectedProvider = useWatch({ control: form.control, name: "provider" })

  const onSubmit = (data: FormValues) => {
    const payload: TrunkProvisionRequest = {
      provider: data.provider,
      name: data.name,
      region: data.region,
      channels: data.channels,
      config: { product_type: data.product_type },
    }
    provisionMutation.mutate(payload, {
      onSuccess: () => {
        toast.success(t("sipTrunks.provisionSuccess"))
        form.reset()
        onOpenChange(false)
      },
      onError: (err) => toast.error(err.message),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>{t("sipTrunks.provisionTitle")}</DialogTitle>
          <DialogDescription>{t("sipTrunks.provisionDescription")}</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="provider"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sipTrunks.provisionProvider")}</FormLabel>
                  <Select
                    onValueChange={(val) => {
                      field.onChange(val)
                      // Reset product type when provider changes
                      form.setValue("product_type", val === "clearlyip" ? "metered" : "elastic")
                    }}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="clearlyip">ClearlyIP</SelectItem>
                      <SelectItem value="twilio">Twilio</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="product_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sipTrunks.provisionProductType")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {selectedProvider === "clearlyip" ? (
                        <>
                          <SelectItem value="metered">
                            {t("sipTrunks.productMetered")}
                          </SelectItem>
                          <SelectItem value="unmetered">
                            {t("sipTrunks.productUnmetered")}
                          </SelectItem>
                        </>
                      ) : (
                        <SelectItem value="elastic">
                          {t("sipTrunks.productElastic")}
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    {selectedProvider === "clearlyip"
                      ? field.value === "metered"
                        ? t("sipTrunks.productMeteredHelp")
                        : t("sipTrunks.productUnmeteredHelp")
                      : t("sipTrunks.productElasticHelp")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sipTrunks.form.name")}</FormLabel>
                  <FormControl>
                    <Input placeholder={t("sipTrunks.form.namePlaceholder")} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="region"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sipTrunks.provisionRegion")}</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {REGIONS.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="channels"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("sipTrunks.provisionChannels")}</FormLabel>
                  <FormControl>
                    <Input type="number" min={1} max={1000} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={provisionMutation.isPending}>
                {provisionMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t("sipTrunks.provisionButton")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
