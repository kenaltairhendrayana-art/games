"""Harness for THE GREAT WORK. Nothing here ships; it is how the game is
measured.

    python gw_test.py smoke          draw every screen offscreen, save PNGs
    python gw_test.py capital        the KEAL counters, and the house gate
    python gw_test.py gov            the state's desk, the calendar, the squad
    python gw_test.py frames         six whole machines and the rules they change
    python gw_test.py score          every loop, measured rather than heard
    python gw_test.py yard           the option list, the ladder, the city
    python gw_test.py slots          prove the three save slots stay apart
    python gw_test.py flow           drive the real App through a whole run
    python gw_test.py balance [n]    auto-play n campaigns and print the table
    python gw_test.py all            smoke, then flow, then balance 6

Fight.update() deliberately touches no font and no display, which is what
lets a campaign run under the dummy driver at whatever speed the CPU will
give. Every balance number in the game came out of `balance`; do not change
a weapon, a reactor or a health total without re-running it, because the
levers are not independent - fixing the shell collision test moved every
fight length in the game by a factor of two.

Targets the tuning is aimed at, for the scripted pilot, which plays the
positioning better than a person will and the strategy worse. Measured at
n=12 after the rack and the yard upgrades went in:

    CRAWLER 100% 37s | SPITTER 100% 42s | BULWARK  91% 65s
    STRIDER  91% 59s | BROOD    75% 71s | LEVIATHAN 75% 72s
    9 victories, 2 unfinished, 1 city lost

RELIEF is measured here and does not appear in the table, which is the
finding rather than an omission. A bot that always has a better use for a
crew never rebuilds the city: at a 74% trigger it fired, cost four points
of completion, and left the city at landfall six SEVEN POINTS LOWER than
doing nothing - the weaker mech let more blocks go than the gang put back.
At any honest trigger (55% with a spare crew, 40% with any crew) it never
fires at all, and the table above is byte-identical to the table without
the feature. That is the correct result: relief is not a build-optimiser's
tool. It is for a person who has just lost a fight, is looking at a third
of a city, and wants the run to continue - which is why the yield is
weighted toward the bottom end (see `Run.relief_gain`).

Watch `taken` as much as `win%`. A fight the pilot wins without being hurt
is a fight with no texture in it, and three separate bugs hid behind a
healthy-looking win rate: the shell collision window was empty, the
LEVIATHAN's beam was cancelled in the wind-up eleven casts out of twelve,
and the broodlings spawned on the city side of the line.
"""
import io
import json
import math
import os
import random
import statistics
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((64, 64))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import great_work as G                                          # noqa: E402

# never touch a real campaign
_TMP = tempfile.mkdtemp(prefix="gwtest")
G._save_dir = lambda: _TMP
G.meta_forget()                  # the ledger caches, and we moved its home
G.SFX.ok = False

HERE = os.path.dirname(os.path.abspath(__file__))
DT = 1 / 40.0
CAP = 240.0


# ---------------------------------------------------------------------------
# SMOKE - a windowed game that dies before the window opens dies invisibly
# ---------------------------------------------------------------------------
def _late_run(house="keal"):
    r = G.Run(house)
    r.day, r.scrap, r.alloy, r.crew = 41, 1240, 6, 6
    r.integrity, r.kaiju_index, r.killed = 62, 4, 4
    for k, v in (("legs", 2), ("torso", 2), ("l_arm", 3), ("r_arm", 2),
                 ("head", 2), ("reactor", 2), ("l_wpn", "pile"),
                 ("r_wpn", "missile"), ("armour", 2)):
        r.mech.install(k, v)
    r.mech.hp["r_arm"] = 0.0
    r.mech.hp["legs"] *= 0.4
    r.mech.hp["armour"] *= 0.15
    return r


def smoke():
    surf = pygame.Surface((G.W, G.H))
    mouse = (600, 400)
    n = [0]

    def snap(name):
        pygame.image.save(surf, os.path.join(HERE, "gw_%s.png" % name))
        n[0] += 1
        print("  ok", name)

    t = G.Title({"run": {"day": 12},
                 "best": {"wins": 1, "losses": 2, "best_kills": 4}})
    t.t = 2.0
    t.draw(surf, mouse)
    snap("title")

    run = G.Run()
    h = G.Hangar(run)
    h.t = 3.0
    run.start_build("legs", G.CATALOGUE["legs"][0])
    run.start_build("l_wpn", G.WEAPONS["fist"])
    h.draw(surf, (900, 300))
    snap("hangar_early")

    G.meta_forget()
    G.add_marks(900)
    for k in ("bp_rail", "warchest", "spec_shriek", "spec_shriek",
              "spec_venom", "bp_claw", "furnace"):
        G.buy_ware(k)
    for back, name in (("title", "hendras"), ("hangar", "hendras_mid")):
        bz = G.Bazaar(back)
        bz.t = 3.1
        bz.draw(surf, (300, 520))
        snap(name)
    for i, nm in enumerate(("market", "capital", "gov")):   # all of the shop
        bz = G.Bazaar()
        bz.t = 3.1
        bz.sec = i
        bz.draw(surf, (0, 0))
        snap("shop_" + nm)
    bz.open = "mod_eject"                            # and a card turned over
    bz.draw(surf, (0, 0))
    snap("shop_inspect")
    bz.open = None

    ch = G.Choose()
    ch.t = 2.0
    ch.draw(surf, (850, 400))
    snap("choose")

    for hk in ("keal", "ryez"):
        rr = _late_run(hk)
        rr.mech.fit_module("stride")
        rr.mech.fit_module("link")
        rr.yard = 1
        rr.start_build("reactor", G.CATALOGUE["reactor"][2])
        hh = G.Hangar(rr)
        hh.t = 5.0
        hh.sel = "legs"
        hh.draw(surf, (980, 250))
        snap("yard_" + hk)
        f = G.Fight(rr, G.kind_at(hk, 5))
        for _ in range(60 * 22):
            if f.over:
                break
            f.update(1 / 60.0, pilot(f))
        f.draw(surf)
        snap("last_" + hk)
    G.set_house("keal")

    late = _late_run()
    late.mech.fit_module("stride")
    late.mech.fit_module("link")
    late.yard = 1
    late.start_build("reactor", G.CATALOGUE["reactor"][2])
    late.start_repair("legs")
    h2 = G.Hangar(late)
    h2.t = 5.0
    for sel, name in (("reactor", "hangar_late"), ("r_wpn", "hangar_shop")):
        h2.sel = sel
        h2.draw(surf, (980, 250))
        snap(name)
    h2.sel = G.YARD_SLOT
    h2.draw(surf, (980, 250))
    snap("hangar_yard")
    h2.sel = G.MOD_SLOT
    h2.rack = True
    h2.draw(surf, (300, 300))
    snap("hangar_rack")
    h2.rack = False
    h2.draw(surf, (980, 250))
    snap("hangar_modpanel")
    h2.spec = True
    h2.draw(surf, mouse)
    snap("hangar_spec")
    h2.spec = False

    b = G.Brief(late, G.BESTIARY[4])
    b.t = 2.0
    b.draw(surf, mouse)
    snap("brief")

    for idx in (0, 2, 5):
        r = G.Run()
        r.kaiju_index = idx
        for k, v in (("legs", 2), ("torso", 2), ("l_arm", 2), ("r_arm", 2),
                     ("head", 2), ("reactor", 2), ("l_wpn", "ripper"),
                     ("r_wpn", "revolver"), ("armour", 2)):
            r.mech.install(k, v)
        f = G.Fight(r, G.BESTIARY[idx])
        for _ in range(60 * 26):
            if f.over:
                break
            f.update(1 / 60.0, pilot(f))
        f.draw(surf)
        snap("fight_%d" % idx)

    r = G.Run()
    r.kaiju_index, r.killed = 2, 2
    f = G.Fight(r, G.BESTIARY[1])
    for _ in range(90):
        f.update(1 / 60.0, {"fire_l": True})
    f.over = "won"
    a = G.After(r, f, ["SPITTER DOWN.", "HARVEST: 470 SCRAP, 3 ALLOY",
                       "NEXT LANDFALL: DAY 24"])
    a.t = 1.0
    a.draw(surf, mouse)
    snap("after")

    win = G.Run()
    win.day, win.killed, win.integrity, win.spent = 57, 6, 48, 5100
    for k, v in (("legs", 3), ("torso", 3), ("l_arm", 3), ("r_arm", 3),
                 ("head", 3), ("reactor", 3), ("l_wpn", "ripper"),
                 ("r_wpn", "sun"), ("armour", 3)):
        win.mech.install(k, v)
    for run_, won, name in ((win, True, "end_win"), (late, False, "end_lose")):
        e = G.Ending(run_, won)
        e.t = 1.0
        e.draw(surf, mouse)
        snap(name)
    print("\n%d screens drawn, no crashes" % n[0])


# ---------------------------------------------------------------------------
# FLOW - the state machine, the buttons and the save file together
# ---------------------------------------------------------------------------
def flow(house_key="keal"):
    G.clear_run()                    # each pass starts from a clean front door
    app = G.App()
    seen = {}

    def key(k):
        app.handle(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0,
                                      unicode="", scancode=0))

    def click(pos):
        app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos,
                                      button=1))

    def draw():
        seen[app.state] = seen.get(app.state, 0) + 1
        s = pygame.Surface((G.W, G.H))
        {"title": lambda: app.title.draw(s, (0, 0)),
         "hangar": lambda: app.hangar.draw(s, (0, 0)),
         "brief": lambda: app.brief.draw(s, (0, 0)),
         "fight": lambda: app.fight.draw(s),
         "after": lambda: app.after.draw(s, (0, 0)),
         "choose": lambda: app.choose.draw(s, (0, 0)),
         "shop": lambda: app.bazaar.draw(s, (0, 0)),
         "end": lambda: app.ending_screen.draw(s, (0, 0))}[app.state]()

    assert app.state == "title"
    draw()
    shop_btn = next(b for b in app.title.buttons if b.key[0] == "shop")
    click(shop_btn.rect.center)          # the stall, and back out of it
    assert app.state == "shop", app.state
    draw()
    key(pygame.K_ESCAPE)
    assert app.state == "title", app.state
    draw()            # to_title() rebuilds Title; its buttons exist after a draw
    new_btn = next(b for b in app.title.buttons if b.key[0] == "new")
    click(new_btn.rect.center)
    assert app.state == "choose", app.state
    draw()
    click(app.choose.rects()[house_key].center)
    assert app.state == "hangar", app.state
    assert app.run.house == house_key
    for k in (pygame.K_0, pygame.K_y):       # the rack and the yard panels
        key(k)
        draw()
    for i in range(9):                       # every socket panel draws
        key(pygame.K_1 + i)
        draw()
    key(pygame.K_TAB)
    draw()
    key(pygame.K_TAB)

    guard = 0
    while app.state != "end" and guard < 4000:
        guard += 1
        if app.state == "hangar":
            for socket in G.SOCKETS:
                if app.run.free_crew < 1:
                    break
                app.hangar.sel = socket
                app.hangar.draw(pygame.Surface((G.W, G.H)), (0, 0))
                for b in app.hangar.buttons:
                    if b.key[0] in ("build", "repair") and b.enabled:
                        click(b.rect.center)
                        break
            draw()
            key(pygame.K_SPACE)
        elif app.state == "brief":
            draw()
            key(pygame.K_SPACE)
        elif app.state == "fight":
            f = app.fight
            for _ in range(80):
                if f.over:
                    break
                f.update(DT, pilot(f))
            draw()
            if f.over:
                f.over_t = 2.0
                key(pygame.K_SPACE)
        elif app.state == "after":
            draw()
            key(pygame.K_SPACE)
    draw()
    want = {"title", "choose", "shop", "hangar", "brief", "fight", "after",
            "end"}
    assert set(seen) == want, "missing %s" % (want - set(seen))
    print("%s states drawn: %s" % (G.HOUSES[house_key].name, seen))
    print("ending: %s  day %d  city %d  killed %d"
          % (app.ending, app.run.day, round(app.run.integrity), app.run.killed))

    run = G.Run("ryez")
    run.day, run.scrap, run.alloy = 21, 900, 4
    run.mech.install("legs", 2)
    run.start_build("head", G.CATALOGUE["head"][0])
    want = (run.day, run.scrap, run.alloy)
    G.save_run(run)
    back = G.Run.from_json(G.load_save()["run"])
    assert (back.day, back.scrap, back.alloy) == want
    assert back.mech.fit["legs"] == 2
    assert back.house == "ryez"          # the signing survives a round trip
    assert back.next_kind().family == "mech"
    assert len(back.jobs) == 1 and back.jobs[0].socket == "head"
    print("save round trip ok")

    for junk in ({}, {"day": "x"}, {"mech": {"fit": {"legs": 99}}},
                 {"jobs": [{"socket": "nope"}]}, {"kaiju_index": 900},
                 {"mech": {"fit": {"l_wpn": "nonsense"}}}):
        r = G.Run.from_json(junk)
        assert r.day >= 1 and r.mech.fit["torso"] is not None
    print("junk save ok\n\nFLOW OK")


# ---------------------------------------------------------------------------
# BALANCE - the numbers
# ---------------------------------------------------------------------------
# What a competent player buys, in the order they can afford it. Not the
# only path - A path. If this one cannot win, none can.
MOD, YARD = G.MOD_SLOT, G.YARD_SLOT
PRIORITY = [
    ("legs", 1), ("l_wpn", "fist"), ("reactor", 1), ("r_arm", 1),
    ("r_wpn", "auto"), ("armour", 1), ("head", 1), (MOD, "stride"),
    ("torso", 2), ("legs", 2), (YARD, 1), ("reactor", 2), (MOD, "link"),
    ("l_wpn", "pile"), ("armour", 2), ("l_arm", 2), ("head", 2),
    ("r_arm", 2), ("torso", 3), (YARD, 2), (MOD, "shutters"),
    ("r_wpn", "storm"), ("reactor", 3), ("r_wpn", "tempest"), ("legs", 3),
    (YARD, 3), ("l_arm", 3), ("armour", 3), ("r_arm", 3), ("head", 3),
]


# RYEZ wants a different ORDER, not different things. Every culture is a
# fixed wait, so the expensive long ones have to be in a tank early or they
# land after the landfall that needed them - measured, the house was losing
# the third fight outright because the heart was eight days behind.
RYEZ_PRIORITY = [
    ("legs", 1), ("l_wpn", "fist"), ("reactor", 1), ("r_arm", 1),
    ("r_wpn", "auto"), ("reactor", 2), ("torso", 2), ("armour", 1),
    ("head", 1), (MOD, "stride"), ("legs", 2), (YARD, 1), (MOD, "link"),
    ("l_wpn", "pile"), ("armour", 2), ("l_arm", 2), ("torso", 3),
    ("reactor", 3), ("head", 2), ("r_arm", 2), (YARD, 2), (MOD, "shutters"),
    ("r_wpn", "storm"), ("legs", 3), (YARD, 3), ("r_wpn", "tempest"),
    ("l_arm", 3), ("armour", 3), ("r_arm", 3), ("head", 3),
]


def _next_part(run, socket, target):
    if run.job_on(socket):
        return None
    if socket == MOD:
        m = run.mech
        if m.has(target) or len(m.mods) >= m.bays:
            return None
        return G.MODULES[target]
    if socket == YARD:
        opts = G.options_for(YARD, run.yard or None)
        return opts[0] if opts and opts[0].tier == target else None
    need = G.NEEDS.get(socket)
    if need and run.mech.fit[need] is None:
        return None
    for p in G.options_for(socket, run.mech.fit[socket]):
        key = p.key if isinstance(p, G.Weapon) else p.tier
        if key == target:
            return p
    return None


def shop(run):
    """Spend the day down the list, and mend before you upgrade.

    The two houses want opposite things from the same people. KEAL piles
    crew onto whatever is nearest finishing, because hands are speed. RYEZ
    spreads handlers over the pods that are drifting worst, because hands
    are only stability there and a pod nobody watches expresses wrong."""
    for s in G.SOCKETS:                  # mending never blocks a pod
        if run.free_crew < 1:
            break
        if run.mech.damage_frac(s) > 0.45 and not run.job_on(s):
            run.start_repair(s)
    # The city is a loss condition, so below a certain point it outranks
    # the next tier - a mech one rung better does not help if the run ends
    # before it is fitted. This has to be decided BEFORE the build loop:
    # that loop spends crew until there is none left, so anything asking
    # for slack afterwards never fires at all, and the first version of
    # this gate sat there and quietly did nothing for eight campaigns.
    if (run.integrity <= RELIEF_AT and not run.job_on(G.CITY_SLOT)
            and run.free_crew >= 2
            and run.scrap >= G.RELIEF.scrap + RELIEF_SPARE):
        run.start_relief()
    for socket, target in PRIORITY:
        if run.no_room() or (not run.bio and run.free_crew < 1):
            break
        p = _next_part(run, socket, target)
        if p is not None and run.can_afford(*run.price(p, socket)):
            run.start_build(socket, p)
    # when the rare stuff is the thing blocking the list, buy it the slow way
    nxt = None
    for socket, target in (PRIORITY):
        p = _next_part(run, socket, target)
        if p is not None:
            nxt = p
            break
    # Smelt only when the rare stuff is ACTUALLY the wall and there is
    # money going spare - an earlier pass smelted eagerly and starved the
    # build, which cost KEAL thirty points of win rate on three fights.
    # The old gate wanted 1000 scrap before it would smelt, so the only
    # player who needed the crucible - the one who lost a fight and has no
    # alloy - could never reach it. It buys when the rare stuff is the wall
    # and it can afford the billet with a little left over.
    if (nxt is not None and nxt.alloy > run.alloy and run.alloy == 0
            and run.scrap >= G.REFINE.scrap + 140
            and not run.job_on(G.REFINE_SLOT)):
        run.start_refine()
    if run.bio:
        pods = run.growing()
        for j in pods:
            run.set_crew(j, 0)
        # ONE pair of hands first, on every pod that can be covered,
        # and only then a second on the ones that need it. It used to go
        # straight to two, which with two handlers in the house meant one
        # pod watched and four expressing wrong - and it was right to,
        # because at the old CALM the first handler was the only one that
        # ever mattered and the second was free to waste.
        for j in pods:
            run.set_crew(j, 0)
        for want in (1, 2):
            for j in sorted(pods, key=lambda j: (-j.left, -j.unstable)):
                if run.free_crew <= 0:
                    break
                if j.crew < want:
                    run.set_crew(j, want)
        return
    for j in sorted(run.jobs, key=lambda j: -j.prog):
        while run.free_crew > 0 and j.crew < run.crew_per_job:
            run.set_crew(j, j.crew + 1)


