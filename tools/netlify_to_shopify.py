"""Convert a Netlify Forms export (launch-list) into a Shopify customer-import CSV.

Usage (from the site folder):
    python3 tools/netlify_to_shopify.py path/to/netlify-export.csv
Writes  <same folder>/shopify-import-<date>.csv  — upload it in Shopify > Customers > Import.
"""
import csv, sys, os, datetime

SHOPIFY_COLS = ["First Name", "Last Name", "Email", "Accepts Email Marketing", "Tags", "Note"]
TAGS = "newsletter, lookupfin-site"


def find(row, *names):
    low = {k.strip().lower(): v for k, v in row.items() if k}
    for n in names:
        if low.get(n):
            return low[n].strip()
    return ""


def main(src):
    with open(src, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    seen, out = set(), []
    for r in rows:
        email = find(r, "email", "e-mail", "email address").lower()
        if not email or "@" not in email or email in seen:
            continue
        seen.add(email)
        name = find(r, "name", "full name")
        first = find(r, "first name", "first_name") or (name.split(" ", 1)[0] if name else "")
        last = find(r, "last name", "last_name") or (name.split(" ", 1)[1] if " " in name else "")
        when = find(r, "created_at", "created at", "date")[:10]
        out.append({
            "First Name": first, "Last Name": last, "Email": email,
            "Accepts Email Marketing": "yes", "Tags": TAGS,
            "Note": f"Signed up on lookupfin.com{' ' + when if when else ''}",
        })
    dst = os.path.join(os.path.dirname(os.path.abspath(src)),
                       f"shopify-import-{datetime.date.today().isoformat()}.csv")
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHOPIFY_COLS)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} sign-ups -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1])
