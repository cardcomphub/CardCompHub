'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function CardFeed({ initialCards }: { initialCards: any[] }) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredCards = initialCards.filter((card) => {
    const searchString = `${card.player_name} ${card.card_sets?.brand} ${card.card_sets?.series} ${card.card_number}`.toLowerCase()
    return searchString.includes(searchQuery.toLowerCase())
  })

  return (
    <div>
      <div className="mb-10 max-w-xl">
        <input
          type="text"
          placeholder="Type player name, card #, or brand..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 rounded-xl px-5 py-3.5 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 transition-all"
        />
        <p className="text-xs text-slate-500 mt-2 font-mono">
          Displaying {filteredCards.length} verified checklist profiles
        </p>
      </div>

      {/* Lightweight Grid Design */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {filteredCards.map((card: any) => (
          <Link 
            href={`/cards/${card.id}`} 
            key={card.id}
            className="bg-slate-900 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between transition-all duration-200 hover:border-emerald-500/40 hover:-translate-y-1 group"
          >
            <div className="aspect-[3/4] w-full bg-slate-950/40 rounded-xl p-2 border border-slate-800/40 flex items-center justify-center overflow-hidden mb-4 relative">
              <img 
                src={card.image_url} 
                alt={card.player_name} 
                className="max-h-full max-w-full object-contain rounded shadow-md group-hover:scale-[1.03] transition-transform duration-200"
                loading="lazy"
              />
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-500 font-mono block uppercase">
                #{card.card_number} • {card.card_sets?.series}
              </span>
              <h2 className="text-base font-black tracking-tight text-white mt-0.5 truncate group-hover:text-emerald-400 transition-colors">
                {card.player_name}
              </h2>
              {card.is_rookie && (
                <span className="mt-2 inline-block bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-bold px-2 py-0.5 rounded">
                  Rookie Card
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}