# SYSTEM (give this to the LLM)

You rewrite a natural-language shopping query to **pull better top-3 gifts** from a retail search API (Constructor).
You’ll be given:

* The **original query** and **constraints** (budget, audience, occasion).
* The **API JSON results** (top N).
* A **whitelist of useful categories** and a **blocklist of drift categories**.

Your job:

1. **Diagnose drift** in the shown results (e.g., beauty, confectionery, party favours, kids).
2. **Rewrite the natural-language query** so embeddings anchor to the *right motifs* and *right domain*.
3. Propose **include/exclude categories** and **must/negative tokens** to stabilise results.
4. Keep **budget** and constraints intact.
5. Prefer **adult, maker, or era-specific** cues when appropriate.

### Heuristics

* Treat results as **good** if they clearly match the user intent and constraints (title/tags/categories contain the right motifs; price within budget).
* Common drift to block: `Beauty`, `Bath & Body`, `Hand Care / Sanitiser`, `Cards / Gift Bags`, `Party Favours & Glow`, `Chocolate / Lollies`, `Kids Art, Craft & Stationery`.
* When the theme is era/style (e.g., **90s/Y2K**), inject explicit **motifs** (e.g., `smiley, butterfly clips, checkerboard, neon, cassette, Tamagotchi, Polaroid, scrunchies, Hello Kitty, mood ring`).
* When the theme is **maker/craft**, inject **tool/kit/material** terms (e.g., `tool, kit, set, materials, glue gun, precision knife, cutting mat, beads, clay, brushes`).
* If catalogue uses `&` in category names, render as **“and”** in URLs.

### Output format (JSON)

Return a single JSON object with these keys:

* `revised_query_text`: string – the new natural-language query (human-readable).
* `must_have_tokens`: string[] – words/phrases to add to the query to anchor embeddings.
* `negative_tokens`: string[] – words/phrases to add as negatives (or to the NL as “exclude …”).
* `include_categories`: string[] – categories to include (names as used by catalogue, `&`→`and` when URL-encoding).
* `exclude_categories`: string[] – categories to exclude.
* `price_band`: string – the budget to state in-query (e.g., “under $20” or “$20–$60”).
* `audience`: string – e.g., “Adults”.
* `rationale`: string – brief explanation of what was wrong and what you fixed.
* `confidence`: 0–1 – how confident you are the fix will yield 2/3 good results.
* `example_titles_expected`: string[] – 3–6 archetypes that should appear if the fix works.

Ensure the **query text** is natural (no operators needed), and that tokens/categories align with the rationale.


# USER INPUT (you’ll paste this block each run)

