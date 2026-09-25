"""Harness for THE GREAT WORK. Nothing here ships; it is how the game is
measured.

    python gw_test.py smoke          draw every screen offscreen, save PNGs
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

Watch `taken` as much as `win%`. A fight the pilot wins without being hurt
is a fight with no texture in it, and three separate bugs hid behind a
healthy-looking win rate: the shell collision window was empty, the
LEVIATHAN's beam was cancelled in the wind-up eleven casts out of twelve,
and the broodlings spawned on the city side of the line.
"""
import os
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
    G.add_marks(400)
    for k in ("bp_rail", "warchest", "spec_shriek", "spec_shriek",
              "spec_venom"):
        G.buy_ware(k)
    for back, name in (("title", "hendras"), ("hangar", "hendras_mid")):
        bz = G.Bazaar(back)
        bz.t = 3.1
        bz.draw(surf, (300, 520))
        snap(name)

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
    ("r_wpn", "revolver"), ("reactor", 3), ("legs", 3), (YARD, 3),
    ("l_arm", 3), ("armour", 3), ("r_arm", 3), ("head", 3),
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
    ("r_wpn", "revolver"), ("legs", 3), (YARD, 3), ("l_arm", 3),
    ("armour", 3), ("r_arm", 3), ("head", 3),
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
    for socket, target in PRIORITY:
        if run.no_room() or (not run.bio and run.free_crew < 1):
            break
        p = _next_part(run, socket, target)
        if p is not None and run.can_afford(*run.price(p)):
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
    if (nxt is not None and nxt.alloy > run.alloy and run.alloy == 0
            and run.scrap >= G.REFINE.scrap + 700
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


def run_fight(run, kind):
    f = G.Fight(run, kind)
    d = {"n": 0, "locked": 0, "asked": 0, "stun": 0, "armed": 0, "legs": 0}
    while f.over is None and f.t < CAP:
        inp = pilot(f)
        m = f.mech
        d["n"] += 1
        d["armed"] += sum(1 for s in ("l", "r") if m.weapon(s))
        d["locked"] += 1 if m.locked else 0
        d["asked"] += 1 if (inp.get("fire_l") or inp.get("fire_r")) else 0
        d["stun"] += 1 if f.stun > 0 else 0
        d["legs"] += 1 if m.alive("legs") else 0
        f.update(DT, inp)
    f.timeout = f.over is None
    if f.timeout:
        f.over = "lost"
    f.diag = d
    return f


def campaign(seed, house_key="keal"):
    import random
    random.seed(seed)
    run = G.Run(house_key)
    report = []
    while run.next_landfall is not None:
        nl = run.next_landfall
        while run.day < nl:
            shop(run)
            run.end_day()
        kind = run.next_kind()
        before = dict(run.mech.fit)
        f = run_fight(run, kind)
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


def balance(n=10, house_key="keal"):
    wipe_meta()
    G.set_house(house_key)
    roster = G.roster_for(house_key)
    per = {k.name: [] for k in roster}
    endings = {}
    last = None
    for s in range(n):
        run, rep = campaign(1000 + s, house_key)
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
    print("-" * 66)
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
              " stun %2.0f%% legs %2.0f%%%s"
              % ("", mean(r["dealt"] / max(1, r["secs"]) for r in rows),
                 sum(x["armed"] for x in d) / tot,
                 100.0 * sum(x["asked"] for x in d) / tot,
                 100.0 * sum(x["locked"] for x in d) / tot,
                 100.0 * sum(x["stun"] for x in d) / tot,
                 100.0 * sum(x["legs"] for x in d) / tot,
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


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    if what in ("smoke", "all"):
        print("== SMOKE ==")
        smoke()
    if what in ("flow", "all"):
        print("\n== FLOW ==")
        for hk in ("keal", "ryez"):
            flow(hk)
    if what in ("balance", "all"):
        print("\n== BALANCE ==")
        for hk in ("keal", "ryez"):
            balance(6 if what == "all" else n, hk)
    if what not in ("smoke", "flow", "balance", "all"):
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
