#!/usr/bin/env python3
"""
Algerian family meal-planner generator — modern edition with week tabs.

Tuned to the family's real constraints:
  * Low effort: one real cooked meal a day (lunch). Breakfasts and dinners are
    no-cook or quick; snacks are batch-prepped by the non-cooking partner.
  * Modern over traditional: everyday halal meals from Algeria-available
    ingredients; heavy traditional dishes appear at most once a week (weekend).
  * Personal: reads preferences.json (favorites / dislikes / monthly caps /
    profiles). Dislikes removed; favorites recur; capped dishes (e.g. msemen
    once a month) are limited.

Design: modern product UI — Space Grotesk display + Inter body, cool palette,
custom line icons (no emoji). The four weeks render as interactive tabs
(Day 1-7, 8-14, 15-21, 22-28).

Usage:  python generate.py [--prefs PATH] [--out PATH] [--seed N]
"""

import argparse
import calendar
import datetime as _dt
import json
import os
import random
import sys

WD_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # date.weekday() order
FRI, SAT = 4, 5  # Algeria weekend; Friday = big lunch, Saturday = relaxed breakfast + leftovers
DEFAULT_CAPS = {"msemen": 1}  # max appearances across the whole month

# Dish tuple: (slug, name, kind, him_boost, her_boost, tags)
#   kind: "n" no-cook | "q" quick (<~25 min) | "p" prep-ahead | "t" traditional
#   tags: "trad" (weekend only), "fish", "leftover"

BREAKFASTS = [
    ("yogurt-bowl", "Yogurt bowl with oats, banana, honey &amp; nuts", "n", "add extra nuts", "calcium + energy", set()),
    ("eggs-cheese-toast", "Scrambled eggs with cheese on toast + tomato", "q", "add avocado", "", set()),
    ("avocado-egg-toast", "Avocado &amp; boiled egg on toast", "q", "drizzle olive oil", "", set()),
    ("overnight-oats", "Overnight oats with milk, dates &amp; peanut butter", "p", "bigger portion", "oats + iron", set()),
    ("smoothie-eggs", "Banana-oat-milk smoothie + 2 boiled eggs", "q", "add peanut butter", "", set()),
    ("turkey-sandwich", "Cheese &amp; turkey sandwich + fruit", "n", "", "", set()),
    ("cheese-tomato-toast", "Cheese toast with olive oil, olives &amp; tomato", "n", "", "", set()),
    ("baghrir", "Baghrir with honey &amp; butter, milk", "t", "add nut butter", "", {"trad"}),
    ("msemen", "Msemen with cheese &amp; honey", "t", "", "", {"trad"}),
]

LUNCHES = [
    # modern / quick — the everyday default
    ("chicken-pasta", "Chicken &amp; vegetable pasta", "q", "extra pasta + cheese", "", set()),
    ("tuna-pasta", "Tuna pasta with tomato sauce", "q", "", "omega-3", {"fish"}),
    ("chicken-rice-bowl", "Chicken &amp; vegetable rice bowl", "q", "bigger rice portion", "", set()),
    ("grilled-chicken-rice", "Grilled chicken with rice &amp; salad", "q", "extra rice + olive oil", "", set()),
    ("chicken-wrap", "Chicken shawarma-style wrap with salad", "q", "add fries on the side", "", set()),
    ("oven-tray-chicken", "Oven tray: chicken, potatoes &amp; peppers", "q", "extra potatoes", "", set()),
    ("mujadara", "Lentils &amp; rice (mujadara) with fried onion", "q", "", "iron + protein", set()),
    ("chickpea-stew", "Chickpea &amp; vegetable stew with bread", "q", "", "iron", set()),
    ("spaghetti-bolognese", "Spaghetti with beef bolognese", "q", "extra meat + cheese", "iron", set()),
    ("fried-rice", "Chicken &amp; egg fried rice with veg", "q", "bigger portion", "", set()),
    ("beef-burger", "Homemade beef burger with salad", "q", "add cheese + extra bun", "iron", set()),
    ("flatbread-pizza", "Flatbread pizza with cheese, tomato &amp; chicken", "q", "extra cheese", "", set()),
    ("kefta-rice", "Kefta (meatballs) in tomato sauce with rice", "q", "", "protein + iron", set()),
    ("fish-fillet-veg", "Pan-fried fish fillet with potatoes &amp; salad", "q", "", "omega-3", {"fish"}),
    ("shakshuka-merguez", "Shakshuka with merguez &amp; bread", "q", "extra bread + oil", "iron", set()),
    # traditional — weekend only, capped to once a week
    ("couscous", "Couscous with vegetables &amp; meat", "t", "extra semolina + chickpeas", "", {"trad"}),
    ("chorba-frik", "Chorba frik with bread", "t", "", "", {"trad"}),
    ("tajine-zitoun", "Tajine zitoun (chicken &amp; olives)", "t", "", "", {"trad"}),
    ("rechta", "Rechta with chicken", "t", "", "", {"trad"}),
    ("dolma", "Dolma (stuffed vegetables)", "t", "", "", {"trad"}),
    ("loubia", "Loubia (white bean stew) with bread", "t", "", "add spinach", {"trad"}),
]

