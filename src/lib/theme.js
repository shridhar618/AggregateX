import { useEffect, useState } from 'react'

export const THEME_KEY = 'revelio.theme'
const THEME_EVENT = 'revelio-theme'
export const THEMES = ['dark', 'light']

export function getStoredTheme() {
  try {
    const stored = window.localStorage.getItem(THEME_KEY)
    return THEMES.includes(stored) ? stored : 'dark'
  } catch {
    return 'dark'
  }
}

export function applyTheme(theme) {
  const nextTheme = THEMES.includes(theme) ? theme : 'dark'
  document.documentElement.dataset.theme = nextTheme
  try {
    window.localStorage.setItem(THEME_KEY, nextTheme)
  } catch {
    // Theme remains active for the current session when storage is unavailable.
  }
  window.dispatchEvent(new CustomEvent(THEME_EVENT, { detail: nextTheme }))
  return nextTheme
}

// Current theme, kept in sync across every control that changes it.
export function useTheme() {
  const [theme, setTheme] = useState(getStoredTheme)
  useEffect(() => {
    const sync = (e) => setTheme(e.detail)
    window.addEventListener(THEME_EVENT, sync)
    return () => window.removeEventListener(THEME_EVENT, sync)
  }, [])
  return [theme, applyTheme]
}

export function initializeTheme() {
  document.documentElement.dataset.theme = getStoredTheme()
}
