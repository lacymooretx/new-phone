import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useConversationMessages, useSendMessage, useConversationNotes, useCreateNote, type ConversationMessage, type ConversationNote } from "@/api/sms"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Skeleton } from "@/components/ui/skeleton"
import { Send, StickyNote, AlertCircle, Check, CheckCheck, Clock, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  return date.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "queued": return <Clock className="h-3 w-3 text-muted-foreground" />
    case "sent": return <Check className="h-3 w-3 text-muted-foreground" />
    case "delivered": return <CheckCheck className="h-3 w-3 text-green-500" />
    case "failed": return <AlertCircle className="h-3 w-3 text-destructive" />
    default: return null
  }
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isOutbound = message.direction === "outbound"
  return (
    <div className={cn("flex", isOutbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-3 py-2 text-sm",
          isOutbound
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground",
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.body}</p>
        <div className={cn("mt-1 flex items-center gap-1 text-xs", isOutbound ? "text-primary-foreground/70 justify-end" : "text-muted-foreground")}>
          <span>{formatTime(message.created_at)}</span>
          {isOutbound && <StatusIcon status={message.status} />}
        </div>
        {message.error_message && (
          <p className="mt-1 text-xs text-destructive">{message.error_message}</p>
        )}
        {isOutbound && message.sent_by_name && (
          <p className={cn("text-xs mt-0.5", isOutbound ? "text-primary-foreground/60" : "text-muted-foreground")}>
            {message.sent_by_name}
          </p>
        )}
      </div>
    </div>
  )
}

function NoteItem({ note }: { note: ConversationNote }) {
  return (
    <div className="flex gap-2 items-start border-l-2 border-yellow-400 pl-3 py-1">
      <StickyNote className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
      <div>
        <p className="text-sm">{note.body}</p>
        <p className="text-xs text-muted-foreground">
          {note.user_name} &middot; {formatTime(note.created_at)}
        </p>
      </div>
    </div>
  )
}

interface ConversationThreadProps {
  conversationId: string
}

export function ConversationThread({ conversationId }: ConversationThreadProps) {
  const { t } = useTranslation()
  const { data: messages, isLoading: messagesLoading } = useConversationMessages(conversationId)
  const { data: notes, isLoading: notesLoading } = useConversationNotes(conversationId)
  const sendMutation = useSendMessage()
  const noteMutation = useCreateNote()
  const [messageText, setMessageText] = useState("")
  const [noteText, setNoteText] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = () => {
    if (!messageText.trim()) return
    sendMutation.mutate(
      { conversationId, body: messageText.trim() },
      {
        onSuccess: () => { setMessageText(""); toast.success(t('smsConversations.messageSent', { defaultValue: 'Message sent' })) },
        onError: (err) => toast.error(err.message),
      },
    )
  }

  const handleSendNote = () => {
    if (!noteText.trim()) return
    noteMutation.mutate(
      { conversationId, body: noteText.trim() },
      {
        onSuccess: () => { setNoteText(""); toast.success(t('smsConversations.noteAdded', { defaultValue: 'Note added' })) },
        onError: (err) => toast.error(err.message),
      },
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (messagesLoading) {
    return (
      <div className="flex-1 p-4 space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className={cn("h-12 rounded-lg", i % 2 === 0 ? "w-2/3" : "w-1/2 ml-auto")} />
        ))}
      </div>
    )
  }

  return (
    <Tabs defaultValue="messages" className="flex flex-col flex-1 min-h-0">
      <TabsList className="mx-4 mt-2 w-fit">
        <TabsTrigger value="messages">{t('smsConversations.messages', { defaultValue: 'Messages' })}</TabsTrigger>
        <TabsTrigger value="notes">
          {t('smsConversations.notes', { defaultValue: 'Notes' })}
          {notes && notes.length > 0 && (
            <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0">
              {notes.length}
            </Badge>
          )}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="messages" className="flex flex-col flex-1 min-h-0 mt-0">
        {/* Message list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {!messages || messages.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">{t('smsConversations.noMessages')}</p>
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Compose bar */}
        <div className="border-t p-3 flex gap-2">
          <Input
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('smsConversations.typeMessage')}
            disabled={sendMutation.isPending}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={!messageText.trim() || sendMutation.isPending}
            size="icon"
          >
            {sendMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </TabsContent>

      <TabsContent value="notes" className="flex flex-col flex-1 min-h-0 mt-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {notesLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : !notes || notes.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">{t('smsConversations.noNotes', { defaultValue: 'No internal notes' })}</p>
          ) : (
            notes.map((note) => <NoteItem key={note.id} note={note} />)
          )}
        </div>

        <div className="border-t p-3 flex gap-2">
          <Textarea
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder={t('smsConversations.addNotePlaceholder', { defaultValue: 'Add an internal note...' })}
            rows={2}
            className="flex-1 resize-none"
          />
          <Button
            onClick={handleSendNote}
            disabled={!noteText.trim() || noteMutation.isPending}
            size="sm"
            variant="outline"
            className="self-end"
          >
            {noteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t('smsConversations.addNote', { defaultValue: 'Add Note' })}
          </Button>
        </div>
      </TabsContent>
    </Tabs>
  )
}
