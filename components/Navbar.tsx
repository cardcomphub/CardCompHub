"use client"

import { useState } from 'react'
import Link from 'next/link'

export default function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen)
  }

  // 👇 Dynamic query parameter paths instead of flat page anchors
  const navLinks = [
    { name: 'All Dashboard', href: '/' },
    { name: 'Baseball', href: '/?sport=Baseball' },
    { name: 'Basketball', href: '/?sport=Basketball' },
    { name: 'Football', href: '/?sport=Football' },
    { name: 'Verify Slab', href: '/verify' }, // 🔥 NEW LINK ADDED HERE
  ]

  return (
    <nav className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-900 w-full">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        
        {/* Brand Logo */}
        <Link href="/" className="text-xl font-black tracking-tight text-white font-sans">
          Card<span className="text-emerald-400">Comp</span>Hub
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-6 font-mono text-xs font-semibold">
          {navLinks.map((link) => (
            <Link 
              key={link.name} 
              href={link.href} 
              className="text-slate-400 hover:text-emerald-400 transition-colors"
            >
              {link.name}
            </Link>
          ))}
        </div>

        {/* Reset Filter Button */}
        <div className="hidden md:block">
          <Link 
            href="/"
            className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xxs font-bold uppercase tracking-wider px-4 py-2 rounded-xl hover:bg-emerald-500 hover:text-slate-950 transition-all font-mono"
          >
            Clear All Filters
          </Link>
        </div>

        {/* Hamburger Menu Toggle */}
        <div className="md:hidden flex items-center">
          <button
            onClick={toggleMobileMenu}
            type="button"
            className="text-slate-400 hover:text-white focus:outline-none p-2 rounded-lg hover:bg-slate-900"
            aria-label="Toggle Navigation Menu"
          >
            {isMobileMenuOpen ? (
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Hamburger Menu Dropdown Drawer */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-slate-950 border-b border-slate-900 font-mono text-xs px-6 py-4 space-y-3">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              href={link.href}
              onClick={() => setIsMobileMenuOpen(false)}
              className="block text-slate-400 hover:text-emerald-400 py-1 transition-colors font-semibold"
            >
              {link.name}
            </Link>
          ))}
          <div className="pt-2 border-t border-slate-900">
            <Link
              href="/"
              onClick={() => setIsMobileMenuOpen(false)}
              className="block text-center bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold uppercase tracking-wider py-2.5 rounded-xl text-xxs"
            >
              Clear All Filters
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}