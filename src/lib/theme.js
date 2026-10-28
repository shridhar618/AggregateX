export const THEME_KEY = 'revelio.theme'
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
  return nextTheme
}

export function initializeTheme() {
  document.documentElement.dataset.theme = getStoredTheme()
}
