import os
import json
import argparse
import re
import requests

def call_openrouter_api(prompt):
    """
    Calls the OpenRouter API with the given prompt.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    base_url = os.environ.get("OPENROUTER_BASE_URL")
    model = os.environ.get("OPENROUTER_MODEL")

    if not all([api_key, base_url, model]):
        raise ValueError("Please set the OPENROUTER_API_KEY, OPENROUTER_BASE_URL, and OPENROUTER_MODEL environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def generate_fixes(prompts_dir, fixes_dir, use_llm=False):
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

        fix_filename = os.path.splitext(prompt_file)[0] + ".json"
        fix_path = os.path.join(fixes_dir, fix_filename)

        if use_llm:
            try:
                api_response = call_openrouter_api(content)
                llm_json_str = api_response["choices"][0]["message"]["content"]
                # The LLM might return a string containing a JSON block
                json_match = re.search(r"```json\n(.*?)\n```", llm_json_str, re.DOTALL)
                if json_match:
                    llm_json_str = json_match.group(1)

                fix = json.loads(llm_json_str)
                with open(fix_path, "w") as f:
                    json.dump(fix, f, indent=2)
                continue
            except Exception as e:
                print(f"Error calling LLM for {prompt_file}: {e}")
                # Fallback to simple heuristics if LLM fails
                pass


        # Extract the JSON block from the markdown file for heuristic-based fixing
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

        with open(fix_path, "w") as f:
            json.dump(fix, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate LLM fix files from prompts.")
    parser.add_argument("--prompts-dir", required=True, help="Directory containing the prompt files.")
    parser.add_argument("--fixes-dir", required=True, help="Directory to save the fix files.")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM to generate fixes.")
    args = parser.parse_args()

    generate_fixes(args.prompts_dir, args.fixes_dir, args.use_llm)
    print(f"Fixes generated in {args.fixes_dir}")
