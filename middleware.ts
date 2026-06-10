import { clerkMiddleware } from "@clerk/nextjs/server";

// Calling clerkMiddleware() with no arguments makes EVERY route public by default.
// It will still track session state so your Navbar knows when to show the Avatar vs the Sign In button.
export default clerkMiddleware();

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};