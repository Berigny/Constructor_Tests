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
  "original_query": "gifts for someone with a clean and uncluttered aesthetic",
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
          "display_name": "Category",
          "name": "Category",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 6,
              "display_name": "Candles & Home Fragrance",
              "value": "Candles & Home Fragrance",
              "data": {}
            },
            {
              "status": "",
              "count": 23,
              "display_name": "Mens Grooming",
              "value": "Mens Grooming",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Decor Accessories",
              "value": "Decor Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Cosmetics",
              "value": "Cosmetics",
              "data": {}
            },
            {
              "status": "",
              "count": 8,
              "display_name": "Chocolate",
              "value": "Chocolate",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Novelty Confectionery",
              "value": "Novelty Confectionery",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Party Favours & Glow",
              "value": "Party Favours & Glow",
              "data": {}
            },
            {
              "status": "",
              "count": 11,
              "display_name": "Accessories",
              "value": "Accessories",
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
              "display_name": "Seasonal Confectionary",
              "value": "Seasonal Confectionary",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Board Games & Puzzles",
              "value": "Board Games & Puzzles",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Dinnerware",
              "value": "Dinnerware",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Gift Bags",
              "value": "Gift Bags",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Impulse & Novelty Toys",
              "value": "Impulse & Novelty Toys",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Ball Sports & Games",
              "value": "Ball Sports & Games",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Diffusers",
              "value": "Diffusers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Craft Supplies",
              "value": "Craft Supplies",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Share Packs",
              "value": "Share Packs",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Kids Art, Craft & Stationery",
              "value": "Kids Art, Craft & Stationery",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Cards",
              "value": "Cards",
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
              "count": 6,
              "display_name": "Fragrant Candles",
              "value": "Fragrant Candles",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Moisturiser",
              "value": "Moisturiser",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Jewellery Storage",
              "value": "Jewellery Storage",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Masks",
              "value": "Masks",
              "data": {}
            },
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
              "display_name": "Lip Balm",
              "value": "Lip Balm",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Womens",
              "value": "Womens",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Halloween Candy",
              "value": "Halloween Candy",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Chocolates",
              "value": "Chocolates",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Party Favours",
              "value": "Party Favours",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Crossbody bags",
              "value": "Crossbody bags",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Caps",
              "value": "Caps",
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
              "count": 4,
              "display_name": "Necklaces",
              "value": "Necklaces",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Bath & Shower",
              "value": "Bath & Shower",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Gift Sets",
              "value": "Gift Sets",
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
              "count": 1,
              "display_name": "Lollies",
              "value": "Lollies",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Mugs & Cups",
              "value": "Mugs & Cups",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Large Gift Bag",
              "value": "Large Gift Bag",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Bath Accessories",
              "value": "Bath Accessories",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Reed Diffusers",
              "value": "Reed Diffusers",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Birthday",
              "value": "Birthday",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Earrings",
              "value": "Earrings",
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
              "count": 6,
              "display_name": "Skincare",
              "value": "Skincare",
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
              "count": 8,
              "display_name": "Fragrances",
              "value": "Fragrances",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Cosmetics Bag",
              "value": "Cosmetics Bag",
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
              "display_name": "Hats",
              "value": "Hats",
              "data": {}
            },
            {
              "status": "",
              "count": 8,
              "display_name": "Jewellery",
              "value": "Jewellery",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Bath & Body",
              "value": "Bath & Body",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Board Games",
              "value": "Board Games",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Wallets",
              "value": "Wallets",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Games & Activities",
              "value": "Games & Activities",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Stationery",
              "value": "Stationery",
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
              "count": 15,
              "display_name": "Pink",
              "value": "Pink",
              "data": {}
            },
            {
              "status": "",
              "count": 59,
              "display_name": "Multi",
              "value": "Multi",
              "data": {}
            },
            {
              "status": "",
              "count": 6,
              "display_name": "Purple",
              "value": "Purple",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "Black",
              "value": "Black",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Beige",
              "value": "Beige",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Navy",
              "value": "Navy",
              "data": {}
            },
            {
              "status": "",
              "count": 7,
              "display_name": "Gold",
              "value": "Gold",
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
              "count": 3,
              "display_name": "Blue",
              "value": "Blue",
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
              "count": 37,
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
              "count": 17,
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
              "count": 10,
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
              "count": 16,
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
              "count": 18,
              "display_name": "$50 - $100",
              "value": "\"50\"-\"100\"",
              "data": {},
              "range": [
                50,
                100
              ]
            },
            {
              "status": "",
              "count": 6,
              "display_name": "$100 and more",
              "value": "\"100\"-\"inf\"",
              "data": {},
              "range": [
                100,
                "inf"
              ]
            }
          ]
        },
        {
          "display_name": "Material",
          "name": "Material",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Stoneware",
              "value": "Stoneware",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "PVC",
              "value": "PVC",
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
              "count": 2,
              "display_name": "Baylis & Harding",
              "value": "Baylis & Harding",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Baylis and Harding",
              "value": "Baylis and Harding",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Cadbury",
              "value": "Cadbury",
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
              "count": 2,
              "display_name": "Ferrero Rocher",
              "value": "Ferrero Rocher",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "Hallmark",
              "value": "Hallmark",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "Lindt",
              "value": "Lindt",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Maltesers",
              "value": "Maltesers",
              "data": {}
            },
            {
              "status": "",
              "count": 15,
              "display_name": "OXX Studio",
              "value": "OXX STUDIO",
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
              "count": 3,
              "display_name": "0 - 50g",
              "value": "0 - 50g",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "50 - 100g",
              "value": "50 - 100g",
              "data": {}
            },
            {
              "status": "",
              "count": 5,
              "display_name": "100 - 200g",
              "value": "100 - 200g",
              "data": {}
            },
            {
              "status": "",
              "count": 4,
              "display_name": "200 - 300g",
              "value": "200 - 300g",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "300 - 400g",
              "value": "300 - 400g",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Over 500g",
              "value": "Over 500g",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "0 - 50ml",
              "value": "0 - 50ml",
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
              "count": 3,
              "display_name": "Floral",
              "value": "Floral",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Sweet",
              "value": "Sweet",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Fresh",
              "value": "Fresh",
              "data": {}
            },
            {
              "status": "",
              "count": 3,
              "display_name": "Fruity",
              "value": "Fruity",
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
              "count": 7,
              "display_name": "Women",
              "value": "Women",
              "data": {}
            },
            {
              "status": "",
              "count": 1,
              "display_name": "Men",
              "value": "Men",
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
              "count": 2,
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
              "count": 2,
              "display_name": "2-4 Years",
              "value": "2+ Years",
              "data": {}
            },
            {
              "status": "",
              "count": 2,
              "display_name": "5+ Years",
              "value": "5+ Years",
              "data": {}
            },
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
          "display_name": "Features",
          "name": "Features",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 4,
              "display_name": "For Indoor/Outdoor Use",
              "value": "For Indoor/Outdoor Use",
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
              "display_name": "Xbody",
              "value": "Xbody",
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
          "display_name": "Formulation",
          "name": "Formulation",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Spray",
              "value": "Spray",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Size Range",
          "name": "Size Range",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Large to Extra Large",
              "value": "Large to Extra Large",
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
              "display_name": "No",
              "value": "No",
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
              "display_name": "AAA",
              "value": "AAA",
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
              "count": 1,
              "display_name": "Adults",
              "value": "Adults",
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
              "count": 1,
              "display_name": "Reference",
              "value": "Reference",
              "data": {}
            }
          ],
          "hidden": false,
          "data": {}
        },
        {
          "display_name": "Card Type",
          "name": "Card Type",
          "type": "multiple",
          "options": [
            {
              "status": "",
              "count": 1,
              "display_name": "Birthday",
              "value": "Birthday",
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
              "count": 51,
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
              "count": 41,
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
              "count": 36,
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
              "count": 41,
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
              "group_id": "81b616fbff55b8698d44852f45c08630",
              "display_name": "Christmas",
              "count": 34,
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
              "group_id": "7a7f3a70f71ac2372ae60e431b8236bb",
              "display_name": "Beauty",
              "count": 27,
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
              "group_id": "bbbcb4ecce212f38c5dcfefbb03a8533",
              "display_name": "Mens",
              "count": 12,
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
              "count": 24,
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
              "group_id": "89abe35cb1ad766f11a28c598fd37ba1",
              "display_name": "Gifting",
              "count": 10,
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
              "group_id": "6095b2832f08bb7ca1c60ffc1b2d091b",
              "display_name": "Kids & Baby",
              "count": 4,
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
            },
            {
              "group_id": "66d0af2d5da0109dc2aae67829f7d4d4",
              "display_name": "Toys",
              "count": 3,
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
            "id": "P_42351818",
            "url": "/product/jasmine-glass-jar-candle-42351818/",
            "uri": "/product/jasmine-glass-jar-candle-42351818/",
            "video": {},
            "badges": [],
            "image_url": "https://assets.kmart.com.au/transform/511bee98-00ab-47ce-8bef-e09a6e1ab021/42351818-1?io=transform:extend,width:300,height:300",
            "altImages": [
              "52840f2c-957c-4cf6-945f-5d3560f6f697/42351818-2",
              "23c45b5a-a296-45b9-a09d-d0e75f5a468f/42351818-3",
              "2f8855b8-d80a-4e53-ba6e-ffebc8be762d/42351818-4",
              "57ce8716-e08e-485b-ba4a-cc148904e174/42351818-5"
            ],
            "FreeShipping": true,
            "MerchDepartment": 71,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FreeShippingMetro": true,
            "nationalInventory": false,
            "FulfilmentChannel": 3,
            "primaryCategoryId": "8c6873ec180492904c0bd55cf2d3d444",
            "ratings": {
              "totalReviews": 126,
              "averageScore": 4.5
            },
            "group_ids": [
              "60cb8622ceab6bc104a182d5b26ea44a",
              "abfc3a65538a6ec86502b2b498b6b4a6",
              "fe55ea1c2dd73aa48c39fb6d1acf56c0",
              "62c62e99dae6e140bcf0916841f4922f",
              "a0f1fceee7e4da759532c423d637ad20",
              "fac0e533fcea70cda9cc5d0ec6a3397c",
              "c4877e77d7c69f808459a0514b3f8603",
              "095f6dbc20979a8530c4107ec30215d4",
              "23435af8ff7216906f3fd483b71f6ea0",
              "c902f85857b055938ef5d8715a2a8c21",
              "50d2c022c440bd69ba551e412e810905",
              "496c27c7768d617ae1d6e2bcb4993cb1",
              "8f8f0c1819f86e31c87c9efb0fd4db08",
              "635d29af4e8b8898a1b2de5e278083b2",
              "fff2ed1c1f179e654ccd64b4d5e8b934",
              "19d4b43fa883720479d5936e4cc04223",
              "63782103ea77d06dc67e4a3f8dd95446",
              "e6a5c757f74f837942879fd60f7c0fbd",
              "8c6873ec180492904c0bd55cf2d3d444"
            ],
            "apn": 9341103905948,
            "Size": "One Size",
            "price": 1,
            "prices": [
              {
                "type": "list",
                "amount": "1.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2023-07-07"
              },
              {
                "type": "promo",
                "amount": "1.00",
                "country": "AU",
                "endDate": "2023-09-06",
                "currency": "AUD",
                "startDate": "2023-08-10"
              }
            ],
            "Colour": "Pink",
            "clearance": false,
            "is_default": false,
            "variation_id": "42351818",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Pink"
          },
          "value": "Jasmine Glass Jar Candle",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341103905948,
                "Size": "One Size",
                "price": 1,
                "prices": [
                  {
                    "type": "list",
                    "amount": "1.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2023-07-07"
                  },
                  {
                    "type": "promo",
                    "amount": "1.00",
                    "country": "AU",
                    "endDate": "2023-09-06",
                    "currency": "AUD",
                    "startDate": "2023-08-10"
                  }
                ],
                "Colour": "Pink",
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/511bee98-00ab-47ce-8bef-e09a6e1ab021/42351818-1?io=transform:extend,width:300,height:300",
                "altImages": [
                  "52840f2c-957c-4cf6-945f-5d3560f6f697/42351818-2",
                  "23c45b5a-a296-45b9-a09d-d0e75f5a468f/42351818-3",
                  "2f8855b8-d80a-4e53-ba6e-ffebc8be762d/42351818-4",
                  "57ce8716-e08e-485b-ba4a-cc148904e174/42351818-5"
                ],
                "is_default": false,
                "variation_id": "42351818",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Pink"
              },
              "value": "Jasmine Glass Jar Candle"
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
            "id": "P_42984542",
            "uri": "/product/hydrating-sheet-mask-rose-42984542/",
            "url": "/product/hydrating-sheet-mask-rose-42984542/",
            "video": {},
            "badges": [],
            "altImages": [
              "0f421756-42a4-4477-aee5-f6346826824d/42984542-2",
              "e359bca0-1aa9-46d9-9249-a8a49511b38a/42984542-3"
            ],
            "image_url": "https://assets.kmart.com.au/transform/baff442b-e333-418e-8575-28d795224674/42984542-1?io=transform:extend,width:300,height:300",
            "FreeShipping": true,
            "MerchDepartment": 20,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FulfilmentChannel": 3,
            "FreeShippingMetro": true,
            "primaryCategoryId": "0a8fdc7c09a42c176deab0fc7c5a8308",
            "nationalInventory": false,
            "ratings": {
              "averageScore": 4.8,
              "totalReviews": 6
            },
            "group_ids": [
              "09dfe6a922353ae4c89e01a17c1b213e",
              "0a8fdc7c09a42c176deab0fc7c5a8308",
              "8f0b723d51b63d5926cfee1846b000e4"
            ],
            "apn": 9341107859742,
            "Size": "One Size",
            "price": 2,
            "prices": [
              {
                "type": "list",
                "amount": "2.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2024-11-01"
              }
            ],
            "Colour": "Pink",
            "clearance": false,
            "is_default": false,
            "variation_id": "42984542",
            "variant_video": {},
            "variant_badges": [],
            "SecondaryColour": "Rose"
          },
          "value": "Hydrating Sheet Mask - Rose",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 9341107859742,
                "Size": "One Size",
                "price": 2,
                "prices": [
                  {
                    "type": "list",
                    "amount": "2.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2024-11-01"
                  }
                ],
                "Colour": "Pink",
                "altImages": [
                  "0f421756-42a4-4477-aee5-f6346826824d/42984542-2",
                  "e359bca0-1aa9-46d9-9249-a8a49511b38a/42984542-3"
                ],
                "clearance": false,
                "image_url": "https://assets.kmart.com.au/transform/baff442b-e333-418e-8575-28d795224674/42984542-1?io=transform:extend,width:300,height:300",
                "is_default": false,
                "variation_id": "42984542",
                "variant_video": {},
                "variant_badges": [],
                "SecondaryColour": "Rose"
              },
              "value": "Hydrating Sheet Mask - Rose"
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
            "id": "P_43513901",
            "url": "/product/baylis-and-harding-signature-collection-jojoba-vanilla-and-almond-oil-43513901/",
            "uri": "/product/baylis-and-harding-signature-collection-jojoba-vanilla-and-almond-oil-43513901/",
            "video": {},
            "badges": [],
            "SavePrice": "WAS $10",
            "image_url": "https://assets.kmart.com.au/transform/4bda4f8e-f8d4-4787-8672-bf514b65a5ba/43513901-0?io=transform:extend,width:300,height:300",
            "altImages": [
              "208a9192-f14a-4072-a49d-fdca74580793/43513901-1",
              "fe40d75c-020b-47e7-8755-0bba683c6d2d/43513901-2",
              "a48304ab-27a9-4f98-a9b7-ca76b867c7a3/43513901-3",
              "a93bfb3f-f38a-407b-94d7-105ad6509e8d/43513901-4"
            ],
            "FreeShipping": true,
            "MerchDepartment": 85,
            "AssortedProducts": false,
            "isPreOrderActive": false,
            "FreeShippingMetro": true,
            "nationalInventory": false,
            "FulfilmentChannel": 3,
            "primaryCategoryId": "7a0ab697c9dad983d0777f6946e0c724",
            "ratings": {
              "totalReviews": 0,
              "averageScore": 0
            },
            "group_ids": [
              "60cb8622ceab6bc104a182d5b26ea44a",
              "df647e6b382ceaac67dd6cee83563b71",
              "009d47c9f06679277fad788febd93ee1",
              "7cc528b2bff05773ccd378082e0d56c8",
              "7a0ab697c9dad983d0777f6946e0c724",
              "3de30c8abc84c4f4d5ff8e82873d9a75",
              "09dfe6a922353ae4c89e01a17c1b213e",
              "d8e2992c0ba8e748dd76db01c237a9d6",
              "1e92886e640473b54f8fa5dd9455435d",
              "3dc32ab822eb350932d388e9848c5b5e",
              "496c27c7768d617ae1d6e2bcb4993cb1",
              "6ed4abbdb5af46c177395861ba344739",
              "8f8f0c1819f86e31c87c9efb0fd4db08",
              "f29aaed132d5701bd93080a0c8643783",
              "2249d9a13d388878fb6eb1dd59c1fbf6",
              "c2b2bc0044a36c51714c375b37d36e5c",
              "63782103ea77d06dc67e4a3f8dd95446",
              "1714c8d704f7553ccbbd4365da6f4024",
              "7812c524226eb7bab11435fe9ea7cd10"
            ],
            "apn": 17854120624,
            "Size": "One Size",
            "price": 5,
            "prices": [
              {
                "type": "list",
                "amount": "5.00",
                "country": "AU",
                "endDate": "9999-12-31",
                "currency": "AUD",
                "startDate": "2025-07-29"
              },
              {
                "type": "promo",
                "amount": "10.00",
                "country": "AU",
                "endDate": "2025-05-11",
                "currency": "AUD",
                "startDate": "2025-04-24"
              }
            ],
            "Colour": "Pink",
            "clearance": true,
            "is_default": false,
            "stateOOS": {
              "WA": "6",
              "NT": "6",
              "TAS": "6",
              "ACT": "6"
            },
            "variation_id": "43513901",
            "variant_video": {},
            "variant_badges": [
              "Clearance"
            ],
            "SecondaryColour": "Mothers Dy"
          },
          "value": "Baylis & Harding Signature Collection - Jojoba, Vanilla and Almond Oil",
          "is_slotted": false,
          "variations": [
            {
              "data": {
                "apn": 17854120624,
                "Size": "One Size",
                "price": 5,
                "prices": [
                  {
                    "type": "list",
                    "amount": "5.00",
                    "country": "AU",
                    "endDate": "9999-12-31",
                    "currency": "AUD",
                    "startDate": "2025-07-29"
                  },
                  {
                    "type": "promo",
                    "amount": "10.00",
                    "country": "AU",
                    "endDate": "2025-05-11",
                    "currency": "AUD",
                    "startDate": "2025-04-24"
                  }
                ],
                "Colour": "Pink",
                "clearance": true,
                "image_url": "https://assets.kmart.com.au/transform/4bda4f8e-f8d4-4787-8672-bf514b65a5ba/43513901-0?io=transform:extend,width:300,height:300",
                "altImages": [
                  "208a9192-f14a-4072-a49d-fdca74580793/43513901-1",
                  "fe40d75c-020b-47e7-8755-0bba683c6d2d/43513901-2",
                  "a48304ab-27a9-4f98-a9b7-ca76b867c7a3/43513901-3",
                  "a93bfb3f-f38a-407b-94d7-105ad6509e8d/43513901-4"
                ],
                "is_default": false,
                "stateOOS": {
                  "WA": "6",
                  "NT": "6",
                  "TAS": "6",
                  "ACT": "6"
                },
                "variation_id": "43513901",
                "variant_video": {},
                "variant_badges": [
                  "Clearance"
                ],
                "SecondaryColour": "Mothers Dy"
              },
              "value": "Baylis & Harding Signature Collection - Jojoba, Vanilla and Almond Oil"
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
    "result_id": "36026485-3f85-4596-a39a-6844c069744a",
    "request": {
      "sort_by": "relevance",
      "sort_order": "descending",
      "num_results_per_page": 3,
      "filters": {},
      "original_query": "gifts for someone with a clean and uncluttered aesthetic",
      "term": "gifts clean uncluttered aesthetic",
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
