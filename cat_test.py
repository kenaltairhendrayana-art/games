"""Harness for CAT CATALOGUE. Nothing here ships; it is how the game is
measured.

    python cat_test.py economy [n]   play n runs to a full binder, print it
    python cat_test.py strays       the five that are not in the catalogue
    python cat_test.py flat         the furnishings, and what they are worth
    python cat_test.py shelves      both pages of the shop, and the ladder
    python cat_test.py value         what each pack is worth per dollar
    python cat_test.py dupes         prove the levelling ladder adds up
    python cat_test.py coats        every coat a different cat, and the odds
    python cat_test.py numbers      the balance in the corner must sit still
    python cat_test.py behaviour    run the cat room and watch what it does
    python cat_test.py grades       prove every level changes the picture
    python cat_test.py sameness      every breed against every other breed
    python cat_test.py smoke         draw every screen offscreen, save PNGs
    python cat_test.py score        every sound and the loop, measured
    python cat_test.py flow         drive the real Game by pressing buttons
    python cat_test.py counts       every number shown comes from the data
    python cat_test.py layout        no click target may cover its own card
    python cat_test.py save          write, reload, and come back the same
    python cat_test.py all           the lot

The economy is the thing to re-run after touching a price, a weight, an
income or the dupe ladder. Those levers are not independent: retiring a
breed at level 10 takes it out of the pool, which pushes every later pack
toward whatever is left, so making commons cheaper to finish makes
legends arrive sooner too.
"""

import math
import os
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import cat_catalogue as cc


# ---------------------------------------------------------------------------
def _fmt(secs):
    secs = int(secs)
    if secs >= 3600:
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"
    return f"{secs // 60}m{secs % 60:02d}s"


def strays():
    """The five that are not in the catalogue, and how they get in.

    Three things have to hold and none of them raise if they stop: a
    pack must never contain one, they must all arrive within a run, and
    they must not count toward the binder - thirty-two listed breeds
    plus five cats off the street would otherwise add up to a finished
    collection and fire the ending early.
    """
    pygame.display.set_mode((cc.W, cc.H))
    ok = True
    print(f"  {len(cc.SECRETS)} unlisted: "
          + ", ".join(b.name for b in cc.SECRETS))

    # 1. the shop has never heard of them
    rng = random.Random(5)
    st = cc.State()
    seen = set()
    for p in cc.PACKS:
        for _ in range(240):
            for pull in st.open_pack(p, 1, rng):
                seen.add(pull.breed.key)
    leaked = seen & {b.key for b in cc.SECRETS}
    print(f"  {len(seen)} breeds came out of "
          f"{len(cc.PACKS)} kinds of box; {len(leaked)} of them unlisted")
    if leaked:
        print(f"  the shop sold an unlisted cat: {sorted(leaked)}")
        ok = False

    # 2. they turn up at the door, all five, inside a long run
    st2 = cc.State()
    rng2 = random.Random(9)
    t = 0.0
    arrived = []
    while t < 2.5 * 3600 and len(arrived) < len(cc.SECRETS):
        st2.tick(1.0)
        t += 1.0
        if st2.stray_tick(1.0, rng2):
            got = st2.take_in(rng2)
            if got and got[1] == "new":
                arrived.append((t, got[0].name))
    for when, name in arrived:
        print(f"    {int(when) // 60:>3}m  {name}")
    if len(arrived) < len(cc.SECRETS):
        print(f"  only {len(arrived)} of {len(cc.SECRETS)} turned up in "
              f"two and a half hours")
        ok = False

    # 3. and they are not part of the binder
    if st2.owned != 0:
        print(f"  five strays counted as {st2.owned} catalogue breeds")
        ok = False
    for b in cc.SECRETS:
        st2.cards[b.key].level = cc.MAX_LEVEL
    if st2.retired != 0 or st2.complete:
        print("  retiring the strays alone finished the binder")
        ok = False
    if st2.strays_owned != len(cc.SECRETS):
        print("  the strays are not being counted as strays")
        ok = False

    # 4. a stray waits to be let in, and survives a save
    st3 = cc.State()
    st3.stray_t = 0.1
    st3.stray_tick(1.0, random.Random(2))
    waited = st3.stray
    for _ in range(600):
        st3.stray_tick(1.0, random.Random(2))
    if st3.stray != waited:
        print("  a cat left the step before it was let in")
        ok = False
    import json
    back = cc.State.from_dict(json.loads(json.dumps(st3.to_dict())))
    if back.stray != waited:
        print("  the cat at the door did not survive a save")
        ok = False
    print("  strays:", "ok" if ok else "FAILED")
    return ok


def flat():
    """The furnishings: every one bought once, and every one felt."""
    ok = True
    st = cc.State()
    st.cards["dsh"] = cc.Card(level=5)
    base = st.income
    print(f"    bare boards        {cc.rate(base)}")
    last = 0
    for u in cc.UPGRADES:
        if u.price <= last:
            print(f"  {u.name} costs no more than the one before it")
            ok = False
        last = u.price
        st.money = u.price
        if not st.buy_thing(u):
            print(f"  could not buy {u.name} with exactly its price")
            ok = False
        if st.buy_thing(u):
            print(f"  {u.name} could be bought twice")
            ok = False
        print(f"    {u.name:<22}{cc.rate(st.income)}   (+{u.gain * 100:.0f}%)")
    if st.income <= base:
        print("  furnishing the flat changed nothing")
        ok = False
    print(f"  everything: {cc.rate(base)} -> {cc.rate(st.income)}, "
          f"the flat at +{int(round(st.comfort * 100 - 100))}%")
    import json
    back = cc.State.from_dict(json.loads(json.dumps(st.to_dict())))
    if back.things != st.things or abs(back.income - st.income) > 1e-6:
        print("  the furnishings did not survive a save")
        ok = False
    where = {u.where for u in cc.UPGRADES}
    print(f"  they appear in: {', '.join(sorted(where))}")
    if not where <= set(cc.AREAS):
        print("  a furnishing belongs to a room that does not exist")
        ok = False
    print("  flat:", "ok" if ok else "FAILED")
    return ok


def shelves():
    """Every pack has to be ON a shelf, and every shelf has to have packs.

    Four products were added to a page that fits five, and the thing that
    goes wrong is silent: they appear, squeezed, on the page the ladder
    lives on, and the ladder stops reading as a ladder.
    """
    ok = True
    for shelf in cc.SHELVES:
        on = cc.packs_on(shelf)
        print(f"    {shelf:<9} {len(on)}: "
              + ", ".join(p.name for p in on))
        if not on:
            print(f"  nothing on the {shelf} shelf")
            ok = False
        if len(on) > 6:
            print(f"  {len(on)} products on one page is more than it holds")
            ok = False
    # Not every shelf is a page in the shop any more. The hall hands
    # three of them out and the resale site lists the rest second hand.
    # What must stay true is that no pack is on NO shelf, and that none
    # of the off-site ones can be ordered from the website - the day a
    # convention pack quietly appears on a shelf tab is the day the
    # convention stops being worth leaving the flat for.
    off = {}
    for pk in cc.PACKS:
        if pk.shelf not in cc.SHELVES:
            off.setdefault(pk.shelf, []).append(pk)
    for shelf in sorted(off):
        print("    {:<9} {}: ".format(shelf, len(off[shelf]))
              + ", ".join(p.name for p in off[shelf]) + "   (not for sale)")
    counted = (sum(len(cc.packs_on(sh)) for sh in cc.SHELVES)
               + sum(len(v) for v in off.values()))
    if counted != len(cc.PACKS):
        print(f"  {len(cc.PACKS) - counted} packs are on no shelf at all")
        ok = False
    for want in ("convention", "resale"):
        if not off.get(want):
            print(f"  nothing is on the {want} shelf")
            ok = False

    # the ladder has to keep going up, on every axis
    last = None
    for p in cc.packs_on("standard"):
        tot = sum(p.weights)
        ev = sum(p.weights[r] / tot * cc.RARITY[r][2] for r in range(cc.SOLD_RARITIES))
        per = ev * p.cards / p.price * 100
        if last and (p.price <= last[0] or per <= last[1]
                     or p.cards <= last[2]):
            print(f"  {p.name} does not improve on the rung below it")
            ok = False
        last = (p.price, per, p.cards)
    print("  shelves:", "ok" if ok else "FAILED")
    return ok


def pack_value():
    """Expected income bought per dollar, for each pack, on an empty binder.

    This is the shape of the shop: every pack should be a worse deal per
    card and a better deal per minute than the one below it, or there is
    no reason for the cheap ones to exist.
    """
    print("pack              price  cards   E[rate]/pack   per $100   ship")
    for p in cc.PACKS:
        tot = sum(wt for wt in p.weights)
        ev = sum(p.weights[r] / tot * cc.RARITY[r][2] for r in range(cc.SOLD_RARITIES))
        per = ev * p.cards
        worth = f"{per / p.price * 100:>11.3f}" if p.price else f"{'free':>11}"
        print(f"{p.name:<22}{p.price:>6}{p.cards:>6}"
              f"{per:>14.3f}{worth}{p.ship:>7.0f}s")


def dupe_ladder():
    ok = True
    total = 0
    for lv in range(1, cc.MAX_LEVEL):
        need = cc.dupes_for(lv)
        total += need
        print(f"  level {lv:>2} -> {lv + 1:<2} {need:>3} duplicates"
              f"   {total:>4} so far")
    print(f"  level {cc.MAX_LEVEL} is retired: dupes_for = "
          f"{cc.dupes_for(cc.MAX_LEVEL)}")
    if total != cc.DUPES_TO_MAX:
        print(f"  MISMATCH: DUPES_TO_MAX says {cc.DUPES_TO_MAX}, ladder "
              f"adds to {total}")
        ok = False

    card = cc.Card()
    pulls = 0
    while not card.maxed:
        card.add_dupe()
        pulls += 1
    print(f"  a card maxes after {pulls} duplicates "
          f"({pulls + 1} copies in all)")
    if pulls != cc.DUPES_TO_MAX:
        print("  MISMATCH: Card.add_dupe does not agree with the ladder")
        ok = False
    before = card.pulled
    card.add_dupe()
    if card.level != cc.MAX_LEVEL or card.dupes != 0:
        print("  BUG: a retired card moved when given another duplicate")
        ok = False
    if card.pulled != before + 1:
        print("  BUG: a retired card did not count the copy it was given")
        ok = False
    print("  dupes:", "ok" if ok else "FAILED")
    return ok


