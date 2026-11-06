// Look Up, Fin! shop — same behaviour as lookupfin.com, with prices from Shopify.

// − / + picker beside the checkout button: updates the cart link and the button label.
function setupQty() {
  const row = document.querySelector("[data-buy]");
  if (!row) return;
  const unit = Number(row.dataset.unit) / 100; // Shopify gives cents
  const max = Number(row.dataset.max) || 5;
  const verb = row.dataset.verb || "Buy";
  const money = (n) => `$${n.toFixed(2)}`;
  const picker = row.querySelector("[data-qty]");
  const buttons = document.querySelectorAll("[data-shop]");
  const bulk = document.querySelectorAll("[data-bulk]");
  let qty = 1;
  const render = () => {
    buttons.forEach((el) => {
      el.href = `/cart/${el.dataset.variant}:${qty}`;
      el.textContent = qty === 1 ? `${verb} – ${money(unit)}` : `${verb} ${qty} – ${money(unit * qty)}`;
    });
    picker.querySelector("[data-qty-num]").textContent = qty;
    picker.querySelector('[data-qty-step="-1"]').disabled = qty <= 1;
    picker.querySelector('[data-qty-step="1"]').disabled = qty >= max;
    bulk.forEach((el) => el.classList.toggle("at-cap", qty >= max));
  };
  picker.querySelectorAll("[data-qty-step]").forEach((b) =>
    b.addEventListener("click", () => {
      qty = Math.min(max, Math.max(1, qty + Number(b.dataset.qtyStep)));
      render();
    })
  );
  render();
}

// Top-bar pill mirrors the big button's verb.
function labelBar() {
  const row = document.querySelector("[data-buy]");
  document.querySelectorAll('[data-buy-label="short"]').forEach((el) => {
    el.textContent = row ? row.dataset.verb : "Buy";
  });
}

setupQty();
labelBar();

// A hairline under the top bar once the page has scrolled.
const bar = document.querySelector(".bar");
if (bar) {
  const markScrolled = () => bar.classList.toggle("scrolled", scrollY > 8);
  addEventListener("scroll", markScrolled, { passive: true });
  markScrolled();
}
