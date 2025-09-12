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
  "original_query": "curated gifts for a gourmet enthusiast who enjoys culinary explorations",
  "constraints": {
    "budget": "",
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
              "count": 6,
              "display_name": "Chocolate Gifts",
              "value": "Chocolate Gifts",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Electric Cooking",
              "value": "Electric Cooking",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Christmas Food",
              "value": "Christmas Food",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Lollies",
              "value": "Lollies",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Food Storage Containers",
              "value": "Food Storage Containers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pantry Storage",
              "value": "Pantry Storage",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Dessert & Food Stands",
              "value": "Dessert & Food Stands",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Serveware",
              "value": "Serveware",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Gadgets",
              "value": "Gadgets",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lunch Boxes",
              "value": "Lunch Boxes",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Tray",
              "value": "Tray",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Notepads",
              "value": "Notepads",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Snacks and Supplements",
              "value": "Snacks and Supplements",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Sketch Pads",
              "value": "Sketch Pads",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Napkins",
              "value": "Napkins",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Platters",
              "value": "Platters",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Food Processors & Mixers",
              "value": "Food Processors & Mixers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Necklaces",
              "value": "Necklaces",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Chocolate",
              "value": "Chocolate",
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
              "display_name": "Knives & Blocks",
              "value": "Knives & Blocks",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Cake Stands",
              "value": "Cake Stands",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Chopping Boards",
              "value": "Chopping Boards",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Clips",
              "value": "Clips",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Grazing Boards",
              "value": "Grazing Boards",
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
              "count": 7,
              "display_name": "Chocolate",
              "value": "Chocolate",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Kitchen Appliances",
              "value": "Kitchen Appliances",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Seasonal Confectionary",
              "value": "Seasonal Confectionary",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Lollies & Candies",
              "value": "Lollies & Candies",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Kitchen Storage",
              "value": "Kitchen Storage",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
              "display_name": "Party Serveware & Accessories",
              "value": "Party Serveware & Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Utensils & Gadgets",
              "value": "Utensils & Gadgets",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lunch & Drink",
              "value": "Lunch & Drink",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
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
              "count": 1,
              "display_name": "Healthy Snacking",
              "value": "Healthy Snacking",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Artistry",
              "value": "Artistry",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Party Napkins",
              "value": "Party Napkins",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Serveware",
              "value": "Serveware",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Accessories",
              "value": "Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Bars",
              "value": "Bars",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Candles & Home Fragrance",
              "value": "Candles & Home Fragrance",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Gift Boxes",
              "value": "Gift Boxes",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Board Games & Puzzles",
              "value": "Board Games & Puzzles",
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
              "count": 1,
              "display_name": "Jewellery",
              "value": "Jewellery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Hair Accessories",
              "value": "Hair Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Board Games",
              "value": "Board Games",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Colour",
          "name": "Colour",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 76,
              "display_name": "Multi",
              "value": "Multi",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Silver",
              "value": "Silver",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Clear",
              "value": "Clear",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "White",
              "value": "White",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Brown",
              "value": "Brown",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Black",
              "value": "Black",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Yellow",
              "value": "Yellow",
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
              "display_name": "Red",
              "value": "Red",
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
          "display_name": "Price",
          "name": "Price",
          "type": "multiple",
          "hidden": false,
          "data": {},
          "options": [
            {
              "status": "",
              "count": 19,
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
              "count": 23,
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
              "count": 33,
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
              "count": 25,
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
              "count": 6,
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
          "display_name": "Quantity",
          "name": "Quantity",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "0 - 50g",
              "value": "0 - 50g",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "50 - 100g",
              "value": "50 - 100g",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "100 - 200g",
              "value": "100 - 200g",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "200 - 300g",
              "value": "200 - 300g",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "300 - 400g",
              "value": "300 - 400g",
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
              "count": 45,
              "display_name": "Adults",
              "value": "Adults",
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
              "count": 3,
              "display_name": "100 to 500W",
              "value": "100 to 500W",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "500 to 1000W",
              "value": "500 to 1000W",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Pack Size",
          "name": "Pack Size",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 3,
              "display_name": "1 - 5 ",
              "value": "1 - 5",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "5 - 10",
              "value": "5 - 10",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "10 - 15",
              "value": "10 - 15",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "15 - 20",
              "value": "15 - 20",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "20 - 30",
              "value": "20 - 30",
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
              "count": 41,
              "display_name": "Cooking",
              "value": "Cooking",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Personal Finance",
              "value": "Personal Finance",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Reference",
              "value": "Reference",
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
          "display_name": "Author",
          "name": "Author",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "NAGI MAEHASHI",
              "value": "NAGI MAEHASHI",
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
              "count": 2,
              "display_name": "HERRON",
              "value": "HERRON",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "SCOTT PAPE",
              "value": "SCOTT PAPE",
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
              "count": 1,
              "display_name": "Digital display",
              "value": "Digital display",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "For Indoor/Outdoor Use",
              "value": "For Indoor/Outdoor Use",
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
              "count": 1,
              "display_name": "Acacia Wood",
              "value": "Acacia Wood",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Stainless Steel",
              "value": "Stainless Steel",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Paper",
              "value": "Paper",
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
              "count": 4,
              "display_name": "Ferrero Rocher",
              "value": "Ferrero Rocher",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Haribo",
              "value": "Haribo",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Harry Potter",
              "value": "Harry Potter",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lindt",
              "value": "Lindt",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Toblerone",
              "value": "Toblerone",
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
              "count": 3,
              "display_name": "Yes",
              "value": "Yes",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "No",
              "value": "No",
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
          "display_name": "Capacity",
          "name": "Capacity",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 5,
              "display_name": "1 - 5 L",
              "value": "1 - 5 L",
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
              "count": 2,
              "display_name": "Women",
              "value": "Women",
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
              "count": 1,
              "display_name": "Yes",
              "value": "Yes",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Fragrance",
          "name": "Fragrance",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Sweet",
              "value": "Sweet",
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
              "count": 1,
              "display_name": "8+ Years",
              "value": "8+ Years",
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
              "count": 95,
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
              "group_id": "ce059e196a9104cd5e29f3295a32e737",
              "display_name": "Mother's Day",
              "count": 26,
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
              "group_id": "81b616fbff55b8698d44852f45c08630",
              "display_name": "Christmas",
              "count": 19,
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
              "group_id": "bbbcb4ecce212f38c5dcfefbb03a8533",
              "display_name": "Mens",
              "count": 5,
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
              "group_id": "89abe35cb1ad766f11a28c598fd37ba1",
              "display_name": "Gifting",
              "count": 16,
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
              "group_id": "faaad9343dac03b28bb32e4b4156a604",
              "display_name": "Clearance",
              "count": 9,
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
              "group_id": "575e0dc3e4b24d90d2a216d4dc5d0f09",
              "display_name": "Tech",
              "count": 3,
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
              "group_id": "b133ad579435cfc931fc4843bcf0256d",
              "display_name": "Womens",
              "count": 7,
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
              "group_id": "4e21b615a67e9e9ad13a030628bb904c",
              "display_name": "Back To School",
              "count": 2,
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
              "group_id": "66d0af2d5da0109dc2aae67829f7d4d4",
              "display_name": "Toys",
              "count": 2,
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
            }
          },
          "data": {
            "id": "P_43663712",
            "uri": "/product/tiki-cocktails-by-shelly-slipsmith-book-43663712/",
            "url": "/product/tiki-cocktails-by-shelly-slipsmith-book-43663712/",
            "video": {},
            "badges": [
              "JustLanded"
            ],
            "image_url": "https://kmartau.mo.cloudinary.net/3516105e-3e26-420a-a60f-f787ac5a5a5f.jpg?tx=w_300,h_300,c_pad",
            "altImages": [],
            "FreeShipping": true,
            "MerchDepartment": 23,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "nationalInventory": false,
            "primaryCategoryId": "5feeafa6e781ffe0ae1673d887a9f37e",
            "FreeShippingMetro": true,
            "FulfilmentChannel": 3,
            "group_ids": [
              "5636f5ea43760c116d2580eb55e6c8e7",
              "fac0e533fcea70cda9cc5d0ec6a3397c",
              "78e850588abaf0a616052a340364864a",
              "1cb45765933db2ff97ea38eb4d8432bb",
              "5feeafa6e781ffe0ae1673d887a9f37e",
              "6225eb5bf8a031f750a1b03f810ccc6a"
            ],
            "apn": 9781923049307,
            "Size": "Miscellaneous",
            "price": 16,
            "Colour": "Miscellaneous",
            "prices": [
              {
                "type": "list",
                "amount": "16.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "1899-12-30"
              }
            ],
            "clearance": false,
            "is_default": false,
            "stateOOS": {
              "NT": "6"
            },
            "variation_id": "43663712",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Fs"
          },
          "value": "Tiki Cocktails by Shelly Slipsmith - Book",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9781923049307,
                "Size": "Miscellaneous",
                "price": 16,
                "Colour": "Miscellaneous",
                "prices": [
                  {
                    "type": "list",
                    "amount": "16.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "1899-12-30"
                  }
                ],
                "image_url": "https://kmartau.mo.cloudinary.net/3516105e-3e26-420a-a60f-f787ac5a5a5f.jpg?tx=w_300,h_300,c_pad",
                "clearance": false,
                "altImages": [],
                "is_default": false,
                "stateOOS": {
                  "NT": "6"
                },
                "variation_id": "43663712",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Fs"
              },
              "value": "Tiki Cocktails by Shelly Slipsmith - Book"
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
            "id": "P_42807124",
            "uri": "/product/celebrations-box-320g-42807124/",
            "url": "/product/celebrations-box-320g-42807124/",
            "video": {},
            "badges": [],
            "altImages": [
              "af2ce0fe-d02e-4719-a8f2-f6598b5266e3/42807124-2"
            ],
            "image_url": "https://assets.kmart.com.au/transform/64d6d46c-bdc3-4e03-9c37-b239c00e9a31/42807124-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 44,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "14417288bd1ac0195e6c9f2e00ded3e9",
            "nationalInventory": false,
            "ratings": {
              "averageScore": 4,
              "totalReviews": 6
            },
            "group_ids": [
              "4ac03cc3eac33a2c09a9f0d130dc4d3a",
              "e81986faeb2c7d7b51015ab9ed064816",
              "fac0e533fcea70cda9cc5d0ec6a3397c",
              "3318e836f8428fd5ab979c464599d10f",
              "6ea408ea56e8b710aa240004af7580c1",
              "290b129cea7f6323c52dfe38265c9378",
              "64e1aee43e4fb58697e067d620bc0d49",
              "14417288bd1ac0195e6c9f2e00ded3e9"
            ],
            "apn": 9300682055598,
            "Size": "Miscellaneous",
            "price": 16,
            "prices": [
              {
                "type": "list",
                "amount": "16.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2025-06-18"
              },
              {
                "type": "promo",
                "amount": "8.00",
                "country": "AU",
                "endDate": "2025-09-07",
                "currency": "AUD",
                "startDate": "2025-09-01"
              }
            ],
            "Colour": "Multi",
            "clearance": false,
            "is_default": false,
            "variation_id": "42807124",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Asst"
          },
          "value": "Celebrations Box 320g",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9300682055598,
                "Size": "Miscellaneous",
                "price": 16,
                "prices": [
                  {
                    "type": "list",
                    "amount": "16.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2025-06-18"
                  },
                  {
                    "type": "promo",
                    "amount": "8.00",
                    "country": "AU",
                    "endDate": "2025-09-07",
                    "currency": "AUD",
                    "startDate": "2025-09-01"
                  }
                ],
                "Colour": "Multi",
                "altImages": [
                  "af2ce0fe-d02e-4719-a8f2-f6598b5266e3/42807124-2"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/64d6d46c-bdc3-4e03-9c37-b239c00e9a31/42807124-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "variation_id": "42807124",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Asst"
              },
              "value": "Celebrations Box 320g"
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
            "id": "P_43532780",
            "uri": "/product/3-layer-food-storage-container-43532780/",
            "url": "/product/3-layer-food-storage-container-43532780/",
            "video": {},
            "badges": [],
            "altImages": [
              "bb94cf33-9fee-427d-b39e-79f5197d2cdf/43532780-2",
              "fd7d11c7-d2a5-48a2-8ab7-019146687870/43532780-3",
              "a38e3dd0-c842-460b-ac46-bf622f8fe09d/43532780-4",
              "885d9869-37a2-4921-a53a-84c7e5b8d9e4/43532780-5",
              "4b40ca99-873e-4a1b-8713-3ad888f32891/43532780-6",
              "7f3e7f61-f45a-4ceb-9a01-94e4509121b2/43532780-7"
            ],
            "image_url": "https://assets.kmart.com.au/transform/5581c64f-a5df-4e72-b307-ca9d82cfa902/43532780-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 38,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "9cd83d576d7b62522405956b02212ac6",
            "nationalInventory": false,
            "ratings": {
              "averageScore": 5,
              "totalReviews": 1
            },
            "group_ids": [
              "82fa99f71019fd39f8737e5daf8f140e",
              "fac0e533fcea70cda9cc5d0ec6a3397c",
              "c435c0bd533b81880a47d7a62f795b86",
              "9cd83d576d7b62522405956b02212ac6",
              "b2d23c022f28def95a01ebcb90d57a83"
            ],
            "apn": 9341111085755,
            "Size": "One Size",
            "price": 7,
            "prices": [
              {
                "type": "list",
                "amount": "7.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "1899-12-30"
              }
            ],
            "Colour": "Clear",
            "clearance": false,
            "is_default": false,
            "variation_id": "43532780",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Clear"
          },
          "value": "3 Layer Food Storage Container",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341111085755,
                "Size": "One Size",
                "price": 7,
                "prices": [
                  {
                    "type": "list",
                    "amount": "7.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "1899-12-30"
                  }
                ],
                "Colour": "Clear",
                "altImages": [
                  "bb94cf33-9fee-427d-b39e-79f5197d2cdf/43532780-2",
                  "fd7d11c7-d2a5-48a2-8ab7-019146687870/43532780-3",
                  "a38e3dd0-c842-460b-ac46-bf622f8fe09d/43532780-4",
                  "885d9869-37a2-4921-a53a-84c7e5b8d9e4/43532780-5",
                  "4b40ca99-873e-4a1b-8713-3ad888f32891/43532780-6",
                  "7f3e7f61-f45a-4ceb-9a01-94e4509121b2/43532780-7"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/5581c64f-a5df-4e72-b307-ca9d82cfa902/43532780-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "variation_id": "43532780",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Clear"
              },
              "value": "3 Layer Food Storage Container"
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
    "result_id": "63761f4e-251c-4148-a0c0-48cd046ed070",
    "request": {
      "sort_by": "relevance",
      "sort_order": "descending",
      "num_results_per_page": 3,
      "filters": {},
      "original_query": "curated gifts for a gourmet enthusiast who enjoys culinary explorations",
      "term": "curated gifts gourmet enthusiast enjoys culinary explorations",
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