# ---------------------------------------------------------------------------
# The economy, played out
# ---------------------------------------------------------------------------
def _affordable(state, policy):
    """Which pack a player buys with the money in hand.

    Three players. `cheap` never leaves the paper sacks. `dear` always
    buys the most expensive thing on the page, which is the trap: the
    Estate Lot sells no commons at all, so a collection bought entirely
    out of lots arrives at the end with six ordinary cats still on level
    one. `need` spends on whatever rarity it is furthest from finishing,
    which is what a person does once they have looked at the binder.
    """
    ladder = [p for p in cc.packs_on("standard") if p.price <= state.money
              and state.sellable(p)]
    if policy in ("cheap", "dear"):
        if not ladder:
            return None
        return ladder[0] if policy == "cheap" else ladder[-1]
    # `need` shops off both pages: it buys for the rarity it is furthest
    # from finishing. It ranks by THROUGHPUT and not by price, because
    # ranking by price sent it to The Single - one guaranteed legend for
    # eighteen hundred - and a bot that buys eight hundred of those takes
    # two hours over a binder the ladder finishes in fifty minutes. The
    # guarantee is priced like a guarantee; it is not a staple.
    can = [p for p in cc.PACKS if p.price <= state.money
           and state.sellable(p) and p.shelf in cc.SHELVES]
    if not can:
        return None
    want = max(range(cc.SOLD_RARITIES), key=lambda r: state.missing(r))
    best, score = None, -1.0
    for p in can:
        tot = sum(p.weights)
        share = p.weights[want] / tot if tot else 0
        if share <= 0:
            continue
        per_min = share * p.cards / p.ship          # cards of what I need
        if per_min > score:
            best, score = p, per_min
    return best or can[-1]


def _mode_for(state, pack):
    """Pay for speed only when the cats can keep paying for it.

    This is the decision the shipping options exist to offer, and it is
    the only sink a late collection has for money it cannot spend on
    packs fast enough.
    """
    for m in (2, 1):
        cost = pack.price + cc.ship_cost(pack, 1, m)
        if cost <= state.money and cost / cc.ship_time(pack, m) <= state.income:
            return m
    return 0


def play(seed=0, policy="need", step=1.0, cap=60 * 3600, verbose=False):
    rng = random.Random(seed)
    s = cc.State()
    t = 0.0
    marks = {}
    while t < cap:
        s.tick(step)
        t += step
        while s.parcels:
            key, qty = s.parcels.pop(0)
            s.open_pack(cc.BY_PACK[key], qty, rng)
        if s.owned == len(cc.BREEDS) and "all_owned" not in marks:
            marks["all_owned"] = t
        if s.retired and "first_retired" not in marks:
            marks["first_retired"] = t
        if s.complete:
            marks["complete"] = t
            break
        if policy != "cheap":
            # the club pays for itself in minutes at this end of the game
            while s.money > cc.CLUB[min(s.club, 2)][0] * 2 and s.join_club():
                pass
            # ... and so does anything that multiplies every cat at once
            for u in cc.UPGRADES:
                if u.key not in s.things and s.money > u.price * 2.5:
                    s.buy_thing(u)
        p = _affordable(s, policy)
        if p is not None:
            s.order(p, 1, _mode_for(s, p))
        if verbose and int(t) % 600 == 0:
            print(f"   {_fmt(t)}  {cc.money(s.money):>10}  "
                  f"{cc.rate(s.income):>10}  own {s.owned:>2}  "
                  f"retired {s.retired:>2}")
    marks.setdefault("complete", None)
    return s, t, marks


def economy(n=3):
    print("Playing to a full binder. The bot buys the best value pack it "
          "can afford,\nships everything by slow post, and opens parcels "
          "the moment they land.\n")
    for policy in ("cheap", "dear", "need"):
        rows = []
        for seed in range(n):
            s, t, m = play(seed, policy)
            rows.append((t, m, s))
        done = [r for r in rows if r[2].complete]
        print(f"  {policy:<6} "
              f"first breed retired {_fmt(min(r[1].get('first_retired', 0) for r in rows))}"
              f" | all {len(cc.BREEDS)} owned "
              f"{_fmt(sum(r[1].get('all_owned', 0) for r in rows) / len(rows))}"
              f" | binder full "
              f"{(_fmt(sum(r[0] for r in done) / len(done)) if done else 'never')}"
              f" | packs {sum(r[2].packs_opened for r in rows) // len(rows)}"
              f" | club {sum(r[2].club for r in rows) / len(rows):.1f}")
    print()
    s, t, m = play(0, "need", verbose=True)
    print(f"\n  one run, in full: {_fmt(t)}, {s.packs_opened} packs, "
          f"{s.cards_pulled} cards, {cc.money(s.spent)} spent, "
          f"ending at {cc.rate(s.income)}")
    return s.complete


# ---------------------------------------------------------------------------
# The cats, measured rather than looked at
# ---------------------------------------------------------------------------
def sameness():
    """Two breeds that share a silhouette are a bug in the breed table.

    Colour and size are stripped before the comparison - a grey cat and a
    ginger cat of the same shape are the same cat, and "it draws" is not
    "it differs". What is left is the outline, normalised to one box.

    The bar moves with the size of the book, and that is a decision
    rather than a dodge. At twenty-four breeds nothing was allowed over
    0.94 overlap and nothing was. At a hundred, in one sitting pose, that
    is not reachable: a Burmese and a Suphalak ARE the same build, and
    the honest thing is to say so rather than to deform one of them until
    a number goes green. So three things are checked instead of one:
    nothing may be effectively identical, the close pairs must stay a
    small fraction of all of them, and the book as a whole must not drift
    toward one average cat.
    """
    pygame.display.set_mode((64, 64))
    SZ = 72
    masks = {}
    # Every cat in the game, not just the catalogue. The five off the
    # street and the five printed for the hall were never compared
    # against anything - which is exactly how a new one ends up being a
    # breed that is already in the book with a different name on it.
    for b in cc.ALL_BREEDS:
        img = cc.cat_surface(b, "sit", 150)
        # the mask IS the shape with the colour thrown away; scaling it to
        # one box throws the size away too, which is the other half of it
        m = pygame.mask.from_surface(img, 24)
        sil = m.to_surface(setcolor=(255, 255, 255, 255),
                           unsetcolor=(0, 0, 0, 255))
        small = pygame.transform.smoothscale(sil, (SZ, SZ))
        masks[b.key] = [1 if small.get_at((x, y))[0] > 110 else 0
                        for y in range(SZ) for x in range(SZ)]
    worst = []
    for i, a in enumerate(cc.ALL_BREEDS):
        for b in cc.ALL_BREEDS[i + 1:]:
            ma, mb = masks[a.key], masks[b.key]
            inter = sum(1 for x, y in zip(ma, mb) if x and y)
            union = sum(1 for x, y in zip(ma, mb) if x or y)
            worst.append((inter / max(1, union), a.name, b.name))
    worst.sort(reverse=True)
    total = len(worst)
    mean = sum(w[0] for w in worst) / total

    IDENTICAL = 0.965          # nothing may be this close to anything
    CLOSE = 0.95               # ... and few may be this close
    CLOSE_SHARE = 0.01         # one pair in a hundred
    BLAND = 0.84               # the whole book, averaged

    print(f"  {len(cc.ALL_BREEDS)} cats, {total} pairs, mean overlap "
          f"{mean:.3f}")
    print("  the eight most alike, by overlap of outline:")
    for same, a, b in worst[:8]:
        flag = "  <-- the same cat twice" if same > IDENTICAL else ""
        print(f"    {same:.3f}  {a} / {b}{flag}")
    print(f"  the two least alike: {worst[-1][0]:.3f}  "
          f"{worst[-1][1]} / {worst[-1][2]}")

    ok = True
    bad = [w for w in worst if w[0] > IDENTICAL]
    close = [w for w in worst if w[0] > CLOSE]
    print(f"  over {IDENTICAL}: {len(bad)}   over {CLOSE}: {len(close)} "
          f"({len(close) / total * 100:.1f}% of pairs, "
          f"{CLOSE_SHARE * 100:.0f}% allowed)")
    if bad:
        ok = False
    if len(close) > total * CLOSE_SHARE:
        print(f"  too many breeds share a build: {len(close)} pairs over "
              f"{CLOSE}, the limit is {int(total * CLOSE_SHARE)}")
        ok = False
    if mean > BLAND:
        print(f"  the book has drifted toward one average cat: mean "
              f"{mean:.3f} against a limit of {BLAND}")
        ok = False
    print("  sameness:", "ok" if ok else "FAILED")
    return ok


def coats():
    """Every coat has to be a different cat, and the shiny rarest of all.

    A recolour that comes out the same colour is the same failure as two
    breeds sharing a silhouette: it draws, so nothing complains, and the
    second collection is quietly empty. Measured the same way - the
    portrait, scaled into one box, compared pixel for pixel.
    """
    pygame.display.set_mode((cc.W, cc.H))
    ok = True
    worst = []
    for b in cc.ALL_BREEDS:          # the strays have coats as well
        imgs = [cc.cat_surface(b, "sit", 130, level=6, variant=i)
                for i in range(len(b.coats))]
        imgs.append(cc.cat_surface(b, "sit", 130, level=6, shiny=True))
        names = list(b.coats) + ["shiny"]
        for i in range(len(imgs)):
            for j in range(i + 1, len(imgs)):
                d = _differs(imgs[i], imgs[j], (56, 56))
                worst.append((d, b.name, names[i], names[j]))
    worst.sort()
    for d, nm, a, c in worst[:6]:
        flag = "   <-- the same cat twice" if d < 0.05 else ""
        print(f"    {d:.3f}  {nm}: {a} against {c}{flag}")
        if d < 0.05:
            ok = False
    print(f"  {len(worst)} pairs of coats compared, the closest "
          f"{worst[0][0]:.3f} apart")

    # the odds, and that a shiny is permanent once it lands
    rng = random.Random(7)
    st = cc.State()
    pulls = shiny = 0
    for _ in range(600):
        for p in st.open_pack(cc.BY_PACK["crate"], 1, rng):
            pulls += 1
            shiny += 1 if p.shiny else 0
    rate = pulls / max(1, shiny)
    print(f"  {pulls} cards pulled, {shiny} shiny - one in "
          f"{rate:.0f} (the dial says one in {cc.SHINY_IN})")
    if not 0.5 * cc.SHINY_IN < rate < 2.0 * cc.SHINY_IN:
        print("  the shiny rate is not what the dial says")
        ok = False
    for k, c in st.cards.items():
        if c.coats_seen(cc.BY_KEY[k]) < 1:
            print(f"  {k} has a card but no coat recorded")
            ok = False

    # the two boxes that do something other than hold cards
    rng = random.Random(11)
    st2 = cc.State()
    st2.open_pack(cc.BY_PACK["crate"], 40, rng)      # a binder with gaps
    before = sum(c.coats_seen(cc.BY_KEY[k]) for k, c in st2.cards.items())
    gaps = sum(len(cc.BY_KEY[k].coats) - c.coats_seen(cc.BY_KEY[k])
               for k, c in st2.cards.items())
    fresh = 0
    for p in st2.open_pack(cc.BY_PACK["swatch"], 6, rng):
        fresh += 1 if p.new_coat else 0
    after = sum(c.coats_seen(cc.BY_KEY[k]) for k, c in st2.cards.items())
    print(f"  the swatch book: {fresh} of 36 cards were a coat not seen "
          f"before ({gaps} gaps were open), {after - before} new")
    if after <= before:
        print("  the swatch book found no new coats at all")
        ok = False

    st3 = cc.State()
    odd = sum(1 for _ in range(200)
              for p in st3.open_pack(cc.BY_PACK["odd"], 1, rng) if p.shiny)
    pulls3 = 200 * cc.BY_PACK["odd"].cards
    print(f"  the oddity crate: {odd} shiny in {pulls3} cards - one in "
          f"{pulls3 / max(1, odd):.0f}, against one in {cc.SHINY_IN} "
          f"everywhere else")
    if odd < 2:
        print("  the oddity crate is not finding shinies")
        ok = False

    # one in 150 has to survive being written to disk
    import json
    st.cards["dsh"].shiny = True
    st.cards["dsh"].coat = 1 if len(cc.BY_KEY["dsh"].coats) > 1 else 0
    st.cards["dsh"].saw(0)
    back = cc.State.from_dict(json.loads(json.dumps(st.to_dict())))
    a, c = st.cards["dsh"], back.cards["dsh"]
    if (a.shiny, a.coat, a.seen) != (c.shiny, c.coat, c.seen):
        print(f"  a shiny came back as {c.shiny}/{c.coat}/{c.seen}")
        ok = False
    if abs(back.income - st.income) > 0.001:
        print("  the shiny bonus did not survive the save")
        ok = False

    # and an old save, from before any of this existed, still loads
    old = {"v": 1, "money": 50.0, "cards": {"dsh": [3, 1, 7]},
           "stamp": time.time()}
    o = cc.State.from_dict(old)
    if "dsh" not in o.cards or o.cards["dsh"].level != 3:
        print("  a save from before coats existed no longer loads")
        ok = False
    print("  coats:", "ok" if ok else "FAILED")
    return ok


