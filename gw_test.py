"""Harness for THE GREAT WORK. Nothing here ships; it is how the game is
measured.

    python gw_test.py smoke          draw every screen offscreen, save PNGs
    python gw_test.py capital        the KEAL counters, and the house gate
    python gw_test.py gov            the state's desk, the calendar, the squad
    python gw_test.py frames         six whole machines and the rules they change
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
        # two handlers hold a pod steady; the rest go where it is worst
        for want in (2, 3):
            for j in sorted(pods, key=lambda j: (-j.unstable, j.left)):
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
    assert ryez.crew == 2, ryez.crew
    assert ryez.max_crew == G.MAX_CREW, ryez.max_crew
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
    run.crew, run.alloy = 2, 0
    for _ in range(4):
        run.capital_night()
    assert run.alloy == 2, "the furnace: %d in four nights" % run.alloy
    assert run.crew == 4, "the office: %d in four nights" % run.crew
    run.crew = G.RECRUIT_CAP
    for _ in range(6):
        run.capital_night()
    assert run.crew == G.RECRUIT_CAP, "the office went past its cap"
    print("  furnace 2 alloy / office 2 hands in four nights, capped at %d"
          % G.RECRUIT_CAP)

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
    assert len(gov_wares) == 15, len(gov_wares)
    assert all(w.house == "keal" for w in gov_wares)
    assert {w.key for w in gov_wares} == set(GOV_KEYS)

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
    print("  %d wares over two desks, %d marks" % (len(gov_wares),
                                                   sum(w.cost for w in
                                                       gov_wares)))

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
    print("  it lands on %.0f of %d, and the city takes %d%% of everything"
          % (f.boss().max_hp, kind.hp, round(f.city_mult * 100)))

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
        assert G.bought(k) and not G.has_ware(k), k
    ryez = G.Run("ryez")
    assert [ryez.landfall(i) for i in range(6)] == list(G.SCHEDULE)
    assert ryez.grace == 0 and ryez.scrap_mult == 1.0
    assert ryez.mech.hide_cut == 0.0
    print("  RYEZ owns all fifteen, keeps its own calendar and its own hide")

    # -- and the desk draws ------------------------------------------------
    G.set_house("keal")
    b = G.Bazaar()
    b.t = 2.0
    b.sec = 2
    b.draw(surf, (0, 0))
    assert len(b.slots) == 15, len(b.slots)
    for box, _ in b.slots:
        assert box.bottom <= G.H and box.right <= G.W, "a card fell off"
    b.click(b.slots[0][0].center)
    assert b.open == b.slots[0][1]
    b.draw(surf, (0, 0))
    b.open = None
    b.draw(surf, (0, 0))
    b.click(b.tab_rect(0).center)
    assert b.sec == 0, "the office would not let go"
    print("  the office draws, fifteen cards fit, and the tabs still move")
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
    assert len(G.CHASSIS_LIST) == 7, len(G.CHASSIS_LIST)
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
    for key in [c.key for c in G.CHASSIS_LIST]:
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

    # -- a frame you have not bought cannot be smuggled into a save --------
    wipe_meta()
    G.set_house("keal")
    r = G.Run("keal", "sovereign")
    assert r.mech.chassis == "standard", r.mech.chassis
    print("  and one you have not bought is quietly the stock frame")
    wipe_meta()
    G.set_house("keal")
    print("\nframes ok")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    SLOPPY[0] = "sloppy" in sys.argv
    args = [a for a in sys.argv[2:] if a != "sloppy"]
    n = int(args[0]) if args else 10
    if what in ("smoke", "all"):
        print("== SMOKE ==")
        smoke()
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
    if what not in ("smoke", "capital", "gov", "frames", "yard", "slots",
                    "flow", "balance", "all"):
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
