"use client";

import { useUser, SignUp } from "@clerk/nextjs";

export default function GiveawaySignupPage() {
  const { isLoaded, isSignedIn, user } = useUser();

  // Wait for Clerk to load before rendering elements to prevent layout shift
  if (!isLoaded) return null;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-950 px-4 py-12 sm:px-6 lg:px-8">
      {/* This single container holds all your content */}
      <div className="max-w-md w-full space-y-8 bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-2xl flex flex-col items-center">
        
        {/* YouTube Video Embed */}
        <div className="w-full aspect-video rounded-xl overflow-hidden border border-slate-700 shadow-2xl bg-black">
          <iframe
            className="w-full h-full"
            src="https://www.youtube.com/embed/MW-iat81HtQ"
            title="YouTube video player"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          ></iframe>
        </div>

        <div className="text-center w-full">
          <h2 className="text-3xl font-extrabold text-white tracking-tight">
            Claim Your Free Rip
          </h2>
          <p className="mt-4 text-slate-400">
            Create your CardCompHub profile below. Free 2025 Topps Signature packs go to the <strong>first 6 people</strong> who register!
          </p>
        </div>

        {/* Conditional UI */}
        {isSignedIn ? (
          <div className="mt-6 space-y-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="p-4 rounded-lg text-sm font-medium border bg-emerald-950/60 border-emerald-400 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)] text-center">
              🎉 You are officially registered!
            </div>
            
            <div className="text-center text-sm text-slate-400 bg-slate-950/50 p-6 rounded-xl border border-slate-800">
              We have your email securely on file:
              <div className="text-white font-semibold mt-2 mb-4 text-base">
                {user?.primaryEmailAddress?.emailAddress}
              </div>
              If you are one of the first 6 to claim a spot, I will be reaching out to you directly via email before the break goes live on the channel!
            </div>
          </div>
        ) : (
          <div className="mt-4 w-full flex justify-center">
            <SignUp 
              routing="hash" 
              appearance={{
                elements: {
                  card: "bg-transparent shadow-none border-none p-0 w-full",
                  headerTitle: "hidden",
                  headerSubtitle: "hidden",
                  footer: "bg-transparent",
                  formButtonPrimary: "bg-blue-600 hover:bg-blue-700 text-sm font-medium py-2.5 rounded-lg text-white transition-all shadow-lg",
                  formFieldInput: "appearance-none rounded-lg block w-full px-4 py-3 border border-slate-700 bg-slate-950 placeholder-slate-500 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm",
                  formFieldLabel: "text-slate-400 font-mono text-xs uppercase tracking-wider font-semibold mb-1",
                  identityPreviewText: "text-slate-300",
                  identityPreviewEditButton: "text-blue-400 hover:text-blue-300",
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}