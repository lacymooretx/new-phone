import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useTranslation } from "react-i18next"
import { useCreatePortRequest } from "@/api/port-requests"
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
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

const e164Regex = /^\+1\d{10}$/

const schema = z.object({
  numbers_text: z.string().min(1, "At least one number is required").refine(
    (val) => {
      const lines = val.split("\n").map((l) => l.trim()).filter(Boolean)
      return lines.length > 0 && lines.every((l) => e164Regex.test(l))
    },
    "Each line must be a valid E.164 number (e.g., +15125551234)"
  ),
  current_carrier: z.string().min(1, "Current carrier is required"),
  provider: z.string().min(1, "Provider is required"),
  requested_date: z.string().optional(),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreatePortRequestDialog({ open, onOpenChange }: Props) {
  const { t } = useTranslation()
  const createMutation = useCreatePortRequest()

  const form = useForm<FormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      numbers_text: "",
      current_carrier: "",
      provider: "clearlyip",
      requested_date: "",
      notes: "",
    },
  })

  const onSubmit = (data: FormValues) => {
    const numbers = data.numbers_text.split("\n").map((l) => l.trim()).filter(Boolean)
    createMutation.mutate(
      {
        numbers,
        current_carrier: data.current_carrier,
        provider: data.provider,
        requested_date: data.requested_date || null,
        notes: data.notes || null,
      },
      {
        onSuccess: () => {
          toast.success(t("portRequests.createSuccess"))
          form.reset()
          onOpenChange(false)
        },
        onError: (err) => toast.error(err.message),
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle>{t("portRequests.createTitle")}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="numbers_text"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("portRequests.form.numbers")}</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={4}
                      placeholder={"+15125551234\n+15125551235"}
                      className="font-mono text-sm"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>{t("portRequests.form.numbersHelp")}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="current_carrier"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("portRequests.form.carrier")}</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g., AT&T" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="provider"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("portRequests.form.provider")}</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
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
              name="requested_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("portRequests.form.requestedDate")}</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
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
                  <FormLabel>{t("portRequests.form.notes")}</FormLabel>
                  <FormControl>
                    <Textarea rows={2} placeholder={t("portRequests.form.notesPlaceholder")} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t("portRequests.form.submit")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
