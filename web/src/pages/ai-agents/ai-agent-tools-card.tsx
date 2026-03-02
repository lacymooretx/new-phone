import { useTranslation } from "react-i18next"
import { type UseFormReturn } from "react-hook-form"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  FormField,
  FormItem,
  FormDescription,
  FormMessage,
} from "@/components/ui/form"
import { Checkbox } from "@/components/ui/checkbox"
import { type AIAgentContextFormValues } from "./ai-agent-context-form-page"

interface AITool {
  id: string
  display_name: string
  description: string
}

interface AIAgentToolsCardProps {
  form: UseFormReturn<AIAgentContextFormValues>
  tools: AITool[] | undefined
}

export function AIAgentToolsCard({ form, tools }: AIAgentToolsCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("aiAgents.contexts.toolsSection")}</CardTitle>
      </CardHeader>
      <CardContent>
        <FormField
          control={form.control}
          name="available_tools"
          render={({ field }) => (
            <FormItem>
              <FormDescription>{t("aiAgents.contexts.formToolsHint")}</FormDescription>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mt-2">
                {tools && tools.length > 0 ? (
                  tools.map((tool) => (
                    <label
                      key={tool.id}
                      className="flex items-center gap-2 rounded-lg border p-3 cursor-pointer hover:bg-accent"
                    >
                      <Checkbox
                        checked={field.value.includes(tool.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            field.onChange([...field.value, tool.id])
                          } else {
                            field.onChange(field.value.filter((id) => id !== tool.id))
                          }
                        }}
                      />
                      <div>
                        <p className="text-sm font-medium">{tool.display_name}</p>
                        <p className="text-xs text-muted-foreground">{tool.description}</p>
                      </div>
                    </label>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground col-span-full">
                    {t("aiAgents.contexts.noToolsAvailable")}
                  </p>
                )}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
      </CardContent>
    </Card>
  )
}
