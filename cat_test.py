"""Harness for CAT CATALOGUE. Nothing here ships; it is how the game is
measured.

    python cat_test.py economy [n]   play n runs to a full binder, print it
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
    if len(cc.packs_on("standard")) + len(cc.packs_on("special")) \
            != len(cc.PACKS):
        print("  a pack is on neither shelf")
        ok = False
    # the ladder has to keep going up, on every axis
    last = None
    for p in cc.packs_on("standard"):
        tot = sum(p.weights)
        ev = sum(p.weights[r] / tot * cc.RARITY[r][2] for r in range(5))
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
        ev = sum(p.weights[r] / tot * cc.RARITY[r][2] for r in range(5))
        per = ev * p.cards
        print(f"{p.name:<22}{p.price:>6}{p.cards:>6}"
              f"{per:>14.3f}{per / p.price * 100:>11.3f}{p.ship:>7.0f}s")


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
           and state.sellable(p)]
    if not can:
        return None
    want = max(range(5), key=lambda r: state.missing(r))
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
    """
    pygame.display.set_mode((64, 64))
    SZ = 72
    masks = {}
    for b in cc.BREEDS:
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
    for i, a in enumerate(cc.BREEDS):
        for b in cc.BREEDS[i + 1:]:
            ma, mb = masks[a.key], masks[b.key]
            inter = sum(1 for x, y in zip(ma, mb) if x and y)
            union = sum(1 for x, y in zip(ma, mb) if x or y)
            same = inter / max(1, union)
            worst.append((same, a.name, b.name))
    worst.sort(reverse=True)
    print("  the ten most alike, by overlap of outline (1.00 is identical):")
    for same, a, b in worst[:10]:
        flag = "  <-- too close" if same > 0.94 else ""
        print(f"    {same:.3f}  {a} / {b}{flag}")
    print(f"  the two least alike: {worst[-1][0]:.3f}  "
          f"{worst[-1][1]} / {worst[-1][2]}")
    bad = [w for w in worst if w[0] > 0.94]
    print("  sameness:", "ok" if not bad else f"FAILED - {len(bad)} pairs")
    return not bad


# ---------------------------------------------------------------------------
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
    for b in cc.BREEDS:
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


def behaviour(minutes=20):
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
    room = cc.CatRoom()
    room.update(0.1, st, cc.ROOM_CAP)
    seen = {r.breed.key: {} for r in room.res}
    spots_used = set()
    moved = {r.breed.key: 0.0 for r in room.res}
    last_x = {r.breed.key: r.x for r in room.res}
    steps = int(minutes * 60 / 0.1)
    for _ in range(steps):
        room.update(0.1, st, cc.ROOM_CAP)
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
    missing = set(cc.ACT_WORD) - every
    if missing:
        print(f"  never happened at all: {sorted(missing)}")
        ok = False
    print(f"  {len(spots_used)} of {len(cc.ROOM_SPOTS)} spots were used, "
          f"{len(every)} of {len(cc.ACT_WORD)} activities happened")

    # The complaint this is written against was "the cats are not
    # moving", with three cats in a room twice as wide as the window.
    # They WERE moving; they were round the corner, and the ones in view
    # had settled for fifty seconds. So: with a small collection and the
    # camera where you come in, most of them have to be on screen and
    # something has to be happening.
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

    def samples(snd):
        return array("h", snd.get_raw())

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

    ok &= tap(("binder", None))
    first = list(g.state.cards)[0]
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
    cc.load_state = lambda: cc.State()
    ok = True
    if cmd in ("smoke", "all"):
        ok &= smoke()
        print()
    if cmd in ("score", "all"):
        ok &= score()
        print()
    if cmd in ("flow", "all"):
        ok &= flow()
        print()
    if cmd in ("layout", "all"):
        ok &= layout()
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
    if cmd in ("behaviour", "all"):
        ok &= behaviour(20)
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