# Dinners: mostly quick sandwiches / burgers; one leftover night a week.
DINNERS = [
    ("leftovers", "Leftovers from yesterday's lunch", "n", "", "", {"leftover"}),
    ("beef-burger-dinner", "Beef burger with salad", "q", "add cheese + extra bun", "iron", set()),
    ("chicken-sandwich", "Grilled chicken sandwich with salad", "q", "add fries", "", set()),
    ("merguez-sandwich", "Merguez sandwich with onions &amp; salad", "q", "", "iron", set()),
    ("shawarma-sandwich", "Chicken shawarma sandwich", "q", "add fries", "", set()),
    ("egg-cheese-sandwich", "Fried egg &amp; cheese sandwich", "q", "double the egg", "", set()),
    ("tuna-baguette", "Tuna baguette with veg", "n", "", "omega-3", {"fish"}),
    ("club-sandwich", "Chicken &amp; egg club sandwich", "q", "extra layer", "", set()),
    ("cheese-plate", "Cheese, olives, bread, tomato &amp; cucumber plate", "n", "add tuna or egg", "", set()),
    ("omelette-veg", "Cheese &amp; vegetable omelette with bread", "q", "", "", set()),
    ("shakshuka", "Shakshuka (eggs in tomato) with bread", "q", "", "", set()),
    ("veg-soup-batch", "Vegetable or lentil soup (from batch) + bread", "q", "", "iron + hydration", set()),
]

SNACKS = [
    "Energy balls (dates, oats, peanut butter) &mdash; prep a batch",
    "Hard-boiled eggs (batch) &middot; mixed nuts",
    "Yogurt pots with honey &amp; nuts",
    "Dates + almonds &middot; cheese",
    "Banana + peanut butter &middot; milk",
    "Cheese &amp; crackers &middot; fruit",
    "Dried figs + walnuts &middot; rayeb",
    "Apple slices + peanut butter &middot; yogurt",
    "Milk-date-banana smoothie &middot; nuts",
    "Hummus + veggie sticks &amp; bread",
]

WEEK_THEMES = [
    ("w1", "Easy &amp; modern", "One cooked meal a day"),
    ("w2", "Quick favourites", "Plus a weekend classic"),
    ("w3", "Light dinners", "Sandwiches &amp; fresh plates"),
    ("w4", "Flexible week", "Repeat what worked"),
]

KIND_TAG = {"n": ("No-cook", "n"), "q": ("Quick", "q"), "p": ("Prep ahead", "p"), "t": ("Weekend", "t")}

# ------------------------------- icons (inline SVG, no emoji) -------------------------------

def _svg(body):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + body + '</svg>')

IC_TARGET = _svg('<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.2"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>')
IC_CAL = _svg('<rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 9.5h17"/><path d="M8 3v3.4M16 3v3.4"/>')
IC_SNACK = _svg('<path d="M4 11.5h16a8 8 0 0 1-16 0Z"/><path d="M9 11.5c-.6-1.8.4-3 0-4.8M13 11.5c-.6-1.8.4-3 0-4.8"/><path d="M3 20h18"/>')
IC_IDEA = _svg('<path d="M9 17h6"/><path d="M10 20.5h4"/><path d="M12 3.5a6 6 0 0 1 4 10.4c-.7.6-1 1.2-1 2.1H9c0-.9-.3-1.5-1-2.1A6 6 0 0 1 12 3.5Z"/>')
IC_LOGO = ('<svg viewBox="0 0 44 44" fill="none" aria-hidden="true">'
           '<rect x="1.5" y="1.5" width="41" height="41" rx="13" fill="#0f766e"/>'
           '<path d="M16 13v10c0 1.6 1.2 2.4 2.6 2.4M19.2 13v18M16 13v5.5" stroke="#d6f5ee" stroke-width="1.8" stroke-linecap="round"/>'
           '<path d="M28 13c-2 0-3.4 2-3.4 5s1.4 4.4 3.4 4.4V31" stroke="#d6f5ee" stroke-width="1.8" stroke-linecap="round"/></svg>')
APP_ICON = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAAEWUlEQVR4nO3dO3LbSBSG0aZqcq/Hm3LodOxUoTY16/EKPMGUPHrwARANdN+f54SySmwIn68uKZV0apP68v3b79Fn4LJfzy+n0Wc4Z4pDiTfDDJEPO4CIs42K+9AHFfFjOjLuQx5IyLR2TNi7PoCQOWfPsHf5wEJmiT3Cfur9AcXMUnu00jVoMbNW72a6jHwh00OPFWTzhBYzvfRoaVPQYqa3rU3dHbSY2cuWtu4KWszs7d7GVgctZo5yT2urghYzR1vb3OKgxcwoa9pbFLSYGW1pg92/9Q0j3QzadGYWS1q8GrSYmc2tJi8GLWZmda1NOzRRzgZtOjO7S42a0ET5FLTpTBXnWjWhifIuaNOZaj42a0ITRdBE+RO0dYOq3rZrQhNF0ER5as26QX2vDZvQRBE0UQRNFEET5eQJIUlMaKL8NfoA7Oefv39c/LevPy//W2VWjkDXQv4oLeySQb+9YUtuyN7vP4s1IX9U6TqvKbdDf7xpt27i3u8/i63nrHKdt5QK+tInfdTbZ9HrfLNf5xKlguaz3hFWj1rQhe0VX+WoBU0UQRe19xStOqUFXdBRsVWMWtBEEXQxR0/NalNa0EQRNFEEXcioL/+V1g5BE0XQRBE0UQRdxOg9dvTjLyVoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCLmL0r+oa/fhLCZoogiZKzO+HXvvTYFV+eox1TOhCRu2xVfbn1gRNGEETRdDFHP3lv9K60VqxoO2Q3FIq6NZMqNaOO9OM135LuaBbc0Nb2/9sM1/7NWVfh379hO/xenLVm0nRP+u21CP84Un/od8ruXLwv97xVY65NUFH6BVh9ZhbE3SMrTEmxNxa4SeFfHbPE+WUkF8JOtCSsNNCfmXlIIqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKIImiqCJImiiCJoogiaKoIkiaKIImiiCJoqgiSJoogiaKNFBf/35Y9Xb0zzi9UcH3drnm5d8M895tOs/ffn+7ffoQ0AvT7+eX06jDwE9/Hp+OcWvHDwWQRNF0EQRNFGeWvtvmR59ENjitWETmiiCJsqfoK0dVPW2XROaKIImyrugrR1U87FZE5oon4I2paniXKsmNFHOBm1KM7tLjZrQRLkYtCnNrK61eXVCi5rZ3Gry5sohamaxpEU7NFEWBW1KM9rSBhdPaFEzypr2Vq0couZoa5tbvUOLmqPc09pdTwpFzd7ubezuVzlEzV62tLXpZTtR09vWpja/Di1qeunRUtcY/SZT7tFzKHb9TqFpzVq9m+n+rW9Rs9QerewanxWEc/YceodMU2HT2jFfvQ9dD4T9mI5cQ4ftu+LONuq51BRP4MSdYYYXBIYf4BKRz22GeM/5F77GXX4ZijheAAAAAElFTkSuQmCC"



