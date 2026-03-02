import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useConversations,
  useUpdateConversation,
  useClaimConversation,
  useReleaseConversation,
  useReassignConversation,
  type Conversation,
} from "@/api/sms"
import { useQueues } from "@/api/queues"
import { useUsers } from "@/api/users"
import { useAuthStore } from "@/stores/auth-store"
import { PageHeader } from "@/components/shared/page-header"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { MessageSquare, User, UserPlus, UserMinus, Users } from "lucide-react"
import { EmptyState } from "@/components/shared/empty-state"
import { ConversationThread } from "./conversation-thread"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

const STATE_OPTIONS = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "waiting", label: "Waiting" },
  { value: "resolved", label: "Resolved" },
  { value: "archived", label: "Archived" },
]

const STATE_COLORS: Record<string, string> = {
  open: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  waiting: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  resolved: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  archived: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return ""
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return "just now"
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString([], { month: "short", day: "numeric" })
}

function ConversationListItem({
  conversation,
  isSelected,
  onClick,
}: {
  conversation: Conversation
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left px-4 py-3 border-b hover:bg-accent/50 transition-colors",
        isSelected && "bg-accent",
        !conversation.assigned_to_user_id && conversation.queue_id && "border-l-2 border-l-orange-400",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{conversation.remote_number}</span>
            <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0", STATE_COLORS[conversation.state])}>
              {conversation.state}
            </Badge>
          </div>
          {conversation.last_message_preview && (
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {conversation.last_message_preview}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            {conversation.did_number && <span>{conversation.did_number}</span>}
            {conversation.queue_name && (
              <>
                <span>&middot;</span>
                <Badge variant="secondary" className="text-[10px] px-1 py-0">
                  {conversation.queue_name}
                </Badge>
              </>
            )}
            {conversation.assigned_to_name && (
              <>
                <span>&middot;</span>
                <span className="flex items-center gap-0.5">
                  <User className="h-3 w-3" />
                  {conversation.assigned_to_name}
                </span>
              </>
            )}
          </div>
        </div>
        <span className="text-xs text-muted-foreground whitespace-nowrap">
          {formatRelativeTime(conversation.last_message_at)}
        </span>
      </div>
    </button>
  )
}

export function SMSConversationsPage() {
  const { t } = useTranslation()
  const [stateFilter, setStateFilter] = useState("all")
  const [queueFilter, setQueueFilter] = useState("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const currentUserId = useAuthStore((s) => s.user?.id)
  const currentUserRole = useAuthStore((s) => s.user?.role)

  const updateMutation = useUpdateConversation()
  const claimMutation = useClaimConversation()
  const releaseMutation = useReleaseConversation()
  const reassignMutation = useReassignConversation()

  const { data: queues } = useQueues()
  const { data: users } = useUsers()

  const { data: conversations, isLoading, isError, error } = useConversations(
    stateFilter === "all" ? undefined : stateFilter,
    queueFilter === "all" ? undefined : queueFilter,
  )

  const selected = conversations?.find((c) => c.id === selectedId) ?? null

  const isSupervisor = currentUserRole === "msp_super_admin" || currentUserRole === "msp_tech" || currentUserRole === "tenant_admin"

  const handleStateChange = (conversationId: string, newState: string) => {
    updateMutation.mutate(
      { conversationId, state: newState },
      {
        onSuccess: () => toast.success(t('smsConversations.stateChanged', { defaultValue: 'Conversation {{state}}', state: newState })),
        onError: (err) => toast.error(err.message),
      },
    )
  }

  const handleClaim = (conversationId: string) => {
    claimMutation.mutate(conversationId, {
      onSuccess: () => toast.success(t('smsConversations.claimed', { defaultValue: 'Conversation claimed' })),
      onError: (err) => toast.error(err.message),
    })
  }

  const handleRelease = (conversationId: string) => {
    releaseMutation.mutate(conversationId, {
      onSuccess: () => toast.success(t('smsConversations.released', { defaultValue: 'Conversation released' })),
      onError: (err) => toast.error(err.message),
    })
  }

  const handleReassign = (conversationId: string, userId: string) => {
    reassignMutation.mutate(
      { conversationId, userId },
      {
        onSuccess: () => toast.success(t('smsConversations.reassigned', { defaultValue: 'Conversation reassigned' })),
        onError: (err) => toast.error(err.message),
      },
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="px-6 pt-6 pb-3">
        <PageHeader title={t('smsConversations.title', { defaultValue: 'Conversations' })} description={t('smsConversations.description')} breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "SMS" }, { label: "Conversations" }]} />
      </div>

      {isError && (
        <div className="mx-6 mb-3 rounded-md border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {t('common.failedToLoad', { message: error?.message || t('common.unknownError') })}
        </div>
      )}

      <div className="flex-1 flex min-h-0 border-t">
        {/* Left panel: conversation list */}
        <div className="w-80 border-r flex flex-col min-h-0 shrink-0">
          <div className="p-3 border-b space-y-2">
            <Select value={stateFilter} onValueChange={setStateFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={queueFilter} onValueChange={setQueueFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder={t('smsConversations.allQueues', { defaultValue: 'All Queues' })} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('smsConversations.allQueues', { defaultValue: 'All Queues' })}</SelectItem>
                {queues?.map((q) => (
                  <SelectItem key={q.id} value={q.id}>
                    {q.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="space-y-0">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 border-b">
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                ))}
              </div>
            ) : !conversations || conversations.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <EmptyState
                  icon={MessageSquare}
                  title={t('smsConversations.emptyTitle')}
                  description={stateFilter === "all" ? t('smsConversations.emptyDescription') : t('smsConversations.noStateConversations', { defaultValue: 'No {{state}} conversations.', state: stateFilter })}
                />
              </div>
            ) : (
              conversations.map((conv) => (
                <ConversationListItem
                  key={conv.id}
                  conversation={conv}
                  isSelected={selectedId === conv.id}
                  onClick={() => setSelectedId(conv.id)}
                />
              ))
            )}
          </div>
        </div>

        {/* Right panel: thread view */}
        <div className="flex-1 flex flex-col min-h-0">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">{t('smsConversations.selectConversation')}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Conversation header */}
              <div className="flex items-center justify-between px-4 py-3 border-b">
                <div>
                  <h3 className="font-semibold text-sm">{selected.remote_number}</h3>
                  <p className="text-xs text-muted-foreground">
                    {t('smsConversations.did', { defaultValue: 'DID' })}: {selected.did_number || t('common.unknownError', { defaultValue: 'Unknown' })} &middot; {selected.channel.toUpperCase()}
                    {selected.queue_name && (
                      <> &middot; {t('smsConversations.queue', { defaultValue: 'Queue' })}: {selected.queue_name}</>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Assignment controls */}
                  {!selected.assigned_to_user_id && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs"
                      onClick={() => handleClaim(selected.id)}
                      disabled={claimMutation.isPending}
                    >
                      <UserPlus className="h-3 w-3 mr-1" />
                      {t('smsConversations.claim', { defaultValue: 'Claim' })}
                    </Button>
                  )}
                  {selected.assigned_to_user_id === currentUserId && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs"
                      onClick={() => handleRelease(selected.id)}
                      disabled={releaseMutation.isPending}
                    >
                      <UserMinus className="h-3 w-3 mr-1" />
                      {t('smsConversations.release', { defaultValue: 'Release' })}
                    </Button>
                  )}
                  {isSupervisor && selected.assigned_to_user_id && (
                    <Select
                      value={selected.assigned_to_user_id}
                      onValueChange={(val) => handleReassign(selected.id, val)}
                    >
                      <SelectTrigger className="h-7 text-xs w-36">
                        <Users className="h-3 w-3 mr-1" />
                        <SelectValue placeholder={t('smsConversations.reassign', { defaultValue: 'Reassign' })} />
                      </SelectTrigger>
                      <SelectContent>
                        {users
                          ?.filter((u) => u.is_active && u.id !== selected.assigned_to_user_id)
                          .map((u) => (
                            <SelectItem key={u.id} value={u.id}>
                              {u.first_name} {u.last_name}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  )}

                  <Select
                    value={selected.state}
                    onValueChange={(val) => handleStateChange(selected.id, val)}
                  >
                    <SelectTrigger className="h-7 text-xs w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">{t('smsConversations.stateOpen', { defaultValue: 'Open' })}</SelectItem>
                      <SelectItem value="waiting">{t('smsConversations.stateWaiting', { defaultValue: 'Waiting' })}</SelectItem>
                      <SelectItem value="resolved">{t('smsConversations.stateResolved', { defaultValue: 'Resolved' })}</SelectItem>
                      <SelectItem value="archived">{t('smsConversations.stateArchived', { defaultValue: 'Archived' })}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Thread */}
              <ConversationThread conversationId={selected.id} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
