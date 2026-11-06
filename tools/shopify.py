#!/usr/bin/env python3
"""Change the Look Up, Fin! Shopify store from the command line.

Reads SHOPIFY_STORE and SHOPIFY_ADMIN_TOKEN from the environment, or from
~/.config/lookupfin/shopify.env (one KEY=value per line). The token comes from
the "lookupfin-cli" custom app in Shopify's Dev Dashboard. Never commit it.

    python3 tools/shopify.py shop                      # who am I talking to
    python3 tools/shopify.py product                   # the book: id, price, stock, status
    python3 tools/shopify.py price 19.99               # set the price
    python3 tools/shopify.py stock 200                 # set available inventory
    python3 tools/shopify.py orders [--unfulfilled]    # recent orders
    python3 tools/shopify.py customers                 # recent customers
    python3 tools/shopify.py discounts                 # active discount codes
    python3 tools/shopify.py discount STORYTIME 20%    # new code, 20% off (or 5.00 for $5 off)
    python3 tools/shopify.py gql 'query { shop { name } }'   # anything else
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

API_VERSION = "2026-10"
PRODUCT_HANDLE = "look-up-fin"


def load_env():
    f = Path.home() / ".config/lookupfin/shopify.env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    store, token = os.environ.get("SHOPIFY_STORE"), os.environ.get("SHOPIFY_ADMIN_TOKEN")
    if not store or not token:
        sys.exit("Need SHOPIFY_STORE and SHOPIFY_ADMIN_TOKEN (env or ~/.config/lookupfin/shopify.env).")
    return store, token


def gql(query, variables=None):
    store, token = load_env()
    req = urllib.request.Request(
        f"https://{store}.myshopify.com/admin/api/{API_VERSION}/graphql.json",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": token},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if body.get("errors"):
        sys.exit("GraphQL errors: " + json.dumps(body["errors"], indent=2))
    return body["data"]


def check_user_errors(payload, key):
    errs = payload[key].get("userErrors") or []
    if errs:
        sys.exit(f"{key}: " + "; ".join(e["message"] for e in errs))


def product():
    d = gql(
        """query($h: String!) { productByHandle(handle: $h) {
          id title status totalInventory
          variants(first: 1) { nodes { id price inventoryItem { id } inventoryQuantity } } } }""",
        {"h": PRODUCT_HANDLE},
    )
    p = d["productByHandle"]
    if not p:
        sys.exit(f"No product with handle {PRODUCT_HANDLE}")
    return p


def cmd_shop(_):
    d = gql("query { shop { name myshopifyDomain primaryDomain { host } plan { displayName } currencyCode } }")
    print(json.dumps(d["shop"], indent=2))


def cmd_product(_):
    p = product()
    v = p["variants"]["nodes"][0]
    print(f"{p['title']}  {p['status']}\nvariant {v['id'].rsplit('/', 1)[1]}  price ${v['price']}  stock {v['inventoryQuantity']}")


def cmd_price(args):
    if not args:
        sys.exit("usage: price 19.99")
    p = product()
    v = p["variants"]["nodes"][0]
    d = gql(
        """mutation($pid: ID!, $vs: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $pid, variants: $vs) {
            productVariants { price } userErrors { message } } }""",
        {"pid": p["id"], "vs": [{"id": v["id"], "price": args[0]}]},
    )
    check_user_errors(d, "productVariantsBulkUpdate")
    print(f"price now ${d['productVariantsBulkUpdate']['productVariants'][0]['price']}")


def cmd_stock(args):
    if not args:
        sys.exit("usage: stock 200")
    p = product()
    item = p["variants"]["nodes"][0]["inventoryItem"]["id"]
    loc = gql("query { locations(first: 1) { nodes { id name } } }")["locations"]["nodes"][0]
    d = gql(
        """mutation($input: InventorySetQuantitiesInput!) {
          inventorySetQuantities(input: $input) { userErrors { message } } }""",
        {"input": {"name": "available", "reason": "correction", "ignoreCompareQuantity": True,
                   "quantities": [{"inventoryItemId": item, "locationId": loc["id"], "quantity": int(args[0])}]}},
    )
    check_user_errors(d, "inventorySetQuantities")
    print(f"stock now {args[0]} at {loc['name']}")


def cmd_orders(args):
    q = "fulfillment_status:unfulfilled" if "--unfulfilled" in args else ""
    d = gql(
        """query($q: String) { orders(first: 50, sortKey: CREATED_AT, reverse: true, query: $q) { nodes {
          name createdAt displayFinancialStatus displayFulfillmentStatus
          totalPriceSet { shopMoney { amount } }
          customer { displayName }
          shippingAddress { city provinceCode countryCodeV2 }
          lineItems(first: 5) { nodes { quantity title } } } } }""",
        {"q": q},
    )
    for o in d["orders"]["nodes"]:
        a = o["shippingAddress"] or {}
        qty = sum(li["quantity"] for li in o["lineItems"]["nodes"])
        print(f"{o['name']}  {o['createdAt'][:10]}  ${o['totalPriceSet']['shopMoney']['amount']:>6}  x{qty}  "
              f"{o['displayFinancialStatus']:<8} {o['displayFulfillmentStatus']:<12} "
              f"{(o['customer'] or {}).get('displayName', '')}  {a.get('city', '')}, {a.get('provinceCode', '')}")


def cmd_customers(_):
    d = gql("""query { customers(first: 50, sortKey: CREATED_AT, reverse: true) { nodes {
          displayName defaultEmailAddress { emailAddress } numberOfOrders amountSpent { amount } createdAt } } }""")
    for c in d["customers"]["nodes"]:
        e = (c["defaultEmailAddress"] or {}).get("emailAddress", "")
        print(f"{c['createdAt'][:10]}  {c['displayName']:<24} {e:<32} orders {c['numberOfOrders']}  ${c['amountSpent']['amount']}")


def cmd_discounts(_):
    d = gql("""query { codeDiscountNodes(first: 50, query: "status:active") { nodes { codeDiscount {
          ... on DiscountCodeBasic { title status usageLimit asyncUsageCount startsAt endsAt
            customerGets { value { ... on DiscountPercentage { percentage }
                                   ... on DiscountAmount { amount { amount } } } } } } } } }""")
    for n in d["codeDiscountNodes"]["nodes"]:
        c = n["codeDiscount"]
        if not c:
            continue
        v = c["customerGets"]["value"]
        off = f"{int(v['percentage'] * 100)}%" if "percentage" in v else f"${v['amount']['amount']}"
        print(f"{c['title']:<16} {off:>6} off  used {c['asyncUsageCount']}/{c['usageLimit'] or '∞'}  {c['status']}  ends {c['endsAt'] or 'never'}")


def cmd_discount(args):
    if len(args) < 2:
        sys.exit("usage: discount CODE 20%  |  discount CODE 5.00")
    code, amt = args[0].upper(), args[1]
    value = ({"percentage": float(amt.rstrip("%")) / 100} if amt.endswith("%")
             else {"discountAmount": {"amount": amt, "appliesOnEachItem": False}})
    d = gql(
        """mutation($d: DiscountCodeBasicInput!) { discountCodeBasicCreate(basicCodeDiscount: $d) {
          codeDiscountNode { id } userErrors { message } } }""",
        {"d": {"title": code, "code": code, "startsAt": "2020-01-01T00:00:00Z",
               "customerSelection": {"all": True},
               "customerGets": {"value": value, "items": {"all": True}},
               "appliesOncePerCustomer": False}},
    )
    check_user_errors(d, "discountCodeBasicCreate")
    print(f"created {code}: {amt} off everything, no end date, unlimited uses")


def cmd_gql(args):
    if not args:
        sys.exit("usage: gql 'query { ... }' ['{\"var\": 1}']")
    print(json.dumps(gql(args[0], json.loads(args[1]) if len(args) > 1 else None), indent=2))


COMMANDS = {
    "shop": cmd_shop, "product": cmd_product, "price": cmd_price, "stock": cmd_stock,
    "orders": cmd_orders, "customers": cmd_customers, "discounts": cmd_discounts,
    "discount": cmd_discount, "gql": cmd_gql,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
