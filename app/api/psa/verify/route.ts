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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { certNumber } = body

    console.log(`\n=== 🔎 NEW LOCAL LOOKUP REQUEST: Cert #${certNumber} ===`)

    if (!certNumber) {
      return NextResponse.json({ error: "Missing required certNumber parameter." }, { status: 400 })
    }

    const cleanCert = certNumber.trim()
    const token = process.env.PSA_API_TOKEN

    if (!token) {
      console.error("❌ LOCAL ERROR: PSA_API_TOKEN is completely undefined inside your .env.local file!")
      return NextResponse.json({ error: "Server API token unassigned locally." }, { status: 500 })
    }

    // 1. Core Profile Metadata Fetch
    console.log(`📡 Fetching core profile metadata from PSA for #${cleanCert}...`)
    const metaResponse = await fetch(`${PSA_API_BASE}/cert/GetByCertNumber/${cleanCert}`, {
      method: "GET",
      headers: { "Authorization": `bearer ${token}`, "Accept": "application/json" }
    })

    if (!metaResponse.ok) {
      const errText = await metaResponse.text()
      console.error(`❌ PSA Meta API Rejected Request: ${errText}`)
      return NextResponse.json({ error: "PSA verification lookup failed." }, { status: metaResponse.status })
    }

    const metaPayload = await metaResponse.json()
    if (metaPayload?.IsValidRequest === false || !metaPayload?.PSACert) {
      console.warn(`⚠️ PSA Registry stated this certificate number is invalid or not found.`)
      return NextResponse.json({ error: "Certification serial code not found." }, { status: 404 })
    }

    const certDetails = metaPayload.PSACert
    const parsedPlayer = certDetails.Subject?.trim() || "Unknown Player"
    const parsedYear = certDetails.Year ? parseInt(certDetails.Year) : null
    const parsedBrand = certDetails.Brand?.trim() || "Unknown Set"
    const parsedGrade = certDetails.CardGrade?.trim() || "RAW"

    console.log(`✅ Found Card: ${parsedYear} ${parsedBrand} ${parsedPlayer} (Grade: ${parsedGrade})`)

    // 2. High-Res Slab Scans Image Fetch
    console.log(`📸 Querying secure image array for slab graphics...`)
    let certImageFront: string | null = null
    let certImageBack: string | null = null

    const imageResponse = await fetch(`${PSA_API_BASE}/cert/GetImagesByCertNumber/${cleanCert}`, {
      method: "GET",
      headers: { "Authorization": `bearer ${token}`, "Accept": "application/json" }
    })

    if (imageResponse.ok) {
      const imagesList = await imageResponse.json()
      
      console.log(`📦 Number of raw image objects returned by PSA: ${imagesList.length}`)

      if (Array.isArray(imagesList) && imagesList.length > 0) {
        // 🛠️ FIXED: Target the exact structural keys returned by the PSA API payload
        const frontMatch = imagesList.find(img => img?.IsFrontImage === true || img?.IsFrontImage === 'true')
        const backMatch = imagesList.find(img => img?.IsFrontImage === false || img?.IsFrontImage === 'false')

        certImageFront = frontMatch?.ImageURL || null
        certImageBack = backMatch?.ImageURL || null
        
        console.log(`🖼️ Extracted Front URL: ${certImageFront}`)
        console.log(`🖼️ Extracted Back URL: ${certImageBack}`)
      }
    } else {
      console.error(`❌ Failed to fetch image array from PSA. Status code: ${imageResponse.status}`)
    }

    // 3. Sync Cache indices to Supabase
    console.log(`💾 Syncing cache entry records to Supabase table index...`)
    const supabase = await getSupabaseClient()
    const { error: dbError } = await supabase
      .from('psa_cert_verifications')
      .upsert({
        cert_number: cleanCert,
        player_name: parsedPlayer,
        card_year: parsedYear,
        card_brand: parsedBrand,
        card_grade: parsedGrade,
        cert_image_front: certImageFront,
        cert_image_back: certImageBack,
        updated_at: new Date().toISOString()
      }, { onConflict: 'cert_number' })

    if (dbError) {
      console.error("❌ SUPABASE WRITE ERROR:", dbError)
    } else {
      console.log("🚀 Supabase cache write successful!")
    }

    return NextResponse.json({
      success: true,
      data: {
        cert_number: cleanCert,
        player_name: parsedPlayer,
        card_year: parsedYear,
        card_brand: parsedBrand,
        card_grade: parsedGrade,
        cert_image_front: certImageFront,
        cert_image_back: certImageBack
      }
    }, { status: 200 })

  } catch (globalError: any) {
    console.error("🚨 GLOBAL HANDLER CRASH:", globalError)
    return NextResponse.json({ error: globalError.message }, { status: 500 })
  }
}