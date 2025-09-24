import React, { useEffect, useState, useRef } from 'react'
import './gallery.css'

function Thumb({ file, onOpen }) {
  const fallback = `/storage/${file.event_id}/${file.name}`
  const src = file.thumb_url || file.thumbnail_480 || fallback
  const srcSetParts = []
  if (file.thumbnail_480) srcSetParts.push(`${file.thumbnail_480} 480w`)
  if (file.thumbnail_720) srcSetParts.push(`${file.thumbnail_720} 720w`)
  if (file.thumbnail_960) srcSetParts.push(`${file.thumbnail_960} 960w`)
  if (file.thumbnail_1440) srcSetParts.push(`${file.thumbnail_1440} 1440w`)
  const srcSet = srcSetParts.length ? srcSetParts.join(', ') : undefined

  // LQIP: request a very small placeholder via the thumb endpoint (e.g. w=40&blur=30)
  // The server should support query params; if not, the fallback will still work.
  const lqip = file.thumbnail_480
    ? `${file.thumbnail_480.replace('w=480', 'w=40')}&blur=30`
    : null

  const [loaded, setLoaded] = useState(false)

  return (
    <div className="thumb" onClick={() => onOpen(file)} role="button" tabIndex={0}>
      <div className={`thumb-inner ${loaded ? 'is-loaded' : 'is-loading'}`}>
        {lqip ? (
          <img className="lqip" src={lqip} alt="placeholder" aria-hidden="true" />
        ) : (
          <div className="lqip lqip--solid" />
        )}
        <img
          className="main"
          src={src}
          srcSet={srcSet}
          sizes="(max-width: 600px) 480px, (max-width: 1200px) 720px, 960px"
          alt={file.name}
          loading="lazy"
          onLoad={() => setLoaded(true)}
        />
      </div>
      <div className="meta">{file.name}{file.ordinal ? ` · ${file.ordinal}` : ''}</div>
    </div>
  )
}

function Lightbox({ item, onClose, onPrev, onNext }) {
  const contentRef = useRef(null)
  const closeBtnRef = useRef(null)
  const previouslyFocused = useRef(null)

  useEffect(() => {
    if (!item) return undefined
    // store previously focused element to restore later
    previouslyFocused.current = document.activeElement
    // focus close button for accessibility
    setTimeout(() => {
      try {
        if (closeBtnRef.current && typeof closeBtnRef.current.focus === 'function') {
          closeBtnRef.current.focus()
        }
      } catch (err) {
        /* ignore */
      }
    }, 0)

    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        onPrev && onPrev()
        return
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        onNext && onNext()
        return
      }
      if (e.key === 'Tab') {
        // focus trap: keep tab within the lightbox content
        const focusable = contentRef.current?.querySelectorAll(
          'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
        ) || []
        if (focusable.length === 0) {
          e.preventDefault()
          return
        }
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          try {
            last.focus()
          } catch (err) {}
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          try {
            first.focus()
          } catch (err) {}
        }
      }
    }

    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      try {
        if (previouslyFocused.current && typeof previouslyFocused.current.focus === 'function') {
          previouslyFocused.current.focus()
        }
      } catch (err) {
        /* ignore */
      }
    }
  }, [item, onClose, onPrev, onNext])

  if (!item) return null
  const src = item.url || (item.thumb_url || `/storage/${item.event_id}/${item.name}`)
  return (
    <div className="lightbox" onClick={onClose} role="dialog" aria-modal="true">
      <button
        className="lightbox-close"
        onClick={onClose}
        aria-label="Close"
        ref={closeBtnRef}
      >
        ×
      </button>
      <div className="lightbox-content" onClick={(e) => e.stopPropagation()} ref={contentRef}>
        <div className="lightbox-controls">
          <button aria-label="Previous" onClick={(e) => { e.stopPropagation(); onPrev && onPrev() }}>◀</button>
          <button aria-label="Next" onClick={(e) => { e.stopPropagation(); onNext && onNext() }}>▶</button>
        </div>
        {item.type === 'video' ? (
          <video controls src={item.url} className="lightbox-media" />
        ) : (
          <img src={src} alt={item.name} className="lightbox-media" />
        )}
        <div className="lightbox-meta">{item.name}</div>
      </div>
    </div>
  )
}

export default function GalleryApp() {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [lightboxItem, setLightboxItem] = useState(null)

  useEffect(() => {
    // For demo, use event_id=1 — host app should mount with real event id
    const eventId = window.__GALLERY_EVENT_ID__ || 1
    fetch(`/events/${eventId}/gallery/order`)
      .then((r) => r.json())
      .then((j) => {
        if (j && j.ok) {
          // normalize fields expected by component
          const mapped = (j.files || []).map((f) => ({
            id: f.id,
            name: f.name,
            type: f.type,
            event_id: eventId,
            url: f.url,
            ordinal: f.ordinal || null,
            // Prefer API-provided thumb_url or thumbnail_480; fallback to storage path
            thumb_url:
              f.thumb_url || f.thumbnail_480 || `/storage/${eventId}/thumbnails/480/${f.name}`,
            thumbnail_480: f.thumbnail_480 || null,
            thumbnail_720: f.thumbnail_720 || null,
            thumbnail_960: f.thumbnail_960 || null,
            thumbnail_1440: f.thumbnail_1440 || null,
          }))
          setFiles(mapped)
        }
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="gallery-app">
      <h1>Gallery</h1>
      {loading ? (
        <div>Loading…</div>
      ) : files.length === 0 ? (
        <div>No files</div>
      ) : (
        <>
          <div className="grid">
            {files.map((f) => (
              <Thumb key={f.id} file={f} onOpen={(it) => setLightboxItem(it)} />
            ))}
          </div>
          <Lightbox item={lightboxItem} onClose={() => setLightboxItem(null)} />
        </>
      )}
    </div>
  )
}
