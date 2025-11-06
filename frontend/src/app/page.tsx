"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeProperty } from "@/services/api";

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

  return (
    <div className="flex flex-col items-center justify-center p-6 min-h-[calc(100vh-80px)]">
      <h1 className="text-3xl font-bold mb-6">Rehabify</h1>
      <form onSubmit={handleSubmit} className="w-full max-w-md">
        <input
          type="text"
          placeholder="Paste Idealista link..."
          value={link}
          onChange={(e) => setLink(e.target.value)}
          className="w-full p-3 border rounded-lg mb-4"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Analyzing..." : "Analyze Property"}
        </button>
      </form>
    </div>
  );
}

