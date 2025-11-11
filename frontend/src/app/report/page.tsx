"use client";

import { useEffect, useState } from "react";
import {
  formatCurrency,
  formatRoomType,
  formatCategoryName,
  getConditionColor,
  getConditionLabel,
} from "@/utils/formatters";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { MapPin, Building2, BedDouble, Home, Wrench, TrendingUp, TriangleAlert } from "lucide-react";

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
      <div className="p-6 max-w-6xl mx-auto">
        <div className="text-center text-neutral-600">Loading...</div>
      </div>
    );
  }

  if (!data.success) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Analysis Report</h1>
        <p className="text-red-600">No analysis data available or analysis failed.</p>
      </div>
    );
  }


  return (
    <main className="mx-auto max-w-6xl px-4 mt-8">
      <div className="grid items-start gap-6 md:grid-cols-[1.2fr_1.8fr]">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Property Info Card */}
          {data.property_info && (
            <Card>
              <CardBody className="flex items-start gap-4">
                <div className="hidden h-28 w-40 flex-none rounded-xl bg-neutral-200 md:block" />
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {data.property_info.location && (
                      <span className="inline-flex items-center gap-1 rounded-lg bg-neutral-100 px-2 py-1 text-xs font-medium">
                        <MapPin className="h-3 w-3" /> {data.property_info.location}
                      </span>
                    )}
                    {data.property_info.size_m2 && (
                      <span className="inline-flex items-center gap-1 rounded-lg bg-neutral-100 px-2 py-1 text-xs font-medium">
                        <Building2 className="h-3 w-3" /> {data.property_info.size_m2} m²
                      </span>
                    )}
                    {data.property_info.bedrooms && (
                      <span className="inline-flex items-center gap-1 rounded-lg bg-neutral-100 px-2 py-1 text-xs font-medium">
                        <BedDouble className="h-3 w-3" /> {data.property_info.bedrooms} beds
                      </span>
                    )}
                  </div>
                  <h2 className="mt-2 text-xl font-bold">Idealista Listing</h2>
                  {data.listing_id && (
                    <p className="text-xs text-neutral-500">Listing ID: {data.listing_id}</p>
                  )}
                </div>
              </CardBody>
            </Card>
          )}

          {/* Risk & Notes Card */}
          <Card>
            <CardHeader title="Risk & Notes" icon={<TriangleAlert className="h-4 w-4" />} />
            <CardBody>
              <ul className="list-disc pl-5 text-sm text-neutral-700 space-y-1">
                <li>Check building structure and moisture before heavy scope.</li>
                <li>Energy efficiency upgrades may unlock higher rent and lower bills.</li>
                <li>Verify condominium fees (HOA) and IMI for net yield accuracy.</li>
              </ul>
            </CardBody>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Remodel Cost Card */}
          {data.investment && (
            <Card>
              <CardHeader title="Estimated remodel cost" icon={<Wrench className="h-4 w-4" />} />
              <CardBody>
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <div className="text-3xl font-extrabold">
                      {formatCurrency(data.investment.remodeling_costs)}
                    </div>
                    {data.property_info?.size_m2 && (
                      <p className="text-xs text-neutral-500">
                        {data.property_info.size_m2} m² × estimated cost per m²
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-neutral-500">Capex (incl. purchase)</p>
                    <div className="text-lg font-bold">
                      {formatCurrency(data.investment.total_investment)}
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Rental Potential Card */}
          {data.rent_estimate && (
            <Card>
              <CardHeader title="Rental potential" icon={<Home className="h-4 w-4" />} />
              <CardBody>
                <div className="space-y-3">
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-2xl font-extrabold">
                        {formatCurrency(
                          data.rent_estimate.monthly_rent || data.rent_estimate.total_monthly_rent || 0
                        )}{" "}
                        / month
                      </div>
                      {data.rent_estimate.rental_strategy && (
                        <p className="text-xs text-neutral-500">
                          {data.rent_estimate.rental_strategy}
                        </p>
                      )}
                    </div>
                  </div>
                  {data.rent_estimate.annual_rent && (
                    <div className="text-sm text-neutral-600">
                      Annual rent: {formatCurrency(data.rent_estimate.annual_rent)}
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>
          )}

          {/* Yield & Payback Card */}
          {data.financial_metrics && (
            <Card>
              <CardHeader title="Yield & payback" icon={<TrendingUp className="h-4 w-4" />} />
              <CardBody>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs text-neutral-500">Gross yield</div>
                    <div className="text-lg font-bold text-neutral-900">
                      {data.financial_metrics.metrics.gross_yield.toFixed(1)}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs text-neutral-500">Net yield</div>
                    <div className="text-lg font-bold text-emerald-700">
                      {data.financial_metrics.metrics.net_yield.toFixed(1)}%
                    </div>
                  </div>
                  <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs text-neutral-500">Net income / yr</div>
                    <div className="text-lg font-bold text-neutral-900">
                      {formatCurrency(data.financial_metrics.net_income.annual_net_income)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs text-neutral-500">Payback</div>
                    <div className="text-lg font-bold text-neutral-900">
                      {(data.financial_metrics.metrics.months_to_break_even / 12).toFixed(1)} yrs
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      {/* Divisions with Images and Costs */}
      {data.rehab_costs && data.rehab_costs.divisions && data.rehab_costs.divisions.length > 0 && (
        <div className="space-y-6 mt-8">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-semibold">Divisions & Remodeling Costs</h2>
            <div className="text-right">
              <p className="text-sm text-neutral-600">Total Remodeling Cost</p>
              <p className="text-2xl font-bold text-emerald-700">
                {formatCurrency(data.rehab_costs.property_total)}
              </p>
            </div>
          </div>

          {data.rehab_costs.divisions.map((division) => (
            <Card key={division.division_id}>
              <CardBody>
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-semibold">
                      {formatRoomType(division.room_type)} - {division.division_id}
                    </h3>
                    <p className="text-sm text-neutral-600">{division.size_m2} m²</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-neutral-600">Total Cost</p>
                    <p className="text-2xl font-bold text-emerald-700">
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
                          <span className="text-neutral-600">
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
                          className="bg-neutral-100 px-3 py-1 rounded-xl text-sm border border-neutral-200"
                        >
                          <span className="text-neutral-600">
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
                          className="relative aspect-square rounded-xl overflow-hidden bg-neutral-200"
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
                    <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                      {division.detailed_notes}
                    </p>
                  </div>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Cost Summary by Category */}
      {data.rehab_costs && data.rehab_costs.summary && (
        <div className="mt-8">
          <Card>
            <CardHeader title="Cost Summary by Category" icon={<Wrench className="h-4 w-4" />} />
            <CardBody>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(data.rehab_costs.summary)
                  .filter(([_, cost]) => cost > 0)
                  .map(([category, cost]) => (
                    <div key={category} className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                      <p className="text-xs text-neutral-500 mb-1">
                        {formatCategoryName(category)}
                      </p>
                      <p className="text-lg font-bold text-neutral-900">{formatCurrency(cost)}</p>
                    </div>
                  ))}
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </main>
  );
}
