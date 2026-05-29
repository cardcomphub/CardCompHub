'use client'; // 👈 This tells Next.js this specific element runs in the browser

import { sendGAEvent } from '@next/third-parties/google';

interface EbayButtonProps {
  url: string;
  playerName: string;
  cardSet: string;
}

export default function EbayButton({ url, playerName, cardSet }: EbayButtonProps) {
  return (
    <a 
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => sendGAEvent({ 
        event: 'affiliate_click', 
        value: { 
          destination: 'ebay', 
          player: playerName, 
          card_set: cardSet 
        } 
      })}
      className="inline-flex text-center justify-center items-center bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2.5 px-5 rounded-xl transition-colors shadow-lg shadow-blue-950/40 font-mono tracking-wider uppercase"
    >
      Shop Live Auctions on eBay &rarr;
    </a>
  );
}