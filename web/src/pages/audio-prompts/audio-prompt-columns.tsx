import type { ColumnDef } from "@tanstack/react-table"
import i18next from "i18next"
import type { AudioPrompt } from "@/api/audio-prompts"
import { DataTableColumnHeader } from "@/components/data-table/data-table-column-header"
import { StatusBadge } from "@/components/shared/status-badge"
import { AudioPlayer } from "@/components/shared/audio-player"
import { Badge } from "@/components/ui/badge"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreHorizontal, Trash2 } from "lucide-react"
import { useAudioPromptPlayback } from "@/api/audio-prompts"

interface ColumnActions {
  onDelete: (prompt: AudioPrompt) => void
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function PlaybackCell({ promptId }: { promptId: string }) {
  const { refetch } = useAudioPromptPlayback(promptId)
  return (
    <AudioPlayer
      fetchUrl={async () => {
        const result = await refetch()
        if (!result.data) throw new Error("No playback URL")
        return { url: result.data.url }
      }}
    />
  )
}

export function getAudioPromptColumns({ onDelete }: ColumnActions): ColumnDef<AudioPrompt, unknown>[] {
  return [
    {
      accessorKey: "name",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('audioPrompts.col.name')} />,
    },
    {
      id: "playback",
      header: i18next.t('softphone.call'),
      cell: ({ row }) => <PlaybackCell promptId={row.original.id} />,
    },
    {
      accessorKey: "category",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.type')} />,
      cell: ({ row }) => <Badge variant="outline">{row.original.category}</Badge>,
    },
    {
      accessorKey: "format",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.type')} />,
    },
    {
      accessorKey: "duration_seconds",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('audioPrompts.col.duration')} />,
      cell: ({ row }) => `${row.original.duration_seconds}s`,
    },
    {
      accessorKey: "file_size_bytes",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('audioPrompts.col.size')} />,
      cell: ({ row }) => formatFileSize(row.original.file_size_bytes),
    },
    {
      accessorKey: "is_active",
      header: ({ column }) => <DataTableColumnHeader column={column} title={i18next.t('common.status')} />,
      cell: ({ row }) => <StatusBadge active={row.original.is_active} />,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0" aria-label={i18next.t('common.actions')}>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onDelete(row.original)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" /> {i18next.t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]
}
