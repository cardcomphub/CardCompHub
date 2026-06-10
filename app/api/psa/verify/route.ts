import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
const PSA_API_BASE = "https://api.psacard.com/publicapi"

async function getSupabaseClient() {
  const { createClient } = await import('@supabase/supabase-js')
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const secretKey = process.env.SUPABASE_SERVICE_ROLE_KEY || 
                    process.env.SUPABASE_ANON_KEY || 
                    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!url || !secretKey) {
    console.error("❌ LOCAL ERROR: Supabase environment variables are missing in .env.local")
    throw new Error("Missing Supabase configuration tokens.")
  }
  return createClient(url, secretKey)
}

const parsePsaNumeric = (val: any): number => {
  if (val === undefined || val === null) return 0
  if (typeof val === 'number') return val
  const cleaned = String(val).replace(/[^0-9.]/g, '')
  const parsed = parseFloat(cleaned)
  return isNaN(parsed) ? 0 : parsed
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { certNumber } = body

    if (!certNumber) {
      return NextResponse.json({ error: "Missing required certNumber parameter." }, { status: 400 })
    }

    const cleanCert = certNumber.trim()
    const token = process.env.PSA_API_TOKEN

    if (!token) {
      return NextResponse.json({ error: "Server API token unassigned locally." }, { status: 500 })
    }

    // 1. Core Profile Metadata Fetch
    const metaResponse = await fetch(`${PSA_API_BASE}/cert/GetByCertNumber/${cleanCert}`, {
      method: "GET",
      headers: { "Authorization": `bearer ${token}`, "Accept": "application/json" }
    })

    if (!metaResponse.ok) {
      return NextResponse.json({ error: "PSA verification lookup failed." }, { status: metaResponse.status })
    }

    const metaPayload = await metaResponse.json()
    if (metaPayload?.IsValidRequest === false || !metaPayload?.PSACert) {
      return NextResponse.json({ error: "Certification serial code not found." }, { status: 404 })
    }

    const certDetails = metaPayload.PSACert
    const parsedPlayer = certDetails.Subject?.trim() || "Unknown Player"
    const parsedYear = certDetails.Year ? parseInt(certDetails.Year) : null
    const parsedBrand = certDetails.Brand?.trim() || "Unknown Set"
    const parsedGrade = certDetails.CardGrade?.trim() || "RAW"
    const parsedCardNumber = certDetails.CardNumber?.trim() || null
    const parsedCategory = certDetails.Category?.trim() || null
    const parsedLabelType = certDetails.LabelType?.trim() || certDetails.LabelText?.trim() || null

    const parsedReverseBarcode = certDetails.ReverseBarCode === true || 
                                 certDetails.ReverseBarCode === 'true' || 
                                 certDetails.ReverseBarcode === true

    const parsedPopCount = Math.floor(parsePsaNumeric(certDetails.TotalPopulation ?? certDetails.Population ?? 0))
    const parsedPopHigher = Math.floor(parsePsaNumeric(certDetails.PopulationHigher ?? certDetails.PopHigher ?? 0))

    // 2. High-Res Slab Scans Image Fetch (Running independently now)
    let certImageFront: string | null = null
    let certImageBack: string | null = null

    const imageResponse = await fetch(`${PSA_API_BASE}/cert/GetImagesByCertNumber/${cleanCert}`, {
      method: "GET",
      headers: { "Authorization": `bearer ${token}`, "Accept": "application/json" }
    })

    if (imageResponse.ok) {
      const imagesList = await imageResponse.json()
      if (Array.isArray(imagesList) && imagesList.length > 0) {
        const frontMatch = imagesList.find(img => img?.IsFrontImage === true || img?.IsFrontImage === 'true')
        const backMatch = imagesList.find(img => img?.IsFrontImage === false || img?.IsFrontImage === 'false')

        certImageFront = frontMatch?.ImageURL || null
        certImageBack = backMatch?.ImageURL || null
      }
    }

    // 3. Sync Cache indices to Supabase (Logging the scan)
    const supabase = await getSupabaseClient()
    await supabase
      .from('psa_cert_verifications')
      .upsert({
        cert_number: cleanCert,
        player_name: parsedPlayer,
        card_year: parsedYear,
        card_brand: parsedBrand,
        card_grade: parsedGrade,
        pop_count: parsedPopCount,
        pop_higher: parsedPopHigher,
        label_type: parsedLabelType,
        reverse_barcode_exists: parsedReverseBarcode,
        card_number: parsedCardNumber,
        category: parsedCategory,
        cert_image_front: certImageFront,
        cert_image_back: certImageBack,
        slab_image_front: certImageFront,
        slab_image_back: certImageBack,
        updated_at: new Date().toISOString()
      }, { onConflict: 'cert_number' })

    return NextResponse.json({
      success: true,
      source: 'live_psa_api',
      data: {
        cert_number: cleanCert,
        player_name: parsedPlayer,
        card_year: parsedYear,
        card_brand: parsedBrand,
        card_grade: parsedGrade,
        card_number: parsedCardNumber,
        category: parsedCategory,
        label_type: parsedLabelType,
        reverse_barcode_exists: parsedReverseBarcode,
        pop_count: parsedPopCount,
        pop_higher: parsedPopHigher,
        cert_image_front: certImageFront,
        cert_image_back: certImageBack,
        slab_image_front: certImageFront,
        slab_image_back: certImageBack
      }
    }, { status: 200 })

  } catch (globalError: any) {
    return NextResponse.json({ error: globalError.message }, { status: 500 })
  }
}