```
{
  "original_query": "gifts for the tech-savvy innovator who loves gadgets",
  "constraints": {
    "budget": "$100+",
    "audience": "Adults",
    "occasion": ""
  },
  "whitelist_categories": [
    "Craft Supplies",
    "Artistry",
    "Jewellery Making",
    "Jewellery",
    "Hair Accessories",
    "Yarn and Haberdashery",
    "Stationery",
    "Notebooks and Journals",
    "Drawing and Colouring",
    "Electronics",
    "Gadgets",
    "Tech",
    "Gaming",
    "Cameras",
    "Toys",
    "Board Games and Puzzles"
  ],
  "blocklist_categories": [
    "Beauty",
    "Skincare",
    "Bath and Body",
    "Hand Care",
    "Perfumes and Fragrances",
    "Cards",
    "Gift Bags",
    "Party Favours and Glow",
    "Chocolate",
    "Lollies and Candies",
    "Kids Art, Craft and Stationery",
    "Novelty Confectionery"
  ],
  "results_json": {
    "response": {
      "result_sources": {
        "token_match": {
          "count": 0
        },
        "embeddings_match": {
          "count": 100
        }
      },
      "facets": [
        {
          "display_name": "Product Type",
          "name": "Product Type",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 3,
              "display_name": "Laptop Stand",
              "value": "Laptop Stand",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Gaming Keyboard",
              "value": "Gaming Keyboard",
              "data": {}
            },
            {
              "status": "",
              "count": 12,
              "display_name": "Bluetooth Speaker",
              "value": "Bluetooth Speaker",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Wireless Charger",
              "value": "Wireless Charger",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
              "display_name": "Portable Charger",
              "value": "Portable Charger",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Light Up Speaker",
              "value": "Light Up Speaker",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Wireless Keyboard",
              "value": "Wireless Keyboard",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Replacement filters",
              "value": "Replacement filters",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Keyboard & Mouse Combo",
              "value": "Keyboard & Mouse Combo",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Watches",
              "value": "Watches",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Mini Speaker",
              "value": "Mini Speaker",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Wireless Earphones & Earbuds",
              "value": "Wireless Earphones & Earbuds",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Alarm Clock",
              "value": "Alarm Clock",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Massages",
              "value": "Massages",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Gaming Headset",
              "value": "Gaming Headset",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Gaming Microphone",
              "value": "Gaming Microphone",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lamps",
              "value": "Lamps",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Phone Stand",
              "value": "Phone Stand",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Tripods",
              "value": "Tripods",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "USB & Hard Drives",
              "value": "USB & Hard Drives",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Bluetooth Headphones & Earphones",
              "value": "Bluetooth Headphones & Earphones",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Wireless Charging Pad",
              "value": "Wireless Charging Pad",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Coffee Machines & Makers",
              "value": "Coffee Machines & Makers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Ipad Case",
              "value": "Ipad Case",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pretend Play & Dress Ups",
              "value": "Pretend Play & Dress Ups",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Category",
          "name": "Category",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Computer & Laptop Accessories",
              "value": "Computer & Laptop Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 10,
              "display_name": "Keyboard & Mouse",
              "value": "Keyboard & Mouse",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Computer Accessories",
              "value": "Computer Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 14,
              "display_name": "Portable Speakers",
              "value": "Portable Speakers",
              "data": {}
            },
            {
              "status": "",
              "count": 15,
              "display_name": "Accessories",
              "value": "Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Home Audio",
              "value": "Home Audio",
              "data": {}
            },
            {
              "status": "",
              "count": 13,
              "display_name": "Portable Chargers",
              "value": "Portable Chargers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Car Accessories",
              "value": "Car Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Camera Accessories",
              "value": "Camera Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Exercise & Fitness",
              "value": "Exercise & Fitness",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Air Purifiers",
              "value": "Air Purifiers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Fitness Trackers & Smart Watches",
              "value": "Fitness Trackers & Smart Watches",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Earphones",
              "value": "Earphones",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Radios & Alarm Clocks",
              "value": "Radios & Alarm Clocks",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Mens Grooming",
              "value": "Mens Grooming",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Headphones & Sound",
              "value": "Headphones & Sound",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Phone Cases & Covers",
              "value": "Phone Cases & Covers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Action Figures",
              "value": "Action Figures",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Impulse & Novelty Toys",
              "value": "Impulse & Novelty Toys",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lighting",
              "value": "Lighting",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Selfie Lights & Sticks",
              "value": "Selfie Lights & Sticks",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Data Storage & Hard Drives",
              "value": "Data Storage & Hard Drives",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Car Phone Charging",
              "value": "Car Phone Charging",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Headphones",
              "value": "Headphones",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Chargers",
              "value": "Chargers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Tea & Coffee",
              "value": "Tea & Coffee",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Ipad Cases",
              "value": "Ipad Cases",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pretend Play & Dress Up",
              "value": "Pretend Play & Dress Up",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Interactive Toys",
              "value": "Interactive Toys",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Vehicles & Remote Control",
              "value": "Vehicles & Remote Control",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Subcategory",
          "name": "Subcategory",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 12,
              "display_name": "Watches",
              "value": "Watches",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Fitness Tech",
              "value": "Fitness Tech",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Personal Care Appliances",
              "value": "Personal Care Appliances",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Figurines & Playsets",
              "value": "Figurines & Playsets",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Jewellery",
              "value": "Jewellery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Boxing",
              "value": "Boxing",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pretend Play Sets",
              "value": "Pretend Play Sets",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Planes, Helicopters and Drones",
              "value": "Planes, Helicopters and Drones",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Price",
          "name": "Price",
          "type": "multiple",
          "hidden": false,
          "data": {},
          "options": [
            {
              "status": "",
              "count": 10,
              "display_name": "$5 and less",
              "value": "\"-inf\"-\"5\"",
              "data": {},
              "range": [
                "-inf",
                5
              ]
            },
            {
              "status": "",
              "count": 32,
              "display_name": "$5 - $10",
              "value": "\"5\"-\"10\"",
              "data": {},
              "range": [
                5,
                10
              ]
            },
            {
              "status": "",
              "count": 35,
              "display_name": "$10 - $20",
              "value": "\"10\"-\"20\"",
              "data": {},
              "range": [
                10,
                20
              ]
            },
            {
              "status": "",
              "count": 19,
              "display_name": "$20 - $30",
              "value": "\"20\"-\"30\"",
              "data": {},
              "range": [
                20,
                30
              ]
            },
            {
              "status": "",
              "count": 19,
              "display_name": "$30 - $50",
              "value": "\"30\"-\"50\"",
              "data": {},
              "range": [
                30,
                50
              ]
            },
            {
              "status": "",
              "count": 4,
              "display_name": "$50 - $100",
              "value": "\"50\"-\"100\"",
              "data": {},
              "range": [
                50,
                100
              ]
            }
          ]
        },
        {
          "display_name": "Colour",
          "name": "Colour",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 41,
              "display_name": "Black",
              "value": "Black",
              "data": {}
            },
            {
              "status": "",
              "count": 31,
              "display_name": "Multi",
              "value": "Multi",
              "data": {}
            },
            {
              "status": "",
              "count": 14,
              "display_name": "White",
              "value": "White",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Purple",
              "value": "Purple",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Pink",
              "value": "Pink",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Green",
              "value": "Green",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Silver",
              "value": "Silver",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Brown",
              "value": "Brown",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Blue",
              "value": "Blue",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Gold",
              "value": "Gold",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Grey",
              "value": "Grey",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Batteries Included",
          "name": "Batteries Included",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 41,
              "display_name": "Yes",
              "value": "Yes",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "No",
              "value": "No",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Features",
          "name": "Features",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 3,
              "display_name": "Built-in microphone with hands free function",
              "value": "Built-in microphone with hands free function",
              "data": {}
            },
            {
              "status": "",
              "count": 12,
              "display_name": "Wireless",
              "value": "Wireless",
              "data": {}
            },
            {
              "status": "",
              "count": 11,
              "display_name": "USB powered",
              "value": "USB powered",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Rechargeable",
              "value": "Rechargeable",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Auxiliary input",
              "value": "Auxiliary input",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Portable",
              "value": "Portable",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Bluetooth",
              "value": "Bluetooth",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Universal",
              "value": "Universal",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "In-built Timer",
              "value": "In-built Timer",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Digital display",
              "value": "Digital display",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Over ear",
              "value": "Over ear",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Compatibility",
          "name": "Compatibility",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 18,
              "display_name": "Bluetooth",
              "value": "Bluetooth",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Smartphone",
              "value": "Smartphone",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "iPhone",
              "value": "iPhone",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Universal",
              "value": "Universal",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "iPad",
              "value": "iPad",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Battery Type",
          "name": "Battery Type",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 31,
              "display_name": "Rechargeable",
              "value": "Rechargeable",
              "data": {}
            },
            {
              "status": "",
              "count": 9,
              "display_name": "Button Cell",
              "value": "Button Cell",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "AA & AAA",
              "value": "AA & AAA",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Rechargable",
              "value": "Rechargable",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "AAA",
              "value": "AAA",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Gender",
          "name": "Gender",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 4,
              "display_name": "Men",
              "value": "Men",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Women",
              "value": "Women",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Suitable for ages",
          "name": "Suitable for ages",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 4,
              "display_name": "5+ Years",
              "value": "5+ Years",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "8+ Years",
              "value": "8+ Years",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Watch Type",
          "name": "Watch Type",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 2,
              "display_name": "Digital",
              "value": "Digital",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Analogue",
              "value": "Analogue",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Battery Required",
          "name": "Battery Required",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 47,
              "display_name": "Yes",
              "value": "Yes",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Brand",
          "name": "Brand",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Anko",
              "value": "Anko",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Verbatim",
              "value": "Verbatim",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Size",
          "name": "Size",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 100,
              "display_name": "/One Size ",
              "value": "One Size Fits All",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Weight",
          "name": "Weight",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "1 - 5kg",
              "value": "1 - 5kg",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Power Rating",
          "name": "Power Rating",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "10 to 100W",
              "value": "10 to 100W",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        }
      ],
      "groups": [
        {
          "group_id": "all",
          "display_name": "All",
          "count": 100,
          "data": {},
          "children": [
            {
              "group_id": "575e0dc3e4b24d90d2a216d4dc5d0f09",
              "display_name": "Tech",
              "count": 77,
              "data": {
                "url": "/tech/",
                "sequence": 16000,
                "isSpecial": false,
                "identifier": "Tech",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "575e0dc3e4b24d90d2a216d4dc5d0f09"
                ],
                "defaultCategory": false
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "4e21b615a67e9e9ad13a030628bb904c",
              "display_name": "Back To School",
              "count": 50,
              "data": {
                "url": "/back-to-school/inactive/",
                "sequence": 7000,
                "isSpecial": false,
                "identifier": "Back To School",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "4e21b615a67e9e9ad13a030628bb904c"
                ],
                "defaultCategory": false
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "dddaa894234df841cfb678463562e055",
              "display_name": "Home & Living",
              "count": 39,
              "data": {
                "url": "/home-and-living/",
                "sequence": 9000,
                "isSpecial": false,
                "identifier": "Home & Living",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "dddaa894234df841cfb678463562e055"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "faaad9343dac03b28bb32e4b4156a604",
              "display_name": "Clearance",
              "count": 30,
              "data": {
                "url": "/inactive/",
                "sequence": 28000,
                "isSpecial": false,
                "identifier": "Clearance",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "faaad9343dac03b28bb32e4b4156a604"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "89abe35cb1ad766f11a28c598fd37ba1",
              "display_name": "Gifting",
              "count": 30,
              "data": {
                "url": "/gifting/",
                "sequence": 26625,
                "isSpecial": false,
                "identifier": "Gifting",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "89abe35cb1ad766f11a28c598fd37ba1"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "bbbcb4ecce212f38c5dcfefbb03a8533",
              "display_name": "Mens",
              "count": 17,
              "data": {
                "url": "/mens/",
                "sequence": 11000,
                "isSpecial": false,
                "identifier": "Men",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "bbbcb4ecce212f38c5dcfefbb03a8533"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "81b616fbff55b8698d44852f45c08630",
              "display_name": "Christmas",
              "count": 17,
              "data": {
                "url": "/christmas/inactive/",
                "sequence": 3000,
                "isSpecial": false,
                "identifier": "Christmas",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "81b616fbff55b8698d44852f45c08630"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "6095b2832f08bb7ca1c60ffc1b2d091b",
              "display_name": "Kids & Baby",
              "count": 3,
              "data": {
                "url": "/kids/",
                "sequence": 12000,
                "isSpecial": false,
                "identifier": "Kids & Baby",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "6095b2832f08bb7ca1c60ffc1b2d091b"
                ],
                "defaultCategory": false
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "b133ad579435cfc931fc4843bcf0256d",
              "display_name": "Womens",
              "count": 11,
              "data": {
                "url": "/womens/",
                "sequence": 10000,
                "isSpecial": false,
                "identifier": "Women",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "b133ad579435cfc931fc4843bcf0256d"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "7cf41d86ecf7aa81d484569f48779de1",
              "display_name": "Online Exclusives",
              "count": 1,
              "data": {
                "url": "/category/online-exclusives/",
                "sequence": 26500,
                "isSpecial": false,
                "identifier": "Online Exclusives",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "7cf41d86ecf7aa81d484569f48779de1"
                ],
                "defaultCategory": false
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "7a7f3a70f71ac2372ae60e431b8236bb",
              "display_name": "Beauty",
              "count": 1,
              "data": {
                "url": "/beauty/",
                "sequence": 14000,
                "isSpecial": false,
                "identifier": "Beauty",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "7a7f3a70f71ac2372ae60e431b8236bb"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "66d0af2d5da0109dc2aae67829f7d4d4",
              "display_name": "Toys",
              "count": 6,
              "data": {
                "url": "/toys/",
                "sequence": 13000,
                "isSpecial": false,
                "identifier": "Toys",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "66d0af2d5da0109dc2aae67829f7d4d4"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "ce059e196a9104cd5e29f3295a32e737",
              "display_name": "Mother's Day",
              "count": 5,
              "data": {
                "url": "/mothers-day/inactive/",
                "sequence": 8000,
                "isSpecial": false,
                "identifier": "Mothers Day",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "ce059e196a9104cd5e29f3295a32e737"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            },
            {
              "group_id": "2d95e1e17abc6c9afb85088671f65e3a",
              "display_name": "Sport & Outdoor",
              "count": 1,
              "data": {
                "url": "/sport-and-outdoor/",
                "sequence": 15000,
                "isSpecial": false,
                "identifier": "Sport & Outdoor",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "2d95e1e17abc6c9afb85088671f65e3a"
                ],
                "defaultCategory": true
              },
              "children": [],
              "parents": [
                {
                  "display_name": "All",
                  "group_id": "all"
                }
              ]
            }
          ],
          "parents": []
        }
      ],
      "results": [
        {
          "matched_terms": [],
          "labels": {
            "__cnstrc_is_global_bestseller": {
              "display_name": "is_global_bestseller",
              "value": null
            }
          },
          "data": {
            "id": "P_42872535",
            "uri": "/product/adjustable-laptop-stand-42872535/",
            "url": "/product/adjustable-laptop-stand-42872535/",
            "video": {},
            "badges": [],
            "altImages": [
              "3823879f-1aac-4e41-af6c-20ee956b366a/42872535-2",
              "01734427-afcc-4af4-b80e-3ca7c0ff781c/42872535-3",
              "8c0a27d8-6ac0-4f0c-b879-a24a5845064b/42872535-4",
              "9079e92f-49dc-4eac-87ad-6650a5e3e9c9/42872535-5",
              "e0c5a8a2-5f8b-4eb0-9eb5-b8fc6927096c/42872535-6",
              "58955962-a963-4111-9cf8-49e4c36c4f83/42872535-7",
              "1462c63f-1ad1-4c9f-8f84-a2eb06a421de/42872535-8"
            ],
            "image_url": "https://assets.kmart.com.au/transform/dbbb2f1e-c305-405d-946f-bf3000fc8c79/42872535-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 75,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "719e3736907bc4d5a30b7156c0b39316",
            "nationalInventory": false,
            "ratings": {
              "averageScore": 4.8,
              "totalReviews": 152
            },
            "group_ids": [
              "038f22a6ca7d5a8ad4f8be406ac2bc8c",
              "a63efe3a46c380256f78e00ad72c8a57",
              "fcaf0586380f0f4acbff3c0ac6cbac8a",
              "fe3dd1772d04b24120dd753a403f2ccb",
              "11982398607b9b53d165e535828aa9f0",
              "719e3736907bc4d5a30b7156c0b39316"
            ],
            "apn": 9341107251621,
            "Size": "One Size",
            "price": 10,
            "prices": [
              {
                "type": "list",
                "amount": "10.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "1899-12-30"
              }
            ],
            "Colour": "Black",
            "clearance": false,
            "is_default": false,
            "variation_id": "42872535",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Black"
          },
          "value": "Adjustable Laptop Stand",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341107251621,
                "Size": "One Size",
                "price": 10,
                "prices": [
                  {
                    "type": "list",
                    "amount": "10.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "1899-12-30"
                  }
                ],
                "Colour": "Black",
                "altImages": [
                  "3823879f-1aac-4e41-af6c-20ee956b366a/42872535-2",
                  "01734427-afcc-4af4-b80e-3ca7c0ff781c/42872535-3",
                  "8c0a27d8-6ac0-4f0c-b879-a24a5845064b/42872535-4",
                  "9079e92f-49dc-4eac-87ad-6650a5e3e9c9/42872535-5",
                  "e0c5a8a2-5f8b-4eb0-9eb5-b8fc6927096c/42872535-6",
                  "58955962-a963-4111-9cf8-49e4c36c4f83/42872535-7",
                  "1462c63f-1ad1-4c9f-8f84-a2eb06a421de/42872535-8"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/dbbb2f1e-c305-405d-946f-bf3000fc8c79/42872535-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "variation_id": "42872535",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Black"
              },
              "value": "Adjustable Laptop Stand"
            }
          ]
        },
        {
          "matched_terms": [],
          "labels": {
            "__cnstrc_is_global_bestseller": {
              "display_name": "is_global_bestseller",
              "value": null
            }
          },
          "data": {
            "id": "P_43241521",
            "uri": "/product/laptop-stand-with-hub-and-phone-holder-43241521/",
            "url": "/product/laptop-stand-with-hub-and-phone-holder-43241521/",
            "video": {},
            "badges": [],
            "altImages": [
              "b81c3d67-aa15-471f-a4eb-688889045839/43241521-2",
              "3d2f80b4-b827-40a4-9094-b2b719a291aa/43241521-3",
              "293cb893-087e-448e-8028-c46aeda20d70/43241521-4",
              "69cad8be-1eef-448c-b750-dbecf3ded71a/43241521-5",
              "5ede66cd-ee72-410f-a386-69e5cbdd3353/43241521-6",
              "27e6d422-8f38-4f0a-9aec-dcd43861eaf3/43241521-7",
              "809dfd24-d061-4309-b74f-5e28f740cfa6/43241521-8",
              "216fa8e5-6697-4bdc-b413-9452656c0c3f/43241521-9",
              "4c64be0e-aade-4368-ac00-7ab6d04f3153/43241521-10",
              "c736f0ff-e32e-4ac2-8c6d-e8050bce18a2/43241521-11"
            ],
            "SavePrice": "WAS $22",
            "image_url": "https://assets.kmart.com.au/transform/4a61bdef-941a-457d-81b7-cb4dfee981cb/43241521-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 75,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "719e3736907bc4d5a30b7156c0b39316",
            "nationalInventory": false,
            "group_ids": [
              "b8cb612e944f2c324d92029f9221d851",
              "3dc32ab822eb350932d388e9848c5b5e",
              "0a36e8932a328cb602e747a46969a3d1",
              "a63efe3a46c380256f78e00ad72c8a57",
              "fe3dd1772d04b24120dd753a403f2ccb",
              "719e3736907bc4d5a30b7156c0b39316",
              "038f22a6ca7d5a8ad4f8be406ac2bc8c",
              "fcaf0586380f0f4acbff3c0ac6cbac8a",
              "11982398607b9b53d165e535828aa9f0"
            ],
            "apn": 9341109531530,
            "Size": "One Size",
            "price": 7.5,
            "prices": [
              {
                "type": "list",
                "amount": "7.50",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2025-08-12"
              }
            ],
            "Colour": "Black",
            "clearance": true,
            "is_default": false,
            "stateOOS": {
              "ACT": "6",
              "QLD": "6",
              "TAS": "6",
              "VIC": "6",
              "NSW": "6"
            },
            "variation_id": "43241521",
            "variant_video": {},
            "variant_badges": [
              "Clearance"
            ],
            "SecondaryColour": "Misc"
          },
          "value": "Laptop Stand with Hub and Phone Holder",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341109531530,
                "Size": "One Size",
                "price": 7.5,
                "prices": [
                  {
                    "type": "list",
                    "amount": "7.50",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2025-08-12"
                  }
                ],
                "Colour": "Black",
                "altImages": [
                  "b81c3d67-aa15-471f-a4eb-688889045839/43241521-2",
                  "3d2f80b4-b827-40a4-9094-b2b719a291aa/43241521-3",
                  "293cb893-087e-448e-8028-c46aeda20d70/43241521-4",
                  "69cad8be-1eef-448c-b750-dbecf3ded71a/43241521-5",
                  "5ede66cd-ee72-410f-a386-69e5cbdd3353/43241521-6",
                  "27e6d422-8f38-4f0a-9aec-dcd43861eaf3/43241521-7",
                  "809dfd24-d061-4309-b74f-5e28f740cfa6/43241521-8",
                  "216fa8e5-6697-4bdc-b413-9452656c0c3f/43241521-9",
                  "4c64be0e-aade-4368-ac00-7ab6d04f3153/43241521-10",
                  "c736f0ff-e32e-4ac2-8c6d-e8050bce18a2/43241521-11"
                ],
                "clearance": true,
                "image_url": "https://assets.kmart.com.au/transform/4a61bdef-941a-457d-81b7-cb4dfee981cb/43241521-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "stateOOS": {
                  "ACT": "6",
                  "QLD": "6",
                  "TAS": "6",
                  "VIC": "6",
                  "NSW": "6"
                },
                "variation_id": "43241521",
                "variant_video": {},
                "variant_badges": [
                  "Clearance"
                ],
                "SecondaryColour": "Misc"
              },
              "value": "Laptop Stand with Hub and Phone Holder"
            }
          ]
        },
        {
          "matched_terms": [],
          "labels": {
            "__cnstrc_is_global_bestseller": {
              "display_name": "is_global_bestseller",
              "value": null
            }
          },
          "data": {
            "id": "P_43099771",
            "url": "/product/mini-mechanical-gaming-keyboard-43099771/",
            "uri": "/product/mini-mechanical-gaming-keyboard-43099771/",
            "video": {},
            "badges": [],
            "image_url": "https://assets.kmart.com.au/transform/26174bac-f354-460e-8ae8-08701fb2f0b9/43099771-1?io=transform:extend,width:300,height:300",
            "altImages": [
              "ebfcf651-943b-40e8-a26b-e894d5abda0a/43099771-2",
              "11184320-2d75-45f3-8af5-3c3553bd6351/43099771-3",
              "5ebd2031-4989-48f2-a147-c3ea83db601f/43099771-4",
              "d5514998-a8fd-4362-b136-76a8b0acf5b2/43099771-5",
              "cfa0019d-be88-494f-b63b-65742aa22088/43099771-6",
              "2c341782-311d-4c60-b7ac-d03e4bb0989d/43099771-7",
              "ca19fa46-e217-4a06-b33f-688bd772c521/43099771-8",
              "ad682230-4d8b-4384-bc76-e1342d08c29e/43099771-9",
              "1577a7e9-8642-4e98-a6a0-8783c8ebd707/43099771-10"
            ],
            "FreeShipping": true,
            "MerchDepartment": 75,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FreeShippingMetro": true,
            "nationalInventory": false,
            "FulfilmentChannel": 3,
            "primaryCategoryId": "a49d5caa5ef0ec4fb13209766c690a68",
            "ratings": {
              "totalReviews": 14,
              "averageScore": 4.8
            },
            "group_ids": [
              "0b9b179ef96ea9b2c7c5f9730416fc1f",
              "c22d0f2beefcf05505a395fd838142ac",
              "acbbb25dfe0352676e90521d576e3d61",
              "bbc66c0be9e3b3b7aaef084bed915f15",
              "6e67fae3eb8cbe37468c7e08dcfe66a9",
              "f3245778f9e1eff6a72eaf02c06f91d7",
              "9eed85ad420e3a3c986cdc6d7e77854d",
              "4f0bf504bde96affac9e0b6f1d6bb288",
              "9b4d17f50ba40e12ca7f563c64e6d550",
              "a49d5caa5ef0ec4fb13209766c690a68",
              "4bf17a4a2ba5c0a22d3c95041ca1d98e"
            ],
            "apn": 9300800825362,
            "Size": "One Size",
            "price": 25,
            "prices": [
              {
                "type": "list",
                "amount": "25.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "1899-12-30"
              },
              {
                "type": "promo",
                "amount": "25.00",
                "country": "AU",
                "endDate": "2022-10-05",
                "currency": "AUD",
                "startDate": "2022-09-15"
              }
            ],
            "Colour": "Black",
            "clearance": false,
            "is_default": false,
            "variation_id": "43099771",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Black"
          },
          "value": "Mini Mechanical Gaming Keyboard",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9300800825362,
                "Size": "One Size",
                "price": 25,
                "prices": [
                  {
                    "type": "list",
                    "amount": "25.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "1899-12-30"
                  },
                  {
                    "type": "promo",
                    "amount": "25.00",
                    "country": "AU",
                    "endDate": "2022-10-05",
                    "currency": "AUD",
                    "startDate": "2022-09-15"
                  }
                ],
                "Colour": "Black",
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/26174bac-f354-460e-8ae8-08701fb2f0b9/43099771-1?io=transform:extend,width:300,height:300",
                "altImages": [
                  "ebfcf651-943b-40e8-a26b-e894d5abda0a/43099771-2",
                  "11184320-2d75-45f3-8af5-3c3553bd6351/43099771-3",
                  "5ebd2031-4989-48f2-a147-c3ea83db601f/43099771-4",
                  "d5514998-a8fd-4362-b136-76a8b0acf5b2/43099771-5",
                  "cfa0019d-be88-494f-b63b-65742aa22088/43099771-6",
                  "2c341782-311d-4c60-b7ac-d03e4bb0989d/43099771-7",
                  "ca19fa46-e217-4a06-b33f-688bd772c521/43099771-8",
                  "ad682230-4d8b-4384-bc76-e1342d08c29e/43099771-9",
                  "1577a7e9-8642-4e98-a6a0-8783c8ebd707/43099771-10"
                ],
                "is_default": false,
                "variation_id": "43099771",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Black"
              },
              "value": "Mini Mechanical Gaming Keyboard"
            }
          ]
        }
      ],
      "sort_options": [
        {
          "sort_by": "relevance",
          "display_name": "Popular",
          "sort_order": "descending",
          "status": "selected",
          "hidden": false
        },
        {
          "sort_by": "numberOfDaysSinceStartDate",
          "display_name": "New",
          "sort_order": "ascending",
          "status": "",
          "hidden": false
        },
        {
          "sort_by": "price",
          "display_name": "$",
          "sort_order": "ascending",
          "status": "",
          "hidden": false
        },
        {
          "sort_by": "price",
          "display_name": "$$$",
          "sort_order": "descending",
          "status": "",
          "hidden": false
        }
      ],
      "refined_content": [],
      "total_num_results": 100,
      "features": [
        {
          "feature_name": "a_a_test",
          "display_name": "a_a_test",
          "enabled": true,
          "variant": null
        },
        {
          "feature_name": "auto_generated_refined_query_rules",
          "display_name": "Affinity Engine",
          "enabled": true,
          "variant": {
            "name": "default_rules",
            "display_name": "Default weights"
          }
        },
        {
          "feature_name": "custom_autosuggest_ui",
          "display_name": "custom_autosuggest_ui",
          "enabled": true,
          "variant": {
            "name": "custom_autosuggest_ui_image_result_count",
            "display_name": "custom_autosuggest_ui_image_result_count"
          }
        },
        {
          "feature_name": "disable_test_only_global_rules_browse",
          "display_name": "Disables global refined filter rules with include_in_test=1 column",
          "enabled": false,
          "variant": null
        },
        {
          "feature_name": "disable_test_only_global_rules_search",
          "display_name": "Disables global refined query rules with include_in_test=1 column",
          "enabled": false,
          "variant": null
        },
        {
          "feature_name": "filter_items",
          "display_name": "Filter-item boosts",
          "enabled": true,
          "variant": {
            "name": "filter_items_w_atcs_and_purchases",
            "display_name": ""
          }
        },
        {
          "feature_name": "manual_searchandizing",
          "display_name": "Searchandizing",
          "enabled": true,
          "variant": null
        },
        {
          "feature_name": "personalization",
          "display_name": "Personalization",
          "enabled": true,
          "variant": {
            "name": "default_personalization",
            "display_name": "Default Personalization"
          }
        },
        {
          "feature_name": "query_items",
          "display_name": "Learn To Rank",
          "enabled": true,
          "variant": {
            "name": "query_items_ctr_and_l2r",
            "display_name": "CTR & LTR"
          }
        },
        {
          "feature_name": "use_enriched_attributes_as_fuzzy_searchable",
          "display_name": "use_enriched_attributes_as_fuzzy_searchable",
          "enabled": false,
          "variant": null
        },
        {
          "feature_name": "use_reranker_service_for_all",
          "display_name": "[DEPRECATED] Use reranker service to rerank search and browse results",
          "enabled": false,
          "variant": null
        },
        {
          "feature_name": "use_reranker_service_for_browse",
          "display_name": "Use reranker service to rerank browse / collections results",
          "enabled": true,
          "variant": {
            "name": "browse_reranker_v0_top100",
            "display_name": "browse_reranker_v0_top100"
          }
        },
        {
          "feature_name": "use_reranker_service_for_search",
          "display_name": "Use reranker service to rerank search results",
          "enabled": true,
          "variant": {
            "name": "search_reranker_v0_top100",
            "display_name": "search_reranker_v0_top100"
          }
        }
      ],
      "related_searches": [],
      "related_browse_pages": []
    },
    "result_id": "95245454-24e5-4d4f-b6b7-d012003d7f5f",
    "request": {
      "sort_by": "relevance",
      "sort_order": "descending",
      "num_results_per_page": 3,
      "filters": {},
      "original_query": "gifts for the tech-savvy innovator who loves gadgets",
      "term": "gifts tech savvy innovator loves gadgets",
      "page": 1,
      "fmt_options": {
        "groups_start": "current",
        "groups_max_depth": 1,
        "show_hidden_facets": false,
        "show_hidden_fields": false,
        "show_protected_facets": false
      },
      "section": "Products",
      "features": {
        "query_items": true,
        "a_a_test": true,
        "auto_generated_refined_query_rules": true,
        "manual_searchandizing": true,
        "personalization": true,
        "filter_items": true,
        "use_reranker_service_for_search": true,
        "use_reranker_service_for_browse": true,
        "use_reranker_service_for_all": false,
        "custom_autosuggest_ui": true,
        "disable_test_only_global_rules_search": false,
        "disable_test_only_global_rules_browse": false,
        "use_enriched_attributes_as_fuzzy_searchable": false
      },
      "feature_variants": {
        "query_items": "query_items_ctr_and_l2r",
        "a_a_test": null,
        "auto_generated_refined_query_rules": "default_rules",
        "manual_searchandizing": null,
        "personalization": "default_personalization",
        "filter_items": "filter_items_w_atcs_and_purchases",
        "use_reranker_service_for_search": "search_reranker_v0_top100",
        "use_reranker_service_for_browse": "browse_reranker_v0_top100",
        "use_reranker_service_for_all": null,
        "custom_autosuggest_ui": "custom_autosuggest_ui_image_result_count",
        "disable_test_only_global_rules_search": null,
        "disable_test_only_global_rules_browse": null,
        "use_enriched_attributes_as_fuzzy_searchable": null
      },
      "searchandized_items": {}
    }
  }
}
```