# ------------------------------- preferences -------------------------------

def _matches(slug, name, term):
    t = term.strip().lower()
    return bool(t) and (t in slug.lower() or t in name.lower())


def filt(pool, dislikes, include_fish):
    out = []
    for d in pool:
        slug, name, kind, him, her, tags = d
        if any(_matches(slug, name, term) for term in dislikes):
            continue
        if "fish" in tags and not include_fish:
            continue
        out.append(d)
    return out


def split_trad(pool):
    return ([d for d in pool if "trad" in d[5]], [d for d in pool if "trad" not in d[5]])


def fav_order(lst, favorites):
    favs = [d for d in lst if any(_matches(d[0], d[1], f) for f in favorites)]
    return favs, [d for d in lst if d not in favs]


class Rotor:
    def __init__(self, lst, favorites, rng):
        self.favs, self.rest = fav_order(lst, favorites)
        self.rng = rng
        self.queue = []

    def _refill(self):
        cyc = list(self.rest)
        self.rng.shuffle(cyc)
        self.queue = list(self.favs) + cyc

    def empty(self):
        return not self.favs and not self.rest

    def next(self, avoid=frozenset()):
        if self.empty():
            return None
        for _ in range(5):
            if not self.queue:
                self._refill()
            for i, d in enumerate(self.queue):
                if d[0] not in avoid:
                    return self.queue.pop(i)
            self._refill()
        return self.queue.pop(0) if self.queue else None


def capped_next(rotor, avoid, caps, counts):
    blocked = set(avoid)
    for _ in range(12):
        d = rotor.next(avoid=blocked)
        if d is None:
            return None
        slug = d[0]
        if slug in caps and counts.get(slug, 0) >= caps[slug]:
            blocked.add(slug)
            continue
        counts[slug] = counts.get(slug, 0) + 1
        return d
    return None


# ------------------------------- nutrition -------------------------------

def targets_for(member):
    role = member.get("role", "")
    name = member.get("name", "Family member")
    if role == "weight_gain":
        h, w = member.get("height_cm", 175), member.get("weight_kg", 73)
        age = member.get("age", 32)
        s = 5 if member.get("sex", "male") == "male" else -161
        bmr = 10 * w + 6.25 * h - 5 * age + s
        act = {"sedentary": 1.3, "light": 1.5, "moderate": 1.65, "active": 1.8}.get(member.get("activity", "light"), 1.5)
        kcal = round((bmr * act + 400) / 50) * 50
        return {"name": "Healthy weight gain", "eyebrow": "Daily goal", "css": "him",
                "kcal": f"{kcal:,}", "unit": "kcal / day", "prot": f"{round(1.6*w)}–{round(1.9*w)} g protein",
                "points": ["Aim for a gentle <strong>+0.25–0.5 kg/week</strong>",
                           "Hit calories through snacks &mdash; your job to prep",
                           "Add olive oil, nuts, dates, full-fat dairy &amp; eggs",
                           "Strength training 3&times;/week builds muscle, not just fat"]}
    if role == "breastfeeding":
        return {"name": "Breastfeeding", "eyebrow": "Daily goal", "css": "her",
                "kcal": "2,300–2,500", "unit": "kcal / day", "prot": "75–90 g protein",
                "points": ["Eat to appetite &mdash; nursing burns ~450–500 extra kcal",
                           "Keep water + a prepped snack where you feed (~2.5–3 L fluids)",
                           "Iron, calcium &amp; omega-3 at most meals",
                           "No-cook breakfasts &amp; dinners by design"]}
    return {"name": "Balanced eating", "eyebrow": "Daily goal", "css": "",
            "kcal": "2,000–2,400", "unit": "kcal / day", "prot": "0.8–1.2 g/kg",
            "points": ["Protein at every meal", "Vegetables at lunch", "Stay hydrated", "Whole grains + healthy fats"]}


# ------------------------------- rendering -------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;450;500;600;700&display=swap');
:root{
  --bg:#eef2f6;--surface:#ffffff;--surface-2:#f8fafc;--ink:#0f172a;--muted:#64748b;--faint:#94a3b8;
  --line:#e6ebf1;--line-strong:#d6dee7;
  --brand:#0d9488;--brand-d:#0f766e;--brand-bg:#d6f3ef;
  --him:#2563eb;--himbg:#e5edff;--her:#db2777;--herbg:#fce7f1;
  --c1:#0d9488;--c2:#2563eb;--c3:#7c3aed;--c4:#db2777;
  --shadow:0 1px 2px rgba(15,23,42,.04),0 10px 26px rgba(15,23,42,.06);
  --radius:16px;
}
*{box-sizing:border-box;}
body{margin:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:var(--ink);
  line-height:1.55;background:
    radial-gradient(900px 320px at 100% -8%, #e2ecfb 0, transparent 60%),
    radial-gradient(760px 300px at -5% 4%, #d8f3ee 0, transparent 55%),
    var(--bg);-webkit-font-smoothing:antialiased;}
.wrap{max-width:1060px;margin:0 auto;padding:28px 24px 96px;}
.disp{font-family:'Space Grotesk',sans-serif;}

/* ---------- header ---------- */
header.hero{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:22px 30px 20px;box-shadow:var(--shadow);}
.brandrow{display:flex;align-items:center;gap:11px;margin-bottom:12px;}
.brandrow svg{width:32px;height:32px;}
.brandrow .bn{font-family:'Space Grotesk',sans-serif;font-weight:600;letter-spacing:.16em;text-transform:uppercase;font-size:.7rem;color:var(--muted);}
.brandrow .bn b{color:var(--ink);}
h1.title{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1.7rem;line-height:1.12;margin:0;letter-spacing:-.02em;}
.lede{margin:8px 0 0;color:var(--muted);font-size:.92rem;max-width:64ch;}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;}
.chip{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-strong);background:var(--surface-2);border-radius:10px;padding:6px 12px;font-size:.8rem;color:var(--muted);}
.chip b{color:var(--ink);font-weight:600;}
.chip .sw{width:7px;height:7px;border-radius:50%;}