def numbers():
    """The balance in the corner of the room must sit still.

    Written against "it is going up rapidly and it is a little hard on
    the eyes". A counter that restreams at sixty frames a second is the
    loudest thing in a room that is meant to be quiet, and rounding it
    by magnitude is not enough on its own - six thousand to the nearest
    hundred still moves every two seconds once the cats are earning
    fifty a second. The step is set by the INCOME, so this checks the
    whole arc of the game rather than one point of it.
    """
    pygame.display.set_mode((cc.W, cc.H))
    ok = True

    def binder_for(target):
        st = cc.State()
        for b in cc.BREEDS:
            for lv in range(1, cc.MAX_LEVEL + 1):
                if st.income >= target:
                    return st
                st.cards[b.key] = cc.Card(level=lv)
        return st

    print("    income      step   new numbers a minute")
    for target, start in ((0.05, 3.0), (1.0, 480.0), (4.0, 90.0),
                          (12.0, 480.0), (56.0, 3000.0), (170.0, 40000.0)):
        g = cc.Game(screen=pygame.display.get_surface())
        g.state = binder_for(target)
        g.state.money = start
        inc = g.state.income
        shown = []
        for _ in range(60 * 60):
            g.update(1 / 60)
            shown.append(cc.money_soft(g.shown))
        ch = sum(1 for a, b in zip(shown, shown[1:]) if a != b)
        print(f"  {cc.rate_soft(inc):>9} {cc.quantum(inc):>9.0f}"
              f"{ch:>19}")
        if ch > 20:
            print(f"  at {cc.rate_soft(inc)} the balance changes {ch} times "
                  f"a minute, which is what it is not supposed to do")
            ok = False
        # it may lag behind the truth, but it must never claim
        # more money than there is
        if g.shown > g.state.money + 1e-6:
            print(f"  the corner says {cc.money_soft(g.shown)}"
                  f" but there is only {cc.money(g.state.money)}")
            ok = False

    # and the website still counts to the dollar, because that is where
    # the decision is made
    g = cc.Game(screen=pygame.display.get_surface())
    g.state = cc.State()
    g.state.money = 1234.56
    g.update(1 / 60)
    if cc.money(g.shown_exact) != "$1,235" and \
            cc.money(g.shown_exact) != "$1,234":
        print(f"  the shop would show {cc.money(g.shown_exact)}")
        ok = False
    print("  numbers:", "ok" if ok else "FAILED")
    return ok


def behaviour(minutes=20, big=False):
    """Run the cat room for an hour of cat-time and watch what happens.

    Three things can go wrong here and none of them raise: a cat can get
    stuck in a state and never move again, an activity can turn out to
    be unreachable because no spot offers it, and every temperament can
    quietly collapse onto the same behaviour, which would make the whole
    feature decorative. So: count what each cat actually does, and check
    it against the temperament it was given.
    """
    pygame.display.set_mode((cc.W, cc.H))
    st = cc.State()
    rng = random.Random(3)
    for b in cc.BREEDS:                   # one of everything, levelled up
        st.cards[b.key] = cc.Card(level=rng.randint(3, 10))
    st.big_room = big
    cap = cc.room_cap(st)
    nspots = cc.room_spot_count(st)
    room = cc.CatRoom()
    room.update(0.1, st, cap)
    seen = {r.breed.key: {} for r in room.res}
    spots_used = set()
    moved = {r.breed.key: 0.0 for r in room.res}
    last_x = {r.breed.key: r.x for r in room.res}
    steps = int(minutes * 60 / 0.1)
    for _ in range(steps):
        room.update(0.1, st, cap)
        for r in room.res:
            d = seen.setdefault(r.breed.key, {})
            if r.state == "rest":
                d[r.act] = d.get(r.act, 0) + 1
                spots_used.add(r.spot)
            moved[r.breed.key] += abs(r.x - last_x[r.breed.key])
            last_x[r.breed.key] = r.x
    ok = True

    print(f"  {minutes} minutes, {len(room.res)} cats in the room")
    for r in sorted(room.res, key=lambda r: r.breed.name):
        d = seen[r.breed.key]
        total = sum(d.values()) or 1
        top = sorted(d.items(), key=lambda kv: -kv[1])[:3]
        bits = ", ".join(f"{k} {v * 100 // total}%" for k, v in top)
        print(f"    {r.breed.name:<20}{r.breed.temper:<9}{bits}")
        if not d:
            print(f"  {r.breed.name} did nothing at all")
            ok = False
        if moved[r.breed.key] < 50:
            print(f"  {r.breed.name} never crossed the room")
            ok = False
        # the thing its temperament is built around has to be the thing
        # it actually does most of
        want = max(r.breed.temperament["acts"].items(),
                   key=lambda kv: kv[1])[0]
        if top and top[0][0] != want and d.get(want, 0) < total * 0.12:
            print(f"  {r.breed.name} is a {r.breed.temper} but hardly ever "
                  f"{want}s ({d.get(want, 0) * 100 // total}%)")
            ok = False

    every = set()
    for d in seen.values():
        every |= set(d)
    back_acts = {"climb", "hide", "chatter"}
    want_acts = set(cc.ACT_WORD) if big else set(cc.ACT_WORD) - back_acts
    missing = want_acts - every
    if missing:
        print(f"  never happened at all: {sorted(missing)}")
        ok = False
    leaked = (every - want_acts) | {i for i in spots_used if i >= nspots}
    if leaked:
        print(f"  happened through a wall that is not down: {sorted(leaked)}")
        ok = False
    print(f"  {len(spots_used)} of {nspots} spots were used, "
          f"{len(every)} of {len(want_acts)} activities happened")
    if len(spots_used) < nspots * 0.8:
        print(f"  {nspots - len(spots_used)} places nobody ever went")
        ok = False

    # The complaint this is written against was "the cats are not
    # moving", with three cats in a room twice as wide as the window.
    # They WERE moving; they were round the corner, and the ones in view
    # had settled for fifty seconds. So: with a small collection and the
    # camera where you come in, most of them have to be on screen and
    # something has to be happening.
    if big:
        print("  behaviour (the back room):", "ok" if ok else "FAILED")
        return ok
    small = cc.State()
    for k, lv in (("dsh", 2), ("ben", 1), ("per", 3)):
        small.cards[k] = cc.Card(level=lv)
    r2 = cc.CatRoom()
    r2.update(0.1, small, cc.ROOM_CAP, 0.0)
    on = busy = frames = 0
    for _ in range(90 * 20):
        r2.update(0.05, small, cc.ROOM_CAP, 0.0)
        frames += 1
        for r in r2.res:
            if -60 <= r.x <= cc.W + 60:
                on += 1
            if r.state != "rest" or r.act == "prowl":
                busy += 1
    print(f"  three cats, 90 seconds, standing at the door: "
          f"{on / frames:.2f} of 3 in view, {busy / frames:.2f} of 3 moving")
    if on / frames < 1.5:
        print("  most of the cats are round the corner where you cannot "
              "see them")
        ok = False
    if busy / frames < 0.4:
        print("  the room looks like a photograph of cats")
        ok = False

    # and no two cats may end up standing in the same place
    seats = [r.spot for r in room.res if r.state == "rest"]
    if len(seats) != len(set(seats)):
        print("  two cats are sitting on the same spot")
        ok = False
    print("  behaviour:", "ok" if ok else "FAILED")
    return ok


def _differs(a, b, box=(88, 124)):
    """How much two surfaces differ, 0 to 1, with the size normalised.

    Scaled into one box first, so "it got bigger" on its own does not
    count as "it looks different" - the same trick `sameness` uses on the
    silhouettes, for the same reason.
    """
    sa = pygame.transform.smoothscale(a.convert(), box)
    sb = pygame.transform.smoothscale(b.convert(), box)
    diff = 0
    for y in range(box[1]):
        for x in range(box[0]):
            ca, cb = sa.get_at((x, y)), sb.get_at((x, y))
            if (abs(ca[0] - cb[0]) + abs(ca[1] - cb[1]) +
                    abs(ca[2] - cb[2])) > 18:
                diff += 1
    return diff / (box[0] * box[1])


def grades():
    """Every level has to CHANGE something, and the ten have to add up.

    The request this is written against was "when your cat levels up the
    card looks better and the cat looks better", and the way that goes
    wrong is silently: a knob gets tuned down, or a grade threshold moves,
    and three levels in a row start drawing the same picture. Nothing
    raises. So this measures the picture.
    """
    pygame.display.set_mode((cc.W, cc.H))
    ok = True
    card = pygame.Surface((152, 214))
    prev_card = prev_cat = None
    rows = []
    for lv in range(1, cc.MAX_LEVEL + 1):
        b = cc.BY_KEY["dsh"]
        card.fill(cc.INK)
        cc.draw_card(card, card.get_rect(), b, lv, dupes=lv,
                     maxed=(lv == cc.MAX_LEVEL))
        cat = cc.cat_surface(b, "sit", 150, level=lv)
        if prev_card is not None:
            dc = _differs(card, prev_card)
            da = _differs(cat, prev_cat)
            rows.append((lv, dc, da))
            if dc < 0.010:
                print(f"  level {lv}: the card is the same picture as "
                      f"level {lv - 1} ({dc:.3f})")
                ok = False
            if da < 0.010:
                print(f"  level {lv}: the cat is the same picture as "
                      f"level {lv - 1} ({da:.3f})")
                ok = False
        prev_card = card.copy()
        prev_cat = cat
    for lv, dc, da in rows:
        print(f"    level {lv - 1} -> {lv:<3} card {dc:.3f}   cat {da:.3f}")

    # and the whole climb has to be worth making
    b = cc.BY_KEY["dsh"]
    one = pygame.Surface((152, 214))
    ten = pygame.Surface((152, 214))
    one.fill(cc.INK)
    ten.fill(cc.INK)
    cc.draw_card(one, one.get_rect(), b, 1)
    cc.draw_card(ten, ten.get_rect(), b, cc.MAX_LEVEL, maxed=True)
    far = _differs(one, ten)
    print(f"  level 1 against level 10: {far:.3f} of the card")
    if far < 0.30:
        print("  a finished card does not look much better than a stray")
        ok = False

    # the grades themselves, and that each one is reachable
    for g in range(5):
        at = [lv for lv in range(1, cc.MAX_LEVEL + 1)
              if cc.grade_of(lv) == g]
        print(f"    grade {g} ({cc.GRADE_NAME[g]:<14}) levels "
              f"{at[0]}-{at[-1]}")
        if not at:
            print(f"  grade {g} can never be reached")
            ok = False
    print("  grades:", "ok" if ok else "FAILED")
    return ok


