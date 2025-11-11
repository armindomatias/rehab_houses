import Link from "next/link";
import { Euro } from "lucide-react";
import { Button } from "./ui/Button";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-600 text-white">
            <Euro className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">Rehabify</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm md:flex">
          <a className="text-neutral-600 hover:text-neutral-900" href="#how">
            How it works
          </a>
          <Link href="/">
            <Button variant="secondary">New analysis</Button>
          </Link>
        </nav>
      </div>
    </header>
  );
}
