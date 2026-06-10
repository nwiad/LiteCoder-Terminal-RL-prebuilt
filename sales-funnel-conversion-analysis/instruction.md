## Sales Conversion Funnel Analysis with Multi-Product Data

You work as a data scientist for "TechMart", an e-commerce company selling electronics, computers, and accessories. Analyze raw web analytics and sales data covering October–December 2023 to build a conversion funnel analysis. Write a Python script (`/app/solution.py`) that reads the input CSV files, processes the data, and writes results to `/app/output.json`.

### Technical Requirements
- Language: Python 3.x
- Input files: `/app/impressions.csv`, `/app/clicks.csv`, `/app/cart_additions.csv`, `/app/purchases.csv`
- Output file: `/app/output.json`

### Input Data Specifications

**impressions.csv** — Records of ad/page impressions:
| Column | Type | Description |
|---|---|---|
| impression_id | string | Unique impression identifier |
| user_id | string | User identifier |
| timestamp | string | ISO 8601 datetime (e.g., `2023-10-15T08:30:00`) |
| traffic_source | string | One of: `organic`, `paid_search`, `social`, `email`, `direct` |
| device_type | string | One of: `desktop`, `mobile`, `tablet` |
| product_category | string | One of: `electronics`, `computers`, `accessories` |

**clicks.csv** — Records of clicks from impressions:
| Column | Type | Description |
|---|---|---|
| click_id | string | Unique click identifier |
| impression_id | string | References impressions.csv |
| user_id | string | User identifier |
| timestamp | string | ISO 8601 datetime |
| product_category | string | Same categories as above |

**cart_additions.csv** — Records of items added to cart:
| Column | Type | Description |
|---|---|---|
| cart_id | string | Unique cart addition identifier |
| click_id | string | References clicks.csv |
| user_id | string | User identifier |
| timestamp | string | ISO 8601 datetime |
| product_category | string | Same categories as above |
| item_price | float | Price in USD |

**purchases.csv** — Records of completed purchases:
| Column | Type | Description |
|---|---|---|
| purchase_id | string | Unique purchase identifier |
| cart_id | string | References cart_additions.csv |
| user_id | string | User identifier |
| timestamp | string | ISO 8601 datetime |
| product_category | string | Same categories as above |
| amount | float | Purchase amount in USD |

### Data Cleaning Rules
1. Remove rows with any missing values in required columns (all columns listed above are required).
2. Remove duplicate rows based on the primary ID column of each file (`impression_id`, `click_id`, `cart_id`, `purchase_id`).
3. After deduplication and missing-value removal, use the cleaned data for all calculations.

### Output Specification

Write a single JSON object to `/app/output.json` with the following structure:

```json
{
  "overall_funnel": {
    "impressions": <int>,
    "clicks": <int>,
    "cart_additions": <int>,
    "purchases": <int>,
    "impression_to_click_rate": <float>,
    "click_to_cart_rate": <float>,
    "cart_to_purchase_rate": <float>,
    "overall_conversion_rate": <float>
  },
  "by_traffic_source": {
    "<source_name>": {
      "impressions": <int>,
      "clicks": <int>,
      "cart_additions": <int>,
      "purchases": <int>,
      "impression_to_click_rate": <float>,
      "click_to_cart_rate": <float>,
      "cart_to_purchase_rate": <float>
    }
  },
  "by_device_type": {
    "<device_name>": {
      "impressions": <int>,
      "clicks": <int>,
      "cart_additions": <int>,
      "purchases": <int>,
      "impression_to_click_rate": <float>,
      "click_to_cart_rate": <float>,
      "cart_to_purchase_rate": <float>
    }
  },
  "by_product_category": {
    "<category_name>": {
      "impressions": <int>,
      "clicks": <int>,
      "cart_additions": <int>,
      "purchases": <int>,
      "impression_to_click_rate": <float>,
      "click_to_cart_rate": <float>,
      "cart_to_purchase_rate": <float>
    }
  },
  "by_month": {
    "<YYYY-MM>": {
      "impressions": <int>,
      "clicks": <int>,
      "cart_additions": <int>,
      "purchases": <int>,
      "impression_to_click_rate": <float>,
      "click_to_cart_rate": <float>,
      "cart_to_purchase_rate": <float>
    }
  },
  "bottleneck": <string>
}
```

### Calculation Rules

- **Conversion rates** are ratios between consecutive funnel stages. For example, `impression_to_click_rate` = clicks / impressions. Round all rates to 4 decimal places.
- **Counts at each stage** are determined by the number of unique records in each cleaned CSV file. For breakdowns (by traffic source, device type, product category), count records from each respective file that match the dimension value. For `by_traffic_source` and `by_device_type`, use the `traffic_source`/`device_type` from `impressions.csv` and join through the funnel chain (impressions → clicks via `impression_id`, clicks → cart_additions via `click_id`, cart_additions → purchases via `cart_id`) to propagate these attributes downstream.
- **by_month**: Group by the month extracted from the `timestamp` column of each respective file. Keys must be in `YYYY-MM` format (e.g., `2023-10`).
- **overall_conversion_rate**: purchases / impressions, rounded to 4 decimal places.
- **bottleneck**: The funnel stage transition with the largest absolute drop in count. One of: `"impression_to_click"`, `"click_to_cart"`, `"cart_to_purchase"`. For example, if the biggest drop is from impressions to clicks, the value is `"impression_to_click"`.
- Only include traffic sources, device types, product categories, and months that appear in the cleaned data.
