/**
 * Utility functions for formatting data in the application
 */

/**
 * Format a number as currency in EUR (Portuguese format)
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("pt-PT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format room type string (e.g., "living_room" -> "Living Room")
 */
export function formatRoomType(roomType: string): string {
  return roomType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Format category name (e.g., "flooring_condition" -> "Flooring Condition")
 */
export function formatCategoryName(category: string): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Get Tailwind CSS color class based on condition rating
 * @param condition - Condition rating (0-4 scale)
 * @returns Tailwind CSS color class
 */
export function getConditionColor(condition?: number): string {
  if (!condition) return "text-gray-500";
  if (condition >= 3.5) return "text-green-600";
  if (condition >= 2.5) return "text-yellow-600";
  return "text-red-600";
}

/**
 * Get human-readable label for condition rating
 * @param condition - Condition rating (0-4 scale)
 * @returns Label string
 */
export function getConditionLabel(condition?: number): string {
  if (!condition) return "N/A";
  if (condition >= 3.5) return "Excellent";
  if (condition >= 2.5) return "Good";
  if (condition >= 1.5) return "Fair";
  return "Poor";
}

/**
 * Format percentage with 2 decimal places
 */
export function formatPercentage(value: number): string {
  return `${value.toFixed(2)}%`;
}

