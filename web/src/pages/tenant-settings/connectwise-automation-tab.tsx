import { useTranslation } from "react-i18next"
import { type UseFormReturn } from "react-hook-form"
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
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TabsContent } from "@/components/ui/tabs"
import { type AutomationFormValues } from "./connectwise-settings-card"

interface CWBoard {
  id: number
  name: string
}

interface CWBoardStatus {
  id: number
  name: string
}

interface CWBoardType {
  id: number
  name: string
}

interface ConnectWiseAutomationTabProps {
  automationForm: UseFormReturn<AutomationFormValues>
  boards: CWBoard[] | undefined
  boardStatuses: CWBoardStatus[] | undefined
  boardTypes: CWBoardType[] | undefined
  selectedBoardId: number | null
  isSaving: boolean
  onSubmit: (data: AutomationFormValues) => Promise<void>
}

export function ConnectWiseAutomationTab({
  automationForm,
  boards,
  boardStatuses,
  boardTypes,
  selectedBoardId,
  isSaving,
  onSubmit,
}: ConnectWiseAutomationTabProps) {
  const { t } = useTranslation()

  return (
    <TabsContent value="automation" className="space-y-4">
      <Form {...automationForm}>
        <form onSubmit={automationForm.handleSubmit(onSubmit)} className="space-y-4 max-w-lg">
          <FormField
            control={automationForm.control}
            name="auto_ticket_missed_calls"
            render={({ field }) => (
              <FormItem className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-0.5">
                  <FormLabel>{t("connectwise.autoTicketMissedCalls")}</FormLabel>
                  <FormDescription>{t("connectwise.autoTicketMissedCallsHint")}</FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={automationForm.control}
            name="auto_ticket_voicemails"
            render={({ field }) => (
              <FormItem className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-0.5">
                  <FormLabel>{t("connectwise.autoTicketVoicemails")}</FormLabel>
                  <FormDescription>{t("connectwise.autoTicketVoicemailsHint")}</FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={automationForm.control}
            name="auto_ticket_completed_calls"
            render={({ field }) => (
              <FormItem className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-0.5">
                  <FormLabel>{t("connectwise.autoTicketCompletedCalls")}</FormLabel>
                  <FormDescription>{t("connectwise.autoTicketCompletedCallsHint")}</FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={automationForm.control}
            name="min_call_duration_seconds"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.minCallDuration")}</FormLabel>
                <FormControl>
                  <Input {...field} type="number" min={0} />
                </FormControl>
                <FormDescription>{t("connectwise.minCallDurationHint")}</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={automationForm.control}
            name="default_board_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.defaultBoard")}</FormLabel>
                <FormControl>
                  <Select
                    value={field.value?.toString() ?? ""}
                    onValueChange={(v) => field.onChange(v ? Number(v) : null)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("connectwise.selectBoard")} />
                    </SelectTrigger>
                    <SelectContent>
                      {boards?.map((board) => (
                        <SelectItem key={board.id} value={board.id.toString()}>
                          {board.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={automationForm.control}
            name="default_status_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.defaultStatus")}</FormLabel>
                <FormControl>
                  <Select
                    value={field.value?.toString() ?? ""}
                    onValueChange={(v) => field.onChange(v ? Number(v) : null)}
                    disabled={!selectedBoardId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("connectwise.selectStatus")} />
                    </SelectTrigger>
                    <SelectContent>
                      {boardStatuses?.map((s) => (
                        <SelectItem key={s.id} value={s.id.toString()}>
                          {s.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={automationForm.control}
            name="default_type_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("connectwise.defaultType")}</FormLabel>
                <FormControl>
                  <Select
                    value={field.value?.toString() ?? ""}
                    onValueChange={(v) => field.onChange(v ? Number(v) : null)}
                    disabled={!selectedBoardId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t("connectwise.selectType")} />
                    </SelectTrigger>
                    <SelectContent>
                      {boardTypes?.map((bt) => (
                        <SelectItem key={bt.id} value={bt.id.toString()}>
                          {bt.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" disabled={isSaving}>
            {isSaving ? t("common.saving") : t("common.save")}
          </Button>
        </form>
      </Form>
    </TabsContent>
  )
}
