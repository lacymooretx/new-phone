import { useState, useCallback } from "react"

/**
 * Hook that intercepts dialog close when form has unsaved changes.
 * Returns a wrapper for onOpenChange that shows a confirmation step.
 */
export function useConfirmClose(isDirty: boolean) {
  const [showConfirm, setShowConfirm] = useState(false)

  const handleOpenChange = useCallback(
    (open: boolean, setOpen: (v: boolean) => void) => {
      if (!open && isDirty) {
        setShowConfirm(true)
      } else {
        setShowConfirm(false)
        setOpen(open)
      }
    },
    [isDirty]
  )

  const confirmClose = useCallback(
    (setOpen: (v: boolean) => void) => {
      setShowConfirm(false)
      setOpen(false)
    },
    []
  )

  const cancelClose = useCallback(() => {
    setShowConfirm(false)
  }, [])

  return { showConfirm, handleOpenChange, confirmClose, cancelClose }
}