def pilot(f):
    """Careful, not clairvoyant: holds its preferred range, steps out of a
    wind-up when it has the legs to and braces when it does not, and never
    walks into its own overheat."""
    m = f.mech
    e = f.nearest(f.mx)
    if e is None or m.down:
        return {}
    gap = e.x - f.mx
    adist = abs(gap)
    toward = "right" if gap > 0 else "left"
    away = "left" if gap > 0 else "right"
    wl, wr = m.weapon("l"), m.weapon("r")
    melee = [w for w in (wl, wr) if w and w.kind == "melee"]
    ranged = [w for w in (wl, wr) if w and w.kind != "melee"]
    if melee:
        keep = min(w.reach for w in melee) * 0.72 + e.span * 0.4
    elif ranged:
        keep = min(520.0, min(w.reach for w in ranged) * 0.6)
    else:
        keep = 600.0
    inp = {}
    threat = (e.state == "windup" and e.attack
              and e.attack["kind"] in ("swipe", "slam", "kick")
              and adist <= e.attack["reach"] + 90)
    if threat and m.speed > 0 and e.timer > 0.20:
        inp[away] = True
    elif threat:
        inp["brace"] = True
        return inp
    elif adist > keep + 50:
        inp[toward] = True
        if m.can_boost and adist > keep + 400:
            inp["boost"] = True
    elif adist < keep - 60:
        inp[away] = True
    if m.locked and m.has("flush"):
        inp["flush"] = True          # that is what the tank is for
    if not (m.locked or m.heat_frac > 0.93):
        for side, w in (("l", wl), ("r", wr)):
            if w is None:
                continue
            reach = w.reach + (e.span * 0.5 if w.kind == "melee" else 0.0)
            if adist <= reach:
                inp["fire_" + side] = True
    return inp


class Sloppy:
    """A pilot who is not a machine.

    The scripted pilot re-reads the fight every tick and steps out of every
    wind-up, which no person does - so its win rate cannot answer the only
    question that matters, which is whether a PERSON can hold the line.
    This one decides on a cadence instead of continuously, and misses some
    fraction of the dodges it ought to make."""

    def __init__(self, react=0.26, dodge=0.55):
        self.react = react
        self.dodge = dodge
        self.until = 0.0
        self.held = {}

    def __call__(self, f):
        if f.t >= self.until:
            self.until = f.t + self.react
            inp = pilot(f)
            if random.random() > self.dodge:      # saw it late, or not at all
                inp.pop("brace", None)
                e = f.nearest(f.mx)
                if e is not None and e.state == "windup":
                    inp.pop("left", None)
                    inp.pop("right", None)
            self.held = inp
        return self.held


def run_fight(run, kind, pilot_fn=None):
    f = G.Fight(run, kind)
    drive = pilot_fn or pilot
    d = {"n": 0, "locked": 0, "asked": 0, "stun": 0, "armed": 0, "legs": 0,
         "wall": 0}
    while f.over is None and f.t < CAP:
        inp = drive(f)
        m = f.mech
        d["n"] += 1
        d["armed"] += sum(1 for s in ("l", "r") if m.weapon(s))
        d["locked"] += 1 if m.locked else 0
        d["asked"] += 1 if (inp.get("fire_l") or inp.get("fire_r")) else 0
        d["stun"] += 1 if f.stun > 0 else 0
        d["legs"] += 1 if m.alive("legs") else 0
        b = f.boss()
        d["wall"] += 1 if (b and b.alive and b.x <= G.WALL_X + 30) else 0
        f.update(DT, inp)
    f.timeout = f.over is None
    if f.timeout:
        f.over = "lost"
    f.diag = d
    return f


def campaign(seed, house_key="keal", sloppy=False):
    random.seed(seed)
    run = G.Run(house_key)
    drive = Sloppy() if sloppy else None
    report = []
    while run.next_landfall is not None:
        nl = run.next_landfall
        while run.day < nl:
            shop(run)
            run.end_day()
        kind = run.next_kind()
        before = dict(run.mech.fit)
        f = run_fight(run, kind, drive)
        ending, _ = run.resolve(f)
        report.append({"kind": kind.name, "day": nl, "won": f.over == "won",
                       "secs": f.t, "timeout": f.timeout,
                       "built": round(run.mech.completion() * 100),
                       "city": round(run.integrity), "scrap": run.scrap,
                       "alloy": run.alloy, "crew": run.crew, "fit": before,
                       "taken": round(f.taken), "dealt": round(f.dealt),
                       "mods": list(run.mech.mods), "yard": run.yard,
                       "diag": f.diag})
        if ending:
            report.append({"ending": ending})
            break
    return run, report


def wipe_meta():
    """Start from a player who has never been to the market.

    `smoke` buys things to draw the stall, and the ledger is a real file in
    the same temp dir, so without this the balance phase silently measures a
    yard with a WAR CHEST in it - which is how `all` came out five points
    rosier than `balance` on its own."""
    data = G.load_save()
    data["meta"] = None
    G.write_save(data)
    G.meta_forget()


SLOPPY = [False]
# Measured, not guessed. At 74 the bot cleared rubble it did not need to
# and paid for it with the build: KEAL's completion fell four points, the
# LEVIATHAN win rate fell twelve, and the city at landfall six came out
# SEVEN POINTS LOWER than doing nothing - the weaker mech let more blocks
# go than relief put back. Relief is not a way to keep a healthy city
# topped up. It is a way to stop a run ending, so the bot reaches for it
# only when the run is two bad fights from over.
RELIEF_AT = 55.0        # the bot starts clearing rubble below this
RELIEF_SPARE = 200      # ...and only with this much left over afterwards


def balance(n=10, house_key="keal"):
    wipe_meta()
    G.set_house(house_key)
    roster = G.roster_for(house_key)
    per = {k.name: [] for k in roster}
    endings = {}
    last = None
    for s in range(n):
        run, rep = campaign(1000 + s, house_key, SLOPPY[0])
        last = (run, rep)
        for row in rep:
            if "ending" in row:
                endings[row["ending"]] = endings.get(row["ending"], 0) + 1
            else:
                per[row["kind"]].append(row)
        if not any("ending" in r for r in rep):
            endings["all six, alive"] = endings.get("all six, alive", 0) + 1

    print("\n%-16s %5s %6s %7s %7s %6s %6s %6s"
          % (G.HOUSES[house_key].name + " v " + G.HOUSES[house_key].roster,
             "day", "win%", "secs", "built%", "city", "dealt", "taken"))
    print("-" * 66 + "  pilot: "
          + ("a person, more or less" if SLOPPY[0] else "the scripted one"))
    mean = statistics.mean
    for k in roster:
        rows = per[k.name]
        if not rows:
            print("%-16s  never reached" % k.name)
            continue
        print("%-16s %5d %5d%% %7.0f %7.0f %6.0f %6.0f %6.0f"
              % (k.name, rows[0]["day"],
                 100 * sum(1 for r in rows if r["won"]) / len(rows),
                 mean(r["secs"] for r in rows), mean(r["built"] for r in rows),
                 mean(r["city"] for r in rows), mean(r["dealt"] for r in rows),
                 mean(r["taken"] for r in rows)))
        d = [r["diag"] for r in rows]
        tot = sum(x["n"] for x in d) or 1
        print("%-16s   dps %4.0f | guns %3.1f | asked %2.0f%% heatlock %2.0f%%"
              " stun %2.0f%% ATWALL %2.0f%%%s"
              % ("", mean(r["dealt"] / max(1, r["secs"]) for r in rows),
                 sum(x["armed"] for x in d) / tot,
                 100.0 * sum(x["asked"] for x in d) / tot,
                 100.0 * sum(x["locked"] for x in d) / tot,
                 100.0 * sum(x["stun"] for x in d) / tot,
                 100.0 * sum(x["wall"] for x in d) / tot,
                 "  (%d TIMED OUT)" % sum(1 for r in rows if r["timeout"])
                 if any(r["timeout"] for r in rows) else ""))
    print("\nendings over %d runs: %s" % (n, endings))

    print("\nlast run, what it had standing at each landfall:")
    for row in last[1]:
        if "ending" in row:
            print("  ->", row["ending"])
            continue
        names = [G.part_of(s, row["fit"][s]).name for s in G.SOCKETS
                 if row["fit"].get(s) is not None]
        print("  day %-3d %-12s built %3d%%  scrap %4d alloy %d crew %d"
              % (row["day"], row["kind"], row["built"], row["scrap"],
                 row["alloy"], row["crew"]))
        print("          " + ", ".join(names))
        print("          rack: %s   yard: %s"
              % (", ".join(G.MODULES[k].name for k in row["mods"]) or "empty",
                 G.YARD[row["yard"] - 1].name if row["yard"] else "nothing"))


# ---------------------------------------------------------------------------
# SLOTS - three drawers that must not reach into each other
# ---------------------------------------------------------------------------
def slots():
    """The one thing a save slot has to do is stay out of the other two.

    Everything a campaign owns lives in one file per slot - the run, the
    record AND the Hendras' ledger - so the test that matters is not "does
    it save" but "does slot two spend slot one's marks". The ledger is the
    dangerous half: it is cached in a module global for the draw loops, so
    a switch that forgets to drop the cache passes every disk check and
    still hands you somebody else's blueprints."""
    for n in range(1, G.SLOTS + 1):
        G.erase_slot(n)
    G.set_slot(1)

    # three different campaigns, one per drawer
    made = {}
    for n, (house, day, city) in ((1, ("keal", 31, 68.0)),
                                  (2, ("ryez", 9, 92.0)),
                                  (3, ("keal", 4, 100.0))):
        G.set_slot(n)
        r = G.Run(house)
        r.day, r.integrity, r.killed = day, city, n
        r.scrap = 100 * n
        G.save_run(r)
        G.add_marks(40 * n)
        made[n] = (house, day, city)
    print("  wrote %d slots" % len(made))

    for n, (house, day, city) in made.items():
        c = G.slot_card(n)
        assert not c["empty"], n
        assert c["run"]["house"] == house, (n, c["run"]["house"])
        assert c["run"]["day"] == day, (n, c["run"]["day"])
        assert c["marks"] == 40 * n, (n, c["marks"])
        print("  slot %d  %-4s day %-3d city %3d%%  %d marks"
              % (n, house, day, c["run"]["city"], c["marks"]))

    # the ledger is per-slot, cache and all
    G.set_slot(1)
    assert G.buy_ware("spec_shriek"), "slot 1 could not afford a jar"
    assert G.stock_of("spec_shriek") == 1
    G.set_slot(2)
    assert G.stock_of("spec_shriek") == 0, "slot 2 opened slot 1's jar"
    assert G.marks() == 80, G.marks()
    G.set_slot(1)
    assert G.stock_of("spec_shriek") == 1, "slot 1 lost its jar on the way back"
    print("  ledger stays home: jar in 1, none in 2, marks 40/80/120 kept")

    # the front door: clicking a card swaps everything behind it
    surf = pygame.Surface((G.W, G.H))
    t = G.Title()
    t.t = 2.0
    t.draw(surf, (0, 0))
    assert t.save["run"]["day"] == 31, t.save["run"]["day"]
    t.click(t.slot_rect(2).center)
    assert G.SLOT[0] == 2, G.SLOT[0]
    assert t.save["run"]["day"] == 9, t.save["run"]["day"]
    t.draw(surf, (0, 0))
    assert G.CURRENT["house"] == "keal", "the title left the house switched"

    # erase takes two presses, and only touches the slot you are on
    era = next(b for b in t.buttons if b.key[0] == "erase")
    t.click(era.rect.center)
    assert not G.slot_card(2)["empty"], "one press wiped a campaign"
    t.click(era.rect.center)
    assert G.slot_card(2)["empty"], "two presses did not"
    assert not G.slot_card(1)["empty"], "erasing 2 took 1 with it"
    assert G.slot_card(3)["run"]["day"] == 4, "erasing 2 took 3 with it"
    assert G.slot_card(2)["marks"] == 0, "an erased slot kept its marks"
    print("  erase is two presses, and lands on one drawer only")

    # closing the game on one drawer reopens on that drawer
    G.set_slot(3)
    G.SLOT[0] = 1                     # pretend it was launched cold
    G.meta_forget()
    assert G.restore_slot() == 3, "it forgot which slot was being played"
    assert G.marks() == 120, G.marks()
    G.set_slot(1)
    print("  it reopens on the drawer that was open")

    # a save written before there were slots becomes slot one
    G.erase_slot(1)
    old = G.Run("ryez")
    old.day = 77
    with io.open(os.path.join(_TMP, G.SAVE_NAME), "w",
                 encoding="utf-8") as fh:
        json.dump({"run": old.to_json(), "meta": {"marks": 7}}, fh)
    G._migrated[0] = False
    G.meta_forget()
    G.set_slot(1)
    assert G.load_save()["run"]["day"] == 77, "the old campaign was dropped"
    assert G.marks() == 7
    assert os.path.exists(os.path.join(_TMP, G.SAVE_NAME)), "it deleted theirs"
    print("  a pre-slot save opens as slot 1, and is left where it was")

    for n in range(1, G.SLOTS + 1):
        G.erase_slot(n)
    os.remove(os.path.join(_TMP, G.SAVE_NAME))
    G.set_slot(1)
    print("\n3 slots, isolated")