def save_round_trip():
    import json
    s = cc.State()
    rng = random.Random(4)
    s.money = 1234.5
    s.open_pack(cc.BY_PACK["crate"], 6, rng)
    s.order(cc.BY_PACK["box"], 2, 1)
    s.parcels.append(("sack", 3))
    d = s.to_dict()
    d["stamp"] = time.time()         # no offline gap, so nothing should move
    back = cc.State.from_dict(json.loads(json.dumps(d)))
    ok = True
    if abs(back.money - s.money) > 0.01:
        print(f"  money came back as {back.money}, not {s.money}")
        ok = False
    if set(back.cards) != set(s.cards):
        print("  the binder lost or gained a breed")
        ok = False
    for k, c in s.cards.items():
        b = back.cards[k]
        if (b.level, b.dupes, b.pulled) != (c.level, c.dupes, c.pulled):
            print(f"  {k} came back as {b.level}/{b.dupes}, not "
                  f"{c.level}/{c.dupes}")
            ok = False
    if len(back.orders) != len(s.orders) or len(back.parcels) != len(s.parcels):
        print("  an order or a parcel went missing")
        ok = False

    # and the other half: time passing while the game is shut
    d2 = s.to_dict()
    d2["stamp"] = time.time() - 600
    away = cc.State.from_dict(d2)
    if away.money <= s.money:
        print("  the cats earned nothing over ten minutes away")
        ok = False
    if away.orders:
        print("  a ten-minute absence did not deliver a 26s parcel")
        ok = False
    print(f"  ten minutes away paid {cc.money(away.away)} at "
          f"{cc.rate(s.income)}")
    print("  save:", "ok" if ok else "FAILED")
    return ok


def smoke():
    """Draw every screen with the dummy driver and save it as a PNG.

    Nothing here asserts; it exists so that a screen can be LOOKED at
    without playing to it, which is the only way most of this UI is ever
    seen more than once.
    """
    screen = pygame.display.set_mode((cc.W, cc.H))
    rng = random.Random(5)
    g = cc.Game(screen)
    g.state = cc.State()                 # never touch the real save
    shots = []

    def shot(name, warm=0.0):
        for _ in range(max(1, int(warm * 20))):
            g.update(0.05)
        g.shown = g.shown_exact = g.state.money   # no stale corner
        g.draw()
        pygame.image.save(screen, f"cat_{name}.png")
        shots.append(name)

    shot("hall_empty")
    g.area = "study"
    shot("room_empty")
    g.state.open_pack(cc.BY_PACK["sack"], 3, rng)
    g.state.money = 86.0
    g.t = 6.0
    shot("room_early")

    g.state.open_pack(cc.BY_PACK["lot"], 9, rng)
    g.state.open_pack(cc.BY_PACK["crate"], 6, rng)
    g.state.money = 24_800.0
    g.state.club = 1
    g.state.order(cc.BY_PACK["crate"], 2, 1)
    g.state.order(cc.BY_PACK["lot"], 1, 2)
    g.state.parcels.append(("case", 1))
    g.t = 20.0
    shot("room_late")

    g.area = "hall"
    shot("hall")
    g.state.things = {u.key for u in cc.UPGRADES}
    g.state.stray = "kam"
    g.area = "hall"
    shot("hall_stray")
    g.area = "cats"
    shot("catroom", warm=12)
    g.cam = g.cam_to = cc.AREA_WIDE["cats"] - cc.W
    shot("catroom_far", warm=6)
    g.cam = g.cam_to = 0.0
    g.focus = g.room.res[0].breed.key if g.room.res else None
    g.focus_t = 5.0
    shot("catroom_focus")
    g.area = "study"

    g.go("shop")
    shot("shop_catalogue")
    g.product = "crate"
    g.qty = 3
    g.mode = 1
    shot("shop_product")
    g.product = None
    g.tab = "home"
    g.state.things = {"bowlmat", "rug", "fountain"}
    shot("shop_home")
    g.tab = "specials"
    shot("shop_specials")
    g.product = "odd"
    shot("shop_oddity")
    g.product = None
    g.tab = "catalogue"
    g.tab = "orders"
    shot("shop_orders")
    g.tab = "club"
    shot("shop_club")

    g.go("binder")
    shot("binder")
    # a shiny, and a breed with coats to show off in the detail panel
    if "sia" in g.state.cards:
        g.state.cards["sia"].shiny = True
        g.state.cards["sia"].seen = 0b1011
    shot("binder_shiny")
    g.pick = "sia"
    shot("binder_detail")

    g.go("open")
    g.open_pack_key = "case"
    g.open_qty = 1
    g.cut = False
    shot("open_closed")
    g.cut_tape()
    g.lid = 1.0
    g.deal = 1.0
    shot("open_facedown")
    g.flip_all()
    shot("open_flipped")

    g.go("menu")
    shot("menu")
    g.go("end")
    shot("end")
    g.go("open")

    g.open_pack_key = "lot"
    g.open_qty = 3
    g.cut = False
    g.pulls = []
    g.flipped = 0
    g.cut_tape()
    g.lid = g.deal = 1.0
    g.flip_all()
    shot("open_bulk")

    print("  wrote", ", ".join(f"cat_{n}.png" for n in shots))
    return True


def score():
    """Measure the music instead of listening to it.

    The failure this is here for is dead air at the seam: a generated
    loop whose last note has decayed to nothing before the buffer ends,
    so it ticks. `_mix` wraps the tail round onto the start of the
    buffer, and this is what proves it did.
    """
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    ok = True
    if not cc.init_audio():
        print("  no audio device even with the dummy driver - skipped")
        return True
    from array import array

    # The mixer may well have come up in stereo whether it was asked to
    # or not, in which case the raw buffer is interleaved pairs and every
    # length read off it is double. Take one channel and measure that -
    # reading the raw bytes as if they were mono is the same mistake the
    # game itself was making.
    chans = (pygame.mixer.get_init() or (0, 0, 1))[2]
    print(f"  the mixer came up {pygame.mixer.get_init()}")

    def samples(snd):
        return array("h", snd.get_raw())[::chans]

    def rms(block):
        if not block:
            return 0.0
        return math.sqrt(sum(v * v for v in block) / len(block)) / 32768.0

    m = cc.music_loop()
    if not m:
        print("  the music did not build")
        return False
    buf = samples(m)
    secs = len(buf) / cc.RATE
    win = cc.RATE // 2
    blocks = [rms(buf[i:i + win]) for i in range(0, len(buf) - win, win)]
    mean = sum(blocks) / len(blocks)
    quiet = [i for i, b in enumerate(blocks) if b < mean * 0.25]
    print(f"  loop {secs:.1f}s, mean level {mean:.3f}, "
          f"quietest half-second {min(blocks):.3f} at "
          f"{blocks.index(min(blocks)) * 0.5:.1f}s")
    if min(blocks) < mean * 0.25:
        print(f"  DEAD AIR: {len(quiet)} half-seconds under a quarter of "
              f"the mean, at {[round(i * 0.5, 1) for i in quiet]}")
        ok = False
    tail = rms(buf[-cc.RATE:])
    head = rms(buf[:cc.RATE])
    print(f"  the seam: {tail:.3f} into {head:.3f}")
    if tail < mean * 0.3 or head < mean * 0.3:
        print("  the loop fades out and in across its own join")
        ok = False
    if max(abs(v) for v in buf) >= 32760:
        print("  the loop clips")
        ok = False

    for name in ("click", "page", "tape", "flip", "coin", "bell", "level",
                 "new", "legend", "purr", "thud"):
        snd = cc.sound(name)
        if snd is None:
            print(f"  {name} did not build")
            ok = False
            continue
        v = samples(snd)
        lvl = rms(v)
        print(f"    {name:<7} {len(v) / cc.RATE:>5.2f}s  level {lvl:.3f}")
        if lvl < 0.01:
            print(f"  {name} is silent")
            ok = False
        if len(v) / cc.RATE > 3.0:
            print(f"  {name} runs for longer than a sound effect should")
            ok = False
    print("  score:", "ok" if ok else "FAILED")
    return ok


