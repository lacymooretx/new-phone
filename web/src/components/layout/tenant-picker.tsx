import { useAuthStore } from "@/stores/auth-store"
import { useTenants } from "@/api/tenants"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function TenantPicker() {
  const { activeTenantId, setActiveTenant } = useAuthStore()
  const { data: tenants } = useTenants()

  if (!tenants?.length) return null

  return (
    <Select value={activeTenantId ?? undefined} onValueChange={setActiveTenant}>
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="Select tenant" />
      </SelectTrigger>
      <SelectContent>
        {tenants.map((t) => (
          <SelectItem key={t.id} value={t.id}>
            {t.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
