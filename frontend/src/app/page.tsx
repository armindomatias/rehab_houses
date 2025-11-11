"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeProperty } from "@/services/api";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Home as HomeIcon, Wrench, TrendingUp, ExternalLink, Loader2 } from "lucide-react";

export default function Home() {
  const [link, setLink] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    // Validate link is not empty
    if (!link.trim()) {
      alert("Please enter a property link");
      return;
    }
    
    setLoading(true);
    
    try {
      const data = await analyzeProperty(link);
      sessionStorage.setItem("analysisData", JSON.stringify(data));
      router.push("/report");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      alert(`Failed to analyze property: ${errorMessage}`);
      setLoading(false);
    }
  };

  const infoPill = (label: string, value: string) => (
    <div className="flex min-w-[140px] items-center justify-between rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs">
      <span className="text-neutral-500">{label}</span>
      <span className="font-semibold text-neutral-800">{value}</span>
    </div>
  );

  return (
    <main className="mx-auto max-w-4xl px-4 overflow-visible">
      <div className="mx-auto mt-16 grid items-center gap-10 rounded-3xl bg-white p-8 shadow-sm md:grid-cols-2 md:p-12 overflow-visible">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight text-neutral-900 md:text-5xl">
            Turn listings into <span className="text-emerald-700">investments</span>.
          </h1>
          <p className="mt-3 text-neutral-600">
            Paste an Idealista link and get renovation, rental potential, and yield estimates instantly.
          </p>
          <form onSubmit={handleSubmit} className="mt-6 space-y-3">
            <Input
              placeholder="Paste property link (idealista.pt)"
              value={link}
              onChange={(e) => setLink(e.target.value)}
              disabled={loading}
            />
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button type="submit" disabled={!link || loading} loading={loading}>
                Analyze Property
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setLink("https://www.idealista.pt/imovel/EXAMPLE");
                }}
                disabled={loading}
              >
                Try demo link
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 pt-2 text-xs text-neutral-500">
              {infoPill("Fast", "< 2s")}
              {infoPill("Coverage", "PT 🇵🇹")}
              {infoPill("Output", "Capex • Yield • Risk")}
            </div>
          </form>
        </div>
        <div className="relative hidden md:block min-h-[400px]">
          <Card className="absolute -left-8 top-10 w-72 rotate-[-2deg]">
            <CardHeader title="Remodel estimate" icon={<Wrench className="h-4 w-4" />} />
            <CardBody>
              <div className="text-2xl font-bold text-neutral-900">€45k – €55k</div>
              <p className="mt-1 text-xs text-neutral-500">Kitchen • Bathrooms • Flooring</p>
            </CardBody>
          </Card>
          <Card className="absolute right-0 top-28 w-72 rotate-2">
            <CardHeader title="Rental potential" icon={<HomeIcon className="h-4 w-4" />} />
            <CardBody>
              <div className="text-2xl font-bold">€1,950 / mo</div>
              <p className="mt-1 text-xs text-neutral-500">Entire apartment • Lisboa</p>
            </CardBody>
          </Card>
          <Card className="absolute bottom-0 left-10 w-72">
            <CardHeader title="Net yield" icon={<TrendingUp className="h-4 w-4" />} />
            <CardBody>
              <div className="text-2xl font-bold text-emerald-700">8.9%</div>
              <p className="mt-1 text-xs text-neutral-500">After costs & vacancy</p>
            </CardBody>
          </Card>
        </div>
      </div>

      <div id="how" className="mx-auto mt-12 grid gap-4 md:grid-cols-3">
        {[
          { icon: <ExternalLink className="h-4 w-4" />, title: "Paste link", text: "We read photos, text, and meta." },
          { icon: <Wrench className="h-4 w-4" />, title: "Estimate remodel", text: "Choose light/medium/heavy scope." },
          { icon: <TrendingUp className="h-4 w-4" />, title: "See yield", text: "Compare entire vs per-room rent." },
        ].map((s, i) => (
          <Card key={i}>
            <CardHeader title={s.title} icon={s.icon} />
            <CardBody>
              <p className="text-sm text-neutral-600">{s.text}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 z-20 grid place-items-center bg-white/70 backdrop-blur">
          <div className="flex items-center gap-3 rounded-2xl border border-neutral-200 bg-white px-5 py-3 shadow-sm">
            <Loader2 className="h-5 w-5 animate-spin text-emerald-700" />
            <span className="text-sm font-medium">Analyzing listing…</span>
          </div>
        </div>
      )}
    </main>
  );
}