def flow():
    """Drive the real Game through a whole loop, by pressing its buttons.

    Not the state object - the Game. Everything here goes through the
    same `press` that a click goes through, so a button whose key is
    wired to nothing fails here rather than in someone's hands.
    """
    screen = pygame.display.set_mode((cc.W, cc.H))
    g = cc.Game(screen)
    g.state = cc.State()
    g.area = "study"
    g.room = cc.CatRoom()
    ok = True

    def tap(key):
        """Find a live button with this key on the current screen, press it."""
        g.draw()
        for b in g.buttons:
            if b.key == key and b.enabled:
                g.press(b.key)
                return True
        print(f"  no live button {key} on screen {g.scene!r}")
        return False

    ok &= tap(("laptop", None))
    if g.scene != "shop":
        print("  the laptop did not open the website")
        ok = False
    ok &= tap(("product", "sack"))
    ok &= tap(("place", None))
    if len(g.state.orders) != 1:
        print("  placing an order did not put anything in the post")
        ok = False
    if g.state.money > 0.01:
        print(f"  the first sack left {cc.money(g.state.money)} behind")
        ok = False

    # the order should be in the catalogue tab as well as the orders tab
    g.tab = "orders"
    g.draw()
    for _ in range(400):                 # 40 seconds, a sack is 25
        g.update(0.1)
    if g.state.orders or not g.state.parcels:
        print("  a 25s parcel had not arrived after 40 seconds")
        ok = False

    ok &= tap(("scene", "room"))
    if [b for b in g.buttons if b.key == ("mat", None)]:
        print("  the mat is reachable from the desk, not just the hall")
        ok = False
    ok &= tap(("go", "hall"))
    g.pan = 0.0
    ok &= tap(("mat", None))
    if g.scene != "open":
        print("  the mat did not open the parcel")
        ok = False
    ok &= tap(("cut", None))
    if len(g.pulls) != cc.BY_PACK["sack"].cards:
        print(f"  a sack held {len(g.pulls)} cards, not "
              f"{cc.BY_PACK['sack'].cards}")
        ok = False
    ok &= tap(("flipall", None))
    ok &= tap(("done", None))
    if g.scene != "room" or not g.state.cards:
        print("  the cards did not reach the binder")
        ok = False
    if g.state.income <= 0:
        print("  a cat in the binder is earning nothing")
        ok = False

    # a parcel walked away from while it is still taped must survive it
    g.state.parcels.append(("box", 1))
    g.area = "hall"
    ok &= tap(("mat", None))
    ok &= tap(("leave", None))
    if len(g.state.parcels) != 1:
        print("  leaving a taped parcel lost it off the mat")
        ok = False
    ok &= tap(("mat", None))
    ok &= tap(("cut", None))
    ok &= tap(("flipall", None))
    ok &= tap(("done", None))

    # walking: the slide has to run down on its own, and the room you
    # are standing in has to survive a save
    g.go("room")
    g.area = "study"
    ok &= tap(("go", "cats"))
    if g.area != "cats" or g.pan <= 0:
        print("  walking to the cat room did not start the walk")
        ok = False
    g.draw()                             # the two-room slide frame
    for _ in range(30):
        g.update(0.05)
    if g.pan != 0:
        print("  the walk never finished")
        ok = False
    if cc.State.from_dict(g.state.to_dict()).area != "cats":
        print("  the room you were standing in was not saved")
        ok = False
    g.go_area("study")
    g.pan = 0.0

    # a parcel of more than twenty cards opens a pack at a time
    g.go_area("hall")                           # the post is in the hall
    g.pan = 0.0
    g.state.parcels.append(("shelf", 3))        # 102 cards, six packs
    ok &= tap(("mat", None))
    ok &= tap(("cut", None))
    if len(g.this_pack()) != cc.PACK_SIZE:
        print(f"  the first pack held {len(g.this_pack())} cards, not "
              f"{cc.PACK_SIZE}")
        ok = False
    seen = 0
    guard = 0
    while guard < 40:
        guard += 1
        g.draw()
        if [b for b in g.buttons if b.key == ("flipall", None)]:
            tap(("flipall", None))
            seen += len(g.this_pack())
        elif [b for b in g.buttons if b.key == ("nextpack", None)]:
            tap(("nextpack", None))
        else:
            break
    if seen != len(g.pulls):
        print(f"  walked {seen} cards of a {len(g.pulls)}-card parcel")
        ok = False
    if cc.packs_in(len(g.pulls)) != 6:
        print(f"  102 cards came to {cc.packs_in(len(g.pulls))} packs")
        ok = False
    ok &= tap(("done", None))
    g.go_area("study")                          # the binder is on the desk
    g.pan = 0.0

    ok &= tap(("binder", None))
    # The binder runs to five pages at a hundred breeds, and the first
    # card out of a parcel is on whichever of them its rarity puts it on.
    # Taking the first key and clicking it blind passed four times in five
    # and failed on the fifth, which is the worst way for a test to be
    # wrong - so it turns pages until it finds the card, and the paging is
    # part of what is being tested.
    first = list(g.state.cards)[0]
    page, pages = 0, 0
    while page < 12:
        g.draw()
        pages = max(pages, len([b for b in g.buttons
                                if isinstance(b.key, tuple)
                                and b.key[0] == "page"]))
        if [b for b in g.buttons if b.key == ("pick", first)]:
            break
        page += 1
        if not tap(("page", page)):
            break
    print(f"  the binder is {pages} pages; {first} is on page {page + 1}")
    ok &= tap(("pick", first))
    if g.pick != first:
        print("  clicking a card in the binder did not open it")
        ok = False
    g.draw()
    if [b for b in g.buttons if b.key == ("scene", "room")]:
        print("  the room is still clickable behind the open card")
        ok = False
    ok &= tap(("pick", first))       # the card closes itself
    ok &= tap(("scene", "room"))

    # and the one that is only reachable with money
    g.state.money = 60_000.0
    g.go("shop")
    g.tab = "club"
    before = g.state.slots
    ok &= tap(("club", None))
    if g.state.slots != before + 1:
        print("  joining the club did not add a parcel to the round")
        ok = False
    print("  flow:", "ok" if ok else "FAILED")
    return ok


def _spoken(g, draw):
    """Every string a screen prints, caught on its way to the surface."""
    said = []
    real = cc.text

    def spy(surf, string, *a, **k):
        said.append(str(string))
        return real(surf, string, *a, **k)

    cc.text = spy
    try:
        draw()
    finally:
        cc.text = real
    return said


def counts():
    """A number the player is shown must come from the data.

    Written against a bug that was visible for three features: the label
    on the binder in the study said 24 OF 24 while the binder itself said
    24 of 36, because `_binder` had `total=24` as a default argument from
    the day there were twenty-four breeds. Nothing raises when a literal
    goes stale - it just quietly keeps telling you the old number.
    """
    screen = pygame.display.set_mode((cc.W, cc.H))
    rng = random.Random(8)
    g = cc.Game(screen)
    g.state = cc.State()
    g.state.open_pack(cc.BY_PACK["crate"], 12, rng)
    g.state.cards["kam"] = cc.Card(level=3)      # one off the street
    g.area = "study"
    g.pan = 0.0
    ok = True

    said = _spoken(g, g.draw)
    want = f"{g.state.owned} of {len(cc.BREEDS)}"
    if want not in said:
        stale = [t for t in said if " of " in t and "/" not in t]
        print(f"  the binder in the room never says {want!r}; it says "
              f"{stale}")
        ok = False
    print(f"  the room says {want!r} with {len(cc.BREEDS)} breeds in the "
          f"table")

    g.go("binder")
    said = _spoken(g, g.draw)
    head = [t for t in said if "breeds" in t]
    if not head or f"of {len(cc.BREEDS)} breeds" not in head[0]:
        print(f"  the binder header says {head}")
        ok = False
    else:
        print(f"  the binder says {head[0]!r}")
    if any(str(len(cc.BREEDS)) not in t and "breeds" in t for t in head):
        print("  a header count does not match the breed table")
        ok = False

    # the strays must not be counted among the catalogue breeds anywhere
    if f"{g.state.owned + 1} of {len(cc.BREEDS)}" in " ".join(said):
        print("  a stray is being counted as a catalogue breed")
        ok = False
    print("  counts:", "ok" if ok else "FAILED")
    return ok


def layout():
    """No click target may cover the thing it is a target for.

    The repo has lost a shop screen and a row of save slots to exactly
    this: an invisible Button that still paints a panel over the card it
    sits on. `Button.draw` returns early for style "hit", and this is
    what checks that every hand-drawn card is still using that style.
    """
    screen = pygame.display.set_mode((cc.W, cc.H))
    rng = random.Random(2)
    g = cc.Game(screen)
    g.state = cc.State()
    g.state.open_pack(cc.BY_PACK["lot"], 4, rng)
    g.state.money = 9_000.0
    ok = True
    for scene, setup in (("room", None),
                         ("room", lambda: setattr(g, "area", "hall")),
                         ("room", lambda: setattr(g, "area", "cats")),
                         ("shop", None),
                         ("shop", lambda: setattr(g, "product", "crate")),
                         ("shop", lambda: (setattr(g, "product", None),
                                           setattr(g, "tab", "room"))),
                         ("shop", lambda: setattr(g, "tab", "home")),
                         ("shop", lambda: setattr(g, "tab", "club")),
                         ("shop", lambda: (setattr(g, "site", "purrbay"),
                                           setattr(g.state, "money", 10 ** 9))),
                         ("shop", lambda: setattr(g, "site", "meowrder")),
                         ("binder", None), ("open", None)):
        if scene == "open":
            g.open_pack_key, g.open_qty = "crate", 1
            g.cut = False
            g.pulls = []
            g.flipped = 0
            g.cut_tape()
            g.lid = g.deal = 1.0
        g.go(scene)
        if setup:
            setup()
        g.pan = 0.0
        for _ in range(40):              # let the cat room fill up first
            g.update(0.05)
        g.pan = 0.0
        g.draw()
        drawn = [b for b in g.buttons if b.style != "hit"]
        hits = [b for b in g.buttons if b.style == "hit"]
        for a in drawn:
            for b in hits:
                if a.rect.colliderect(b.rect) and a.key != b.key:
                    print(f"  {scene}: drawn button {a.key} overlaps hit "
                          f"area {b.key}")
                    ok = False
        for i, a in enumerate(drawn):
            for b in drawn[i + 1:]:
                if a.rect.colliderect(b.rect):
                    print(f"  {scene}: two drawn buttons overlap: "
                          f"{a.key} and {b.key}")
                    ok = False
        # a cat may hang half off the edge of the window; a button that
        # is entirely outside it is a click target nobody can reach
        screen = pygame.Rect(0, 0, cc.W, cc.H)
        for b in g.buttons:
            if not screen.colliderect(b.rect):
                print(f"  {scene}: {b.key} is off the screen at "
                      f"{tuple(b.rect)}")
                ok = False
            elif b.style != "hit" and not screen.contains(b.rect):
                print(f"  {scene}: {b.key} hangs off the edge at "
                      f"{tuple(b.rect)}")
                ok = False
        print(f"  {scene:<6} {g.area if scene == 'room' else '':<6} "
              f"{len(drawn):>2} buttons, {len(hits):>2} hit areas")
    print("  layout:", "ok" if ok else "FAILED")
    return ok



