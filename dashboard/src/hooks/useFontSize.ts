import { useCallback, useEffect, useRef } from 'react'

const BASE = 100
const STEP = 12.5
const MIN = 75
const MAX = 200
const KEY = 'gost-a11y-font-pct'

export function useFontSize() {
  const pctRef = useRef(BASE)

  useEffect(() => {
    const stored = parseFloat(localStorage.getItem(KEY) || '') || BASE
    pctRef.current = stored
    if (stored !== BASE) {
      document.documentElement.style.fontSize = stored + '%'
    }
    return () => {
      document.documentElement.style.fontSize = ''
    }
  }, [])

  const increase = useCallback(() => {
    pctRef.current = Math.min(MAX, pctRef.current + STEP)
    document.documentElement.style.fontSize = pctRef.current + '%'
    localStorage.setItem(KEY, String(pctRef.current))
  }, [])

  const decrease = useCallback(() => {
    pctRef.current = Math.max(MIN, pctRef.current - STEP)
    document.documentElement.style.fontSize = pctRef.current + '%'
    localStorage.setItem(KEY, String(pctRef.current))
  }, [])

  const reset = useCallback(() => {
    pctRef.current = BASE
    document.documentElement.style.fontSize = ''
    localStorage.removeItem(KEY)
  }, [])

  return { increase, decrease, reset }
}
