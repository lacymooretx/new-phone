import { useForm, useWatch } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTranslation } from "react-i18next"
import { useProvisionTrunk, useActivateKeycode, type TrunkProvisionRequest, type KeycodeActivateRequest } from "@/api/sip-trunks"
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
import { Checkbox } from "@/components/ui/checkbox"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

// Discriminated union: ClearlyIP uses keycode, Twilio uses standard provisioning
const clearlyipSchema = z.object({
  provider: z.literal("clearlyip"),
  keycode: z.string().min(1, "Keycode is required"),
  name_prefix: z.string().min(1).max(100).optional(),
  import_dids: z.boolean().optional(),
})

const twilioSchema = z.object({
  provider: z.literal("twilio"),
  product_type: z.string().min(1, "Product type is required"),
  name: z.string().min(1, "Name is required"),
  region: z.string().min(1, "Region is required"),
  channels: z.coerce.number().int().min(1).max(1000).optional(),
})

const schema = z.discriminatedUnion("provider", [clearlyipSchema, twilioSchema])

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
  const activateKeycodeMutation = useActivateKeycode()

  const form = useForm<FormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      provider: "clearlyip",
      keycode: "",
      name_prefix: "ClearlyIP",
      import_dids: true,
    },
  })

  const selectedProvider = useWatch({ control: form.control, name: "provider" })

  const onSubmit = (data: FormValues) => {
    if (data.provider === "clearlyip") {
      const payload: KeycodeActivateRequest = {
        keycode: data.keycode,
        name_prefix: data.name_prefix || "ClearlyIP",
        import_dids: data.import_dids ?? true,
      }
      activateKeycodeMutation.mutate(payload, {
        onSuccess: (result) => {
          const msg = t("sipTrunks.keycodeActivateSuccess", {
            location: result.location_name,
            dids: result.imported_dids.length,
          })
          toast.success(msg)
          form.reset()
          onOpenChange(false)
        },
        onError: (err) => toast.error(err.message),
      })
    } else {
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
  }

  const isPending = provisionMutation.isPending || activateKeycodeMutation.isPending

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
                      // Reset form defaults for the selected provider
                      if (val === "clearlyip") {
                        form.reset({
                          provider: "clearlyip",
                          keycode: "",
                          name_prefix: "ClearlyIP",
                          import_dids: true,
                        })
                      } else {
                        form.reset({
                          provider: "twilio",
                          product_type: "elastic",
                          name: "",
                          region: "us-east",
                          channels: 30,
                        })
                      }
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

            {selectedProvider === "clearlyip" ? (
              <>
                <FormField
                  control={form.control}
                  name="keycode"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("sipTrunks.keycodeLabel")}</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder={t("sipTrunks.keycodePlaceholder")}
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>{t("sipTrunks.keycodeHelp")}</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="name_prefix"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("sipTrunks.namePrefixLabel")}</FormLabel>
                      <FormControl>
                        <Input placeholder="ClearlyIP" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="import_dids"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                      <div className="space-y-1 leading-none">
                        <FormLabel>{t("sipTrunks.importDidsLabel")}</FormLabel>
                        <FormDescription>{t("sipTrunks.importDidsHelp")}</FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
              </>
            ) : (
              <>
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
                          <SelectItem value="elastic">
                            {t("sipTrunks.productElastic")}
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription>{t("sipTrunks.productElasticHelp")}</FormDescription>
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
              </>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {selectedProvider === "clearlyip"
                  ? t("sipTrunks.keycodeActivateButton")
                  : t("sipTrunks.provisionButton")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