def convention():
    """The calendar, the door, and the three tables behind it.

    The whole feature rests on two rules that are easy to break by
    accident: the hall exists on exactly one day in seven, and each table
    gives out exactly one pack per convention. Both of them are a single
    comparison in the code, and a single comparison is the kind of thing a
    later change walks over without anyone noticing until the player is
    standing in an empty hall on a Tuesday with nine packs in their bag.
    """
    ok = True
    screen = pygame.display.set_mode((cc.W, cc.H))
    # which second of play is a convention, and which is not, is the
    # calendar's business - the test asks it rather than counting days
    # itself, which is how it broke the first time the week moved.
    on = next(cc.DAY * d + 60 for d in range(14)
              if cc.convention_open(cc.DAY * d + 60))
    off = next(cc.DAY * d + 60 for d in range(14)
               if not cc.convention_open(cc.DAY * d + 60))
    print(f"  day one is a {cc.DAY_NAMES[cc.weekday_of(0)]}; the first "
          f"convention is {cc.clock_str(cc.until_convention(0))} in")

    # -- one day in seven, and the right one -----------------------------
    open_days = []
    for d in range(21):
        t = cc.DAY * d + cc.DAY * 0.5
        if cc.convention_open(t):
            open_days.append((d, cc.weekday_of(t)))
    want = [(d, cc.CONVENTION_DAY) for d in range(21)
            if (d + cc.WEEK_START) % 7 == cc.CONVENTION_DAY]
    print(f"  open on days {[d for d, _ in open_days]} of 21 - "
          f"{cc.DAY_NAMES[cc.CONVENTION_DAY]}s")
    if open_days != want:
        print(f"  the hall is open on the wrong days: {open_days}")
        ok = False
    # and it is shut the rest of the time, at every hour of the day
    shut = off
    for frac in (0.0, 0.01, 0.25, 0.5, 0.75, 0.99):
        if cc.convention_open(shut + cc.DAY * frac):
            print(f"  the hall is open on a {cc.DAY_NAMES[cc.weekday_of(shut)]}")
            ok = False
            break
    # the countdown has to land on the door opening, not near it
    for d in (0, 1, 4, 5, 6, 9):
        t = cc.DAY * d + 11.0
        left = cc.until_convention(t)
        if cc.convention_open(t):
            if left != 0:
                print(f"  day {d}: open now but says {left:.0f}s to go")
                ok = False
            continue
        if left <= 0 or not cc.convention_open(t + left + 0.5):
            print(f"  day {d}: {left:.0f}s to go does not reach a convention")
            ok = False

    # -- the five they print for the hall --------------------------------
    # The whole claim being made is "nowhere else", so the test is the
    # negative one: open a great many of everything that is not a
    # convention pack and prove not one of them can produce one.
    rng = random.Random(21)
    loose = 0
    for pk in cc.PACKS:
        if pk.shelf == "convention":
            continue
        st = cc.State()
        for _ in range(200):
            for pull in st.open_pack(pk, 1, rng):
                if pull.breed.rarity == cc.R_EXPO:
                    loose += 1
    print(f"  {len(cc.EXPO_BREEDS)} printed for the hall; {loose} of them "
          f"came out of a pack that is not from it")
    if loose:
        ok = False
    # nor off the resale site, at any price, on any day
    full = cc.State()
    for br in cc.ALL_BREEDS:
        full.cards[br.key] = cc.Card(level=4)
    for day in range(200):
        full.played = cc.DAY * day
        full.lots = []
        full.refresh_lots()
        for lot in full.lots:
            if lot.kind == "card" and cc.BY_KEY[lot.key].rarity == cc.R_EXPO:
                print(f"  day {day}: {cc.BY_KEY[lot.key].name} is on the "
                      f"resale site")
                ok = False
    # ... and they DO come out of the hall's own packs
    st = cc.State()
    seen = {}
    for _ in range(300):
        for pk in ("expo", "judge", "scalp"):
            for pull in st.open_pack(cc.BY_PACK[pk], 1, rng):
                if pull.breed.rarity == cc.R_EXPO:
                    seen[pull.breed.key] = seen.get(pull.breed.key, 0) + 1
    rate = sum(seen.values()) / 300.0
    print(f"  {rate:.2f} of them per convention, if you win all three tables")
    missed = [b.name for b in cc.EXPO_BREEDS if b.key not in seen]
    if missed:
        print(f"  never came out of anything: {missed}")
        ok = False
    if not 1.0 <= rate <= 4.0:
        print(f"  {rate:.2f} a convention is the wrong side of a chase")
        ok = False
    # the binder counts them on their own, or it reads "104 of 100"
    st2 = cc.State()
    for br in cc.EXPO_BREEDS:
        st2.cards[br.key] = cc.Card(level=cc.MAX_LEVEL)
    if st2.owned or st2.retired:
        print(f"  five from the hall count as {st2.owned} of the catalogue "
              f"and {st2.retired} retired")
        ok = False
    if st2.expo_owned != len(cc.EXPO_BREEDS):
        print("  the hall counter does not count them")
        ok = False

    # -- the door --------------------------------------------------------
    g = cc.Game(screen)
    g.state = cc.State()
    g.state.played = off                 # a day it is shut
    g.was_conv = g.state.convention()
    g.go_area("conv")
    if g.area == "conv":
        print("  you can walk into the hall on a day it is shut")
        ok = False
    g.state.played = on
    g.go_area("conv")
    if g.area != "conv":
        print("  you cannot walk into the hall on the day it is open")
        ok = False

    # the clock running past midnight has to put you back in the flat
    g.state.played = on + cc.DAY
    g.was_conv = True
    g.update(0.05)
    if g.area == "conv":
        print("  the hall stayed open past the end of the convention")
        ok = False
    # and a game that walks in without ever seeing the door shut - a save
    # loaded in the hall, a clock pushed on - comes out of it too
    g.state.played = on
    g.go_area("conv")
    g.state.played = on + cc.DAY * 2
    g.was_conv = False
    g.update(0.05)
    if g.area == "conv":
        print("  the hall stayed open after the convention ended")
        ok = False

    # -- one go per table, per convention --------------------------------
    for key, title, who, pack_key, game, blurb in cc.STALLS:
        g = cc.Game(screen)
        g.state = cc.State()
        g.state.played = on
        g.state.money = 500000
        g.go_area("conv")
        g.state.conv_refresh()
        g.press(("stall", key))
        if g.scene != "mini":
            print(f"  {key}: pressing the stall did not start a game")
            ok = False
            continue
        rounds = _play_mini(g, win=True)
        g.press(("mini", "leave"))
        got = len(g.state.parcels)
        g.press(("stall", key))          # and again, same day
        if g.scene == "mini":
            print(f"  {key}: you can play it twice at one convention")
            ok = False
            g.mini = None
            g.go("room")
        if len(g.state.parcels) != got:
            print(f"  {key}: a second go handed out a second pack")
            ok = False
        print(f"    {key:<6} won in {rounds} presses -> "
              + (g.state.parcels[-1][0] if g.state.parcels else "nothing"))
        if not g.state.parcels:
            print(f"  {key}: winning gave you nothing")
            ok = False
        elif g.state.parcels[-1][0] != pack_key:
            print(f"  {key}: gave out {g.state.parcels[-1][0]}, not {pack_key}")
            ok = False
        # next week it is open again
        g.state.played += cc.DAY * 7
        g.state.conv_refresh()
        if g.state.conv_played(key):
            print(f"  {key}: still closed at the next convention")
            ok = False

    # -- losing ----------------------------------------------------------
    for key, want_pack in (("queue", False), ("fake", False), ("scalp", True)):
        g = cc.Game(screen)
        g.state = cc.State()
        g.state.played = on
        g.state.money = 500000
        g.go_area("conv")
        g.state.conv_refresh()
        g.press(("stall", key))
        _play_mini(g, win=False)
        before = g.state.money
        g.press(("mini", "leave"))
        held = len(g.state.parcels)
        print(f"    {key:<6} lost -> {held} parcel(s), "
              f"${before - g.state.money:,.0f} out of pocket")
        if bool(held) != want_pack:
            print(f"  {key}: losing gave you {held} packs, wanted "
                  f"{int(want_pack)}")
            ok = False
        if not g.state.conv_played(key):
            print(f"  {key}: losing left the table open")
            ok = False

    # the scalper's two prices, which is the whole game at his table
    g = cc.Game(screen)
    g.state = cc.State()
    g.state.played = on
    g.state.money = 500000
    g.go_area("conv")
    g.state.conv_refresh()
    g.press(("stall", "scalp"))
    g.mini.secret = 30
    g.mini.guess = 30
    start = g.state.money
    g.press(("mini", "offer"))
    g.press(("mini", "leave"))
    paid = start - g.state.money
    face = cc.BY_PACK["scalp"].price * cc.SCALP_MULT * 0.30
    full = cc.BY_PACK["scalp"].price * cc.SCALP_MULT
    print(f"    haggled to 30% and paid ${paid:,.0f}; he was asking "
          f"${full:,.0f}")
    if abs(paid - face) > 1:
        print(f"  a 30% offer that lands should cost ${face:,.0f}")
        ok = False

    # -- and none of it is on the website --------------------------------
    g = cc.Game(screen)
    g.state = cc.State()
    g.state.money = 10 ** 9
    seen = set()
    for shelf in cc.SHELVES:
        g.go("shop")
        g.shelf = shelf
        g.draw()
        seen |= {b.key for b in g.buttons if isinstance(b.key, str)}
    bad = seen & {p.key for p in cc.CONV_PACKS}
    if bad:
        print(f"  the shop is selling {sorted(bad)}")
        ok = False
    else:
        print("    the shop sells none of the three")

    print("  convention:", "ok" if ok else "FAILED")
    return ok


def _play_mini(g, win):
    """Press buttons at a minigame until it is over, winning or losing on
    purpose. Returns how many presses it took."""
    presses = 0
    while g.mini is not None and not g.mini.done and presses < 60:
        presses += 1
        m = g.mini
        if m.kind == "queue":
            lo, hi = m.band_rect()
            m.pos = (lo + hi) * 0.5 if win else 0.0
            g.press(("mini", "stop"))
        elif m.kind == "fake":
            i = m.real_index()
            g.press(("mini", i if win else (i + 1) % len(m.cards)))
        else:
            if win:
                m.guess = m.secret - m.secret % 5
                if abs(m.guess - m.secret) > 2:
                    m.guess += 5
            else:
                m.guess = 5 if m.secret > 50 else 95
            g.press(("mini", "offer"))
    return presses



