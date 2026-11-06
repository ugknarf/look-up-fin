# Look Up, Fin! — Shopify theme

The storefront at shop.lookupfin.com. One product, one page: the jacket flap from
lookupfin.com with the price and stock coming from Shopify, and the buy button
going straight to checkout.

The story and author pages stay on lookupfin.com in this repo.
This theme links back there and loads its art and favicons from there, so every
image exists once.

## How it deploys

    python3 tools/theme.py push            # upload shopify/ as an unpublished theme named after the branch
    python3 tools/theme.py list            # themes in the store, with preview links
    python3 tools/theme.py publish NAME    # make it live
    python3 tools/theme.py pull NAME       # bring Customize-editor edits back into git

Variants are branches. The first upload of a new theme name is a zip upload in
Online Store > Themes > Import; after that `push` replaces it in place.
Credentials: ~/.config/lookupfin/shopify.env (see tools/shopify.py).

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
