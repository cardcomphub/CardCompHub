import Link from "next/link";

export default function GiveawayBanner() {
  return (
    <div className="bg-blue-600 text-white px-4 py-3 text-center shadow-md">
      <p className="text-sm md:text-base font-medium">
        🎉 <strong>2025 Topps Signature Break!</strong> We are giving away free packs to the first 6 people who sign up. 
        <Link href="/giveaway" className="ml-3 underline font-bold hover:text-blue-200 transition-colors">
          Claim your spot &rarr;
        </Link>
      </p>
    </div>
  );
}