export default function Footer() {
  return (
    <footer className="mt-16 border-t border-neutral-200 bg-white/80">
      <div className="mx-auto max-w-6xl px-4 py-8 text-xs text-neutral-500">
        © {new Date().getFullYear()} Rehabify. Estimates are illustrative. Always verify with professionals.
      </div>
    </footer>
  );
}
