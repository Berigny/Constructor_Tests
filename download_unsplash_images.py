import os
import json
import time
import argparse
import requests

# Replace with your Unsplash Access Key
access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "BKixl8dRzGpGeFmQ6unCJMHKfIBtTmBx5mWLaL4DdVk")

# List of 50 search queries
queries = [
    "parent family", "grandparent elderly", "couple partner", "child kid", "two friends",
    "office coworker", "dog", "cat", "fish aquarium", "newborn", "toddler", "kid 6-8",
    "tween", "teenager", "adult", "adult male", "adult female", "newborn", "toddler",
    "kid 6-8", "tween", "teenager", "plush toy", "sensory play", "teething ring",
    "baby board book", "toy castle", "wooden blocks", "crayons arts crafts", "STEM kit",
    "jigsaw puzzle", "kids running outdoor", "gaming controller", "trading cards",
    "headphones music", "sewing DIY", "cooking ingredients", "spa candle",
    "potted herb gardening", "paint brush canvas", "sneakers sport", "fashion accessories",
    "dog chew toy", "pet bed", "dog grooming", "dog hiking", "dog treats", "dog training",
    "reading novel", "board game night"
]

# Collection IDs for your specified categories
collection_ids = {
    "Featured": "317099",
    "Wallpapers": "1065976",
    "Nature": "3330448",
    "3D Renders": "7683081",
    "Textures": "3330446",
    "Travel": "2597413",
    "Film": "2429828",
    "People": "3349876",
    "Architecture": "3348849",
    "Interiors": "3336091",
    "Street Photography": "3336097",
    "Experimental": "296"
}

# Map each query to a relevant collection
query_collections = [
    "People", "People", "People", "People", "People",
    "Interiors", "Nature", "Nature", "Nature", "People",
    "People", "People", "People", "People", "People",
    "People", "People", "People", "People", "People",
    "People", "People", "Textures", "Experimental", "Textures",
    "Textures", "Textures", "Textures", "Textures", "Experimental",
    "Textures", "Nature", "Experimental", "Textures", "Textures",
    "Textures", "Textures", "Textures", "Nature", "Textures",
    "Street Photography", "Textures", "Textures", "Textures", "Textures",
    "Nature", "Textures", "Textures", "Textures", "Interiors"
]

# CLI options
ap = argparse.ArgumentParser(description="Download sample images from Unsplash by query/collection")
ap.add_argument("--limit", type=int, default=None, help="Limit number of images to download (default: all)")
ap.add_argument("--out-dir", default="unsplash_images", help="Output directory for images and metadata.json")
ap.add_argument("--sleep", type=float, default=0.6, help="Sleep seconds between API calls to avoid rate limits")
ap.add_argument("--only-queries", nargs="+", default=None, help="Only download for these query strings (case-insensitive; '/' treated as space)")
args = ap.parse_args()

# Create output folder
out_dir = args.out_dir
os.makedirs(out_dir, exist_ok=True)

# List to store metadata for all images
all_metadata = []

def _norm(s: str) -> str:
    return " ".join(str(s).replace("/", " ").split()).lower().strip()

pairs = list(zip(queries, query_collections))
if args.only_queries:
    wanted = set(_norm(q) for q in args.only_queries)
    pairs = [(q, c) for (q, c) in pairs if _norm(q) in wanted]

limit = args.limit if args.limit is not None else len(pairs)

seen_ids = set()

for idx, (query, collection) in enumerate(pairs, start=1):
    if idx > limit:
        break
    # API endpoint for a random photo
    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "collections": collection_ids[collection],
        "client_id": access_key
    }
    
    # Fetch photo metadata
    response = requests.get(url, params=params)
    
    if response.status_code == 404:
        # Fallback 1: query only
        fallback_params = {
            "query": query,
            "client_id": access_key
        }
        response = requests.get(url, params=fallback_params)
    if response.status_code == 404:
        # Fallback 2: collection only
        fallback_params = {
            "collections": collection_ids[collection],
            "client_id": access_key
        }
        response = requests.get(url, params=fallback_params)
    if response.status_code == 404:
        # Fallback 3: no filters
        fallback_params = {"client_id": access_key}
        response = requests.get(url, params=fallback_params)

    if response.status_code == 200:
        data = response.json()
        img_url = data['urls']['regular']
        photo_id = data.get('id')
        if not photo_id:
            print(f"Missing photo id for query '{query}'")
            continue
        if photo_id in seen_ids:
            print(f"Duplicate photo id {photo_id} skipped")
            continue
        seen_ids.add(photo_id)
        
        # Extract relevant metadata
        metadata = {
            "image_number": idx,
            "query": query,
            "collection": collection,
            "photo_id": photo_id,
            "description": data.get('description', 'N/A'),
            "alt_description": data.get('alt_description', 'N/A'),
            "photographer": data.get('user', {}).get('name', 'N/A'),
            "tags": [tag['title'] for tag in data.get('tags', [])],
            "width": data.get('width', 'N/A'),
            "height": data.get('height', 'N/A'),
            "filename": f"{photo_id}.jpg",
        }
        all_metadata.append(metadata)
        
        # Download the image
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            filename = os.path.join(out_dir, f"{photo_id}.jpg")
            if os.path.exists(filename):
                print(f"File already exists, skipping: {filename}")
            else:
                with open(filename, 'wb') as f:
                    f.write(img_response.content)
                print(f"Downloaded {filename} from {collection}")
        else:
            print(f"Failed to download image for query '{query}' in collection '{collection}'")
    else:
        print(f"API request failed for query '{query}' in collection '{collection}': {response.status_code} - {response.text}")
        all_metadata.append({
            "image_number": idx,
            "query": query,
            "collection": collection,
            "error": f"API request failed: {response.status_code}"
        })
    # Rate limiting buffer
    time.sleep(args.sleep)

# Save metadata to a JSON file
metadata_file = os.path.join(out_dir, "metadata.json")
with open(metadata_file, 'w') as f:
    json.dump(all_metadata, f, indent=4)
print(f"Saved metadata to {metadata_file}")
