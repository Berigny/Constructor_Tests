import os
import json
import argparse
import re

def generate_fixes(prompts_dir, fixes_dir):
    """
    Generates LLM fix files based on the prompts.
    """
    if not os.path.exists(fixes_dir):
        os.makedirs(fixes_dir)

    for prompt_file in os.listdir(prompts_dir):
        if not prompt_file.endswith(".md"):
            continue

        prompt_path = os.path.join(prompts_dir, prompt_file)
        with open(prompt_path, "r") as f:
            content = f.read()

        # Extract the JSON block from the markdown file
        json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
        if not json_match:
            continue

        prompt_data = json.loads(json_match.group(1))

        original_query = prompt_data.get("original_query", "")
        blocklist_categories = prompt_data.get("blocklist_categories", [])

        # A simple heuristic: exclude blocklisted categories
        fix = {
            "revised_query_text": original_query,
            "must_have_tokens": [],
            "negative_tokens": [],
            "include_categories": [],
            "exclude_categories": blocklist_categories,
            "price_band": prompt_data.get("constraints", {}).get("budget", ""),
            "audience": prompt_data.get("constraints", {}).get("audience", ""),
            "rationale": "Initial fix based on excluding blocklisted categories.",
            "confidence": 0.5,
            "example_titles_expected": []
        }

        # Add maker/craft keywords
        if "making things" in original_query or "crafter" in original_query:
            fix["must_have_tokens"].extend(["craft", "kit", "set", "DIY", "art supplies", "making"])
            fix["exclude_categories"].extend(["Chocolate", "Novelty Confectionery", "Beauty", "Skincare", "Bath and Body", "Mens Grooming"])
            fix["rationale"] = "Added maker/craft keywords and excluded irrelevant categories."
            fix["confidence"] = 0.7

        # Add 90s motifs
        if "90s" in original_query or "retro" in original_query:
            fix["must_have_tokens"].extend(["90s", "retro", "nostalgia", "smiley", "butterfly clips", "checkerboard", "neon", "Hello Kitty"])
            fix["exclude_categories"].extend(["Beauty", "Hand Care", "Bath & Body", "Mens Grooming"])
            fix["rationale"] = "Added 90s motifs and excluded irrelevant categories."
            fix["confidence"] = 0.7

        fix_filename = os.path.splitext(prompt_file)[0] + ".json"
        fix_path = os.path.join(fixes_dir, fix_filename)

        with open(fix_path, "w") as f:
            json.dump(fix, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate LLM fix files from prompts.")
    parser.add_argument("--prompts-dir", required=True, help="Directory containing the prompt files.")
    parser.add_argument("--fixes-dir", required=True, help="Directory to save the fix files.")
    args = parser.parse_args()

    generate_fixes(args.prompts_dir, args.fixes_dir)
    print(f"Fixes generated in {args.fixes_dir}")