/* ---------- sections ---------- */
h2.section{display:flex;align-items:center;gap:11px;margin:52px 0 18px;font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1.4rem;letter-spacing:-.01em;}
h2.section svg{width:21px;height:21px;color:var(--brand);flex:none;}
h2.section .rule{flex:1;height:1px;background:var(--line-strong);margin-left:4px;}

/* ---------- cards ---------- */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:16px;}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:22px 24px;box-shadow:var(--shadow);}
.card .eyebrow{font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;color:var(--faint);font-weight:600;}
.card .name{font-family:'Space Grotesk',sans-serif;font-size:1.14rem;font-weight:600;margin:4px 0 0;}
.card.him{border-top:3px solid var(--him);}.card.her{border-top:3px solid var(--her);}
.stat{display:flex;align-items:baseline;gap:8px;margin:16px 0 2px;}
.stat .num{font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:600;line-height:1;letter-spacing:-.02em;}
.him .stat .num{color:var(--him);}.her .stat .num{color:var(--her);}
.stat .unit{font-size:.82rem;color:var(--muted);}
.protein{font-size:.9rem;color:var(--muted);font-weight:500;}
.card ul{margin:14px 0 0;padding:0;list-style:none;}
.card ul li{position:relative;padding-left:18px;margin:7px 0;font-size:.9rem;color:var(--muted);}
.card ul li::before{content:"";position:absolute;left:0;top:.58em;width:6px;height:6px;border-radius:2px;background:var(--brand);}

