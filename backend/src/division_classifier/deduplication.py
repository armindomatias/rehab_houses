
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
        #os.makedirs('logs', exist_ok=True)
        
        # Create a timestamp for the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #log_filename = f"logs/deduplication_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                #logging.FileHandler(log_filename),
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
        distance_threshold: int = 15,  # Balanced threshold for room clustering
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
                return distance_threshold + 1  # force split when hashes missing
            return a - b

        # First pass: group by very similar images (likely same room, same angle)
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

        # Second pass: merge clusters that are likely the same room
        # This helps when images of the same room are taken from very different angles
        merged_clusters = []
        used = set()
        
        for i, cluster1 in enumerate(clusters):
            if i in used:
                continue
                
            merged = cluster1.copy()
            used.add(i)
            
            # Look for other clusters that might be the same room
            for j, cluster2 in enumerate(clusters[i+1:], i+1):
                if j in used:
                    continue
                    
                # Check if any image in cluster2 is similar to any image in merged
                should_merge = False
                for item1 in merged:
                    for item2 in cluster2:
                        if (item1["phash"] and item2["phash"] and 
                            distance(item1["phash"], item2["phash"]) <= distance_threshold * 1.5):
                            should_merge = True
                            break
                    if should_merge:
                        break
                
                if should_merge:
                    merged.extend(cluster2)
                    used.add(j)
            
            merged_clusters.append(merged)

        # Convert back to list of raw items
        return [[ee["item"] for ee in c] for c in merged_clusters]

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
        listing_id: str,
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

        # Extract with error handling and better Portuguese text parsing
        expected_bedrooms = None
        expected_bathrooms = None
        
        for i, spec in enumerate(property_specs):
            spec_text = str(spec).lower()
            if 't3' in spec_text or 't2' in spec_text or 't1' in spec_text:
                # Extract number from T3, T2, T1 format
                match = re.search(r't(\d+)', spec_text)
                if match:
                    expected_bedrooms = int(match.group(1))
            elif 'quarto' in spec_text or 'bedroom' in spec_text:
                # Extract number from "X quartos" format
                match = re.search(r'(\d+)\s*quarto', spec_text)
                if match:
                    expected_bedrooms = int(match.group(1))
            elif 'casa de banho' in spec_text or 'bathroom' in spec_text:
                # Extract number from "X casas de banho" format
                match = re.search(r'(\d+)\s*casa de banho', spec_text)
                if match:
                    expected_bathrooms = int(match.group(1))
            elif 'banho' in spec_text:
                # Extract number from "X banhos" format
                match = re.search(r'(\d+)\s*banho', spec_text)
                if match:
                    expected_bathrooms = int(match.group(1))

        result: Dict[str, List[Dict[str, Any]]] = {}
        for room_type, items in aggregated.items():
            self.logger.info(f"Processing {room_type}: {len(items)} images")
            
            # Cluster within room_type
            clusters = self._cluster_by_phash_and_sequence(items, order_map, distance_threshold)
            self.logger.info(f"  Created {len(clusters)} initial clusters")

            # Optionally cap number of clusters based on expected counts
            cap = None
            if room_type in ("bedroom", "bedrooms", "room", "quarto") and isinstance(expected_bedrooms, int):
                cap = expected_bedrooms
                self.logger.info(f"  Capping bedrooms to {cap} (expected: {expected_bedrooms})")
            elif room_type in ("bathroom", "bath", "casa_de_banho") and isinstance(expected_bathrooms, int):
                cap = expected_bathrooms
                self.logger.info(f"  Capping bathrooms to {cap} (expected: {expected_bathrooms})")
            elif room_type in ("kitchen", "living_room"):
                cap = 1
                self.logger.info(f"  Capping {room_type} to {cap}")

            if cap is not None and len(clusters) > cap:
                # Keep the largest clusters first (most images = most representative)
                clusters.sort(key=lambda c: len(c), reverse=True)
                original_count = len(clusters)
                clusters = clusters[:cap]
                self.logger.info(f"  Reduced from {original_count} to {len(clusters)} clusters")
            else:
                self.logger.info(f"  No capping applied, keeping {len(clusters)} clusters")

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
                self.logger.info(f"    Cluster {idx}: {len(cluster_items)} images -> {len(images)} unique URLs")

            result[room_type] = dedup_entries

        # Save
        listing_folder = os.path.join("data", "image_analysis", listing_id)
        os.makedirs(listing_folder, exist_ok=True)
        
        if not output_filename:
            base_name = os.path.splitext(os.path.basename(aggregated_input_path))[0]
            output_filename = f"{base_name}_dedup.json"
        out_path = os.path.join(listing_folder, output_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Deduplicated per-division results saved to: {out_path}")
        return out_path

if __name__ == "__main__":

    deduplication = Deduplication()

    listing_number = "34458598"

    dedup_out = deduplication.deduplicate_aggregated_results(
        aggregated_input_path=f"data/image_analysis/{listing_number}/idealista_listing_{listing_number}_classifications_aggregated.json",
        listing_json_path=f"data/scraped_data/idealista_listing_{listing_number}.json",
        listing_id=listing_number,
        output_filename=f"idealista_listing_{listing_number}_classifications_dedup.json",
        distance_threshold=15,  # Balanced threshold for room clustering; 12-18 is a good range
    )
    print(dedup_out)