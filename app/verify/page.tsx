import { Metadata } from 'next'
import VerifyClient from './VerifyClient'

// 🚀 GOOGLE SEO ENGINE ADVANTAGE METADATA MAPS
export const metadata: Metadata = {
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

export default function VerifyPage() {
  return <VerifyClient />
}