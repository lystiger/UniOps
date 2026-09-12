# Product master

UniOps is the single owner of product identity. The Unigreen catalogue presents
UniOps products and never owns a SKU; EasyBooks is an accounting source and a
mapping target. The full cross-repository contract, including the Unigreen side,
migration and media boundary, is `Unigreen/docs/product-master-architecture.md`.

## What a canonical product is

| Field | Rule |
| --- | --- |
| `id` | UUID, immutable |
| `sku` | `UG` + six digits, allocated by UniOps, immutable, never reused |
| `name`, `unit`, `category` | Official values; editable by office/admin |
| `status` | `active` or `discontinued` (database check constraint) |
| `specifications` | Structured JSON for operational attributes (ply, weight, roll length…) |
| `code`, `easybooks_material_goods_id` | The EasyBooks mapping, written by the sync; unique |

A materially different sellable variant (ply, core/coreless, roll length,
dimensions, weight, units per pack or carton, material, pack configuration) is a
separate product with its own SKU. Wording, marketing copy, SEO and images are not.

## SKU allocation

`app.services.catalog.allocate_sku` increments the single row of
`product_sku_sequence` with one `UPDATE … RETURNING` inside the creating
transaction. On PostgreSQL that row lock serialises concurrent creations across
processes; a rolled-back creation returns its number, a committed one is never
handed out again. `products.sku` has no default, a unique constraint and a format
check, so a code path that does not allocate fails instead of inventing a SKU. There
is no delete route. Migration `c2e91a4b8701` backfilled existing products in
creation order and set the counter after the last one.

The EasyBooks sync allocates a SKU when it meets a product UniOps does not have,
and matches existing products by EasyBooks id or code, so a resync keeps every
SKU. It still overwrites `name` and `unit` from EasyBooks for linked products.

## API

| Route | Access |
| --- | --- |
| `GET /api/products?search=&category=&status=` | any signed-in user, or the catalogue service key |
| `GET /api/products/{id}` | same |
| `POST /api/products` | office/admin, or the catalogue service key; a `sku` field is rejected |
| `PATCH /api/products/{id}` | office/admin only; name, unit, category, status, specifications |

## Catalogue service key

`UNIOPS_CATALOG_SERVICE_KEY` (at least 32 characters, empty disables it). The
Unigreen backend sends it as `X-UniOps-Catalog-Key`. It is compared in constant
time and opens only the three routes marked above; it is not a user and cannot
edit a product or reach any other data. A wrong key gets
`401 CATALOG_SERVICE_KEY_INVALID`.

## Do not

- Do not synchronise products back from Unigreen, or push UniOps fields into
  Unigreen in the background. Authority flows one way; the only cross-system
  writes are the staff-initiated map and create requests described in the
  Unigreen document.
- Do not let any caller choose a SKU, and do not encode attributes in it.
