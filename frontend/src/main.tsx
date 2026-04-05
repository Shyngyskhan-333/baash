import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const envFastUi = ['1', 'true', 'yes', 'on'].includes(
  String(import.meta.env.VITE_FAST_UI ?? '').toLowerCase()
)

const envQuickTest = ['1', 'true', 'yes', 'on'].includes(
  String(
    import.meta.env.VITE_QUICK_TEST_MODE ?? import.meta.env.VITE_DEMO_MODE ?? '',
  ).toLowerCase(),
)

const lowPower = (() => {
  try {
    const nav = navigator as unknown as { hardwareConcurrency?: number; deviceMemory?: number }
    const cpu = typeof nav.hardwareConcurrency === 'number' ? nav.hardwareConcurrency : 8
    const mem = typeof nav.deviceMemory === 'number' ? nav.deviceMemory : 8
    return cpu <= 4 || mem <= 4
  } catch {
    return false
  }
})()

const storedFastUi = (() => {
  try {
    return localStorage.getItem('lexlens-fast-ui') === '1'
  } catch {
    return false
  }
})()

const fastUi = envFastUi || envQuickTest || storedFastUi || lowPower

if (fastUi) {
  document.body.classList.add('fast-ui')
}

const root = createRoot(document.getElementById('root')!)
root.render(
  <App />
)