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
  "original_query": "gift for a culinary artist who loves creating memorable meals",
  "constraints": {
    "budget": "$50+",
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
              "count": 8,
              "display_name": "Gadgets",
              "value": "Gadgets",
              "data": {}
            },
            {
              "status": "",
              "count": 8,
              "display_name": "Air Fryers",
              "value": "Air Fryers",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Knives & Blocks",
              "value": "Knives & Blocks",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Chopping Boards",
              "value": "Chopping Boards",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
              "display_name": "Food Processors & Mixers",
              "value": "Food Processors & Mixers",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Electric Cooking",
              "value": "Electric Cooking",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
              "display_name": "Juicers & Blenders",
              "value": "Juicers & Blenders",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Stationery",
              "value": "Stationery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Crafting Objects",
              "value": "Crafting Objects",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Fridge Storage",
              "value": "Fridge Storage",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Frypans & Woks",
              "value": "Frypans & Woks",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Artistry Accessories",
              "value": "Artistry Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Food Storage Containers",
              "value": "Food Storage Containers",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Steamers & Rice Cookers",
              "value": "Steamers & Rice Cookers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Notebooks",
              "value": "Notebooks",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Toasters",
              "value": "Toasters",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Sandwich Makers",
              "value": "Sandwich Makers",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Pantry Storage",
              "value": "Pantry Storage",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pinata",
              "value": "Pinata",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Table Accessories",
              "value": "Table Accessories",
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
              "count": 8,
              "display_name": "Utensils & Gadgets",
              "value": "Utensils & Gadgets",
              "data": {}
            },
            {
              "status": "",
              "count": 36,
              "display_name": "Kitchen Appliances",
              "value": "Kitchen Appliances",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Blocks & Construction",
              "value": "Blocks & Construction",
              "data": {}
            },
            {
              "status": "",
              "count": 9,
              "display_name": "Food Preparation",
              "value": "Food Preparation",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Stationery & Office Supplies",
              "value": "Stationery & Office Supplies",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Craft Supplies",
              "value": "Craft Supplies",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Kitchen Storage",
              "value": "Kitchen Storage",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Cookware",
              "value": "Cookware",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Artistry",
              "value": "Artistry",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Notebooks & Journals",
              "value": "Notebooks & Journals",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Kids Art, Craft & Stationery",
              "value": "Kids Art, Craft & Stationery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Baby",
              "value": "Baby",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pinatas",
              "value": "Pinatas",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Table Decor",
              "value": "Table Decor",
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
              "count": 2,
              "display_name": "Construction",
              "value": "Construction",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Drawing & Colouring",
              "value": "Drawing & Colouring",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Figurines & Playsets",
              "value": "Figurines & Playsets",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Feeding & Nursing",
              "value": "Feeding & Nursing",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Crafting",
              "value": "Crafting",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Craft, Sand, Dough",
              "value": "Craft, Sand, Dough",
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
              "count": 20,
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
              "count": 30,
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
              "count": 29,
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
              "count": 16,
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
              "count": 12,
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
              "count": 11,
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
              "count": 4,
              "display_name": "Yellow",
              "value": "Yellow",
              "data": {}
            },
            {
              "status": "",
              "count": 17,
              "display_name": "White",
              "value": "White",
              "data": {}
            },
            {
              "status": "",
              "count": 40,
              "display_name": "Multi",
              "value": "Multi",
              "data": {}
            },
            {
              "status": "",
              "count": 13,
              "display_name": "Black",
              "value": "Black",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Green",
              "value": "Green",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Clear",
              "value": "Clear",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Silver",
              "value": "Silver",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Grey",
              "value": "Grey",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Orange",
              "value": "Orange",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Metallic",
              "value": "Metallic",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Red",
              "value": "Red",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Blue",
              "value": "Blue",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Book Genre",
          "name": "Book Genre",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 21,
              "display_name": "Cooking",
              "value": "Cooking",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Health and Wellbeing",
              "value": "Health and Wellbeing",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Material",
          "name": "Material",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 11,
              "display_name": "Stainless Steel",
              "value": "Stainless Steel",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Polypropylene",
              "value": "Polypropylene",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Plastic",
              "value": "Plastic",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Silicone",
              "value": "Silicone",
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
              "count": 2,
              "display_name": "Overheat Protection",
              "value": "Overheat Protection",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "In-built Timer",
              "value": "In-built Timer",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "On/Off Indicator",
              "value": "On/Off Indicator",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "BPA Free",
              "value": "BPA Free",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Digital display",
              "value": "Digital display",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Variable Temperature Control",
              "value": "Variable Temperature Control",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Variable Speed Setting",
              "value": "Variable Speed Setting",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Cook and Keep Warm Setting",
              "value": "Cook and Keep Warm Setting",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Audience",
          "name": "Audience",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 22,
              "display_name": "Adults",
              "value": "Adults",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Capacity",
          "name": "Capacity",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 6,
              "display_name": "0 - 5 L",
              "value": "0 - 5 L",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "5 - 10 L",
              "value": "5 - 10 L",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "10 - 20 L",
              "value": "10 - 20 L",
              "data": {}
            },
            {
              "status": "",
              "count": 13,
              "display_name": "1 - 5 L",
              "value": "1 - 5 L",
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
            },
            {
              "status": "",
              "count": 13,
              "display_name": "100 to 500W",
              "value": "100 to 500W",
              "data": {}
            },
            {
              "status": "",
              "count": 9,
              "display_name": "500 to 1000W",
              "value": "500 to 1000W",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "1000 to 1500W",
              "value": "1000 to 1500W",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "1500 to 2000W",
              "value": "1500 to 2000W",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "2000 to 2500W",
              "value": "2000 to 2500W",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Author",
          "name": "Author",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 3,
              "display_name": "HERRON",
              "value": "HERRON",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "DONNA HAY",
              "value": "DONNA HAY",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "NAGI MAEHASHI",
              "value": "NAGI MAEHASHI",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Dishwasher Safe",
          "name": "Dishwasher Safe",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 4,
              "display_name": "No",
              "value": "No",
              "data": {}
            },
            {
              "status": "",
              "count": 8,
              "display_name": "Yes",
              "value": "Yes",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Microwave Safe",
          "name": "Microwave Safe",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 3,
              "display_name": "No",
              "value": "No",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Yes",
              "value": "Yes",
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
          "display_name": "Suitable for ages",
          "name": "Suitable for ages",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 8,
              "display_name": "5+ Years",
              "value": "5+ Years",
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
              "display_name": "Harry Potter",
              "value": "Harry Potter",
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
              "group_id": "dddaa894234df841cfb678463562e055",
              "display_name": "Home & Living",
              "count": 90,
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
              "count": 25,
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
              "group_id": "66d0af2d5da0109dc2aae67829f7d4d4",
              "display_name": "Toys",
              "count": 9,
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
              "group_id": "81b616fbff55b8698d44852f45c08630",
              "display_name": "Christmas",
              "count": 13,
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
              "group_id": "89abe35cb1ad766f11a28c598fd37ba1",
              "display_name": "Gifting",
              "count": 9,
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
              "group_id": "4e21b615a67e9e9ad13a030628bb904c",
              "display_name": "Back To School",
              "count": 7,
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
              "group_id": "b133ad579435cfc931fc4843bcf0256d",
              "display_name": "Womens",
              "count": 4,
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
              "group_id": "e82df739dd8c84c8ae105b514f4c10df",
              "display_name": "Easter",
              "count": 2,
              "data": {
                "url": "/easter/inactive/",
                "sequence": 1000,
                "isSpecial": false,
                "identifier": "Easter",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "e82df739dd8c84c8ae105b514f4c10df"
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
              "group_id": "3994fedf071695a6e3324b82401f924d",
              "display_name": "Kmart Inspired",
              "count": 1,
              "data": {
                "url": "/kmart-inspired/",
                "sequence": 26750,
                "isSpecial": false,
                "identifier": "Kmart Inspired",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "3994fedf071695a6e3324b82401f924d"
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
              "group_id": "bbbcb4ecce212f38c5dcfefbb03a8533",
              "display_name": "Mens",
              "count": 3,
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
              "group_id": "575e0dc3e4b24d90d2a216d4dc5d0f09",
              "display_name": "Tech",
              "count": 1,
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
              "group_id": "6095b2832f08bb7ca1c60ffc1b2d091b",
              "display_name": "Kids & Baby",
              "count": 1,
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
            }
          ],
          "parents": []
        }
      ],
      "results": [
        {
          "matched_terms": [],
          "labels": {
            "__cnstrc_is_new_arrivals": {
              "display_name": "is_new_arrivals",
              "value": null
            },
            "__cnstrc_is_global_bestseller": {
              "display_name": "is_global_bestseller",
              "value": null
            }
          },
          "data": {
            "id": "P_43615773",
            "uri": "/product/lemon-juicer-43615773/",
            "url": "/product/lemon-juicer-43615773/",
            "video": {},
            "badges": [],
            "altImages": [
              "bebba9a2-81e8-438f-bd05-c53623cb393f/43615773-2",
              "fa5f6f80-dce0-4c8c-87fe-76f1b87207b2/43615773-3"
            ],
            "image_url": "https://assets.kmart.com.au/transform/33892f04-67bd-4512-bbfe-e22bae1ec486/43615773-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 38,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "7cff7b708e2fa5f3e741767424d24045",
            "nationalInventory": false,
            "ratings": {
              "averageScore": 0,
              "totalReviews": 0
            },
            "group_ids": [
              "53d76faea2dd804d5d534c80ff5bdca9",
              "3f5ad6e657621ebe3bceda3dd4271e63",
              "c579bbc252ed7a06ababd064365a3d01",
              "ee65fed9146c40cbc0eb68d418c75e35",
              "fac0e533fcea70cda9cc5d0ec6a3397c",
              "b97cb6f72c79534d26214b3f6c3f5d15",
              "7cff7b708e2fa5f3e741767424d24045"
            ],
            "apn": 9341111452458,
            "Size": "One Size",
            "price": 6,
            "prices": [
              {
                "type": "list",
                "amount": "6.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "1899-12-30"
              }
            ],
            "Colour": "Yellow",
            "clearance": false,
            "is_default": false,
            "stateOOS": {
              "NT": "6",
              "ACT": "6"
            },
            "variation_id": "43615773",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Yellow"
          },
          "value": "Lemon Juicer",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341111452458,
                "Size": "One Size",
                "price": 6,
                "prices": [
                  {
                    "type": "list",
                    "amount": "6.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "1899-12-30"
                  }
                ],
                "Colour": "Yellow",
                "altImages": [
                  "bebba9a2-81e8-438f-bd05-c53623cb393f/43615773-2",
                  "fa5f6f80-dce0-4c8c-87fe-76f1b87207b2/43615773-3"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/33892f04-67bd-4512-bbfe-e22bae1ec486/43615773-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "stateOOS": {
                  "NT": "6",
                  "ACT": "6"
                },
                "variation_id": "43615773",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Yellow"
              },
              "value": "Lemon Juicer"
            }
          ]
        },
        {
          "matched_terms": [],
          "labels": {
            "__cnstrc_is_new_arrivals": {
              "display_name": "is_new_arrivals",
              "value": null
            }
          },
          "data": {
            "id": "P_43533725",
            "uri": "/product/7.5l-air-fryer-43533725/",
            "url": "/product/7.5l-air-fryer-43533725/",
            "video": {},
            "badges": [
              "JustLanded"
            ],
            "altImages": [
              "da87249f-afc5-428b-ab51-f515d620ab4c/43533725-2",
              "487d1eb0-8d5d-497f-a422-aee315d4c9b0/43533725-3",
              "028e88b2-5147-42e8-8cf6-5f938cf68146/43533725-4",
              "73079d45-8544-4f38-8c51-db1521f4cb90/43533725-5",
              "da240277-c4cb-460b-ae3e-2accf577e85b/43533725-6",
              "e59c93e5-c599-4a57-bb73-1a06ba3bc437/43533725-7",
              "88f736dd-4c0e-4cc3-af1e-c7bd41d0cc8c/43533725-8"
            ],
            "image_url": "https://assets.kmart.com.au/transform/2ec18690-ba4d-4bfa-a2cb-fe6c8293ec46/43533725-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 56,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "9f414d14733d7e230124c43f77cccb9d",
            "nationalInventory": false,
            "ratings": {
              "averageScore": 0,
              "totalReviews": 0
            },
            "group_ids": [
              "2a73fd861e869c3907d82be827d495ad",
              "4c965bb661453a317ae88687574993f1",
              "ee65fed9146c40cbc0eb68d418c75e35",
              "fac0e533fcea70cda9cc5d0ec6a3397c",
              "186544a3e32b5c6a195df70748e9bf30",
              "9f414d14733d7e230124c43f77cccb9d",
              "53d76faea2dd804d5d534c80ff5bdca9",
              "c579bbc252ed7a06ababd064365a3d01"
            ],
            "apn": 9341111089449,
            "Size": "One Size",
            "price": 85,
            "prices": [
              {
                "type": "list",
                "amount": "85.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2025-05-19"
              }
            ],
            "Colour": "White",
            "clearance": false,
            "is_default": false,
            "stateOOS": {
              "ACT": "6"
            },
            "variation_id": "43533725",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "White"
          },
          "value": "7.5L Air Fryer",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341111089449,
                "Size": "One Size",
                "price": 85,
                "prices": [
                  {
                    "type": "list",
                    "amount": "85.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2025-05-19"
                  }
                ],
                "Colour": "White",
                "altImages": [
                  "da87249f-afc5-428b-ab51-f515d620ab4c/43533725-2",
                  "487d1eb0-8d5d-497f-a422-aee315d4c9b0/43533725-3",
                  "028e88b2-5147-42e8-8cf6-5f938cf68146/43533725-4",
                  "73079d45-8544-4f38-8c51-db1521f4cb90/43533725-5",
                  "da240277-c4cb-460b-ae3e-2accf577e85b/43533725-6",
                  "e59c93e5-c599-4a57-bb73-1a06ba3bc437/43533725-7",
                  "88f736dd-4c0e-4cc3-af1e-c7bd41d0cc8c/43533725-8"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/2ec18690-ba4d-4bfa-a2cb-fe6c8293ec46/43533725-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "stateOOS": {
                  "ACT": "6"
                },
                "variation_id": "43533725",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "White"
              },
              "value": "7.5L Air Fryer"
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
            "id": "P_43467327",
            "url": "/product/231-piece-mini-blocks-food-series:-candy-cake-43467327/",
            "uri": "/product/231-piece-mini-blocks-food-series:-candy-cake-43467327/",
            "video": {},
            "badges": [],
            "SavePrice": "WAS $15",
            "image_url": "https://assets.kmart.com.au/transform/7ee2354e-05df-434e-a870-47a85ce7b34a/43467327-1?io=transform:extend,width:300,height:300",
            "altImages": [
              "5093715b-b308-4ec9-a060-127562db12e1/43467327-2",
              "0d5c8b07-d5a7-4797-b38c-4c1423913715/43467327-3",
              "859bcec9-1db3-4f31-baeb-cde0e3cd0408/43467327-4",
              "064f4e3b-da40-4e2e-ab7a-aae67b247083/43467327-5",
              "0c018397-763b-4b1b-a30d-d72e86067e88/43467327-6"
            ],
            "FreeShipping": true,
            "MerchDepartment": 67,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FreeShippingMetro": true,
            "nationalInventory": false,
            "FulfilmentChannel": 3,
            "primaryCategoryId": "fd104bba4f28d18b8b30155ad269a0e8",
            "group_ids": [
              "fd104bba4f28d18b8b30155ad269a0e8",
              "9107867b288d4f17d62959fdfccd699c",
              "d58b8d70406633c2a45462ed332d2d91",
              "721ca04b4e803cea55c223569ed2f8ad",
              "4346d2ca431c657acb69049648295481",
              "3dc32ab822eb350932d388e9848c5b5e",
              "533c7dbe214575e4e49e9f33cc9dde67",
              "10deef1b85db5f8887949ef60211837c",
              "d41d2da886f225a0a442e282597a6355"
            ],
            "apn": 9341110748743,
            "Size": "One Size",
            "price": 12,
            "prices": [
              {
                "type": "list",
                "amount": "12.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2025-07-29"
              }
            ],
            "Colour": "Multi",
            "clearance": true,
            "is_default": false,
            "variation_id": "43467327",
            "variant_video": {},
            "variant_badges": [
              "Clearance"
            ],
            "SecondaryColour": "Assorted"
          },
          "value": "231 Piece Mini Blocks Food Series: Candy Cake",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341110748743,
                "Size": "One Size",
                "price": 12,
                "prices": [
                  {
                    "type": "list",
                    "amount": "12.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2025-07-29"
                  }
                ],
                "Colour": "Multi",
                "clearance": true,
                "image_url": "https://assets.kmart.com.au/transform/7ee2354e-05df-434e-a870-47a85ce7b34a/43467327-1?io=transform:extend,width:300,height:300",
                "altImages": [
                  "5093715b-b308-4ec9-a060-127562db12e1/43467327-2",
                  "0d5c8b07-d5a7-4797-b38c-4c1423913715/43467327-3",
                  "859bcec9-1db3-4f31-baeb-cde0e3cd0408/43467327-4",
                  "064f4e3b-da40-4e2e-ab7a-aae67b247083/43467327-5",
                  "0c018397-763b-4b1b-a30d-d72e86067e88/43467327-6"
                ],
                "is_default": false,
                "variation_id": "43467327",
                "variant_video": {},
                "variant_badges": [
                  "Clearance"
                ],
                "SecondaryColour": "Assorted"
              },
              "value": "231 Piece Mini Blocks Food Series: Candy Cake"
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
    "result_id": "01c4e539-ef4c-45af-8912-8de8794834d1",
    "request": {
      "sort_by": "relevance",
      "sort_order": "descending",
      "num_results_per_page": 3,
      "filters": {},
      "original_query": "gift for a culinary artist who loves creating memorable meals",
      "term": "gift culinary artist loves creating memorable meals",
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
