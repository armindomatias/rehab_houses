
import requests
import json
import os
from typing import List, Dict, Any, Optional

import logging
from datetime import datetime

import re
from io import BytesIO
from PIL import Image
import imagehash

class Deduplication:

    def __init__(self):
        self.logger = self._setup_logging()
        self.logger.info("Initializing Deduplication...")

    # Logger setup
    def _setup_logging(self):
        """Setup logging configuration with both file and console handlers"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create a timestamp for the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/deduplication_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def _download_image_bytes(self, url: str) -> Optional[bytes]:
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                return resp.content
            self.logger.warning(f"Failed to download image ({resp.status_code}): {url}")
            return None
        except Exception as e:
            self.logger.warning(f"Error downloading image {url}: {e}")
            return None

    def _compute_phash(self, image_bytes: bytes) -> Optional[imagehash.ImageHash]:
        try:
            with Image.open(BytesIO(image_bytes)) as im:
                im = im.convert("RGB")
                return imagehash.phash(im)
        except Exception as e:
            self.logger.warning(f"Error computing pHash: {e}")
            return None

    def _cluster_by_phash_and_sequence(
        self,
        items: List[Dict[str, Any]],
        order_map: Dict[str, int],
        distance_threshold: int = 12,
    ) -> List[List[Dict[str, Any]]]:
        """Greedy clustering by gallery order, starting a new cluster when pHash differs beyond threshold."""
        # Precompute hashes and order
        enriched = []
        for it in items:
            url = it.get("room_url") or it.get("image_url")
            order_idx = order_map.get(url, 10_000)
            ph = None
            img_bytes = self._download_image_bytes(url) if url else None
            if img_bytes:
                ph = self._compute_phash(img_bytes)
            enriched.append({"item": it, "url": url, "order": order_idx, "phash": ph})

        # Sort by gallery order to reflect natural grouping
        enriched.sort(key=lambda x: x["order"])

        clusters: List[List[Dict[str, Any]]] = []
        current: List[Dict[str, Any]] = []
        current_rep: Optional[imagehash.ImageHash] = None

        def distance(a: Optional[imagehash.ImageHash], b: Optional[imagehash.ImageHash]) -> int:
            if a is None or b is None:
                return distance_threshold  # force split when hashes missing
            return a - b

        for e in enriched:
            if not current:
                current = [e]
                current_rep = e["phash"]
                continue
            d = distance(current_rep, e["phash"])
            if d <= distance_threshold:
                current.append(e)
                # Update representative lazily: keep first as anchor
            else:
                clusters.append(current)
                current = [e]
                current_rep = e["phash"]

        if current:
            clusters.append(current)

        # Convert back to list of raw items
        return [[ee["item"] for ee in c] for c in clusters]

    def _aggregate_numeric_fields(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        numeric_keys = [
            "size_m2",
            "overall_condition",
            "appliances_condition",
            "plumbing_condition",
            "electrical_condition",
            "flooring_condition",
            "ceiling_condition",
            "painting_condition",
            "windows_condition",
            "windows_number",
        ]
        agg: Dict[str, Any] = {}
        for key in numeric_keys:
            vals = [v for v in (it.get(key) for it in items) if isinstance(v, (int, float))]
            if not vals:
                continue
            mean_val = sum(vals) / len(vals)
            # Round counts to int, others to one decimal
            if key in ("size_m2", "windows_number"):
                agg[key] = int(round(mean_val))
            else:
                agg[key] = round(mean_val, 1)
        return agg

    def _merge_notes(self, items: List[Dict[str, Any]]) -> str:
        notes = []
        for it in items:
            n = it.get("detailed_notes")
            if n and isinstance(n, str):
                notes.append(n.strip())
        # Deduplicate heuristically
        seen = set()
        unique = []
        for n in notes:
            key = n.lower()
            if key not in seen:
                seen.add(key)
                unique.append(n)
        return " \n".join(unique)

    def deduplicate_aggregated_results(
        self,
        aggregated_input_path: str,
        listing_json_path: str,
        output_filename: Optional[str] = None,
        distance_threshold: int = 12,
    ) -> str:
        """Create per-division aggregated results: one record per unique room division with image gallery.

        Returns the output file path.
        """
        # Load aggregated classification
        with open(aggregated_input_path, "r", encoding="utf-8") as f:
            aggregated = json.load(f)

        # Load listing to get gallery order and expected counts
        with open(listing_json_path, "r", encoding="utf-8") as f:
            listing_arr = json.load(f)
        listing = listing_arr[0] if isinstance(listing_arr, list) and listing_arr else listing_arr
        gallery = listing.get("gallery", [])
        order_map = {g.get("url"): idx for idx, g in enumerate(gallery)}

        property_specs = listing.get("characteristics", []) or []

        # Error handling for the property specs text/regex converter
        def _extract_number(text, default=None):
            """Safely extract first number from text"""
            try:
                match = re.search(r'\d+', str(text))
                return int(match.group()) if match else None
            except (ValueError, AttributeError):
                return None

        def _safe_get(lst, index, default=None):
            """Safely get item from list by index"""
            try:
                return lst[index]
            except (IndexError, TypeError):
                return None

        # Extract with error handling
        expected_bedrooms = _extract_number(_safe_get(property_specs, 1))
        expected_bathrooms = _extract_number(_safe_get(property_specs, 2))

        result: Dict[str, List[Dict[str, Any]]] = {}
        for room_type, items in aggregated.items():
            # Cluster within room_type
            clusters = self._cluster_by_phash_and_sequence(items, order_map, distance_threshold)

            # Optionally cap number of clusters based on expected counts
            cap = None
            if room_type in ("bedroom", "bedrooms", "room", "quarto") and isinstance(expected_bedrooms, int):
                cap = expected_bedrooms
            elif room_type in ("bathroom", "bath", "casa_de_banho") and isinstance(expected_bathrooms, int):
                cap = expected_bathrooms
            elif room_type in ("kitchen", "living_room"):
                cap = 1

            if cap is not None and len(clusters) > cap:
                # Keep the largest clusters first
                clusters.sort(key=lambda c: len(c), reverse=True)
                clusters = clusters[:cap]

            # Build aggregated entries per cluster
            dedup_entries: List[Dict[str, Any]] = []
            for idx, cluster_items in enumerate(clusters, 1):
                numeric = self._aggregate_numeric_fields(cluster_items)
                # Prefer consistent room_type majority
                types = [it.get("room_type") for it in cluster_items if it.get("room_type")]
                final_type = room_type
                if types:
                    # simple majority
                    counts: Dict[str, int] = {}
                    for t in types:
                        counts[t] = counts.get(t, 0) + 1
                    final_type = max(counts.items(), key=lambda x: x[1])[0]

                images = list({it.get("room_url") or it.get("image_url") for it in cluster_items if it.get("room_url") or it.get("image_url")})
                notes = self._merge_notes(cluster_items)

                entry = {
                    "division_id": f"{final_type}_{idx}",
                    "room_type": final_type,
                    "images": images,
                    "num_source_images": len(cluster_items),
                    **numeric,
                    "detailed_notes": notes,
                }
                dedup_entries.append(entry)

            result[room_type] = dedup_entries

        # Save
        os.makedirs("data/image_analysis", exist_ok=True)
        if not output_filename:
            base_name = os.path.splitext(os.path.basename(aggregated_input_path))[0]
            output_filename = f"{base_name}_dedup.json"
        out_path = os.path.join("data", "image_analysis", output_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Deduplicated per-division results saved to: {out_path}")
        return out_path

if __name__ == "__main__":

    deduplication = Deduplication()

    listing_number = "34082358"

    dedup_out = deduplication.deduplicate_aggregated_results(
        aggregated_input_path=f"data/image_analysis/idealista_listing_{listing_number}_classifications_aggregated.json",
        listing_json_path=f"data/scraped_data/idealista_listing_{listing_number}.json",
        output_filename=f"idealista_listing_{listing_number}_classifications_dedup.json",
        distance_threshold=12,  # lower = stricter clustering; 10–14 is a good range
    )
    print(dedup_out)