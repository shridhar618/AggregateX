import { useState } from 'react'
import Icon from './Icon'
import { applyTheme, getStoredTheme } from '../../lib/theme'

export default function ThemeToggle({ className = '' }) {
  const [theme, setTheme] = useState(getStoredTheme)
  const nextTheme = theme === 'dark' ? 'light' : 'dark'
  const label = `Switch to ${nextTheme} theme`

  const toggle = () => {
    const next = applyTheme(nextTheme)
    setTheme(next)
  }

  return (
    <button
      type="button"
      className={className}
      onClick={toggle}
      aria-label={label}
      title={label}
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
    </button>
  )
}
