'use client';

import { useState } from 'react';

export default function SignatureDisplay({ signatureUrl, playerName }: { signatureUrl: string, playerName: string }) {
  const [hasError, setHasError] = useState(false);

  return (
    <div className="bg-slate-200 rounded-lg p-2 w-full sm:w-72 h-24 flex items-center justify-center border-2 border-slate-300 shadow-inner relative overflow-hidden group">
      <span className="absolute top-1.5 left-2 text-[9px] font-black text-slate-400 uppercase tracking-widest z-10">
        Verified Auto
      </span>
      
      {hasError ? (
        <span className="text-xs text-slate-500 font-mono italic flex items-center h-full justify-center">
          No Signature on File
        </span>
      ) : (
        <img
          src={signatureUrl}
          alt={`${playerName} Autograph`}
          className="max-h-full max-w-full object-contain mix-blend-multiply opacity-80 group-hover:opacity-100 transition-opacity"
          onError={() => setHasError(true)}
        />
      )}
    </div>
  );
}