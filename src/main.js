// Look Up, Fin! — the site reads like the picture book itself.

// Everything you'll want to change before launch lives here.
const CONFIG = {
  status: "preorder", // "preorder" | "available"
  price: "$19.99", // keep it the same as Amazon
  shipNote: "Ships by December 15 · Free Shipping on 2+ copies", // once books are in hand: "Ships within 3 business days."
  deadline: "", // e.g. "Pre-orders close November 19." — empty hides the line
  shopUrl: "https://shop.lookupfin.com/cart/57894542016678:1?channel=buy_button", // Shopify checkout link: /cart/VARIANT_ID:QUANTITY
  maxQty: 5, // cap on the quantity picker; bigger orders email for a quote
  amazonUrl: "#", // Amazon listing
  instagramUrl: "https://www.instagram.com/emcostudios/", // @emcostudios
  contactEmail: "hello@lookupfin.com",
  // "Join the list" is collected by Netlify Forms: see the <form> in index.html.
};

// Fill in prices, links and button labels from CONFIG.
function applyConfig() {
  const preorder = CONFIG.status === "preorder";
  document.querySelectorAll("[data-buy-label]").forEach((el) => {
    // every buy button: "Preorder – $19.99" (or "Buy – $19.99" once books ship)
    el.textContent = el.dataset.buyLabel === "signed"
      ? `${preorder ? "Preorder" : "Buy"} a signed copy` // the title-page button
      : `${preorder ? "Preorder" : "Buy"} – ${CONFIG.price}`;
  });
  document.querySelectorAll("[data-price]").forEach((el) => (el.textContent = CONFIG.price));
  document.querySelectorAll("[data-ship]").forEach((el) => (el.textContent = CONFIG.shipNote));
  document.querySelectorAll("[data-deadline]").forEach((el) => {
    if (preorder && CONFIG.deadline) el.textContent = CONFIG.deadline;
    else el.remove();
  });
  setupQty(preorder);
  document.querySelectorAll("[data-bulk-max]").forEach((el) => (el.textContent = CONFIG.maxQty));
  document.querySelectorAll("[data-bulk-link]").forEach((el) => {
    el.href = `mailto:${CONFIG.contactEmail}?subject=${encodeURIComponent("Look Up, Fin! bulk order")}`;
    el.textContent = CONFIG.contactEmail;
  });
  // No listing yet → no Amazon link, so pre-orders stay here.
  document.querySelectorAll("[data-amazon]").forEach((el) => {
    if (CONFIG.amazonUrl === "#") el.remove();
    else el.href = CONFIG.amazonUrl;
  });
  document.querySelectorAll("[data-instagram]").forEach((el) => (el.href = CONFIG.instagramUrl));
  document.querySelectorAll("[data-contact]").forEach((el) => (el.href = `mailto:${CONFIG.contactEmail}`));
  document.querySelectorAll("[data-year]").forEach((el) => (el.textContent = new Date().getFullYear()));
}

// − / + picker beside the checkout button: updates the Shopify link and the button label.
function setupQty(preorder) {
  const picker = document.querySelector("[data-qty]");
  const buttons = document.querySelectorAll("[data-shop]");
  const unit = parseFloat(CONFIG.price.replace(/[^0-9.]/g, ""));
  const verb = preorder ? "Preorder" : "Buy";
  let qty = 1;
  const render = () => {
    const url = CONFIG.shopUrl.replace(/:(\d+)(?=\?|$)/, `:${qty}`);
    const total = `$${(unit * qty).toFixed(2)}`;
    buttons.forEach((el) => {
      el.href = url;
      el.textContent = qty === 1 ? `${verb} – ${CONFIG.price}` : `${verb} ${qty} – ${total}`;
    });
    if (!picker) return;
    picker.querySelector("[data-qty-num]").textContent = qty;
    picker.querySelector('[data-qty-step="-1"]').disabled = qty <= 1;
    picker.querySelector('[data-qty-step="1"]').disabled = qty >= CONFIG.maxQty;
    document.querySelectorAll("[data-bulk]").forEach((el) => el.classList.toggle("at-cap", qty >= CONFIG.maxQty));
  };
  picker?.querySelectorAll("[data-qty-step]").forEach((b) =>
    b.addEventListener("click", () => {
      qty = Math.min(CONFIG.maxQty, Math.max(1, qty + Number(b.dataset.qtyStep)));
      render();
    })
  );
  render();
}

// Add .in to .reveal elements as they scroll into view.
function revealOnScroll() {
  const revealer = new IntersectionObserver(
    (entries) =>
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          revealer.unobserve(e.target);
        }
      }),
    { threshold: 0.15 }
  );
  document.querySelectorAll(".reveal").forEach((el) => revealer.observe(el));
}

function setupSignup() {
  const form = document.querySelector("[data-signup]");
  if (!form) return;
  // Netlify Forms catches this (see the <form> in index.html). Sign-ups appear in
  // Netlify > Forms > launch-list; export the CSV and import it into Shopify > Customers.
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = form.querySelector(".signup-msg");
    const body = new URLSearchParams(new FormData(form)).toString();
    const local = ["localhost", "127.0.0.1"].includes(location.hostname);
    try {
      if (local) {
        console.log("Signup (only saved on the live Netlify site):", form.email.value);
      } else {
        const res = await fetch("/", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body,
        });
        if (!res.ok) throw new Error(res.status);
      }
      form.reset();
      msg.textContent = form.dataset.thanks || "You’re on the list. Thank you!";
    } catch {
      msg.textContent = "Something went wrong. Please try again.";
    }
  });
}

applyConfig();
revealOnScroll();
setupSignup();

// A hairline under the top bar once the page has scrolled.
const bar = document.querySelector(".bar");
const markScrolled = () => bar.classList.toggle("scrolled", scrollY > 8);
addEventListener("scroll", markScrolled, { passive: true });
markScrolled();
