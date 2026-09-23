import { useEffect, useRef } from 'react'
import { AppearanceSettings } from './AppearanceSettings'
import { useSettings } from './useSettings'

interface SettingsDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SettingsDrawer({ open, onOpenChange }: SettingsDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const { resetSettings } = useSettings()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      className="settings-dialog liquid-glass liquid-glass-elevated"
      aria-labelledby="settings-title"
      onClose={() => onOpenChange(false)}
      onClick={(event) => {
        if (event.target === dialogRef.current) onOpenChange(false)
      }}
    >
      <div className="settings-dialog-head">
        <div><span className="eyebrow">EventLens</span><h2 id="settings-title">Настройки</h2></div>
        <button className="dialog-close" type="button" aria-label="Закрыть настройки" onClick={() => onOpenChange(false)}>
          <span aria-hidden="true">×</span>
        </button>
      </div>
      <div className="settings-dialog-body"><AppearanceSettings /></div>
      <div className="settings-dialog-footer">
        <button className="reset-settings-button" type="button" onClick={resetSettings}>Сбросить настройки</button>
        <span>Настройки сохраняются на этом устройстве.</span>
      </div>
    </dialog>
  )
}
