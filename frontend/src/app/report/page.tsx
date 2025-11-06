"use client";

import { useEffect, useState } from "react";

interface AnalysisData {
  link?: string;
  renovation_cost?: number;
  monthly_rent_estimate?: number;
  roi?: string;
}

export default function Report() {
  const [data, setData] = useState<AnalysisData>({});

  useEffect(() => {
    // Get data from sessionStorage
    const storedData = sessionStorage.getItem("analysisData");
    if (storedData) {
      try {
        setData(JSON.parse(storedData));
      } catch (error) {
        console.error("Error parsing stored data:", error);
      }
    }
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Analysis Report</h1>
      {data.link ? (
        <div className="space-y-2 bg-white p-6 rounded-lg shadow">
          <p><strong>Property Link:</strong> {data.link}</p>
          <p><strong>Renovation Cost:</strong> €{data.renovation_cost?.toLocaleString()}</p>
          <p><strong>Monthly Rent Estimate:</strong> €{data.monthly_rent_estimate?.toLocaleString()}</p>
          <p><strong>ROI:</strong> {data.roi}</p>
        </div>
      ) : (
        <p className="text-gray-600">No analysis data available.</p>
      )}
    </div>
  );
}

