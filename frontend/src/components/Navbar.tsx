import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="bg-white shadow p-4">
      <div className="max-w-6xl mx-auto flex justify-between items-center">
        <Link href="/" className="text-lg font-bold">🏠 Rehabify</Link>
        <div className="space-x-4">
          <Link href="/" className="hover:underline">Home</Link>
        </div>
      </div>
    </nav>
  );
}
