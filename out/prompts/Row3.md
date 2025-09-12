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
  "original_query": "gifts that evoke nostalgia and retro charm from the 90s",
  "constraints": {
    "budget": "",
    "audience": "Kids",
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
          "display_name": "Category",
          "name": "Category",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 68,
              "display_name": "Accessories",
              "value": "Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Mens Grooming",
              "value": "Mens Grooming",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Craft Supplies",
              "value": "Craft Supplies",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Party Favours & Glow",
              "value": "Party Favours & Glow",
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
              "count": 8,
              "display_name": "Kids Art, Craft & Stationery",
              "value": "Kids Art, Craft & Stationery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lollies & Candies",
              "value": "Lollies & Candies",
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
              "count": 1,
              "display_name": "Pens & Pencils",
              "value": "Pens & Pencils",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Cosmetics",
              "value": "Cosmetics",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Novelty Confectionery",
              "value": "Novelty Confectionery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Seasonal Confectionary",
              "value": "Seasonal Confectionary",
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
              "count": 2,
              "display_name": "Backpacks & Bags",
              "value": "Backpacks & Bags",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Party Serveware & Accessories",
              "value": "Party Serveware & Accessories",
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
              "display_name": "Dolls & Accessories",
              "value": "Dolls & Accessories",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Product Type",
          "name": "Product Type",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 10,
              "display_name": "Necklaces",
              "value": "Necklaces",
              "data": {}
            },
            {
              "status": "",
              "count": 46,
              "display_name": "Keyrings",
              "value": "Keyrings",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Hand Care",
              "value": "Hand Care",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Jewellery Making",
              "value": "Jewellery Making",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Bracelets",
              "value": "Bracelets",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Earrings",
              "value": "Earrings",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Party Favours",
              "value": "Party Favours",
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
              "display_name": "Bath & Shower",
              "value": "Bath & Shower",
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
              "display_name": "Notebooks",
              "value": "Notebooks",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pens",
              "value": "Pens",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lip Balm",
              "value": "Lip Balm",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Christmas Food",
              "value": "Christmas Food",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "iPhone Cases & Covers",
              "value": "iPhone Cases & Covers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Serveware",
              "value": "Serveware",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Pinata",
              "value": "Pinata",
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
              "count": 64,
              "display_name": "Jewellery",
              "value": "Jewellery",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Bath & Body",
              "value": "Bath & Body",
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
              "count": 7,
              "display_name": "Crafting",
              "value": "Crafting",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Watches",
              "value": "Watches",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Lips",
              "value": "Lips",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Handbags",
              "value": "Handbags",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Purses & Wallets",
              "value": "Purses & Wallets",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Backpacks",
              "value": "Backpacks",
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
              "display_name": "Dolls",
              "value": "Dolls",
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
              "count": 21,
              "display_name": "Gold",
              "value": "Gold",
              "data": {}
            },
            {
              "status": "",
              "count": 11,
              "display_name": "Pink",
              "value": "Pink",
              "data": {}
            },
            {
              "status": "",
              "count": 28,
              "display_name": "Multi",
              "value": "Multi",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Black",
              "value": "Black",
              "data": {}
            },
            {
              "status": "",
              "count": 10,
              "display_name": "Red",
              "value": "Red",
              "data": {}
            },
            {
              "status": "",
              "count": 11,
              "display_name": "Silver",
              "value": "Silver",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Yellow",
              "value": "Yellow",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
              "display_name": "Blue",
              "value": "Blue",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Brown",
              "value": "Brown",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Beige",
              "value": "Beige",
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
              "count": 1,
              "display_name": "Purple",
              "value": "Purple",
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
              "display_name": "Disney Lilo & Stitch",
              "value": "Disney Lilo & Stitch",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Dubble Bubble",
              "value": "Dubble Bubble",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Hello Kitty",
              "value": "Hello Kitty",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "OXX Studio",
              "value": "OXX STUDIO",
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
              "count": 45,
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
              "count": 55,
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
              "count": 8,
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
              "count": 4,
              "display_name": "$20 - $30",
              "value": "\"20\"-\"30\"",
              "data": {},
              "range": [
                20,
                30
              ]
            }
          ]
        },
        {
          "display_name": "Suitable for ages",
          "name": "Suitable for ages",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 2,
              "display_name": "2-4 Years",
              "value": "2+ Years",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
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
          "display_name": "Gender",
          "name": "Gender",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 62,
              "display_name": "Women",
              "value": "Women",
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
              "count": 2,
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
            }
          ],
          "hidden": false,
          "data": {}
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
              "count": 1,
              "display_name": "100 - 200g",
              "value": "100 - 200g",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "0 - 50ml",
              "value": "0 - 50ml",
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
          "display_name": "Suitable for",
          "name": "Suitable for",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 2,
              "display_name": "Kids",
              "value": "Kids",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Style",
          "name": "Style",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Flower",
              "value": "Flower",
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
          "display_name": "Battery Required",
          "name": "Battery Required",
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
          "display_name": "Battery Type",
          "name": "Battery Type",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Button Cell",
              "value": "Button Cell",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Ink Colour",
          "name": "Ink Colour",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Black",
              "value": "Black",
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
              "group_id": "ce059e196a9104cd5e29f3295a32e737",
              "display_name": "Mother's Day",
              "count": 67,
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
              "count": 63,
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
              "group_id": "dddaa894234df841cfb678463562e055",
              "display_name": "Home & Living",
              "count": 52,
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
              "group_id": "7a7f3a70f71ac2372ae60e431b8236bb",
              "display_name": "Beauty",
              "count": 3,
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
              "group_id": "e1114432a2ac994a333544d5da17e1fb",
              "display_name": "Halloween",
              "count": 1,
              "data": {
                "url": "/halloween/inactive/",
                "sequence": 4000,
                "isSpecial": false,
                "identifier": "Halloween",
                "breadcrumbs": [
                  "b9805e11857bf8b29b5d9a8ea8de48b7",
                  "e1114432a2ac994a333544d5da17e1fb"
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
              "count": 23,
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
              "group_id": "4e21b615a67e9e9ad13a030628bb904c",
              "display_name": "Back To School",
              "count": 20,
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
              "count": 14,
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
              "group_id": "6095b2832f08bb7ca1c60ffc1b2d091b",
              "display_name": "Kids & Baby",
              "count": 8,
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
              "group_id": "89abe35cb1ad766f11a28c598fd37ba1",
              "display_name": "Gifting",
              "count": 6,
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
              "group_id": "81b616fbff55b8698d44852f45c08630",
              "display_name": "Christmas",
              "count": 3,
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
              "group_id": "2d95e1e17abc6c9afb85088671f65e3a",
              "display_name": "Sport & Outdoor",
              "count": 2,
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
            "id": "P_43593866",
            "uri": "/product/oxx-bodycare-hand-sanitiser-30ml-cherry-scented-43593866/",
            "url": "/product/oxx-bodycare-hand-sanitiser-30ml-cherry-scented-43593866/",
            "Brand": "OXX",
            "video": {},
            "badges": [],
            "altImages": [
              "7159518a-eb19-4bfa-860f-260d3165433e/43593866-2",
              "da5115c5-8eda-4b0f-b1e4-782ecf93c702/43593866-3",
              "3dab4a98-9afc-4416-bd81-e95f3a5be693/43593866-4",
              "3e73855a-1fb1-42e7-b7cc-7c0331a546e7/43593866-5",
              "018521f5-d850-4b70-951b-d5969b878642/43593866-6"
            ],
            "image_url": "https://assets.kmart.com.au/transform/96813177-e491-49ee-b8d7-da8429e553e2/43593866-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 85,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "2249d9a13d388878fb6eb1dd59c1fbf6",
            "nationalInventory": false,
            "group_ids": [
              "547bace47fbb15b4d69b9c587d9e0c8f",
              "b36f6b5d81cf83b182953bd4f3c18c86",
              "09dfe6a922353ae4c89e01a17c1b213e",
              "2249d9a13d388878fb6eb1dd59c1fbf6",
              "eba93bc03eec22b889d22fc821ecc9bd",
              "e03ba3848703b24610aa8a96876a1223",
              "8c4cd3a37365614698b7be22fdd61fec"
            ],
            "apn": 9341111352505,
            "Size": "One Size",
            "price": 4,
            "prices": [
              {
                "type": "list",
                "amount": "4.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "1899-12-30"
              }
            ],
            "Colour": "MULTI",
            "clearance": false,
            "is_default": false,
            "variation_id": "43593866",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Cupcake"
          },
          "value": "OXX Bodycare Hand Sanitiser 30ml - Cherry Scented",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341111352505,
                "Size": "One Size",
                "price": 4,
                "prices": [
                  {
                    "type": "list",
                    "amount": "4.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "1899-12-30"
                  }
                ],
                "Colour": "MULTI",
                "altImages": [
                  "7159518a-eb19-4bfa-860f-260d3165433e/43593866-2",
                  "da5115c5-8eda-4b0f-b1e4-782ecf93c702/43593866-3",
                  "3dab4a98-9afc-4416-bd81-e95f3a5be693/43593866-4",
                  "3e73855a-1fb1-42e7-b7cc-7c0331a546e7/43593866-5",
                  "018521f5-d850-4b70-951b-d5969b878642/43593866-6"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/96813177-e491-49ee-b8d7-da8429e553e2/43593866-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "variation_id": "43593866",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Cupcake"
              },
              "value": "OXX Bodycare Hand Sanitiser 30ml - Cherry Scented"
            }
          ]
        },
        {
          "matched_terms": [],
          "labels": {
            "__cnstrc_is_new_arrivals": {
              "display_name": "is_new_arrivals",
              "value": null
            },
            "__cnstrc_is_global_trending_now": {
              "display_name": "is_global_trending_now",
              "value": null
            }
          },
          "data": {
            "id": "P_S171131",
            "uri": "/product/flower-charm-necklace-white-pink-and-gold-tone-s171131/",
            "url": "/product/flower-charm-necklace-white-pink-and-gold-tone-s171131/",
            "video": {},
            "badges": [],
            "image_url": "https://assets.kmart.com.au/transform/69e5f469-2bda-482b-9a0a-ed283133f0e9/73526629-1?io=transform:extend,width:300,height:300",
            "altImages": [
              "2dcdeb62-ebe6-414b-9717-4c31c342563d/73526629-2",
              "1bb6ea76-49aa-4952-b8f7-40a820144932/73526629-3",
              "f9e89b3a-a9f0-4824-8de3-b23e1a9b3f8c/73526629-4",
              "c5cb3dc7-b614-42a6-956d-d0527883cfa7/73526629-5",
              "caac6cdd-fff3-40c0-b15c-bc08638c9d21/73526629-6",
              "287bf809-6ee1-4b95-b972-c6895fe7a65b/73526629-7"
            ],
            "FreeShipping": true,
            "MerchDepartment": 32,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "nationalInventory": false,
            "primaryCategoryId": "2a02df4c852ef4521638accf041bc0d2",
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "ratings": {
              "averageScore": 0,
              "totalReviews": 0
            },
            "group_ids": [
              "19f1fca999bb71dfe161536f207e63cb",
              "1c42d31c157d84e1eeb5e8e0cf23fd21",
              "f2324b102fa3001890c6421baf1f5606",
              "7f81fe542cf4448fbcd799615527dc02",
              "980f7d55e059ea2729fbe5c75ad5ff01",
              "2a02df4c852ef4521638accf041bc0d2",
              "0ec2fc639f1e98c8cecf3f3bc890a7f9",
              "0fe0a5d390827ac12e63d4cc1040fc39",
              "d5c7858af01166e5a39fc8a640a925f4"
            ],
            "apn": 9341111382762,
            "Size": "One Size",
            "price": 6,
            "Colour": "Gold",
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
            "clearance": false,
            "is_default": false,
            "stateOOS": {
              "NT": "6"
            },
            "variation_id": "73526629",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "GOLD METAL"
          },
          "value": "Flower Charm Necklace - White, Pink and Gold Tone",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341111382762,
                "Size": "One Size",
                "price": 6,
                "Colour": "Gold",
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
                "image_url": "https://assets.kmart.com.au/transform/69e5f469-2bda-482b-9a0a-ed283133f0e9/73526629-1?io=transform:extend,width:300,height:300",
                "clearance": false,
                "altImages": [
                  "2dcdeb62-ebe6-414b-9717-4c31c342563d/73526629-2",
                  "1bb6ea76-49aa-4952-b8f7-40a820144932/73526629-3",
                  "f9e89b3a-a9f0-4824-8de3-b23e1a9b3f8c/73526629-4",
                  "c5cb3dc7-b614-42a6-956d-d0527883cfa7/73526629-5",
                  "caac6cdd-fff3-40c0-b15c-bc08638c9d21/73526629-6",
                  "287bf809-6ee1-4b95-b972-c6895fe7a65b/73526629-7"
                ],
                "is_default": false,
                "stateOOS": {
                  "NT": "6"
                },
                "variation_id": "73526629",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "GOLD METAL"
              },
              "value": "Flower Charm Necklace - White, Pink and Gold Tone"
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
            "id": "P_73600756",
            "uri": "/product/motel-bag-charm-keyring-pink-73600756/",
            "url": "/product/motel-bag-charm-keyring-pink-73600756/",
            "video": {},
            "badges": [],
            "image_url": "https://assets.kmart.com.au/transform/6c85d7cd-7f2c-4b18-ae4f-1db4e0d5339d/73600756-1?io=transform:extend,width:300,height:300",
            "altImages": [
              "c3510fe6-8fa4-48f1-a6a4-e1c1bd593919/73600756-2",
              "de21e1b4-1077-4b98-9bb1-3c6f5ae0ed6f/73600756-3"
            ],
            "FreeShipping": true,
            "MerchDepartment": 32,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "nationalInventory": false,
            "primaryCategoryId": "940933b0ea093191ecbd3a8821eab247",
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "ratings": {
              "averageScore": 0,
              "totalReviews": 0
            },
            "group_ids": [
              "19f1fca999bb71dfe161536f207e63cb",
              "1c42d31c157d84e1eeb5e8e0cf23fd21",
              "940933b0ea093191ecbd3a8821eab247",
              "1bd8ad84c5f1dfab13cd60a51fbc5577",
              "76a9dfd8d11cff59ffc2e47add2bbf7c",
              "7f81fe542cf4448fbcd799615527dc02",
              "0ec2fc639f1e98c8cecf3f3bc890a7f9",
              "0fe0a5d390827ac12e63d4cc1040fc39"
            ],
            "apn": 9352602191497,
            "Size": "One Size",
            "price": 6,
            "Colour": "Pink",
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
            "clearance": false,
            "is_default": false,
            "variation_id": "73600756",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Pink"
          },
          "value": "Motel Bag Charm Keyring - Pink",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9352602191497,
                "Size": "One Size",
                "price": 6,
                "Colour": "Pink",
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
                "image_url": "https://assets.kmart.com.au/transform/6c85d7cd-7f2c-4b18-ae4f-1db4e0d5339d/73600756-1?io=transform:extend,width:300,height:300",
                "clearance": false,
                "altImages": [
                  "c3510fe6-8fa4-48f1-a6a4-e1c1bd593919/73600756-2",
                  "de21e1b4-1077-4b98-9bb1-3c6f5ae0ed6f/73600756-3"
                ],
                "is_default": false,
                "variation_id": "73600756",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Pink"
              },
              "value": "Motel Bag Charm Keyring - Pink"
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
    "result_id": "f514ecdb-2747-4c37-b448-3b1546529467",
    "request": {
      "sort_by": "relevance",
      "sort_order": "descending",
      "num_results_per_page": 3,
      "filters": {},
      "original_query": "gifts that evoke nostalgia and retro charm from the 90s",
      "term": "gifts evoke nostalgia retro charm 90s",
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
