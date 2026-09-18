import { createRoot } from 'react-dom/client'

// Self-hosted so a judge's cold load never waits on a font CDN, and the type
// never flashes mid-recording. Latin subsets only — the unscoped entrypoints
// also ship Cyrillic, Greek and Vietnamese, which this UI never renders.
//
// 700 is here for headings only. The console never needed a bold weight; the
// paper theme leans on one, because on cream a heading cannot separate itself
// from body text by brightness the way it did on graphite.
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/inter/latin-700.css'
import '@fontsource/jetbrains-mono/latin-400.css'
import '@fontsource/jetbrains-mono/latin-500.css'
import '@fontsource/jetbrains-mono/latin-600.css'

import './styles.css'
import App from './App'

// No StrictMode: its dev-only double render would open two WebSockets and
// write two CONN# rows, which makes the member count lie while testing.
createRoot(document.getElementById('root')).render(<App />)
