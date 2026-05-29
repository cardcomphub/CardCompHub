'use client'

import { useState, useEffect } from 'react'

export default function KaboomIntro({ onComplete }: { onComplete: () => void }) {
  const [isShattering, setIsShattering] = useState(false)
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    // Phase 1: Hold the graphic, shake violently, then trigger the shatter blast
    const shatterTimer = setTimeout(() => {
      setIsShattering(true)
    }, 1300)

    // Phase 2: Fade out the entire overlay frame and mount the main site directory
    const hideTimer = setTimeout(() => {
      setIsVisible(false)
      onComplete()
    }, 2300)

    return () => {
      clearTimeout(shatterTimer)
      clearTimeout(hideTimer)
    }
  }, [onComplete])

  if (!isVisible) return null

  // Generate unique custom trajectories for 18 holographic foil glass shards
  const shards = Array.from({ length: 18 }).map((_, i) => {
    const angle = (i / 18) * 360 + Math.random() * 20
    const distance = 300 + Math.random() * 300
    const tx = Math.cos((angle * Math.PI) / 180) * distance
    const ty = Math.sin((angle * Math.PI) / 180) * distance
    const rotation = Math.random() * 720 - 360
    const scale = 0.5 + Math.random() * 1.5

    return {
      id: i,
      style: {
        '--tx': `${tx}px`,
        '--ty': `${ty}px`,
        '--rot': `${rotation}deg`,
        '--scale': scale,
        top: `${35 + Math.random() * 30}%`,
        left: `${35 + Math.random() * 30}%`,
        clipPath: getRandomClipPath(),
      } as React.CSSProperties
    }
  })

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-slate-950 overflow-hidden transition-opacity duration-500 ${isShattering ? 'bg-slate-950/20 pointer-events-none' : 'opacity-100'}`}>
      
      {/* INJECTED BULLETPROOF EXPLOSION CSS KEYFRAMES */}
      <style>{`
        @keyframes comicPop {
          0% { transform: scale(0) rotate(-15deg); opacity: 0; }
          70% { transform: scale(1.15) rotate(5deg); opacity: 1; }
          100% { transform: scale(1) rotate(-2deg); }
        }
        @keyframes fastShake {
          0%, 100% { transform: translate(0, 0) rotate(-2deg); }
          20% { transform: translate(-4px, 4px) rotate(1deg); }
          40% { transform: translate(4px, -2px) rotate(-4deg); }
          60% { transform: translate(-2px, -4px) rotate(0deg); }
          80% { transform: translate(4px, 4px) rotate(-3deg); }
        }
        @keyframes blastAway {
          0% { transform: translate(0, 0) rotate(0deg) scale(1); opacity: 1; filter: blur(0px); }
          100% { transform: translate(var(--tx), var(--ty)) rotate(var(--rot)) scale(var(--scale)); opacity: 0; filter: blur(4px); }
        }
        @keyframes textImplode {
          0% { transform: scale(1) rotate(-2deg); opacity: 1; filter: brightness(1); }
          30% { transform: scale(1.1) rotate(2deg); filter: brightness(1.5); }
          100% { transform: scale(0.2); opacity: 0; filter: blur(12px); }
        }
        .animate-pop { animation: comicPop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
        .animate-shake { animation: fastShake 0.15s infinite linear; }
        .animate-blast { animation: blastAway 0.9s cubic-bezier(0.1, 0.8, 0.25, 1) forwards; }
        .animate-implode { animation: textImplode 0.7s cubic-bezier(0.6, -0.28, 0.735, 0.045) forwards; }
        .ben-day-dots { background-image: radial-gradient(rgba(245, 158, 11, 0.4) 15%, transparent 16%); background-size: 8px 8px; }
      `}</style>

      {/* MASTER KABOOM FRAME COMPOSITION */}
      <div className={`relative w-full max-w-4xl aspect-video flex items-center justify-center transition-transform ${!isShattering ? 'animate-pop' : ''}`}>
        
        {/* BACKGROUND ACTION LAYER: Comic Starburst Burst */}
        <div className={`absolute inset-0 flex items-center justify-center transition-all duration-300 ${!isShattering ? 'animate-shake' : 'scale-150 opacity-0 blur-md'}`}>
          <svg viewBox="0 0 500 500" className="w-[140%] h-[140%] text-amber-500 fill-current opacity-90 drop-shadow-[0_0_40px_rgba(245,158,11,0.5)]">
            <path d="M250,50 L280,180 L400,100 L320,220 L480,250 L320,280 L400,400 L280,320 L250,450 L220,320 L100,400 L180,220 L20,250 L180,220 L100,100 L220,180 Z" />
          </svg>
          {/* Internal Dot Matrix Filter Layer */}
          <div className="absolute inset-0 ben-day-dots rounded-full mix-blend-overlay scale-75" />
        </div>

        {/* MIDGROUND DATA LAYER: Stylized Glowing Analytics Bar Lines */}
        <div className={`absolute inset-0 flex items-center justify-center pointer-events-none transition-all duration-500 ${isShattering ? 'scale-150 opacity-0' : ''}`}>
          <div className="flex items-end gap-3 h-48 opacity-30 mix-blend-screen -rotate-12 transform scale-110">
            <div className="w-4 bg-cyan-400 h-24 rounded-full animate-pulse" />
            <div className="w-4 bg-emerald-400 h-40 rounded-full animate-pulse delay-75" />
            <div className="w-4 bg-pink-500 h-16 rounded-full animate-pulse delay-150" />
            <div className="w-4 bg-yellow-400 h-32 rounded-full animate-pulse delay-100" />
          </div>
        </div>

        {/* THE HOLOGRAPHIC FOIL SHARD ENGINE */}
        {shards.map((shard) => (
          <div
            key={shard.id}
            style={shard.style}
            className={`absolute w-32 h-32 bg-gradient-to-tr from-cyan-400/80 via-pink-400/70 to-yellow-300/80 shadow-[0_0_15px_rgba(255,255,255,0.4)] border border-white/40 opacity-0 mix-blend-screen ${isShattering ? 'animate-blast' : 'opacity-100'}`}
          />
        ))}

        {/* FOREGROUND CENTRAL ARTWORK: Stylized Text Graphics */}
        <div className={`relative flex flex-col items-center select-none ${isShattering ? 'animate-implode' : 'animate-shake'}`}>
          
          {/* Mini Header Accent Sticker */}
          <div className="bg-cyan-400 text-slate-950 font-black text-xs md:text-sm px-4 py-1 rounded-md uppercase tracking-widest transform -rotate-6 translate-y-3 shadow-md border-2 border-slate-950 z-20 font-mono">
            Data Compression!
          </div>

          {/* Core "KABOOM!" Comic Logo Font Stack */}
          <div className="relative transform font-sans tracking-tighter">
            {/* Super Deep Black Comic-Block Shadow Base */}
            <h1 className="text-7xl md:text-9xl font-black text-slate-950 select-none absolute top-4 left-4 translate-x-2 translate-y-2 text-center tracking-tighter uppercase italic">
              KABOOM!
            </h1>
            <h1 className="text-7xl md:text-9xl font-black text-slate-950 select-none absolute top-2 left-2 translate-x-1 translate-y-1 text-center tracking-tighter uppercase italic">
              KABOOM!
            </h1>
            {/* Top Bright Orange-Red Vibrant Face Layer */}
            <h1 className="text-7xl md:text-9xl font-black bg-gradient-to-b from-yellow-400 via-orange-500 to-red-600 bg-clip-text text-transparent text-center tracking-tighter uppercase italic relative z-10 drop-shadow-[0_4px_0_#0f172a]">
              KABOOM!
            </h1>
          </div>

          {/* Sub-Footer Arrival Banner Capsule */}
          <div className="bg-yellow-400 text-slate-950 font-black text-xs md:text-base px-6 py-1.5 rounded-xl border-4 border-slate-950 uppercase tracking-wider transform rotate-3 -translate-y-4 shadow-xl z-20">
            MINT METRICS ARRIVAL!
          </div>

        </div>

      </div>
    </div>
  )
}

// Helper utility to construct radical jagged lightning & diamond fracture shapes for the glass foil shards
function getRandomClipPath() {
  const shapes = [
    "polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)",
    "polygon(0 0, 100% 20%, 70% 90%, 20% 100%)",
    "polygon(30% 0%, 100% 0%, 85% 85%, 0% 70%)",
    "polygon(50% 0%, 100% 100%, 0% 60%)",
    "polygon(0% 15%, 85% 0%, 100% 85%, 15% 100%)"
  ]
  return shapes[Math.floor(Math.random() * shapes.length)]
}