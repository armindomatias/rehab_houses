"use client";

import { useEffect, useState } from "react";
import {
  formatCurrency,
  formatRoomType,
  formatCategoryName,
  getConditionColor,
  getConditionLabel,
} from "@/utils/formatters";

interface Division {
  division_id: string;
  room_type: string;
  size_m2: number;
  images: string[];
  costs: Record<string, number>;
  total_cost: number;
  detailed_notes?: string;
  conditions?: Record<string, number>;
}

interface AnalysisData {
  success?: boolean;
  listing_id?: string;
  property_info?: {
    location?: string;
    size_m2?: number;
    bedrooms?: number;
    bathrooms?: number;
  };
  investment?: {
    purchase_price: number;
    remodeling_costs: number;
    total_investment: number;
  };
  rehab_costs?: {
    property_total: number;
    summary: Record<string, number>;
    divisions: Division[];
  };
  rent_estimate?: {
    monthly_rent?: number;
    total_monthly_rent?: number;
    annual_rent?: number;
    rental_strategy?: string;
  };
  financial_metrics?: {
    metrics: {
      roi_percentage: number;
      net_yield: number;
      gross_yield: number;
      months_to_break_even: number;
    };
    net_income: {
      monthly_net_income: number;
      annual_net_income: number;
    };
    expenses: {
      total_annual_expenses: number;
    };
  };
}

export default function Report() {
  const [data, setData] = useState<AnalysisData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get data from sessionStorage
    const storedData = sessionStorage.getItem("analysisData");
    if (storedData) {
      try {
        const parsed = JSON.parse(storedData);
        setData(parsed);
      } catch (error) {
        console.error("Error parsing stored data:", error);
      }
    }
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  if (!data.success) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Analysis Report</h1>
        <p className="text-red-600">No analysis data available or analysis failed.</p>
      </div>
    );
  }


  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Property Analysis Report</h1>
        {data.listing_id && (
          <span className="text-sm text-gray-500">Listing ID: {data.listing_id}</span>
        )}
      </div>

      {/* Property Info */}
      {data.property_info && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Property Information</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {data.property_info.location && (
              <div>
                <p className="text-sm text-gray-600">Location</p>
                <p className="font-medium">{data.property_info.location}</p>
              </div>
            )}
            {data.property_info.size_m2 && (
              <div>
                <p className="text-sm text-gray-600">Size</p>
                <p className="font-medium">{data.property_info.size_m2} m²</p>
              </div>
            )}
            {data.property_info.bedrooms && (
              <div>
                <p className="text-sm text-gray-600">Bedrooms</p>
                <p className="font-medium">{data.property_info.bedrooms}</p>
              </div>
            )}
            {data.property_info.bathrooms && (
              <div>
                <p className="text-sm text-gray-600">Bathrooms</p>
                <p className="font-medium">{data.property_info.bathrooms}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Investment Summary */}
      {data.investment && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Investment Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Purchase Price</p>
              <p className="text-2xl font-bold">{formatCurrency(data.investment.purchase_price)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Remodeling Costs</p>
              <p className="text-2xl font-bold">{formatCurrency(data.investment.remodeling_costs)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Investment</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatCurrency(data.investment.total_investment)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Financial Metrics */}
      {data.financial_metrics && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Financial Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600">ROI</p>
              <p className="text-2xl font-bold text-green-600">
                {data.financial_metrics.metrics.roi_percentage.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Net Yield</p>
              <p className="text-2xl font-bold">
                {data.financial_metrics.metrics.net_yield.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Monthly Net Income</p>
              <p className="text-2xl font-bold">
                {formatCurrency(data.financial_metrics.net_income.monthly_net_income)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Annual Net Income</p>
              <p className="text-2xl font-bold">
                {formatCurrency(data.financial_metrics.net_income.annual_net_income)}
              </p>
            </div>
          </div>
          {data.rent_estimate && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-gray-600">Monthly Rent Estimate</p>
              <p className="text-xl font-semibold">
                {formatCurrency(
                  data.rent_estimate.monthly_rent || data.rent_estimate.total_monthly_rent || 0
                )}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Divisions with Images and Costs */}
      {data.rehab_costs && data.rehab_costs.divisions && data.rehab_costs.divisions.length > 0 && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-semibold">Divisions & Remodeling Costs</h2>
            <div className="text-right">
              <p className="text-sm text-gray-600">Total Remodeling Cost</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatCurrency(data.rehab_costs.property_total)}
              </p>
            </div>
          </div>

          {data.rehab_costs.divisions.map((division) => (
            <div key={division.division_id} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-semibold">
                      {formatRoomType(division.room_type)} - {division.division_id}
                    </h3>
                    <p className="text-sm text-gray-600">{division.size_m2} m²</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">Total Cost</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {formatCurrency(division.total_cost)}
                    </p>
                  </div>
                </div>

                {/* Conditions */}
                {division.conditions && (
                  <div className="mb-4 flex flex-wrap gap-4">
                    {Object.entries(division.conditions).map(([key, value]) => {
                      if (value === null || value === undefined) return null;
                      return (
                        <div key={key} className="text-sm">
                          <span className="text-gray-600">
                            {formatCategoryName(key)}:
                          </span>
                          <span className={`ml-2 font-medium ${getConditionColor(value)}`}>
                            {value.toFixed(1)} ({getConditionLabel(value)})
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Cost Breakdown */}
                {Object.keys(division.costs).length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm font-semibold mb-2">Cost Breakdown:</p>
                    <div className="flex flex-wrap gap-3">
                      {Object.entries(division.costs).map(([costType, cost]) => (
                        <div
                          key={costType}
                          className="bg-gray-100 px-3 py-1 rounded text-sm"
                        >
                          <span className="text-gray-600">
                            {formatCategoryName(costType)}:
                          </span>
                          <span className="ml-2 font-medium">{formatCurrency(cost)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Images */}
                {division.images && division.images.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-2">Images ({division.images.length}):</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {division.images.map((imageUrl, idx) => (
                        <div
                          key={idx}
                          className="relative aspect-square rounded-lg overflow-hidden bg-gray-200"
                        >
                          <img
                            src={imageUrl}
                            alt={`${division.room_type} ${idx + 1}`}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = "/placeholder-image.png";
                            }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Detailed Notes */}
                {division.detailed_notes && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-sm font-semibold mb-2">Notes:</p>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {division.detailed_notes}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Cost Summary by Category */}
      {data.rehab_costs && data.rehab_costs.summary && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Cost Summary by Category</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(data.rehab_costs.summary)
              .filter(([_, cost]) => cost > 0)
              .map(([category, cost]) => (
                <div key={category}>
                  <p className="text-sm text-gray-600">
                    {formatCategoryName(category)}
                  </p>
                  <p className="text-xl font-semibold">{formatCurrency(cost)}</p>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
