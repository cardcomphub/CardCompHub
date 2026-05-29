'use client'

import { useState, useEffect, useRef } from 'react'

interface ZoomableThumbnailProps {
  src: string;
  alt: string;
}

export default function ZoomableThumbnail({ src, alt }: ZoomableThumbnailProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isMagnified, setIsMagnified] = useState(false)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  // 1. THE HIGH-RES URL HACK
  // Intercepts low-resolution search thumbnails and replaces the sizing token
  // with eBay's master source code flag (s-l1600), delivering full crystal-clear resolution.
  const getHighResUrl = (url: string) => {
    if (!url) return ''
    return url.replace(/s-l\d+\.(jpg|jpeg|png|webp)/i, 's-l1600.jpg')
  }

  const highResSrc = getHighResUrl(src)

  useEffect(() => {
    if (!isOpen) {
      setIsMagnified(false)
      return
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  // 2. MOUSE-TRACKING LOUPE PANNING MECHANISM
  // Tracks your coordinates across the image box bounds to shift the viewport
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isMagnified || !containerRef.current) return
    
    const { left, top, width, height } = containerRef.current.getBoundingClientRect()
    
    // Calculate accurate position percentage vectors
    const x = ((e.clientX - left) / width) * 100
    const y = ((e.clientY - top) / height) * 100
    
    setMousePos({ x, y })
  }

  return (
    <>
      {/* Base Row Small Preview Window Component */}
      <div 
        onClick={() => setIsOpen(true)}
        className="relative h-24 w-16 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-center p-1 overflow-hidden shadow-lg hover:border-emerald-500/50 transition-all cursor-zoom-in group"
      >
        <img 
          src={src} 
          alt={alt} 
          className="max-h-full max-w-full object-contain rounded-sm transition-transform duration-200 group-hover:scale-[1.04]"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-emerald-500/0 group-hover:bg-emerald-500/5 transition-colors flex items-center justify-center">
          <span className="text-[10px] text-emerald-400 font-bold opacity-0 group-hover:opacity-100 transition-opacity uppercase font-mono tracking-wider bg-slate-950/80 px-1.5 py-0.5 rounded border border-slate-800 shadow-md">
            Inspect
          </span>
        </div>
      </div>

      {/* Full Screen Cinematic Inspection Studio */}
      {isOpen && (
        <div 
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 bg-slate-950/90 backdrop-blur-xl z-50 flex flex-col items-center justify-center p-4 md:p-8 cursor-zoom-out animate-in fade-in duration-200"
        >
          <div 
            onClick={(e) => e.stopPropagation()} 
            className="relative max-w-3xl w-full flex flex-col items-center animate-in zoom-in-95 duration-200"
          >
            {/* Interactive Image Frame */}
            <div 
              ref={containerRef}
              onMouseMove={handleMouseMove}
              onClick={() => setIsMagnified(!isMagnified)}
              className="relative w-full aspect-[3/4] max-h-[75vh] bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex items-center justify-center p-2 group"
              style={{ cursor: isMagnified ? 'zoom-out' : 'zoom-in' }}
            >
              <img 
                src={highResSrc} 
                alt={alt} 
                className="max-h-[72vh] max-w-full object-contain rounded-xl select-none pointer-events-none transition-transform duration-100 ease-out"
                style={{
                  transform: isMagnified ? 'scale(2.5)' : 'scale(1)',
                  transformOrigin: isMagnified ? `${mousePos.x}% ${mousePos.y}%` : 'center center'
                }}
              />
              
              {/* Quick UI Hint Helper HUD Banner */}
              {!isMagnified && (
                <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-slate-950/80 border border-slate-800/80 px-3 py-1.5 rounded-full text-[10px] font-mono uppercase font-bold tracking-wider text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-md">
                  Click Photo to Zoom & Pan
                </div>
              )}
            </div>
            
            {/* Bottom Descriptive Title Capsule */}
            <div className="mt-4 flex items-center gap-3 bg-slate-900/90 border border-slate-800 px-5 py-2 rounded-full shadow-lg pointer-events-auto">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <p className="text-slate-200 font-mono text-xs font-bold tracking-tight">
                {alt}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}