/* ---------- legend ---------- */
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;margin:-6px 2px 14px;}
.legend .lg{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);font-weight:600;}
.tag{display:inline-block;font-size:.68rem;font-weight:600;letter-spacing:.02em;padding:3px 9px;border-radius:6px;}
.tag.q{background:#dcfce7;color:#15803d;}
.tag.t{background:#fef3c7;color:#b45309;}
.tag.n{background:#e0f2fe;color:#0369a1;}
.tag.p{background:#ede9fe;color:#6d28d9;}
.lkey{display:inline-flex;align-items:center;gap:6px;font-size:.78rem;color:var(--faint);}
.lkey .sw{width:8px;height:8px;border-radius:50%;}

/* ---------- quick access ---------- */
.quickbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:18px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 18px;box-shadow:var(--shadow);}
.quickbar .ql{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);font-weight:600;margin-right:2px;}
.qa{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:.92rem;border:1px solid var(--line-strong);background:var(--surface-2);color:var(--ink);border-radius:10px;padding:9px 16px;cursor:pointer;transition:.15s;display:inline-flex;align-items:center;gap:8px;white-space:nowrap;}
.qa:hover{border-color:var(--brand);color:var(--brand-d);}
.qa .arr{transition:.15s;}.qa:hover .arr{transform:translateX(2px);}
.qa.qa-primary{background:var(--ink);color:#fff;border-color:var(--ink);}
.qa.qa-primary:hover{background:#000;color:#fff;}
.qa .qd{font-weight:500;font-size:.8rem;color:var(--faint);}
.qa.qa-primary .qd{color:#9fb0c2;}

.spotlight{margin-top:14px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;animation:spin .2s ease;}
@keyframes spin{from{opacity:0;transform:translateY(-4px);}to{opacity:1;transform:none;}}
.sp-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 20px;border-bottom:1px solid var(--line);background:linear-gradient(90deg,var(--brand-bg),transparent);}
.sp-head .sp-when{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1.08rem;}
.sp-head .sp-when small{display:block;font-family:'Inter',sans-serif;font-weight:500;font-size:.78rem;color:var(--muted);margin-top:1px;letter-spacing:.02em;}
.sp-close{border:0;background:transparent;font-size:1.4rem;line-height:1;color:var(--faint);cursor:pointer;padding:2px 6px;border-radius:8px;}
.sp-close:hover{background:var(--surface-2);color:var(--ink);}
.sp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1px;background:var(--line);}
.sp-meal{background:var(--surface);padding:15px 18px;}
.sp-meal h5{margin:0 0 6px;font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);font-weight:600;}
.sp-meal .sp-body{font-size:.9rem;}
.sp-meal .sp-body strong{font-weight:550;}
.sp-note{padding:14px 20px;font-size:.88rem;color:var(--muted);}

/* ---------- tabs ---------- */
.tabs{display:flex;gap:6px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:6px;box-shadow:var(--shadow);overflow-x:auto;margin-top:6px;}
.tab{flex:1;min-width:120px;border:0;background:transparent;cursor:pointer;border-radius:10px;padding:11px 14px;text-align:left;color:var(--muted);transition:.15s;font-family:inherit;}
.tab:hover{background:var(--surface-2);}
.tab .tnum{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:.98rem;color:var(--ink);display:block;letter-spacing:-.01em;}
.tab .tsub{font-size:.74rem;color:var(--faint);display:block;margin-top:1px;white-space:nowrap;}
.tab.active{background:var(--ink);}
.tab.active .tnum{color:#fff;}.tab.active .tsub{color:#aeb9c7;}
.tab .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:middle;}
.tab.active .dot{outline:2px solid rgba(255,255,255,.35);}

.panel{display:none;margin-top:16px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;}
.panel.active{display:block;}
.panel-head{display:flex;align-items:center;gap:12px;padding:18px 22px;border-bottom:1px solid var(--line);}
.panel-head .pn{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1.1rem;}
.panel-head .ps{font-size:.85rem;color:var(--muted);}
.panel-head .pbar{flex:none;width:6px;height:30px;border-radius:4px;}
.tbl-scroll{overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:.875rem;}
th,td{text-align:left;vertical-align:top;padding:13px 16px;border-bottom:1px solid var(--line);}
tr:last-child td{border-bottom:none;}
thead th{font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);font-weight:600;background:var(--surface-2);}
thead th .sub{font-weight:500;text-transform:none;letter-spacing:0;color:var(--faint);}
tbody tr:nth-child(even){background:#fbfcfe;}
tbody tr.today{background:var(--brand-bg)!important;box-shadow:inset 3px 0 0 var(--brand-d);}
tbody tr.today td.day .dn{color:var(--brand-d);}
.todaytag{display:inline-block;margin-top:3px;font-family:'Inter',sans-serif;font-size:.6rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#fff;background:var(--brand-d);border-radius:5px;padding:2px 6px;}
.tab.iscur .tnum::after{content:"Now";font-family:'Inter',sans-serif;font-size:.58rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--brand-d);background:var(--brand-bg);border-radius:5px;padding:1px 5px;margin-left:7px;vertical-align:middle;}
.tab.active.iscur .tnum::after{color:#0b3b35;background:#7fe6d6;}
td.day{white-space:nowrap;}
td.day .dn{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1.02rem;color:var(--ink);}
td.day .dw{display:block;font-size:.72rem;color:var(--faint);text-transform:uppercase;letter-spacing:.06em;margin-top:1px;}
.meal strong{font-weight:550;color:var(--ink);}
.meal .tag{margin-left:6px;vertical-align:middle;}
.boost{display:inline-flex;align-items:center;gap:6px;margin-top:5px;font-size:.78rem;font-weight:500;}
.boost::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;flex:none;}
.boost.him{color:var(--him);}.boost.her{color:var(--her);}
.boost-wrap{display:flex;flex-direction:column;gap:2px;}

/* ---------- tips ---------- */
.tips{display:grid;grid-template-columns:repeat(auto-fit,minmax(258px,1fr));gap:16px;}
.tip{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:var(--shadow);}
.tip h4{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:1rem;margin:0 0 6px;}
.tip p{margin:0;font-size:.9rem;color:var(--muted);}

footer{margin-top:52px;padding-top:22px;border-top:1px solid var(--line-strong);text-align:center;color:var(--faint);font-size:.8rem;line-height:1.7;}
footer .bsaha{font-family:'Space Grotesk',sans-serif;color:var(--muted);font-size:.92rem;font-weight:500;}
@media print{
  body{background:#fff;}.wrap{max-width:none;padding:0;}
  .card,.panel,.tip,header.hero,.legend,.tabs{box-shadow:none;}
  .tabs,.quickbar,.spotlight{display:none;}.panel{display:block!important;page-break-inside:avoid;margin-top:14px;}
}

/* ===================== MOBILE-FIRST (small screens are a first-class layout) ===================== */
@media(max-width:680px){
  .wrap{padding:16px 12px 72px;}
  header.hero{padding:18px 18px 16px;border-radius:14px;}
  .brandrow{margin-bottom:10px;}
  h1.title{font-size:1.45rem;}
  .lede{font-size:.9rem;margin-top:6px;}
  .meta{margin-top:12px;gap:6px;}
  .chip{font-size:.76rem;padding:5px 10px;}
  h2.section{margin:32px 0 12px;font-size:1.2rem;}

  /* Quick access: big thumb-friendly buttons */
  .quickbar{padding:12px;gap:8px;margin-top:14px;}
  .quickbar .ql{flex-basis:100%;margin:0 0 2px;}
  .qa{flex:1 1 0;justify-content:center;padding:14px 10px;font-size:.95rem;border-radius:12px;}

  /* Tabs: horizontal swipe strip with snap */
  .tabs{gap:5px;padding:5px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;}
  .tab{min-width:46%;scroll-snap-align:start;padding:10px 12px;}

  /* Day tables -> stacked cards */
  .panel{border-radius:14px;}
  .panel-head{padding:14px 16px;}
  .tbl-scroll{overflow:visible;}
  table,thead,tbody,tr,td{display:block;width:100%;}
  thead{display:none;}
  tbody tr{background:var(--surface)!important;border-bottom:7px solid var(--bg);padding-bottom:8px;}
  tbody tr:last-child{border-bottom:none;}
  tbody tr.today{background:var(--brand-bg)!important;box-shadow:inset 4px 0 0 var(--brand-d);}
  td{border:none!important;padding:7px 16px;display:flex;align-items:flex-start;gap:12px;font-size:.92rem;}
  td::before{content:attr(data-label);flex:0 0 76px;font-size:.6rem;line-height:1.5;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);font-weight:700;padding-top:3px;}
  td .mc{flex:1 1 auto;min-width:0;}
  td.day{display:flex;align-items:baseline;gap:8px;padding:12px 16px 8px;border-bottom:1px solid var(--line)!important;margin-bottom:4px;background:var(--surface-2)!important;}
  tbody tr.today td.day{background:transparent!important;}
  td.day::before{display:none;}
  td.day .dn{font-size:1.15rem;}
  td.day .dw{display:inline;margin:0;}
  .meal .tag{margin-left:0;}
  .meal strong{display:inline-block;margin-bottom:2px;}

  /* Spotlight + cards stack to one column */
  .sp-grid{grid-template-columns:1fr;}
  .sp-head{padding:14px 16px;}
  .cards{grid-template-columns:1fr;}
  .legend{gap:6px 14px;margin:-2px 2px 12px;}
  .tips{grid-template-columns:1fr;}
}
@media(max-width:380px){
  .tab{min-width:60%;}
  td::before{flex-basis:64px;}
}
"""

PANEL_COLORS = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)"]


def render_meal(dish):
    if dish is None:
        return "<em style='color:var(--faint)'>(add more dishes)</em>"
    slug, name, kind, him, her, tags = dish
    label, cls = KIND_TAG.get(kind, ("Quick", "q"))
    html = f'<strong>{name}</strong> <span class="tag {cls}">{label}</span>'
    boosts = ""
    if him:
        boosts += f'<span class="boost him">Gain &middot; {him}</span>'
    if her:
        boosts += f'<span class="boost her">Nursing &middot; {her}</span>'
    if boosts:
        html += f'<div class="boost-wrap">{boosts}</div>'
    return html


def render_panel(w, title, sub, rows_data, start, end):
    """rows_data: list of (day_number, weekday_name, b, l, d, snack)."""
    color = PANEL_COLORS[w]
    rows = ""
    for (dnum, wname, b, l, d, snack) in rows_data:
        rows += (f'<tr data-day="{dnum}"><td class="day"><span class="dn">{dnum}</span><span class="dw">{wname}</span></td>'
                 f'<td class="meal" data-label="Breakfast"><div class="mc">{render_meal(b)}</div></td>'
                 f'<td class="meal" data-label="Lunch"><div class="mc">{render_meal(l)}</div></td>'
                 f'<td class="meal" data-label="Dinner"><div class="mc">{render_meal(d)}</div></td>'
                 f'<td class="meal" data-label="Snacks"><div class="mc">{snack}</div></td></tr>\n')
    active = " active" if w == 0 else ""
    return f"""
  <div class="panel{active}" id="panel-{w}">
    <div class="panel-head">
      <span class="pbar" style="background:{color}"></span>
      <div><div class="pn">{title}</div><div class="ps">Days {start}&ndash;{end} &middot; {sub}</div></div>
    </div>
    <div class="tbl-scroll"><table>
      <thead><tr><th>Day</th><th>Breakfast</th><th>Lunch <span class="sub">(the cook)</span></th><th>Dinner</th><th>Snacks</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </div>"""


def render_tabbar(week_meta):
    """week_meta: list of (title, sub, start, end)."""
    btns = ""
    for w, (title, sub, start, end) in enumerate(week_meta):
        color = PANEL_COLORS[w]
        active = " active" if w == 0 else ""
        btns += (f'<button class="tab{active}" data-w="{w}" data-start="{start}" data-end="{end}">'
                 f'<span class="tnum"><span class="dot" style="background:{color}"></span>Day {start}&ndash;{end}</span>'
                 f'<span class="tsub">{title}</span></button>')
    return f'<div class="tabs" role="tablist">{btns}</div>'


def render_card(t):
    pts = "".join(f"<li>{p}</li>" for p in t["points"])
    cls = f" {t['css']}" if t["css"] else ""
    return f"""
    <div class="card{cls}">
      <div class="eyebrow">{t['eyebrow']}</div>
      <div class="name">{t['name']}</div>
      <div class="stat"><span class="num">{t['kcal']}</span><span class="unit">{t['unit']}</span></div>
      <div class="protein">{t['prot']}</div>
      <ul>{pts}</ul>
    </div>"""


def section(icon, title):
    return f'<h2 class="section">{icon}<span>{title}</span><span class="rule"></span></h2>'


TAB_JS = """
<script>
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tab'));
  var panels=[].slice.call(document.querySelectorAll('.panel'));
  function activate(w){
    tabs.forEach(function(t){t.classList.toggle('active',t.dataset.w===String(w));});
    panels.forEach(function(p){p.classList.toggle('active',p.id==='panel-'+w);});
  }
  tabs.forEach(function(t){t.addEventListener('click',function(){activate(t.dataset.w);});});

  var WD=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var MO=['January','February','March','April','May','June','July','August','September','October','November','December'];
  var qb=document.getElementById('quickbar');
  var planY=qb?+qb.dataset.year:0, planM=qb?+qb.dataset.month:0;  // JS month 0-11

  function tabFor(dom){
    return tabs.filter(function(t){return dom>=+t.dataset.start && dom<=+t.dataset.end;})[0];
  }

  // Auto-select the current week of the month and highlight today's row.
  var dom = new Date().getDate();
  var curTab = tabFor(dom) || tabs[tabs.length-1];
  if(curTab){ curTab.classList.add('iscur'); activate(curTab.dataset.w); }
  var trow = document.querySelector('tr[data-day="'+dom+'"]');
  if(trow){
    trow.classList.add('today');
    var dc = trow.querySelector('td.day');
    if(dc){ dc.insertAdjacentHTML('beforeend','<span class="todaytag">Today</span>'); }
  }

  // ---- Quick access: Today / Tomorrow ----
  var spot=document.getElementById('spotlight');
  var MEALS=['Breakfast','Lunch','Dinner','Snacks'];
  function showSpot(label, dateObj){
    if(!spot) return;
    var sameMonth = (dateObj.getMonth()===planM && dateObj.getFullYear()===planY);
    var wd=WD[dateObj.getDay()], dnum=dateObj.getDate(), mon=MO[dateObj.getMonth()];
    var head='<div class="sp-head"><div class="sp-when">'+label+
             '<small>'+wd+', '+dnum+' '+mon+'</small></div>'+
             '<button class="sp-close" aria-label="Close">&times;</button></div>';
    var body;
    if(sameMonth){
      var row=document.querySelector('tr[data-day="'+dnum+'"]');
      if(row){
        var cells=row.querySelectorAll('td');
        var g='';
        for(var i=0;i<4;i++){
          g+='<div class="sp-meal"><h5>'+MEALS[i]+'</h5><div class="sp-body">'+cells[i+1].innerHTML+'</div></div>';
        }
        body='<div class="sp-grid">'+g+'</div>';
        var tb=tabFor(dnum); if(tb) activate(tb.dataset.w);
      } else { body='<div class="sp-note">No plan row for that day.</div>'; }
    } else {
      body='<div class="sp-note">That date is in '+MO[dateObj.getMonth()]+
           ', outside this month\\'s plan. Ask me to regenerate the planner for the new month.</div>';
    }
    spot.innerHTML=head+body;
    spot.hidden=false;
    spot.querySelector('.sp-close').addEventListener('click',function(){spot.hidden=true;});
    spot.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  var bToday=document.getElementById('qa-today');
  var bTom=document.getElementById('qa-tomorrow');
  if(bToday) bToday.addEventListener('click',function(){showSpot('Today', new Date());});
  if(bTom) bTom.addEventListener('click',function(){var d=new Date();d.setDate(d.getDate()+1);showSpot('Tomorrow', d);});

  // Auto-open: in the morning show Today's plan; in the evening/night show Tomorrow's.
  var hr=new Date().getHours();
  if(hr>=18 || hr<5){ var dt=new Date(); dt.setDate(dt.getDate()+1); showSpot('Tomorrow', dt); }
  else { showSpot('Today', new Date()); }
})();
</script>
"""


def build_html(prefs, rng):
    dislikes = prefs.get("dislikes", [])
    favorites = prefs.get("favorites", [])
    include_fish = prefs.get("diet", {}).get("include_fish", True)
    caps = dict(DEFAULT_CAPS)
    caps.update(prefs.get("monthly_caps", {}))
    counts = {}

    bf_trad, bf_mod = split_trad(filt(BREAKFASTS, dislikes, include_fish))
    l_trad, l_mod = split_trad(filt(LUNCHES, dislikes, include_fish))
    dinners = filt(DINNERS, dislikes, include_fish)
    leftover = next((d for d in dinners if "leftover" in d[5]), None)
    easy_dinners = [d for d in dinners if "leftover" not in d[5]]

    bf_mod_r, bf_trad_r = Rotor(bf_mod or bf_trad, favorites, rng), Rotor(bf_trad, favorites, rng)
    l_mod_r, l_trad_r = Rotor(l_mod or l_trad, favorites, rng), Rotor(l_trad, favorites, rng)
    din_r = Rotor(easy_dinners, favorites, rng)

    # ---- map the real current month onto 4 tabs (week 4 absorbs days 29-31) ----
    today = _dt.date.today()
    num_days = calendar.monthrange(today.year, today.month)[1]
    groups = [[], [], [], []]
    for dom in range(1, num_days + 1):
        wd = _dt.date(today.year, today.month, dom).weekday()
        groups[min(3, (dom - 1) // 7)].append((dom, wd, WD_NAMES[wd]))

    snacks_seq = []
    while len(snacks_seq) < num_days:
        c = list(SNACKS); rng.shuffle(c); snacks_seq.extend(c)

    panels_html = ""
    week_meta = []
    snack_i = 0
    for w in range(4):
        _, title, sub = WEEK_THEMES[w]
        group = groups[w]
        start, end = group[0][0], group[-1][0]
        week_meta.append((title, sub, start, end))
        rows_data = []
        avoid_b, avoid_l = set(), set()
        for (dom, wd, wname) in group:
            # Friday = the big traditional lunch; Saturday = relaxed breakfast + leftover dinner
            if wd == SAT and not bf_trad_r.empty():
                bi = capped_next(bf_trad_r, set(), caps, counts) or capped_next(bf_mod_r, avoid_b, caps, counts)
            else:
                bi = capped_next(bf_mod_r, avoid_b, caps, counts)
            if wd == FRI and not l_trad_r.empty():
                li = capped_next(l_trad_r, set(), caps, counts) or capped_next(l_mod_r, avoid_l, caps, counts)
            else:
                li = capped_next(l_mod_r, avoid_l, caps, counts)
            di = leftover if (wd == SAT and leftover is not None) else capped_next(din_r, set(), caps, counts)
            rows_data.append((dom, wname, bi, li, di, snacks_seq[snack_i]))
            snack_i += 1
            if bi:
                avoid_b.add(bi[0])
            if li:
                avoid_l.add(li[0])
        panels_html += render_panel(w, title, sub, rows_data, start, end)

    tabbar = render_tabbar(week_meta)

    quickbar = (
        f'<div class="quickbar" id="quickbar" data-year="{today.year}" data-month="{today.month - 1}">'
        '<span class="ql">Quick access</span>'
        '<button class="qa qa-primary" id="qa-today">Today <span class="arr">&rsaquo;</span></button>'
        '<button class="qa" id="qa-tomorrow">Tomorrow <span class="arr">&rsaquo;</span></button>'
        '</div>\n  <div class="spotlight" id="spotlight" hidden></div>'
    )

    cards = "".join(render_card(targets_for(m)) for m in prefs.get("members", []))
    cards += """
    <div class="card">
      <div class="eyebrow">The system</div>
      <div class="name">Low effort by design</div>
      <ul style="margin-top:14px;">
        <li><strong>One real cook a day</strong> &mdash; lunch; make a little extra</li>
        <li><strong>Breakfast &amp; dinner</strong> are no-cook or quick sandwiches</li>
        <li><strong>The non-cook preps snacks</strong> in weekend batches</li>
        <li><strong>Mostly modern</strong> halal meals; Friday is the weekend classic</li>
        <li><strong>Saturday</strong> = relaxed breakfast + leftover dinner</li>
      </ul>
    </div>"""

    fav_txt = ", ".join(favorites) if favorites else "none yet"
    dis_txt = ", ".join(dislikes) if dislikes else "none"
    today = _dt.date.today().strftime("%B %Y")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Family Meal Planner</title>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Meal Plan">
<meta name="theme-color" content="#0f766e">
<link rel="apple-touch-icon" href="{APP_ICON}">
<link rel="icon" type="image/png" href="{APP_ICON}">
<style>{CSS}</style></head><body>
<div class="wrap">

  <header class="hero">
    <div class="brandrow">{IC_LOGO}<span class="bn"><b>La Ma&iuml;da</b> &nbsp;/&nbsp; Family Meal Planner</span></div>
    <h1 class="title">A month of meals, built around your family.</h1>
    <p class="lede">A low-effort halal plan for Algeria &mdash; modern everyday cooking, one prepared meal a day, with portions for healthy weight gain and breastfeeding nutrition.</p>
    <div class="meta">
      <span class="chip">{today}</span>
      <span class="chip"><span class="sw" style="background:var(--brand)"></span>Favourites: <b>{fav_txt}</b></span>
      <span class="chip"><span class="sw" style="background:var(--her)"></span>Avoiding: <b>{dis_txt}</b></span>
    </div>
  </header>

  {quickbar}

  {section(IC_CAL, "The four-week plan")}
  <div class="legend">
    <span class="lkey"><span class="sw" style="background:var(--him)"></span>Weight-gain portion</span>
    <span class="lkey"><span class="sw" style="background:var(--her)"></span>Breastfeeding boost</span>
  </div>
  {tabbar}
  {panels_html}

  {section(IC_TARGET, "Daily targets")}
  <div class="cards">{cards}</div>

  {section(IC_SNACK, "Snacks to batch-prep")}
  <div class="cards">
    <div class="card him">
      <div class="eyebrow">High-calorie &middot; prep once</div>
      <div class="name">For weight gain</div>
      <ul style="margin-top:14px;">
        <li>Energy balls: dates, oats, peanut butter, nuts &mdash; roll a dozen</li>
        <li>Boiled eggs by the half-dozen, kept in the fridge</li>
        <li>Trail mix: nuts + dried figs/raisins in small bags</li>
        <li>Overnight-oats jars (milk, oats, dates, peanut butter)</li>
        <li>Cheese + cracker + fruit packs</li>
      </ul>
    </div>
    <div class="card her">
      <div class="eyebrow">One-handed &middot; while feeding</div>
      <div class="name">For breastfeeding</div>
      <ul style="margin-top:14px;">
        <li>Dates + almonds within reach of where you feed</li>
        <li>Yogurt or rayeb pots &mdash; calcium + hydration</li>
        <li>A pre-made sandwich or wrap in the fridge</li>
        <li>A bottle of water at every feeding spot</li>
        <li>Warm milk with honey for night feeds</li>
      </ul>
    </div>
  </div>

  {section(IC_IDEA, "Make it sustainable")}
  <div class="tips">
    <div class="tip"><h4>Cook once, eat twice</h4><p>Lunch is the only real cook. Make a little extra and the next dinner is sorted with zero work.</p></div>
    <div class="tip"><h4>The non-cook owns snacks &amp; shopping</h4><p>Whoever doesn&rsquo;t cook can still own the no-cook prep: a weekend snack session and the weekly shop take real load off the main cook.</p></div>
    <div class="tip"><h4>Share the cooking days</h4><p>With a one-month-old, take the easy lunches &mdash; pasta, burgers and oven trays are hard to get wrong.</p></div>
    <div class="tip"><h4>Stock shortcuts</h4><p>Canned tuna &amp; chickpeas, frozen veg, eggs, bread and yogurt carry the no-cook meals on the hardest days.</p></div>
    <div class="tip"><h4>Repetition is fine</h4><p>Eating the same good lunch a few days running is normal right now. Variety can wait.</p></div>
    <div class="tip"><h4>Tell me your tastes</h4><p>Name a meal you love or dislike and the next plan updates automatically.</p></div>
  </div>

  <footer>
    Calorie and protein figures are healthy-adult estimates, not medical advice &mdash; adjust the weight-gain target by watching the scale.<br>
    The breastfeeding parent should follow a doctor&rsquo;s advice on supplements and any personal dietary needs.<br>
    <span class="bsaha">Bsaha &mdash; health to your family.</span>
  </footer>
</div>
{TAB_JS}
</body></html>"""


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_prefs = os.path.join(os.path.dirname(here), "preferences.json")
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefs", default=default_prefs)
    ap.add_argument("--out", default="meal-planner.html")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    try:
        with open(args.prefs, encoding="utf-8") as f:
            prefs = json.load(f)
    except FileNotFoundError:
        print(f"No preferences at {args.prefs}; using defaults.", file=sys.stderr)
        prefs = {"members": [
            {"role": "weight_gain", "sex": "male", "height_cm": 175, "weight_kg": 73, "activity": "light"},
            {"role": "breastfeeding", "sex": "female"}],
            "diet": {"halal_only": True, "dairy_ok": True, "include_fish": True},
            "favorites": [], "dislikes": ["berkoukes", "leben"], "monthly_caps": {"msemen": 1}}

    seed = args.seed
    if seed is None:
        t = _dt.date.today()
        seed = t.year * 100 + t.month  # fresh variety each month
    rng = random.Random(seed)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(build_html(prefs, rng))
    print(f"Wrote {args.out}")
    print(f"Favorites: {prefs.get('favorites', [])} | Dislikes: {prefs.get('dislikes', [])} | Caps: {dict(DEFAULT_CAPS, **prefs.get('monthly_caps', {}))}")


if __name__ == "__main__":
    main()
