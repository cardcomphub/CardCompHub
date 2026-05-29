import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Navbar from "@/components/Navbar";
import { GoogleAnalytics } from "@next/third-parties/google";
import { Analytics } from "@vercel/analytics/react"; // 📊 1. IMPORT VERCEL ANALYTICS ENGINE
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CardCompHub | Sports Card Valuation & Checklist Hub",
  description: "Programmatic indexing engine tracking real-time sports card valuation benchmarks, variants, and comps data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased scroll-smooth`}
    >
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100">
        <Navbar />
        {children}
        
        {/* 📊 2. INJECT VERCEL WEB ANALYTICS TRACKER */}
        <Analytics />
      </body>
      
      {/* 📈 INJECT GOOGLE ANALYTICS 4 CORE */}
      <GoogleAnalytics gaId="G-14ZZEWTNDE" />
    </html>
  );
}