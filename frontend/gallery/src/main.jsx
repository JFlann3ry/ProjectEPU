import React from 'react'
import { createRoot } from 'react-dom/client'
import GalleryApp from './GalleryApp'
import './styles.css'

// Dev convenience: if the host hasn't provided an event id, read it from the
// ?event= query param (or ?event_id= / ?eventId=) and expose it as
// window.__GALLERY_EVENT_ID__ so the app can pick it up.
try {
  if (!window.__GALLERY_EVENT_ID__) {
    const qs = new URL(window.location.href).searchParams
    const ev = qs.get('event') || qs.get('event_id') || qs.get('eventId')
    if (ev) {
      // coerce numeric when appropriate
      const n = Number(ev)
      window.__GALLERY_EVENT_ID__ = Number.isFinite(n) ? n : ev
    }
  }
} catch (err) {
  // ignore when running in non-browser test envs
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GalleryApp />
  </React.StrictMode>
)
