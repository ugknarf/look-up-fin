# Look Up, Fin! — Shopify theme

The storefront at shop.lookupfin.com. One product, one page: the jacket flap from
lookupfin.com with the price and stock coming from Shopify, and the buy button
going straight to checkout.

The story and author pages stay on lookupfin.com (repo `ugknarf/look-up-fin`).
This theme links back there and loads its art and favicons from there, so every
image exists once.

## How it deploys

Shopify's GitHub integration watches `main`. Push, and the theme updates in the
store within a minute. No build step. (Shopify needs the theme at the repo root,
which is why this is its own repo instead of a folder in `look-up-fin`.)

## What Emily can change without code

Online Store > Themes > Customize > Theme settings:

- **The book:** product handle, Preorder/Available, shipping note, preorder
  deadline, signed sticker, max copies per order.
- **Links:** main site, Amazon listing, Instagram, contact email.

Price and sold-out state come from the product itself (Products > Look Up, Fin!).

## Files

- `layout/theme.liquid`: the page shell (top bar, footer) from lookupfin.com.
- `snippets/flap.liquid`: the buy flap. Used by the home page and the product page.
- `templates/cart.liquid`: bounces to checkout. Everything else bounces home.
- `assets/style.css`: lookupfin.com's stylesheet with art paths made absolute.
  When `src/style.css` changes in `look-up-fin`, copy it here and re-run the
  `sed` at the top of this file's "Shop-only" section (or just diff and paste).
- `assets/theme.js`: quantity picker and top-bar hairline.