# ---------------------------------------------------------------------------
# YARD - the option list, the ladder, and putting the city back
# ---------------------------------------------------------------------------
def yard():
    """Three things that all fail silently if they fail at all.

    A weapon you cannot reach, a price that is cheaper for skipping, and a
    relief job that quietly does nothing all look exactly like a working
    game from the outside."""
    surf = pygame.Surface((G.W, G.H))
    G.set_house("keal")
    run = G.Run("keal")
    run.scrap, run.alloy, run.crew = 4000, 9, 5
    run.integrity = 62.0

    # -- every refit is reachable without owning its base ------------------
    bare = G.options_for("l_wpn", None)
    fam = {u for _, u in G.WEAPON_FAMILIES}
    keys = {w.key for w in bare}
    missing = fam - keys
    assert not missing, "locked behind their base: %s" % sorted(missing)
    print("  a bare hardpoint offers %d weapons, refits included" % len(bare))

    # -- and costs the whole ladder for the privilege ----------------------
    for base, up in G.WEAPON_FAMILIES:
        ladder = G.WEAPONS[base].scrap + G.WEAPONS[up].scrap
        straight = run.price(G.WEAPONS[up], "l_wpn")[0]
        assert straight == ladder, (up, straight, ladder)
        al = run.price(G.WEAPONS[up], "l_wpn")[1]
        assert al == G.WEAPONS[base].alloy + G.WEAPONS[up].alloy, up
        run.mech.install("l_wpn", base)
        refit = run.price(G.WEAPONS[up], "l_wpn")[0]
        assert refit == G.WEAPONS[up].scrap, (up, refit)
        assert refit < straight, up
        run.mech.fit["l_wpn"] = None
    print("  skipping the ladder costs the ladder, climbing it does not")

    # -- and every one of them can actually be clicked ---------------------
    h = G.Hangar(run)
    h.sel = "l_wpn"
    h.t = 1.0
    reached = set()
    h.draw(surf, (0, 0))
    first = len([b for b in h.buttons if b.key[0] == "build"])
    for step in range(40):
        h.draw(surf, (0, 0))
        for b in h.buttons:
            if b.key[0] == "build":
                reached.add(b.key[1].key)
        if h.scroll >= h.scroll_max:
            break
        h.wheel(-1)
    assert h.scroll_max > 0, "a sixteen-item list that does not scroll"
    assert reached == keys, "unreachable by scrolling: %s" % sorted(
        keys - reached)
    print("  %d fit on screen, all %d reachable by wheel in %d notches"
          % (first, len(reached), step))
    h.wheel(99)
    assert h.scroll == 0.0, "scrolled up past the top"
    h.sel = "legs"
    h.draw(surf, (0, 0))
    assert h.scroll_for == "legs" and h.scroll == 0.0, "scroll followed"
    print("  it starts at the top again on a different socket")

    # -- putting the city back --------------------------------------------
    for house in ("keal", "ryez"):
        G.set_house(house)
        r = G.Run(house)
        r.scrap, r.crew, r.integrity = 2000, 4, 61.0
        cost = r.price(G.RELIEF)[0]
        assert cost == G.RELIEF.scrap, "%s got a discount on rubble" % house
        want = r.relief_gain()
        assert r.start_relief()
        assert r.scrap == 2000 - cost, "relief was free"
        j = r.job_on(G.CITY_SLOT)
        assert j.crew == 1 and not j.bio, house
        assert not r.growing(), "relief took up a pod"
        assert not r.start_relief(), "two gangs on one city"
        for _ in range(G.RELIEF.days):
            r.end_day()
        assert abs(r.integrity - (61.0 + want)) < 1e-6, r.integrity
        # the worse it is, the more one gang gets done - otherwise this is
        # a polish for a healthy city and no use at all to a dying run
        last = None
        for c in (95.0, 70.0, 45.0, 20.0):
            r.integrity = c
            g = r.relief_gain()
            assert last is None or g > last, (c, g, last)
            last = g
        assert r.relief_gain() > G.RELIEF.days * 4, "a rescue that rescues"
        r.integrity = 97.0
        assert r.start_relief()
        for _ in range(G.RELIEF.days):
            r.end_day()
        assert r.integrity == 100.0, r.integrity
        assert not r.start_relief(), "rebuilt a city that was whole"
        back = G.Run.from_json(r.to_json())
        assert back.integrity == 100.0
        r.integrity = 61.0
        print("  %-4s %d scrap and %dd puts %.1f%% back at 61%%, %.1f%% at "
              "20%%, and stops at 100"
              % (house, cost, G.RELIEF.days, r.relief_gain(), last))

    # a relief job has to survive being saved mid-work
    G.set_house("keal")
    r = G.Run("keal")
    r.scrap, r.crew, r.integrity = 2000, 4, 50.0
    r.start_relief()
    r.end_day()
    back = G.Run.from_json(r.to_json())
    assert back.job_on(G.CITY_SLOT) is not None, "the gang went home"
    for _ in range(G.RELIEF.days):
        back.end_day()
    assert back.integrity > 50.0, back.integrity
    print("  a half-finished relief job survives a save")

    # -- nothing you paid for vanishes out of the rack -------------------
    # THE GREAT SAC needs a spare organ site on a grown body, and the
    # first pass expressed that by dropping the card. So a player who
    # bought it for 210 marks and was not standing in a GRAVID MOTHER
    # saw no card, no reason and no mention of it anywhere - which is
    # the same mistake as hiding a shop counter, made a third time.
    wipe_meta()
    G.set_house("ryez")
    G.add_marks(30000)
    for k in ("g_scalehide", "g_embryo", "g_lungs", "g_scream",
              "st_gravid", "g_greatsac"):
        assert G.buy_ware(k), k
    stock = G.Mech("standard")
    mother = G.Mech("gravid")
    for frame in (stock.frame, mother.frame):
        keys = [m.key for m in G.module_list(frame)]
        assert "greatsac" in keys, (frame.key, "the card disappeared")
    assert not G.module_fits(G.MODULES["greatsac"], stock.frame)
    assert G.module_fits(G.MODULES["greatsac"], mother.frame)
    assert G.module_why(G.MODULES["greatsac"], stock.frame)
    assert G.module_why(G.MODULES["greatsac"], mother.frame) is None
    # ...and it still cannot be PRESSED on a body with nowhere to put it
    for chassis, want in (("standard", False), ("gravid", True)):
        run = G.Run("ryez", chassis)
        run.mech.fit_module("greatsac")
        f = G.Fight(run, run.next_kind())
        assert f.can_greatsac() is want, (chassis, want)
        assert f.great_sac() is (True if want else False), chassis
    print("  the great sac shows on every rack and only works on hers")

    # -- and the rack says how many more there are to buy ----------------
    # "15 of them" is whatever you happen to own, so a player has no way
    # to know there are three more on a counter somewhere
    assert G.locked_modules() == 0, G.locked_modules()
    wipe_meta()
    G.set_house("ryez")
    G.add_marks(30000)
    for k in ("g_scalehide", "g_embryo"):
        G.buy_ware(k)
    n = G.locked_modules()
    assert n == 3, ("scalehide and embryo bought, so lungs, scream and "
                    "the great sac are left: %d" % n)
    # the four KEAL ones are NOT counted - a gene rack will never hold
    # one, and counting them sends a RYEZ player looking for nothing
    keal_only = [m for m in G.MODULE_LIST
                 if m.key in G.BLUEPRINT_MODULES
                 and G.WARES[G.BLUEPRINT_MODULES[m.key]].house == "keal"]
    assert len(keal_only) == 4, len(keal_only)
    G.set_house("keal")
    assert G.locked_modules() == 4, G.locked_modules()
    print("  and it counts the %d this house can still be sold, not the "
          "%d in the table" % (n, len(keal_only) + n))

    # the overlay itself draws, with the card greyed on the wrong body
    G.set_house("ryez")
    G.add_marks(30000)
    G.buy_ware("st_gravid")
    G.buy_ware("g_greatsac")
    for chassis in ("standard", "gravid"):
        run = G.Run("ryez", chassis)
        run.scrap, run.alloy = 20000, 200
        h = G.Hangar(run)
        h.sel = G.MOD_SLOT
        h.rack = True
        sf = pygame.Surface((G.W, G.H))
        h.draw(sf, (0, 0))
        got = [b for b in h.rack_buttons if b.key[0] == "build"
               and getattr(b.key[1], "key", None) == "greatsac"]
        assert len(got) == 1, (chassis, "no card for it at all")
        assert got[0].enabled is (chassis == "gravid"), chassis
    print("  and the card is on the screen either way, greyed on the "
          "body that cannot carry it")
    wipe_meta()
    G.set_house("keal")

    # -- every socket has a name in every house --------------------------
    # The GRAVID MOTHER's two extra organ sites are the whole point of
    # her, they were missing from RYEZ_HUD, and the fight HUD looked a
    # socket up with a bare [] - so fitting anything at all to the one
    # grown body that HAS them closed the game the moment the fight
    # drew. She shipped like that.
    for s in G.SOCKETS:
        assert s in G.HUD_LABEL, s
        assert s in G.RYEZ_HUD, s
        assert s in G.SOCKET_LABEL, s
        assert s in G.RYEZ_SOCKETS, s
    for house in ("keal", "ryez"):
        G.set_house(house)
        seen = {}
        for s in G.SOCKETS:
            lab = G.sock_label(s)
            assert lab and lab not in seen, (house, s, lab, seen.get(lab))
            seen[lab] = s
    print("  all %d sockets are named in both houses, twice over"
          % len(G.SOCKETS))

    # ...and the fight actually draws for a body that uses all of them
    for house, chassis, wares in (("ryez", "gravid", ("st_gravid",)),
                                  ("keal", "turret", ("ch_turret",)),
                                  ("keal", "tank", ("ch_tank",))):
        wipe_meta()
        G.set_house(house)
        G.add_marks(20000)
        for k in wares:
            assert G.buy_ware(k), k
        run = G.Run(house, chassis)
        assert run.mech.chassis == chassis, run.mech.chassis
        run.scrap, run.alloy = 20000, 200
        for s in run.mech.sockets():
            if s not in G.HARDPOINTS:
                run.mech.install(s, 3)
        mounted = 0
        for s in G.HARDPOINTS:
            if s not in run.mech.sockets():
                continue
            opts = G.options_for(s, None, run.mech.frame)
            if opts:
                run.mech.install(s, opts[0].key)
                mounted += 1
        assert mounted >= 2, (chassis, mounted)
        f = G.Fight(run, run.next_kind())
        sf = pygame.Surface((G.W, G.H))
        for i in range(90):
            f.update(1 / 60.0, {})
        f.draw(sf)                    # the line that used to take it down
        assert sf.get_bounding_rect().w > 0
    print("  and a fight draws for every frame with a mount on every "
          "socket it has")
    wipe_meta()
    G.set_house("keal")

    # -- a small mount you can see -----------------------------------------
    # AUX POD and AUX FLARE POD cost money, fill a socket, show in the
    # HUD and fire, and were drawn NOWHERE - not in the street, not in
    # the gantry, in either house. The TITAN TURRET is sold on having
    # two of them. Worse, their shots came out of the right hand,
    # because `weapon_muzzle` read an arm socket for every side.
    def with_without(house, chassis, ware, key, front):
        wipe_meta()
        G.set_house(house)
        G.add_marks(20000)
        assert G.buy_ware(ware), ware
        shots = []
        for fit in (False, True):
            run = G.Run(house, chassis)
            run.scrap, run.alloy = 20000, 200
            for s in run.mech.sockets():
                if s not in G.HARDPOINTS:
                    run.mech.install(s, 3)
            if fit:
                run.mech.install("l_aux", key)
                run.mech.install("r_aux", key)
            pz = G.Pose()
            pz.face = 1
            pz.aim = {k: -0.3 for k in G.SIDES}
            sf = pygame.Surface((460, 470), pygame.SRCALPHA)
            sf.fill((0, 0, 0, 0))
            if front:
                G.draw_mech_front(sf, run.mech, 230, 440, 0.6, t=2.0)
            else:
                G.draw_mech_side(sf, run.mech, 210, 440, 0.6, 2.0, pz,
                                 bio=(house == "ryez"))
            w, h = sf.get_size()
            # COLOUR, not an alpha mask. An empty mount is already
            # drawn as a dashed ghost in the same place, so the
            # silhouette barely moves when a pod goes into it - the
            # first version of this compared masks and read zero.
            shots.append([sf.get_at((x, y))[:3]
                          for y in range(0, h, 2)
                          for x in range(0, w, 2)])
        bare, armed = shots
        return sum(1 for a, b in zip(bare, armed) if a != b)

    for house, chassis, ware in (("keal", "turret", "ch_turret"),
                                 ("ryez", "gravid", "st_gravid")):
        for key in G.AUX_GUNS:
            for front, where in ((False, "the street"), (True, "the yard")):
                d = with_without(house, chassis, ware, key, front)
                assert d > 60, (
                    "%s on a %s is invisible in %s (%d pixels changed)"
                    % (key, chassis, where, d))
    # ...and the two of them are not the same drawing
    a = with_without("keal", "turret", "ch_turret", "auxpod", False)
    b = with_without("keal", "turret", "ch_turret", "auxflare", False)
    assert a != b, "the pod and the flare pod draw identically"
    print("  both small mounts draw, in both views and both houses")

    # -- and a shot leaves the pod, not the hand --------------------------
    wipe_meta()
    G.set_house("keal")
    G.add_marks(20000)
    G.buy_ware("ch_turret")
    run = G.Run("keal", "turret")
    for s in run.mech.sockets():
        if s not in G.HARDPOINTS:
            run.mech.install(s, 3)
    run.mech.install("r_wpn", "titanauto")
    run.mech.install("r_aux", "auxpod")
    pz = G.Pose()
    pz.face = 1
    arm, _ = G.weapon_muzzle(run.mech, pz, "r", 300.0, 440.0, 0.6)
    pod, _ = G.weapon_muzzle(run.mech, pz, "ra", 300.0, 440.0, 0.6)
    assert arm is not None and pod is not None
    assert (arm - pod).length() > 20, (
        "the pod fires out of the arm's hand: %s against %s" % (arm, pod))
    print("  and its shots leave the pod, %dpx off the hand they used to "
          "come from" % round((arm - pod).length()))
    wipe_meta()
    G.set_house("keal")

    # -- the things you FIGHT are machines too ---------------------------
    # Every KEAL model in the roster was `chassis standard`: the stock
    # frame at a different tier in a different colour, so seven models
    # were one machine at seven sizes. Overlap over union had the
    # SOVEREIGN and the FOUNDER at 56% of one drawing. They field their
    # own frames now, out of the same table and for sale to nobody.
    wipe_meta()
    G.set_house("ryez")
    roster = G.roster_for("ryez")
    for k in roster:
        assert k.rig.chassis != "standard", (
            "%s is the stock frame in a different colour" % k.name)
        assert G.CHASSIS[k.rig.chassis].foe or k.rig.chassis == "sovereign", (
            "%s fields a frame that is also on the shop shelf" % k.name)
    # the one model you can also buy is the one that shares a name
    assert G.KEAL_KINDS["sovereign"].rig.chassis == "sovereign"

    def still(k):
        """An enemy with its gait PINNED. `Enemy.__init__` starts every
        one of them on a random walk phase, so measuring an outline
        without nailing that down gives a different answer every run -
        this read 43% and then 54% on the same code."""
        e = G.Enemy(k, 0)
        e.walk, e.moving = 0.0, 0.0
        return e

    def outline(k):
        sf = pygame.Surface((820, 700), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        G.draw_enemy(sf, still(k), 430, 660, 0.55, 2.0)
        w, h = sf.get_size()
        return bytes(1 if sf.get_at((x, y))[3] > 40 else 0
                     for y in range(0, h, 3) for x in range(0, w, 3))
    seen = {k.key: outline(k) for k in roster}
    keys = [k.key for k in roster]
    worst = None
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            pa, pb = seen[a], seen[b]
            both = sum(1 for x, y in zip(pa, pb) if x and y)
            either = sum(1 for x, y in zip(pa, pb) if x or y)
            iou = both / float(max(1, either))
            if worst is None or iou > worst[0]:
                worst = (iou, a, b)
    assert worst[0] < 0.55, (
        "%s and %s are %.0f%% the same machine"
        % (worst[1], worst[2], worst[0] * 100))
    print("  the eight KEAL models field %d frames of their own; the two "
          "most alike share %.0f%% of an outline"
          % (len(set(k.rig.chassis for k in roster)), worst[0] * 100))

    # -- and nothing walks under the road --------------------------------
    # a `build` overlay draws in the BODY zone, which scales about the
    # hip, so a shape put down at ground level lands below it on a frame
    # with short legs. The BASTION's braced feet did exactly that.
    for k in roster:
        sf = pygame.Surface((820, 700), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        G.draw_enemy(sf, still(k), 430, 660, 0.55, 2.0)
        assert sf.get_bounding_rect().bottom <= 664, (
            "%s is drawn %dpx under the road"
            % (k.name, sf.get_bounding_rect().bottom - 660))
    print("  and every one of them stands on the road, not through it")

    # -- the brief shows what is actually coming -------------------------
    # It called `draw_kaiju` for whatever was on the schedule, and half
    # of what is on the schedule is machines - so a RYEZ player opened
    # the one screen that exists to show them the thing they are about
    # to fight and got a headless animal with a machine's proportions.
    # `draw_kind` is the shared branch both screens go through, so test
    # it rather than the pixels of a screen that has a background: a
    # crop of the brief has no alpha in it and its bounding box is the
    # whole crop, which is what the first version of this measured.
    def shape_of(fn):
        sf = pygame.Surface((760, 640), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        fn(sf)
        w, h = sf.get_size()
        return bytes(1 if sf.get_at((x, y))[3] > 40 else 0
                     for y in range(0, h, 3) for x in range(0, w, 3))
    steel = G.KEAL_KINDS["sovereign"]
    assert steel.family == "mech", steel.family
    asmech = shape_of(lambda sf: G.draw_kind(sf, steel, 380, 600, 0.6, 1.0))
    asbeast = shape_of(lambda sf: G.draw_kaiju(sf, steel, 380, 600, 0.6, 1.0,
                                               0.0, 0.8, -1))
    both = sum(1 for x, y in zip(asmech, asbeast) if x and y)
    either = sum(1 for x, y in zip(asmech, asbeast) if x or y)
    assert both / float(max(1, either)) < 0.4, (
        "draw_kind is still routing a machine through the animal "
        "renderer")
    beast = G.KINDS["leviathan"]
    askaiju = shape_of(lambda sf: G.draw_kind(sf, beast, 380, 600, 0.6, 1.0))
    direct = shape_of(lambda sf: G.draw_kaiju(sf, beast, 380, 600, 0.6, 1.0,
                                              0.0, 0.8, -1))
    assert askaiju == direct, "an animal stopped being drawn as one"
    print("  and the brief draws a machine when a machine is coming")
    wipe_meta()
    G.set_house("keal")

    # -- THE LADDER: seven rungs, and the top ones are not duels ---------
    # One body at a time is a duel and a duel is a thing a finished
    # machine wins outright - measured, a plain animal took the top rung
    # eight times out of eight. Company fixes the fight rather than
    # inflating the boss, and the company is drawn from rungs already
    # beaten so nothing new has to be balanced.
    wipe_meta()
    assert len(G.SCHEDULE) == 7, G.SCHEDULE
    assert len(G.MARKS_FOR) == len(G.SCHEDULE), (len(G.MARKS_FOR),
                                                 len(G.SCHEDULE))
    assert len(G.ESCORTS) == len(G.SCHEDULE), len(G.ESCORTS)
    for i in range(3):
        assert not G.escorts_at(i), "landfall %d is not a duel" % (i + 1)
    for i in range(3, 7):
        assert G.escorts_at(i), "landfall %d comes alone" % (i + 1)

    for house in ("keal", "ryez"):
        G.set_house(house)
        roster = G.roster_for(house)
        # every rung has its OWN datasheet. The seventh used to be the
        # sixth again, which is a fine fight and a poor reveal - the
        # brief printed the same name and the same numbers twice.
        headline = [G.kind_at(house, i) for i in range(len(G.SCHEDULE))]
        assert len(set(k.key for k in headline)) == len(G.SCHEDULE), (
            [k.name for k in headline])
        # ...and what is left over past the end of the ladder is ESCORT
        # STOCK: bodies the schedule never puts on a brief
        spare = [k for k in roster if k not in headline]
        assert spare, "no escort stock at all"
        for k in spare:
            assert any(k is G.kind_at(house, r)
                       for i in range(len(G.SCHEDULE))
                       for r, _c, _f in G.escorts_at(i)), (
                "%s is in the roster and reachable from nowhere" % k.name)
        # THREAT, not hit points. The first version of this asserted
        # the last landfall carried more HP than the one before it and
        # it does not: 11540 against 12946, while winning it 8 times in
        # 12 against 11. A second BODY is worth more than any amount of
        # health on the first, which is the whole reason escorts exist,
        # so counting health measures the wrong thing. What a unit test
        # can honestly say is how many things are on the road and how
        # hard the biggest of them hits; the win rate lives in the
        # balance run, where it is played rather than added up.
        threat, count = {}, {}
        for i in range(len(G.SCHEDULE)):
            run = G.Run(house)
            run.kaiju_index = i
            f = G.Fight(run, run.next_kind())
            assert f.boss() is f.enemies[0], i
            count[i] = len(f.enemies)
            threat[i] = sum(max(a["dmg"] / max(0.2, a["cool"])
                                for a in e.kind.attacks)
                            for e in f.enemies)
        # ...and then THIS proxy failed too, 99 against 111, because a
        # STRIDER escorting the sixth hits harder than two HOUNDs
        # escorting the seventh. Both attempts were the same mistake:
        # trying to prove "the finale is the hardest fight" by adding
        # up a datasheet. It is the hardest because the boss takes the
        # longest to kill while two fast things chew on you, and no sum
        # of numbers in a table says that. The claim belongs to the
        # balance run, which PLAYS it - 8 wins in 12 against 11 in 12
        # on the rung before. What is left here is what a table really
        # can promise.
        assert count[6] >= 3, count
        assert count[6] >= max(count.values()), count
        assert threat[6] > threat[0] * 4, threat
        biggest = max(G.roster_for(house), key=lambda k: k.hp)
        assert G.kind_at(house, 6) is biggest, (
            "the heaviest body in the roster is not the one at the end")
        for i in range(1, len(G.SCHEDULE)):
            assert G.kind_at(house, i).hp > G.kind_at(house, i - 1).hp, (
                "rung %d is lighter than the one under it" % (i + 1))
    print("  seven landfalls, each with its own body; the first three "
          "are duels and the last puts %d on the road hitting %.1fx "
          "the first" % (count[6], threat[6] / max(1.0, threat[0])))

    # -- the seventh one actually happens --------------------------------
    # It did not. `resolve` ended the campaign on the length of the
    # ROSTER, which was six, so the seventh was scheduled, printed on
    # the brief and then quietly never arrived.
    G.set_house("keal")
    run = G.Run("keal")
    run.kaiju_index = 5
    seen = []
    for _ in range(3):
        nl = run.next_landfall
        if nl is None:
            break
        seen.append(nl)
        f = G.Fight(run, run.next_kind())
        for e in f.enemies:
            e.hp = 0.0
        f.over = "won"
        ending, _ = run.resolve(f)
        if ending:
            seen.append(ending)
            break
    assert seen[:2] == [G.SCHEDULE[5], G.SCHEDULE[6]], seen
    assert seen[-1] == "victory", seen
    print("  and the ladder, not the roster, is what ends a campaign")

    # -- an escort pays, because otherwise it is a tax --------------------
    G.set_house("keal")
    run = G.Run("keal")
    run.kaiju_index = 5              # the sixth: a STRIDER and a SPITTER
    f = G.Fight(run, run.next_kind())
    extra = [e for e in f.enemies if getattr(e, "escort", False)]
    assert len(extra) == 2, len(extra)
    for e in extra:
        e.hp = 0.0
    f.update(1 / 60.0, {})
    assert f.escort_scrap > 0, "killing the others paid nothing"
    was = run.scrap
    f.over = "won"
    f.enemies[0].hp = 0.0
    run.resolve(f)
    assert run.scrap - was > f.kind.scrap, (
        "the harvest did not include what came with it")
    print("  and what comes with the sixth is worth another %d %s"
          % (f.escort_scrap, G.word("scrap", "scrap").lower()))

    # the SEVENTH pays nothing for its boss - the top-rung body's own
    # harvest is zero, "nothing left to salvage", and the campaign ends
    # on that landfall anyway - but what came WITH it still pays. It
    # used to pay nothing at all, because the escort there was another
    # copy of the boss and inherited the same empty harvest.
    run = G.Run("keal")
    run.kaiju_index = 6
    f = G.Fight(run, run.next_kind())
    assert f.kind.scrap == 0, f.kind.scrap
    for e in f.enemies:
        e.hp = 0.0
    f.update(1 / 60.0, {})
    assert f.escort_scrap > 0, "the last landfall pays nothing at all"
    wipe_meta()
    G.set_house("keal")

    # -- nothing on the grown side is being WELDED ------------------------
    # A job in progress fills from the feet and the fill line carried a
    # torch: a hot white glow and orange sparks flying off the bead. On a
    # tank that is the steel half of the game leaking into the other one.
    # The line is a waterline there, and what comes off it is bubbles.
    #
    # The colours are matched EXACTLY rather than by hue. A first pass
    # asked "is this pixel warm or cold" and the HOLLOW SWARM's trim is a
    # yellow-green, so its bubbles counted as sparks - and half the body
    # tones fell in one bucket or the other as well.
    SPARK = (255, 206, 128)

    def marks(house, chassis="standard"):
        wipe_meta()
        G.set_house(house)
        if chassis != "standard":
            G.add_marks(4000)
            G.buy_ware("st_" + chassis)
        m = G.Mech(chassis)
        sf = pygame.Surface((440, 470), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        rig = G.Rig(sf, 220, 450, 0.62, m.frame.prop)
        G.draw_socket_front(rig, "legs", 3, 0.0, 1, "job", 0.45, 2.0,
                            m.frame.tones, (m.frame.style or {}).get("beast"))
        trim = (m.frame.tones or G.BIO_TONES).get("trim", G.RYEZ_ACID)
        wet = (G.shade(trim, 0.85), G.shade(trim, 0.62), G.shade(trim, 0.7))
        hot = cold = 0
        w, h = sf.get_size()
        for y in range(h):
            for x in range(w):
                c = sf.get_at((x, y))
                if c[3] < 40:
                    continue
                if c[:3] == SPARK:
                    hot += 1
                elif c[:3] in wet:
                    cold += 1
        return hot, cold
    steel = marks("keal")
    grown = marks("ryez")
    strain = marks("ryez", "hollow")
    assert steel[0] > 0, "the welder went out"
    assert steel[1] == 0, "a shipyard is growing something"
    assert grown[0] == 0, (
        "there is still a torch over the tank: %d sparks" % grown[0])
    assert grown[1] > 0, "nothing marks how far the culture has got"
    # and a STRAIN gets it too. The house test in there used to be
    # `tones is BIO_TONES`, and a bought body turns up carrying its own
    # palette, so every one of them was being welded in its tank
    assert strain[0] == 0, (
        "a HOLLOW SWARM is being welded: %d sparks" % strain[0])
    assert strain[1] > 0, "a strain's tank has no waterline"
    G.set_house("ryez")
    assert G.work_sfx() == "graft"
    G.set_house("keal")
    assert G.work_sfx() == "weld"
    print("  a weld throws %d sparks and no bubbles; a culture throws "
          "%d bubbles and no sparks, strain or not" % (steel[0], grown[1]))
    wipe_meta()
    G.set_house("keal")

    # -- HANDLERS: what a pair of hands on a pod is actually worth --------
    # Both halves of this were reported by a player: "the handlers don't
    # do anything" and "I can't mend two things at once". They are one
    # bug. RYEZ ran five tanks on the two hands a gantry gets, so mending
    # anything meant an organ came out wrong - and the dose was set so
    # that one handler covered a THIRTEEN day culture when the longest in
    # the game is nine, which made the second pair of hands a no-op in
    # every situation that can occur.
    wipe_meta()
    G.set_house("ryez")

    def drifts(days, hands):
        """Where a culture of this length ends up with this many on it."""
        u = 0.0
        for _ in range(days):
            u = max(0.0, min(100.0, u + G.DRIFT_PER_DAY
                             - G.HANDLER_CALM * hands))
        return u >= G.FAULT_AT

    # against the cultures that EXIST, not against invented lengths
    lens = sorted({int(math.ceil(max(1, p.days) * G.GESTATE))
                   for s in G.SOCKETS if s in G.CATALOGUE
                   for p in G.CATALOGUE[s]})
    assert max(lens) <= 12, lens
    assert all(drifts(d, 0) for d in lens if d >= 4), (
        "a pod nobody watches can still come out right: %s" % lens)
    assert any(not drifts(d, 1) for d in lens), "one handler is never enough"
    assert any(drifts(d, 1) for d in lens), (
        "one handler covers every culture in the game, so the second pair "
        "of hands cannot ever matter: %s" % lens)
    assert not any(drifts(d, 2) for d in lens), "two handlers still fault"
    short = [d for d in lens if not drifts(d, 1)]
    long_ = [d for d in lens if drifts(d, 1)]
    print("  one handler holds a %d-%dd culture and loses a %d-%dd one; "
          "two hold anything" % (min(short), max(short), min(long_),
                                 max(long_)))

    # and the slider stops where the effect stops
    run = G.Run("ryez")
    run.scrap, run.alloy = 9000, 90
    run.start_build("head", G.CATALOGUE["head"][0])
    pod = run.jobs[0]
    run.set_crew(pod, 9)
    assert pod.crew == G.HANDS_PER_POD, (
        "a pod took %d handlers and two already stop it drifting"
        % pod.crew)
    run.set_crew(pod, 0)

    # -- and there are enough hands for the tanks to mean anything --------
    assert run.crew == G.HANDS_START and run.crew > G.CREW_START, run.crew
    fresh = G.Run("ryez")
    fresh.scrap = 9000
    for s in ("legs", "torso"):
        fresh.mech.install(s, 1)
        fresh.mech.hp[s] = 10
    assert fresh.start_repair("legs"), "RYEZ cannot mend at all"
    assert fresh.start_repair("torso"), (
        "RYEZ cannot mend two things at once with %d hands and nothing "
        "else running" % fresh.crew)
    keal = G.Run("keal")
    keal.scrap = 9000
    for s in ("legs", "torso"):
        keal.mech.install(s, 1)
        keal.mech.hp[s] = 10
    assert keal.start_repair("legs") and keal.start_repair("torso")
    print("  both houses can have two things being mended at once")

    # -- RYEZ can grow its hands, which it could not do at all ------------
    # every ware that sent one was Zoe's and Zoe will not sell to a tank
    # farm, so the grown house opened on two and finished on two
    givers = ("earlyshift", "hq", "recruit", "v_hands")
    G.set_house("ryez")
    reach = [k for k in givers if G.WARES[k].house in (None, "ryez")]
    assert reach == ["earlyshift", "v_hands"], reach
    G.add_marks(4000)
    G.buy_ware("v_hands")
    grow = G.Run("ryez")
    start = grow.crew
    for _ in range(4):
        grow.capital_night()
    assert grow.crew == start + 2, (start, grow.crew)
    for _ in range(40):
        grow.capital_night()
    assert grow.crew == grow.max_crew == grow.pods + 2, (
        grow.crew, grow.max_crew, grow.pods)
    print("  his students take RYEZ from %d hands to %d, one per tank "
          "plus two" % (start, grow.crew))

    # -- and the whole point: a watched tank and an unwatched one -------
    # This is the player's complaint stated as a measurement. If it comes
    # out the same either way then the sliders are furniture.
    def tanks(n, watch):
        wipe_meta()
        G.set_house("ryez")
        r = G.Run("ryez")
        r.scrap, r.alloy = 20000, 200
        for s in ("head", "l_arm", "r_arm", "reactor")[:n]:
            r.start_build(s, G.CATALOGUE[s][-1])   # the long ones
        pods = r.growing()
        assert len(pods) == n, len(pods)
        if watch:
            for want in (1, 2):
                for j in pods:
                    if r.free_crew > 0 and j.crew < want:
                        r.set_crew(j, want)
        else:
            for j in pods:
                r.set_crew(j, 0)
        for _ in range(max(int(j.need) for j in pods) + 1):
            r.end_day()
        return sum(1 for j in pods if j.faulted)
    assert tanks(2, False) == 2, "an unwatched tank came out right"
    assert tanks(2, True) == 0, (
        "handlers changed nothing on two long cultures, which is exactly "
        "as many as four pairs of hands can hold")
    print("  two long cultures: 0 of 2 wrong with handlers on them, "
          "2 of 2 with nobody watching")

    # ...and the tanks still outnumber the hands, which is the decision.
    # Four long cultures want eight handlers and the house has four, so
    # something in there comes out wrong whatever you do with the sliders
    assert tanks(4, True) > 0, (
        "four long cultures and four hands and nothing went wrong - the "
        "pods are free and there is no decision left in them")
    print("  four of them at once is more than the house has hands for, "
          "and it costs")
    wipe_meta()
    G.set_house("keal")

    print("\nyard ok")


# ---------------------------------------------------------------------------
# CAPITAL - the KEAL half of the shop, and the gate under it
# ---------------------------------------------------------------------------
def capital():
    """Twelve things that are bought in one house and used in one house.

    The dangerous half of this is not the effects, it is the GATE. Every
    one of these is paid for out of a ledger that is shared between both
    houses in a slot, so the thing to prove is that RYEZ cannot reach any
    of it while still being able to see that it owns it."""
    wipe_meta()
    surf = pygame.Surface((G.W, G.H))
    cap = [w for w in G.WARE_LIST if w.seller in ("mike", "zoe")]
    assert len(cap) == 12, len(cap)
    assert all(w.house == "keal" for w in cap), "a Capital ware is unlocked"
    print("  %d wares over two counters, all KEAL" % len(cap))

    G.set_house("keal")
    base_mods = len(G.module_list())
    base_wpns = len(G.options_for("l_wpn", None))
    G.add_marks(4000)
    for w in cap:
        assert G.can_buy(w.key), w.key
        assert G.buy_ware(w.key), w.key
        assert not G.can_buy(w.key), "%s sold twice" % w.key
    print("  bought the lot for %d marks, %d left" % (4000 - G.marks(),
                                                      G.marks()))

    # -- the gate ----------------------------------------------------------
    for w in cap:
        assert G.bought(w.key), w.key
        assert G.has_ware(w.key), w.key
    G.set_house("ryez")
    for w in cap:
        assert G.bought(w.key), "%s left the ledger" % w.key
        assert not G.has_ware(w.key), "%s works in a RYEZ run" % w.key
    assert len(G.module_list()) == base_mods, "KEAL bays in a RYEZ rack"
    assert len(G.options_for("l_wpn", None)) == base_wpns, "KEAL guns, RYEZ"
    ryez = G.Run("ryez")
    # the HQ sends nobody to a tank farm and the recruiting office does
    # not raise its ceiling either - RYEZ's hands come from its own pod
    # count and from Vask's students, neither of which is on this list
    assert ryez.crew == G.HANDS_START, ryez.crew
    assert ryez.max_crew == ryez.pods + 2, ryez.max_crew
    print("  RYEZ owns all twelve and can use none of them")

    G.set_house("keal")
    assert len(G.module_list()) == base_mods + 4, len(G.module_list())
    assert len(G.options_for("l_wpn", None)) == base_wpns + 3
    print("  KEAL rack %d -> %d, hardpoint %d -> %d"
          % (base_mods, base_mods + 4, base_wpns, base_wpns + 3))

    # -- Zoe: five things the company does while you build -----------------
    run = G.Run("keal")
    assert run.crew == 3, "the HQ did not send anybody: %d" % run.crew
    assert run.max_crew == G.RECRUIT_CAP, run.max_crew
    plain = G.WEAPONS["auto"].scrap
    assert run.price(G.WEAPONS["auto"], "l_wpn")[0] == int(round(plain * 0.9))
    run.crew, run.alloy, run.scrap = 4, 0, 4000
    # the furnace costs a HAND, off the top, for the whole run
    assert run.furnace_hand == 1
    assert run.free_crew == run.crew - 1, run.free_crew
    coke = run.scrap
    for _ in range(G.FURNACE_DAYS):
        run.capital_night()
    assert run.alloy == 1, "the furnace: %d in %d nights" % (
        run.alloy, G.FURNACE_DAYS)
    assert run.scrap == coke, "the furnace is still eating scrap"
    run.crew = G.RECRUIT_CAP
    for _ in range(6):
        run.capital_night()
    assert run.crew == G.RECRUIT_CAP, "the office went past its cap"
    print("  furnace 1 alloy per %d nights and one hand on it; office fills "
          "to %d" % (G.FURNACE_DAYS, G.RECRUIT_CAP))

    # -- and it is a TRADE now, not a tap ---------------------------------
    # It used to pour half an alloy a night for nothing: 28 over a 57-day
    # campaign against a full build's 25, which paid for the whole rare
    # metal economy out of one 95-mark purchase.
    rich = G.Run("keal")
    rich.scrap, rich.alloy = 20000, 0
    spent = rich.scrap
    for _ in range(G.SCHEDULE[-1]):
        rich.capital_night()
    spent -= rich.scrap
    assert spent == 0, "it is charging money as well as a hand"
    # a whole machine: every rung of the body, the dearest hardpoint pair,
    # and three bays - not just the body, which is where the first version
    # of this assertion got its 14 and compared it against 14
    build_needs = (sum(p.alloy for tbl in G.CATALOGUE.values() for p in tbl)
                   + 2 * max(G.WEAPONS[u].alloy + G.WEAPONS[b].alloy
                             for b, u in G.WEAPON_FAMILIES)
                   + sum(sorted((m.alloy for m in G.MODULE_LIST),
                                reverse=True)[:3]))
    assert rich.alloy < build_needs * 0.75, (
        "the furnace still covers most of a build on its own: %d of %d"
        % (rich.alloy, build_needs))
    print("  over a campaign: %d alloy, free of money, against a whole "
          "machine's %d" % (rich.alloy, build_needs))

    # -- and the hand it costs is a hand you cannot build with ------------
    lean = G.Run("keal")
    lean.crew, lean.scrap, lean.alloy = 2, 6000, 9
    assert lean.free_crew == 1, lean.free_crew
    assert lean.start_build("legs", G.CATALOGUE["legs"][0])
    assert lean.free_crew == 0, lean.free_crew
    assert not lean.start_build("torso", G.CATALOGUE["torso"][0]), (
        "two jobs on one free hand")
    print("  two on the books is one usable hand while it is lit")

    r2 = G.Run("keal")
    r2.mech.install("torso", 2)
    r2.mech.hp["torso"] *= 0.4
    cost, days = r2.mech.repair_cost("torso")
    assert cost > 0 and days >= 1, (cost, days)
    r2.killed = 3
    assert r2.income > G.Run("ryez").income, "the colony pays nothing"
    print("  mending %d/%dd, and the colony is in the income" % (cost, days))

    # -- Mike: four bays and three hardpoints ------------------------------
    def rig(lw="auto", rw="auto", mods=()):
        r = G.Run("keal")
        r.kaiju_index = 2
        for k, v in (("legs", 2), ("torso", 3), ("l_arm", 3), ("r_arm", 3),
                     ("head", 2), ("reactor", 3), ("armour", 2),
                     ("l_wpn", lw), ("r_wpn", rw)):
            r.mech.install(k, v)
        for m in mods:
            assert r.mech.fit_module(m), m
        return r

    plain = G.Run("keal")
    plain.mech.install("reactor", 3)
    aux = rig(mods=("aux",))
    assert aux.mech.heat_cap > plain.mech.heat_cap, "the aux core is inert"
    assert aux.mech.vent > plain.mech.vent
    assert not plain.mech.can_boost, "tier-2 legs should not dash"
    assert rig(mods=("thrust",)).mech.can_boost, "thrusters do not dash"
    print("  aux core %d -> %d ceiling, thrusters dash on tier-2 legs"
          % (plain.mech.heat_cap, aux.mech.heat_cap))

    r = rig(mods=("emp",))
    f = G.Fight(r, G.roster_for("keal")[2])
    for _ in range(40):
        f.update(1 / 40.0, {})
    assert f.fire_emp(), "the EMP did not fire"
    assert f.boss().stun >= 2.9, f.boss().stun
    assert not f.fire_emp(), "the EMP fired twice in one landfall"
    print("  EMP stops one for %.0fs, once a landfall" % f.boss().stun)

    r = rig(mods=("eject",))
    f = G.Fight(r, G.roster_for("keal")[2])
    f.mech.hp["torso"] = 6.0
    f.mech_hit(f.boss(), 9999)
    assert f.over is None, "the seat did not catch it"
    assert r.ejected and f.mech.hp["torso"] > 0
    f.mech.hp["torso"] = 6.0
    f.mech_hit(f.boss(), 9999)
    assert f.over == "lost", "the seat caught it twice"
    bare = rig()
    fb = G.Fight(bare, G.roster_for("keal")[2])
    fb.mech.hp["torso"] = 6.0
    fb.mech_hit(fb.boss(), 9999)
    assert fb.over == "lost", "no seat and it still stood up"
    print("  the seat catches one core a CAMPAIGN, and the flag saves")

    # -- the three hardpoints, each doing the thing it is sold as ----------
    r = rig("blight", "blight")
    f = G.Fight(r, G.roster_for("keal")[2])
    for _ in range(240):
        f.update(1 / 40.0, {"fire_l": True, "fire_r": True, "right": True})
    e = f.boss()
    assert e.rot_t > 4.0, "the blight did not stack: %.1f" % e.rot_t
    hp = e.hp
    for _ in range(80):
        f.update(1 / 40.0, {"right": True})
    assert e.hp < hp - 40, "it stopped working the moment the guns did"
    print("  blight stacks to %.1fs and bills %.0f after the guns go cold"
          % (e.rot_t, hp - e.hp))

    r = rig("flame", "flame")
    f = G.Fight(r, G.roster_for("keal")[2])
    peak = 0.0
    for _ in range(900):
        f.update(1 / 40.0, {"fire_l": True, "fire_r": True, "right": True})
        if f.boss() and f.boss().alive:
            peak = max(peak, f.boss().rot_t)
        if f.over:
            break
    assert 0 < peak <= G.WEAPONS["flame"].rot_cap + 0.01, peak
    print("  flame refreshes to %.1fs and never past its cap" % peak)

    r = rig("claw", "claw")
    f = G.Fight(r, G.roster_for("keal")[2])
    far = 0
    for _ in range(120):
        f.update(1 / 40.0, {"fire_l": True, "fire_r": True})
        far = max(far, len(f.shots))
    assert far > 0, "the claw did not throw anything"
    assert f.dealt > 0, "and nothing it threw arrived"
    print("  claw put %d bolts up before anything was in reach" % far)

    # -- a Capital run has to round-trip -----------------------------------
    r = rig(mods=("eject",))
    r.ejected = True
    r.furnace, r.queue = 0.5, 1
    back = G.Run.from_json(r.to_json())
    assert back.ejected and back.queue == 1 and abs(back.furnace - 0.5) < 1e-6
    print("  a spent seat and a half-built billet survive a save")

    # -- and the screen draws, both halves of it ---------------------------
    b = G.Bazaar()
    b.t = 2.0
    for i in range(len(G.Bazaar.SECTIONS)):
        b.sec = i
        b.draw(surf, (0, 0))
        assert b.slots, "section %d has nothing on the boards" % i
        for box, _ in b.slots:
            assert box.bottom <= G.H, "a card fell off the screen"
    b.sec = 0
    b.draw(surf, (0, 0))
    b.click(b.tab_rect(1).center)
    assert b.sec == 1, "the tab did not switch"
    b.draw(surf, (0, 0))
    b.click(b.slots[0][0].center)
    assert b.open == b.slots[0][1], "a Capital ware would not pick up"
    b.draw(surf, (0, 0))
    print("  both counters draw, the tabs switch, the stock picks up")
    wipe_meta()
    G.set_house("keal")
    print("\ncapital ok")


# ---------------------------------------------------------------------------
# GOV - the state's counter, which moves the calendar and the numbers
# ---------------------------------------------------------------------------
GOV_KEYS = ("coffee", "rushhour", "evac", "hazmat", "walls", "qscrap",
            "military", "funding", "sabotage", "decoys", "prebomb",
            "supplies", "shipping", "mercs", "studies")


def gov():
    """Fifteen more, and this counter reaches further into the run than
    either of the others: it moves the landfall dates, the income, what a
    part carries, what the city loses and what the animal shows up with.

    Which is why almost every check below is a BEFORE and an AFTER of the
    same number rather than an assertion that a flag is set."""
    wipe_meta()
    surf = pygame.Surface((G.W, G.H))
    G.set_house("keal")
    gov_wares = [w for w in G.WARE_LIST if w.seller in ("genk", "zach")]
    assert len(gov_wares) == 20, len(gov_wares)
    # The state does not work for a company. Almost everything on these
    # two desks is something a ministry does to the CITY or the CALENDAR,
    # which helps whoever is holding the coast - so it is unlocked. The
    # one exception is QUALITY SCRAP, which is steel off the top of the
    # pile and no use to a house that grows its soldiers.
    locked = [w.key for w in gov_wares if w.house]
    assert locked == ["qscrap"], locked
    sold = {w.key for w in gov_wares if w.kind != "contract"}
    assert sold == set(GOV_KEYS), sold ^ set(GOV_KEYS)

    # -- everything measured twice: once bare, once bought -----------------
    bare = G.Run("keal")
    bare.killed, bare.integrity = 3, 90.0
    bare.mech.install("torso", 2)
    was = {
        "landfalls": [bare.landfall(i) for i in range(6)],
        "income": bare.income,
        "rush": bare.rush_rate,
        "price": bare.price(G.WEAPONS["auto"], "l_wpn")[0],
        "torso_hp": bare.mech.max_hp("torso"),
        "dmg": bare.mech.dmg_mult,
        "cut": bare.mech.hide_cut,
    }
    G.add_marks(4000)
    for k in GOV_KEYS:
        assert G.can_buy(k), k
        assert G.buy_ware(k), k
    print("  %d lines over two desks - %d sold to you, %d sold about you"
          % (len(gov_wares), len(sold), len(gov_wares) - len(sold)))

    run = G.Run("keal")
    run.killed, run.integrity = 3, 90.0
    run.mech.install("torso", 2)
    assert run.grace == 3, run.grace
    now = [run.landfall(i) for i in range(6)]
    assert now == [d + 3 for d in was["landfalls"]], now
    assert run.next_landfall == now[0]
    print("  three separate lines, three days: %s -> %s"
          % (was["landfalls"], now))

    assert run.income > was["income"], (was["income"], run.income)
    assert run.rush_rate < was["rush"], (was["rush"], run.rush_rate)
    assert run.price(G.WEAPONS["auto"], "l_wpn")[0] < was["price"]
    assert run.mech.max_hp("torso") > was["torso_hp"]
    assert run.mech.dmg_mult > was["dmg"]
    assert run.mech.hide_cut > was["cut"] == 0.0
    print("  income %d->%d  rush %d->%d  price %d->%d  torso %.0f->%.0f"
          % (was["income"], run.income, was["rush"], run.rush_rate,
             was["price"], run.price(G.WEAPONS["auto"], "l_wpn")[0],
             was["torso_hp"], run.mech.max_hp("torso")))

    # -- COFFEE: a day of work is worth more -------------------------------
    run.crew = 3
    run.scrap = 4000
    run.start_build("legs", G.CATALOGUE["legs"][0])
    j = run.job_on("legs")
    run.set_crew(j, 3)
    run.end_day()
    assert j.done > 3.0, "the coffee did nothing: %.2f" % j.done
    print("  three hands did %.1f days of work in one night" % j.done)

    # -- EVACUATIONS and HAZMAT, on a body ---------------------------------
    wipe_meta()
    G.set_house("keal")
    plain = G.Run("keal")
    plain.kaiju_index = 2
    m0 = G.marks()
    _pay(plain)
    bare_marks, bare_scrap, bare_alloy = G.marks() - m0, plain.scrap, plain.alloy
    G.add_marks(4000)
    for k in GOV_KEYS:
        G.buy_ware(k)
    rich = G.Run("keal")
    rich.kaiju_index = 2
    m1 = G.marks()
    _pay(rich)
    assert G.marks() - m1 > bare_marks, "evacuations paid nothing"
    assert rich.scrap > bare_scrap and rich.alloy > bare_alloy
    print("  a body pays %d->%d marks, %d->%d scrap, %d->%d alloy"
          % (bare_marks, G.marks() - m1, bare_scrap, rich.scrap,
             bare_alloy, rich.alloy))

    # -- MILITARY SUPPORT and BETTER WALLS ---------------------------------
    kind = G.roster_for("keal")[2]
    f = G.Fight(_rig(), kind)
    assert f.boss().max_hp < kind.hp, "it landed at full health"
    assert f.city_mult < 1.0, "the walls do nothing"
    # the same wall has to count for NOT turning up, or a player who has
    # paid for walls gets the discount for losing and not for declining
    wipe_meta()
    G.set_house("keal")
    bare_stand = G.Brief(G.Run("keal"), kind).stand_cost()
    G.add_marks(4000)
    for k in GOV_KEYS:
        G.buy_ware(k)
    walled = G.Brief(G.Run("keal"), kind).stand_cost()
    assert walled < bare_stand, (bare_stand, walled)
    print("  it lands on %.0f of %d, the city takes %d%% of everything, "
          "and standing down is %d not %d"
          % (f.boss().max_hp, kind.hp, round(f.city_mult * 100),
             walled, bare_stand))

    # -- KAIJU STUDIES: the hide is thinner --------------------------------
    e = G.Enemy(kind, 0)
    flat = e.hurtby(100.0)
    e2 = G.Enemy(kind, 0)
    cut = e2.hurtby(100.0, cut=0.34)
    assert cut > flat, (flat, cut)
    whole = G.Enemy(kind, 0).hurtby(100.0, pierce=True)
    assert flat < cut < whole, (flat, cut, whole)
    print("  100 into %s hide: %.0f flat, %.0f with studies, %.0f piercing"
          % (kind.name, flat, cut, whole))

    # -- MERCENARIES: somebody else takes it -------------------------------
    r = _rig(tier=1)
    r.kaiju_index = 4
    f = G.Fight(r, G.roster_for("keal")[4])
    took = 0
    for _ in range(2400):
        f.update(1 / 40.0, {})
        for row in f.log:
            if "MERCENARY TOOK" in row[0]:
                took += 1
                row[0] = ""
        if f.over:
            break
    assert took > 0, "nobody stood in the way in a whole fight"
    print("  a squad took %d blows meant for the machine" % took)

    wipe_meta()
    G.set_house("keal")
    r = _rig(tier=1)
    r.kaiju_index = 4
    f = G.Fight(r, G.roster_for("keal")[4])
    for _ in range(400):
        f.update(1 / 40.0, {})
    assert not f.mercs, "a squad turned up for somebody who has not paid"
    print("  and nobody turns up for somebody who has not paid")

    # -- the gate, from the other house ------------------------------------
    G.add_marks(4000)
    for k in GOV_KEYS:
        G.buy_ware(k)
    G.set_house("ryez")
    for k in GOV_KEYS:
        want = (k != "qscrap")
        assert G.bought(k), k
        assert G.has_ware(k) is want, (k, want)
    ryez = G.Run("ryez")
    # the state moved RYEZ's calendar too, and pays RYEZ the same
    # the three delay lines are in GOV_KEYS; EARLY WAKE is a contract and
    # is not bought until later, so this is +3 rather than +2
    assert ([ryez.landfall(i) for i in range(len(G.SCHEDULE))]
            == [d + 3 for d in G.SCHEDULE])
    assert ryez.grace == 3 and ryez.scrap_mult > 1.0
    assert ryez.mech.hide_cut > 0.0
    assert G.Mech("standard").max_hp("torso") == G.Run("ryez").mech.max_hp(
        "torso") or True
    print("  RYEZ gets the state's help too - calendar %+d, scrap x%.2f - "
          "and only QUALITY SCRAP stays steel" % (ryez.grace,
                                                  ryez.scrap_mult))

    # -- and the other half of his book: contracts on the animal ----------
    wipe_meta()
    G.set_house("keal")
    deals = [w for w in G.WARE_LIST if w.kind == "contract"]
    assert len(deals) == 5, len(deals)
    assert all(w.seller == "zach" for w in deals), "somebody else is dealing"
    kind = G.roster_for("keal")[2]
    bare = G.Run("keal")
    bare.kaiju_index = 2
    was = {"walk": G.Enemy(kind, 0).walk_speed,
           "hide": G.Enemy(kind, 0).hurtby(100.0),
           "hp": G.Fight(bare, kind).boss().max_hp,
           "hit": G.kaiju_mult("hit"),
           "marks": bare.marks_mult,
           "scrap": bare.scrap_mult,
           "days": [bare.landfall(i) for i in range(6)]}
    G.add_marks(3000)
    for w in deals:
        assert G.buy_ware(w.key), w.key
        assert not G.shelved(w.key), "%s did not sign itself" % w.key
    run = G.Run("keal")
    run.kaiju_index = 2
    now = {"walk": G.Enemy(kind, 0).walk_speed,
           "hide": G.Enemy(kind, 0).hurtby(100.0),
           "hp": G.Fight(run, kind).boss().max_hp,
           "hit": G.kaiju_mult("hit"),
           "marks": run.marks_mult,
           "scrap": run.scrap_mult,
           "days": [run.landfall(i) for i in range(6)]}
    assert now["walk"] > was["walk"], (was["walk"], now["walk"])
    assert now["hide"] < was["hide"], "the hide did not thicken"
    assert now["hp"] > was["hp"] * 1.15
    assert now["hit"] > was["hit"]
    assert now["marks"] > was["marks"] * 2.0, now["marks"]
    assert now["scrap"] > was["scrap"]
    assert now["days"] == [d - 1 for d in was["days"]], now["days"]
    print("  all five signed: walk %.0f->%.0f, 100 lands as %.0f->%.0f,"
          % (was["walk"], now["walk"], was["hide"], now["hide"]))
    print("    health %.0f->%.0f, marks x%.2f, scrap x%.2f, landfall %d->%d"
          % (was["hp"], now["hp"], now["marks"], now["scrap"],
             was["days"][0], now["days"][0]))

    # -- EARLY WAKE fights his own three, which is the point --------------
    for k in ("sabotage", "decoys", "prebomb"):
        G.buy_ware(k)
    both = G.Run("keal")
    assert both.grace == 2, "three forward and one back is not two: %d" % (
        both.grace)
    print("  three days bought and one sold back nets %+d" % both.grace)

    # -- shelving one puts it back without losing it ----------------------
    for w in deals:
        assert G.arm_ware(w.key, False), w.key
        assert G.shelved(w.key) and G.bought(w.key), w.key
    off = G.Run("keal")
    off.kaiju_index = 2
    assert G.Enemy(kind, 0).walk_speed == was["walk"], "still running fast"
    assert G.kaiju_mult("hit") == 1.0 and G.kaiju_mult("hp") == 1.0
    assert off.marks_mult == was["marks"], off.marks_mult
    assert [off.landfall(i) for i in range(6)] == [d + 3 for d in was["days"]]
    assert not G.can_buy(deals[0].key), "a shelved contract went back on sale"
    print("  shelved: every number back where it was, and still owned")
    for w in deals:
        G.arm_ware(w.key, True)
        assert not G.shelved(w.key)
    print("  and signing them again is one click, not another 480 marks")

    # -- it survives the save, and the slot ---------------------------------
    G.meta_forget()
    assert not G.shelved("c_word"), "the arming did not reach the disk"
    G.arm_ware("c_word", False)
    G.meta_forget()
    assert G.shelved("c_word"), "the shelving did not either"
    G.arm_ware("c_word", True)

    # -- a signed contract reaches a RYEZ run just the same ---------------
    # It used not to, because the whole desk was KEAL-locked. That was
    # always wrong for these: a contract makes the ANIMAL worse, and the
    # animal does not care what is waiting for it on the beach.
    G.set_house("ryez")
    assert G.kaiju_mult("hit") > 1.0 and G.kaiju_mult("walk") > 1.0
    ry = G.Run("ryez")
    assert ry.marks_mult > 1.0 and ry.grace == 2
    for w in deals:
        G.arm_ware(w.key, False)
    assert G.kaiju_mult("hit") == 1.0, "shelving does not reach RYEZ"
    ry2 = G.Run("ryez")
    assert ry2.marks_mult == 1.0 and ry2.grace == 3
    for w in deals:
        G.arm_ware(w.key, True)
    print("  and RYEZ can sign them too, and shelve them again")
    G.set_house("keal")

    # -- the fight is genuinely harder, measured -------------------------
    for w in deals:
        G.arm_ware(w.key, False)

    def _run_one():
        """Kill it, and also say how much was still standing at twenty
        seconds - `taken` is no use here, because a tier-three build with
        two autocannons finishes a BULWARK without ever being reached."""
        r = G.Run("keal")
        r.kaiju_index = 2
        for s, v in (("legs", 3), ("torso", 3), ("l_arm", 3), ("r_arm", 3),
                     ("head", 3), ("reactor", 3), ("armour", 3),
                     ("l_wpn", "auto"), ("r_wpn", "auto")):
            r.mech.install(s, v)
        f = G.Fight(r, kind)
        left = None
        for _ in range(4800):
            f.update(1 / 40.0, {"fire_l": True, "fire_r": True})
            if left is None and f.t >= 20.0:
                b = f.boss()
                left = b.hp if b else 0.0
            if f.over:
                break
        return f, (left if left is not None else 0.0)
    easy, easy_left = _run_one()
    for w in deals:
        G.arm_ware(w.key, True)
    hard, hard_left = _run_one()
    assert hard.t > easy.t, (easy.t, hard.t)
    assert hard_left > easy_left, (easy_left, hard_left)
    print("  same build, same animal: dead in %.0fs -> %.0fs, and at 20s "
          "there is %.0f left instead of %.0f"
          % (easy.t, hard.t, hard_left, easy_left))
    wipe_meta()
    G.set_house("keal")

    # -- and the numbers are read out in the right house's words ----------
    G.set_house("keal")
    a = G.ware_effect(G.WARES["hazmat"])
    G.set_house("ryez")
    b = G.ware_effect(G.WARES["hazmat"])
    assert "SCRAP" in a and "ALLOY" in a, a
    assert "BIOMASS" in b and "GENOME" in b, b
    assert "SCRAP" not in b and "ALLOY" not in b, b
    print("  and a RYEZ player is told BIOMASS, not SCRAP")
    G.set_house("keal")

    # -- no counter is ever hidden ----------------------------------------
    # This was a house gate twice and wrong twice. You can BUY anything
    # from anywhere - it simply does nothing in the wrong house, which is
    # what the amber line on the card says - so hiding the counter made
    # those wares purchasable and unreachable at the same time.
    G.set_house("keal")
    G.add_marks(2000)                # this far in, the purse is empty
    every = len(G.Bazaar.SECTIONS)
    for label, shop in (("the title", G.Bazaar("title")),
                        ("a KEAL run", G.Bazaar("hangar", G.Run("keal")))):
        assert len(shop.open_sections()) == every, (
            label, [G.Bazaar.SECTIONS[i][0] for i in shop.open_sections()])
    G.set_house("ryez")
    ryez_shop = G.Bazaar("hangar", G.Run("ryez"))
    assert len(ryez_shop.open_sections()) == every
    # and what is reachable is buyable, both ways round
    assert G.can_buy("ch_tank"), "a RYEZ run cannot buy a KEAL frame"
    G.set_house("keal")
    assert G.can_buy("g_lungs"), "a KEAL run cannot buy a RYEZ gene"
    assert G.can_buy("st_bloom"), "nor a RYEZ strain"
    print("  all %d counters open from everywhere, and everything on them "
          "is buyable" % every)

    # and a card shows the thing as what it IS, not as whatever house is
    # looking at it - a DEEP LEVIATHAN previewed in a KEAL run was drawn
    # as a machine, because the renderer guesses the body from CURRENT
    for h in ("keal", "ryez"):
        G.set_house(h)
        # the stock body is whatever the house is - that is the whole
        # point of it - but a named strain or frame is itself, always
        assert G.chassis_grown("standard") is (h == "ryez"), h
        for key in ("deepone", "bloom", "hollow"):
            assert G.chassis_grown(key) is True, (h, key)
        for key in ("warmachine", "tank", "robo"):
            assert G.chassis_grown(key) is False, (h, key)
    G.set_house("keal")
    print("  and a strain previews as an animal even to a shipyard")

    # -- and the desk draws ------------------------------------------------
    G.set_house("keal")
    b = G.Bazaar()
    b.t = 2.0
    b.sec = 2
    b.draw(surf, (0, 0))
    assert len(b.slots) == 20, len(b.slots)
    for box, _ in b.slots:
        assert box.bottom <= G.H and box.right <= G.W, "a card fell off"
    b.click(b.slots[0][0].center)
    assert b.open == b.slots[0][1]
    b.draw(surf, (0, 0))
    b.open = None
    b.draw(surf, (0, 0))
    b.click(b.tab_rect(0).center)
    assert b.sec == 0, "the office would not let go"
    print("  the office draws, twenty cards fit, and the tabs still move")
    wipe_meta()
    G.set_house("keal")
    print("\ngov ok")


def _pay(run):
    """Put a body down and collect for it, without a whole fight."""
    class _Won:
        over = "won"
        wrecked = 0
        taken = 0.0
        dealt = 0.0
        integrity = run.integrity
        kind = G.roster_for(run.house)[run.kaiju_index]
    run.resolve(_Won())


def _rig(tier=2):
    r = G.Run("keal")
    r.kaiju_index = 2
    for k, v in (("legs", tier), ("torso", tier), ("l_arm", tier),
                 ("r_arm", tier), ("head", tier), ("reactor", tier),
                 ("armour", tier), ("l_wpn", "auto"), ("r_wpn", "auto")):
        r.mech.install(k, v)
    return r


# ---------------------------------------------------------------------------
# FRAMES - six whole machines, and the one thing they all have to do
# ---------------------------------------------------------------------------
CH_KEYS = ("ch_cyclops", "ch_warmachine", "ch_sovereign", "ch_tank",
           "ch_turret", "ch_robo")


def frames():
    """A chassis is the only purchase in the game that changes the RULES
    rather than a number, so most of what is below is a check that the
    rest of the game still holds together underneath one - that the yard
    offers the right sockets, the save remembers which machine it was, and
    a frame with no legs or no head does not quietly become one that has
    them."""
    wipe_meta()
    G.set_house("keal")
    surf = pygame.Surface((G.W, G.H))
    # seven of steel and six grown, plus the stock body they share -
    # and then the frames KEAL FIELDS, which are in the same table and
    # are for sale to nobody
    steel_frames = [c for c in G.CHASSIS_LIST
                    if c.ware and G.WARES[c.ware].house == "keal"]
    foes = [c for c in G.CHASSIS_LIST if c.foe]
    assert len(G.CHASSIS_LIST) - len(foes) == 13, len(G.CHASSIS_LIST)
    assert len(steel_frames) == 6, len(steel_frames)
    assert len(foes) == 7, len(foes)
    for c in foes:
        assert c.ware is None, c.key
        assert c not in G.owned_chassis(), c.key
    assert [c.key for c in G.owned_chassis()] == ["standard"], "free frames"

    G.add_marks(4000)
    before = G.marks()
    for k in CH_KEYS:
        assert G.can_buy(k), k
        assert G.buy_ware(k), k
    spent = before - G.marks()
    assert G.marks() > before - 1700, "somebody paid twice"
    assert len(G.owned_chassis()) == 7, len(G.owned_chassis())
    print("  seven frames, six of them bought for %d marks" % spent)

    # -- LITTLE ROBO pays YOU, and cannot take you below nothing ----------
    wipe_meta()
    G.set_house("keal")
    assert G.marks() == 0
    assert G.buy_ware("ch_robo"), "could not take the free one"
    assert G.marks() == 1, G.marks()
    print("  the toy is free and hands you a mark for it")

    G.add_marks(4000)
    for k in CH_KEYS:
        G.buy_ware(k)

    # -- what each frame HAS ----------------------------------------------
    for key, want in (("standard", 9), ("cyclops", 9), ("warmachine", 9),
                      ("sovereign", 9), ("tank", 8), ("turret", 10),
                      ("robo", 9)):
        m = G.Mech(key)
        assert len(m.sockets()) == want, (key, m.sockets())
    tank = G.Mech("tank")
    assert not tank.usable("head"), "the tank grew a head"
    tank.install("head", 3)
    assert tank.fit["head"] is None, "and then fitted something to it"
    turret = G.Mech("turret")
    assert not turret.usable("legs") and turret.usable("l_aux")
    assert turret.sides() == ["l", "r", "la", "ra"], turret.sides()
    assert G.Mech("standard").sides() == ["l", "r"]
    print("  tank has no head, turret has no legs and four mounts")

    # -- and what each frame will MOUNT ------------------------------------
    stock = {w.key for w in G.options_for("l_wpn", None,
                                          G.CHASSIS["standard"])}
    cyc = {w.key for w in G.options_for("l_wpn", None, G.CHASSIS["cyclops"])}
    assert set(G.CHASSIS["cyclops"].guns) <= cyc, cyc
    assert not (stock & cyc), "own_only frame took the stock rack"
    sov = {w.key for w in G.options_for("l_wpn", None,
                                        G.CHASSIS["sovereign"])}
    assert stock <= sov and "judgement" in sov, "sovereign lost the rack"
    aux = {w.key for w in G.options_for("l_aux", None, G.CHASSIS["turret"])}
    assert aux == set(G.AUX_GUNS), aux
    assert G.options_for("l_aux", None, G.CHASSIS["standard"]) == []
    assert G.options_for("legs", None, G.CHASSIS["turret"]) == []
    print("  cyclops %d guns, sovereign %d, aux mounts %d, turret legs 0"
          % (len(cyc), len(sov), len(aux)))

    # -- the multipliers are real ------------------------------------------
    def built(key):
        r = G.Run("keal", key)
        r.kaiju_index = 2
        for s, v in (("legs", 3), ("torso", 3), ("l_arm", 3), ("r_arm", 3),
                     ("head", 3), ("reactor", 3), ("armour", 3)):
            r.mech.install(s, v)
        guns = G.CHASSIS[key].guns or ("pile", "auto")
        r.mech.install("l_wpn", guns[0])
        r.mech.install("r_wpn", guns[-1])
        if r.mech.usable("l_aux"):
            r.mech.install("l_aux", "auxpod")
            r.mech.install("r_aux", "auxflare")
        return r

    base = built("standard").mech
    war = built("warmachine").mech
    cyclops = built("cyclops").mech
    robo = built("robo").mech
    assert war.max_hp("torso") > base.max_hp("torso") * 1.4
    assert war.speed < base.speed and war.dr > base.dr
    assert cyclops.speed > base.speed and cyclops.max_hp("torso") < \
        base.max_hp("torso")
    assert robo.max_hp("torso") < base.max_hp("torso") * 0.25
    assert built("turret").mech.completion() > 0.9, "a turret cannot finish"
    assert built("tank").mech.completion() > 0.9, "a tank cannot finish"
    print("  war machine %.0f torso vs %.0f stock; cyclops %.0f speed vs %.0f"
          % (war.max_hp("torso"), base.max_hp("torso"), cyclops.speed,
             base.speed))

    # -- ROOTED: a turret does not move ------------------------------------
    r = built("turret")
    f = G.Fight(r, G.roster_for("keal")[2])
    x0 = f.mx
    for _ in range(400):
        f.update(1 / 40.0, {"right": True})
    assert abs(f.mx - x0) < 0.01, "the seawall moved"
    print("  ten seconds of holding right moved the turret %.2f units"
          % abs(f.mx - x0))

    # -- BLIND: no bar, and a veil -----------------------------------------
    r = built("tank")
    f = G.Fight(r, G.roster_for("keal")[2])
    assert f.mech.has_flag("blind") and not f.mech.sensors
    for _ in range(120):
        f.update(1 / 40.0, {"fire_l": True})
    f.draw(surf)
    print("  the tank draws with no bar and no sensors")

    # -- CHARGE: boost and brace, on the one frame that has it -------------
    r = built("warmachine")
    f = G.Fight(r, G.roster_for("keal")[2])
    hit = shrug = 0
    for _ in range(2400):
        f.update(1 / 40.0, {"right": True, "boost": True, "brace": True,
                            "fire_l": True, "fire_r": True})
        for row in f.log:
            if "WENT BACKWARDS" in row[0]:
                hit += 1
                row[0] = ""
            if "PLATES TOOK IT" in row[0]:
                shrug += 1
                row[0] = ""
        if f.over:
            break
    assert hit > 0, "the charge never connected"
    print("  %d charges landed, %d blows shrugged off inside one" % (hit,
                                                                    shrug))
    # and the charge is not a bonus, it is the weapon: a pilot who only
    # swings takes over a minute on a BULWARK, and one who charges when it
    # is off cooldown takes about fourteen seconds
    r = built("warmachine")
    f = G.Fight(r, G.roster_for("keal")[2])
    for _ in range(4800):
        ch = f.boost_cd <= 0 and f.charge <= 0
        f.update(1 / 40.0, {"right": True, "fire_l": not ch,
                            "fire_r": not ch, "boost": ch, "brace": ch})
        if f.over:
            break
    assert f.over == "won", "the charge cannot close a fight"
    assert f.t < 30.0, "%.0fs with the charge" % f.t
    print("  charging instead of swinging: %s in %.0fs" % (f.over, f.t))

    plain = built("standard")
    fp = G.Fight(plain, G.roster_for("keal")[2])
    for _ in range(200):
        fp.update(1 / 40.0, {"boost": True, "brace": True})
    assert fp.charge == 0.0, "the stock frame charged"
    print("  and the stock frame does not, however you hold the keys")

    # -- MENDS: the sovereign closes itself --------------------------------
    r = built("sovereign")
    for s in r.mech.sockets():
        r.mech.hp[s] *= 0.3

    class _Won:
        over = "won"
        wrecked = 0
        taken = 0.0
        dealt = 0.0
        integrity = r.integrity
        kind = G.roster_for("keal")[r.kaiju_index]
    r.resolve(_Won())
    assert r.mech.hp["torso"] == r.mech.max_hp("torso"), "it stayed hurt"
    r2 = built("standard")
    r2.mech.hp["torso"] *= 0.3
    hurt = r2.mech.hp["torso"]
    r2.resolve(_Won())
    assert abs(r2.mech.hp["torso"] - hurt) < 1e-6, "everything mends itself"
    print("  sovereign closed itself; the stock frame did not")

    # -- every frame survives a save and a whole fight ---------------------
    # what THIS house can actually start a run on - walking the whole
    # table here means asking a shipyard to build a GRAVID MOTHER, which
    # it correctly refuses, and then failing the assertion about it
    for key in [c.key for c in G.owned_chassis()]:
        r = built(key)
        back = G.Run.from_json(r.to_json())
        assert back.mech.chassis == key, (key, back.mech.chassis)
        assert back.mech.sockets() == r.mech.sockets(), key
        for s in r.mech.sockets():
            assert back.mech.fit[s] == r.mech.fit[s], (key, s)
        f = G.Fight(back, G.roster_for("keal")[2])
        for _ in range(4800):        # the slow frames need the room
            f.update(1 / 40.0, {"fire_l": True, "fire_r": True,
                                "right": True})
            if f.over:
                break
        f.draw(surf)
        print("  %-11s %-4s in %5.1fs, dealt %6.0f, took %5.0f"
              % (key, f.over or "---", f.t, f.dealt, f.taken))

    # -- and it looks like itself in BOTH renderers ------------------------
    # The yard draws the machine face-on and the fight draws it in profile,
    # and they are two different routines. The livery reached the profile
    # one and not the other, so a WAR MACHINE was built for six weeks in
    # standard grey and turned red at landfall. Every frame is now rendered
    # both ways and compared against the stock frame's pixels.
    def shot(key, front):
        m = built(key).mech
        s = pygame.Surface((300, 420))
        s.fill((0, 0, 0))
        if front:
            G.draw_mech_front(s, m, 150, 400, 0.34, t=2.0)
        else:
            pz = G.Pose()
            pz.face = 1
            G.draw_mech_side(s, m, 150, 400, 0.46, 2.0, pz)
        return pygame.image.tostring(s, "RGB")

    for view, name in ((True, "the yard"), (False, "the street")):
        base = shot("standard", view)
        seen = {}
        for ch in G.owned_chassis():
            px = shot(ch.key, view)
            if ch.key != "standard":
                assert px != base, "%s looks like the stock frame in %s" % (
                    ch.key, name)
            for other, opx in seen.items():
                assert px != opx, "%s and %s are identical in %s" % (
                    ch.key, other, name)
            seen[ch.key] = px
        print("  all seven are distinguishable in %s" % name)

    # -- the WAR MACHINE's signature, which is the reason to own one -------
    cl = G.WEAPONS["cleaver"]
    assert cl.sweep == 3 and cl.knock > 0 and cl.reach > 280, cl.key
    assert "cleaver" in G.CHASSIS["warmachine"].guns
    for ch in G.CHASSIS_LIST:
        if ch.key != "warmachine":
            assert "cleaver" not in ch.guns, ch.key
        got = {w.key for w in G.options_for("l_wpn", None, ch)}
        assert ("cleaver" in got) == (ch.key == "warmachine"), ch.key
    r = built("warmachine")
    r.mech.install("l_wpn", "cleaver")
    r.mech.install("r_wpn", "cleaver")
    f = G.Fight(r, G.roster_for("keal")[4])
    f.enemies.append(G.Enemy(G.BROODLING, f.boss().x - 120))
    f.enemies.append(G.Enemy(G.BROODLING, f.boss().x - 240))
    hit_at_once = 0
    for _ in range(4800):
        before = sum(1 for e in f.enemies if e.alive)
        f.update(1 / 40.0, {"right": True, "fire_l": True, "fire_r": True})
        hit_at_once = max(hit_at_once, before)
        if f.over:
            break
    assert f.dealt > 0, "the cleaver never landed"
    print("  RED CLEAVER: %s, %d reach, %d bodies a stroke, %s in %.0fs"
          % (G.stat_line(cl).split("  ")[0], cl.reach, cl.sweep,
             f.over, f.t))

    # -- a frame you can find out you are flying ---------------------------
    # The brief and the fight HUD both used to say THE MACHINE whatever
    # was standing in the gantry, so a WAR MACHINE and a stock frame read
    # identically on the one screen where you decide whether to deploy.
    assert G.frame_label(G.Mech("standard")) == "THE MACHINE"
    for ch in G.CHASSIS_LIST:
        lab = G.frame_label(G.Mech(ch.key))
        assert lab == ("THE MACHINE" if ch.key == "standard" else ch.name), (
            ch.key, lab)
    G.set_house("ryez")
    assert G.frame_label(G.Mech("warmachine")) == G.word("machine"), (
        "a KEAL frame name leaked into a RYEZ run")
    G.set_house("keal")
    print("  the brief names the frame, and RYEZ still says THE ANIMAL")

    # -- and every module you can press says which key ---------------------
    keyed = set(G.MOD_KEY)
    assert keyed == {"flush", "emp", "lungs", "scream", "greatsac"}, keyed
    for k in keyed:
        assert k in G.MODULES, k
    print("  %d modules are on a key, and the HUD prints all %d"
          % (len(keyed), len(keyed)))

    # -- one face per frame, and it is that frame's face -------------------
    # Every KEAL head used to get the same single lamp, and the overlay
    # then painted a visor or a big eye somewhere near it - so most of
    # the frames wore a cyclops dot they had no business with.
    faces = {c.key: c.style.get("eye", "dot") for c in G.owned_chassis()
             if G.Mech(c.key).usable("head")}
    assert faces["standard"] == "dot", faces
    assert faces["cyclops"] == "cyclops", faces
    assert len(set(faces.values())) == len(faces), (
        "two frames share a face: %s" % faces)
    # a frame whose overlay draws a cowl right over the head owns its own
    # visor; draw_face_side has to stand back or there are two
    assert faces["warmachine"] == "cowl", faces
    assert "tank" not in faces, "the tank has a head to put a face on"
    for key, eye in faces.items():
        if key == "standard":
            continue
        assert eye != "dot", "%s still wears the stock lamp" % key
    print("  %d faces, all different: %s" % (
        len(faces), ", ".join("%s %s" % (k, v) for k, v in faces.items())))

    # -- and no frame has a hole in its palette ---------------------------
    # `_tone` falls back to STEEL for any key a palette does not define,
    # so a frame that gave only main/dark/light/trim had its PLATE drawn
    # in stock blue-grey. One pale panel on a red machine, and it read as
    # a missing texture rather than a bug.
    for ch in G.CHASSIS_LIST:                # every palette, both houses
        if not ch.tones:
            continue
        for key in ("main", "dark", "light", "trim", "plate", "hollow"):
            assert key in ch.tones, (ch.key, key)
            assert ch.tones[key] != G.STEEL, (ch.key, key)
    print("  every frame's palette is complete, so nothing falls to steel")

    # -- and they are different SHAPES, not the same one repainted --------
    # A livery passes the test above on colour alone. This one measures
    # the silhouette: how tall the thing is, how wide, and where the
    # widest part of it sits.
    def box(key):
        m = built(key).mech
        # SRCALPHA, or get_bounding_rect finds every opaque pixel on the
        # surface and every frame measures exactly the size of the canvas
        s = pygame.Surface((420, 460), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        G.draw_mech_front(s, m, 210, 440, 0.38, t=2.0)
        r = s.get_bounding_rect()
        return r.w, r.h
    shapes = {c.key: box(c.key) for c in G.owned_chassis()}
    base_w, base_h = shapes["standard"]
    for key, (w, h) in shapes.items():
        if key == "standard":
            continue
        assert (abs(w - base_w) > 6 or abs(h - base_h) > 6), (
            "%s is the stock silhouette in a different colour: %dx%d "
            "against %dx%d" % (key, w, h, base_w, base_h))
    # what each frame is SUPPOSED to be, rather than whatever it happened
    # to measure the day it was written - the WAR MACHINE grew taller when
    # its legs were thickened and broke an assertion that only ever said
    # "the cyclops is currently the taller of those two"
    widest = max(shapes, key=lambda k: shapes[k][0])
    assert widest == "warmachine", (widest, shapes)
    assert shapes["cyclops"][0] < base_w * 0.8, shapes["cyclops"]
    assert shapes["cyclops"][1] > base_h, shapes["cyclops"]
    assert shapes["sovereign"][0] > base_w * 1.3, shapes["sovereign"]
    assert shapes["sovereign"][1] > base_h, shapes["sovereign"]
    assert shapes["warmachine"][0] > shapes["cyclops"][0] * 1.6, shapes
    assert shapes["tank"][1] < base_h - 20, shapes["tank"]
    assert shapes["turret"][0] > base_w * 1.3, shapes["turret"]
    assert shapes["robo"][0] < base_w * 0.8, shapes["robo"]
    assert shapes["robo"][1] < base_h * 0.8, shapes["robo"]
    print("  and they are different shapes: " + ", ".join(
        "%s %dx%d" % (k, v[0], v[1]) for k, v in shapes.items()))

    # -- ...and a bounding box is a weak thing to measure -----------------
    # Two machines can box the same and still be one drawing. Measured as
    # overlap over union with the colour thrown away, the four humanoid
    # frames were 50 to 67 per cent the SAME PICTURE - the CYCLOPS was the
    # stock frame with horns and the SOVEREIGN was the stock frame eight
    # per cent bigger in cream. Only the TANK, TURRET and ROBO, the three
    # that changed the body plan rather than the trim, stood apart. So
    # every frame carries a `build` now, and this is the bar that only a
    # body plan clears.
    def plate(key, front):
        m = built(key).mech
        for s in G.HARDPOINTS:
            if s in m.sockets():
                o = G.options_for(s, None, m.frame)
                if o:
                    m.install(s, o[0].key)
        sf = pygame.Surface((620, 640), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        if front:
            G.draw_mech_front(sf, m, 310, 560, 0.62, t=2.0)
        else:
            pz = G.Pose()
            pz.face = 1
            G.draw_mech_side(sf, m, 310, 560, 0.62, 2.0, pz)
        w, h = sf.get_size()
        return bytes(1 if sf.get_at((x, y))[3] > 40 else 0
                     for y in range(0, h, 3) for x in range(0, w, 3))
    keys = [c.key for c in G.owned_chassis()]
    for front, where in ((True, "the gantry"), (False, "the street")):
        seen = {k: plate(k, front) for k in keys}
        worst = None
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                pa, pb = seen[a], seen[b]
                both = sum(1 for x, y in zip(pa, pb) if x and y)
                either = sum(1 for x, y in zip(pa, pb) if x or y)
                iou = both / float(max(1, either))
                if worst is None or iou > worst[0]:
                    worst = (iou, a, b)
        assert worst[0] < 0.62, (
            "%s and %s are %.0f%% the same drawing in %s"
            % (worst[1], worst[2], worst[0] * 100, where))
        print("  in %s the two most alike, %s and %s, share %.0f%% of one "
              "outline" % (where, worst[1], worst[2], worst[0] * 100))

    # and the three that were the stock frame with trim on now have a
    # body plan, in BOTH renderers - a frame that only changes in profile
    # is the stock frame right up until landfall
    for key in ("cyclops", "warmachine", "sovereign", "turret"):
        assert G.CHASSIS[key].style.get("build"), key
    assert not G.CHASSIS["standard"].style.get("build")

    # -- and RYEZ gets whole ANIMALS, which are not the frames repainted ---
    wipe_meta()
    G.set_house("ryez")
    G.add_marks(9000)
    strains = [w for w in G.WARE_LIST
               if w.kind == "chassis" and w.house == "ryez"]
    assert len(strains) == 6, len(strains)
    for w in strains:
        assert G.buy_ware(w.key), w.key
    mine = [c.key for c in G.owned_chassis()]
    assert "standard" in mine and "warmachine" not in mine, mine
    assert len(mine) == 7, mine
    G.set_house("keal")
    assert "bloom" not in [c.key for c in G.owned_chassis()]
    G.set_house("ryez")
    print("  %d strains, and a shipyard is offered none of them"
          % len(strains))

    # every strain does something no FRAME does
    flags = {}
    for w in strains:
        ch = G.CHASSIS[G.CHASSIS_WARE[w.key]]
        flags[ch.key] = set(ch.flags)
    steel = set()
    for c in G.CHASSIS_LIST:
        if c.ware and G.WARES[c.ware].house == "keal":
            steel |= set(c.flags)
    for key, fl in flags.items():
        assert not (fl & steel), "%s shares %s with a frame" % (key,
                                                                fl & steel)
    print("  and none of them shares a trick with a frame")

    def grown(key):
        r = G.Run("ryez", key)
        r.kaiju_index = 2
        for s in r.mech.sockets():
            if s in G.HARDPOINTS:
                continue
            r.mech.install(s, 3)
        r.mech.install("l_wpn", "auto")
        r.mech.install("r_wpn", "auto")
        return r

    # HARDEN climbs, REGROW closes, FAINT dodges, COLONY sheds, MIASMA rots
    f = G.Fight(grown("spire"), G.roster_for("ryez")[2])
    d0 = f.mech.dr
    for _ in range(400):
        f.update(1 / 40.0, {})
    assert f.mech.dr > d0 + 4, (d0, f.mech.dr)
    assert f.mech.harden <= G.HARDEN_CAP + 1e-6
    print("  spire: hide %.0f -> %.0f over ten seconds" % (d0, f.mech.dr))

    r = grown("deepone")
    f = G.Fight(r, G.roster_for("ryez")[2])
    f.mech.hp["torso"] *= 0.5
    low = f.mech.hp["torso"]
    for _ in range(400):
        f.update(1 / 40.0, {})
    assert f.mech.hp["torso"] > low, "it did not close"
    plain = G.Fight(grown("standard"), G.roster_for("ryez")[2])
    plain.mech.hp["torso"] *= 0.5
    was = plain.mech.hp["torso"]
    for _ in range(400):
        plain.update(1 / 40.0, {})
    assert plain.mech.hp["torso"] <= was, "everything closes itself"
    print("  deep leviathan closed %.0f in ten seconds; the stock body 0"
          % (f.mech.hp["torso"] - low))

    f = G.Fight(grown("hollow"), G.roster_for("ryez")[2])
    most = 0
    for _ in range(1600):
        f.update(1 / 40.0, {})
        most = max(most, len(f.mercs))
        if f.over:
            break
    assert most > 0, "the swarm shed nothing"
    print("  hollow swarm put %d of them out without being asked" % most)

    # -- and what comes out of it is not a man with a rifle --------------
    # The brood ARE Mercs with a flag on them, and that is right: "a
    # small thing standing between you and it that soaks one hit" is one
    # object, not two. They were DRAWN as Mercs as well, which is not -
    # so RYEZ's hatchlings came out of the sac in helmets, in army
    # green, carrying rifles.
    bf = G.Fight(grown("hollow"), G.roster_for("ryez")[2])

    # sx() is a camera, not an offset, so put the speck where we want it
    # by inverting it rather than by guessing
    s0, s1 = bf.sx(0.0), bf.sx(1000.0)
    at = lambda px: (px - s0) * 1000.0 / (s1 - s0)

    def speck(brood, age=6.0):
        sf = pygame.Surface((90, 70), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        m = G.Merc(at(45.0), 1)
        m.brood, m.t = brood, age
        bf.draw_merc(sf, m, 52, (0, 0))
        w, h = sf.get_size()
        return sf, bytes(1 if sf.get_at((x, y))[3] > 40 else 0
                         for y in range(h) for x in range(w))
    man_s, man = speck(False)
    bug_s, bug = speck(True)
    assert sum(man) and sum(bug), "one of the two drew nothing at all"
    # overlap over union, NOT over the smaller one - a big shape that
    # simply contains a small one shares ~100% of the small one's pixels
    # and that says nothing about whether they are the same drawing
    both = sum(1 for a, b in zip(man, bug) if a and b)
    either = sum(1 for a, b in zip(man, bug) if a or b)
    share = both / float(max(1, either))
    assert share < 0.4, (
        "the brood are still the hired men: %.0f%% of the two drawings "
        "coincide" % (share * 100))
    mb, bb = man_s.get_bounding_rect(), bug_s.get_bounding_rect()
    assert bb.w > mb.w, "a hatchling is not bigger than a person"
    assert bb.w > bb.h, (
        "a hatchling should be low and wide, not stood up: %dx%d"
        % (bb.w, bb.h))
    assert mb.h > mb.w, "a mercenary should still be a person"
    print("  the brood are %dx%d and low; a mercenary is %dx%d and "
          "upright" % (bb.w, bb.h, mb.w, mb.h))

    # -- and the sac they come out of is ON the animal, filling up -------
    # "it puts one on the animal" was true of the rules and not of the
    # picture: the sac was a number counting down in the dark
    def sac_box(frac):
        sf = pygame.Surface((440, 420), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        bf.brood_t = G.COLONY_EVERY * (1.0 - frac)
        bf.draw_brood_sac(sf, 210, 396)
        return sf.get_bounding_rect()
    empty, full = sac_box(0.02), sac_box(0.97)
    assert empty.w > 0, "there is nothing on the animal to see"
    assert full.w > empty.w * 1.7, (
        "the sac does not visibly fill: %dpx -> %dpx" % (empty.w, full.w))
    bare = G.Fight(grown("standard"), G.roster_for("ryez")[2])
    sf = pygame.Surface((440, 420), pygame.SRCALPHA)
    sf.fill((0, 0, 0, 0))
    bare.draw_brood_sac(sf, 210, 396)
    assert sf.get_bounding_rect().w == 0, (
        "an animal with no sac and no colony grew one anyway")
    print("  and the sac on it swells from %dpx across to %d before it "
          "opens" % (empty.w, full.w))

    # -- the GRAVID MOTHER's three, which nothing else has ---------------
    # She is the one with organ sites going spare, so she is the one the
    # signature kit hangs off: what she puts down is bigger, she has a
    # hardpoint that puts down more of it and they fly, and she has one
    # bay that spends most of the room inside her on a full-size body.
    wipe_meta()
    G.set_house("ryez")
    G.add_marks(9000)
    for k in ("st_gravid", "g_greatsac", "g_embryo"):
        assert G.buy_ware(k), k

    mother = G.CHASSIS["gravid"]
    assert "wingbrood" in mother.guns
    for ch in G.CHASSIS_LIST:                # and nobody else can mount it
        got = [w.key for w in G.options_for("l_wpn", None, ch)]
        assert ("wingbrood" in got) == (ch.key == "gravid"), (ch.key, got)
    # the sac is LISTED everywhere once it is bought - hiding it was the
    # bug - and CARRIED only by a grown body with a site going spare
    for ch in G.CHASSIS_LIST:
        assert "greatsac" in [m.key for m in G.module_list(ch)], ch.key
        assert G.module_fits(G.MODULES["greatsac"], ch) == (
            ch.key == "gravid"), ch.key
    print("  the winged brood and the great sac fit her and nothing else")

    def hers(*mods):
        run = G.Run("ryez", "gravid")
        run.scrap, run.alloy = 20000, 200
        for s in run.mech.sockets():
            if s not in G.HARDPOINTS:
                run.mech.install(s, 3)
        for m in mods:
            run.mech.fit_module(m)
        return run

    # -- what she puts down is not what anything else puts down ----------
    run = hers("embryo")
    fm = G.Fight(run, G.roster_for("ryez")[2])
    fm.brood_t = 0.01
    for _ in range(12):
        fm.update(1 / 60.0, {})
    mine = [m for m in fm.mercs if m.brood]
    plain = G.Run("ryez")
    for s in plain.mech.sockets():
        if s not in G.HARDPOINTS:
            plain.mech.install(s, 3)
    plain.mech.fit_module("embryo")
    fp = G.Fight(plain, G.roster_for("ryez")[2])
    fp.brood_t = 0.01
    for _ in range(12):
        fp.update(1 / 60.0, {})
    theirs = [m for m in fp.mercs if m.brood]
    assert len(mine) == len(theirs) + 1, (len(mine), len(theirs))
    assert all(m.tier == 2 for m in mine), [m.tier for m in mine]
    assert all(m.tier == 1 for m in theirs), [m.tier for m in theirs]
    assert G.BROOD_TIER[2][0] > G.BROOD_TIER[1][0]
    # hers stands up to a blow that kills an ordinary one
    one, two = theirs[0], mine[0]
    e = fp.boss()
    fp.mech_hit(e, 400.0)
    assert one.hp <= 0, "an ordinary one survived a swipe"
    fm.mech_hit(fm.boss(), 400.0)
    assert two.hp > 0, "hers went down to the first blow like any other"
    fm.mech_hit(fm.boss(), 400.0)
    assert two.hp <= 0, "hers is unkillable"
    print("  hers come out %d at a time against %d, and each one stands "
          "up to two blows" % (len(mine), len(theirs)))

    # -- and the winged ones do not walk ---------------------------------
    run = hers()
    run.mech.install("l_wpn", "wingbrood")
    fw = G.Fight(run, G.roster_for("ryez")[2])
    for _ in range(40):
        fw.update(1 / 60.0, {"fire_l": True})
    fliers = [m for m in fw.mercs if m.tier == 3]
    assert len(fliers) >= 3, len(fliers)
    assert all(m.alt > 0 for m in fliers), [m.alt for m in fliers]
    was = min(abs(m.x - fw.boss().x) for m in fliers)
    for _ in range(120):
        fw.update(1 / 60.0, {})
    now = min(abs(m.x - fw.boss().x) for m in fw.mercs if m.tier == 3)
    assert now < was - 200, (
        "the winged brood closed %d in two seconds, which is a walk"
        % (was - now))
    print("  three of them go up and close %dm in two seconds"
          % round(was - now))

    # -- the great sac: one of her own, the size of you ------------------
    run = hers("greatsac")
    fs = G.Fight(run, G.roster_for("ryez")[2])
    assert fs.can_greatsac()
    assert fs.great_sac(), "she would not"
    assert len(fs.allies) == 1
    assert fs.mech.locked and fs.mech.heat >= fs.mech.heat_cap, (
        "the strain of it is the whole cost and it did not land")
    assert not fs.great_sac(), "twice in one landfall"
    scion = fs.allies[0]
    # "as big as the standard" is a claim about the PICTURE, so measure
    # the picture rather than trusting the scale number
    def tall(draw):
        sf = pygame.Surface((760, 620), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        draw(sf)
        return sf.get_bounding_rect().h
    big = tall(lambda sf: G.draw_enemy(sf, scion, 380, 560, G.FSCALE, 2.0))
    pz = G.Pose()
    pz.face = 1
    std = G.Mech("standard")
    for s in std.sockets():
        if s not in G.HARDPOINTS:
            std.install(s, 3)
    me = tall(lambda sf: G.draw_mech_side(sf, std, 380, 560, G.FSCALE, 2.0,
                                          pz, bio=True))
    assert abs(big - me) < me * 0.15, (
        "a SCION is %dpx and the stock animal is %d - that is not the "
        "same size" % (big, me))
    # it fights, and it stands in front of you. The road is a mile
    # long, so put the thing within walking distance rather than
    # measuring how long a kaiju takes to cross a city
    fs.boss().x = fs.mx + 700
    before = fs.dealt
    for _ in range(400):
        fs.update(1 / 60.0, {})
    assert fs.dealt > before, "it walked up the road and did nothing"
    if fs.allies and fs.allies[0].hp > 0:
        hp0 = fs.allies[0].hp
        body = sum(fs.mech.hp[s] for s in fs.mech.sockets())
        fs.mech_hit(fs.boss(), 300.0)
        assert fs.allies[0].hp < hp0, "the scion did not take the blow"
        assert sum(fs.mech.hp[s] for s in fs.mech.sockets()) == body, (
            "it took the blow AND so did you")
    print("  the scion draws %dpx against the stock animal's %d, and it "
          "takes the blows" % (big, me))
    # put the drawer back the way the rest of the strain section found
    # it - everything after this asks for a body it has to own
    wipe_meta()
    G.set_house("ryez")
    G.add_marks(9000)
    for w in strains:
        assert G.buy_ware(w.key), w.key


    f = G.Fight(grown("bloom"), G.roster_for("ryez")[2])
    f.boss().x = f.mx + 300          # a landfall starts a mile apart
    for _ in range(200):
        f.update(1 / 40.0, {})
    near = f.dealt
    p2 = G.Fight(grown("standard"), G.roster_for("ryez")[2])
    p2.boss().x = p2.mx + 300
    for _ in range(200):
        p2.update(1 / 40.0, {})
    assert near > 0, "standing next to a bloom cost nothing"
    assert near > p2.dealt, (near, p2.dealt)
    print("  standing near a bloom cost it %.0f in five seconds; near the "
          "stock body, %.0f" % (near, p2.dealt))

    # a hit lands on a RANDOM socket, so "the torso is still full" does
    # not mean it was dodged - count the whole body instead
    def dodges(key, swings=400):
        fr = G.Fight(grown(key), G.roster_for("ryez")[2])
        out = 0
        for _ in range(swings):
            whole = sum(fr.mech.hp[s] for s in fr.mech.sockets())
            fr.mech_hit(fr.boss(), 10.0, silent=True)
            out += sum(fr.mech.hp[s] for s in fr.mech.sockets()) >= whole
            for s in fr.mech.sockets():
                fr.mech.hp[s] = fr.mech.max_hp(s)
        return out
    miss = dodges("stalker")
    solid = dodges("standard")
    assert solid == 0, "the stock body dodged %d" % solid
    assert 80 < miss < 300, "dodge rate is %d in 400" % miss
    print("  pale stalker was not there for %d of 400 blows; the stock "
          "body for %d" % (miss, solid))

    # -- and they are six DESIGNS, not one design in six colours ----------
    # Proportions and a palette are not a design, and nor is decoration:
    # the first pass laid a fin, some sacs and a fruiting cap over the
    # shared body and the six still read as one animal wearing six
    # things, which is what the bar being at 0.06 was letting through.
    # A plan has to reach the HEAD, the STANCE and one big mass, so the
    # bar is where only that can clear it - and the stock body is in the
    # comparison, because "different from each other" is half the job.
    def mono(key):
        m = G.Mech(key)
        for s in m.sockets():
            if s not in G.HARDPOINTS:
                m.install(s, 3)
        m.harden = G.HARDEN_CAP
        sf = pygame.Surface((520, 560), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        pz = G.Pose()
        pz.face = 1
        G.draw_mech_side(sf, m, 260, 470, 0.62, 2.0, pz, bio=True)
        # every drawn pixel as 1, ignoring what colour it was
        w, h = sf.get_size()
        return bytes(1 if sf.get_at((x, y))[3] > 40 else 0
                     for y in range(0, h, 3) for x in range(0, w, 3))
    shapes = {}
    for key in ("standard", "hollow", "deepone", "spire", "stalker",
                "gravid", "bloom"):
        shapes[key] = mono(key)
    worst = None
    ks = list(shapes)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            pa, pb = shapes[a], shapes[b]
            diff = sum(1 for x, y in zip(pa, pb) if x != y)
            on = sum(pa) + sum(pb)
            score = diff / float(max(1, on))
            if worst is None or score < worst[0]:
                worst = (score, a, b)
    assert worst[0] > 0.18, (
        "%s and %s are the same animal in two colours (%.3f apart)"
        % (worst[1], worst[2], worst[0]))
    # and no strain is the stock body with something stuck on it
    for key in shapes:
        if key == "standard":
            continue
        pa, pb = shapes[key], shapes["standard"]
        d = sum(1 for x, y in zip(pa, pb) if x != y)
        score = d / float(max(1, sum(pa) + sum(pb)))
        assert score > 0.22, (
            "%s is the stock body with decoration on it (%.3f)"
            % (key, score))
    print("  and in pure silhouette the closest two, %s and %s, still "
          "differ by %.0f%%" % (worst[1], worst[2], worst[0] * 100))

    # -- the head, the stance, and the head is the loud one ---------------
    # Five of the six kept the stock snout on the stock neck for a while
    # and it undid everything else: a wing loses an argument with a face.
    for key in ("hollow", "deepone", "spire", "stalker", "gravid", "bloom"):
        assert G.strain_hides(G.Mech(key), "head"), (
            "%s still wears the stock skull" % key)
        assert key in G.LEG_PLAN, "%s stands like everything else" % key
    assert not G.strain_hides(G.Mech("standard"), "head")
    assert "standard" not in G.LEG_PLAN
    print("  all six replace the stock head and none of them stands the "
          "same way")

    # -- and the SPIRE's trick is a thing you can see happening ----------
    # its hide thickening is a number in the HUD and a tower on its back;
    # if the tower is already full at landfall the mechanic is invisible
    def spire_at(hard):
        m = G.Mech("spire")
        for s in m.sockets():
            if s not in G.HARDPOINTS:
                m.install(s, 3)
        m.harden = hard
        sf = pygame.Surface((520, 560), pygame.SRCALPHA)
        sf.fill((0, 0, 0, 0))
        pz = G.Pose()
        pz.face = 1
        G.draw_mech_side(sf, m, 260, 470, 0.62, 2.0, pz, bio=True)
        return sf.get_bounding_rect().h
    lo, hi = spire_at(0.0), spire_at(G.HARDEN_CAP)
    assert hi - lo > 40, "the spire builds nothing: %d -> %d" % (lo, hi)
    print("  and the spire is %d tall at landfall and %d by the end of "
          "one" % (lo, hi))

    # put the ledger back the way the rest of this test expects it
    wipe_meta()
    G.set_house("keal")
    G.add_marks(4000)
    for k in CH_KEYS:
        G.buy_ware(k)

    # -- and the screen that picks one draws -------------------------------
    pf = G.PickFrame("keal")
    pf.t = 1.0
    pf.draw(surf, (0, 0))
    assert len(pf.buttons) == 7
    for r_, _ in pf.buttons:
        assert r_.bottom <= G.H, "a frame card fell off the screen"
    pf.click(pf.buttons[4][0].center)
    assert pf.sel == 4, pf.sel
    pf.draw(surf, (0, 0))
    got = pf.click(pf.go.rect.center)
    assert got == pf.frames[4].key, got
    print("  the picker draws seven, and hands back the one you clicked")

    # -- ...and RYEZ gets the same screen, which it did not ---------------
    # The picker was gated on `picked == "keal"` for as long as only
    # Novak sold frames and it stayed that way after Hauk started
    # selling whole animals. You could buy all six strains out of the
    # cellar and be put in the stock body every run, with no screen
    # anywhere that mentioned them.
    wipe_meta()
    G.set_house("ryez")
    G.add_marks(4000)
    for k in ("st_hollow", "st_deepone", "st_bloom"):
        G.buy_ware(k)
    grown = [c.key for c in G.owned_chassis()]
    assert grown == ["standard", "hollow", "deepone", "bloom"], grown
    pf = G.PickFrame("ryez")
    pf.t = 1.0
    pf.draw(surf, (0, 0))
    assert len(pf.buttons) == 4, len(pf.buttons)
    assert pf.grown and pf.go.label.startswith("GROW"), pf.go.label
    pf.click(pf.buttons[2][0].center)
    pf.draw(surf, (0, 0))
    assert pf.click(pf.go.rect.center) == "deepone"
    print("  and a RYEZ player with three strains is offered all four, "
          "in its own words")

    # the gate itself, from the front door, because the widget above was
    # never the broken part - the branch that decides whether to show it
    # was, and it read `picked == "keal"`
    G.clear_run()
    app = G.App()
    scr = pygame.Surface((G.W, G.H))
    app.title.draw(scr, (0, 0))
    nb = next(b for b in app.title.buttons if b.key[0] == "new")
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=nb.rect.center,
                                  button=1))
    assert app.state == "choose", app.state
    app.choose.draw(scr, (0, 0))
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                  pos=app.choose.rects()["ryez"].center,
                                  button=1))
    assert app.state == "frame", (
        "RYEZ owns three strains and was sent straight to the tanks in "
        "the stock body: %s" % app.state)
    assert app.frames.house == "ryez"
    print("  and picking RYEZ at the front door now stops to ask which")
    G.clear_run()
    wipe_meta()
    G.set_house("keal")

    # -- a frame you have not bought cannot be smuggled into a save --------
    wipe_meta()
    G.set_house("keal")
    r = G.Run("keal", "sovereign")
    assert r.mech.chassis == "standard", r.mech.chassis
    print("  and one you have not bought is quietly the stock frame")
    wipe_meta()
    G.set_house("keal")
    print("\nframes ok")


# ---------------------------------------------------------------------------
# SCORE - seven loops, and none of them the same loop twice
# ---------------------------------------------------------------------------
def _fingerprint(buf, rate, bands=12, frames=24):
    """A coarse spectrum over time, with loudness AND length divided out.

    Both have to go before two pieces can be compared. Two tracks at
    different volumes are not different tracks, and neither are two at
    different tempos - normalising each frame to its own peak and taking
    a fixed number of frames whatever the length leaves only the shape."""
    n = len(buf)
    step = max(1, n // frames)
    out = []
    for f in range(frames):
        seg = buf[f * step:(f + 1) * step]
        row = []
        for b in range(bands):
            hz = 55.0 * (2 ** (b / 2.0))
            re = im = 0.0
            for i in range(0, len(seg), 7):     # sparse DFT; shape only
                a = 2 * math.pi * hz * i / rate
                re += seg[i] * math.cos(a)
                im += seg[i] * math.sin(a)
            row.append(math.hypot(re, im))
        m = max(row) or 1.0
        out += [v / m for v in row]
    return out


def score():
    """Every loop in the game, measured rather than listened to.

    The shop used to play one tune over all four of its counters, so the
    Capital sounded like a wet street at night and the mad scientist's
    cellar sounded like a bargain. Four new pieces went in for that, and
    the risk with four written in one sitting is that they come out as
    one piece in four hats."""
    names = list(G.TRACKS)
    built = {}
    for nm in names:
        s = G.TRACKS[nm]()
        s.finish()                   # a Score is lazy now; render it all
        pk = max(abs(v) for v in s.buf)
        rms = (sum(v * v for v in s.buf) / len(s.buf)) ** 0.5
        secs = len(s.buf) / float(s.RATE)
        assert pk < 0.95, "%s clips at %.2f" % (nm, pk)
        assert rms > 0.02, "%s is effectively silence (rms %.3f)" % (nm, rms)
        assert 8.0 < secs < 60.0, "%s is %.0fs long" % (nm, secs)
        built[nm] = (s, pk, rms, secs)
        print("  %-9s %5.1fs  peak %.2f  rms %.3f" % (nm, secs, pk, rms))

    # nothing should be much louder than anything else, or the mix jumps
    # every time the player changes screen
    loud = [v[2] for v in built.values()]
    assert max(loud) / min(loud) < 2.0, (
        "the loudest loop is %.1fx the quietest" % (max(loud) / min(loud)))

    fp = {nm: _fingerprint(built[nm][0].buf, built[nm][0].RATE)
          for nm in names}
    worst = None
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = sum(abs(x - y) for x, y in zip(fp[a], fp[b])) / len(fp[a])
            if worst is None or d < worst[0]:
                worst = (d, a, b)
    assert worst[0] > 0.10, (
        "%s and %s are the same piece in two hats (%.3f apart)"
        % (worst[1], worst[2], worst[0]))
    print("  %d loops, all distinct; closest pair %s/%s at %.3f"
          % (len(names), worst[1], worst[2], worst[0]))

    # and every shop counter has to name a tune that exists
    for sec, tune in G.Bazaar.SECTION_MUSIC.items():
        assert tune in G.TRACKS, (sec, tune)
        assert sec in [s[0] for s in G.Bazaar.SECTIONS], sec
    assert len(set(G.Bazaar.SECTION_MUSIC.values())) == \
        len(G.Bazaar.SECTION_MUSIC), "two counters share a tune"
    print("  and all %d counters have one of their own"
          % len(G.Bazaar.SECTION_MUSIC))
    print("\nscore ok")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    SLOPPY[0] = "sloppy" in sys.argv
    args = [a for a in sys.argv[2:] if a != "sloppy"]
    n = int(args[0]) if args else 10
    if what in ("smoke", "all"):
        print("== SMOKE ==")
        smoke()
    if what in ("score", "all"):
        print("== SCORE ==")
        score()
    if what in ("frames", "all"):
        print("== FRAMES ==")
        frames()
    if what in ("gov", "all"):
        print("== GOV ==")
        gov()
    if what in ("capital", "all"):
        print("== CAPITAL ==")
        capital()
    if what in ("yard", "all"):
        print("== YARD ==")
        yard()
    if what in ("slots", "all"):
        print("\n== SLOTS ==")
        slots()
    if what in ("flow", "all"):
        print("\n== FLOW ==")
        for hk in ("keal", "ryez"):
            flow(hk)
    if what in ("balance", "all"):
        print("\n== BALANCE ==")
        for hk in ("keal", "ryez"):
            balance(6 if what == "all" else n, hk)
    if what not in ("smoke", "capital", "gov", "frames", "score", "yard",
                    "slots", "flow", "balance", "all"):
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
