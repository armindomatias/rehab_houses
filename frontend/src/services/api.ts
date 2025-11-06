const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export async function analyzeProperty(link: string) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ link }),
  });
  
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to analyze property: ${res.status} ${errorText}`);
  }
  
  return res.json();
}
