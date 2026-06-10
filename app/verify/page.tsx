import { Metadata } from 'next'
import VerifyClient from './VerifyClient'

export const dynamic = 'force-dynamic'

interface PSACertData {
  cert_number: string
  player_name: string
  card_year: number | null
  card_brand: string
  card_grade: string
  card_number: string | null
  category: string | null
  label_type: string | null
  reverse_barcode_exists: boolean
  psa_estimate: number
  pop_count: number
  pop_higher: number
  cert_image_front: string | null
  cert_image_back: string | null
  slab_image_front: string | null
  slab_image_back: string | null
}

// 🚀 ENGINE ADVANTAGE 1: DYNAMIC METADATA MAPS - Overrides static SEO layout automatically when a cert parameter hits the URL string
export async function generateMetadata({ searchParams }: { searchParams: Promise<{ cert?: string }> }): Promise<Metadata> {
  const { cert } = await searchParams
  
  const baseMetadata: Metadata = {
    title: 'PSA Cert Verification & Slab Authenticator | CardCompHub',
    description: 'Instantly verify the authenticity of any PSA-graded sports trading card or TCG item. Check official certification details, population metrics, and registry history.',
    keywords: [
      'PSA verification', 
      'PSA cert lookup', 
      'sports card authenticator', 
      'verify sports card grade', 
      'card registry lookup',
      'CardCompHub'
    ],
    openGraph: {
      title: 'PSA Cert Verification & Slab Authenticator | CardCompHub',
      description: 'Instantly verify the authenticity of any PSA-graded sports trading card or TCG item.',
      url: 'https://www.cardcomphub.com/verify',
      siteName: 'CardCompHub',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: 'PSA Cert Verification & Slab Authenticator | CardCompHub',
      description: 'Verify your PSA slabs instantly via the official database registry.',
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
      },
    },
  }

  if (!cert) return baseMetadata

  try {
    // Queries your internal POST route structure using an absolute host pointer
    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
    const res = await fetch(`${baseUrl}/api/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ certNumber: cert.trim() }),
      cache: 'no-store'
    })

    if (res.ok) {
      const payload = await res.json()
      const data: PSACertData = payload.data

      if (data) {
        const itemTitle = `${data.card_year || ''} ${data.card_brand} ${data.player_name} #${data.card_number || ''}`.trim()
        return {
          ...baseMetadata,
          title: `PSA Cert #${data.cert_number} Verified: ${itemTitle} (${data.card_grade}) | CardCompHub`,
          description: `Official registry metadata for PSA graded card #${data.cert_number}. Population Count: ${data.pop_count || 'N/A'} | Population Higher: ${data.pop_higher || 0} | Estimated Value: $${data.psa_estimate || '0.00'}. Verify slab details before buying.`,
          openGraph: {
            ...baseMetadata.openGraph,
            title: `PSA Cert #${data.cert_number} Verified | CardCompHub`,
            description: `Official registry logs and grading pop report parameters for ${itemTitle}.`,
          }
        }
      }
    }
  } catch (e) {
    console.error("🚨 Metadata engine fetch mismatch handled safely:", e)
  }

  return baseMetadata
}

export default async function VerifyPage({ searchParams }: { searchParams: Promise<{ cert?: string }> }) {
  const { cert } = await searchParams
  let serverFetchedData: PSACertData | null = null

  if (cert) {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
      const res = await fetch(`${baseUrl}/api/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ certNumber: cert.trim() }),
        cache: 'no-store'
      })
      if (res.ok) {
        const payload = await res.json()
        serverFetchedData = payload.data
      }
    } catch (err) {
      console.error("🚨 Server-side initialization pre-fetch exception logged:", err)
    }
  }

  // 🤖 ENGINE ADVANTAGE 2: STRUCTURED DATA INJECTION (JSON-LD) - Serves deep product context schema arrays directly to search crawlers
  const jsonLd = serverFetchedData ? {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": `${serverFetchedData.card_year || ''} ${serverFetchedData.card_brand} ${serverFetchedData.player_name} #${serverFetchedData.card_number || ''}`.trim(),
    "image": serverFetchedData.slab_image_front || serverFetchedData.cert_image_front || "",
    "description": `Professional Sports Authenticator (PSA) Graded ${serverFetchedData.card_grade} collectible asset card. Official registry confirmation hash: ${serverFetchedData.cert_number}. Total condition population: ${serverFetchedData.pop_count || 'N/A'}.`,
    "offers": {
      "@type": "Offer",
      "price": serverFetchedData.psa_estimate || "0.00",
      "priceCurrency": "USD",
      "valueAddedTaxIncluded": "true"
    }
  } : null

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      
      {/* Hydrates client component tree instantly with complete pre-cached metadata nodes */}
      <VerifyClient initialServerData={serverFetchedData} requestedCertQuery={cert || ""} />
      
      {/* 📝 ENGINE ADVANTAGE 3: ON-PAGE SEMANTIC TEXT CONTENT BLOCK - Secures massive LSI search indexing weight parameters */}
      <footer className="mt-20 border-t border-slate-900 pt-10 text-slate-500 text-xs font-mono max-w-4xl mx-auto px-4 pb-12">
        <h3 className="text-slate-400 font-bold mb-3 text-sm uppercase tracking-wider">About Our Sports Card Authentication & Verification Suite</h3>
        <p className="leading-relaxed mb-4">
          The CardCompHub slab verification toolkit connects sports card investors and collectors directly to active certification clearinghouse databases. 
          By verifying official tracking strings, our system decodes intricate condition report markers, historical grade population reports, 
          baseline market valuation appraisals, and structural security criteria (such as fugitive ink label identifiers and reverse-side barcode indexes).
        </p>
        <p className="leading-relaxed">
          Cross-referencing verified player descriptions, physical checklist identifiers, label typography patterns, and high-resolution front-and-back asset pictures 
          prior to placing secondary market auction bids serves as a vital safeguard against cracked holder housings, fraudulent modifications, and counterfeit grading inserts.
        </p>
      </footer>
    </>
  )
}