def bigroom():
    """Taking the flat next door.

    One button changes three numbers and the width of a surface, and a
    resident holds its spot as an INDEX into a tuple that just got
    longer. The failure that would not raise is a cat left sitting on
    furniture that is no longer at that index - so the indices are
    checked, not just the counts.
    """
    ok = True
    screen = pygame.display.set_mode((cc.W, cc.H))

    # the back room is bolted on the end, and nothing before it moved
    base = cc.ROOM_SPOTS[:cc.ROOM_BASE]
    if len(cc.ROOM_SPOTS) <= cc.ROOM_BASE:
        print("  there is no back room in the spot table")
        ok = False
    small = cc.State()
    big = cc.State()
    big.big_room = True
    print(f"  wall up: {cc.room_cap(small)} cats, "
          f"{cc.room_spot_count(small)} places, {cc.cats_wide(small)} wide")
    print(f"  wall down: {cc.room_cap(big)} cats, "
          f"{cc.room_spot_count(big)} places, {cc.cats_wide(big)} wide")
    for name, a, b in (("cats", cc.room_cap(small), cc.room_cap(big)),
                       ("places", cc.room_spot_count(small),
                        cc.room_spot_count(big)),
                       ("width", cc.cats_wide(small), cc.cats_wide(big))):
        if b <= a:
            print(f"  knocking the wall through did not add {name}")
            ok = False
    # every back-room place has to be somewhere a cat can get to, and
    # somewhere the room is actually drawn
    for i in range(cc.ROOM_BASE, len(cc.ROOM_SPOTS)):
        kind, x, y, face, size, label = cc.ROOM_SPOTS[i]
        if not cc.CATS_W < x < cc.CATS_W_BIG:
            print(f"  {label} is at x={x}, outside the back room")
            ok = False
        if kind not in cc.SPOT_ACTS:
            print(f"  {label} is a '{kind}', which nothing can do")
            ok = False
    names = [sp[5] for sp in cc.ROOM_SPOTS]
    if len(set(names)) != len(names):
        dupe = sorted({x for x in names if names.count(x) > 1})
        print(f"  two places share a name: {dupe}")
        ok = False

    # -- buying it -------------------------------------------------------
    g = cc.Game(screen)
    g.state = cc.State()
    g.state.money = cc.BIG_ROOM_PRICE - 1
    g.press(("bigroom", None))
    if g.state.big_room:
        print("  you can take the flat next door without paying for it")
        ok = False
    g.state.money = cc.BIG_ROOM_PRICE + 500
    g.press(("bigroom", None))
    if not g.state.big_room:
        print("  paying for the flat next door did not get you it")
        ok = False
    if abs(g.state.money - 500) > 0.01:
        print(f"  it cost {cc.BIG_ROOM_PRICE + 500 - g.state.money}, not "
              f"{cc.BIG_ROOM_PRICE}")
        ok = False
    before = g.state.money
    g.press(("bigroom", None))            # and not twice
    if g.state.money != before:
        print("  you can buy the same wall twice")
        ok = False

    # -- it survives being put down and picked up ------------------------
    d = g.state.to_dict()
    back = cc.State.from_dict(d)
    if not back.big_room:
        print("  the wall went back up when the game was saved")
        ok = False

    # -- and the room fills out ------------------------------------------
    rng = random.Random(8)
    for b in rng.sample(list(cc.BREEDS), 60):
        g.state.cards[b.key] = cc.Card(level=rng.randint(4, 9))
    room = cc.CatRoom()
    for _ in range(40):
        room.update(0.1, g.state, cc.room_cap(g.state))
    print(f"  {len(room.res)} cats in the room, {len(cc.cats_in(g.state, 'study'))}"
          f" on the desk, {len(cc.cats_in(g.state, 'hall'))} in the hall")
    if len(room.res) != cc.BIG_CAP:
        print(f"  the big room holds {len(room.res)}, not {cc.BIG_CAP}")
        ok = False
    # let them settle, then make sure the back room is not a showroom
    for _ in range(6000):
        room.update(0.1, g.state, cc.room_cap(g.state), 1780.0)
    back_room = [r for r in room.res if r.x > cc.CATS_W]
    print(f"  standing at the far end: {len(back_room)} of {len(room.res)} "
          f"cats are through the wall")
    if len(back_room) < 4:
        print("  nobody uses the room you just paid for")
        ok = False

    # -- and the wall going up does not strand anybody -------------------
    # (it cannot happen in play - but sync is the only place that knows
    # both numbers, so it is the only place that can be sure)
    g.state.big_room = False
    room.update(0.1, g.state, cc.room_cap(g.state))
    stuck = [r for r in room.res if r.spot >= cc.room_spot_count(g.state)]
    if stuck:
        print(f"  {len(stuck)} cats left sitting through a wall")
        ok = False
    else:
        print("  putting the wall back brings everybody with it")

    print("  bigroom:", "ok" if ok else "FAILED")
    return ok



def resale():
    """The second website.

    This is the one feature in the game that can turn money straight
    into binder, so the things that matter are the ones that stop it
    doing that too fast: the stock has to be fixed for the day and the
    same after a reload, a sealed box has to take a slot on the round
    like every other box, and the prices have to stay high enough that
    buying a collection is worse value than ordering one.
    """
    ok = True
    screen = pygame.display.set_mode((cc.W, cc.H))

    # -- most of them are scalpers ---------------------------------------
    honest = sum(sl[2] for sl in cc.SELLERS[:cc.SELLER_HONEST])
    total = sum(sl[2] for sl in cc.SELLERS)
    print(f"  {len(cc.SELLERS)} sellers, {honest / total * 100:.0f}% of "
          f"listings from somebody not taking the mick")
    if honest / total > 0.35:
        print("  most of them are supposed to be scalpers")
        ok = False
    if min(sl[1] for sl in cc.SELLERS) < 1.0:
        print("  somebody is selling below face value")
        ok = False

    # -- nothing off the books, ever -------------------------------------
    # Worst case for this is a player who has already found all five: the
    # first version kept them out of the breeds you are missing and let
    # them back in through the ones you own.
    full = cc.State()
    for br in cc.ALL_BREEDS:
        full.cards[br.key] = cc.Card(level=4)
    listed = 0
    for day in range(300):
        full.played = cc.DAY * day
        full.lots = []
        full.refresh_lots()
        for lot in full.lots:
            if lot.kind != "card":
                continue
            listed += 1
            if cc.BY_KEY[lot.key].rarity == cc.R_UNLISTED:
                print(f"  day {day}: {cc.BY_KEY[lot.key].name} is for sale")
                ok = False
    print(f"  {listed} cards listed over 300 days, none of them unlisted")

    # -- the stock is the day's, not the roll's --------------------------
    a = cc.State()
    a.played = cc.DAY * 4 + 30
    a.refresh_lots()
    b = cc.State()
    b.played = cc.DAY * 4 + 300          # same day, much later
    b.refresh_lots()
    if [l.to_row() for l in a.lots] != [l.to_row() for l in b.lots]:
        print("  the listings change within the day")
        ok = False
    c = cc.State()
    c.played = cc.DAY * 5 + 30
    c.refresh_lots()
    if [l.to_row() for l in a.lots] == [l.to_row() for l in c.lots]:
        print("  the listings are the same every day")
        ok = False
    # and they survive the round trip, so a reload is not a reroll
    a.money = 10.0
    back = cc.State.from_dict(a.to_dict())
    if [l.to_row() for l in back.lots] != [l.to_row() for l in a.lots]:
        print("  the listings do not survive being saved")
        ok = False
    back.refresh_lots()
    if [l.to_row() for l in back.lots] != [l.to_row() for l in a.lots]:
        print("  loading a save rerolls the listings")
        ok = False
    print(f"  {len(a.lots)} listings a day, fixed until the day turns")

    # -- a box takes a slot, a card does not -----------------------------
    st = cc.State()
    st.played = cc.DAY * 4 + 30
    st.money = 10 ** 9
    st.refresh_lots()
    cards = [l for l in st.lots if l.kind == "card"]
    packs = [l for l in st.lots if l.kind == "pack"]
    if not cards or not packs:
        print(f"  a day with {len(cards)} cards and {len(packs)} boxes on it")
        ok = False
        print("  resale:", "FAILED")
        return False
    before = len(st.orders)
    st.take_lot(packs[0])
    if len(st.orders) != before + 1:
        print("  a sealed box did not go in the post")
        ok = False
    # Not one of them may land instantly. The three the convention hands
    # out are posted in zero seconds because they are not posted at all,
    # and a listing for one of those went straight past the round.
    for pk in cc.PACKS:
        for qty in (1, 2):
            if cc.resale_ship(pk, qty) < cc.RESALE_MIN_SHIP - 0.01:
                print(f"  {pk.name} x{qty} arrives in "
                      f"{cc.resale_ship(pk, qty):.0f}s off the site")
                ok = False
            if cc.resale_ship(pk, qty) < cc.ship_time(pk, cc.POST, qty):
                print(f"  {pk.name} comes faster second hand than new")
                ok = False
    before = len(st.orders)
    got = st.take_lot(cards[0])
    if len(st.orders) != before:
        print("  a single card went in the post")
        ok = False
    if cards[0].key not in st.cards:
        print("  buying a card did not put it in the binder")
        ok = False
    elif st.cards[cards[0].key].level != cards[0].level:
        print(f"  bought a level {cards[0].level} and got a level "
              f"{st.cards[cards[0].key].level}")
        ok = False
    print(f"  bought {got.breed.name} at level {got.level} off "
          f"{cc.SELLERS[cards[0].seller][0]}")
    if st.take_lot(cards[0]) is not None:
        print("  the same listing sold twice")
        ok = False

    # the round filling up stops the boxes and nothing else
    st2 = cc.State()
    st2.played = cc.DAY * 4 + 30
    st2.money = 10 ** 9
    st2.refresh_lots()
    pk = [l for l in st2.lots if l.kind == "pack"][0]
    cd = [l for l in st2.lots if l.kind == "card"][0]
    while len(st2.orders) < st2.slots:
        st2.orders.append(cc.Order(0, "sack", 1, 99.0, 0.0, 0))
    if st2.can_take(pk):
        print("  a box went on a full round")
        ok = False
    if not st2.can_take(cd):
        print("  a full round stopped you buying a single card")
        ok = False

    # -- and you cannot buy what you cannot afford -----------------------
    st3 = cc.State()
    st3.played = cc.DAY * 4 + 30
    st3.refresh_lots()
    st3.money = min(st3.lot_cost(l) for l in st3.lots) - 1
    if any(st3.can_take(l) for l in st3.lots):
        print("  you can buy something you cannot afford")
        ok = False

    # -- it is a money hole, not a shortcut ------------------------------
    # The cheapest route to a card through the post, against the cheapest
    # route to one through the site. The site has to lose, and lose
    # badly, or there is no reason for the shop to exist.
    best = 0.0
    for pk in cc.PACKS:
        if pk.shelf not in cc.SHELVES or not pk.price:
            continue
        tot = sum(pk.weights)
        ev = sum(pk.weights[r] / tot * cc.RARITY[r][2]
                 for r in range(cc.SOLD_RARITIES))
        best = max(best, ev * pk.cards / pk.price)
    worst_site = 0.0
    for b in cc.BREEDS:
        for lv in (1, 5, 10):
            w = cc.card_worth(b, lv, False) * min(sl[1] for sl in cc.SELLERS)
            worst_site = max(worst_site, b.rate_at(lv) / w)
    print(f"  per pound: the shop buys {best:.5f}/s, the site at its "
          f"kindest {worst_site:.5f}/s  ({best / worst_site:.0f}x worse)")
    if worst_site > best:
        print("  the resale site is better value than the shop")
        ok = False

    # -- the page draws, and the two sites are both reachable ------------
    g = cc.Game(screen)
    g.state = st
    g.go("shop")
    g.press(("site", "purrbay"))
    if g.site != "purrbay":
        print("  the bookmark did not change site")
        ok = False
    g.draw()
    keys = {b.key for b in g.buttons}
    if ("site", "meowrder") not in keys:
        print("  there is no way back to the shop")
        ok = False
    if not any(k[0] == "lot" for k in keys if isinstance(k, tuple)):
        print("  nothing on the site can be bought")
        ok = False
    g.press(("site", "meowrder"))
    g.draw()
    if ("site", "purrbay") not in {b.key for b in g.buttons}:
        print("  there is no way to the resale site from the shop")
        ok = False

    print("  resale:", "ok" if ok else "FAILED")
    return ok



