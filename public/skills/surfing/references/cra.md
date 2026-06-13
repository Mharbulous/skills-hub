# CRA — Canada Revenue Agency

Site-specific knowledge for interacting with CRA online services via browser automation.

## Table of Contents

1. [General — canada.ca pages](#general)
2. [My Account — individual](#my-account)
3. [My Business Account — adding and accessing](#my-business-account)
4. [Chat widget](#chat-widget)
5. [Navigation tips](#navigation-tips)

---

## General — canada.ca pages {#general}

**Timeout on navigation.** Pages on `canada.ca` frequently timeout when navigated to
directly, especially pages with cookie consent walls. If `navigate` times out:
- Retry once — sometimes it works on the second attempt
- If it keeps timing out, use `WebSearch` to find the information instead of loading
  the page directly
- The CRA My Account pages (on `apps5.ams-sga.cra-arc.gc.ca`) are a different domain
  and generally load fine once authenticated

**WebFetch is blocked.** The egress proxy blocks `www.canada.ca`, so `WebFetch` will
fail on CRA pages. Use `WebSearch` instead for looking up CRA contact info, forms, etc.

---

## My Account — individual {#my-account}

**URL pattern:** `apps5.ams-sga.cra-arc.gc.ca/gol-ged/mima/ngbeta/#/ind/...`

**Authentication:** Brahm must log in manually (credentials + 2FA). Claude handles
everything after authentication.

**User menu (top-right dropdown):** Click "BRAHM DORST" in the top-right corner to
reveal a dropdown with:
- Profile
- **View all accounts** — shows all linked accounts (individual, business, etc.)
- **+ Add account** — this is how you add a business account (see below)
- Sign out

**Key pages and their sidebar links:**
- Overview: `#/ind/overview`
- Tax returns: `#/ind/tax-returns` (left sidebar)
- Accounts and payments: `#/ind/accounting-summary`
- Submit documents: `#/ind/sdocs/home-history`
- Connect with us: `#/ind/communications/connectWithUs`
- Mail: `#/ind/communications/home` (shows correspondence, has a badge count)

**Balance info:** The "Accounts and payments" section shows the current income tax
balance on the overview page.

---

## My Business Account — adding and accessing {#my-business-account}

**CRITICAL DISCOVERY (2026-03-24):** The direct "My Business Account" registration
path is broken for this business number. It returns: *"This service cannot be used
for the specified taxpayer."*

**The path that works:**
1. Log into individual My Account
2. Click **BRAHM DORST** dropdown (top-right)
3. Click **"+ Add account"**
4. Select **"Business account"**
5. Select **"Add business number"** (not "Business Registration Online")
6. Enter the 9-digit business number (792054926 for BDLC)
7. Click Submit → **"Your business has been added successfully"**

This links the business to the individual CRA account through the unified sign-in
system. After adding, closing the dialog navigates directly into the business account
overview at `#/bus/overview`.

**URL pattern for business pages:** `apps5.ams-sga.cra-arc.gc.ca/gol-ged/mima/ngbeta/#/bus/...`

**Switching between accounts:** Use the top-right user dropdown → "View all accounts"
to switch between individual and business views.

---

## Chat widget {#chat-widget}

The "Chat with the CRA" widget is a **shadow DOM element** — standard `find`, `read_page`,
and coordinate-based clicks DO NOT WORK on its buttons.

### How to interact with the chat widget

**Finding the widget:**
```javascript
const chatWidget = document.querySelector('#onlinechatWidgetId');
const shadow = chatWidget.shadowRoot;
```

**Clicking buttons:**
```javascript
// Buttons are <button class="message-buttons"> with id = button text
const btn = shadow.querySelector('#Accounting\\ and\\ Balances');
btn.click();
```

**IMPORTANT — Old buttons persist in the DOM.** When the bot shows new options, the
old buttons remain. You must target the LAST matching button:
```javascript
const allButtons = shadow.querySelectorAll('button.message-buttons');
let lastBtn = null;
for (const btn of allButtons) {
  if (btn.textContent.trim() === 'Taxes and documents') {
    lastBtn = btn;
  }
}
lastBtn.click();
```

**Listing all current buttons:**
```javascript
const buttons = shadow.querySelectorAll('button.message-buttons');
const results = [];
for (const btn of buttons) {
  results.push({ text: btn.textContent?.trim(), id: btn.id });
}
JSON.stringify(results);
```

**Text input:** The textarea exists (`shadow.querySelector('textarea')`) but is
**hidden (0x0 dimensions)** when the bot is in guided-menu mode. Free-text input is
not available — you can only click the presented buttons.

**Closing the chat:**
```javascript
shadow.querySelector('#btn_endChat').click();
// Then confirm with the "End chat" button in the dialog that appears
```

**Other control buttons in the shadow DOM:**
- `#btn_endChat` — close/end chat
- `#btn_accessibility` — accessibility mode
- `#btn_fullScreenChat` — expand to full screen
- `#btn_minimizeChat` — collapse

### Limitations of the CRA chat

- **Virtual agent only.** There is no path to a live human agent through this chat.
  It's a guided menu bot with pre-set topic trees.
- **Individual account scope only.** The chat cannot help with My Business Account
  issues, GST/HST account problems, or business number registration.
- **No escalation.** If the menu options don't cover your question, there's no
  fallback — you'll just loop back to the topic menu.

---

## Navigation tips {#navigation-tips}

**Clicking sidebar links:** The left sidebar nav links sometimes don't respond to
coordinate clicks but work with ref-based clicks. Use `find` to locate the link,
then click by ref.

**Page loads:** CRA pages within My Account generally load quickly (1-2 seconds),
but give them 3 seconds after navigation before taking screenshots, especially
after form submissions.

**Session timeout:** CRA sessions timeout after ~20 minutes of inactivity. If pages
start showing errors or redirecting, Brahm needs to re-authenticate.
