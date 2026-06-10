import Image from 'next/image'

export default function AmazonSuppliesBanner() {
  // Replace this placeholder string with your custom text link tagged from your Amazon Associates Storefront Console
  const amazonAffiliateUrl = "https://amzn.to/4wTL9e5" 

  return (
    <div className="w-full max-w-5xl mx-auto my-10 font-mono">
      <a 
        href={amazonAffiliateUrl} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="block group relative overflow-hidden rounded-2xl border border-slate-900 bg-gradient-to-r from-slate-950 via-slate-900 to-blue-950/20 p-6 transition-all hover:border-blue-500/40 shadow-xl"
      >
        {/* Dynamic ambient highlight glow */}
        <div className="absolute top-0 right-0 h-full w-1/3 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.04)_0,transparent_70%)] pointer-events-none" />

        <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
          <div className="text-left space-y-2">
            <span className="text-[9px] font-black uppercase tracking-widest text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded font-mono">
              Collector Supply Hub
            </span>
            <h3 className="text-lg font-black text-white sm:text-xl tracking-tight font-sans">
              Protect Your Pulls with Archival-Quality Gear
            </h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Don't lose market value to surface scratches or soft corners. Restock on crystal-clear penny sleeves, rigid 35pt toploaders, and acid-free storage vaults directly through Amazon.
            </p>
          </div>
          
          <div className="flex-shrink-0 w-full md:w-auto text-center bg-blue-600 text-white text-xs font-black px-6 py-3.5 rounded-xl group-hover:bg-blue-500 transition-colors shadow-lg shadow-blue-950/50 uppercase tracking-wider">
            Get Protection Supplies &rarr;
          </div>
        </div>
      </a>
      
      {/* ⚖️ AMAZON ASSOCIATES COMPLIANCE MANDATE */}
      <p className="text-[9px] text-slate-600 text-left mt-2 px-2 italic">
        *As an Amazon Associate, CardCompHub earns a commission from qualifying purchases which helps keep our platform market analytics active at zero extra cost to you.
      </p>
    </div>
  )
}