def merch():
    """Six things for the cards, and the loft on the resale site.

    Every one of these is a multiplier applied somewhere else in the
    game, which is the quietest kind of thing to get wrong: a bonus that
    is read but never applied looks exactly like a bonus that is applied,
    right up until somebody measures it. So each one is measured against
    the same state without it.
    """
    ok = True
    screen = pygame.display.set_mode((cc.W, cc.H))
    rng = random.Random(5)

    def stocked(keys=()):
        st = cc.State()
        for b in list(cc.BREEDS)[:40]:
            st.cards[b.key] = cc.Card(level=5)
        st.kit = set(keys)
        return st

    bare = stocked()
    print(f"  {len(cc.MERCH)} things, "
          f"{sum(1 for m in cc.MERCH if m.income)} of them income")
    if len({m.key for m in cc.MERCH}) != len(cc.MERCH):
        print("  two of them share a key")
        ok = False

    # -- income ----------------------------------------------------------
    gain = [m for m in cc.MERCH if m.income]
    with_all = stocked(m.key for m in gain)
    want = 1.0 + sum(m.income for m in gain)
    got = with_all.income / bare.income
    print(f"  all the paper: {bare.income:.2f}/s -> {with_all.income:.2f}/s "
          f"(x{got:.3f}, wanted x{want:.3f})")
    if abs(got - want) > 0.002:
        print("  the income bonuses do not reach the income")
        ok = False
    # and they stack with the flat rather than replacing it
    both = stocked(m.key for m in gain)
    both.things = {u.key for u in cc.UPGRADES}
    if abs(both.income / bare.income - want * both.comfort) > 0.01:
        print("  the flat and the paper do not stack")
        ok = False

    # -- shinies ---------------------------------------------------------
    tops = next(m for m in cc.MERCH if m.shiny != 1.0)
    a = stocked()
    b = stocked((tops.key,))
    pk = cc.BY_PACK["lot"]
    na = sum(1 for _ in range(260)
             for pull in a.open_pack(pk, 1, rng) if pull.shiny)
    nb = sum(1 for _ in range(260)
             for pull in b.open_pack(pk, 1, rng) if pull.shiny)
    cards = 260 * pk.cards
    print(f"  shinies in {cards} cards: {na} bare, {nb} with toploaders "
          f"(x{tops.shiny:.2f} on the dial)")
    if nb <= na:
        print("  the toploaders did not change the odds")
        ok = False

    # -- the price guide -------------------------------------------------
    guide = next(m for m in cc.MERCH if m.resale != 1.0)
    a = cc.State()
    a.played = cc.DAY * 3
    a.refresh_lots()
    b = cc.State.from_dict(a.to_dict())
    b.kit = {guide.key}
    pairs = [(a.lot_cost(x), b.lot_cost(y)) for x, y in zip(a.lots, b.lots)]
    worst = max(abs(q / p - guide.resale) for p, q in pairs if p)
    print(f"  the guide takes {(1 - guide.resale) * 100:.0f}% off every "
          f"listing (worst miss {worst * 100:.2f}%)")
    if worst > 0.02:
        print("  the price guide does not come off the price")
        ok = False

    # -- the loupe -------------------------------------------------------
    loupe = next(m for m in cc.MERCH if m.loupe)
    for kit, spare in ((set(), 0), ({loupe.key}, 1)):
        g = cc.Game(screen)
        g.state = cc.State()
        g.state.kit = set(kit)
        g.state.played = next(cc.DAY * d + 60 for d in range(14)
                              if cc.convention_open(cc.DAY * d + 60))
        g.go_area("conv")
        g.state.conv_refresh()
        g.press(("stall", "fake"))
        if g.mini.spare != spare:
            print(f"  loupe {bool(kit)}: {g.mini.spare} spare answers, "
                  f"wanted {spare}")
            ok = False
        # get it wrong once on purpose
        wrong = (g.mini.real_index() + 1) % len(g.mini.cards)
        g.press(("mini", wrong))
        if bool(kit) and g.mini.done:
            print("  the loupe did not cover a wrong answer")
            ok = False
        if not kit and not g.mini.done:
            print("  a wrong answer at the desk cost nothing")
            ok = False
    print("  the loupe is worth exactly one wrong answer at the desk")

    # -- the loft --------------------------------------------------------
    attic = cc.BY_PACK["attic"]
    days = 400
    seen = []
    for d in range(days):
        st = cc.State()
        st.played = cc.DAY * d
        st.refresh_lots()
        for lot in st.lots:
            if lot.key == "attic":
                seen.append((st.lot_cost(lot), lot.seller))
    print(f"  the loft is on {len(seen)} days in {days} "
          f"({len(seen) / days * 100:.0f}%), "
          f"${min(c for c, _ in seen):,.0f} to ${max(c for c, _ in seen):,.0f}")
    if not 0.04 <= len(seen) / days <= 0.25:
        print("  the loft is either never there or always there")
        ok = False
    if any(sel >= cc.SELLER_HONEST for _, sel in seen):
        print("  a scalper is selling their own childhood")
        ok = False
    # it must be a lot of cards and mostly cheap ones
    low = sum(attic.weights[r] for r in (cc.R_COMMON, cc.R_UNCOMMON))
    print(f"  {attic.cards} cards, {low * 100 // sum(attic.weights)}% of "
          f"them common or uncommon")
    if attic.cards < 100 or low / sum(attic.weights) < 0.8:
        print("  it is supposed to be a lot of cards and mostly rubbish")
        ok = False
    # and it must never be ordinary stock on either website
    if attic.shelf in cc.SHELVES:
        print("  the loft is on the website")
        ok = False
    # the real check: what it buys you is THROUGHPUT, not income
    def per_slot(pk):
        tot = sum(pk.weights)
        ev = sum(pk.weights[r] / tot * cc.RARITY[r][2]
                 for r in range(cc.SOLD_RARITIES))
        return pk.cards / cc.resale_ship(pk), ev * pk.cards / cc.resale_ship(pk)
    ac, ai = per_slot(attic)
    sc, si = per_slot(cc.BY_PACK["shelf"])
    print(f"  per second of a parcel slot: {ac:.3f} cards and {ai:.4f}/s, "
          f"against the Whole Shelf at {sc:.3f} and {si:.4f}/s")
    if ac <= sc:
        print("  the loft is not even a lot of cards")
        ok = False
    if ai >= si:
        print("  the loft is a better way to buy income than the shop")
        ok = False

    print("  merch:", "ok" if ok else "FAILED")
    return ok



def intro():
    """The four screens before the first pack.

    Two ways this goes wrong and neither raises: it plays again every
    time the game is opened, or it plays once and leaves you somewhere
    that is not the desk with no idea what to press. Both are checked by
    walking it rather than by reading the flag.
    """
    ok = True
    screen = pygame.display.set_mode((cc.W, cc.H))
    fresh = cc.load_state
    cc.load_state = lambda: cc.State()      # a brand new collection
    try:
        g = cc.Game(screen)
        if g.scene != "intro":
            print(f"  a new collection opens on {g.scene!r}, not the intro")
            ok = False
        # every screen has to say something, and say it in full
        for i, (head, body) in enumerate(cc.INTRO):
            g.beat, g.beat_t = i, 2.0
            g.update(0.05)
            g.draw()
            if not head.strip() or not body.strip():
                print(f"  screen {i + 1} is blank")
                ok = False
            if "{" in head.format(money=cc.money(cc.START_MONEY)):
                print(f"  screen {i + 1} has an unfilled slot in it")
                ok = False
        print(f"  {len(cc.INTRO)} screens, and the last one is "
              f"{cc.INTRO[-1][0].format(money=cc.money(cc.START_MONEY))!r}")

        # walking it all the way through lands you at the desk
        g = cc.Game(screen)
        presses = 0
        while g.scene == "intro" and presses < 20:
            g.draw()
            g.press(("intro", "next"))
            presses += 1
        print(f"  {presses} presses to the end, landing in {g.area!r}")
        if presses != len(cc.INTRO):
            print(f"  {presses} presses for {len(cc.INTRO)} screens")
            ok = False
        if g.scene != "room" or g.area != "study":
            print(f"  it ends in {g.scene}/{g.area}, not at the desk")
            ok = False
        if not g.state.seen_intro:
            print("  it did not record that it had been seen")
            ok = False
        # ... and the desk it lands on has the laptop on it
        g.draw()
        if ("laptop", None) not in {b.key for b in g.buttons}:
            print("  it leaves you somewhere with nothing to press")
            ok = False

        # skipping does the same, from the first frame
        g = cc.Game(screen)
        g.draw()
        if ("intro", "skip") not in {b.key for b in g.buttons}:
            print("  the first screen cannot be skipped")
            ok = False
        g.press(("intro", "skip"))
        if g.scene != "room" or not g.state.seen_intro:
            print("  skipping did not get out of it")
            ok = False

        # and it never plays twice
        saved = g.state.to_dict()
        cc.load_state = lambda: cc.State.from_dict(saved)
        again = cc.Game(screen)
        if again.scene == "intro":
            print("  it plays again every time the game is opened")
            ok = False
        else:
            print("  a collection that has seen it opens at the room")
    finally:
        cc.load_state = fresh

    print("  intro:", "ok" if ok else "FAILED")
    return ok


def main():
    args = sys.argv[1:] or ["all"]
    cmd = args[0]
    n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
    pygame.init()
    # Nothing in here may touch the collection on this machine. `flow`
    # presses PLACE ORDER on a real Game, and a real Game saves when you
    # do that - which is how a test harness quietly eats a save file.
    cc.save_state = lambda state: None
    # ... and never READ it: a Game built here would otherwise start in
    # whatever room the player left theirs in, which is how `flow` came
    # to fail only when it was run after something else had been played.
    def _fresh():
        # ... and a Game built on a brand new collection opens on the
        # intro, which is four screens none of these tests are about.
        # The one that IS about it turns this back off.
        st = cc.State()
        st.seen_intro = True
        return st

    cc.load_state = _fresh
    ok = True
    if cmd in ("smoke", "all"):
        ok &= smoke()
        print()
    if cmd in ("score", "all"):
        ok &= score()
        print()
    if cmd in ("intro", "all"):
        ok &= intro()
        print()
    if cmd in ("flow", "all"):
        ok &= flow()
        print()
    if cmd in ("counts", "all"):
        ok &= counts()
        print()
    if cmd in ("layout", "all"):
        ok &= layout()
        print()
    if cmd in ("strays", "all"):
        ok &= strays()
        print()
    if cmd in ("flat", "all"):
        ok &= flat()
        print()
    if cmd in ("convention", "all"):
        ok &= convention()
        print()
    if cmd in ("shelves", "all"):
        ok &= shelves()
        print()
    if cmd in ("value", "all"):
        pack_value()
        print()
    if cmd in ("dupes", "all"):
        ok &= dupe_ladder()
        print()
    if cmd in ("save", "all"):
        ok &= save_round_trip()
        print()
    if cmd in ("coats", "all"):
        ok &= coats()
        print()
    if cmd in ("numbers", "all"):
        ok &= numbers()
        print()
    if cmd in ("merch", "all"):
        ok &= merch()
        print()
    if cmd in ("resale", "all"):
        ok &= resale()
        print()
    if cmd in ("bigroom", "all"):
        ok &= bigroom()
        print()
    if cmd in ("behaviour", "all"):
        ok &= behaviour(20)
        print()
        ok &= behaviour(20, big=True)
        print()
    if cmd in ("grades", "all"):
        ok &= grades()
        print()
    if cmd in ("sameness", "all"):
        ok &= sameness()
        print()
    if cmd in ("economy", "all"):
        ok &= economy(n)
    print("\n", "ALL OK" if ok else "SOMETHING FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
