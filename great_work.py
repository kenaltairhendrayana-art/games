"""
THE GREAT WORK
==============
Build the mech. The kaiju will not wait.

A hangar sim wearing a monster movie. Most of this game is a calendar:
you have a half-finished thing standing in a bay, a crew who can only be
in so many places, and not enough money. You spend days working on it.
The days pass whether you spend them well or not, and on the days marked
in red something comes up the road.

Then you climb in, or let it off the leash, and find out what you made.

SIGN WITH ONE OF TWO COMPANIES, and the other one is the campaign.
  KEAL CO builds it out of steel. A gantry, a crew, a mech - and RYEZ
           grows things in tanks and lets them walk up the road at you.
  RYEZ CO grows it. A tank, handlers, an animal - and KEAL builds things
           out of ship plate and drives them up the road at you.
The two are the same nine sockets, the same calendar and the same six
roles in the opposing roster, because the joke is that the two companies
are the same company with a different smell. What changes is the body you
are making, the words for all of it, and everything you point it at.

Nothing ships beside this file. Two mechs, six kaiju, six machines, both
logos, the city they wade through, the thirteen sounds and the three
pieces of music are all drawn or synthesised here, out of code.

Requirements: pygame-ce (or pygame)  ->  pip install pygame-ce
Run:                                     python great_work.py

THE SHAPE OF IT
  Nine sockets - legs, torso, head, two arms, two hardpoints, a reactor
  and a suit of plate, or limbs, core mass, sense cluster, forelimbs,
  organs, a heart and a carapace, depending who signed you. Each one empty, or holding
  one of three tiers, or holding one of ten weapons. A job is worked by
  the crew you put on it and finishes when it finishes.

  Then two things that are not on the ladder. The RACK holds modules:
  thirteen of them, small, cheap and mostly a trade, and the torso
  decides how many bays you get - one, two, three. And THE YARD upgrades
  itself, which is the only thing in the game that buys you days rather
  than spending them.

  And one thing that outlives the run. Every body you put down pays
  MARKS, which are no use to a yard and no use to a hatchery, and THE
  HENDRAS will take them. Sarah draws - blueprints that put new weapons
  in your catalogue for good, and standing orders that start every run
  better off. Jack grows - specimens in jars you open mid-fight, and
  grafts that hold for good. None of it resets when a campaign does,
  which makes a run that ends badly still worth having played.

  THE TWO HOUSES WORK DIFFERENTLY. KEAL welds: put more crew on a job and
  it lands sooner, because steel does what it is told. RYEZ splices and
  waits - a culture in a pod takes half as long again and NO number of
  handlers makes it faster. What handlers buy there is stability: an
  unwatched pod drifts, and past the line it expresses wrong and the organ
  grafts on at 62% of what it should have been. FORCING a pod open early
  is flawed by definition. So KEAL runs few things quickly and RYEZ runs
  five, six, seven at once and can never watch them all.

  Six landfalls on a fixed calendar. Kill the thing and you harvest it:
  scrap for the yard, ALLOY for the parts money cannot buy, and one more
  pair of hands. Let it past and the city pays, in a number that never
  goes back up.

  The mech comes apart while you fight. A leg that dies stays dead until
  somebody fixes it, and fixing it costs days you were going to spend on
  the shoulder cannon.

CONTROLS
  Hangar
    click           a socket to open it, a part to queue it
    1 .. 9          the same nine sockets from the keyboard
    0               the module rack, all thirteen at once
    Y               the yard's own upgrades
    + / -           put another crew on the selected job, or take one off
    R               rush the selected job - it finishes tonight, at double
    SPACE / ENTER   end the day
    TAB             the spec sheet - what the build adds up to
  Fight
    A D / arrows    walk
    J / left click  fire the left hardpoint
    K / right click fire the right hardpoint
    S / down        brace - halves what gets through, but you cannot act
    SPACE           boost (piston striders only)
    V               dump the coolant (with the flush module, once a fight)
    1 2 3           open one of Jack's jars, if you are carrying one
  Any time
    P               pause
    M               mute - the music goes with it
    F               speed 1x / 2x / 3x
    ESC             back out one screen
  The stall
    click           a ware to buy it; ESC or SPACE leaves
  Everywhere        the mouse does all of it too
"""

import json
import math
import os
import random
import sys
from array import array

import pygame
from pygame import Vector2

TAU = math.tau


# ---------------------------------------------------------------------------
# THE WINDOW
#
# One size, two screens. The hangar owns the whole window; the fight owns
# the whole window and puts its own HUD on top. Nothing is drawn outside
# these bounds and nothing assumes a resolution but this one.
# ---------------------------------------------------------------------------
W, H = 1180, 760
FPS = 60

# The fight runs in a strip of world much wider than the window, and the
# camera slides along it. x=0 is the city wall; x=WORLD_W is the sea.
WORLD_W = 3200
GROUND_Y = 596                      # screen y of the ground line in a fight

BG       = (12, 13, 18)
PANEL    = (20, 22, 30)
PANEL_HI = (29, 32, 44)
LINE     = (52, 58, 76)
INK      = (226, 231, 243)
DIM      = (134, 143, 166)
FAINT    = (78, 85, 105)

STEEL    = (126, 136, 158)          # the mech, unpainted
STEEL_D  = (74, 82, 100)
STEEL_L  = (176, 186, 208)
PAINT    = (196, 142, 48)           # the yard's yellow
PAINT_D  = (126, 88, 24)
CORE     = (108, 214, 236)          # reactor light

RUST     = (196, 92, 58)
GOOD     = (104, 206, 128)
WARN     = (232, 182, 62)
BAD      = (224, 78, 78)
ALLOY_C  = (170, 132, 226)
GHOST    = (58, 64, 84)             # an empty socket's dashed outline


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def unit(v, fallback=(1, 0)):
    L = v.length()
    return v / L if L > 1e-6 else Vector2(fallback)


def approach(v, target, step):
    """Move v toward target by at most step. Every bar in the UI uses it."""
    if v < target:
        return min(target, v + step)
    return max(target, v - step)


_fonts = {}


def font(size, bold=True):
    key = (size, bold)
    f = _fonts.get(key)
    if f is None:
        path = pygame.font.match_font("consolas,couriernew,dejavusansmono,arial")
        f = pygame.font.Font(path, size) if path else pygame.font.SysFont(None, size)
        f.set_bold(bold)
        _fonts[key] = f
    return f


def text(surf, s, size, pos, colour, center=False, right=False, left=False,
         shadow=True, bold=True, alpha=255):
    f = font(size, bold)
    img = f.render(s, True, colour)
    if alpha < 255:
        img.set_alpha(alpha)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.midright = pos
    elif left:
        r.midleft = pos
    else:
        r.topleft = pos
    if shadow:
        sh = f.render(s, True, (0, 0, 0))
        sh.set_alpha(alpha if alpha < 255 else 140)
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


def fit(label, size, width, bold=True):
    """The largest size up to `size` whose label fits inside `width`.

    A label that overruns its own button only ever shows up in a
    screenshot, so this makes it impossible instead of something to
    remember."""
    while size > 9 and font(size, bold).size(label)[0] > width:
        size -= 1
    return size


_glows = {}


def glow(radius, colour, strength=100):
    """A soft additive disc, cached - every light in the game is one.

    The falloff is baked into the COLOUR, not the alpha. BLEND_ADD ignores
    the source alpha completely, so a surface that fades out by alpha adds
    at full strength everywhere and every light in the game comes out as a
    hard saturated disc. Premultiplying is the whole fix."""
    key = (radius, colour, strength)
    s = _glows.get(key)
    if s is None:
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = max(8, radius // 2)
        for i in range(steps, 0, -1):
            f = i / steps
            k = (strength / 255.0) * (1.0 - f) ** 2.2
            pygame.draw.circle(s, (int(colour[0] * k), int(colour[1] * k),
                                   int(colour[2] * k), 255),
                               (radius, radius), int(radius * f))
        _glows[key] = s
    return s


def blit_glow(surf, pos, radius, colour, strength=100):
    radius = max(2, int(radius))
    g = glow(radius, colour, strength)
    surf.blit(g, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_ADD)


def shade(c, f):
    """Lighten (f>1) or darken (f<1) without leaving the byte range."""
    return (int(clamp(c[0] * f, 0, 255)),
            int(clamp(c[1] * f, 0, 255)),
            int(clamp(c[2] * f, 0, 255)))


def mix(a, b, t):
    return (int(lerp(a[0], b[0], t)), int(lerp(a[1], b[1], t)),
            int(lerp(a[2], b[2], t)))


def panel(surf, rect, fill=PANEL, edge=LINE, radius=6, width=1):
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    if width:
        pygame.draw.rect(surf, edge, rect, width, border_radius=radius)


def bar(surf, rect, frac, colour, back=(30, 33, 44), edge=None):
    pygame.draw.rect(surf, back, rect, border_radius=3)
    f = clamp(frac, 0.0, 1.0)
    if f > 0:
        inner = pygame.Rect(rect.x, rect.y, max(2, int(rect.w * f)), rect.h)
        pygame.draw.rect(surf, colour, inner, border_radius=3)
    if edge:
        pygame.draw.rect(surf, edge, rect, 1, border_radius=3)


def dashed_poly(surf, pts, colour, width=2, dash=7, gap=6, closed=True):
    """An empty socket is drawn as a dashed ghost of the part that goes
    there, so the machine always shows its own whole silhouette - what is
    missing is as legible as what is bolted on."""
    if len(pts) < 2:
        return
    seq = list(pts) + ([pts[0]] if closed else [])
    carry, on = 0.0, True
    for i in range(len(seq) - 1):
        a, b = Vector2(seq[i]), Vector2(seq[i + 1])
        seg = (b - a).length()
        if seg < 0.01:
            continue
        d = unit(b - a)
        t = 0.0
        while t < seg:
            want = (dash if on else gap) - carry
            step = min(want, seg - t)
            if on and step > 0.4:
                pygame.draw.line(surf, colour, a + d * t, a + d * (t + step), width)
            t += step
            carry += step
            if carry >= (dash if on else gap) - 1e-6:
                carry, on = 0.0, not on


class Button:
    """Rect plus label plus a hover glow. The whole UI is made of these."""

    def __init__(self, rect, label, key=None, enabled=True, tone=None,
                 primary=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.key = key
        self.enabled = enabled
        self.tone = tone or PAINT
        self.primary = primary      # the one thing the screen is asking for
        self.hot = False

    def hover(self, mouse):
        self.hot = self.enabled and self.rect.collidepoint(mouse)
        return self.hot

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surf, size=20):
        r = self.rect
        if not self.enabled:
            panel(surf, r, (22, 24, 32), (44, 48, 62), 5)
            text(surf, self.label, fit(self.label, size, r.w - 16), r.center,
                 FAINT, center=True)
            return
        if self.primary:
            panel(surf, r, shade(self.tone, 0.34 if not self.hot else 0.46),
                  self.tone, 5, 2)
            blit_glow(surf, r.center, r.h, self.tone, 30 if self.hot else 16)
            text(surf, self.label, fit(self.label, size, r.w - 16), r.center,
                 (255, 244, 224), center=True)
            return
        panel(surf, r, PANEL_HI if self.hot else PANEL,
              self.tone if self.hot else LINE, 5)
        if self.hot:
            blit_glow(surf, r.center, r.h, self.tone, 26)
        text(surf, self.label, fit(self.label, size, r.w - 16), r.center,
             INK if self.hot else (196, 203, 220), center=True)



# ---------------------------------------------------------------------------
# THE TWO HOUSES
#
# KEAL CO builds it out of steel. RYEZ CO grows it. They have been at each
# other over the same waterfront for eleven years, and the city is what is
# standing between them.
#
# Whichever one you sign with, the other one's product walks up the road at
# you on the days marked in red. The two campaigns are the same shape by
# design - the same nine sockets, the same calendar, the same six roles in
# the opposing roster - because the point is that the two companies are the
# same company with a different smell.
#
# Everything a house renames lives in WORDS below. Nothing else in the game
# knows there is more than one of them: the catalogue, the fight and the
# save file are all house-blind, and the labels are looked up at the moment
# they are drawn.
# ---------------------------------------------------------------------------
KEAL_STEEL = (126, 136, 158)
KEAL_GOLD = (196, 142, 48)
RYEZ_FLESH = (150, 96, 156)
RYEZ_ACID = (154, 200, 78)


def draw_keal_logo(surf, cx, cy, r, t=0.0, alive=True):
    """A bolt head with a girder K through it. Six rivets, no curves."""
    hexa = [(cx + r * math.cos(a), cy + r * math.sin(a))
            for a in (i * TAU / 6 - math.pi / 2 for i in range(6))]
    inner = [(cx + r * 0.80 * math.cos(a), cy + r * 0.80 * math.sin(a))
             for a in (i * TAU / 6 - math.pi / 2 for i in range(6))]
    pygame.draw.polygon(surf, (30, 33, 42), hexa)
    pygame.draw.polygon(surf, KEAL_STEEL if alive else (70, 74, 86), hexa,
                        max(2, int(r * 0.09)))
    pygame.draw.polygon(surf, shade(KEAL_STEEL, 0.62), inner,
                        max(1, int(r * 0.04)))
    for i in range(6):
        a = i * TAU / 6 - math.pi / 2 + TAU / 12
        p = (cx + r * 0.9 * math.cos(a), cy + r * 0.9 * math.sin(a))
        pygame.draw.circle(surf, shade(KEAL_STEEL, 0.8), p,
                           max(1.5, r * 0.055))
    # the K: an upright girder and two struts, all cut square
    gold = KEAL_GOLD if alive else (96, 84, 56)
    w = r * 0.155
    up = [(cx - r * 0.44, cy - r * 0.50), (cx - r * 0.44 + w * 2, cy - r * 0.50),
          (cx - r * 0.44 + w * 2, cy + r * 0.50), (cx - r * 0.44, cy + r * 0.50)]
    pygame.draw.polygon(surf, gold, up)
    arm_u = [(cx - r * 0.10, cy - r * 0.04), (cx + r * 0.40, cy - r * 0.52),
             (cx + r * 0.40 + w * 1.5, cy - r * 0.30),
             (cx - r * 0.10 + w * 1.4, cy + r * 0.14)]
    arm_d = [(cx - r * 0.10, cy - r * 0.02), (cx + r * 0.40, cy + r * 0.50),
             (cx + r * 0.40 - w * 1.5, cy + r * 0.52),
             (cx - r * 0.12 - w * 0.2, cy + r * 0.16)]
    pygame.draw.polygon(surf, gold, arm_u)
    pygame.draw.polygon(surf, shade(gold, 0.78), arm_d)
    if alive:
        # a weld line crawling round the rim, because it is a fabrication mark
        a = (t * 0.8) % TAU
        p = (cx + r * 0.88 * math.cos(a), cy + r * 0.88 * math.sin(a))
        blit_glow(surf, p, r * 0.22, (255, 226, 170), 120)


def draw_ryez_logo(surf, cx, cy, r, t=0.0, alive=True):
    """A cell wall with a twist of strand inside it. No straight lines."""
    lobes = []
    for i in range(48):
        a = i * TAU / 48
        wob = 1.0 + 0.040 * math.sin(a * 5 + t * 0.7)
        lobes.append((cx + r * wob * math.cos(a), cy + r * wob * math.sin(a)))
    flesh = RYEZ_FLESH if alive else (74, 62, 78)
    acid = RYEZ_ACID if alive else (86, 96, 66)
    pygame.draw.polygon(surf, (26, 22, 32), lobes)
    pygame.draw.polygon(surf, flesh, lobes, max(2, int(r * 0.085)))
    pygame.draw.polygon(surf, shade(flesh, 0.62),
                        [(cx + r * 0.80 * math.cos(i * TAU / 32),
                          cy + r * 0.80 * math.sin(i * TAU / 32))
                         for i in range(32)], max(1, int(r * 0.035)))
    # two strands that cross twice and part at the top, which reads as a Y
    n = 22
    left, right = [], []
    for i in range(n + 1):
        f = i / n
        y = cy + r * (0.62 - 1.24 * f)
        spread = r * 0.38 * (0.32 + 0.68 * f)
        phase = f * math.pi * 1.6 + math.sin(t * 0.9) * 0.18
        left.append((cx - spread * math.cos(phase), y))
        right.append((cx + spread * math.cos(phase), y))
    for i in range(0, n, 3):                    # the base pairs
        pygame.draw.line(surf, shade(acid, 0.7), left[i], right[i],
                         max(1, int(r * 0.035)))
    pygame.draw.lines(surf, acid, False, left, max(2, int(r * 0.095)))
    pygame.draw.lines(surf, shade(acid, 0.75), False, right,
                      max(2, int(r * 0.095)))
    pygame.draw.circle(surf, flesh, (cx, cy + r * 0.66), max(2, r * 0.13))
    if alive:
        pygame.draw.circle(surf, mix(acid, (255, 255, 255), 0.4),
                           (cx, cy + r * 0.66), max(1, r * 0.055))
        blit_glow(surf, (cx, cy + r * 0.66), r * 0.40, acid, 70)


class House:
    __slots__ = ("key", "name", "tagline", "pitch", "colour", "dark", "logo",
                 "body", "words", "roster", "verb")

    def __init__(self, key, name, tagline, pitch, colour, logo, body, verb,
                 roster, words):
        self.key = key
        self.name = name
        self.tagline = tagline
        self.pitch = pitch
        self.colour = colour
        self.dark = shade(colour, 0.5)
        self.logo = logo
        self.body = body            # "mech" or "bio" - which art to draw
        self.verb = verb            # what a finished job is called
        self.roster = roster        # the name of the OTHER house's roster
        self.words = words


# Everything either house renames. A key that is missing falls through to
# the KEAL wording, which is the default the rest of the file is written in.
RYEZ_WORDS = {
    "scrap": "BIOMASS", "alloy": "GENOME", "crew": "HANDLERS",
    "built": "GROWN", "heat": "STRAIN", "overheat": "SEIZING - COOLING",
    "yard": "THE HATCHERY", "rack": "GENE RACK", "machine": "THE ANIMAL",
    "sockets": "ORGANS", "deploy": "RELEASE", "fitted": "GROWN",
    "the_yard_place": "the hatchery", "gantry": "THE TANK",
    "bays": "GENE SITES", "repair": "MEND", "rushed": "FORCED OPEN",
    "spent": "BIOMASS SPENT", "scrapped": "REABSORBED - HALF BACK",
    "wrecked": "DEAD", "empty": "BARE",
}

# Socket labels, per house.
RYEZ_SOCKETS = {
    "legs": "LIMBS", "torso": "CORE MASS", "head": "SENSE CLUSTER",
    "l_arm": "LEFT FORELIMB", "r_arm": "RIGHT FORELIMB",
    "l_wpn": "LEFT ORGAN", "r_wpn": "RIGHT ORGAN",
    "reactor": "HEART", "armour": "CARAPACE",
}

# the fight HUD is narrower than the yard's, so it gets its own short set
RYEZ_HUD = {"legs": "LIMBS", "torso": "CORE", "head": "SENSE",
            "l_arm": "L LIMB", "r_arm": "R LIMB", "l_wpn": "L ORGAN",
            "r_wpn": "R ORGAN", "reactor": "HEART", "armour": "SHELL"}

# Part and weapon names, keyed by (socket, tier-or-weapon-key). Same stats,
# same costs, same everything - a different thing to call it.
RYEZ_PARTS = {
    ("legs", 1): "SPLAYED LIMBS", ("legs", 2): "TENDON LIMBS",
    ("legs", 3): "SPRUNG HAUNCHES",
    ("torso", 1): "BARE SKELETON", ("torso", 2): "MUSCLED TRUNK",
    ("torso", 3): "LAYERED VISCERA",
    ("head", 1): "EYE CLUSTER", ("head", 2): "CROWNED SKULL",
    ("head", 3): "PREDATOR SIGHT",
    ("l_arm", 1): "GRAFTED FORELIMB", ("l_arm", 2): "CORDED FORELIMB",
    ("l_arm", 3): "BREAKER FORELIMB",
    ("r_arm", 1): "GRAFTED FORELIMB", ("r_arm", 2): "CORDED FORELIMB",
    ("r_arm", 3): "BREAKER FORELIMB",
    ("reactor", 1): "SLOW HEART", ("reactor", 2): "TWIN HEART",
    ("reactor", 3): "FURNACE HEART",
    ("armour", 1): "SCALE HIDE", ("armour", 2): "PLATED CHITIN",
    ("armour", 3): "LIVING CARAPACE",
    ("wpn", "fist"): "HAMMER CLAW", ("wpn", "pile"): "PISTON CLAW",
    ("wpn", "saw"): "RASP TONGUE", ("wpn", "ripper"): "TWIN RASP",
    ("wpn", "auto"): "SPINE VOLLEY", ("wpn", "revolver"): "QUILL BATTERY",
    ("wpn", "missile"): "SPORE PODS", ("wpn", "swarm"): "SPORE BLOOM",
    ("wpn", "lance"): "BILE JET", ("wpn", "sun"): "SOLVENT JET",
}

RYEZ_MODULES = {
    "autoloader": "FAST TWITCH", "sinks": "GILL VENTS",
    "shutters": "SHELL FOLDS", "gyro": "DEEP BALLAST",
    "claws": "FEEDING CLAWS", "redundant": "SECOND NERVE",
    "flush": "COLD BLOOD", "link": "DEPTH EYES", "shock": "STING HIDE",
    "stride": "SPRUNG TENDONS", "hoist": "EXTRA SAC",
    "baffles": "SUNKEN HEART", "spotter": "OUTRIDER",
}

RYEZ_YARD = {1: "SECOND TANK", 2: "NIGHT FEED", 3: "GENE VATS"}

# The current house, for labels only. Everything that MATTERS is on the Run;
# this exists so that forty draw calls do not each have to be handed one.
CURRENT = {"house": "keal"}


def house():
    return HOUSES[CURRENT["house"]]


def set_house(key):
    CURRENT["house"] = key if key in HOUSES else "keal"


def word(key, default=None):
    """A label, in the wording of whichever house is signed."""
    w = HOUSES[CURRENT["house"]].words
    return w.get(key, default if default is not None else key.upper())


def sock_label(socket):
    if CURRENT["house"] == "ryez":
        return RYEZ_SOCKETS.get(socket, SOCKET_LABEL.get(socket, socket))
    return SOCKET_LABEL.get(socket, socket)


def pname(socket, part):
    """What this house calls that part. Same part either way."""
    if part is None:
        return "?"
    if CURRENT["house"] != "ryez":
        return part.name
    if isinstance(part, Weapon):
        return RYEZ_PARTS.get(("wpn", part.key), part.name)
    if isinstance(part, Module):
        return RYEZ_MODULES.get(part.key, part.name)
    if isinstance(part, Refine):
        return REFINE_RYEZ_NAME
    if isinstance(part, YardUp):
        return RYEZ_YARD.get(part.tier, part.name)
    return RYEZ_PARTS.get((part.socket, part.tier), part.name)


# The flavour, which is where the reskin would show if it were one. Same
# statistics, same costs, a different thing entirely to be told about.
RYEZ_BLURB = {
    ("legs", 1): "Four points of contact and no grace at all. It walks.",
    ("legs", 2): "Proper tendon under the hide. Four strides to the river.",
    ("legs", 3): "It stores the jump in the haunch. That is the boost.",
    ("torso", 1): "The skeleton that set last winter. Ribs, not hide.",
    ("torso", 2): "Wrapped in sheet muscle. Doubles what it survives.",
    ("torso", 3): "Organs doubled and packed deep. Built to be hit.",
    ("head", 1): "Six eyes and a pit organ. It can see what it is biting.",
    ("head", 2): "Hears a hydraulic line tense half a second before it fires.",
    ("head", 3): "Finds the weld in the plate and puts everything through it.",
    ("l_arm", 1): "Bone, joint, and a site for whatever we grow on it.",
    ("l_arm", 2): "Corded muscle. Everything on the end of it cycles faster.",
    ("l_arm", 3): "A shoulder that throws the whole animal behind the hand.",
    ("r_arm", 1): "Bone, joint, and a site for whatever we grow on it.",
    ("r_arm", 2): "Corded muscle. Everything on the end of it cycles faster.",
    ("r_arm", 3): "A shoulder that throws the whole animal behind the hand.",
    ("reactor", 1): "One chamber, and it tires. Good for about a minute.",
    ("reactor", 2): "Two chambers out of phase. The organs stop being the limit.",
    ("reactor", 3): "It runs hot enough to scald. Nobody handles it awake.",
    ("armour", 1): "Overlapping scale. Takes the edge off everything.",
    ("armour", 2): "Chitin over a crush layer. Spends itself to save the trunk.",
    ("armour", 3): "It grows back between landfalls. Slowly, and it hurts.",
    ("wpn", "fist"): "A fused claw on a wrist. Cheap to grow and it never jams.",
    ("wpn", "pile"): "The same claw with a tendon spring behind it.",
    ("wpn", "saw"): "Held against plate it does terrible work. You must hold it.",
    ("wpn", "ripper"): "Two rasps counter-turning. Nothing comes off it whole.",
    ("wpn", "auto"): "Fires its own bone and grows it back. The honest answer.",
    ("wpn", "revolver"): "Four rows on a turning cuff. Runs hot, does not care.",
    ("wpn", "missile"): "Four at a time, and they burst where they land.",
    ("wpn", "swarm"): "Six sacs and a faster refill. Clears a street.",
    ("wpn", "lance"): "Billed by the second. Bring a heart or do not bring this.",
    ("wpn", "sun"): "Goes through the first one and into what is behind it.",
}

RYEZ_MOD_BLURB = {
    "autoloader": "Twitch fibre laid through the firing organs.",
    "sinks": "Gills down the back. You shed faster and you hold less.",
    "shutters": "Folds that drop over the seams. Bracing becomes a plan.",
    "gyro": "It will not go over, and it will not be hurried either.",
    "claws": "You are standing on a very great deal of protein.",
    "redundant": "Two of every nerve, routed the long way round.",
    "flush": "One flush of cold, and then you have used your cold.",
    "link": "It watches where the last one went and corrects.",
    "shock": "Charged hide. It does not stop the blow, it bills for it.",
    "stride": "The difference between reaching it and watching it go past.",
    "hoist": "Only worth the site if there is a pod cluster on the arm.",
    "baffles": "The one organ you cannot fight without, moved deep.",
    "spotter": "A small one that rides above the fight and tells you.",
}

RYEZ_MOD_EFFECT = {
    "autoloader": "organs cycle 20% faster, and run 16% hotter",
    "link": "+14% from anything it spits, fires or sprays",
    "baffles": "the heart cannot be hit; the trunk takes it instead",
    "hoist": "a pod cluster throws one more",
    "flush": "V dumps the whole heat load - once per landfall",
    "sinks": "shedding +30%, ceiling -14%",
}

RYEZ_YARD_BLURB = {
    1: "There is room along the wall for one more vat.",
    2: "The lights stay on. Nobody asked the neighbours.",
    3: "We stopped selling the culture and started growing it.",
}


def pblurb(socket, part):
    """The sentence under a part, in this house's voice."""
    if part is None:
        return ""
    if CURRENT["house"] != "ryez":
        return part.blurb
    if isinstance(part, Weapon):
        return RYEZ_BLURB.get(("wpn", part.key), part.blurb)
    if isinstance(part, Module):
        return RYEZ_MOD_BLURB.get(part.key, part.blurb)
    if isinstance(part, Refine):
        return REFINE_RYEZ_BLURB
    if isinstance(part, YardUp):
        return RYEZ_YARD_BLURB.get(part.tier, part.blurb)
    return RYEZ_BLURB.get((part.socket, part.tier), part.blurb)


def peffect(part):
    """The line of numbers under a module, in this house's units."""
    if CURRENT["house"] == "ryez":
        if isinstance(part, Module):
            return RYEZ_MOD_EFFECT.get(part.key, part.effect)
        if isinstance(part, Refine):
            return REFINE_RYEZ_EFFECT
    return part.effect

HOUSES = {
    "keal": House(
        "keal", "KEAL CO",
        "we build it out of steel",
        "A gantry, a crew, and a half-finished machine. Put more hands on "
        "a job and it lands sooner - steel does what it is told. RYEZ grows "
        "things in tanks and lets them walk up the road at us.",
        KEAL_GOLD, draw_keal_logo, "mech", "FITTED", "bio", {}),
    "ryez": House(
        "ryez", "RYEZ CO",
        "we grow it",
        "Pods, handlers, and a half-grown animal. A culture takes the days "
        "it takes and no crowd makes it faster - handlers only stop it "
        "expressing wrong. KEAL drives ship plate up the road at us.",
        RYEZ_FLESH, draw_ryez_logo, "bio", "GROWN", "mech", RYEZ_WORDS),
}


# ---------------------------------------------------------------------------
# WHERE PROGRESS GOES
#
# Never beside the game, which may be read-only and is certainly somewhere
# a player does not look. One file, two things in it: the run in progress
# and what has been finished before.
# ---------------------------------------------------------------------------
def _save_dir():
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(root, "TheGreatWork")
    elif sys.platform == "darwin":
        d = os.path.expanduser("~/Library/Application Support/TheGreatWork")
    else:
        root = (os.environ.get("XDG_DATA_HOME")
                or os.path.expanduser("~/.local/share"))
        d = os.path.join(root, "the-great-work")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except OSError:
        return os.path.dirname(os.path.abspath(__file__))


SAVE_NAME = "progress.json"


def load_save():
    try:
        with open(os.path.join(_save_dir(), SAVE_NAME), encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError, TypeError):
        return {}


def write_save(data):
    try:
        with open(os.path.join(_save_dir(), SAVE_NAME), "w",
                  encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# THE HENDRAS
#
# Two dealers who do not work for either company and will sell to both.
# Sarah draws; Jack grows. What they take is MARKS - what the city pays you
# for a body, which is no use to a yard and no use to a hatchery and is
# exactly the sort of thing a Hendra will take.
#
# Everything bought here is PERMANENT and lives in the save file next to
# the run, not in it. A campaign that ends badly still leaves you holding
# what you bought, which is the whole point of the stall: it is the only
# part of the game that does not reset.
# ---------------------------------------------------------------------------
class Ware:
    __slots__ = ("key", "seller", "name", "cost", "kind", "effect", "blurb")

    def __init__(self, key, seller, name, cost, kind, effect, blurb):
        self.key = key
        self.seller = seller        # "sarah" or "jack"
        self.name = name
        self.cost = cost
        self.kind = kind            # "blueprint", "power" or "specimen"
        self.effect = effect
        self.blurb = blurb


WARE_LIST = [
    # -- Sarah: the drawing office ------------------------------------------
    Ware("bp_rail", "sarah", "RAIL LANCE", 120, "blueprint",
         "a hardpoint gun that ignores hide entirely",
         "She drew it in an afternoon and spent a year on the rails."),
    Ware("bp_hook", "sarah", "GRAVE HOOK", 110, "blueprint",
         "melee that drags what it hits back into reach",
         "For the ones that would rather be somewhere else."),
    Ware("warchest", "sarah", "WAR CHEST", 70, "power",
         "every run starts with 200 more in the bank",
         "She knows somebody. She always knows somebody."),
    Ware("earlyshift", "sarah", "EARLY SHIFT", 90, "power",
         "every run starts with a third pair of hands",
         "Signed on before you got there and already working."),
    Ware("sharptools", "sarah", "SHARP TOOLS", 80, "power",
         "mending costs 30% less, for good",
         "A proper set, indexed, and nobody is allowed to borrow them."),
    # -- Jack: the menagerie ------------------------------------------------
    Ware("spec_shriek", "jack", "SHRIEKER", 35, "specimen",
         "one jar: staggers whatever is in front of you",
         "Do not open it indoors. He is not joking about that."),
    Ware("spec_leech", "jack", "LEECH BLOOM", 40, "specimen",
         "one jar: mends the worst-hurt part by a third, mid-fight",
         "It eats the damage. Nobody has asked what it does afterwards."),
    Ware("spec_venom", "jack", "VENOM SAC", 45, "specimen",
         "one jar: ten seconds where nothing's hide counts",
         "Green, and it moves on its own when the lid is off."),
    Ware("thickblood", "jack", "THICK BLOOD", 100, "power",
         "every part carries 12% more, for good",
         "A graft that takes on steel as happily as on meat."),
    Ware("quicknerve", "jack", "QUICK NERVE", 85, "power",
         "10% faster on its feet, for good",
         "Shorter path from deciding to moving. That is all it is."),
    Ware("deepgut", "jack", "DEEP GUT", 130, "power",
         "one more bay in the rack, for good",
         "Room made where there was not room. Do not ask for what."),
]
WARES = {w.key: w for w in WARE_LIST}
SPECIMENS = [w for w in WARE_LIST if w.kind == "specimen"]

RYEZ_WARE_NAME = {"bp_rail": "BARB LAUNCHER", "bp_hook": "TONGUE HOOK",
                  "warchest": "FULL LARDER", "earlyshift": "EARLY SHIFT",
                  "sharptools": "CLEAN HANDS", "thickblood": "THICK BLOOD",
                  "quicknerve": "QUICK NERVE", "deepgut": "DEEP GUT"}

# what a body is worth to the city, by which landfall it was
MARKS_FOR = (14, 20, 28, 36, 46, 60)


# -- the ledger -------------------------------------------------------------
# Cached, because `has_ware` is asked inside draw loops and a disk read per
# call would be felt. Every write goes through _meta_put, which re-reads the
# whole save first so it can never clobber the run sitting beside it.
_META = [None]


def meta():
    if _META[0] is None:
        m = (load_save().get("meta") or {})
        _META[0] = {
            "marks": max(0, int(m.get("marks", 0) or 0)),
            "owned": [k for k in (m.get("owned") or []) if k in WARES],
            "stock": {k: max(0, int(v)) for k, v in
                      (m.get("stock") or {}).items()
                      if k in WARES and int(v) > 0},
            "spent": max(0, int(m.get("spent", 0) or 0)),
        }
    return _META[0]


def _meta_put(m):
    _META[0] = m
    data = load_save()
    data["meta"] = m
    write_save(data)


def meta_forget():
    """Drop the cache - the tests point _save_dir somewhere else."""
    _META[0] = None


def marks():
    return meta()["marks"]


def add_marks(n):
    m = dict(meta())
    m["marks"] = max(0, m["marks"] + int(n))
    _meta_put(m)


def has_ware(key):
    return key in meta()["owned"]


def stock_of(key):
    return meta()["stock"].get(key, 0)


def can_buy(key):
    w = WARES.get(key)
    if w is None:
        return False
    if w.kind != "specimen" and has_ware(key):
        return False               # a blueprint is bought once
    return marks() >= w.cost


def buy_ware(key):
    if not can_buy(key):
        return False
    w = WARES[key]
    m = dict(meta())
    m["marks"] -= w.cost
    m["spent"] = m.get("spent", 0) + w.cost
    if w.kind == "specimen":
        st = dict(m["stock"])
        st[key] = st.get(key, 0) + 1
        m["stock"] = st
    else:
        m["owned"] = list(m["owned"]) + [key]
    _meta_put(m)
    return True


def use_specimen(key):
    """Take one out of the cupboard. Jars do not come back."""
    if stock_of(key) <= 0:
        return False
    m = dict(meta())
    st = dict(m["stock"])
    st[key] = st[key] - 1
    if st[key] <= 0:
        del st[key]
    m["stock"] = st
    _meta_put(m)
    return True


def ware_name(w):
    if CURRENT["house"] == "ryez":
        return RYEZ_WARE_NAME.get(w.key, w.name)
    return w.name

# ---------------------------------------------------------------------------
# NOISE
#
# Nothing ships beside this file, so every sound is a few thousand samples
# built at start-up. A machine with no audio device gets silence and never
# hears about it.
# ---------------------------------------------------------------------------
class Sfx:
    RATE = 22050

    def __init__(self):
        self.ok = False
        self.muted = False
        self.bank = {}
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=1,
                              buffer=512)
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            return
        try:
            self.bank = {
                # the yard
                "click":  self._mk(700, 38, "sine", 0.14, 0.0),
                "weld":   self._mk(260, 220, "noise", 0.13, 1.2),
                "rivet":  self._mk(1100, 60, "square", 0.16, -0.5),
                "done":   self._mk(430, 300, "sine", 0.20, 1.1),
                "horn":   self._mk(150, 700, "saw", 0.20, -0.12),
                "deny":   self._mk(160, 140, "square", 0.16, -0.5),
                # the fight
                "cannon": self._mk(190, 130, "noise", 0.28, -0.6),
                "thud":   self._mk(95, 150, "sine", 0.30, -0.5),
                "hit":    self._mk(320, 80, "noise", 0.22, -0.4),
                "beam":   self._mk(620, 260, "saw", 0.18, 0.25),
                "roar":   self._mk(74, 900, "saw", 0.34, -0.25),
                "wreck":  self._mk(120, 520, "noise", 0.30, -0.7),
                "alarm":  self._mk(560, 420, "square", 0.17, 0.5),
            }
            self.ok = True
        except (pygame.error, MemoryError):
            self.ok = False

    def _mk(self, freq, ms, kind="sine", vol=0.25, bend=0.0):
        n = int(self.RATE * ms / 1000)
        buf = array("h")
        phase = 0.0
        for i in range(n):
            f = i / n
            hz = freq * (1.0 + bend * f)
            phase += TAU * hz / self.RATE
            if kind == "noise":
                v = random.uniform(-1.0, 1.0)
            elif kind == "saw":
                v = ((phase / TAU) % 1.0) * 2.0 - 1.0
            elif kind == "square":
                v = 1.0 if math.sin(phase) >= 0 else -1.0
            else:
                v = math.sin(phase)
            env = (1.0 - f) ** 2.0
            buf.append(int(clamp(v * env * vol, -1.0, 1.0) * 32767))
        return pygame.mixer.Sound(buffer=buf)

    def play(self, name, vol=1.0):
        if not self.ok or self.muted:
            return
        s = self.bank.get(name)
        if s is None:
            return
        try:
            ch = pygame.mixer.find_channel(True)
            if ch:
                ch.set_volume(clamp(vol, 0.0, 1.0))
                ch.play(s)
        except pygame.error:
            pass


SFX = Sfx()


# ---------------------------------------------------------------------------
# MUSIC
#
# Three loops out of the same array of samples the sounds are. They are
# built on first use and kept, because building one costs about a fifth of
# a second and doing all three at start-up would be felt.
#
# A note that overhangs the end of the loop wraps round to the beginning,
# which is what makes the seam join. And `to_bytes` trims the tail back to
# the last thing anybody can hear: every loop otherwise carries a second
# of silence that comes round once a bar.
# ---------------------------------------------------------------------------
def _hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


class Score:
    RATE = 22050

    def __init__(self, seconds):
        self.n = int(self.RATE * seconds)
        self.buf = [0.0] * self.n

    def _put(self, i, v):
        self.buf[i % self.n] += v

    def note(self, kind, midi, t, dur, vol=0.3, detune=0.0):
        """One voice. `kind` picks the waveform and the envelope with it."""
        hz = _hz(midi) * (1.0 + detune)
        start = int(t * self.RATE)
        n = int(dur * self.RATE)
        if n <= 0:
            return
        atk = 0.006 if kind in ("saw", "square", "pluck") else 0.09
        if kind == "bell":
            atk = 0.002
        ai = max(1, int(atk * self.RATE))
        ph = 0.0
        for i in range(n):
            f = i / n
            ph += TAU * hz / self.RATE
            if kind == "saw":
                v = ((ph / TAU) % 1.0) * 2.0 - 1.0
                v = v * 0.7 + 0.3 * math.sin(ph * 2.0)
            elif kind == "square":
                v = (1.0 if math.sin(ph) >= 0 else -1.0) * 0.6
            elif kind == "horn":
                # odd harmonics, a slow lip - this is the voice the yard
                # theme has not got, which is what keeps them apart
                v = (math.sin(ph) + 0.42 * math.sin(ph * 3.0)
                     + 0.2 * math.sin(ph * 5.0)) * 0.55
            elif kind == "bell":
                # the loudest partial is the tierce at 1.19x, not the
                # fundamental - that is what makes it read as metal
                v = (0.42 * math.sin(ph) + 1.0 * math.sin(ph * 1.19)
                     + 0.5 * math.sin(ph * 2.0) + 0.3 * math.sin(ph * 2.99)
                     + 0.18 * math.sin(ph * 4.2)) * 0.38
            elif kind == "pad":
                v = (math.sin(ph) + 0.5 * math.sin(ph * 2.002)
                     + 0.25 * math.sin(ph * 3.0)) * 0.42
            else:                                        # pluck
                v = math.sin(ph) + 0.3 * math.sin(ph * 2.0)
                v *= 0.6
            if kind == "bell":
                env = math.exp(-f * 4.2)
            elif kind == "pluck":
                env = math.exp(-f * 5.5)
            elif kind == "pad":
                env = math.sin(math.pi * clamp(f, 0.0, 1.0)) ** 0.7
            else:
                env = (1.0 - f) ** 0.6
            if i < ai:
                env *= i / ai
            self._put(start + i, v * env * vol)

    def drum(self, kind, t, vol=0.4):
        start = int(t * self.RATE)
        if kind == "kick":
            n = int(0.16 * self.RATE)
            ph = 0.0
            for i in range(n):
                f = i / n
                ph += TAU * (128.0 * (1.0 - 0.72 * f)) / self.RATE
                self._put(start + i, math.sin(ph) * (1.0 - f) ** 2.2 * vol)
        elif kind == "snare":
            n = int(0.13 * self.RATE)
            for i in range(n):
                f = i / n
                v = random.uniform(-1, 1) * 0.8 + math.sin(
                    TAU * 190.0 * i / self.RATE) * 0.3
                self._put(start + i, v * (1.0 - f) ** 2.6 * vol)
        elif kind == "hat":
            n = int(0.045 * self.RATE)
            for i in range(n):
                f = i / n
                self._put(start + i,
                          random.uniform(-1, 1) * (1.0 - f) ** 3.0 * vol * 0.5)
        elif kind == "clank":
            # a hammer on a hull: noise burst plus two ringing partials
            n = int(0.42 * self.RATE)
            for i in range(n):
                f = i / n
                ring = (math.sin(TAU * 740.0 * i / self.RATE) * 0.5
                        + math.sin(TAU * 1103.0 * i / self.RATE) * 0.35)
                nz = random.uniform(-1, 1) * math.exp(-f * 26.0)
                self._put(start + i, (ring * math.exp(-f * 5.0) + nz) * vol)

    def to_bytes(self):
        peak = max(1e-6, max(abs(v) for v in self.buf))
        g = 0.82 / peak
        # trim back in 10ms blocks to the last audible one, keep 0.1s, and
        # fade 25ms so the loop point does not click
        blk = int(self.RATE * 0.01)
        thresh = peak * 0.004
        end = self.n
        while end > blk * 8:
            seg = self.buf[end - blk:end]
            if max(abs(v) for v in seg) > thresh:
                break
            end -= blk
        end = min(self.n, end + int(self.RATE * 0.1))
        fade = int(self.RATE * 0.025)
        out = array("h")
        for i in range(end):
            v = self.buf[i] * g
            if i >= end - fade:
                v *= (end - i) / fade
            out.append(int(clamp(v, -1.0, 1.0) * 32767))
        return out


# Chords are (root midi, the three notes over it). Each piece names its own
# progression so that nothing but the key is shared between them.
def _build_yard():
    """THE YARD - slow, wide, almost nothing happening. A hammer on 1."""
    bpm, bars = 68.0, 8
    beat = 60.0 / bpm
    s = Score(bars * 4 * beat + 2.2)
    roots = (33, 33, 31, 36, 33, 33, 28, 31)
    for b in range(bars):
        t = b * 4 * beat
        r = roots[b]
        s.note("pad", r, t, beat * 4.4, 0.20)
        s.note("pad", r + 7, t + 0.05, beat * 4.2, 0.13)
        s.note("pad", r + 12, t + 0.1, beat * 4.0, 0.10)
        s.drum("clank", t, 0.30)
        if b % 2 == 1:
            s.drum("clank", t + beat * 2.5, 0.18)
        # a bell figure every other bar, never on the beat it landed last
        if b % 4 in (1, 3):
            for k, off in enumerate((0, 7, 12)):
                s.note("bell", r + 24 + off, t + beat * (1.0 + k * 0.75),
                       beat * 1.6, 0.16)
    return s


def _build_landfall():
    """LANDFALL - the fight. Chugs, a horn over the top, a full kit."""
    bpm, bars = 150.0, 8
    beat = 60.0 / bpm
    s = Score(bars * 4 * beat + 1.4)
    roots = (33, 33, 36, 34, 33, 33, 31, 30)
    horn = ((0, 7, 10, 7), (0, 10, 12, 10), (3, 7, 3, 0), (0, 5, 7, 10))
    for b in range(bars):
        t = b * 4 * beat
        r = roots[b]
        for e in range(8):                        # eighth-note chug
            te = t + e * beat * 0.5
            if e in (3, 7):
                continue                          # the gap is the groove
            s.note("saw", r, te, beat * 0.42, 0.30)
            s.note("saw", r + 12, te, beat * 0.42, 0.11)
        for e in range(4):
            s.drum("kick", t + e * beat, 0.46 if e in (0, 2) else 0.22)
            s.drum("hat", t + e * beat + beat * 0.5, 0.20)
        s.drum("snare", t + beat, 0.36)
        s.drum("snare", t + beat * 3, 0.36)
        line = horn[b % 4]
        for k, step in enumerate(line):
            s.note("horn", r + 24 + step, t + k * beat, beat * 0.9, 0.17)
    return s


def _build_vigil():
    """THE VIGIL - title and after. An arpeggio, no kit, no grit."""
    bpm, bars = 96.0, 8
    beat = 60.0 / bpm
    s = Score(bars * 4 * beat + 1.8)
    roots = (40, 38, 36, 38, 40, 43, 41, 36)
    shape = (0, 7, 12, 16, 12, 7, 12, 4)
    for b in range(bars):
        t = b * 4 * beat
        r = roots[b]
        for k, step in enumerate(shape):
            s.note("pluck", r + 12 + step, t + k * beat * 0.5, beat * 0.9,
                   0.24 if k % 4 == 0 else 0.16)
        s.note("pad", r - 12, t, beat * 4.3, 0.17)
        s.note("pad", r - 5, t + 0.04, beat * 4.1, 0.10)
        if b % 4 == 2:
            s.note("bell", r + 24, t + beat * 2, beat * 2.4, 0.13)
    return s


TRACKS = {"yard": _build_yard, "landfall": _build_landfall,
          "vigil": _build_vigil}
_music = {}
_playing = [None]


def music(name):
    """Start a loop, or keep the one that is already going."""
    if not SFX.ok or SFX.muted:
        return
    if _playing[0] == name:
        return
    snd = _music.get(name)
    if snd is None:
        maker = TRACKS.get(name)
        if maker is None:
            return
        try:
            snd = pygame.mixer.Sound(buffer=maker().to_bytes())
        except (pygame.error, MemoryError):
            return
        _music[name] = snd
    try:
        pygame.mixer.music.stop()
        if _playing[0] and _music.get(_playing[0]):
            _music[_playing[0]].stop()
        snd.set_volume(0.42)
        snd.play(loops=-1)
        _playing[0] = name
    except pygame.error:
        pass


def music_stop():
    for s in _music.values():
        try:
            s.stop()
        except pygame.error:
            pass
    _playing[0] = None


# ---------------------------------------------------------------------------
# THE CATALOGUE
#
# Nine sockets. Seven of them hold one of three tiers of the same thing and
# two of them hold a weapon, of which there are ten. Every screen in the
# game reads off the tables below - the gantry, the shop, the damage
# report and the fight all ask the same two questions, "what is in this
# socket" and "what does it do", so adding a part means adding a row here
# and nothing else.
#
# A tier is a REFIT of the one below it: you cannot bolt a layered core
# onto a bare frame, you pay for plated and then you pay for layered. That
# is what makes ALLOY the real constraint. There are eighteen pieces of it
# in the whole game and twenty-four pieces' worth of things to spend it on,
# so no machine is ever finished - only finished enough.
# ---------------------------------------------------------------------------
SOCKETS = ("legs", "torso", "head", "l_arm", "l_wpn", "r_arm", "r_wpn",
           "reactor", "armour")

SOCKET_LABEL = {"legs": "LEGS", "torso": "TORSO", "head": "HEAD",
                "l_arm": "LEFT ARM", "r_arm": "RIGHT ARM",
                "l_wpn": "LEFT HARDPOINT", "r_wpn": "RIGHT HARDPOINT",
                "reactor": "REACTOR", "armour": "PLATE"}

# the fight HUD is narrower than the yard's, so it gets its own labels
HUD_LABEL = {"legs": "LEGS", "torso": "CORE", "head": "HEAD",
             "l_arm": "L ARM", "r_arm": "R ARM", "l_wpn": "L GUN",
             "r_wpn": "R GUN", "reactor": "REACTOR", "armour": "PLATE"}

# a hardpoint is dead weight without the arm it hangs off
NEEDS = {"l_wpn": "l_arm", "r_wpn": "r_arm"}

# where the damage goes. An empty socket cannot be hit - that damage
# rolls onto the torso instead, which is why a stripped machine dies fast.
HIT_WEIGHT = {"torso": 32, "legs": 20, "l_arm": 11, "r_arm": 11,
              "l_wpn": 4, "r_wpn": 4, "head": 8, "reactor": 8}


class Part:
    """One row of the catalogue. `stats` is read by name and never copied."""

    __slots__ = ("socket", "tier", "name", "scrap", "alloy", "days", "hp",
                 "blurb", "stats")

    def __init__(self, socket, tier, name, scrap, alloy, days, hp, blurb,
                 **stats):
        self.socket = socket
        self.tier = tier
        self.name = name
        self.scrap = scrap
        self.alloy = alloy
        self.days = days
        self.hp = hp
        self.blurb = blurb
        self.stats = stats

    def get(self, key, default=0):
        return self.stats.get(key, default)


CATALOGUE = {
    "legs": [
        Part("legs", 1, "SCAFFOLD LEGS", 90, 0, 4, 200,
             "Site scaffolding with feet welded on. It walks.",
             speed=118),
        Part("legs", 2, "HYDRAULIC LEGS", 240, 1, 5, 340,
             "Proper actuators. You can cross the river in four steps.",
             speed=178),
        Part("legs", 3, "PISTON STRIDERS", 580, 0, 6, 520,
             "Ram-assisted. Holds a charge in the knee - that is the boost.",
             speed=232, boost=1),
    ],
    "torso": [
        Part("torso", 1, "GIRDER FRAME", 0, 0, 0, 320,
             "The frame that went up last winter. It is a ribcage, not armour.",
             ),
        Part("torso", 2, "PLATED TORSO", 250, 1, 5, 700,
             "Skinned in ship plate. Doubles what the machine can survive.",
             ),
        Part("torso", 3, "LAYERED CORE", 500, 2, 6, 1200,
             "Plate, void, plate. Built to be hit and go on standing.",
             ),
    ],
    "head": [
        Part("head", 1, "SENSOR POD", 60, 0, 3, 90,
             "Two cameras and a rangefinder. You can see what you are shooting.",
             spread=0.55, warn=0.0),
        Part("head", 2, "COMMAND HEAD", 200, 1, 4, 150,
             "Reads the wind-up half a second before it lands.",
             spread=0.35, warn=0.30, crit=0.10),
        Part("head", 3, "WARSIGHT", 490, 0, 5, 210,
             "Picks the seam in the hide and puts every round through it.",
             spread=0.18, warn=0.55, crit=0.22, dmg=1.14),
    ],
    "l_arm": [
        Part("l_arm", 1, "WELDED ARM", 80, 0, 4, 150,
             "Girder, elbow, a fist-sized socket. Stiff, and it holds.",
             cycle=1.0, melee=1.0),
        Part("l_arm", 2, "SERVO ARM", 265, 0, 5, 280,
             "Powered joints. Everything on the end of it cycles faster.",
             cycle=0.80, melee=1.18),
        Part("l_arm", 3, "IMPACT ARM", 400, 1, 5, 430,
             "A shoulder that throws its whole weight behind the hand.",
             cycle=0.68, melee=1.45),
    ],
    "reactor": [
        Part("reactor", 1, "SHOP GENERATOR", 70, 0, 3, 110,
             "The one that runs the yard. It will run a mech for a minute.",
             heat=100, vent=13),
        Part("reactor", 2, "FUSION CELL", 250, 1, 5, 190,
             "A real core. The weapons stop being the thing that stops you.",
             heat=160, vent=21),
        Part("reactor", 3, "KAIJU HEART", 480, 3, 6, 270,
             "It was still beating when they cut it out. It still is.",
             heat=240, vent=30),
    ],
    "armour": [
        Part("armour", 1, "SALVAGE PLATE", 90, 0, 4, 180,
             "Hull steel off the breakers. Takes the edge off everything.",
             dr=4),
        Part("armour", 2, "COMPOSITE PLATE", 260, 1, 5, 340,
             "Laminate over a crush layer. Spends itself to save the frame.",
             dr=10),
        Part("armour", 3, "SCALE WEAVE", 500, 2, 6, 520,
             "Their hide, cleaned and re-hung on our frame. It works.",
             dr=18),
    ],
}
# the right arm is the left arm's table with the socket swapped, so the two
# can never drift apart
CATALOGUE["r_arm"] = [
    Part("r_arm", p.tier, p.name, p.scrap, p.alloy, p.days, p.hp, p.blurb,
         **p.stats) for p in CATALOGUE["l_arm"]]


# ---------------------------------------------------------------------------
# THE WEAPONS
#
# Heat is the only ammunition. Every weapon is priced in damage-per-heat,
# and the reactor decides how much heat per second you are allowed to
# spend - so the lance is a bad weapon on a shop generator and the best
# one in the game on a kaiju heart, and nothing about the lance changed.
#
#   kind    "melee" swings an arc, "gun" throws a shell, "salvo" throws
#           several with a splash, "beam" is held down and bills by the
#           second rather than by the shot.
# ---------------------------------------------------------------------------
class Weapon:
    __slots__ = ("key", "name", "kind", "scrap", "alloy", "days", "hp",
                 "dmg", "cd", "heat", "reach", "blurb", "base", "shots",
                 "splash", "stagger", "speed", "pierce")

    def __init__(self, key, name, kind, scrap, alloy, days, hp, dmg, cd,
                 heat, reach, blurb, base=None, shots=1, splash=0,
                 stagger=0.0, speed=0.0, pierce=0):
        self.key = key
        self.name = name
        self.kind = kind
        self.scrap = scrap
        self.alloy = alloy
        self.days = days
        self.hp = hp
        self.dmg = dmg              # per hit, or per second for a beam
        self.cd = cd                # seconds between shots
        self.heat = heat            # per shot, or per second for a beam
        self.reach = reach          # melee arc length / gun range
        self.blurb = blurb
        self.base = base            # the weapon this one is a refit of
        self.shots = shots
        self.splash = splash
        self.stagger = stagger      # how much of the stagger meter one hit fills
        self.speed = speed          # projectile speed
        self.pierce = pierce

    @property
    def dph(self):
        """Damage per point of heat - the number that decides the build."""
        rate = self.dmg * self.shots
        cost = self.heat
        return rate / max(0.01, cost)


WEAPON_LIST = [
    Weapon("fist", "RIVET FIST", "melee", 60, 0, 3, 150,
           26, 0.75, 5.0, 172,
           "A hydraulic hammer on a wrist. Cheap, and it never jams.",
           stagger=0.12),
    Weapon("pile", "PILE DRIVER", "melee", 190, 1, 4, 250,
           70, 1.15, 12.0, 186,
           "The same fist with a charge behind it. It moves things.",
           base="fist", stagger=0.34),

    Weapon("saw", "CHAIN SAW", "melee", 140, 0, 4, 150,
           13, 0.16, 3.0, 150,
           "Held against the hide it does terrible work. You must hold it.",
           stagger=0.03),
    Weapon("ripper", "RIPPER", "melee", 310, 2, 5, 250,
           22, 0.15, 3.6, 158,
           "Two chains counter-rotating. Nothing comes off it whole.",
           base="saw", stagger=0.04),

    Weapon("auto", "AUTOCANNON", "gun", 130, 0, 4, 150,
           20, 0.34, 4.2, 900,
           "Forty millimetre, belt fed. The honest answer to most things.",
           speed=1250, stagger=0.05),
    Weapon("revolver", "REVOLVER CANNON", "gun", 320, 1, 5, 250,
           28, 0.28, 6.2, 980,
           "Four barrels on a drum. Runs hot and does not care.",
           base="auto", speed=1400, stagger=0.07),

    Weapon("missile", "MISSILE RACK", "salvo", 200, 1, 5, 150,
           34, 2.60, 26.0, 1100,
           "Four at a time, and they go off where they land.",
           shots=4, splash=110, speed=720, stagger=0.10),
    Weapon("swarm", "SWARM RACK", "salvo", 380, 2, 5, 250,
           40, 2.40, 44.0, 1200,
           "Six tubes and a faster reload. Clears a street.",
           base="missile", shots=6, splash=132, speed=780, stagger=0.09),

    Weapon("lance", "PLASMA LANCE", "beam", 320, 2, 6, 150,
           110, 0.0, 34.0, 1000,
           "Billed by the second. Bring a reactor or do not bring this.",
           stagger=0.0),
    # Sarah's, and locked until she has been paid for the drawing
    Weapon("rail", "RAIL LANCE", "gun", 340, 2, 5, 190,
           46, 0.52, 9.4, 1500,
           "Ignores hide outright. She spent a year on the rails.",
           speed=2100, stagger=0.09, pierce=1),
    Weapon("hook", "GRAVE HOOK", "melee", 300, 1, 5, 190,
           40, 0.85, 7.0, 320,
           "Drags what it catches back into reach, whatever it wanted.",
           stagger=0.16),

    Weapon("sun", "SUN LANCE", "beam", 560, 3, 6, 250,
           170, 0.0, 40.0, 1150,
           "Goes through the first one and into whatever is behind it.",
           base="lance", pierce=1),
]
WEAPONS = {w.key: w for w in WEAPON_LIST}
# families laid out for the shop: the base, then its refit
WEAPON_FAMILIES = (("fist", "pile"), ("saw", "ripper"), ("auto", "revolver"),
                   ("missile", "swarm"), ("lance", "sun"))
# families that are not in the book until a Hendra sells you the book
BLUEPRINT_WEAPONS = {"rail": "bp_rail", "hook": "bp_hook"}


def part_of(socket, fit):
    """Whatever is in a socket, as a Part, Weapon, Module or YardUp."""
    if fit is None:
        return None
    if socket == MOD_SLOT:
        return MODULES.get(fit)
    if socket == REFINE_SLOT:
        return REFINE
    if socket == YARD_SLOT:
        return YARD[fit - 1] if isinstance(fit, int) and 1 <= fit <= len(YARD)             else None
    if socket in ("l_wpn", "r_wpn"):
        return WEAPONS.get(fit)
    table = CATALOGUE.get(socket)
    if not table or not 1 <= fit <= len(table):
        return None
    return table[fit - 1]


def options_for(socket, fit):
    """What the yard could put in this socket next, given what is in it.

    A body socket offers only the tier above what it holds; a hardpoint
    offers every weapon it does not hold, plus the refit of the one it
    does. Nothing here checks whether you can afford it - the shop does
    that, so the player can see what they are saving for."""
    if socket == YARD_SLOT:
        nxt = (fit or 0) + 1
        return [YARD[nxt - 1]] if nxt <= len(YARD) else []
    if socket in ("l_wpn", "r_wpn"):
        out = []
        for base, up in WEAPON_FAMILIES:
            if fit == base:
                out.append(WEAPONS[up])        # the refit of what is mounted
            elif fit != up:
                out.append(WEAPONS[base])      # swap to a different family
        for key, ware in BLUEPRINT_WEAPONS.items():
            if fit != key and has_ware(ware):
                out.append(WEAPONS[key])
        return out
    table = CATALOGUE.get(socket, ())
    nxt = (fit or 0) + 1
    return [table[nxt - 1]] if nxt <= len(table) else []



# ---------------------------------------------------------------------------
# THE RACK
#
# Tiers are a ladder: every body socket offers exactly one thing next, so
# most of the build has no decision in it at all - you buy the next rung
# when you can afford the next rung. Modules are the other axis. They are
# cheap, they are small, they do not replace anything, and there are only
# ever as many bays as the torso has room for, so putting one in is always
# a decision about what you are NOT putting in.
#
# Most of them cost something as well as giving something. A module that
# is only better is not a choice.
# ---------------------------------------------------------------------------
class Module:
    __slots__ = ("key", "name", "scrap", "alloy", "days", "blurb", "effect",
                 "hp", "tier")

    def __init__(self, key, name, scrap, alloy, days, effect, blurb):
        self.key = key
        self.name = name
        self.scrap = scrap
        self.alloy = alloy
        self.days = days
        self.effect = effect         # the one line of numbers
        self.blurb = blurb
        self.hp = 0                  # modules are inside; nothing hits them
        self.tier = 0

    def get(self, key, default=0):
        return default


MODULE_LIST = [
    Module("autoloader", "AUTOLOADER", 190, 0, 3,
           "barrels cycle 20% faster, and run 16% hotter",
           "A belt and a ram instead of a crewman with a shell."),
    Module("sinks", "HEAT SINKS", 170, 0, 3,
           "vent +30%, ceiling -14%",
           "Fins down the back. You cool faster and you hold less."),
    Module("shutters", "BLAST SHUTTERS", 240, 1, 4,
           "bracing takes 30% instead of 50%, and vents at 2.5x",
           "Plates that drop over the seams. Bracing becomes a plan."),
    Module("gyro", "GYRO STABILISER", 220, 0, 3,
           "nothing staggers or scrambles you; walk -8%",
           "It will not go over, and it will not be hurried either."),
    Module("claws", "SALVAGE CLAWS", 210, 0, 3,
           "+30% scrap off a corpse",
           "You are standing on the most valuable thing in the country."),
    Module("redundant", "REDUNDANT LINKAGE", 300, 1, 4,
           "the first part wrecked each landfall hangs on",
           "Two of every cable, routed the long way round."),
    Module("flush", "COOLANT FLUSH", 250, 1, 3,
           "V dumps the whole heat load - once per landfall",
           "One tank of cold, and then you have used your tank of cold."),
    Module("link", "TARGETING LINK", 280, 1, 4,
           "+14% from anything with a barrel",
           "It watches where the last one went and corrects."),
    Module("shock", "SHOCK PLATING", 230, 0, 3,
           "anything that hits you in melee takes 16 back",
           "Charged hull. It does not stop the blow, it bills for it."),
    Module("stride", "STRIDE ASSIST", 180, 0, 3,
           "walk +20%",
           "Ankle rams. The difference between reaching it and watching it."),
    Module("hoist", "AMMO HOIST", 200, 0, 3,
           "a salvo throws one more",
           "Only worth the bay if there is a rack on the arm."),
    Module("baffles", "CORE BAFFLES", 260, 1, 4,
           "the reactor cannot be hit; the frame takes it instead",
           "The one part you cannot fight without, moved inboard."),
    Module("spotter", "SPOTTER DRONE", 320, 1, 4,
           "sensors and wind-up warning with no head at all",
           "It sits above the fight and tells you what is coming."),
]
MODULES = {m.key: m for m in MODULE_LIST}
MOD_SLOT = "mods"                    # a job socket, but not one on the body


# ---------------------------------------------------------------------------
# THE YARD ITSELF
#
# The other half of the game is a calendar, so the other half of the
# upgrades are things that change the calendar. None of these are bolted
# to the machine and none of them can be hit.
# ---------------------------------------------------------------------------
class YardUp:
    __slots__ = ("tier", "name", "scrap", "alloy", "days", "effect", "blurb",
                 "hp")

    def __init__(self, tier, name, scrap, alloy, days, effect, blurb):
        self.tier = tier
        self.name = name
        self.scrap = scrap
        self.alloy = alloy
        self.days = days
        self.effect = effect
        self.blurb = blurb
        self.hp = 0

    def get(self, key, default=0):
        return default


YARD = [
    YardUp(1, "SECOND CRANE", 240, 0, 4,
           "four on a job instead of three, and rushing costs 25% less",
           "There is room over the shoulder for one more gang."),
    YardUp(2, "NIGHT SHIFT", 430, 1, 5,
           "one more pair of hands on the books, repairs a day quicker",
           "The lights stay on. Nobody asked the neighbours."),
    YardUp(3, "FOUNDRY", 720, 2, 6,
           "+25% income, and one more alloy off every corpse",
           "We stopped selling the hide and started cooking it."),
]
YARD_SLOT = "yard"


# ---------------------------------------------------------------------------
# THE LONG WAY ROUND
#
# ALLOY only ever came off a corpse, which meant a run that lost a fight
# lost the thing it needed to win the next one, and a run that won them all
# still finished sitting on money it could not spend. This is the other
# way: put a great deal of scrap and several days into a crucible - or a
# culture - and get one piece out. It is deliberately a bad rate. It is
# meant to be the thing you do when the alternative is nothing.
# ---------------------------------------------------------------------------
class Refine:
    __slots__ = ("tier", "name", "scrap", "alloy", "days", "effect", "blurb",
                 "hp")

    def __init__(self):
        self.tier = 0
        self.name = "SMELT A BILLET"
        self.scrap = 300
        self.alloy = 0
        self.days = 4
        self.hp = 0
        self.effect = "one ALLOY out, two once the FOUNDRY is lit"
        self.blurb = ("A bad rate and everybody knows it. It is still "
                      "better than going out short.")


REFINE = Refine()
REFINE_SLOT = "refine"
REFINE_RYEZ_NAME = "CULTURE A STRAND"
REFINE_RYEZ_EFFECT = "one GENOME out, two once the GENE VATS are running"
REFINE_RYEZ_BLURB = ("Slow, wasteful, and it works. It is still better than "
                     "going out short.")

# ---------------------------------------------------------------------------
# THE MACHINE
#
# The mech is nine numbers and nine hit points. Everything else about it -
# how fast it walks, how long it can shoot, what a hit takes off it - is
# read out of the catalogue at the moment it is asked, so there is no
# second copy of the build to go stale.
#
# Damage is LOCAL. A hit picks a socket, the plate takes its cut, and what
# is left goes into that part; when the part is gone the overflow rolls
# into the torso. So a machine does not lose a health bar, it loses a leg,
# and it keeps that limp until somebody in the yard fixes it.
# ---------------------------------------------------------------------------
class Mech:
    def __init__(self):
        self.fit = {s: None for s in SOCKETS}
        self.hp = {s: 0.0 for s in SOCKETS}
        # what the yard had standing when the money ran out
        self.install("torso", 1)
        self.install("l_arm", 1)
        self.mods = []               # module keys, in the order they went in
        # fight-time state, reset by Fight
        self.heat = 0.0
        self.locked = False

    # -- the build ---------------------------------------------------------
    def install(self, socket, fit):
        self.fit[socket] = fit
        self.hp[socket] = self.max_hp(socket)

    def max_hp(self, socket):
        p = part_of(socket, self.fit[socket])
        if p is None:
            return 0.0
        return float(p.hp) * (1.12 if has_ware("thickblood") else 1.0)

    def held(self, socket):
        return part_of(socket, self.fit[socket])

    # -- the rack ----------------------------------------------------------
    @property
    def bays(self):
        """How many modules fit. A girder frame has room for one; you buy
        the room by buying the torso, which is what makes the torso worth
        more than its health number says."""
        return (self.fit["torso"] or 1) + (1 if has_ware("deepgut") else 0)

    def has(self, key):
        return key in self.mods

    def fit_module(self, key):
        if key in self.mods or key not in MODULES:
            return False
        if len(self.mods) >= self.bays:
            return False
        self.mods.append(key)
        return True

    def pull_module(self, key):
        if key in self.mods:
            self.mods.remove(key)
            return True
        return False

    def alive(self, socket):
        """Installed and not wrecked. Everything in the fight asks this."""
        return self.fit[socket] is not None and self.hp[socket] > 0

    def stat(self, socket, key, default=0.0):
        p = self.held(socket)
        if p is None or self.hp[socket] <= 0:
            return default
        return p.get(key, default)

    def weapon(self, side):
        """The weapon on a side, or None if the weapon or its arm is out."""
        wsock = "l_wpn" if side == "l" else "r_wpn"
        asock = "l_arm" if side == "l" else "r_arm"
        if not self.alive(wsock) or not self.alive(asock):
            return None
        return WEAPONS.get(self.fit[wsock])

    # -- what it adds up to ------------------------------------------------
    @property
    def speed(self):
        v = self.stat("legs", "speed", 0.0)
        if self.has("stride"):
            v *= 1.20
        if self.has("gyro"):
            v *= 0.92
        if has_ware("quicknerve"):
            v *= 1.10
        return v

    @property
    def can_boost(self):
        return bool(self.stat("legs", "boost", 0))

    @property
    def heat_cap(self):
        # no reactor at all is not no heat - it is a very small budget
        v = self.stat("reactor", "heat", 60.0)
        return v * 0.86 if self.has("sinks") else v

    @property
    def vent(self):
        v = self.stat("reactor", "vent", 5.0)
        return v * 1.30 if self.has("sinks") else v

    @property
    def dr(self):
        return self.stat("armour", "dr", 0.0)

    @property
    def spread(self):
        return self.stat("head", "spread", 1.0)

    @property
    def crit(self):
        return self.stat("head", "crit", 0.0)

    @property
    def warn(self):
        """Seconds of extra telegraph the sensors buy you."""
        return max(self.stat("head", "warn", 0.0),
                   0.35 if self.has("spotter") else 0.0)

    @property
    def sensors(self):
        """Whether the pilot can read the animal at all."""
        return self.alive("head") or self.has("spotter")

    @property
    def brace_factor(self):
        return 0.30 if self.has("shutters") else 0.45

    @property
    def dmg_mult(self):
        return self.stat("head", "dmg", 1.0)

    def arm_stat(self, side, key, default=1.0):
        return self.stat("l_arm" if side == "l" else "r_arm", key, default)

    @property
    def down(self):
        return self.hp["torso"] <= 0

    @property
    def armed(self):
        return self.weapon("l") is not None or self.weapon("r") is not None

    def ready(self):
        """Can this thing be sent out at all? A frame with no legs and no
        weapon is not a mech, it is a statue, and the game says so."""
        return self.alive("legs") and self.armed

    def completion(self):
        """How much of the great work is done, 0..1, by value not by count."""
        have = worth = 0.0
        for s in SOCKETS:
            if s in ("l_wpn", "r_wpn"):
                best = max(WEAPONS[u].scrap + WEAPONS[b].scrap
                           for b, u in WEAPON_FAMILIES)
                worth += best
                w = self.held(s)
                if w:
                    have += w.scrap + (WEAPONS[w.base].scrap if w.base else 0)
            else:
                table = CATALOGUE[s]
                worth += sum(p.scrap for p in table) or 1.0
                fitted = self.fit[s] or 0
                have += sum(p.scrap for p in table[:fitted])
        return clamp(have / max(1.0, worth), 0.0, 1.0)

    # -- taking it ---------------------------------------------------------
    def hit_socket(self, aim=None):
        """Which part catches this one. An empty socket cannot be hit, so
        the emptier the machine the more of everything the torso eats."""
        pool = [(s, wt) for s, wt in HIT_WEIGHT.items() if self.alive(s)
                and not (s == "reactor" and self.has("baffles"))]
        if aim and self.alive(aim):
            return aim
        if not pool:
            return "torso"
        total = sum(wt for _, wt in pool)
        r = random.uniform(0, total)
        for s, wt in pool:
            r -= wt
            if r <= 0:
                return s
        return pool[-1][0]

    def hurt(self, dmg, aim=None, bracing=False, pierce_plate=False):
        """Put `dmg` into the machine. Returns (socket, applied, wrecked)."""
        dr = 0.0 if pierce_plate else self.dr
        if dr > 0 and self.alive("armour"):
            taken = min(dr, dmg * 0.85)
            dmg -= taken
            # the plate spends itself doing it, and one day it is gone
            self.hp["armour"] = max(0.0, self.hp["armour"] - taken * 0.55)
        if bracing:
            dmg *= self.brace_factor
        socket = self.hit_socket(aim)
        before = self.hp[socket]
        self.hp[socket] = max(0.0, before - dmg)
        wrecked = before > 0 >= self.hp[socket]
        spill = dmg - before
        if spill > 0 and socket != "torso":
            # nothing left to break here, so it goes through into the frame
            self.hp["torso"] = max(0.0, self.hp["torso"] - spill * 0.5)
        return socket, dmg, wrecked

    # -- putting it back together -----------------------------------------
    def damage_frac(self, socket):
        mx = self.max_hp(socket)
        if mx <= 0:
            return 0.0
        return clamp(1.0 - self.hp[socket] / mx, 0.0, 1.0)

    def repair_cost(self, socket):
        """(scrap, days) to bring one socket back to full. A wrecked part is
        not a new part - it is always cheaper to weld than to buy."""
        p = self.held(socket)
        f = self.damage_frac(socket)
        if p is None or f <= 0.001:
            return (0, 0)
        base = max(p.scrap, 120)
        days = max(1, int(round(f * max(p.days, 3) * 0.6)))
        cost = int(round(f * base * 0.45)) + 8
        if has_ware("sharptools"):
            cost = int(round(cost * 0.70))
        return (cost, days)

    def needs_repair(self):
        return [s for s in SOCKETS if self.damage_frac(s) > 0.001]

    # -- the fight uses these ---------------------------------------------
    def reset_for_fight(self):
        self.heat = 0.0
        self.locked = False

    def add_heat(self, amount):
        self.heat = clamp(self.heat + amount, 0.0, self.heat_cap)
        if self.heat >= self.heat_cap - 0.01:
            self.locked = True

    def cool(self, dt):
        self.heat = max(0.0, self.heat - self.vent * dt)
        if self.locked and self.heat <= self.heat_cap * 0.62:
            self.locked = False

    @property
    def heat_frac(self):
        return clamp(self.heat / max(1.0, self.heat_cap), 0.0, 1.0)

    # -- saved between sessions -------------------------------------------
    def to_json(self):
        return {"fit": dict(self.fit), "mods": list(self.mods),
                "hp": {k: round(v, 1) for k, v in self.hp.items()}}

    @classmethod
    def from_json(cls, data):
        m = cls()
        fit = (data or {}).get("fit", {})
        hp = (data or {}).get("hp", {})
        for s in SOCKETS:
            v = fit.get(s)
            if s in ("l_wpn", "r_wpn"):
                m.fit[s] = v if v in WEAPONS else None
            else:
                m.fit[s] = v if isinstance(v, int) and 1 <= v <= 3 else None
            m.hp[s] = clamp(float(hp.get(s, m.max_hp(s)) or 0.0),
                            0.0, m.max_hp(s))
        if m.fit["torso"] is None:                # a run without a frame
            m.install("torso", 1)                 # is not a run
        mods = (data or {}).get("mods") or []
        m.mods = [k for k in mods if k in MODULES][:m.bays]
        return m


# ---------------------------------------------------------------------------
# DRAWING THE MACHINE - FRONT
#
# The gantry view. Every part is a list of polygons in the mech's own
# coordinates, where (0, 0) is between its feet and up is negative, and a
# Rig puts them on the screen at whatever size the panel has room for.
#
# The shapes are shared between the three states a socket can be in -
# BOLTED ON, EMPTY and BEING WORKED - because an empty socket is drawn as
# a dashed outline of the exact part that goes there. That is the whole
# point of the screen: you can see the machine you have not built yet.
# ---------------------------------------------------------------------------
class Rig:
    """Mech coordinates onto a surface. Nothing else knows the scale."""

    def __init__(self, surf, cx, gy, scale):
        self.surf = surf
        self.cx = cx
        self.gy = gy
        self.s = scale

    def p(self, x, y):
        return (self.cx + x * self.s, self.gy + y * self.s)

    def pts(self, pts):
        return [self.p(x, y) for x, y in pts]

    def poly(self, pts, colour, width=0):
        pygame.draw.polygon(self.surf, colour, self.pts(pts), width)

    def ghost(self, pts, colour=GHOST, width=2):
        dashed_poly(self.surf, self.pts(pts), colour,
                    max(1, int(width * min(1.4, self.s))),
                    dash=max(4, int(7 * self.s)), gap=max(3, int(6 * self.s)))

    def line(self, a, b, colour, width=2):
        pygame.draw.line(self.surf, colour, self.p(*a), self.p(*b),
                         max(1, int(width * self.s)))

    def circle(self, c, r, colour, width=0):
        pygame.draw.circle(self.surf, colour, self.p(*c),
                           max(1, int(r * self.s)),
                           0 if width == 0 else max(1, int(width * self.s)))

    def light(self, c, r, colour, strength=110):
        blit_glow(self.surf, self.p(*c), r * self.s, colour, strength)


def mirror(pts):
    return [(-x, y) for x, y in pts]


# -- the shapes -------------------------------------------------------------
# Each returns [(points, tone)] where tone names a shade, not a colour, so
# one part can be drawn in steel, in rust or in ghost grey without the
# shape knowing anything about it.
def shape_legs(tier):
    hip_x = (30, 34, 40)[tier - 1]
    tw = (11, 15, 17)[tier - 1]
    sw = (10, 13, 14)[tier - 1]
    fw = (22, 26, 30)[tier - 1]
    knee = (-118, -122, -130)[tier - 1]
    out = []
    for sgn in (-1, 1):
        cx = hip_x * sgn
        thigh = [(cx - tw, -198), (cx + tw, -198), (cx + tw - 2, knee),
                 (cx - tw + 2, knee)]
        shin = [(cx - sw, knee + 4), (cx + sw, knee + 4),
                (cx + sw + (4 if tier == 3 else 0), -42),
                (cx - sw - (4 if tier == 3 else 0), -42)]
        foot = [(cx - fw, -40), (cx + fw, -40), (cx + fw - 3, -6),
                (cx - fw + 3, -6)]
        out += [(thigh, "main"), (shin, "main"), (foot, "dark")]
        kr = (9, 11, 13)[tier - 1]              # the knee, as an octagon
        out.append(([(cx + math.cos(a) * kr, knee + 2 + math.sin(a) * kr)
                     for a in (i * TAU / 8 for i in range(8))], "dark"))
        if tier >= 2:                         # a piston up the outside
            out.append(([(cx + sgn * (tw + 2), -190),
                         (cx + sgn * (tw + 6), -190),
                         (cx + sgn * (sw + 6), knee + 10),
                         (cx + sgn * (sw + 2), knee + 10)], "light"))
        if tier == 3:                         # calf blocks, a wider stance
            out.append(([(cx - sw - 7, knee - 6), (cx + sw + 7, knee - 6),
                         (cx + sw + 7, -78), (cx - sw - 7, -78)], "dark"))
    if tier >= 2:                             # the hip yoke ties them together
        out.append(([(-hip_x - 8, -212), (hip_x + 8, -212),
                     (hip_x + 4, -190), (-hip_x - 4, -190)], "dark"))
    return out


def shape_torso(tier):
    if tier == 1:                             # a ribcage, drawn as one
        return [([(-64, -330), (64, -330), (52, -240), (38, -202),
                  (-38, -202), (-52, -240)], "hollow")]
    sh = 74 if tier == 2 else 86
    body = [(-sh, -332), (sh, -332), (sh - 14, -244), (40, -202),
            (-40, -202), (-sh + 14, -244)]
    out = [(body, "main")]
    out.append(([(-sh + 10, -326), (sh - 10, -326), (sh - 18, -292),
                 (-sh + 18, -292)], "light"))          # collar
    out.append(([(-30, -236), (30, -236), (26, -206), (-26, -206)], "dark"))
    if tier == 3:                             # outer yokes, a wider outline
        for sgn in (-1, 1):
            out.append(([(sgn * (sh - 4), -338), (sgn * (sh + 16), -326),
                         (sgn * (sh + 12), -286), (sgn * (sh - 6), -282)],
                        "dark"))
    return out


def shape_head(tier):
    if tier == 1:
        return [([(-16, -374), (16, -374), (14, -338), (-14, -338)], "main")]
    if tier == 2:
        return [([(-21, -386), (21, -386), (21, -352), (13, -336),
                  (-13, -336), (-21, -352)], "main"),
                ([(-4, -398), (4, -398), (6, -382), (-6, -382)], "light")]
    return [([(-23, -392), (23, -392), (23, -354), (14, -334),
              (-14, -334), (-23, -354)], "main"),
            ([(-26, -406), (-8, -396), (-10, -382), (-26, -388)], "dark"),
            ([(26, -406), (8, -396), (10, -382), (26, -388)], "dark")]


def shape_arm(tier, side):
    sgn = -1 if side == "l" else 1
    w = (9, 12, 15)[tier - 1]
    sx = (66, 76, 88)[tier - 1] * sgn
    ex = (74, 86, 98)[tier - 1] * sgn
    out = [([(sx - w * sgn, -326), (sx + w * sgn, -326),
             (ex + w * sgn, -258), (ex - w * sgn, -258)], "main"),
           ([(ex - w * sgn, -252), (ex + w * sgn, -252),
             (ex + (w + 1) * sgn, -192), (ex - (w + 1) * sgn, -192)], "main")]
    if tier >= 2:                             # pauldron
        out.insert(0, ([(sx - 18 * sgn, -344), (sx + 20 * sgn, -336),
                        (sx + 18 * sgn, -306), (sx - 16 * sgn, -312)],
                       "dark"))
    if tier == 3:                             # a forearm that means it
        out.append(([(ex - (w + 6) * sgn, -238), (ex + (w + 6) * sgn, -238),
                     (ex + (w + 5) * sgn, -196), (ex - (w + 5) * sgn, -196)],
                    "light"))
    return out


def arm_hand(tier, side):
    """Where a weapon hangs. The shop and the fight both ask for this."""
    sgn = -1 if side == "l" else 1
    return ((74, 86, 98)[tier - 1] * sgn, -186)


def shape_armour(tier):
    # Two chest plates with the yard stripe down the seam. A single slab
    # across the belly reads as a bib, which is not what we are going for.
    out = []
    for sgn in (-1, 1):
        out.append(([(sgn * 22, -310), (sgn * 52, -298), (sgn * 46, -238),
                     (sgn * 24, -244)], "plate"))
        out.append(([(sgn * 26, -306), (sgn * 48, -296), (sgn * 47, -288),
                     (sgn * 26, -297)], "trim"))
    out.append(([(-34, -238), (34, -238), (29, -210), (-29, -210)], "plate"))
    if tier >= 2:
        for sgn in (-1, 1):
            out.append(([(sgn * 26, -208), (sgn * 47, -202), (sgn * 43, -152),
                         (sgn * 26, -158)], "plate"))    # thigh guards
    if tier == 3:
        for sgn in (-1, 1):
            out.append(([(sgn * 56, -340), (sgn * 94, -322), (sgn * 88, -286),
                         (sgn * 54, -296)], "plate"))    # shoulder caps
            out.append(([(sgn * 62, -334), (sgn * 88, -322), (sgn * 86, -312),
                         (sgn * 60, -322)], "trim"))
    return out


def shape_weapon(key, side, tier_arm):
    """The weapon as it hangs in the gantry, around the hand."""
    hx, hy = arm_hand(tier_arm, side)
    sgn = -1 if side == "l" else 1
    w = WEAPONS.get(key)
    if w is None:
        return []
    if w.kind == "melee" and key in ("fist", "pile"):
        big = key == "pile"
        s = 20 if big else 16
        # a fist the same width and colour as the forearm reads as more
        # forearm, so it goes dark with knuckles across it
        out = [([(hx - s, hy - 2), (hx + s, hy - 2), (hx + s - 3, hy + s * 2),
                 (hx - s + 3, hy + s * 2)], "dark")]
        for i in range(3):
            x = hx - s + 5 + i * (s - 2)
            out.append(([(x - 4, hy + 2), (x + 4, hy + 2), (x + 4, hy + 13),
                         (x - 4, hy + 13)], "light"))
        if big:
            out.append(([(hx - 10, hy + 38), (hx + 10, hy + 38),
                         (hx + 7, hy + 64), (hx - 7, hy + 64)], "light"))
        return out
    if w.kind == "melee":                      # saw / ripper
        long = 66 if key == "ripper" else 56
        out = [([(hx - 7, hy - 4), (hx + 7, hy - 4), (hx + 7, hy + long),
                 (hx - 7, hy + long)], "main")]
        for i in range(6):
            y = hy + 6 + i * (long - 10) / 6.0
            out.append(([(hx + 7, y), (hx + 14, y + 3), (hx + 7, y + 7)],
                        "light"))
        if key == "ripper":
            for i in range(6):
                y = hy + 9 + i * (long - 10) / 6.0
                out.append(([(hx - 7, y), (hx - 14, y + 3), (hx - 7, y + 7)],
                            "light"))
        return out
    if w.kind == "gun":
        long = 62 if key == "revolver" else 52
        out = [([(hx - 8, hy - 6), (hx + 8, hy - 6), (hx + 8, hy + 16),
                 (hx - 8, hy + 16)], "dark"),
               ([(hx - 4, hy + 14), (hx + 4, hy + 14), (hx + 4, hy + long),
                 (hx - 4, hy + long)], "main")]
        if key == "revolver":
            out.append(([(hx - 11, hy + 2), (hx + 11, hy + 2),
                         (hx + 11, hy + 22), (hx - 11, hy + 22)], "light"))
        return out
    if w.kind == "salvo":
        rows = 3 if key == "swarm" else 2
        out = [([(hx - 20 * sgn, hy - 12), (hx + 16 * sgn, hy - 12),
                 (hx + 16 * sgn, hy + 10 * rows), (hx - 20 * sgn, hy + 10 * rows)],
                "dark")]
        for r in range(rows):
            for c in range(2):
                x = hx + (-14 + c * 18) * sgn
                y = hy - 6 + r * 10
                out.append(([(x - 5, y), (x + 5, y), (x + 5, y + 6),
                             (x - 5, y + 6)], "light"))
        return out
    # beam
    long = 74 if key == "sun" else 64
    out = [([(hx - 10, hy - 8), (hx + 10, hy - 8), (hx + 8, hy + 18),
             (hx - 8, hy + 18)], "dark"),
           ([(hx - 5, hy + 16), (hx + 5, hy + 16), (hx + 5, hy + long),
             (hx - 5, hy + long)], "main")]
    for i in range(3):
        y = hy + 26 + i * 14
        out.append(([(hx - 9, y), (hx + 9, y), (hx + 9, y + 4),
                     (hx - 9, y + 4)], "light"))
    return out


SHAPE = {"legs": shape_legs, "torso": shape_torso, "head": shape_head,
         "armour": shape_armour}


def part_shape(socket, fit, arm_tier=1):
    """One socket's polygons, whatever kind of socket it is - and whichever
    company signed you. The joints are in the same places either way."""
    bio = CURRENT["house"] == "ryez"
    if socket in ("l_arm", "r_arm"):
        side = "l" if socket == "l_arm" else "r"
        return (bio_arm if bio else shape_arm)(fit, side)
    if socket in ("l_wpn", "r_wpn"):
        side = "l" if socket == "l_wpn" else "r"
        return (bio_weapon if bio else shape_weapon)(fit, side, arm_tier)
    if socket == "reactor":
        r = (11, 15, 19)[fit - 1]
        if bio:                              # a heart, deep in the trunk
            hx, hy = HEART_AT
            return [([(hx - r * 1.15 * math.cos(a),
                       hy + r * 1.3 * math.sin(a)
                       - r * 0.3 * abs(math.cos(a * 2)))
                      for a in (i * TAU / 14 for i in range(14))], "trim")]
        return [([(-r, -284 - r), (r, -284 - r), (r, -284 + r), (-r, -284 + r)],
                 "trim")]
    fn = (BIO_SHAPE if bio else SHAPE).get(socket)
    return fn(fit) if fn else []


TONES = {"main": STEEL, "dark": STEEL_D, "light": STEEL_L, "trim": PAINT,
         "plate": (150, 136, 112), "hollow": STEEL}


def _tone(name, dmg, wrecked, tones=None):
    c = (tones or TONES).get(name, STEEL)
    if wrecked:
        return shade(mix(c, (44, 40, 40), 0.75), 0.9)
    if dmg > 0.05:
        f = clamp((dmg - 0.05) * 0.62, 0.0, 0.52)
        return mix(shade(c, 0.86), (148, 88, 58), f)
    return c


def draw_socket_front(rig, socket, fit, dmg=0.0, arm_tier=1, mode="on",
                      prog=0.0, t=0.0):
    """One socket in one of its three states."""
    tones = BIO_TONES if CURRENT["house"] == "ryez" else None
    shapes = part_shape(socket, fit, arm_tier)
    if not shapes:
        return
    wrecked = dmg >= 0.999
    if mode == "ghost":
        for pts, _ in shapes:
            rig.ghost(pts)
        return
    if mode == "job":
        # the ghost, then the part welded up from the feet as the days pass
        for pts, _ in shapes:
            rig.ghost(pts, (70, 78, 100))
        ys = [y for pts, _ in shapes for _, y in pts]
        lo, hi = min(ys), max(ys)
        cut = rig.p(0, hi - (hi - lo) * clamp(prog, 0.0, 1.0))[1]
        old = rig.surf.get_clip()
        rig.surf.set_clip(pygame.Rect(0, cut, rig.surf.get_width(),
                                      rig.surf.get_height()))
        for pts, tone in shapes:
            if tone == "hollow":
                rig.poly(pts, _tone("dark", 0, False, tones), 3)
            else:
                rig.poly(pts, shade((tones or TONES).get(tone, STEEL), 0.86))
                rig.poly(pts, _tone("dark", 0, False, tones), 1)
        rig.surf.set_clip(old)
        # the torch
        if prog < 1.0:
            wob = math.sin(t * 9.0) * 6 * rig.s
            rig.surf.set_clip(None)
            px = rig.p(0, 0)[0] + wob
            blit_glow(rig.surf, (px, cut), 7 * rig.s, (255, 236, 180), 110)
            for _ in range(4):                 # sparks off the bead
                sx = px + random.uniform(-9, 9) * rig.s
                sy = cut + random.uniform(-2, 11) * rig.s
                pygame.draw.line(rig.surf, (255, 206, 128), (sx, sy),
                                 (sx + random.uniform(-3, 3), sy + 4), 1)
        return
    for pts, tone in shapes:
        if tone == "hollow":                   # a bare frame, or bare ribs
            rig.poly(pts, _tone("main", dmg, wrecked, tones), 3)
            mid = sum(p[1] for p in pts) / len(pts)
            if tones is BIO_TONES:
                xs = [q[0] for q in pts]
                ys = [q[1] for q in pts]
                x0, x1 = min(xs), max(xs)
                y0, y1 = min(ys), max(ys)
                c = _tone("dark", dmg, wrecked, tones)
                for i in range(6):             # ribs, not cross braces
                    f = 0.12 + i * 0.152
                    x = lerp(x0, x1, f)
                    h = (y1 - y0) * (0.30 + 0.16 * math.sin(f * math.pi))
                    mid_y = (y0 + y1) * 0.5
                    rig.line((x, mid_y - h), (x - 6, mid_y + h), c, 3)
            else:
                rig.line((pts[0][0] + 6, mid - 26), (pts[1][0] - 6, mid + 26),
                         _tone("dark", dmg, wrecked, tones), 3)
                rig.line((pts[1][0] - 6, mid - 26), (pts[0][0] + 6, mid + 26),
                         _tone("dark", dmg, wrecked, tones), 3)
            continue
        rig.poly(pts, _tone(tone, dmg, wrecked, tones))
        rig.poly(pts, shade(_tone(tone, dmg, wrecked, tones), 0.6), 1)
    if wrecked:
        ys = [y for pts, _ in shapes for _, y in pts]
        xs = [x for pts, _ in shapes for x, _ in pts]
        cx, cy = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5
        for i in range(3):
            a = t * 0.6 + i * 2.1
            rig.line((cx - 14, cy + math.sin(a) * 10),
                     (cx + 14, cy + math.cos(a) * 10), (30, 28, 30), 3)


def draw_mech_front(surf, mech, cx, gy, scale, jobs=None, t=0.0, lit=True):
    """The whole machine as it stands in the gantry tonight."""
    rig = Rig(surf, cx, gy, scale)
    jobs = jobs or {}
    arm_t = {"l": mech.fit["l_arm"] or 1, "r": mech.fit["r_arm"] or 1}

    def state(socket):
        job = jobs.get(socket)
        if job is not None and mech.fit[socket] != job[0]:
            return ("job", job[0], job[1])
        if mech.fit[socket] is None:
            nxt = options_for(socket, None)
            if not nxt:
                return (None, None, 0.0)
            first = nxt[0]
            key = first.key if isinstance(first, Weapon) else first.tier
            return ("ghost", key, 0.0)
        return ("on", mech.fit[socket], 0.0)

    order = ("legs", "l_arm", "r_arm", "torso", "armour", "head",
             "reactor", "l_wpn", "r_wpn")
    for socket in order:
        mode, fit, prog = state(socket)
        if mode is None or fit is None:
            continue
        at = arm_t["l" if socket in ("l_arm", "l_wpn") else "r"] \
            if socket in ("l_arm", "r_arm", "l_wpn", "r_wpn") else 1
        dmg = mech.damage_frac(socket)
        if socket in ("l_wpn", "r_wpn"):
            # a weapon hangs off whatever arm is actually there, and goes
            # dark with it - a live gun on a dead arm is a lie
            side = "l" if socket == "l_wpn" else "r"
            arm = "l_arm" if side == "l" else "r_arm"
            if mech.fit[arm] is not None and mech.hp[arm] <= 0:
                dmg = max(dmg, 0.999)
            if mech.fit["l_arm" if side == "l" else "r_arm"] is None \
                    and mode != "job":
                continue
        draw_socket_front(rig, socket, fit, dmg, at, mode, prog, t)
    # the core light, which is the only thing on the machine that is alive
    if mech.alive("reactor") and lit:
        tier = mech.fit["reactor"]
        r = (11, 15, 19)[tier - 1]
        bio = CURRENT["house"] == "ryez"
        beat = abs(math.sin(t * 2.6)) ** 3.0
        pulse = (0.80 + 0.45 * beat) if bio else (0.86 + 0.14 * math.sin(t * 2.2))
        CORE_C = HEART if bio else CORE
        CX, CY = HEART_AT if bio else (0, -284)
        rig.circle((CX, CY), r * 0.95, (28, 14, 20) if bio else (18, 28, 34))
        rig.circle((CX, CY), r * 0.95, shade(CORE_C, 0.55), 1)
        rig.circle((CX, CY), r * 0.45 * pulse, CORE_C)
        rig.light((CX, CY), r * 1.1 * pulse, CORE_C, 34)
    if mech.alive("head") and lit:
        tier = mech.fit["head"]
        eye = (-356, -366, -370)[tier - 1]
        if CURRENT["house"] == "ryez":     # an eye on the side of a skull
            e, hs = head_eye(tier)
            rig.circle((e.x, e.y), hs * 0.20, (250, 232, 140))
            rig.circle((e.x, e.y), hs * 0.09, (24, 16, 18))
            rig.light((e.x, e.y), hs * 0.55, RYEZ_ACID, 55)
        else:
            rig.light((0, eye), 5, (255, 176, 96), 60)
            rig.circle((0, eye), 2.4, (255, 214, 150))



# ---------------------------------------------------------------------------
# DRAWING THE ANIMAL
#
# RYEZ's half of the game, and it is NOT the machine in a different colour.
# The nine sockets are the same nine sockets - a socket is a contract about
# what a part does, not about where it sits - but the thing they hang off
# is a low four-legged animal in profile: a trunk carried on two or three
# pairs of splayed legs, a neck and a head out in front, a tail behind, and
# a pair of forelimbs up near the throat where the organs grow.
#
# That means the pod view is a PROFILE and the gantry view is a front
# elevation, which is the right way round for each: a mech reads head-on
# and an animal reads side-on. All the machinery underneath survives it -
# an empty socket still ghosts the exact shape that goes there, a growing
# part still fills from the bottom, damage still tints per part - because
# none of that ever cared what the coordinates meant.
#
#   x = 0 is the middle of the trunk, +x is the way it is facing,
#   y = 0 is the ground, and up is negative. Same as everything else.
# ---------------------------------------------------------------------------
FLESH = (156, 104, 148)
FLESH_D = (96, 58, 96)
FLESH_L = (206, 156, 196)
CHITIN = (128, 150, 92)
HEART = (236, 108, 132)

TRUNK_BACK, TRUNK_FRONT = -74.0, 96.0
TRUNK_TOP, TRUNK_BELLY = -264.0, -150.0
LEG_ROOT_Y = -162.0
NECK_ROOT = (90.0, -242.0)
HEART_AT = (-8.0, -206.0)


def _t(v):
    return (v.x, v.y)


def _blob(cx, cy, rx, ry, n=16, lump=0.0, seed=0.0):
    """A closed organic outline. Nothing in here has a straight edge."""
    pts = []
    for i in range(n):
        a = i * TAU / n
        w = 1.0 + lump * math.sin(a * 3.0 + seed)
        pts.append((cx + rx * w * math.cos(a), cy + ry * w * math.sin(a)))
    return pts


def _taper(ax, ay, bx, by, wa, wb, bow=0.0):
    """A limb segment, fat at the joint and thin at the end, bowed out."""
    a, b = Vector2(ax, ay), Vector2(bx, by)
    d = unit(b - a)
    nrm = Vector2(-d.y, d.x)
    out = []
    n = 4
    for i in range(n + 1):
        f = i / n
        q = a + (b - a) * f
        w = lerp(wa, wb, f) + bow * math.sin(f * math.pi)
        out.append(((q + nrm * w).x, (q + nrm * w).y))
    for i in range(n, -1, -1):
        f = i / n
        q = a + (b - a) * f
        w = lerp(wa, wb, f) + bow * math.sin(f * math.pi)
        out.append(((q - nrm * w).x, (q - nrm * w).y))
    return out


def leg_xs(tier):
    """Where the pairs of legs come out of the belly. Two pairs or three -
    the count is the loudest thing about the silhouette, so it is the thing
    the tier changes."""
    return (66.0, -34.0) if tier == 1 else (72.0, 8.0, -58.0)


def leg_geom(tier):
    """(upper, lower, width, splay) for one leg of this tier."""
    return ((72.0, 96.0, 9.0, 0.40),
            (84.0, 108.0, 12.0, 0.46),
            (98.0, 122.0, 14.0, 0.54))[tier - 1]


def _one_leg(rx, tier, phase=0.0, moving=0.0, dx=0.0):
    """Two segments from the belly to the ground. Shared by the pod view
    and the fight, so a leg cannot look like two different legs."""
    up, low, w, splay = leg_geom(tier)
    splay *= 0.30 + rx / 84.0          # fore legs plant forward, hind back
    swing = math.sin(phase) * 0.38 * moving
    bend = 0.52 + max(0.0, -math.cos(phase)) * 0.42 * moving
    if rx < 0:
        bend *= 1.35                   # and the hind pair crouches
    root = Vector2(rx + dx, LEG_ROOT_Y)
    a1 = math.pi / 2 - splay + swing
    knee = root + Vector2(math.cos(a1), math.sin(a1)) * up
    a2 = a1 + bend
    foot = knee + Vector2(math.cos(a2), math.sin(a2)) * low
    if foot.y > -6:
        foot.y = -6
    return root, knee, foot, w


def bio_legs(tier, phase=0.0, moving=0.0, half=None):
    """`half` picks the far pair or the near pair, so the fight can put the
    trunk between them. The pod view asks for both and draws them flat."""
    out = []
    pairs = ((-16.0, "dark", 0.0), (14.0, "main", math.pi))
    if half == "far":
        pairs = pairs[:1]
    elif half == "near":
        pairs = pairs[1:]
    for dx, sh, off in pairs:
        for i, rx in enumerate(leg_xs(tier)):
            root, knee, foot, w = _one_leg(rx, tier, phase + off + i * 1.7,
                                           moving, dx=dx)
            out.append((_taper(root.x, root.y, knee.x, knee.y, w, w * 0.78,
                               w * 0.3), sh))
            out.append((_taper(knee.x, knee.y, foot.x, foot.y, w * 0.74,
                               w * 0.42, w * 0.2), sh))
            out.append((_blob(knee.x, knee.y, w + 2, w + 2, 9), "dark"))
            for k in (-1, 0, 1):               # a foot that grips the road
                out.append(([(foot.x, foot.y - 3),
                             (foot.x + (16 + k * 5) * (1 if k >= 0 else -0.7),
                              foot.y + 3 + abs(k)),
                             (foot.x, foot.y + 5)], "dark"))
    return out


def bio_torso(tier, wag=0.0):
    """Trunk and tail together, for the pod view."""
    return bio_tail(tier, wag) + bio_trunk(tier)


def bio_tail(tier, wag=0.0):
    """The tail belongs to the trunk, so a bare skeleton still has
    vertebrae hanging off the back of it."""
    cy = (TRUNK_TOP + TRUNK_BELLY) * 0.5
    ry = (TRUNK_BELLY - TRUNK_TOP) * 0.5
    grow = (0.86, 1.0, 1.12)[tier - 1]
    out = []
    seg = 6
    prev = Vector2(TRUNK_BACK + 8, cy + 6)
    for i in range(seg):
        f = (i + 1) / seg
        nxt = Vector2(TRUNK_BACK - 150.0 * f,
                      cy + 10 + 118.0 * f * f + wag * 26.0 * f * f)
        w = (ry * grow * 0.72) * (1.0 - f * 0.88)
        out.append((_taper(prev.x, prev.y, nxt.x, nxt.y,
                           max(2.0, w), max(1.5, w * 0.6)), "dark"))
        prev = nxt
    return out


def bio_trunk(tier):
    cx = (TRUNK_BACK + TRUNK_FRONT) * 0.5
    cy = (TRUNK_TOP + TRUNK_BELLY) * 0.5
    rx = (TRUNK_FRONT - TRUNK_BACK) * 0.5
    ry = (TRUNK_BELLY - TRUNK_TOP) * 0.5
    grow = (0.86, 1.0, 1.12)[tier - 1]
    body = _blob(cx, cy, rx * grow, ry * grow, 18, 0.10, 1.4)
    if tier == 1:                              # ribs, and you can see through
        return [(body, "hollow")]
    out = [(body, "main")]
    for i in range(5):                         # flank plates over the ribs
        f = 0.14 + i * 0.18
        x = lerp(TRUNK_BACK, TRUNK_FRONT, f)
        h = ry * grow * (0.62 - abs(f - 0.5) * 0.4)
        out.append((_blob(x, cy + 8, 13, h, 10, 0.12, x), "dark"))
    if tier == 3:                              # a heavier shoulder mass
        out.append((_blob(TRUNK_FRONT - 30, cy - 6, 28, ry * 0.62, 12, 0.12,
                          3.0), "dark"))
    return out


def _up_of(d):
    """The perpendicular of `d` that points UP the screen. Screen y grows
    downward, so the naive (-d.y, d.x) is the one pointing at the road, and
    building a skull off it puts the jaw on top."""
    n = Vector2(-d.y, d.x)
    return n if n.y < 0 else -n


def neck_head(tier, rear=0.0):
    """The neck as a chain and the skull on the end. `rear` lifts it, which
    is what a wind-up looks like on an animal."""
    reach = (50.0, 60.0, 70.0)[tier - 1]
    rise = (-0.42, -0.50, -0.56)[tier - 1] - rear * 0.5
    root = Vector2(*NECK_ROOT)
    tip = root + Vector2(math.cos(rise), math.sin(rise)) * reach
    return root, tip, (27.0, 33.0, 39.0)[tier - 1]


def bio_head(tier, rear=0.0):
    root, tip, hs = neck_head(tier, rear)
    d = unit(tip - root)
    nrm = _up_of(d)
    out = []
    seg = 4
    prev = root
    for i in range(seg):
        f = (i + 1) / seg
        q = root + (tip - root) * f
        out.append((_taper(prev.x, prev.y, q.x, q.y, hs * (0.86 - 0.16 * f),
                           hs * (0.86 - 0.16 * (f + 1 / seg))), "main"))
        prev = q
    hc = tip + d * hs * 0.5
    top = [hc + nrm * hs * 0.78 - d * hs * 0.55,
           hc - nrm * hs * 0.20 - d * hs * 0.62,
           hc - nrm * hs * 0.16 + d * hs * 1.35,
           hc + nrm * hs * 0.56 + d * hs * 0.95]
    jaw = [hc - nrm * hs * 0.18 - d * hs * 0.55,
           hc - nrm * hs * 0.78 - d * hs * 0.40,
           hc - nrm * hs * 0.62 + d * hs * 1.15,
           hc - nrm * hs * 0.16 + d * hs * 1.25]
    out.append(([_t(p) for p in top], "main"))
    out.append(([_t(p) for p in jaw], "dark"))
    for i in range(4):                         # teeth
        f = 0.15 + i * 0.28
        q = hc + d * hs * f * 1.4 - nrm * hs * 0.17
        out.append(([_t(q), _t(q - nrm * hs * 0.26 + d * 3),
                     _t(q + d * hs * 0.22)], "light"))
    if tier >= 2:                              # horns
        for k in (1, 0.45):
            b = hc + nrm * hs * 0.6 * k - d * hs * 0.25
            out.append(([_t(b), _t(b + nrm * hs * 1.5 * k - d * hs * 0.7),
                         _t(b + nrm * hs * 0.5 * k + d * hs * 0.2)], "dark"))
    if tier == 3:                              # a crest down the skull
        b = hc - d * hs * 0.5
        out.append(([_t(b + nrm * hs * 0.8),
                     _t(b + nrm * hs * 2.0 - d * hs * 0.1),
                     _t(b + nrm * hs * 0.9 + d * hs * 0.9)], "dark"))
    return out


def head_eye(tier, rear=0.0):
    root, tip, hs = neck_head(tier, rear)
    d = unit(tip - root)
    nrm = _up_of(d)
    return (tip + d * hs * 0.72 + nrm * hs * 0.34), hs


def bio_hand(tier, side, reach=0.0):
    """The tip of a forelimb, where an organ grows. `reach` throws it
    forward, which is what a strike looks like on something with claws."""
    up, low = ((52.0, 46.0), (62.0, 54.0), (74.0, 64.0))[tier - 1]
    dx = -12.0 if side == "l" else 10.0
    root = Vector2(TRUNK_FRONT - 18 + dx, TRUNK_BELLY - 34)
    a = math.sin(clamp(reach, 0.0, 1.0) * math.pi)
    a1 = 0.30 - a * 0.70
    elb = root + Vector2(math.cos(a1), math.sin(a1)) * up
    fore = a1 + 0.95 - a * 0.85
    hand = elb + Vector2(math.cos(fore), math.sin(fore)) * low
    return root, elb, hand


def bio_arm_posed(tier, side, reach=0.0):
    """The forelimb, optionally thrown forward into a strike."""
    root, elb, hand = bio_hand(tier, side, reach)
    w = (8.0, 11.0, 14.0)[tier - 1]
    sh = "dark" if side == "l" else "main"
    out = [(_taper(root.x, root.y, elb.x, elb.y, w, w * 0.82, w * 0.3), sh),
           (_taper(elb.x, elb.y, hand.x, hand.y, w * 0.8, w * 0.5,
                   w * 0.25), sh),
           (_blob(elb.x, elb.y, w + 2, w + 2, 9), "dark")]
    if tier >= 2:
        out.insert(0, (_blob(root.x, root.y - 4, w * 2.2, w * 1.6, 11, 0.12,
                             2.0), "dark"))
    if tier == 3:
        out.append((_blob((elb.x + hand.x) * 0.5, (elb.y + hand.y) * 0.5,
                          w * 1.5, w * 1.1, 10, 0.1, 5.0), "light"))
    return out


def bio_arm(tier, side):
    root, elb, hand = bio_hand(tier, side)
    w = (8.0, 11.0, 14.0)[tier - 1]
    sh = "dark" if side == "l" else "main"
    out = [(_taper(root.x, root.y, elb.x, elb.y, w, w * 0.82, w * 0.3), sh),
           (_taper(elb.x, elb.y, hand.x, hand.y, w * 0.8, w * 0.5,
                   w * 0.25), sh),
           (_blob(elb.x, elb.y, w + 2, w + 2, 9), "dark")]
    if tier >= 2:
        out.insert(0, (_blob(root.x, root.y - 4, w * 2.2, w * 1.6, 11, 0.12,
                             2.0), "dark"))
    if tier == 3:
        out.append((_blob((elb.x + hand.x) * 0.5, (elb.y + hand.y) * 0.5,
                          w * 1.5, w * 1.1, 10, 0.1, 5.0), "light"))
    return out


def bio_armour(tier):
    """Plate grown ALONG THE SPINE, which is where an animal keeps it."""
    out = []
    n = 6
    for i in range(n):
        f = i / (n - 1.0)
        x = lerp(TRUNK_BACK + 4, TRUNK_FRONT - 10, f)
        h = 16 + 20 * math.sin(f * math.pi)
        y = TRUNK_TOP + 10 - h * 0.15
        out.append(([(x - 15, y + 8), (x, y - h), (x + 15, y + 8),
                     (x + 9, y + 18), (x - 9, y + 18)], "plate"))
    if tier >= 2:                              # skirts down the flank
        for f in (0.26, 0.52, 0.78):
            x = lerp(TRUNK_BACK + 6, TRUNK_FRONT - 18, f)
            out.append(([(x - 19, -178), (x + 5, -184), (x + 20, -168),
                         (x + 13, -138), (x - 8, -134), (x - 20, -152)],
                        "plate"))
    if tier == 3:                              # a sail, and a tail club
        for i in range(5):                     # a ridge of spines, not a dome
            f = i / 4.0
            x = lerp(TRUNK_BACK + 16, TRUNK_FRONT - 36, f)
            h = 22 + 26 * math.sin(f * math.pi)
            out.append(([(x - 11, TRUNK_TOP + 2), (x + 2, TRUNK_TOP - h),
                         (x + 12, TRUNK_TOP + 2)], "plate"))
        out.append((_blob(-206, -92, 26, 22, 10, 0.18, 2.0), "plate"))
    return out


def bio_weapon(key, side, tier_arm):
    """The organs. Claws and rasps grow on the forelimb; anything that is
    thrown or sprayed grows on the BACK, because that is where a sac goes."""
    w = WEAPONS.get(key)
    if w is None:
        return []
    _, _, hand = bio_hand(tier_arm, side)
    hx, hy = hand.x, hand.y
    back_x = 18 + (18 if side == "r" else -34)
    back_y = TRUNK_TOP + 40
    if w.kind == "melee" and key in ("fist", "pile"):
        big = key == "pile"
        s = 17 if big else 13
        out = [(_blob(hx + 4, hy + 8, s, s * 0.9, 11, 0.14, 1.0), "dark")]
        for k in (-1, 0, 1):
            a = 0.55 + k * 0.42
            tipv = Vector2(hx + 4, hy + 8) + Vector2(math.cos(a),
                                                     math.sin(a)) * s * 2.4
            out.append((_taper(hx + 4, hy + 8, tipv.x, tipv.y, s * 0.30,
                               1.5), "light"))
        return out
    if w.kind == "melee":                      # a rasping tongue
        long = 58 if key == "ripper" else 48
        tipv = Vector2(hx + long * 0.86, hy + long * 0.5)
        out = [(_taper(hx, hy, tipv.x, tipv.y, 9, 5, 3), "main")]
        for i in range(6):
            f = 0.1 + i * 0.15
            q = Vector2(hx, hy) + (tipv - Vector2(hx, hy)) * f
            nrm = unit(tipv - Vector2(hx, hy))
            nrm = Vector2(-nrm.y, nrm.x)
            out.append(([_t(q + nrm * 7), _t(q + nrm * 15),
                         _t(q + nrm * 7 + unit(tipv - Vector2(hx, hy)) * 7)],
                        "light"))
            if key == "ripper":
                out.append(([_t(q - nrm * 7), _t(q - nrm * 15),
                             _t(q - nrm * 7 + unit(tipv - Vector2(hx, hy)) * 7)], "light"))
        return out
    if w.kind == "gun":                        # a quill battery on the back
        n = 7 if key == "revolver" else 4
        out = [(_blob(back_x, back_y - 14, 26, 17, 12, 0.15, 4.0), "dark")]
        for i in range(n):
            f = (i - (n - 1) / 2.0) / max(1.0, n - 1.0)
            a = -math.pi / 2 + f * 0.85
            base = Vector2(back_x, back_y - 20)
            tipv = base + Vector2(math.cos(a), math.sin(a)) * 40
            out.append((_taper(base.x, base.y, tipv.x, tipv.y, 3.4, 1.2),
                        "light"))
        return out
    if w.kind == "salvo":                      # sacs, clustered on the spine
        n = 6 if key == "swarm" else 4
        out = [(_blob(back_x, back_y - 12, 26, 17, 13, 0.16, 6.0), "dark")]
        for i in range(n):
            a = math.pi + i * math.pi / max(1, n - 1)
            q = Vector2(back_x, back_y - 12) + Vector2(math.cos(a) * 17,
                                                       math.sin(a) * 11)
            out.append((_blob(q.x, q.y, 7, 6.4, 10, 0.18, i), "light"))
        return out
    long = 44 if key == "sun" else 36          # a bile gland and a spout
    out = [(_blob(back_x, back_y - 18, 28, 20, 12, 0.18, 8.0), "dark")]
    base = Vector2(back_x + 16, back_y - 22)
    tipv = base + Vector2(0.94, -0.34) * long
    out.append((_taper(base.x, base.y, tipv.x, tipv.y, 8, 4, 2), "main"))
    for i in range(3):
        q = base + (tipv - base) * (0.3 + i * 0.26)
        out.append((_blob(q.x, q.y, 7, 5, 8, 0.2, i * 2.0), "light"))
    return out


def draw_beast_side(surf, mech, sx, gy, scale, t, pose, tones=None):
    """The animal in the street. Same shape functions as the pod view -
    they were authored in profile, so the fight gets them for nothing and
    only the moving parts are computed here."""
    tones = tones or BIO_TONES
    rig = Side(surf, sx, gy, scale, pose.face)

    def col(socket, base):
        if mech.fit[socket] is None:
            return None
        return _tone(base, mech.damage_frac(socket), mech.hp[socket] <= 0,
                     tones)

    def blit(shapes, socket):
        c = {}
        for pts, tn in shapes:
            if tn not in c:
                c[tn] = col(socket, "main" if tn == "hollow" else tn)
            if c[tn] is None:
                continue
            if tn == "hollow":
                rig.poly(pts, c[tn], 3)
            else:
                rig.poly(pts, c[tn])
                rig.poly(pts, shade(c[tn], 0.6), 1)

    tt = mech.fit["torso"]
    lt = mech.fit["legs"]
    rear = 0.0
    swing = max(pose.swing["l"], pose.swing["r"])
    if pose.brace:
        rear = -0.35
    elif swing > 0:
        rear = math.sin(swing * math.pi) * 0.9
    wag = math.sin(t * 2.2 + pose.walk * 0.5) * 0.9 * (0.4 + pose.moving)

    if tt:
        blit(bio_tail(tt, wag), "torso")
    if lt:
        blit(bio_legs(lt, pose.walk, pose.moving, "far"), "legs")
    if tt:
        blit(bio_trunk(tt), "torso")
    if mech.fit["armour"] is not None:
        blit(bio_armour(mech.fit["armour"]), "armour")
    if lt:
        blit(bio_legs(lt, pose.walk, pose.moving, "near"), "legs")
    else:
        # nothing to stand on: the trunk is down in the road
        rig.poly(_blob(10, -70, 120, 40, 14, 0.1, 2.0), (44, 34, 44))
    if mech.fit["head"] is not None:
        blit(bio_head(mech.fit["head"], rear), "head")
        if mech.alive("head"):
            e, hs = head_eye(mech.fit["head"], rear)
            rig.circle((e.x, e.y), hs * 0.20, (250, 232, 140))
            rig.circle((e.x, e.y), hs * 0.09, (24, 16, 18))
            rig.light((e.x, e.y), hs * 0.6, RYEZ_ACID, 60)
    for side in ("l", "r"):
        asock = "l_arm" if side == "l" else "r_arm"
        at = mech.fit[asock]
        if at is None:
            continue
        reach = pose.swing[side]
        blit(bio_arm_posed(at, side, reach), asock)
        wsock = "l_wpn" if side == "l" else "r_wpn"
        if mech.weapon(side) is not None:
            blit(bio_weapon(mech.fit[wsock], side, at), wsock)
    if mech.fit["reactor"] is not None:
        rt = mech.fit["reactor"]
        rr = (11, 15, 19)[rt - 1]
        alive = mech.alive("reactor")
        heat = mech.heat_frac
        c = HEART if alive else (70, 62, 66)
        c = mix(c, (255, 150, 90), heat * 0.8) if alive else c
        if alive:
            rr *= 1.0 + 0.24 * abs(math.sin(t * 2.6)) ** 3.0
        hx, hy = HEART_AT
        rig.circle((hx, hy), rr * 0.95, (30, 14, 20))
        rig.circle((hx, hy), rr * 0.95, shade(c, 0.55), 1)
        rig.circle((hx, hy), rr * 0.5, c)
        if alive:
            rig.light((hx, hy), rr * (1.2 + heat), c, 40 + heat * 60)
    if pose.brace and (mech.alive("l_arm") or mech.alive("r_arm")):
        rig.bar((TRUNK_FRONT + 26, TRUNK_TOP + 20),
                (TRUNK_FRONT + 34, TRUNK_BELLY - 6), 7, (210, 200, 230))
    if pose.flash > 0.01:
        blit_glow(surf, (sx, gy - 200 * scale), 150 * scale,
                  (255, 236, 220), int(150 * clamp(pose.flash, 0, 1)))


def beast_muzzle(mech, pose, side, sx, gy, scale):
    """Where a spine or a jet of bile leaves the animal."""
    wsock = "l_wpn" if side == "l" else "r_wpn"
    key = mech.fit[wsock]
    w = WEAPONS.get(key) if key else None
    if w is None:
        return None, Vector2(pose.face, 0)
    back_x = 18 + (18 if side == "r" else -34)
    back_y = TRUNK_TOP + 40
    local = Vector2(back_x + 30, back_y - 26)
    ang = pose.aim[side]
    rig = Side(None, sx, gy, scale, pose.face)
    return (Vector2(rig.p(local.x, local.y)),
            Vector2(math.cos(ang) * pose.face, math.sin(ang)))


BIO_SHAPE = {"legs": bio_legs, "torso": bio_torso, "head": bio_head,
             "armour": bio_armour}
BIO_TONES = {"main": FLESH, "dark": FLESH_D, "light": FLESH_L,
             "trim": RYEZ_ACID, "plate": CHITIN, "hollow": FLESH_L}


# ---------------------------------------------------------------------------
# DRAWING THE MACHINE - SIDE
#
# The fight view. Same build, same damage, different body: the gantry sees
# the machine head-on and the street sees it in profile, walking.
#
# Nothing here reads the catalogue for its shape - it reads the TIER, and
# the tier changes thicknesses and joint positions. That is deliberate: a
# tier-three leg has to look like a tier-three leg from both directions or
# the player cannot trust either picture.
# ---------------------------------------------------------------------------
class Pose:
    """Everything the fight knows about how the body is arranged."""

    def __init__(self):
        self.walk = 0.0            # gait phase
        self.moving = 0.0          # 0..1, how much of the gait to apply
        self.face = 1              # +1 looking out to sea, -1 looking home
        self.swing = {"l": 0.0, "r": 0.0}     # melee arc, 0..1
        self.recoil = {"l": 0.0, "r": 0.0}    # gun kick, 0..1
        self.beam = {"l": 0.0, "r": 0.0}      # beam held, 0..1
        self.aim = {"l": 0.06, "r": 0.06}     # where each hardpoint points
        self.brace = False
        self.flash = 0.0
        self.lean = 0.0


def limb(a, b, w1, w2=None):
    """A tapered bar between two points - every limb in the game is one."""
    w2 = w1 if w2 is None else w2
    a, b = Vector2(a), Vector2(b)
    d = unit(b - a)
    n = Vector2(-d.y, d.x)
    return [a + n * w1, b + n * w2, b - n * w2, a - n * w1]


class Side:
    """Profile coordinates onto the screen, with a facing built in."""

    def __init__(self, surf, x, gy, scale, face=1):
        self.surf = surf
        self.x = x
        self.gy = gy
        self.s = scale
        self.f = face

    def p(self, x, y):
        return (self.x + x * self.s * self.f, self.gy + y * self.s)

    def poly(self, pts, colour, width=0):
        pygame.draw.polygon(self.surf, colour, [self.p(*q) for q in pts],
                            width)

    def bar(self, a, b, w1, colour, w2=None, edge=None):
        q = limb(a, b, w1, w2)
        self.poly(q, colour)
        if edge:
            self.poly(q, edge, 1)

    def circle(self, c, r, colour, width=0):
        pygame.draw.circle(self.surf, colour, self.p(*c),
                           max(1, r * self.s),
                           0 if not width else max(1, int(width * self.s)))

    def light(self, c, r, colour, strength=110):
        blit_glow(self.surf, self.p(*c), r * self.s, colour, strength)


# joint heights, by leg tier
LEG_GEOM = {1: (196, 78, 76, 8, 9, 20),
            2: (204, 82, 80, 11, 12, 25),
            3: (216, 88, 86, 13, 14, 30)}
#            hip  thigh shin  w1  w2  foot


def _leg_points(tier, phase, moving):
    """Forward kinematics for one leg. Screen space: +y is down."""
    hip_y, L1, L2, _, _, _ = LEG_GEOM[tier]
    swing = math.sin(phase) * 0.46 * moving
    bend = max(0.0, -math.cos(phase)) * 0.62 * moving
    hip = Vector2(0.0, -hip_y)
    a1 = math.pi / 2 + swing
    knee = hip + Vector2(math.cos(a1), math.sin(a1)) * L1
    a2 = a1 - bend
    ankle = knee + Vector2(math.cos(a2), math.sin(a2)) * L2
    # the machine does not sink into the road
    if ankle.y > -12:
        ankle.y = -12
    return hip, knee, ankle


def draw_mech_side(surf, mech, sx, gy, scale, t, pose, alpha_dead=False,
                   tones=None, bio=None):
    """`tones` repaints the whole machine - that is how a KEAL model is
    drawn by the same routine that draws yours, in its own livery."""
    if bio is None:
        bio = tones is None and CURRENT["house"] == "ryez"
    if bio:
        draw_beast_side(surf, mech, sx, gy, scale, t, pose,
                        tones if tones is not BIO_TONES else None)
        return
    rig = Side(surf, sx, gy, scale, pose.face)
    lean = pose.lean

    def tone(socket, base):
        if mech.fit[socket] is None:
            return None
        return _tone(base, mech.damage_frac(socket), mech.hp[socket] <= 0,
                     tones)

    legs_t = mech.fit["legs"]
    hip_y = LEG_GEOM[legs_t][0] if legs_t else 190

    # -- legs, far one first so the near one reads in front ---------------
    if legs_t:
        _, _, _, w1, w2, fw = LEG_GEOM[legs_t]
        main = tone("legs", "main")
        dark = tone("legs", "dark")
        for i, (dx, sh) in enumerate(((-13, 0.62), (11, 1.0))):
            hip, knee, ankle = _leg_points(legs_t, pose.walk + i * math.pi,
                                           pose.moving)
            c = shade(main, sh)
            cd = shade(dark, sh)
            rig.bar((hip.x + dx, hip.y), (knee.x + dx, knee.y), w1, c, w2 - 1,
                    shade(c, 0.6))
            rig.bar((knee.x + dx, knee.y), (ankle.x + dx, ankle.y), w2 - 1, c,
                    w2 - 2, shade(c, 0.6))
            rig.circle((knee.x + dx, knee.y), w1 + 1, cd)
            rig.poly([(ankle.x + dx - fw * 0.35, ankle.y),
                      (ankle.x + dx + fw * 0.75, ankle.y),
                      (ankle.x + dx + fw * 0.68, ankle.y + 13),
                      (ankle.x + dx - fw * 0.4, ankle.y + 13)], cd)
    else:
        # no legs at all: the frame is on a cradle and is not going anywhere
        pygame.draw.polygon(surf, (44, 48, 60),
                            [rig.p(-44, -hip_y + 10), rig.p(44, -hip_y + 10),
                             rig.p(62, -6), rig.p(-62, -6)])

    # -- torso -------------------------------------------------------------
    tt = mech.fit["torso"] or 1
    body_top = -336 if tt == 3 else (-330 if tt == 2 else -324)
    back = -34 - (6 if tt == 3 else 0)
    front = 30 + (8 if tt >= 2 else 0)
    body = [(back + lean, -hip_y + 4), (front + lean, -hip_y - 2),
            (front + 6 + lean * 1.4, body_top + 40),
            (front - 4 + lean * 1.6, body_top),
            (back + 6 + lean * 1.4, body_top - 2),
            (back - 8 + lean, -hip_y - 60)]
    if bio:
        bx = (back + front) * 0.5 + lean * 1.2
        by = (-hip_y + body_top) * 0.5 - 8
        brx = (front - back) * 0.66
        bry = (-hip_y - body_top) * 0.5 + 18
        body = [(bx + brx * math.cos(a) * (1.0 + 0.12 * math.sin(a * 3.0)),
                 by + bry * math.sin(a))
                for a in (i * TAU / 18 for i in range(18))]
    tc = tone("torso", "main") or STEEL
    if tt == 1:
        rig.poly(body, tc, 3)
        rig.bar((back + 4, -hip_y - 10), (front, body_top + 30), 3, tc)
        rig.bar((front - 2, -hip_y - 8), (back + 8, body_top + 26), 3, tc)
    elif bio:
        rig.poly(body, tc)
        rig.poly(body, shade(tc, 0.62), 2)
        for i in range(4):                     # ribs down the flank
            f = 0.2 + i * 0.2
            x = lerp(back, front, f)
            rig.bar((x, body_top + 26), (x - 6, -hip_y - 16), 3.4,
                    shade(tc, 0.78))
    else:
        rig.poly(body, tc)
        rig.poly(body, shade(tc, 0.62), 1)
        rig.poly([(back + 8, body_top + 8), (front - 2, body_top + 4),
                  (front - 6, body_top + 30), (back + 12, body_top + 34)],
                 shade(tc, 1.18))

    # -- plate -------------------------------------------------------------
    if mech.fit["armour"] is not None:
        ac = tone("armour", "plate")
        at = mech.fit["armour"]
        rig.poly([(front - 4 + lean, body_top + 26), (front + 12 + lean,
                                                      body_top + 34),
                  (front + 8 + lean, -hip_y - 34), (front - 10 + lean,
                                                    -hip_y - 30)], ac)
        if at >= 2:
            rig.poly([(back - 6, -hip_y - 54), (back + 12, -hip_y - 58),
                      (back + 8, -hip_y - 6), (back - 10, -hip_y - 2)],
                     shade(ac, 0.84))
        if at == 3:
            rig.poly([(back + 2, body_top + 6), (front + 4, body_top + 2),
                      (front + 2, body_top + 22), (back, body_top + 26)],
                     shade(ac, 1.1))

    # -- head --------------------------------------------------------------
    if mech.fit["head"] is not None:
        ht = mech.fit["head"]
        hc = tone("head", "main")
        hw = (17, 21, 23)[ht - 1]
        hh = (30, 40, 46)[ht - 1]
        hx = front - 12 + lean * 1.8
        hy = body_top
        rig.poly([(hx - hw, hy), (hx + hw, hy - 2),
                  (hx + hw - 3, hy - hh), (hx - hw + 2, hy - hh + 2)], hc)
        rig.poly([(hx - hw, hy), (hx + hw, hy - 2),
                  (hx + hw - 3, hy - hh), (hx - hw + 2, hy - hh + 2)],
                 shade(hc, 0.6), 1)
        if ht == 3:
            rig.poly([(hx - hw - 2, hy - hh + 4), (hx - hw - 16, hy - hh - 12),
                      (hx - hw - 4, hy - hh - 2)], shade(hc, 0.72))
        if mech.alive("head"):
            ex = hx + hw - 5
            ey = hy - hh * 0.62
            if bio:
                for k in range(3):
                    rig.circle((ex - k * 5, ey + k * 4 - 4), 2.4,
                               (250, 232, 140))
                rig.light((ex - 4, ey), 9, RYEZ_ACID, 60)
            else:
                rig.circle((ex, ey), 3.0, (255, 206, 150))
                rig.light((ex, ey), 7, (255, 176, 96), 70)

    # -- reactor -----------------------------------------------------------
    if mech.fit["reactor"] is not None:
        rt = mech.fit["reactor"]
        rr = (9, 12, 15)[rt - 1]
        rx, ry = back + 22 + lean, body_top + 58
        alive = mech.alive("reactor")
        col = (HEART if bio else CORE) if alive else (70, 70, 78)
        heat = mech.heat_frac
        col = mix(col, (255, 128, 64), heat * 0.85) if alive else col
        if bio and alive:
            rr *= 1.0 + 0.22 * abs(math.sin(t * 2.6)) ** 3.0
        rig.circle((rx, ry), rr, (16, 24, 30))
        rig.circle((rx, ry), rr, shade(col, 0.6), 1.2)
        rig.circle((rx, ry), rr * 0.5, col)
        if alive:
            rig.light((rx, ry), rr * (1.2 + heat * 0.9), col, 40 + heat * 60)

    # -- arms and what is bolted to them ----------------------------------
    for side, depth in (("l", 0.62), ("r", 1.0)):
        asock = "l_arm" if side == "l" else "r_arm"
        at = mech.fit[asock]
        if at is None:
            continue
        ac = shade(tone(asock, "main"), depth)
        w = (8, 11, 13)[at - 1]
        # the far arm sits back and low, or the two of them read as one
        near = side == "r"
        sh = Vector2(back + (22 if near else 8) + lean * 1.3,
                     body_top + (24 if near else 34))
        wpn = mech.weapon(side)
        swing = pose.swing[side]
        recoil = pose.recoil[side]
        if pose.brace:
            ang, fore = -0.35, -0.55
        elif wpn is None:
            ang, fore = 1.05, 0.9
        elif wpn.kind == "melee":
            # the arc: back over the shoulder, then down and through
            a = math.sin(swing * math.pi) if swing > 0 else 0.0
            ang = lerp(0.72, -1.15, swing) - a * 0.25
            fore = lerp(0.62, -0.18, swing)
        else:
            ang = pose.aim[side] + recoil * 0.22
            fore = -0.02 - recoil * 0.1
        L1, L2 = 54.0, 52.0
        elbow = sh + Vector2(math.cos(ang), math.sin(ang)) * L1
        hand = elbow + Vector2(math.cos(ang + fore),
                               math.sin(ang + fore)) * L2
        if wpn is not None and wpn.kind in ("gun", "salvo", "beam"):
            hand -= unit(hand - elbow) * recoil * 11.0
        rig.bar((sh.x, sh.y), (elbow.x, elbow.y), w, ac, w - 1, shade(ac, 0.6))
        rig.bar((elbow.x, elbow.y), (hand.x, hand.y), w - 1, ac, w - 2,
                shade(ac, 0.6))
        rig.circle((elbow.x, elbow.y), w + 1, shade(ac, 0.72))
        if at >= 2:
            rig.circle((sh.x, sh.y), w + 5, shade(ac, 0.8))
        if wpn is not None:
            draw_weapon_side(rig, wpn, hand, unit(hand - elbow),
                             shade(tone("l_wpn" if side == "l" else "r_wpn",
                                        "main") or ac, depth),
                             pose, side)

    if pose.brace and mech.alive("l_arm") or pose.brace and mech.alive("r_arm"):
        # the guard: whatever arms are left, held across the front
        gx = front + 18 + lean
        pygame.draw.line(surf, (200, 214, 240),
                         rig.p(gx, body_top + 16), rig.p(gx, -hip_y - 10),
                         max(2, int(4 * scale)))
    if pose.flash > 0.01:
        # the hit reads as a flare over the hull, not a white box on it
        f = clamp(pose.flash, 0, 1)
        blit_glow(surf, (sx, gy - 230 * scale), 150 * scale,
                  (255, 236, 220), int(150 * f))


def weapon_muzzle(mech, pose, side, sx, gy, scale):
    """Where a shot comes out, in screen coordinates. The fight needs this
    and the drawing needs this, so neither one owns it."""
    if CURRENT["house"] == "ryez":
        return beast_muzzle(mech, pose, side, sx, gy, scale)
    asock = "l_arm" if side == "l" else "r_arm"
    at = mech.fit[asock]
    wpn = mech.weapon(side)
    if at is None or wpn is None:
        return None, Vector2(pose.face, 0)
    tt = mech.fit["torso"] or 1
    body_top = -336 if tt == 3 else (-330 if tt == 2 else -324)
    back = -34 - (6 if tt == 3 else 0)
    near = side == "r"
    sh = Vector2(back + (22 if near else 8) + pose.lean * 1.3,
                 body_top + (24 if near else 34))
    ang = pose.aim[side] + pose.recoil[side] * 0.22
    fore = -0.02 - pose.recoil[side] * 0.1
    elbow = sh + Vector2(math.cos(ang), math.sin(ang)) * 54.0
    hand = elbow + Vector2(math.cos(ang + fore), math.sin(ang + fore)) * 52.0
    d = unit(hand - elbow)
    tip = hand + d * (WEAPON_LEN.get(wpn.key, 40))
    rig = Side(None, sx, gy, scale, pose.face)
    return (Vector2(rig.p(tip.x, tip.y)),
            Vector2(d.x * pose.face, d.y))


WEAPON_LEN = {"fist": 24, "pile": 34, "saw": 44, "ripper": 50,
              "auto": 58, "revolver": 66, "missile": 30, "swarm": 34,
              "lance": 62, "sun": 72}


def draw_weapon_side(rig, w, hand, d, colour, pose, side):
    """A weapon in profile, pointing the way the forearm does."""
    n = Vector2(-d.y, d.x)
    L = WEAPON_LEN.get(w.key, 40)
    tip = hand + d * L
    if w.kind == "melee" and w.key in ("fist", "pile"):
        s = 15 if w.key == "pile" else 12
        rig.poly([hand + n * s - d * 4, hand - n * s - d * 4,
                  tip - n * (s - 2), tip + n * (s - 2)], colour)
        rig.poly([hand + n * s - d * 4, hand - n * s - d * 4,
                  tip - n * (s - 2), tip + n * (s - 2)], shade(colour, 0.6), 1)
        if w.key == "pile":
            ext = pose.swing[side]
            pt = tip + d * (6 + 26 * ext)
            rig.bar((tip.x, tip.y), (pt.x, pt.y), 5, shade(colour, 1.2))
    elif w.kind == "melee":
        rig.poly([hand + n * 8, hand - n * 8, tip - n * 6, tip + n * 6],
                 colour)
        teeth = 7
        spin = (pose.swing[side] * 9.0) % 1.0
        for i in range(teeth):
            f = (i / teeth + spin) % 1.0
            q = hand + d * (L * f)
            rig.poly([q + n * 7, q + n * 13, q + n * 7 + d * 6], STEEL_L)
            rig.poly([q - n * 7, q - n * 13, q - n * 7 + d * 6], STEEL_L)
    elif w.kind == "gun":
        rig.poly([hand + n * 10 - d * 8, hand - n * 10 - d * 8,
                  hand - n * 9 + d * 16, hand + n * 9 + d * 16],
                 shade(colour, 0.78))
        rig.bar((hand.x + d.x * 14, hand.y + d.y * 14), (tip.x, tip.y), 4.5,
                colour, 3.6, shade(colour, 0.6))
        if w.key == "revolver":
            rig.circle((hand.x + d.x * 10, hand.y + d.y * 10), 11,
                       shade(colour, 0.9))
        if pose.recoil[side] > 0.25:
            rig.light((tip.x, tip.y), 13 * pose.recoil[side],
                      (255, 214, 140), 150)
    elif w.kind == "salvo":
        rows = 3 if w.key == "swarm" else 2
        rig.poly([hand + n * (7 * rows) - d * 12, hand - n * (7 * rows) - d * 12,
                  hand - n * (7 * rows) + d * L, hand + n * (7 * rows) + d * L],
                 shade(colour, 0.8))
        for i in range(rows * 2):
            off = (i - (rows * 2 - 1) / 2.0) * 7.0
            q = hand + n * off + d * (L - 3)
            rig.circle((q.x, q.y), 3.0, shade(colour, 1.25))
    else:                                       # beam
        rig.poly([hand + n * 11 - d * 10, hand - n * 11 - d * 10,
                  hand - n * 8 + d * 20, hand + n * 8 + d * 20],
                 shade(colour, 0.76))
        rig.bar((hand.x + d.x * 18, hand.y + d.y * 18), (tip.x, tip.y), 5.5,
                colour, 4.0, shade(colour, 0.6))
        for i in range(3):
            q = hand + d * (26 + i * 12)
            rig.poly([q + n * 9, q - n * 9, q - n * 9 + d * 3,
                      q + n * 9 + d * 3], shade(colour, 1.2))
        held = pose.beam[side]
        if held > 0.02:
            rig.light((tip.x, tip.y), 12 * held, (180, 230, 255), 170)


# ---------------------------------------------------------------------------
# THE THINGS THAT COME OUT OF THE SEA
#
# One body, eight knobs, six animals. The knobs were chosen so that each
# one changes the OUTLINE and not just the size or the colour: three low
# legs is a different shape from one tall pair however you paint it, and a
# sail down the spine cannot be mistaken for a shell over it.
#
# That is not a style note. A roster where every monster is one trapezoid
# in a different colour is the commonest way a bestiary goes wrong, and it
# passes every test that only asks whether something was drawn.
# ---------------------------------------------------------------------------
POISE = {"spitter": 1.1, "bulwark": 1.7, "strider": 1.25, "brood": 1.8,
         "leviathan": 2.6}


class Kind:
    __slots__ = ("key", "name", "title", "hide", "dark", "scale", "hp",
                 "speed", "dr", "attacks", "scrap", "alloy", "wreck",
                 "rampage", "body", "note", "poise", "family", "build",
                 "rig", "minion")

    def __init__(self, key, name, title, hide, scale, hp, speed, dr,
                 attacks, scrap, alloy, wreck, rampage, body, note):
        self.key = key
        self.name = name
        self.title = title
        self.hide = hide
        self.dark = shade(hide, 0.58)
        self.scale = scale
        self.hp = hp
        self.speed = speed
        self.dr = dr
        self.attacks = attacks
        self.scrap = scrap
        self.alloy = alloy
        self.wreck = wreck          # city points per second once it is past
        self.rampage = rampage      # city points if it puts the mech down
        self.body = body
        self.note = note
        self.poise = POISE.get(key, 1.0)
        self.family = "bio"         # "mech" for a KEAL model
        self.build = None           # the loadout a KEAL model is drawn from
        self.rig = None             # and the Mech built out of it
        self.minion = None          # what its spawn attack puts down


def atk(kind, reach, windup, dmg, cool, **kw):
    d = {"kind": kind, "reach": reach, "windup": windup, "dmg": dmg,
         "cool": cool}
    d.update(kw)
    return d


# body = (half-length, half-height, centre height, leg pairs, leg length,
#         neck, neck angle, head size, head kind, crest, tail, arms, sac)
BESTIARY = [
    Kind("crawler", "CRAWLER", "the first one", (96, 130, 84), 0.78,
         820, 76, 0,
         [atk("swipe", 236, 0.55, 45, 1.6)],
         330, 2, 2.0, 10,
         (78, 30, -96, 3, 96, 26, -0.25, 22, 1, 0, 70, 0, 0),
         "Low, quick, and no bigger than a warehouse. They said it was a "
         "one-off."),
    Kind("spitter", "SPITTER", "it does not have to reach you", (176, 152, 48),
         0.86, 2400, 64, 2,
         [atk("swipe", 244, 0.60, 42, 1.8, lunge=1),
          atk("spit", 1100, 0.95, 64, 3.0, speed=560, arc=1)],
         470, 3, 2.4, 14,
         (86, 36, -120, 2, 128, 74, -0.60, 26, 3, 1, 110, 0, 0),
         "Throws a bolt of something that eats plate. Keep moving and it "
         "lands where you were."),
    Kind("bulwark", "BULWARK", "hit it until it stops", (104, 104, 124),
         0.96, 4700, 42, 6,
         [atk("swipe", 262, 0.50, 60, 2.0),
          atk("slam", 314, 0.95, 122, 2.8, shake=1, lunge=1)],
         650, 4, 2.8, 17,
         (98, 54, -96, 2, 92, 16, -0.10, 34, 0, 2, 50, 0, 0),
         "Armoured like a hill. Small guns bounce; bring something that "
         "arrives all at once."),
    Kind("strider", "STRIDER", "it is not interested in you", (186, 96, 64),
         1.04, 6400, 100, 3,
         [atk("kick", 292, 0.50, 80, 1.7, lunge=1),
          atk("leap", 900, 0.90, 118, 5.2, over=1)],
         820, 5, 3.0, 20,
         (62, 34, -212, 1, 220, 92, -0.75, 26, 2, 0, 150, 1, 0),
         "Long legs and somewhere to be. It will go over you to get there."),
    Kind("brood", "BROODMOTHER", "she does not come alone", (146, 78, 142),
         1.04, 8500, 54, 4,
         [atk("swipe", 284, 0.65, 76, 2.0, lunge=1),
          atk("spit", 1000, 0.95, 62, 3.4, speed=520, arc=1),
          atk("spawn", 0, 1.40, 0, 13.0, brood=2)],
        1020, 6, 3.6, 24,
         (104, 54, -128, 3, 132, 56, -0.45, 30, 3, 2, 130, 1, 1),
         "The sac on her back is full. Splash damage is not a luxury "
         "tonight."),
    Kind("leviathan", "LEVIATHAN", "the last one", (58, 96, 150), 1.22,
        13000, 48, 8,
         [atk("swipe", 336, 0.70, 124, 2.2, lunge=1),
          atk("slam", 364, 1.20, 178, 4.6, shake=1, lunge=1),
          atk("beam", 1700, 1.45, 50, 6.0, hold=1.9),
          atk("roar", 0, 0.90, 0, 11.0, stun=1)],
         0, 0, 4.8, 34,
         (118, 62, -246, 2, 250, 86, -0.62, 40, 2, 2, 190, 1, 0),
         "Everything the others were, at once, and it has been waiting for "
         "the rest to soften us up."),
]
KINDS = {k.key: k for k in BESTIARY}

BROODLING = Kind("broodling", "BROODLING", "", (176, 116, 170), 0.32,
                 230, 128, 0,
                 [atk("swipe", 150, 0.40, 26, 1.4)],
                 0, 0, 0.3, 0,
                 (60, 24, -80, 3, 74, 20, -0.2, 16, 1, 0, 52, 0, 0),
                 "")


def _leg_chain(root, length, phase, moving, lean=0.0):
    """Two-segment leg, splayed out and down. Same maths as the mech's."""
    L1 = length * 0.52
    L2 = length * 0.52
    swing = math.sin(phase) * 0.40 * moving
    bend = 0.55 + max(0.0, -math.cos(phase)) * 0.45 * moving
    a1 = math.pi / 2 - 0.55 + swing + lean
    knee = Vector2(root) + Vector2(math.cos(a1), math.sin(a1)) * L1
    a2 = a1 + bend
    foot = knee + Vector2(math.cos(a2), math.sin(a2)) * L2
    if foot.y > -6:
        foot.y = -6
    return Vector2(root), knee, foot


def draw_kaiju(surf, kind, sx, gy, scale, t, walk=0.0, moving=1.0, face=-1,
               windup=0.0, hurt=0.0, dead=0.0, open_maw=0.0):
    """One animal, in profile, walking. `face` -1 means it is heading home."""
    (bl, bh, cy, pairs, leg, neck, neck_a, head, hkind, crest, tail,
     arms, sac) = kind.body
    rig = Side(surf, sx, gy, scale * kind.scale, face)
    hide = kind.hide
    if hurt > 0.01:
        hide = mix(hide, (255, 230, 220), clamp(hurt, 0, 1) * 0.8)
    if dead > 0.01:
        hide = mix(hide, (46, 44, 48), clamp(dead, 0, 1))
    dark = shade(hide, 0.58)
    mid = shade(hide, 0.8)
    lo = cy + bh * 0.2
    breathe = math.sin(t * 2.0) * 2.5 + windup * -8.0
    cy = cy + breathe * 0.4

    # -- tail, drawn first so it sits behind everything -------------------
    if tail > 4:
        seg = 7
        prev = Vector2(-bl + 6, cy + 4)
        for i in range(seg):
            f = (i + 1) / seg
            wag = math.sin(t * 2.4 - f * 2.6) * 14 * f
            nxt = Vector2(-bl - tail * f, cy + 10 * f + wag)
            rig.bar((prev.x, prev.y), (nxt.x, nxt.y),
                    max(2.0, bh * 0.72 * (1 - f * 0.86)), dark,
                    max(1.5, bh * 0.72 * (1 - (f + 1 / seg) * 0.86)))
            prev = nxt

    # -- the far legs -----------------------------------------------------
    for depth, shading, dx in ((0, 0.55, -10), (1, 1.0, 10)):
        for i in range(pairs):
            f = (i / max(1, pairs - 1)) if pairs > 1 else 0.5
            rx = lerp(-bl * 0.6, bl * 0.72, f)
            ph = walk + i * 1.9 + depth * math.pi
            root, knee, foot = _leg_chain((rx + dx, cy + bh * 0.5), leg, ph,
                                          moving)
            c = shade(hide, shading * 0.82)
            rig.bar((root.x, root.y), (knee.x, knee.y), leg * 0.11, c,
                    leg * 0.085)
            rig.bar((knee.x, knee.y), (foot.x, foot.y), leg * 0.085, c,
                    leg * 0.05)
            # a foot that grips
            for k in (-1, 0, 1):
                rig.poly([(foot.x, foot.y - 3),
                          (foot.x + 16 * (1 if k >= 0 else -1) * 0.7,
                           foot.y + 2 + k),
                          (foot.x, foot.y + 4)], shade(c, 0.7))
        if depth == 0:
            # -- the body, between the far legs and the near ones ---------
            body = []
            for i in range(14):
                a = i / 14 * TAU
                rx = bl * math.cos(a)
                ry = bh * math.sin(a)
                if sac and rx < -bl * 0.1:      # the egg sac swells the rear
                    ry *= 1.5
                    rx *= 1.18
                if math.sin(a) < 0:
                    ry *= 0.86
                body.append((rx, cy + ry))
            rig.poly(body, hide)
            rig.poly(body, dark, 2)
            # flank plates
            for i in range(4):
                fx = lerp(-bl * 0.5, bl * 0.55, i / 3.0)
                rig.poly([(fx - 9, cy - 2), (fx + 9, cy + 1),
                          (fx + 7, cy + bh * 0.62), (fx - 8, cy + bh * 0.6)],
                         mid)
            if sac:
                rig.circle((-bl * 0.72, cy + 6), bh * 0.66,
                           mix(hide, (250, 220, 120), 0.45))
                rig.circle((-bl * 0.72, cy + 6), bh * 0.66, dark, 2)
            # -- crest ------------------------------------------------------
            if crest == 1:                      # a row of spines
                for i in range(7):
                    f = i / 6.0
                    x = lerp(-bl * 0.8, bl * 0.7, f)
                    h = 18 + 16 * math.sin(f * math.pi)
                    rig.poly([(x - 7, cy - bh * 0.82), (x, cy - bh - h),
                              (x + 7, cy - bh * 0.82)], dark)
            elif crest == 2 and sac == 0 and kind.key == "bulwark":
                rig.poly([(-bl * 0.9, cy - bh * 0.5), (-bl * 0.4, cy - bh * 1.5),
                          (bl * 0.5, cy - bh * 1.5), (bl * 0.86, cy - bh * 0.4),
                          (bl * 0.8, cy + bh * 0.2), (-bl * 0.86, cy + bh * 0.2)],
                         mid)                   # one shell over the back
                rig.poly([(-bl * 0.9, cy - bh * 0.5), (-bl * 0.4, cy - bh * 1.5),
                          (bl * 0.5, cy - bh * 1.5), (bl * 0.86, cy - bh * 0.4),
                          (bl * 0.8, cy + bh * 0.2), (-bl * 0.86, cy + bh * 0.2)],
                         dark, 3)
                for i in range(4):
                    x = lerp(-bl * 0.7, bl * 0.6, i / 3.0)
                    rig.poly([(x - 10, cy - bh * 1.42), (x, cy - bh * 2.1),
                              (x + 10, cy - bh * 1.42)], dark)
            elif crest == 2:                    # a sail
                pts = [(-bl * 0.86, cy - bh * 0.8)]
                for i in range(6):
                    f = i / 5.0
                    x = lerp(-bl * 0.8, bl * 0.66, f)
                    pts.append((x, cy - bh - (34 + 52 * math.sin(f * math.pi))))
                pts.append((bl * 0.66, cy - bh * 0.8))
                rig.poly(pts, mid)
                rig.poly(pts, dark, 2)

    # -- neck and head ----------------------------------------------------
    nroot = Vector2(bl * 0.82, cy - bh * 0.3)
    a = neck_a + math.sin(t * 1.6) * 0.06 - windup * 0.35
    ntip = nroot + Vector2(math.cos(a), math.sin(a)) * neck
    if neck > 8:
        segn = 4
        prev = nroot
        for i in range(segn):
            f = (i + 1) / segn
            q = nroot + (ntip - nroot) * f
            rig.bar((prev.x, prev.y), (q.x, q.y), head * (0.72 - 0.16 * f),
                    hide, head * (0.72 - 0.16 * (f + 1 / segn)), dark)
            prev = q
    hd = unit(ntip - nroot) if neck > 8 else Vector2(1, -0.15)
    hn = Vector2(-hd.y, hd.x)
    hc = ntip + hd * head * 0.4
    maw = open_maw * 0.5
    if hkind == 0:                              # blunt, armoured
        rig.poly([hc + hn * head * 0.8 - hd * head * 0.5,
                  hc - hn * head * 0.8 - hd * head * 0.5,
                  hc - hn * head * 0.55 + hd * head * 1.15,
                  hc + hn * head * 0.6 + hd * head * 1.1], hide)
        rig.poly([hc + hn * head * 0.8 - hd * head * 0.5,
                  hc - hn * head * 0.8 - hd * head * 0.5,
                  hc - hn * head * 0.55 + hd * head * 1.15,
                  hc + hn * head * 0.6 + hd * head * 1.1], dark, 2)
    elif hkind == 1:                            # beaked
        rig.poly([hc + hn * head * 0.7 - hd * head * 0.4,
                  hc - hn * head * 0.7 - hd * head * 0.4,
                  hc + hd * head * 1.5], hide)
        rig.poly([hc + hn * head * 0.7 - hd * head * 0.4,
                  hc - hn * head * 0.7 - hd * head * 0.4,
                  hc + hd * head * 1.5], dark, 2)
    elif hkind == 2:                            # crowned
        rig.poly([hc + hn * head * 0.78 - hd * head * 0.5,
                  hc - hn * head * 0.72 - hd * head * 0.5,
                  hc - hn * head * 0.45 + hd * head * 1.3,
                  hc + hn * head * 0.5 + hd * head * 1.2], hide)
        for k in (-1, 1):                    # a pair of horns
            base = hc + hn * head * 0.6 * k - hd * head * 0.2
            rig.poly([base, base + hn * head * 1.5 * k - hd * head * 0.55,
                      base + hn * head * 0.5 * k + hd * head * 0.2], dark)
        rig.poly([hc + hn * head * 0.78 - hd * head * 0.5,
                  hc - hn * head * 0.72 - hd * head * 0.5,
                  hc - hn * head * 0.45 + hd * head * 1.3,
                  hc + hn * head * 0.5 + hd * head * 1.2], dark, 2)
    else:                                       # a maw that opens
        top = [hc + hn * head * 0.7 - hd * head * 0.45,
               hc - hn * head * 0.1 - hd * head * 0.5,
               hc - hn * head * 0.1 + hd * head * 1.35,
               hc + hn * head * 0.55 + hd * head * 0.9]
        bot = [hc - hn * head * (0.1 - maw) - hd * head * 0.5,
               hc - hn * head * (0.75 + maw) - hd * head * 0.4,
               hc - hn * head * (0.6 + maw * 1.6) + hd * head * 1.1,
               hc - hn * head * (0.1 - maw) + hd * head * 1.3]
        rig.poly(top, hide)
        rig.poly(top, dark, 2)
        rig.poly(bot, shade(hide, 0.9))
        rig.poly(bot, dark, 2)
        for i in range(4):                      # teeth
            f = 0.1 + i * 0.3
            q = hc + hd * head * (f * 1.5) - hn * head * 0.12
            rig.poly([q, q - hn * head * (0.22 + maw * 0.3) + hd * 3,
                      q + hd * head * 0.2], (236, 232, 214))
    # the eye, which is the only part of it that looks at you
    eye = hc + hd * head * 0.45 + hn * head * 0.3
    rig.circle((eye.x, eye.y), head * 0.16, (250, 236, 170))
    rig.circle((eye.x, eye.y), head * 0.07, (24, 18, 16))
    if windup > 0.05:
        rig.light((eye.x, eye.y), head * (0.34 + windup * 0.5),
                  (255, 120, 60), int(40 + 70 * windup))

    # -- front arms -------------------------------------------------------
    if arms:
        for depth, shading in ((0, 0.6), (1, 1.0)):
            root = Vector2(bl * 0.62, cy - bh * 0.1)
            aa = -0.5 + math.sin(t * 2.2 + depth) * 0.25 - windup * 0.9
            elb = root + Vector2(math.cos(aa), math.sin(aa)) * (bl * 0.5)
            hand = elb + Vector2(math.cos(aa + 1.15),
                                 math.sin(aa + 1.15)) * (bl * 0.46)
            c = shade(hide, shading * 0.9)
            rig.bar((root.x, root.y), (elb.x, elb.y), bh * 0.3, c, bh * 0.22)
            rig.bar((elb.x, elb.y), (hand.x, hand.y), bh * 0.22, c, bh * 0.14)
            for k in (-1, 0, 1):
                tipv = hand + Vector2(math.cos(aa + 1.15 + k * 0.35),
                                      math.sin(aa + 1.15 + k * 0.35)) * bh * 0.5
                rig.bar((hand.x, hand.y), (tipv.x, tipv.y), bh * 0.09,
                        shade(c, 0.8), bh * 0.03)



# ---------------------------------------------------------------------------
# THE THINGS THAT COME UP FROM THE DOCKS
#
# KEAL CO's production line, for the campaign where you are the hatchery.
# Six machines against six animals, and they are the SAME SIX ROLES with
# the same health, the same speed, the same hide and the same attacks -
# mirrored out of the bestiary rather than typed out again, so the two
# campaigns cannot drift apart and one set of balance numbers covers both.
#
# What differs is what you are looking at. A KEAL machine is drawn by the
# same routine that draws yours, out of a build, so every one of them is a
# real loadout you could have chosen: the BASTION is a tier-three torso on
# tier-one legs with two pile drivers, and it looks it.
# ---------------------------------------------------------------------------
MECH_BODY = (95, 70, -250, 2, 200, 0, 0.0, 0, 0, 0, 0, 0, 0)


def _machine(src, key, name, title, hide, scale, build, note):
    """One KEAL model, wearing an animal's statistics."""
    k = Kind(key, name, title, hide, scale, src.hp, src.speed, src.dr,
             src.attacks, src.scrap, src.alloy, src.wreck, src.rampage,
             MECH_BODY, note)
    k.family = "mech"
    k.build = build
    k.poise = src.poise
    m = Mech()
    for socket, fit in build.items():
        m.install(socket, fit)
    k.rig = m
    return k


DRONE_BUILD = {"legs": 1, "torso": 1, "r_arm": 1, "r_wpn": "fist"}

KEAL_ROSTER = [
    _machine(BESTIARY[0], "picket", "KL-1 PICKET", "the first one",
             (122, 140, 110), 0.70,
             {"legs": 1, "torso": 1, "head": 1, "r_arm": 1, "r_wpn": "auto"},
             "A frame, a gun and a camera. They build them in a fortnight "
             "and they do not expect them back."),
    _machine(BESTIARY[1], "dragoon", "KL-3 DRAGOON",
             "it does not have to reach you", (170, 146, 74), 0.82,
             {"legs": 2, "torso": 2, "head": 1, "l_arm": 1,
              "l_wpn": "missile", "r_arm": 1, "r_wpn": "auto"},
             "It lobs a rack of them over and walks on. Keep moving and "
             "they land where you were."),
    _machine(BESTIARY[2], "bastion", "KL-7 BASTION", "hit it until it stops",
             (98, 106, 130), 0.98,
             {"legs": 1, "torso": 3, "head": 2, "armour": 3, "l_arm": 3,
              "l_wpn": "pile", "r_arm": 3, "r_wpn": "pile"},
             "Ship plate over a layered core on short legs. Small hits "
             "bounce; bring something that arrives all at once."),
    _machine(BESTIARY[3], "harrier", "KL-9 HARRIER",
             "it is not interested in you", (192, 106, 72), 1.00,
             {"legs": 3, "torso": 2, "head": 2, "l_arm": 2, "l_wpn": "saw",
              "r_arm": 2, "r_wpn": "revolver"},
             "Striders and a jump pack. It has somewhere to be and it will "
             "go over you to get there."),
    _machine(BESTIARY[4], "matron", "KL-12 MATRON", "it brings its own crew",
             (136, 110, 154), 1.02,
             {"legs": 2, "torso": 3, "head": 3, "armour": 2, "l_arm": 2,
              "l_wpn": "swarm", "r_arm": 2, "r_wpn": "missile"},
             "A walking hangar. The bay on its back is full of little ones "
             "and splash damage is not a luxury tonight."),
    _machine(BESTIARY[5], "sovereign", "KL-X SOVEREIGN", "the last one",
             (70, 124, 158), 1.30,
             {"legs": 3, "torso": 3, "head": 3, "armour": 3, "l_arm": 3,
              "l_wpn": "ripper", "r_arm": 3, "r_wpn": "sun"},
             "Everything the others were, on one frame, and it has been in "
             "the shed the whole time waiting for them to soften us up."),
]
KEAL_KINDS = {k.key: k for k in KEAL_ROSTER}

DRONE = _machine(BROODLING, "drone", "DRONE", "", (176, 160, 120), 0.30,
                 DRONE_BUILD, "")

# each roster's minion, so the spawn cap and the spawn call can ask the
# animal rather than being told
for _k in BESTIARY:
    _k.minion = BROODLING
for _k in KEAL_ROSTER:
    _k.minion = DRONE
BROODLING.minion = BROODLING
DRONE.minion = DRONE

ROSTERS = {"bio": BESTIARY, "mech": KEAL_ROSTER}


def roster_for(house_key):
    """Whatever the OTHER company makes."""
    return ROSTERS[HOUSES.get(house_key, HOUSES["keal"]).roster]


def kind_at(house_key, index):
    r = roster_for(house_key)
    return r[index] if 0 <= index < len(r) else None


def draw_enemy(surf, e, x, gy, scale, t, windup=0.0):
    """One opponent, whichever company made it."""
    k = e.kind
    dead = clamp(e.dead_t * 0.7, 0, 0.85) if not e.alive else 0.0
    if k.family == "bio":
        draw_kaiju(surf, k, x, gy, scale, t, e.walk, e.moving, -1, windup,
                   e.hurt, dead, e.maw)
        return
    pose = Pose()
    pose.face = -1
    pose.walk = e.walk
    pose.moving = e.moving
    pose.lean = -6.0 * e.moving
    pose.aim = {"l": 0.06, "r": 0.06}
    if e.state == "windup" and e.attack:
        kind = e.attack["kind"]
        if kind in ("swipe", "slam", "kick"):
            pose.swing = {"l": windup, "r": windup * 0.8}
        else:
            pose.recoil = {"l": windup, "r": windup}
    elif e.state == "strike":
        pose.beam = {"l": 1.0, "r": 1.0}
    tint = k.hide
    tones = {"main": tint, "dark": shade(tint, 0.6), "light": shade(tint, 1.3),
             "trim": mix(tint, KEAL_GOLD, 0.55),
             "plate": mix(tint, (150, 136, 112), 0.5), "hollow": tint}
    if e.hurt > 0.01:
        f = clamp(e.hurt, 0, 1) * 0.8
        tones = {n: mix(c, (255, 235, 225), f) for n, c in tones.items()}
    if dead > 0.01:
        tones = {n: mix(c, (46, 44, 48), dead) for n, c in tones.items()}
    draw_mech_side(surf, k.rig, x, gy, scale * k.scale, t, pose, tones=tones)

# ---------------------------------------------------------------------------
# THE CITY
#
# Three layers of skyline and a road. The far two are parallax and never
# change; the near one is a list of blocks that can be knocked down, and
# the number of them still standing IS the city's integrity. Nothing here
# is decoration - when the thing gets past you, you watch which buildings
# go.
# ---------------------------------------------------------------------------
FSCALE = 0.80                     # world units to pixels, in a fight
WALL_X = 150                      # the kaiju wants to get left of this


class City:
    def __init__(self, seed=7):
        rnd = random.Random(seed)
        self.far = [(x, rnd.randint(150, 360), rnd.randint(60, 130))
                    for x in range(-400, WORLD_W + 400, 104)]
        self.mid = [(x, rnd.randint(190, 430), rnd.randint(70, 160))
                    for x in range(-400, WORLD_W + 400, 136)]
        # a foreground row, below the road, purely for depth
        self.near = [(x, rnd.randint(16, 54), rnd.randint(70, 150))
                     for x in range(-400, WORLD_W + 400, 178)]
        # the near blocks only exist behind the wall, which is the whole
        # point of the wall
        self.blocks = []
        x = -560
        while x < WALL_X + 40:
            h = rnd.randint(230, 470)
            w = rnd.randint(78, 130)
            self.blocks.append({"x": x, "w": w, "h": h, "down": 0.0,
                                "lit": rnd.random() < 0.8,
                                "seed": rnd.randint(0, 9999)})
            x += w + rnd.randint(12, 40)
        self.rnd = rnd

    def standing(self):
        return sum(1 for b in self.blocks if b["down"] < 0.9)

    def wreck_one(self):
        up = [b for b in self.blocks if b["down"] < 0.05]
        if not up:
            return None
        b = self.rnd.choice(up[-8:] if len(up) > 8 else up)
        b["down"] = 1.0
        return b


def sky(surf, t):
    """A dusk that never quite finishes. Two bands and a haze."""
    top, bot = (16, 18, 30), (54, 40, 44)
    h = GROUND_Y + 8
    for i in range(0, h, 4):
        f = i / h
        pygame.draw.rect(surf, mix(top, bot, f ** 1.4), (0, i, W, 4))
    # a low sun, not a spotlight: a thin band along the horizon
    band = pygame.Surface((W, 90))
    for i in range(90):
        k = (1 - i / 90.0) ** 2 * 0.30
        band.fill((int(120 * k), int(62 * k), int(46 * k)), (0, 89 - i, W, 1))
    surf.blit(band, (0, GROUND_Y - 90), special_flags=pygame.BLEND_ADD)
    blit_glow(surf, (W - 180, GROUND_Y - 10), 150, (180, 104, 64), 60)


def draw_city(surf, city, cam, t, shake=(0, 0)):
    sky(surf, t)
    ox, oy = shake

    def sx(wx, par):
        return int((wx - cam * par) * FSCALE + W * 0.5 + ox)

    for bx, bw, bh in city.far:
        x = sx(bx, 0.25)
        if -200 < x < W + 200:
            pygame.draw.rect(surf, (30, 32, 46),
                             (x, GROUND_Y - bh + oy, int(bw * FSCALE), bh + 40))
    for bx, bw, bh in city.mid:
        x = sx(bx, 0.55)
        if -240 < x < W + 240:
            w = int(bw * FSCALE)
            pygame.draw.rect(surf, (40, 43, 60), (x, GROUND_Y - bh + oy, w,
                                                  bh + 40))
            for r in range(2, bh // 26):
                for c in range(1, max(2, w // 22)):
                    if (bx + r * 7 + c * 13) % 5 < 2:
                        pygame.draw.rect(surf, (74, 66, 62),
                                         (x + c * 20, GROUND_Y - bh + r * 24 + oy,
                                          6, 9))
    # the near blocks, the ones that can fall
    for b in city.blocks:
        x = sx(b["x"], 1.0)
        w = int(b["w"] * FSCALE)
        if x < -240 or x > W + 240:
            continue
        h = int(b["h"] * (1.0 - b["down"] * 0.72))
        col = (56, 58, 74) if b["down"] < 0.5 else (40, 34, 34)
        pygame.draw.rect(surf, col, (x, GROUND_Y - h + oy, w, h + 30))
        pygame.draw.rect(surf, shade(col, 0.7), (x, GROUND_Y - h + oy, w, h + 30), 1)
        if b["down"] < 0.5 and b["lit"]:
            rn = random.Random(b["seed"])
            for r in range(1, max(2, h // 30)):
                for c in range(1, max(2, w // 20)):
                    if rn.random() < 0.42:
                        pygame.draw.rect(surf, (206, 170, 110),
                                         (x + c * 18 - 2,
                                          GROUND_Y - h + r * 28 + oy, 5, 8))
        elif b["down"] >= 0.5:
            for i in range(3):                  # smoke off the rubble
                a = t * 0.5 + b["seed"] * 0.01 + i
                blit_glow(surf, (x + w * 0.5 + math.sin(a) * 18,
                                 GROUND_Y - h - 20 - (a * 26) % 90 + oy),
                          26, (70, 60, 58), 26)
    # the wall
    wx = sx(WALL_X, 1.0)
    pygame.draw.rect(surf, (72, 74, 88), (wx - 12, GROUND_Y - 120 + oy, 18, 150))
    pygame.draw.rect(surf, (44, 46, 58), (wx - 12, GROUND_Y - 120 + oy, 18, 150), 2)
    for i in range(6):
        pygame.draw.rect(surf, (54, 56, 70),
                         (wx - 14, GROUND_Y - 118 + i * 22 + oy, 22, 5))
    # the road
    pygame.draw.rect(surf, (28, 28, 34), (0, GROUND_Y + oy, W, H - GROUND_Y))
    pygame.draw.line(surf, (52, 52, 62), (0, GROUND_Y + oy), (W, GROUND_Y + oy), 3)
    step = int(150 * FSCALE)
    off = int((-cam * FSCALE + W * 0.5 + ox) % step)
    for i in range(-1, W // step + 2):
        pygame.draw.rect(surf, (58, 56, 52),
                         (off + i * step, GROUND_Y + 40 + oy, int(58 * FSCALE), 5))
    # rooftops between the camera and the road, at 1.5x parallax. Nothing
    # happens down here; it is here so the road is not the bottom of a pit.
    for bx, bh, bw in city.near:
        x = int((bx - cam * 1.45) * FSCALE + W * 0.5 + ox)
        if x < -220 or x > W + 220:
            continue
        w = int(bw * FSCALE)
        top = H - 70 - bh
        pygame.draw.rect(surf, (17, 17, 22), (x, top + oy * 0.4, w, bh + 80))
        pygame.draw.rect(surf, (25, 25, 32), (x, top + oy * 0.4, w, 4))
        for c in range(1, max(2, w // 26)):
            if (bx + c * 7) % 4 < 2:
                pygame.draw.rect(surf, (96, 78, 52),
                                 (x + c * 24, top + 16 + oy * 0.4, 5, 7))


# ---------------------------------------------------------------------------
# THE FIGHT
#
# Everything in here is in WORLD units and seconds. The camera turns them
# into pixels at the last moment and nothing upstream of that knows the
# window exists, which is what lets the whole fight run headless in a test
# harness with no display at all.
# ---------------------------------------------------------------------------
class Shot:
    __slots__ = ("pos", "vel", "dmg", "splash", "owner", "life", "colour",
                 "size", "arc", "trail", "pierce")

    def __init__(self, pos, vel, dmg, owner, colour, splash=0, life=3.0,
                 size=5, arc=0.0, pierce=0):
        self.pierce = pierce
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.dmg = dmg
        self.splash = splash
        self.owner = owner
        self.life = life
        self.colour = colour
        self.size = size
        self.arc = arc              # gravity, for anything lobbed
        self.trail = []


class Bit:
    __slots__ = ("pos", "vel", "life", "max_life", "colour", "size", "grav",
                 "kind")

    def __init__(self, pos, vel, life, colour, size=3, grav=520.0, kind="spark"):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.life = life
        self.max_life = life
        self.colour = colour
        self.size = size
        self.grav = grav
        self.kind = kind


class Number:
    __slots__ = ("pos", "v", "life", "colour", "s")

    def __init__(self, pos, s, colour):
        self.pos = Vector2(pos)
        self.v = Vector2(random.uniform(-16, 16), -58)
        self.life = 0.9
        self.colour = colour
        self.s = s


class Enemy:
    """One animal on the field. The broodlings are these too."""

    def __init__(self, kind, x, hp_mult=1.0):
        self.kind = kind
        self.x = float(x)
        self.max_hp = kind.hp * hp_mult
        self.hp = self.max_hp
        self.walk = random.uniform(0, TAU)
        self.moving = 1.0
        self.state = "walk"
        self.timer = 0.0
        self.attack = None
        self.cool = {a["kind"]: random.uniform(0.4, 1.4) for a in kind.attacks}
        self.hurt = 0.0
        self.stagger = 0.0
        self.dead_t = 0.0
        self.maw = 0.0
        self.y = 0.0                # off the ground, for a leap
        self.vy = 0.0
        self.beam_t = 0.0
        self.stun = 0.0

    @property
    def span(self):
        return self.kind.body[0] * self.kind.scale

    @property
    def top(self):
        """How high the body reaches, in world units; negative is up.

        This used to be an expression inlined in the shell collision test,
        and it had its sign inverted - the window a shell had to arrive in
        was `211 < y < -10`, which is empty. No ranged weapon in the game
        had ever hit anything, and every balance number measured before
        this was the melee half of the build fighting on its own."""
        b = self.kind.body
        return (b[2] - b[1] * 1.7 - b[5] * 0.5) * self.kind.scale

    @property
    def alive(self):
        return self.hp > 0

    def hurtby(self, dmg, pierce=False):
        d = max(1.0, dmg - (0.0 if pierce else self.kind.dr))
        self.hp -= d
        self.hurt = 0.28
        return d


class Fight:
    """One landfall. Owns the animals, the shots, the bits and the camera."""

    ENGAGE = 130.0                  # extra world units the mech's body takes

    def __init__(self, run, kind, city=None):
        self.run = run
        self.mech = run.mech
        self.kind = kind
        self.city = city or City(seed=run.day * 13 + 7)
        self.mech.reset_for_fight()
        self.mx = WALL_X + 420.0
        self.mvel = 0.0
        self.pose = Pose()
        self.pose.face = 1
        self.enemies = [Enemy(kind, WORLD_W - 260)]
        self.shots = []
        self.bits = []
        self.numbers = []
        self.cd = {"l": 0.0, "r": 0.0}
        self.beam_on = {"l": False, "r": False}
        self.boost = 0.0
        self.boost_cd = 0.0
        self.cam = self.mx
        self.shake = 0.0
        self.t = 0.0
        self.over = None            # None, "won", "lost"
        self.over_t = 0.0
        self.integrity = float(run.integrity)
        self.wrecked = 0
        self.dealt = 0.0
        self.taken = 0.0
        self.log = []
        self.stun = 0.0
        self.spared = False          # redundant linkage, one part per landfall
        self.flushed = False         # coolant flush, one tank per landfall
        self.venom = 0.0             # Jack's sac, while it lasts
        self.jars = []               # what came out in the log
        self.tutorial = 4.0 if run.kaiju_index == 0 else 0.0

    # -- geometry ---------------------------------------------------------
    def boss(self):
        for e in self.enemies:
            if e.kind is self.kind:
                return e
        return None

    def sx(self, wx):
        return (wx - self.cam) * FSCALE + W * 0.5

    MUZZLE_Y = -300.0               # roughly where a hardpoint sits

    def aim_angle(self, side):
        """The angle from this hardpoint to the nearest live animal, in the
        machine's own frame where +x is whichever way it is facing."""
        e = None
        best = 1e9
        for o in self.enemies:
            if not o.alive:
                continue
            d = abs(o.x - self.mx)
            if d < best:
                best, e = d, o
        if e is None:
            return 0.06
        dx = (e.x - self.mx) * self.pose.face - 60.0
        dy = e.top * 0.5 - self.MUZZLE_Y
        if dx < 40.0:
            dx = 40.0
        return clamp(math.atan2(dy, dx), -0.95, 0.62)

    def nearest(self, x, alive=True):
        pool = [e for e in self.enemies if e.alive or not alive]
        if not pool:
            return None
        return min(pool, key=lambda e: abs(e.x - x))

    # -- the machine ------------------------------------------------------
    def fire(self, side, dt):
        wpn = self.mech.weapon(side)
        if wpn is None or self.mech.locked or self.mech.down or self.stun > 0:
            return
        if self.pose.brace:
            return
        cycle = self.mech.arm_stat(side, "cycle", 1.0)
        gun_mult = 1.14 if self.mech.has("link") else 1.0
        fast = self.mech.has("autoloader") and wpn.kind in ("gun", "salvo")
        if fast:
            cycle *= 0.80
        if wpn.kind == "beam":
            self.beam_on[side] = True
            self.mech.add_heat(wpn.heat * dt)
            self.pose.beam[side] = 1.0
            tgt = None
            best = 1e9
            for e in self.enemies:
                if not e.alive:
                    continue
                d = (e.x - self.mx) * self.pose.face
                if 0 < d < wpn.reach and d < best:
                    best, tgt = d, e
            hit = []
            for e in self.enemies:
                if not e.alive:
                    continue
                d = (e.x - self.mx) * self.pose.face
                if 0 < d < wpn.reach and (wpn.pierce or e is tgt):
                    hit.append(e)
            for e in hit:
                dealt = e.hurtby(wpn.dmg * dt * self.mech.dmg_mult * gun_mult,
                                 pierce=self.pierce_now(wpn))
                self.dealt += dealt
                if random.random() < dt * 8:
                    self.spark(e.x, -80 - random.uniform(0, 90), (180, 230, 255))
            if hit and random.random() < dt * 3.5:
                SFX.play("beam", 0.35)
            return
        if self.cd[side] > 0:
            return
        self.cd[side] = wpn.cd * cycle
        self.mech.add_heat(wpn.heat * (1.16 if fast else 1.0))
        crit = random.random() < self.mech.crit
        mult = self.mech.dmg_mult * (1.9 if crit else 1.0)
        if wpn.kind != "melee":
            mult *= gun_mult
        if wpn.kind == "melee":
            self.pose.swing[side] = 0.0001
            mult *= self.mech.arm_stat(side, "melee", 1.0)
            reach = wpn.reach
            struck = 0
            for e in self.enemies:
                if not e.alive or struck >= 2:
                    continue
                if abs(e.x - self.mx) <= reach + e.span * 0.55:
                    dealt = e.hurtby(wpn.dmg * mult * (1.0 if not struck
                                                       else 0.55),
                                     pierce=self.pierce_now(wpn))
                    self.dealt += dealt
                    e.stagger += wpn.stagger / e.kind.poise
                    if wpn.key == "hook" and e.y >= 0:
                        # it does not ask whether the thing wanted to come
                        pull = min(110.0, max(0.0, abs(e.x - self.mx) - 150.0))
                        e.x -= math.copysign(pull, e.x - self.mx)
                    self.number(e.x, -140, int(dealt), crit)
                    self.spark(e.x - self.pose.face * e.span * 0.4, -130,
                               (255, 200, 130), 9)
                    struck += 1
            SFX.play("hit" if struck else "cannon", 0.5 if struck else 0.16)
            return
        # anything that leaves the barrel
        SFX.play("cannon", 0.5 if wpn.kind == "salvo" else 0.36)
        self.pose.recoil[side] = 1.0
        self.shake = max(self.shake, 3.0 if wpn.kind == "salvo" else 1.6)
        mz, d = weapon_muzzle(self.mech, self.pose, side, self.sx(self.mx),
                              GROUND_Y, FSCALE)
        wy = -300.0
        if mz is not None:
            wy = (mz.y - GROUND_Y) / FSCALE
        base = self.pose.aim[side]
        tgt = None
        for o in self.enemies:
            if o.alive and (tgt is None
                            or abs(o.x - self.mx) < abs(tgt.x - self.mx)):
                tgt = o
        shots = wpn.shots + (1 if (wpn.kind == "salvo"
                                   and self.mech.has("hoist")) else 0)
        for i in range(shots):
            spread = self.mech.spread
            if wpn.kind == "salvo" and tgt is not None:
                # lobbed, so it needs a ballistic solution rather than a line
                dx = (tgt.x - self.mx) * self.pose.face - 60.0
                dy = tgt.top * 0.5 - wy
                tof = max(0.5, abs(dx) / max(160.0, wpn.speed * 0.85))
                vx = dx / tof + random.uniform(-26, 26) * spread
                vy = dy / tof - 0.5 * 520.0 * tof
                v = Vector2(vx * self.pose.face, vy)
            else:
                ang = base + random.uniform(-0.05, 0.05) * spread
                v = Vector2(math.cos(ang) * self.pose.face,
                            math.sin(ang)) * wpn.speed
            self.shots.append(Shot((self.mx + 60 * self.pose.face, wy), v,
                                   wpn.dmg * mult, "mech",
                                   (255, 214, 140) if wpn.kind == "gun"
                                   else (255, 168, 96),
                                   splash=wpn.splash,
                                   size=5 if wpn.kind == "gun" else 7,
                                   arc=520.0 if wpn.kind == "salvo" else 0.0,
                                   pierce=1 if self.pierce_now(wpn) else 0))

    def pierce_now(self, wpn):
        """Whether this hit ignores hide: the rail always does, and a venom
        sac makes everything do it for ten seconds."""
        return bool(wpn.pierce) or self.venom > 0

    def open_jar(self, key):
        """One of Jack's, out of the cupboard and into the street."""
        if self.mech.down or stock_of(key) <= 0 or not use_specimen(key):
            return False
        w = WARES[key]
        self.say(ware_name(w).upper() + " - OUT OF THE JAR")
        SFX.play("beam", 0.6)
        if key == "spec_shriek":
            e = self.nearest(self.mx)
            if e is not None and e.alive:
                e.state, e.timer, e.attack = "stagger", 1.5, None
                e.stagger = 0.0
                self.spark(e.x, -160, (220, 240, 255), 16, 220)
        elif key == "spec_leech":
            hurt = [s for s in SOCKETS if self.mech.fit[s] is not None
                    and self.mech.damage_frac(s) > 0.01]
            if hurt:
                s = max(hurt, key=self.mech.damage_frac)
                mx = self.mech.max_hp(s)
                self.mech.hp[s] = min(mx, self.mech.hp[s] + mx * 0.33)
                self.say(sock_label(s) + " KNITTING")
                self.spark(self.mx, -220, (150, 240, 170), 14, 150)
        else:
            self.venom = 10.0
            self.spark(self.mx, -240, RYEZ_ACID, 18, 180)
        return True

    def spark(self, wx, wy, colour, n=6, spread=140):
        for _ in range(n):
            self.bits.append(Bit((wx, wy),
                                 (random.uniform(-spread, spread),
                                  random.uniform(-spread, 40)),
                                 random.uniform(0.25, 0.6), colour,
                                 random.uniform(2, 4)))

    def number(self, wx, wy, v, crit=False):
        self.numbers.append(Number((wx, wy), str(v),
                                   (255, 206, 96) if crit else (236, 240, 250)))

    def say(self, s):
        self.log.append([s, 3.2])
        if len(self.log) > 4:
            self.log.pop(0)

    # -- the animals ------------------------------------------------------
    def enemy_think(self, e, dt):
        if not e.alive:
            e.dead_t += dt
            return
        if e.stun > 0:
            e.stun -= dt
            e.moving = approach(e.moving, 0.0, dt * 3)
            return
        for k in list(e.cool):
            e.cool[k] = max(0.0, e.cool[k] - dt)
        e.hurt = max(0.0, e.hurt - dt * 3.4)
        e.maw = approach(e.maw, 0.0, dt * 2.2)
        if e.stagger >= 1.0 and e.state != "strike":
            e.stagger = 0.0
            e.state, e.timer, e.attack = "stagger", 0.85, None
            self.say(e.kind.name + " REELS")
        e.stagger = max(0.0, e.stagger - dt * 0.22)

        if e.y < 0 or e.vy < 0:                 # airborne, from a leap
            e.vy += 1500 * dt
            e.y = min(0.0, e.y + e.vy * dt)
            e.x -= e.kind.speed * 2.3 * dt
            if e.y >= 0:
                e.y, e.vy = 0.0, 0.0
                self.shake = max(self.shake, 9)
                SFX.play("thud", 0.8)
                for _ in range(14):
                    self.bits.append(Bit((e.x, -8),
                                         (random.uniform(-300, 300),
                                          random.uniform(-300, -40)),
                                         0.7, (110, 100, 92), 4))
                if abs(e.x - self.mx) < 260 and not self.mech.down:
                    self.mech_hit(e, 120)
            return

        if e.state == "stagger":
            e.timer -= dt
            e.moving = approach(e.moving, 0.0, dt * 4)
            if e.timer <= 0:
                e.state = "walk"
            return

        if e.state == "windup":
            e.timer -= dt
            if e.attack.get("lunge") and not self.mech.down:
                step = e.kind.speed * 1.5 * dt
                to = self.mx - e.x
                e.x += math.copysign(min(step, abs(to)), to) if to else 0.0
                e.moving = approach(e.moving, 0.85, dt * 4)
                e.walk += dt * 5.0
            else:
                e.moving = approach(e.moving, 0.0, dt * 4)
            if e.attack["kind"] in ("spit", "beam"):
                e.maw = approach(e.maw, 1.0, dt * 2.5)
            if e.timer <= 0:
                self.enemy_strike(e)
            return

        if e.state == "strike":                 # the beam holds on
            e.timer -= dt
            e.moving = 0.0
            a = e.attack
            if a["kind"] == "beam" and not self.mech.down:
                if abs(e.x - self.mx) < a["reach"]:
                    self.mech_hit(e, a["dmg"] * dt, silent=True, beam=True)
            if e.timer <= 0:
                e.state = "walk"
                e.beam_t = 0.0
            return

        # walking: it wants the wall, and you are in the road
        dist = abs(e.x - self.mx)
        blocked = (not self.mech.down) and dist < e.span + self.ENGAGE
        # The heaviest thing it can reach you with, not the first thing in
        # the table. Iterating in order meant the cheap swipe was always off
        # cooldown first and won every time, so the LEVIATHAN's beam, slam
        # and roar were three attacks it owned and almost never used.
        choices = []
        for a in e.kind.attacks:
            k = a["kind"]
            if e.cool[k] > 0:
                continue
            if k == "spawn":
                live = sum(1 for o in self.enemies
                           if o.alive and o.kind is e.kind.minion)
                if live >= 4:            # she cannot bury you in bodies
                    e.cool[k] = 3.0
                    continue
                self.begin(e, a)
                return
            if self.mech.down:
                continue
            if k in ("swipe", "slam", "kick"):
                if dist <= a["reach"] + e.span * 0.4:
                    choices.append(a)
            elif k == "spit":
                if 200 < dist <= a["reach"]:
                    choices.append(a)
            elif k == "beam":
                # No minimum range: you cannot walk out of a beam, which is
                # the point of one. Standing in its face used to switch this
                # off entirely, and it landed 225 damage in 86 seconds.
                if dist <= a["reach"]:
                    choices.append(a)
            elif k == "leap":
                if 300 < dist < a["reach"] and self.mx < e.x:
                    choices.append(a)
            elif k == "roar":
                if dist < 900:
                    choices.append(a)
        if choices:
            self.begin(e, max(choices, key=lambda a: a["cool"]))
            return
        if blocked:
            e.moving = approach(e.moving, 0.25, dt * 2)
            e.x += (self.mx + (e.span + self.ENGAGE) - e.x) * 0.0
            return
        e.moving = approach(e.moving, 1.0, dt * 2)
        if e.x > WALL_X:
            e.x -= e.kind.speed * dt
            e.walk += dt * (2.4 + e.kind.speed / 60.0)
        else:
            # it is inside the wall now, and it is not fighting any more
            e.x = WALL_X
            e.moving = approach(e.moving, 0.0, dt * 2)
            self.integrity -= e.kind.wreck * dt
            if random.random() < dt * 0.55:
                b = self.city.wreck_one()
                if b is not None:
                    self.wrecked += 1
                    self.shake = max(self.shake, 6)
                    SFX.play("wreck", 0.6)

    def begin(self, e, a):
        e.state = "windup"
        e.attack = a
        e.timer = a["windup"] + self.mech.warn * 0.45
        e.cool[a["kind"]] = a["cool"]
        if a["kind"] == "roar":
            SFX.play("roar", 0.8)

    def enemy_strike(self, e):
        a = e.attack
        k = a["kind"]
        e.state = "walk"
        if k in ("swipe", "slam", "kick"):
            if not self.mech.down and abs(e.x - self.mx) <= a["reach"] + 60:
                self.mech_hit(e, a["dmg"])
                if self.mech.has("shock"):        # the hull bills for it
                    back = e.hurtby(16.0, pierce=True)
                    self.dealt += back
                    self.number(e.x, -190, int(back))
                    self.spark(e.x, -150, (150, 220, 255), 7)
            else:
                SFX.play("thud", 0.4)
            if a.get("shake"):
                self.shake = max(self.shake, 10)
                for _ in range(16):
                    self.bits.append(Bit((e.x - e.span * 0.6, -8),
                                         (random.uniform(-260, 120),
                                          random.uniform(-340, -60)),
                                         0.8, (120, 108, 96), 5))
        elif k == "spit":
            src = Vector2(e.x - e.span * 0.9, -e.kind.body[2] - 60)
            tgt = Vector2(self.mx, -160)
            d = tgt - src
            tof = max(0.35, abs(d.x) / max(120.0, a.get("speed", 520)))
            v = Vector2(d.x / tof, d.y / tof - 0.5 * 520 * tof)
            self.shots.append(Shot(src, v, a["dmg"], "kaiju",
                                   mix(e.kind.hide, (230, 255, 150), 0.6),
                                   splash=90, size=9, arc=520.0))
            SFX.play("beam", 0.4)
        elif k == "beam":
            e.state = "strike"
            e.timer = a.get("hold", 1.4)
            SFX.play("roar", 0.5)
        elif k == "leap":
            e.vy = -760.0
            e.y = -0.01
            SFX.play("thud", 0.5)
        elif k == "spawn":
            minion = e.kind.minion or BROODLING
            for i in range(a.get("brood", 2)):
                self.enemies.append(Enemy(minion,
                                          e.x + e.span + 70 + i * 95))
            self.say("SHE HAS PUT MORE OF THEM DOWN")
            SFX.play("roar", 0.6)
        elif k == "roar":
            self.shake = max(self.shake, 8)
            if self.mech.has("gyro"):
                self.say("THE ROAR - THE GYRO HOLDS IT")
                return
            self.stun = 1.1
            self.mech.add_heat(self.mech.heat_cap * 0.18)
            self.say("THE ROAR - SYSTEMS SCRAMBLED")

    def mech_hit(self, e, dmg, silent=False, beam=False):
        if self.mech.down:
            return
        socket, applied, wrecked = self.mech.hurt(
            dmg, bracing=self.pose.brace, pierce_plate=beam)
        self.taken += applied
        self.pose.flash = max(self.pose.flash, 0.5 if not beam else 0.16)
        if not silent:
            self.shake = max(self.shake, 4.5)
            SFX.play("thud", 0.7)
            self.spark(self.mx, -200, (255, 170, 120), 10, 190)
            self.number(self.mx, -250, int(applied), False)
        if wrecked and self.mech.has("redundant") and not self.spared:
            # the second cable, routed the long way round
            self.spared = True
            self.mech.hp[socket] = self.mech.max_hp(socket) * 0.12
            wrecked = False
            self.say(sock_label(socket) + " IS HANGING ON")
            SFX.play("rivet", 0.8)
        if wrecked:
            self.say(sock_label(socket) + " GONE")
            SFX.play("wreck", 0.7)
            self.shake = max(self.shake, 9)
            for _ in range(18):
                self.bits.append(Bit((self.mx, -200),
                                     (random.uniform(-260, 260),
                                      random.uniform(-320, -20)),
                                     1.0, (150, 120, 96), 5))
        if self.mech.down and self.over is None:
            self.over, self.over_t = "lost", 0.0
            SFX.play("wreck", 1.0)
            self.say("THE MACHINE IS DOWN")

    # -- the tick ---------------------------------------------------------
    def update(self, dt, inp):
        """`inp` is a plain dict, not a pygame state, so the whole fight
        runs under a test harness with no window and no keyboard."""
        self.t += dt
        self.venom = max(0.0, self.venom - dt)
        for i, w in enumerate(SPECIMENS):
            if inp.get("jar%d" % (i + 1)):
                self.open_jar(w.key)
        self.tutorial = max(0.0, self.tutorial - dt)
        self.stun = max(0.0, self.stun - dt)
        for row in self.log:
            row[1] -= dt
        while self.log and self.log[0][1] <= 0:
            self.log.pop(0)

        # -- the pilot -----------------------------------------------------
        down = self.mech.down
        move = 0.0
        if not down and self.stun <= 0:
            move = (1.0 if inp.get("right") else 0.0) - \
                   (1.0 if inp.get("left") else 0.0)
        self.pose.brace = bool(inp.get("brace")) and not down and \
            (self.mech.alive("l_arm") or self.mech.alive("r_arm"))
        if self.pose.brace:
            move = 0.0
        speed = self.mech.speed
        if self.boost > 0:
            speed *= 2.3
        self.mvel = approach(self.mvel, move * speed, speed * 5.0 * dt)
        self.mx = clamp(self.mx + self.mvel * dt, 60.0, WORLD_W - 60.0)
        self.pose.moving = approach(self.pose.moving,
                                    clamp(abs(self.mvel) / max(40.0, speed),
                                          0.0, 1.0), dt * 5)
        if speed > 0:
            self.pose.walk += dt * (1.6 + 4.2 * self.pose.moving)
        self.pose.lean = approach(self.pose.lean,
                                  clamp(self.mvel / max(60.0, speed), -1, 1) * 5.0,
                                  dt * 30)
        # it always faces whatever is closest and still moving
        near = self.nearest(self.mx)
        if near is not None:
            self.pose.face = 1 if near.x >= self.mx else -1
        self.boost = max(0.0, self.boost - dt)
        self.boost_cd = max(0.0, self.boost_cd - dt)
        if inp.get("boost") and self.mech.can_boost and self.boost_cd <= 0 \
                and not down:
            self.boost, self.boost_cd = 0.32, 1.5
            SFX.play("rivet", 0.3)

        # -- weapons -------------------------------------------------------
        self.beam_on = {"l": False, "r": False}
        for side in ("l", "r"):
            self.cd[side] = max(0.0, self.cd[side] - dt)
            self.pose.recoil[side] = approach(self.pose.recoil[side], 0.0,
                                              dt * 5.5)
            if self.pose.swing[side] > 0:
                self.pose.swing[side] = min(1.0, self.pose.swing[side] + dt * 4.2)
                if self.pose.swing[side] >= 1.0:
                    self.pose.swing[side] = 0.0
            self.pose.beam[side] = approach(self.pose.beam[side], 0.0, dt * 6)
            self.pose.aim[side] = approach(self.pose.aim[side],
                                           self.aim_angle(side), dt * 5.0)
            if inp.get("fire_" + side) and not down:
                self.fire(side, dt)
        self.mech.cool(dt)
        if self.pose.brace and self.mech.has("shutters"):
            self.mech.cool(dt * 1.5)         # 2.5x venting behind the plates
        if inp.get("flush") and not self.flushed and self.mech.has("flush")                 and not down:
            self.flushed = True
            self.mech.heat = 0.0
            self.mech.locked = False
            self.say("COOLANT DUMPED")
            SFX.play("beam", 0.7)
            self.spark(self.mx, -240, (180, 240, 255), 18, 220)
        self.pose.flash = approach(self.pose.flash, 0.0, dt * 3.0)

        # -- the animals ---------------------------------------------------
        for e in self.enemies:
            self.enemy_think(e, dt)
            if e.alive and e.state == "walk" and e.moving > 0.05:
                e.walk += dt * (2.2 + e.kind.speed / 70.0) * e.moving
        # a dead one lies where it fell for a moment, then it is salvage
        self.enemies = [e for e in self.enemies
                        if e.alive or e.dead_t < 2.4]

        # -- shots ----------------------------------------------------------
        for s in self.shots:
            s.life -= dt
            s.vel.y += s.arc * dt
            s.pos += s.vel * dt
            if len(s.trail) > 5:
                s.trail.pop(0)
            s.trail.append(Vector2(s.pos))
            if s.pos.y > -6:                      # into the road
                self.burst(s)
                s.life = 0
                continue
            if s.owner == "mech":
                for e in self.enemies:
                    if not e.alive:
                        continue
                    if abs(e.x - s.pos.x) < e.span * 0.9 and \
                            e.top < s.pos.y < -8:
                        dealt = e.hurtby(s.dmg, pierce=bool(s.pierce))
                        self.dealt += dealt
                        self.number(e.x, s.pos.y, int(dealt))
                        e.stagger += 0.05 / e.kind.poise
                        self.burst(s, e)
                        s.life = 0
                        break
            else:
                if abs(self.mx - s.pos.x) < 90 and -340 < s.pos.y < -30 \
                        and not self.mech.down:
                    self.mech_hit(None, s.dmg)
                    self.burst(s)
                    s.life = 0
        self.shots = [s for s in self.shots if s.life > 0]

        for b in self.bits:
            b.life -= dt
            b.vel.y += b.grav * dt
            b.pos += b.vel * dt
            if b.pos.y > -4:
                b.pos.y = -4
                b.vel *= 0.0
        self.bits = [b for b in self.bits if b.life > 0]
        for nb in self.numbers:
            nb.life -= dt
            nb.v.y += 70 * dt
            nb.pos += nb.v * dt
        self.numbers = [n for n in self.numbers if n.life > 0]

        # -- camera ---------------------------------------------------------
        boss = self.boss()
        focus = self.mx
        if boss is not None:
            # lead toward the animal, but only so far - the machine is what
            # the player is steering and it never leaves the frame
            focus = self.mx + clamp(boss.x - self.mx, -520, 520) * 0.44
        focus = clamp(focus, W * 0.5 / FSCALE, WORLD_W - W * 0.5 / FSCALE)
        self.cam = lerp(self.cam, focus, dt * 3.4)
        edge = (W * 0.5 - 210) / FSCALE
        self.cam = clamp(self.cam, self.mx - edge, self.mx + edge)
        self.shake = max(0.0, self.shake - dt * 22)

        # -- is it over? ----------------------------------------------------
        self.integrity = max(0.0, self.integrity)
        if self.over is None:
            if boss is None or not boss.alive:
                if not any(e.alive for e in self.enemies):
                    self.over, self.over_t = "won", 0.0
                    SFX.play("done", 0.8)
            if self.integrity <= 0:
                self.over, self.over_t = "lost", 0.0
        else:
            self.over_t += dt

    def burst(self, s, e=None):
        col = s.colour
        n = 10 if s.splash else 5
        self.spark(s.pos.x, s.pos.y, col, n, 180 if s.splash else 110)
        if s.splash:
            self.shake = max(self.shake, 3.5)
            SFX.play("thud", 0.4)
            for other in self.enemies:
                if not other.alive or other is e:
                    continue
                if abs(other.x - s.pos.x) < s.splash + other.span * 0.6:
                    dealt = other.hurtby(s.dmg * 0.55)
                    self.dealt += dealt
                    self.number(other.x, -140, int(dealt))
            if e is not None:
                pass

    # -- drawing ----------------------------------------------------------
    def draw(self, surf):
        sh = (random.uniform(-1, 1) * self.shake,
              random.uniform(-1, 1) * self.shake) if self.shake > 0.2 else (0, 0)
        draw_city(surf, self.city, self.cam, self.t, sh)
        gy = GROUND_Y + sh[1]

        # the far ones first so a broodling never stands in front of mother
        order = sorted(self.enemies, key=lambda e: -e.kind.scale)
        for e in order:
            x = self.sx(e.x) + sh[0]
            if x < -400 or x > W + 400:
                continue
            windup = 0.0
            if e.state == "windup" and e.attack:
                full = e.attack["windup"] + self.mech.warn * 0.45
                windup = clamp(1.0 - e.timer / max(0.12, full), 0, 1)
            draw_enemy(surf, e, x, gy + e.y * FSCALE, FSCALE, self.t, windup)
            if e.state == "windup" and e.attack and \
                    e.attack["kind"] in ("swipe", "slam", "kick"):
                self.telegraph(surf, e, gy, sh)
            if e.state == "strike" and e.attack and e.attack["kind"] == "beam":
                self.draw_beam(surf, e, gy, sh)

        mx = self.sx(self.mx) + sh[0]
        if self.mech.down:
            # it kneels where it fell
            p = Pose()
            p.face = self.pose.face
            p.walk = 0.0
            p.moving = 0.0
            p.lean = 26
            draw_mech_side(surf, self.mech, mx, gy + 30, FSCALE, self.t, p)
            for i in range(3):
                blit_glow(surf, (mx + math.sin(self.t + i) * 20,
                                 gy - 120 - ((self.t * 30 + i * 40) % 140)),
                          40, (90, 74, 66), 34)
        else:
            draw_mech_side(surf, self.mech, mx, gy, FSCALE, self.t, self.pose)
            for side in ("l", "r"):
                w = self.mech.weapon(side)
                if w and w.kind == "beam" and self.beam_on[side]:
                    self.draw_mech_beam(surf, side, w, mx, gy, sh)

        for s in self.shots:
            pts = [(self.sx(q.x) + sh[0], gy + q.y * FSCALE) for q in s.trail]
            if len(pts) > 1:
                pygame.draw.lines(surf, shade(s.colour, 0.7), False, pts, 2)
            p = (self.sx(s.pos.x) + sh[0], gy + s.pos.y * FSCALE)
            pygame.draw.circle(surf, s.colour, p, max(2, s.size * 0.62))
            blit_glow(surf, p, s.size * 1.5, s.colour, 55)
        for b in self.bits:
            f = b.life / b.max_life
            p = (self.sx(b.pos.x) + sh[0], gy + b.pos.y * FSCALE)
            pygame.draw.circle(surf, b.colour, p, max(1, b.size * f))
        for nb in self.numbers:
            a = int(255 * clamp(nb.life / 0.9, 0, 1))
            text(surf, nb.s, 22, (self.sx(nb.pos.x) + sh[0],
                                  gy + nb.pos.y * FSCALE), nb.colour,
                 center=True, alpha=a)
        self.hud(surf)

    def telegraph(self, surf, e, gy, sh):
        """The wind-up, drawn as a bracket on the ground where it lands.
        A command head buys you half a second of this; a sensor pod does
        not, which is what the head is FOR."""
        f = clamp(1.0 - e.timer / max(0.12, e.attack["windup"]
                                      + self.mech.warn * 0.45), 0, 1)
        reach = e.attack["reach"]
        x0 = self.sx(e.x - reach) + sh[0]
        x1 = self.sx(e.x) + sh[0]
        col = mix((240, 120, 80), (255, 230, 160), f)
        y = gy + 16
        pygame.draw.line(surf, col, (x0, y), (x1, y), 3)
        pygame.draw.line(surf, col, (x0, y - 14), (x0, y + 6), 3)
        h = int(70 * f)
        s = pygame.Surface((max(2, int(x1 - x0)), 90), pygame.SRCALPHA)
        s.fill((col[0], col[1], col[2], int(40 + 50 * f)))
        surf.blit(s, (x0, y - h))

    def draw_beam(self, surf, e, gy, sh):
        y = gy - (e.kind.body[2] + 70) * FSCALE * e.kind.scale
        x0 = self.sx(e.x - e.span) + sh[0]
        x1 = self.sx(e.x - e.attack["reach"]) + sh[0]
        w = 8 + math.sin(self.t * 40) * 3
        pygame.draw.line(surf, (200, 255, 190), (x0, y), (x1, y + 40), int(w))
        pygame.draw.line(surf, (255, 255, 255), (x0, y), (x1, y + 40),
                         max(1, int(w * 0.4)))
        blit_glow(surf, (x1, y + 40), 40, (160, 255, 150), 120)

    def draw_mech_beam(self, surf, side, w, mx, gy, sh):
        mz, d = weapon_muzzle(self.mech, self.pose, side, mx, gy, FSCALE)
        if mz is None:
            return
        end = Vector2(mz) + Vector2(d.x, d.y) * w.reach * FSCALE
        wob = 7 + math.sin(self.t * 44) * 2.5
        pygame.draw.line(surf, (150, 220, 255), mz, end, int(wob))
        pygame.draw.line(surf, (255, 255, 255), mz, end, max(1, int(wob * 0.42)))
        blit_glow(surf, mz, 22, (160, 220, 255), 150)

    # -- the instruments --------------------------------------------------
    def hud(self, surf):
        m = self.mech
        # the machine, part by part
        panel(surf, pygame.Rect(14, 12, 236, 186), (16, 18, 26), LINE, 6)
        text(surf, word("machine", "THE MACHINE"), 16, (26, 20), DIM)
        y = 42
        for s in SOCKETS:
            if m.fit[s] is None:
                continue
            mx_ = m.max_hp(s)
            f = m.hp[s] / mx_ if mx_ else 0.0
            col = GOOD if f > 0.6 else (WARN if f > 0.25 else BAD)
            if f <= 0:
                col = (70, 64, 70)
            lab = (RYEZ_HUD if CURRENT["house"] == "ryez"
                   else HUD_LABEL)[s]
            text(surf, lab, 13, (26, y), DIM if f > 0 else FAINT)
            bar(surf, pygame.Rect(140, y + 2, 96, 8), f, col)
            y += 17
        # heat, which is the only ammunition in the game
        hb = pygame.Rect(14, 208, 236, 26)
        hf = m.heat_frac
        hc = mix((96, 180, 230), (255, 110, 60), hf)
        panel(surf, hb, (16, 18, 26), LINE, 5)
        bar(surf, pygame.Rect(hb.x + 4, hb.y + 4, hb.w - 8, hb.h - 8), hf, hc)
        lab = (word("overheat", "OVERHEAT - VENTING") if m.locked
               else word("heat", "HEAT"))
        text(surf, lab, fit(lab, 15, hb.w - 18), hb.center, INK,
             center=True)
        if m.mods:
            chips = pygame.Rect(14, 240, 236, 22 * ((len(m.mods) + 1) // 2)
                                + 8)
            panel(surf, chips, (16, 18, 26), LINE, 5)
            for i, k in enumerate(m.mods):
                mod = MODULES[k]
                cx = chips.x + 8 + (i % 2) * 114
                cy = chips.y + 4 + (i // 2) * 22
                live = not (k == "flush" and self.flushed)
                short = pname(MOD_SLOT, mod)
                short = short.split()[0][:9] if len(short) > 11 else short
                text(surf, short, 12, (cx, cy), CORE if live else FAINT)
                if k == "flush":
                    text(surf, "V" if live else "-", 12, (cx + 100, cy),
                         GOOD if live else FAINT, right=True)
        # Jack's cupboard, and how long the sac has left in it
        jy = 240 + ((22 * ((len(m.mods) + 1) // 2) + 8 + 6) if m.mods else 0)
        held = [w for w in SPECIMENS if stock_of(w.key) > 0]
        if held or self.venom > 0:
            jr = pygame.Rect(14, jy, 236, 18 * len(held) + 8
                             + (16 if self.venom > 0 else 0))
            panel(surf, jr, (16, 18, 26), LINE, 5)
            for i, w in enumerate(SPECIMENS):
                if stock_of(w.key) <= 0:
                    continue
                row = jr.y + 4 + held.index(w) * 18
                text(surf, str(SPECIMENS.index(w) + 1), 12, (jr.x + 8, row),
                     PAINT)
                nm = ware_name(w)
                text(surf, nm, fit(nm, 12, 150), (jr.x + 22, row), ALLOY_C)
                text(surf, "x%d" % stock_of(w.key), 12, (jr.right - 8, row),
                     DIM, right=True)
            if self.venom > 0:
                bar(surf, pygame.Rect(jr.x + 8, jr.bottom - 13, jr.w - 16, 6),
                    self.venom / 10.0, RYEZ_ACID)

        # the animal
        boss = self.boss()
        if boss is not None:
            know = m.sensors
            bw = 520
            r = pygame.Rect(W // 2 - bw // 2, 16, bw, 34)
            panel(surf, r, (16, 18, 26), LINE, 6)
            f = clamp(boss.hp / boss.max_hp, 0, 1)
            bar(surf, pygame.Rect(r.x + 6, r.y + 20, r.w - 12, 9), f,
                shade(boss.kind.hide, 1.4) if know else (120, 124, 142),
                back=(12, 13, 18))
            text(surf, boss.kind.name, 17, (r.centerx, r.y + 4), INK,
                 center=True)
            text(surf, "%d" % int(boss.hp) if know else "NO SENSORS",
                 14, (r.right - 8, r.y + 3), DIM if know else FAINT,
                 right=True)

        # the city
        r = pygame.Rect(W - 250, 12, 236, 52)
        panel(surf, r, (16, 18, 26), LINE, 6)
        f = clamp(self.integrity / 100.0, 0, 1)
        text(surf, "CITY", 15, (r.x + 10, r.y + 8), DIM)
        text(surf, "%d%%" % int(self.integrity), 20, (r.right - 10, r.y + 6),
             GOOD if f > 0.5 else (WARN if f > 0.22 else BAD), right=True)
        bar(surf, pygame.Rect(r.x + 8, r.y + 32, r.w - 16, 10), f,
            GOOD if f > 0.5 else (WARN if f > 0.22 else BAD))

        # the hardpoints
        for i, side in enumerate(("l", "r")):
            w = m.weapon(side)
            r = pygame.Rect(W // 2 - 250 + i * 256, H - 62, 244, 46)
            panel(surf, r, (16, 18, 26), LINE, 5)
            key = "J" if side == "l" else "K"
            if w is None:
                text(surf, key + "  -", 16, (r.x + 10, r.y + 14), FAINT)
                continue
            ready = self.cd[side] <= 0 and not m.locked
            text(surf, key, 15, (r.x + 10, r.y + 6), DIM)
            wn = pname("l_wpn" if side == "l" else "r_wpn", w)
            text(surf, wn, fit(wn, 17, 190), (r.x + 34, r.y + 6),
                 INK if ready else FAINT)
            cf = 1.0 - clamp(self.cd[side] / max(0.01, w.cd), 0, 1) \
                if w.kind != "beam" else 1.0
            bar(surf, pygame.Rect(r.x + 10, r.y + 30, r.w - 20, 7), cf,
                PAINT if ready else (70, 66, 74))

        for i, (s, life) in enumerate(reversed(self.log)):
            text(surf, s, 19, (W // 2, 96 + i * 24), mix(BG, RUST, 1.0)
                 if "GONE" in s else (222, 196, 140), center=True,
                 alpha=int(255 * clamp(life, 0, 1)))

        if self.tutorial > 0:
            a = int(230 * clamp(self.tutorial / 4.0, 0, 1))
            text(surf, "A / D  WALK      J / K  FIRE      S  BRACE", 19,
                 (W // 2, H - 100), (230, 216, 180), center=True, alpha=a)
            text(surf, "IT IS WALKING TO THE CITY. BE IN THE WAY.", 16,
                 (W // 2, H - 78), (200, 160, 120), center=True, alpha=a)
        if self.stun > 0:
            text(surf, "SYSTEMS SCRAMBLED", 30, (W // 2, H // 2 - 40),
                 (255, 150, 90), center=True,
                 alpha=int(220 * clamp(self.stun, 0, 1)))


# ---------------------------------------------------------------------------
# THE RUN
#
# A calendar, a bank, a crew and one machine. Everything the player does
# between fights goes through here, and the whole thing serialises to JSON
# so a run can be put down on day nine and picked up a week later.
#
# The schedule is FIXED and published. You are never surprised by a
# landfall; you are only ever short of the days between them.
# ---------------------------------------------------------------------------
SCHEDULE = (7, 15, 24, 34, 45, 57)
MAX_CREW = 6
CREW_PER_JOB = 3
RUSH_PER_DAY = 62

# RYEZ's half of the calendar. A culture gestates for half as long again as
# the equivalent weld takes, and no number of handlers makes it faster -
# what they do is hold it together. Left alone a pod drifts; at FAULT_AT it
# expresses wrong and the organ grafts on at a fraction of what it should
# be, which is the same cost FORCING one carries by definition.
GESTATE = 1.5
DRIFT_PER_DAY = 16.0
HANDLER_CALM = 12.0
FAULT_AT = 50.0
FLAWED_HP = 0.62
POD_BASE = 5
BIO_COST = 0.76

# Those four numbers are the whole of RYEZ's decision, so they are chosen
# to make it a real one rather than a tax. Nobody on a pod is +16 a day and
# it faults on the fourth; one handler is +4 and it faults on the
# thirteenth; two is -8 and it never faults at all. So a short culture
# tolerates a single pair of hands and a long one does not, and with four
# pods and three handlers you are always choosing which tank goes unwatched
# tonight. An earlier pass had nobody able to hold more than two, every
# spare pod faulting, and the yard paying for everything twice.


class Job:
    """A thing being worked on. For KEAL that is a job on a gantry and the
    crew ARE the speed. For RYEZ it is a culture in a pod, which takes the
    time it takes however many handlers you stand around it - what they buy
    there is stability, and an unstable pod grafts a flawed organ."""

    __slots__ = ("socket", "target", "kind", "need", "done", "crew", "rushed",
                 "bio", "unstable")

    def __init__(self, socket, target, kind, need, crew=1, bio=False):
        self.socket = socket
        self.target = target
        self.kind = kind            # "build" or "repair"
        self.need = float(need)
        self.done = 0.0
        self.crew = crew
        self.rushed = False
        self.bio = bio              # a pod, not a gantry
        self.unstable = 0.0         # 0..100; over FAULT_AT it comes out wrong

    @property
    def left(self):
        return max(0.0, self.need - self.done)

    @property
    def prog(self):
        return clamp(self.done / max(0.001, self.need), 0.0, 1.0)

    def days_left(self, crew=None):
        if self.bio:
            return int(math.ceil(self.left))     # biology ignores overtime
        c = max(1, crew if crew is not None else self.crew)
        return int(math.ceil(self.left / c))

    @property
    def faulted(self):
        return self.rushed or self.unstable >= FAULT_AT

    def label(self):
        if self.kind == "repair":
            return word("repair", "REPAIR") + " " + sock_label(self.socket)
        return pname(self.socket, part_of(self.socket, self.target))

    def to_json(self):
        return {"socket": self.socket, "target": self.target,
                "kind": self.kind, "need": self.need, "done": self.done,
                "crew": self.crew, "rushed": self.rushed, "bio": self.bio,
                "unstable": round(self.unstable, 1)}

    @classmethod
    def from_json(cls, d):
        j = cls(d["socket"], d["target"], d.get("kind", "build"),
                d.get("need", 1), int(d.get("crew", 1)),
                bool(d.get("bio", False)))
        j.done = float(d.get("done", 0))
        j.rushed = bool(d.get("rushed", False))
        j.unstable = clamp(float(d.get("unstable", 0)), 0.0, 100.0)
        return j


class Run:
    def __init__(self, house_key="keal"):
        self.house = house_key if house_key in HOUSES else "keal"
        set_house(self.house)
        self.day = 1
        self.scrap = 170
        self.alloy = 0
        self.crew = 2
        self.integrity = 100.0
        self.kaiju_index = 0
        self.killed = 0
        self.yard = 0                # SECOND CRANE / NIGHT SHIFT / FOUNDRY
        self.mech = Mech()
        self.jobs = []
        if self.house == "ryez":
            self.news = ["THE SKELETON AND ONE FORELIMB TOOK LAST WINTER.",
                         "THEN THE FUNDING WENT.",
                         "KEAL COMES UP THE ROAD ON DAY %d." % SCHEDULE[0]]
        else:
            self.news = ["THE FRAME AND THE LEFT ARM WENT UP LAST WINTER.",
                         "THEN THE MONEY RAN OUT.",
                         "RYEZ PUTS ONE ASHORE ON DAY %d." % SCHEDULE[0]]
        self.spent = 0
        self.rushes = 0
        if has_ware("warchest"):
            self.scrap += 200
        if has_ware("earlyshift"):
            self.crew += 1

    # -- the calendar -----------------------------------------------------
    @property
    def next_landfall(self):
        if self.kaiju_index >= len(SCHEDULE):
            return None
        return SCHEDULE[self.kaiju_index]

    @property
    def days_left(self):
        nl = self.next_landfall
        return None if nl is None else nl - self.day

    def next_kind(self):
        return kind_at(self.house, self.kaiju_index)

    @property
    def income(self):
        """A wrecked city cannot feed a shipyard, which is the whole of the
        feedback loop: lose ground and you lose the means to take it back."""
        base = 68 + 16 * self.killed
        got = base * (0.45 + 0.55 * clamp(self.integrity / 100.0, 0, 1))
        return int(got * (1.25 if self.yard >= 3 else 1.0))

    @property
    def bio(self):
        return self.house == "ryez"

    @property
    def pods(self):
        """How many cultures can be going at once. RYEZ's parallelism is
        tanks, not hands, which is why its whole rhythm is different."""
        return POD_BASE + self.yard

    def growing(self):
        return [j for j in self.jobs if j.bio]

    def no_room(self):
        """A pod holds a culture. Mending is not a culture - it is handlers
        working on the animal itself, and it never blocks a tank."""
        if self.bio:
            return len(self.growing()) >= self.pods
        return len(self.jobs) >= len(SOCKETS) + 2

    @property
    def crew_per_job(self):
        return 4 if self.yard >= 1 else CREW_PER_JOB

    @property
    def max_crew(self):
        return MAX_CREW + (1 if self.yard >= 2 else 0)

    def refine_yield(self):
        return 2 if self.yard >= 3 else 1

    def start_refine(self):
        if self.job_on(REFINE_SLOT) or self.no_room():
            return False
        if not self.bio and self.free_crew < 1:
            return False
        cost = REFINE.scrap
        if self.scrap < cost:
            return False
        self.scrap -= cost
        self.spent += cost
        need = REFINE.days
        if self.bio:
            need = int(math.ceil(need * GESTATE))
        self.jobs.append(Job(REFINE_SLOT, 0, "build", need,
                             crew=0 if self.bio else 1, bio=self.bio))
        return True

    def price(self, part):
        """What this house pays for a part. Steel is bought and biology is
        grown, so RYEZ pays less biomass for the same thing - which is how
        it makes up the throughput it loses to gestation. The GENOME cost
        is the same either way, because that is the part nobody can grow."""
        s = part.scrap * (BIO_COST if self.bio else 1.0)
        return int(round(s)), part.alloy

    @property
    def rush_rate(self):
        return int(RUSH_PER_DAY * (0.75 if self.yard >= 1 else 1.0))

    @property
    def free_crew(self):
        return self.crew - sum(j.crew for j in self.jobs)

    def job_on(self, socket):
        for j in self.jobs:
            if j.socket == socket:
                return j
        return None

    # -- spending ---------------------------------------------------------
    def can_afford(self, scrap, alloy):
        return self.scrap >= scrap and self.alloy >= alloy

    def start_build(self, socket, part):
        if self.job_on(socket) or self.no_room():
            return False
        if not self.bio and self.free_crew < 1:
            return False
        scrap, alloy = self.price(part)
        if not self.can_afford(scrap, alloy):
            return False
        self.scrap -= scrap
        self.alloy -= alloy
        self.spent += scrap
        key = part.key if isinstance(part, (Weapon, Module)) else part.tier
        need = max(1, part.days)
        if self.bio:
            need = int(math.ceil(need * GESTATE))
        self.jobs.append(Job(socket, key, "build", need,
                             crew=0 if self.bio else 1, bio=self.bio))
        return True

    def start_repair(self, socket):
        if self.job_on(socket) or self.free_crew < 1:
            return False
        scrap, days = self.mech.repair_cost(socket)
        if self.yard >= 2:
            days = max(1, days - 1)       # the night shift
        if days <= 0 or self.scrap < scrap:
            return False
        self.scrap -= scrap
        self.spent += scrap
        self.jobs.append(Job(socket, self.mech.fit[socket], "repair", days))
        return True

    def cancel(self, job):
        """Half the scrap back and all the alloy. Losing the rare stuff to a
        change of mind would make the player afraid of the shop."""
        if job not in self.jobs:
            return
        if job.kind == "build":
            p = part_of(job.socket, job.target)
            if p:
                self.scrap += int(self.price(p)[0] * 0.5)
                self.alloy += p.alloy
        self.jobs.remove(job)

    def rush(self, job):
        """KEAL pays overtime. RYEZ cannot - forcing a pod open early just
        means the thing inside is not finished, and it grafts on flawed."""
        cost = int(math.ceil(job.left) * self.rush_rate)
        if job.rushed or self.scrap < cost or job.left <= 0:
            return False
        self.scrap -= cost
        self.spent += cost
        job.rushed = True
        job.done = job.need
        self.rushes += 1
        return True

    def set_crew(self, job, n):
        low = 0 if job.bio else 1        # a pod can be left to itself
        n = int(clamp(n, low, self.crew_per_job))
        delta = n - job.crew
        if delta > 0 and self.free_crew < delta:
            n = job.crew + self.free_crew
        job.crew = int(clamp(n, low, self.crew_per_job))

    # -- the night --------------------------------------------------------
    def end_day(self):
        """Returns "landfall", "done" or None."""
        self.news = []
        for job in list(self.jobs):
            if job.bio:
                # a pod advances one day, whoever is standing over it; what
                # the handlers do is keep the culture from drifting
                job.done += 1
                job.unstable = clamp(job.unstable + DRIFT_PER_DAY
                                     - HANDLER_CALM * job.crew, 0.0, 100.0)
            else:
                job.done += job.crew
            if job.done >= job.need - 1e-6:
                flawed = job.bio and job.faulted
                if job.kind == "repair":
                    self.mech.hp[job.socket] = self.mech.max_hp(job.socket)
                    self.news.append(sock_label(job.socket) + " MENDED")
                elif job.socket == MOD_SLOT:
                    self.mech.fit_module(job.target)
                    self.news.append(pname(MOD_SLOT, MODULES[job.target])
                                     + " IN THE " + word("rack", "RACK"))
                elif job.socket == REFINE_SLOT:
                    got = self.refine_yield()
                    if flawed:
                        got = max(1, got - 1)
                    self.alloy += got
                    self.news.append("+%d %s OUT OF THE %s"
                                     % (got, word("alloy", "ALLOY"),
                                        "VATS" if self.bio else "CRUCIBLE"))
                    flawed = False
                elif job.socket == YARD_SLOT:
                    self.yard = max(self.yard, job.target)
                    self.crew = min(self.crew, self.max_crew)
                    self.news.append(pname(YARD_SLOT, YARD[job.target - 1])
                                     + " OPEN")
                else:
                    self.mech.install(job.socket, job.target)
                    self.news.append(
                        pname(job.socket, part_of(job.socket, job.target))
                        + " " + house().verb)
                if flawed and job.socket in SOCKETS:
                    # it expressed, but not properly
                    self.mech.hp[job.socket] = (self.mech.max_hp(job.socket)
                                                * FLAWED_HP)
                    self.news.append("IT CAME OUT WRONG - "
                                     + sock_label(job.socket)
                                     + " IS AT %d%%" % round(FLAWED_HP * 100))
                self.jobs.remove(job)
        self.day += 1
        got = self.income
        self.scrap += got
        self.news.append("+%d %s" % (got, word("scrap", "SCRAP")))
        nl = self.next_landfall
        if nl is not None and self.day >= nl:
            return "landfall"
        return None

    # -- after a fight ----------------------------------------------------
    def resolve(self, fight):
        """Take the fight's outcome into the run and say what happened."""
        lines = []
        self.integrity = clamp(fight.integrity, 0.0, 100.0)
        kind = fight.kind
        if fight.over == "won":
            self.killed += 1
            got_s = int(kind.scrap * (1.30 if self.mech.has("claws") else 1.0))
            got_a = kind.alloy + (1 if self.yard >= 3 else 0)
            self.scrap += got_s
            self.alloy += got_a
            got_m = MARKS_FOR[min(self.kaiju_index, len(MARKS_FOR) - 1)]
            add_marks(got_m)
            lines.append("%s DOWN." % kind.name)
            lines.append("+%d MARKS FOR THE BODY" % got_m)
            lines.append("HARVEST: %d %s, %d %s"
                         % (got_s, word("scrap", "SCRAP"),
                            got_a, word("alloy", "ALLOY")))
            if self.crew < self.max_crew:
                self.crew += 1
                lines.append("ONE MORE PAIR OF HANDS SIGNED ON")
        else:
            self.integrity = clamp(self.integrity - kind.rampage, 0.0, 100.0)
            lines.append("THE MACHINE WENT DOWN.")
            lines.append("%s WENT THROUGH THE CITY AND BACK TO THE SEA."
                         % kind.name)
            lines.append("-%d CITY" % kind.rampage)
        if fight.wrecked:
            lines.append("%d BLOCKS LOST" % fight.wrecked)
        self.kaiju_index += 1
        if self.integrity <= 0:
            return "over", lines
        if self.kaiju_index >= len(roster_for(self.house)):
            return ("victory" if fight.over == "won" else "unfinished"), lines
        lines.append("NEXT LANDFALL: DAY %d" % SCHEDULE[self.kaiju_index])
        return None, lines

    # -- saved ------------------------------------------------------------
    def to_json(self):
        return {"house": self.house,
                "day": self.day, "scrap": self.scrap, "alloy": self.alloy,
                "crew": self.crew, "yard": self.yard,
                "integrity": round(self.integrity, 2),
                "kaiju_index": self.kaiju_index, "killed": self.killed,
                "mech": self.mech.to_json(),
                "jobs": [j.to_json() for j in self.jobs],
                "spent": self.spent, "rushes": self.rushes}

    @classmethod
    def from_json(cls, d):
        r = cls((d or {}).get("house", "keal"))
        try:
            r.day = max(1, int(d.get("day", 1)))
            r.scrap = max(0, int(d.get("scrap", 0)))
            r.alloy = max(0, int(d.get("alloy", 0)))
            r.yard = int(clamp(int(d.get("yard", 0)), 0, len(YARD)))
            r.crew = int(clamp(int(d.get("crew", 2)), 1, r.max_crew))
            r.integrity = clamp(float(d.get("integrity", 100)), 0.0, 100.0)
            r.house = d.get("house") if d.get("house") in HOUSES else "keal"
            set_house(r.house)
            r.kaiju_index = int(clamp(int(d.get("kaiju_index", 0)), 0,
                                      len(roster_for(r.house))))
            r.killed = max(0, int(d.get("killed", 0)))
            r.mech = Mech.from_json(d.get("mech"))
            r.jobs = [Job.from_json(j) for j in d.get("jobs", [])
                      if j.get("socket") in SOCKETS + (MOD_SLOT, YARD_SLOT,
                                                       REFINE_SLOT)]
            r.spent = int(d.get("spent", 0))
            r.rushes = int(d.get("rushes", 0))
            r.news = ["RUN RESUMED - DAY %d" % r.day]
        except (ValueError, TypeError, AttributeError, KeyError):
            return cls()
        return r


def save_run(run):
    data = load_save()
    data["run"] = run.to_json() if run else None
    write_save(data)


def clear_run():
    data = load_save()
    data["run"] = None
    write_save(data)


def record_end(run, won):
    data = load_save()
    best = data.get("best", {})
    if won:
        best["wins"] = int(best.get("wins", 0)) + 1
        if run.integrity > best.get("best_city", 0):
            best["best_city"] = round(run.integrity, 1)
    else:
        best["losses"] = int(best.get("losses", 0)) + 1
    best["best_kills"] = max(int(best.get("best_kills", 0)), run.killed)
    data["best"] = best
    data["run"] = None
    write_save(data)


# ---------------------------------------------------------------------------
# THE YARD
#
# The screen this game is mostly made of. Left is the machine socket by
# socket, middle is the machine itself in the gantry, right is what the
# yard could put in whichever socket you are looking at, and along the
# bottom is what the crew are doing tonight.
#
# The gantry is not a background. It is the only place the build is
# legible as a THING rather than a list, so an empty socket keeps its
# dashed outline and a job in progress is welded up from the feet.
# ---------------------------------------------------------------------------
def wrap(s, size, width, bold=True):
    f = font(size, bold)
    out, line = [], ""
    for word in s.split():
        t = (line + " " + word).strip()
        if f.size(t)[0] > width and line:
            out.append(line)
            line = word
        else:
            line = t
    if line:
        out.append(line)
    return out


def stat_line(p):
    """The one sentence of numbers a part is worth, in its own units."""
    if isinstance(p, Weapon):
        bits = []
        if p.kind == "beam":
            bits.append("%d dmg/s" % p.dmg)
            bits.append("%d heat/s" % p.heat)
        else:
            bits.append("%d x%d" % (p.dmg, p.shots) if p.shots > 1
                        else "%d dmg" % p.dmg)
            bits.append("%.2fs" % p.cd)
            bits.append("%.0f heat" % p.heat)
        bits.append("%.1f dmg/heat" % p.dph)
        if p.splash:
            bits.append("splash")
        if p.pierce:
            bits.append("pierces")
        return "  ".join(bits)
    s = getattr(p, "stats", None)
    if s is None:
        return getattr(p, "effect", "")
    bits = []
    if "speed" in s:
        bits.append("%d speed" % s["speed"])
    if s.get("boost"):
        bits.append("boost")
    if "heat" in s:
        bits.append("%d heat cap" % s["heat"])
    if "vent" in s:
        bits.append("%d vent/s" % s["vent"])
    if "dr" in s:
        bits.append("-%d per hit" % s["dr"])
    if "cycle" in s and s["cycle"] != 1.0:
        bits.append("%d%% faster" % round((1 - s["cycle"]) * 100))
    if "melee" in s and s["melee"] != 1.0:
        bits.append("+%d%% melee" % round((s["melee"] - 1) * 100))
    if "warn" in s and s["warn"]:
        bits.append("+%.2fs warning" % s["warn"])
    if "crit" in s:
        bits.append("%d%% crit" % round(s["crit"] * 100))
    if "dmg" in s:
        bits.append("+%d%% damage" % round((s["dmg"] - 1) * 100))
    bits.append("%d hp" % p.hp)
    return "  ".join(bits)


def draw_tank(surf, rect, gy, inner, t):
    """RYEZ's half of the gantry: a vat with something growing in it."""
    glass = pygame.Rect(inner.x + 26, inner.y + 8, inner.w - 52,
                        gy - inner.y - 4)
    pygame.draw.rect(surf, (14, 22, 24), glass, border_radius=26)
    fluid = glass.inflate(-10, -10)
    fluid.h -= 8
    pygame.draw.rect(surf, (22, 44, 40), fluid, border_radius=22)
    for i in range(30):                        # bubbles going up the column
        rn = (i * 97) % 211 / 211.0
        bx = fluid.x + 14 + rn * (fluid.w - 28)
        by = fluid.bottom - ((t * (26 + rn * 40) + i * 47) % fluid.h)
        pygame.draw.circle(surf, (90, 150, 130), (bx, by), 1 + (i % 3))
    pygame.draw.rect(surf, (52, 92, 84), glass, 3, border_radius=26)
    for k in range(3):                         # rings round the vat
        y = glass.y + 40 + k * (glass.h - 80) / 2.0
        pygame.draw.rect(surf, (44, 74, 70), (glass.x - 4, y, glass.w + 8, 7),
                         border_radius=3)
    pygame.draw.rect(surf, (46, 56, 62),
                     (glass.x - 14, glass.y - 10, glass.w + 28, 18),
                     border_radius=5)
    for fx in (glass.x + 40, glass.right - 40):   # feed pipes
        pygame.draw.rect(surf, (58, 70, 66), (fx - 5, inner.y, 10,
                                              glass.y - inner.y + 12))
        blit_glow(surf, (fx, glass.y + 26), 30, (90, 190, 140), 34)
    # the catwalk the handlers stand on
    pygame.draw.rect(surf, (44, 47, 60), (inner.x + 4, gy - 128, inner.w - 8, 7))
    pygame.draw.rect(surf, (28, 30, 40), (inner.x + 4, gy - 128, inner.w - 8, 7),
                     1)


def draw_gantry(surf, rect, run, t, sel=None):
    """The cage the machine stands in, and the people working on it."""
    panel(surf, rect, (15, 16, 22), LINE, 6)
    gy = rect.bottom - 44
    inner = rect.inflate(-24, -24)
    # floor
    pygame.draw.rect(surf, (26, 27, 35), (rect.x + 2, gy, rect.w - 4,
                                          rect.bottom - gy - 2))
    pygame.draw.line(surf, (60, 64, 80), (rect.x + 4, gy), (rect.right - 4, gy), 2)
    for i in range(7):
        x = rect.x + 20 + i * (rect.w - 40) / 6.0
        pygame.draw.line(surf, (34, 36, 46), (x, gy + 4), (x, rect.bottom - 6), 1)
    if CURRENT["house"] == "ryez":
        draw_tank(surf, rect, gy, inner, t)
        draw_mech_front(surf, run.mech, rect.centerx + 26, gy - 26, 0.84,
                        {j.socket: (j.target, j.prog) for j in run.jobs}, t)
        levels = [gy - 128]
        slot = 0
        for j in run.jobs:
            for c in range(j.crew):
                side = -1 if (slot % 2 == 0) else 1
                x = clamp(rect.centerx + side * (132 + (slot // 2) * 30),
                          inner.x + 26, inner.right - 26)
                draw_worker(surf, x, levels[0], t + slot * 1.7,
                            j.socket == sel)
                slot += 1
        for i in range(run.free_crew):
            draw_worker(surf, inner.x + 44 + i * 26, gy, t + i * 2.3, False,
                        idle=True)
        return
    # the two trusses
    for tx in (inner.x + 16, inner.right - 16):
        pygame.draw.rect(surf, (48, 52, 68), (tx - 7, inner.y, 14, gy - inner.y))
        pygame.draw.rect(surf, (32, 35, 46), (tx - 7, inner.y, 14, gy - inner.y), 1)
        n = 10
        for i in range(n):
            y0 = inner.y + i * (gy - inner.y) / n
            y1 = inner.y + (i + 1) * (gy - inner.y) / n
            pygame.draw.line(surf, (66, 72, 92), (tx - 6, y0), (tx + 6, y1), 2)
    # platforms
    levels = [gy - 120, gy - 250, gy - 370]
    for i, y in enumerate(levels):
        pygame.draw.rect(surf, (44, 47, 60),
                         (inner.x + 10, y, inner.w - 20, 7))
        pygame.draw.rect(surf, (28, 30, 40),
                         (inner.x + 10, y, inner.w - 20, 7), 1)
        for k in range(0, inner.w - 20, 26):
            pygame.draw.line(surf, (60, 64, 84),
                             (inner.x + 12 + k, y), (inner.x + 12 + k, y - 9), 1)
    # floodlights
    old_clip = surf.get_clip()
    surf.set_clip(rect.inflate(-4, -4))
    for fx in (inner.x + 40, inner.right - 40):
        pygame.draw.rect(surf, (70, 74, 92), (fx - 9, inner.y + 4, 18, 11))
        cone = pygame.Surface((150, gy - inner.y))
        pygame.draw.polygon(cone, (17, 14, 9),
                            [(66, 0), (84, 0), (146, cone.get_height()),
                             (4, cone.get_height())])
        surf.blit(cone, (fx - 75, inner.y + 14), special_flags=pygame.BLEND_ADD)
        blit_glow(surf, (fx, inner.y + 15), 40, (200, 168, 106), 90)
    surf.set_clip(old_clip)
    # the machine
    draw_mech_front(surf, run.mech, rect.centerx, gy, 1.12,
                    {j.socket: (j.target, j.prog) for j in run.jobs}, t)
    # the crew, one figure per body on a job, on the platform nearest it
    HEIGHT = {"legs": 0, "armour": 0, "torso": 1, "reactor": 1, "l_arm": 1,
              "r_arm": 1, "l_wpn": 0, "r_wpn": 0, "head": 2}
    slot = 0
    for j in run.jobs:
        lvl = levels[HEIGHT.get(j.socket, 1)]
        for c in range(j.crew):
            side = -1 if (slot % 2 == 0) else 1
            x = rect.centerx + side * (118 + (slot // 2) * 34)
            x = clamp(x, inner.x + 26, inner.right - 26)
            draw_worker(surf, x, lvl, t + slot * 1.7, j.socket == sel)
            slot += 1
    idle = run.free_crew
    for i in range(idle):
        draw_worker(surf, inner.x + 44 + i * 26, gy, t + i * 2.3, False,
                    idle=True)


def draw_worker(surf, x, y, t, highlight=False, idle=False):
    """A person, eleven pixels tall, for scale and for company."""
    bob = math.sin(t * 3.0) * 1.4
    c = (196, 168, 110) if not idle else (110, 112, 126)
    pygame.draw.rect(surf, c, (x - 2, y - 11 + bob, 4, 7))
    pygame.draw.circle(surf, shade(c, 1.15), (x, y - 13 + bob), 2.4)
    sw = math.sin(t * 6.0) * 2.2 if not idle else 0.0
    pygame.draw.line(surf, shade(c, 0.8), (x, y - 4 + bob),
                     (x - 2 + sw, y + bob), 2)
    pygame.draw.line(surf, shade(c, 0.8), (x, y - 4 + bob),
                     (x + 2 - sw, y + bob), 2)
    if not idle and int(t * 5) % 3 == 0:
        blit_glow(surf, (x + 5, y - 7 + bob), 7, (255, 220, 150), 90)


class Hangar:
    """The build screen. Owns its own buttons and its own selection."""

    LIST = pygame.Rect(14, 68, 278, 528)
    GANTRY = pygame.Rect(302, 68, 486, 528)
    SHOP = pygame.Rect(798, 68, 368, 528)
    JOBS = pygame.Rect(14, 604, 916, 142)
    ENDDAY = pygame.Rect(942, 604, 224, 142)

    def __init__(self, run):
        self.run = run
        self.sel = "legs"
        self.t = 0.0
        self.toast = []
        self.spec = False
        self.rack = False
        self.night = 0.0
        self.buttons = []
        self.rack_buttons = []

    def say(self, s, bad=False):
        self.toast.append([s, 2.4, bad])
        if len(self.toast) > 3:
            self.toast.pop(0)

    # -- input ------------------------------------------------------------
    def key(self, k):
        run = self.run
        if pygame.K_1 <= k <= pygame.K_9:
            self.sel = SOCKETS[k - pygame.K_1]
            self.rack = False
            SFX.play("click", 0.5)
            return None
        if k == pygame.K_0:
            self.sel = MOD_SLOT
            self.rack = True
            SFX.play("click", 0.5)
            return None
        if k == pygame.K_y:
            self.sel = YARD_SLOT
            self.rack = False
            SFX.play("click", 0.5)
            return None
        if k == pygame.K_TAB:
            self.spec = not self.spec
            self.rack = False
            return None
        if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            return self.end_day()
        job = run.job_on(self.sel)
        if job is not None:
            if k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                run.set_crew(job, job.crew + 1)
                SFX.play("click", 0.4)
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                run.set_crew(job, job.crew - 1)
                SFX.play("click", 0.4)
            elif k == pygame.K_r:
                cost = int(math.ceil(job.left) * run.rush_rate)
                if run.rush(job):
                    self.say(word("rushed", "RUSHED") + " - %d %s"
                             % (cost, word("scrap", "SCRAP")))
                    SFX.play("rivet", 0.6)
                else:
                    self.say("CANNOT RUSH THAT", True)
                    SFX.play("deny", 0.5)
        return None

    def click(self, pos):
        run = self.run
        if self.rack:
            for b in self.rack_buttons:
                if not b.hit(pos):
                    continue
                kind, data = b.key
                if kind == "pull":
                    run.mech.pull_module(data)
                    self.say("PULLED: " + MODULES[data].name)
                    SFX.play("deny", 0.4)
                elif kind == "build":
                    if run.start_build(MOD_SLOT, data):
                        self.say("QUEUED: " + data.name)
                        SFX.play("weld", 0.5)
                    else:
                        self.say("CANNOT START THAT", True)
                        SFX.play("deny", 0.5)
                return None
            r = pygame.Rect(40, 56, W - 80, H - 112)
            if not r.collidepoint(pos):
                self.rack = False
            return None
        for b in self.buttons:
            if not b.hit(pos):
                continue
            kind, data = b.key
            SFX.play("click", 0.5)
            if kind == "sel":
                self.sel = data
                if data == MOD_SLOT:
                    self.rack = True
            elif kind == "rack":
                self.rack = True
            elif kind == "pull":
                run.mech.pull_module(data)
                self.say("PULLED: " + MODULES[data].name)
            elif kind == "build":
                if run.start_build(self.sel, data):
                    self.say("QUEUED: " + data.name)
                    SFX.play("weld", 0.5)
                elif run.job_on(self.sel):
                    self.say("THAT SOCKET IS ALREADY BEING WORKED", True)
                elif run.free_crew < 1:
                    self.say("NO CREW FREE", True)
                else:
                    self.say("NOT ENOUGH IN THE BANK", True)
                    SFX.play("deny", 0.5)
            elif kind == "refine":
                if run.start_refine():
                    self.say("INTO THE " + ("VATS" if run.bio else "CRUCIBLE"))
                    SFX.play("weld", 0.5)
                else:
                    self.say("CANNOT START THAT", True)
                    SFX.play("deny", 0.5)
            elif kind == "repair":
                if run.start_repair(self.sel):
                    self.say("REPAIR QUEUED")
                    SFX.play("weld", 0.5)
                else:
                    self.say("CANNOT START THAT REPAIR", True)
                    SFX.play("deny", 0.5)
            elif kind == "crew":
                job, n = data
                run.set_crew(job, job.crew + n)
            elif kind == "rush":
                cost = int(math.ceil(data.left) * run.rush_rate)
                if run.rush(data):
                    self.say(word("rushed", "RUSHED") + " - %d %s"
                             % (cost, word("scrap", "SCRAP")))
                    SFX.play("rivet", 0.6)
                else:
                    self.say("NOT ENOUGH IN THE BANK", True)
                    SFX.play("deny", 0.5)
            elif kind == "cancel":
                run.cancel(data)
                self.say(word("scrapped", "JOB SCRAPPED - HALF BACK"))
            elif kind == "endday":
                return self.end_day()
            elif kind == "jobsel":
                self.sel = data.socket
            return None
        return None

    def end_day(self):
        r = self.run.end_day()
        self.night = 1.0
        SFX.play("horn", 0.6)
        save_run(self.run)
        return r

    # -- frame ------------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.night = max(0.0, self.night - dt * 1.6)
        for row in self.toast:
            row[1] -= dt
        while self.toast and self.toast[0][1] <= 0:
            self.toast.pop(0)

    def draw(self, surf, mouse):
        run = self.run
        self.buttons = []
        surf.fill(BG)
        self.top_bar(surf)
        self.socket_list(surf)
        draw_gantry(surf, self.GANTRY, run, self.t, self.sel)
        self.shop(surf)
        self.job_strip(surf)
        for b in self.buttons:
            b.hover(mouse)
        for b in self.buttons:
            # "build" and "sel" are invisible hit areas laid over panels
            # that draw themselves - drawing them repaints the panel and
            # blanks it, which is exactly what the shop cards were doing.
            if b.key[0] in ("repair", "crew", "rush", "cancel", "endday",
                            "pull", "rack"):
                b.draw(surf, 18)
        if self.rack:
            self.rack_overlay(surf, mouse)
        if self.spec:
            self.spec_sheet(surf)
        for i, (s, life, bad) in enumerate(reversed(self.toast)):
            text(surf, s, 19, (W // 2, 600 - i * 24), BAD if bad else PAINT,
                 center=True, alpha=int(255 * clamp(life, 0, 1)))
        if self.night > 0.01:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((6, 7, 12, int(190 * self.night)))
            surf.blit(ov, (0, 0))
            text(surf, "DAY %d" % run.day, 52, (W // 2, H // 2 - 80), INK,
                 center=True, alpha=int(255 * min(1, self.night * 1.6)))
            for i, line in enumerate(run.news[:5]):
                text(surf, line, 21, (W // 2, H // 2 - 14 + i * 28), PAINT,
                     center=True, alpha=int(255 * min(1, self.night * 1.6)))

    def top_bar(self, surf):
        run = self.run
        r = pygame.Rect(14, 12, W - 28, 46)
        panel(surf, r, PANEL, LINE, 6)
        text(surf, "DAY %d" % run.day, 26, (r.x + 14, r.y + 10), INK)
        nl = run.days_left
        kind = run.next_kind()
        if nl is not None and kind is not None:
            urgent = nl <= 2
            s = ("LANDFALL TODAY" if nl <= 0 else
                 "LANDFALL IN %d DAY%s" % (nl, "" if nl == 1 else "S"))
            text(surf, s, 20, (r.x + 150, r.y + 14),
                 BAD if urgent else WARN)
            text(surf, kind.name, 16, (r.x + 150 + font(20).size(s)[0] + 16,
                                       r.y + 17), DIM)
        cols = [(word("scrap", "SCRAP"), str(run.scrap), PAINT),
                (word("alloy", "ALLOY"), str(run.alloy), ALLOY_C),
                (word("crew", "CREW"),
                 "%d/%d" % (run.free_crew, run.crew), INK),
                ("CITY", "%d%%" % int(run.integrity),
                 GOOD if run.integrity > 50 else
                 (WARN if run.integrity > 22 else BAD)),
                (word("built", "BUILT"),
                 "%d%%" % round(run.mech.completion() * 100), CORE)]
        x = r.right - 14
        for label, val, col in reversed(cols):
            wv = font(22).size(val)[0]
            text(surf, val, 22, (x, r.y + 12), col, right=True)
            text(surf, label, 12, (x - wv - 6, r.y + 18), FAINT, right=True)
            x -= wv + font(12).size(label)[0] + 30

    def slot_held(self, socket):
        """What is in a slot, for the two slots that are not on the body."""
        if socket == YARD_SLOT:
            return part_of(YARD_SLOT, self.run.yard or None)
        if socket == MOD_SLOT:
            return None
        return self.run.mech.held(socket)

    def slot_fit(self, socket):
        if socket == YARD_SLOT:
            return self.run.yard or None
        if socket == MOD_SLOT:
            return None
        return self.run.mech.fit[socket]

    def socket_list(self, surf):
        run = self.run
        r = self.LIST
        panel(surf, r, (15, 16, 22), LINE, 6)
        text(surf, word("sockets", "SOCKETS"), 15, (r.x + 12, r.y + 8), DIM)
        y = r.y + 30
        rows = list(SOCKETS) + [MOD_SLOT, YARD_SLOT]
        for i, s in enumerate(rows):
            row = pygame.Rect(r.x + 8, y, r.w - 16, 43)
            sel = s == self.sel
            job = run.job_on(s)
            off = s in (MOD_SLOT, YARD_SLOT)
            panel(surf, row, PANEL_HI if sel else (19, 20, 27),
                  PAINT if sel else (LINE if not off else (46, 52, 72)), 5)
            tag = "0" if s == MOD_SLOT else ("Y" if s == YARD_SLOT
                                             else str(i + 1))
            text(surf, tag, 13, (row.x + 7, row.y + 3),
                 PAINT if sel else FAINT)
            label = (word("rack", "MODULE RACK") if s == MOD_SLOT else
                     word("yard", "THE YARD") if s == YARD_SLOT
                     else sock_label(s))
            text(surf, label, 14, (row.x + 24, row.y + 3),
                 INK if sel else (DIM if not off else (150, 142, 188)))
            if s == MOD_SLOT:
                m = run.mech
                name = ", ".join(pname(MOD_SLOT, MODULES[k]).split()[0].title()
                                 for k in m.mods) or "- NOTHING IN IT -"
                text(surf, name, fit(name, 13, row.w - 66),
                     (row.x + 24, row.y + 19),
                     (206, 212, 228) if m.mods else FAINT)
                text(surf, "%d/%d" % (len(m.mods), m.bays), 13,
                     (row.right - 8, row.y + 4),
                     GOOD if len(m.mods) < m.bays else DIM, right=True)
            elif s == YARD_SLOT:
                p = self.slot_held(s)
                name = pname(s, p) if p else "- NOTHING BUILT -"
                text(surf, name, fit(name, 13, row.w - 40),
                     (row.x + 24, row.y + 19),
                     (206, 212, 228) if p else FAINT)
            else:
                p = run.mech.held(s)
                name = pname(s, p) if p else "- " + word("empty", "EMPTY") + " -"
                need = NEEDS.get(s)
                if p is None and need and run.mech.fit[need] is None:
                    name = "- NEEDS " + sock_label(need) + " -"
                text(surf, name, fit(name, 13, row.w - 40),
                     (row.x + 24, row.y + 19),
                     (206, 212, 228) if p else FAINT)
                if p is not None:
                    f = run.mech.hp[s] / max(1.0, run.mech.max_hp(s))
                    col = GOOD if f > 0.6 else (WARN if f > 0.25 else BAD)
                    bar(surf, pygame.Rect(row.x + 24, row.y + 34,
                                          row.w - 38, 5), f,
                        col if f > 0 else (70, 64, 70))
            if job is not None:
                bar(surf, pygame.Rect(row.x + 24, row.y + 34, row.w - 38, 5),
                    job.prog, CORE)
                text(surf, "%dd" % job.days_left(), 12,
                     (row.right - 8, row.y + 20), CORE, right=True)
            self.buttons.append(Button(row, "", ("sel", s)))
            y += 45

    def shop(self, surf):
        run = self.run
        r = self.SHOP
        panel(surf, r, (15, 16, 22), LINE, 6)
        s = self.sel
        title = (word("rack", "MODULE RACK") if s == MOD_SLOT else
                 word("yard", "THE YARD") if s == YARD_SLOT else sock_label(s))
        text(surf, title, 22, (r.x + 14, r.y + 10), PAINT)
        if s == MOD_SLOT:
            self.rack_panel(surf, r)
            return
        held = self.slot_held(s)
        y = r.y + 42
        if held is not None:
            text(surf, word("fitted", "FITTED") + ": " + pname(s, held), 15,
                 (r.x + 14, y), INK)
            y += 20
            line = (peffect(held) if isinstance(held, (YardUp, Refine))
                    else stat_line(held))
            for ln in wrap(line, 13, r.w - 28)[:2]:
                text(surf, ln, 13, (r.x + 14, y), DIM)
                y += 16
            y += 6
            if s != YARD_SLOT:
                dmgf = run.mech.damage_frac(s)
                if dmgf > 0.001:
                    cost, days = run.mech.repair_cost(s)
                    if run.yard >= 2:
                        days = max(1, days - 1)
                    lab = (word("wrecked", "WRECKED") if dmgf >= 0.999
                           else "%d%% DAMAGE" % round(dmgf * 100))
                    text(surf, lab, 14, (r.x + 14, y), BAD)
                    self.buttons.append(Button(
                        pygame.Rect(r.x + 150, y - 4, r.w - 164, 26),
                        "%s  %d / %dd" % (word("repair", "REPAIR"), cost,
                                          days), ("repair", s),
                        enabled=run.scrap >= cost and run.job_on(s) is None
                        and run.free_crew > 0, tone=GOOD))
                    y += 30
        else:
            text(surf, "NOTHING BUILT" if s == YARD_SLOT
                 else word("empty", "EMPTY"), 15, (r.x + 14, y), FAINT)
            y += 24
        job = run.job_on(s)
        if job is not None:
            box = pygame.Rect(r.x + 10, y, r.w - 20, 62)
            panel(surf, box, (22, 26, 34), CORE, 5)
            text(surf, "ON THE JOB: " + job.label(),
                 fit("ON THE JOB: " + job.label(), 15, box.w - 20),
                 (box.x + 10, box.y + 8), CORE)
            bar(surf, pygame.Rect(box.x + 10, box.y + 30, box.w - 20, 8),
                job.prog, CORE)
            text(surf, "%d %s   %d DAY%s LEFT"
                 % (job.crew, word("crew", "CREW"), job.days_left(),
                    "" if job.days_left() == 1 else "S"),
                 13, (box.x + 10, box.y + 42), DIM)
            return
        need = NEEDS.get(s)
        if need and run.mech.fit[need] is None:
            text(surf, "Nothing hangs off an arm that is not there.", 14,
                 (r.x + 14, y), FAINT)
            return
        opts = options_for(s, self.slot_fit(s))
        if s == YARD_SLOT:
            opts = list(opts) + [REFINE]
        if not opts:
            text(surf, "This is as good as it gets.", 14, (r.x + 14, y), FAINT)
            return
        for p in opts[:5]:
            card = pygame.Rect(r.x + 10, y, r.w - 20, 84)
            ok = (run.can_afford(*run.price(p)) and not run.no_room()
                  and (run.bio or run.free_crew > 0))
            panel(surf, card, (20, 22, 30) if ok else (17, 18, 24), LINE, 5)
            nm = pname(s, p)
            text(surf, nm, fit(nm, 17, card.w - 130),
                 (card.x + 10, card.y + 7), INK if ok else FAINT)
            self.price(surf, card, p, run)
            line = (peffect(p) if isinstance(p, (YardUp, Refine))
                    else stat_line(p))
            text(surf, line, fit(line, 12, card.w - 20),
                 (card.x + 10, card.y + 28), CORE)
            for i, ln in enumerate(wrap(pblurb(s, p), 12, card.w - 20)[:2]):
                text(surf, ln, 12, (card.x + 10, card.y + 44 + i * 14), DIM,
                     bold=False)
            act = ("refine", None) if isinstance(p, Refine) else ("build", p)
            if isinstance(p, Refine):
                ok = ok and run.job_on(REFINE_SLOT) is None
            self.buttons.append(Button(card, "", act, enabled=ok))
            if ok:
                pygame.draw.rect(surf, ALLOY_C if isinstance(p, Refine)
                                 else PAINT, card, 1, border_radius=5)
            y += 90
            if y > r.bottom - 40:
                break

    def price(self, surf, card, p, run):
        """Cost and time along the top right of a card, in this house's
        money and this house's calendar."""
        cost, alloy = run.price(p)
        days = p.days
        if run.bio and not isinstance(p, (YardUp, Refine)):
            days = int(math.ceil(days * GESTATE))
        cx = card.right - 10
        text(surf, "%dd" % days, 15, (cx, card.y + 8), DIM, right=True)
        cx -= font(15).size("%dd" % days)[0] + 12
        if p.alloy:
            lab = "%d" % alloy
            text(surf, lab, 15, (cx, card.y + 8),
                 ALLOY_C if run.alloy >= alloy else BAD, right=True)
            text(surf, "AL", 11, (cx - font(15).size(lab)[0] - 3, card.y + 12),
                 FAINT, right=True)
            cx -= font(15).size(lab)[0] + font(11).size("AL")[0] + 12
        text(surf, "%d" % cost, 15, (cx, card.y + 8),
             PAINT if run.scrap >= cost else BAD, right=True)

    def rack_panel(self, surf, r):
        """What is in the rack now, and the way into the full list."""
        run = self.run
        m = run.mech
        y = r.y + 42
        text(surf, "%d OF %d %s USED" % (len(m.mods), m.bays,
                                         word("bays", "BAYS")), 15,
             (r.x + 14, y), GOOD if len(m.mods) < m.bays else DIM)
        y += 22
        text(surf, "The %s decides how many there are."
             % sock_label("torso").lower(), 12, (r.x + 14, y), FAINT,
             bold=False)
        y += 24
        for k in m.mods:
            mod = MODULES[k]
            box = pygame.Rect(r.x + 10, y, r.w - 20, 56)
            panel(surf, box, (21, 24, 31), (60, 80, 70), 5)
            nm = pname(MOD_SLOT, mod)
            text(surf, nm, fit(nm, 16, box.w - 90),
                 (box.x + 10, box.y + 6), INK)
            for i, ln in enumerate(wrap(peffect(mod), 12, box.w - 20)[:2]):
                text(surf, ln, 12, (box.x + 10, box.y + 26 + i * 14), CORE)
            self.buttons.append(Button(
                pygame.Rect(box.right - 76, box.y + 4, 68, 20), "PULL",
                ("pull", k), tone=BAD))
            y += 62
        for _ in range(m.bays - len(m.mods)):
            box = pygame.Rect(r.x + 10, y, r.w - 20, 40)
            dashed_poly(surf, [box.topleft, box.topright, box.bottomright,
                               box.bottomleft], (58, 62, 82), 2)
            text(surf, word("empty", "EMPTY") + " BAY", 14, box.center,
                 FAINT, center=True)
            y += 46
        job = run.job_on(MOD_SLOT)
        if job is not None:
            box = pygame.Rect(r.x + 10, y, r.w - 20, 50)
            panel(surf, box, (22, 26, 34), CORE, 5)
            text(surf, "BUILDING: " + job.label(),
                 fit("BUILDING: " + job.label(), 15, box.w - 20),
                 (box.x + 10, box.y + 6), CORE)
            bar(surf, pygame.Rect(box.x + 10, box.y + 28, box.w - 20, 8),
                job.prog, CORE)
            y += 56
        self.buttons.append(Button(
            pygame.Rect(r.x + 10, min(y, r.bottom - 58), r.w - 20, 48),
            "OPEN THE RACK", ("rack", None), tone=PAINT, primary=True))

    def rack_overlay(self, surf, mouse):
        """All thirteen of them at once, because the choice is the point."""
        run = self.run
        m = run.mech
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((5, 6, 10, 210))
        surf.blit(ov, (0, 0))
        r = pygame.Rect(40, 56, W - 80, H - 112)
        panel(surf, r, (16, 18, 25), PAINT, 8)
        text(surf, word("rack", "THE RACK"), 28, (r.x + 22, r.y + 12), PAINT)
        text(surf, "%d OF %d %s USED" % (len(m.mods), m.bays,
                                         word("bays", "BAYS")), 18,
             (r.x + 260, r.y + 20), GOOD if len(m.mods) < m.bays else WARN)
        text(surf, "%s %d    %s %d    %s %d FREE"
             % (word("scrap", "SCRAP"), run.scrap, word("alloy", "ALLOY"),
                run.alloy, word("crew", "CREW"), run.free_crew), 16,
             (r.right - 22, r.y + 20), DIM, right=True)
        job = run.job_on(MOD_SLOT)
        cols, cw, ch = 3, (r.w - 44) // 3, 104
        self.rack_buttons = []
        for i, mod in enumerate(MODULE_LIST):
            cx = r.x + 16 + (i % cols) * cw
            cy = r.y + 56 + (i // cols) * (ch + 8)
            card = pygame.Rect(cx, cy, cw - 10, ch)
            inside = m.has(mod.key)
            building = job is not None and job.target == mod.key
            room = len(m.mods) < m.bays
            afford = run.can_afford(*run.price(mod))
            can = (not inside and not building and job is None and room
                   and afford and not run.no_room()
                   and (run.bio or run.free_crew > 0))
            edge = (GOOD if inside else CORE if building
                    else PAINT if can else LINE)
            panel(surf, card, (22, 28, 26) if inside else
                  (20, 24, 32) if building else
                  (20, 22, 30) if can else (16, 17, 23), edge, 5)
            nm = pname(MOD_SLOT, mod)
            text(surf, nm, fit(nm, 17, card.w - 108),
                 (card.x + 10, card.y + 7),
                 INK if (inside or can or building) else FAINT)
            if inside:
                text(surf, "IN THE " + word("rack", "RACK"), 12,
                     (card.right - 10, card.y + 10), GOOD, right=True)
            elif building:
                text(surf, "%dd" % job.days_left(), 12,
                     (card.right - 10, card.y + 10), CORE, right=True)
            else:
                self.price(surf, card, mod, run)
            for k, ln in enumerate(wrap(peffect(mod), 12, card.w - 20)[:2]):
                text(surf, ln, 12, (card.x + 10, card.y + 28 + k * 14), CORE)
            for k, ln in enumerate(wrap(pblurb(MOD_SLOT, mod), 12,
                                        card.w - 20)[:2]):
                text(surf, ln, 12, (card.x + 10, card.y + 60 + k * 14), DIM,
                     bold=False)
            act = ("pull", mod.key) if inside else ("build", mod)
            b = Button(card, "", act, enabled=inside or can)
            b.hover(mouse)
            if b.hot:
                pygame.draw.rect(surf, BAD if inside else PAINT, card, 2,
                                 border_radius=5)
                text(surf, "CLICK TO PULL IT" if inside else "CLICK TO BUILD",
                     12, (card.right - 10, card.bottom - 16),
                     BAD if inside else PAINT, right=True)
            self.rack_buttons.append(b)
        note = ("Every bay is full. Pull one, or grow a bigger %s."
                % sock_label("torso").lower()
                if len(m.mods) >= m.bays else
                "One job at a time in here." if job is not None else
                "Three bays, thirteen of them. That is the whole point.")
        text(surf, note, 15, (r.centerx, r.bottom - 26), FAINT, center=True)

    def job_strip(self, surf):
        run = self.run
        r = self.JOBS
        bio = run.bio
        panel(surf, r, (15, 16, 22), LINE, 6)
        text(surf, "IN THE PODS" if bio else "TONIGHT", 15,
             (r.x + 12, r.y + 8), DIM)
        if bio:
            text(surf, "%d OF %d PODS RUNNING    %d OF %d %s ON THEM"
                 % (len(run.jobs), run.pods, run.crew - run.free_crew,
                    run.crew, word("crew", "CREW")), 13,
                 (r.right - 12, r.y + 10), FAINT, right=True)
        else:
            text(surf, "%d OF %d %s ASSIGNED"
                 % (run.crew - run.free_crew, run.crew, word("crew", "CREW")),
                 13, (r.right - 12, r.y + 10), FAINT, right=True)
        if not run.jobs:
            text(surf, "Every pod is empty. Nothing is growing." if bio else
                 "Nobody is working on anything. That is a whole day.",
                 17, (r.centerx, r.centery), FAINT, center=True)
        slots = max(1, min(4, run.pods if bio else 4))
        cw = (r.w - 24) / slots
        for i, j in enumerate(run.jobs[:4]):
            box = pygame.Rect(r.x + 12 + i * cw, r.y + 28, cw - 8, 102)
            hot = j.socket == self.sel
            panel(surf, box, (21, 23, 31), CORE if hot else LINE, 5)
            head = ("POD %d - " % (i + 1) if bio else "") + (
                word("rack", "RACK") if j.socket == MOD_SLOT else
                word("yard", "YARD") if j.socket == YARD_SLOT else
                word("alloy", "ALLOY") if j.socket == REFINE_SLOT
                else sock_label(j.socket))
            text(surf, head, fit(head, 12, box.w - 16), (box.x + 8, box.y + 5),
                 FAINT)
            text(surf, j.label(), fit(j.label(), 16, box.w - 16),
                 (box.x + 8, box.y + 18), INK)
            bar(surf, pygame.Rect(box.x + 8, box.y + 40, box.w - 16, 8),
                j.prog, CORE)
            dl = j.days_left()
            text(surf, "%d DAY%s" % (dl, "" if dl == 1 else "S"), 14,
                 (box.x + 8, box.y + 52), WARN)
            bw = 24
            if bio:
                # the second bar is the one that decides whether it works
                f = clamp(j.unstable / 100.0, 0, 1)
                col = GOOD if f < 0.28 else (WARN if f < FAULT_AT / 100.0
                                             else BAD)
                bw2 = box.w - 106
                bar(surf, pygame.Rect(box.x + 8, box.y + 68, bw2, 7), f, col)
                mark = box.x + 8 + bw2 * (FAULT_AT / 100.0)
                pygame.draw.line(surf, INK, (mark, box.y + 66),
                                 (mark, box.y + 77), 1)
                lab = "DRIFT" if not j.faulted else "WILL BE WRONG"
                text(surf, lab, fit(lab, 11, 92),
                     (box.right - 8, box.y + 68), FAINT if not j.faulted
                     else BAD, right=True)
                text(surf, "%d ON IT" % j.crew, 13,
                     (box.right - bw * 2 - 18, box.y + 50), INK, right=True)
            else:
                text(surf, "%d %s" % (j.crew, word("crew", "CREW")), 13,
                     (box.right - bw * 2 - 20, box.y + 54), DIM, right=True)
            self.buttons.append(Button(
                pygame.Rect(box.right - bw * 2 - 12, box.y + 46, bw, 22),
                "-", ("crew", (j, -1)),
                enabled=j.crew > (0 if bio else 1)))
            self.buttons.append(Button(
                pygame.Rect(box.right - bw - 8, box.y + 46, bw, 22),
                "+", ("crew", (j, 1)),
                enabled=j.crew < run.crew_per_job and run.free_crew > 0))
            cost = int(math.ceil(j.left) * run.rush_rate)
            self.buttons.append(Button(
                pygame.Rect(box.x + 8, box.y + (80 if bio else 68),
                            box.w * 0.52, 20),
                ("FORCE %d" if bio else "RUSH %d") % cost, ("rush", j),
                enabled=not j.rushed and run.scrap >= cost and j.left > 0,
                tone=RUST))
            self.buttons.append(Button(
                pygame.Rect(box.x + 12 + box.w * 0.52,
                            box.y + (80 if bio else 68), box.w * 0.34, 20),
                "DROP", ("cancel", j), tone=BAD))
        if len(run.jobs) > 4:
            text(surf, "+%d MORE %s" % (len(run.jobs) - 4,
                                        "GROWING" if bio else "RUNNING"), 13,
                 (r.right - 12, r.bottom - 20), WARN, right=True)
        e = self.ENDDAY
        self.buttons.append(Button(e, "END DAY", ("endday", None), tone=PAINT,
                                   primary=True))
        nl = run.days_left
        if nl is not None and nl <= 1:
            text(surf, "THEY COME TOMORROW", 13, (e.centerx, e.bottom - 22),
                 BAD, center=True)

    def spec_sheet(self, surf):
        """TAB. What the build actually adds up to, in the fight's units."""
        m = self.run.mech
        r = pygame.Rect(W // 2 - 320, 80, 640, 550)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((5, 6, 10, 200))
        surf.blit(ov, (0, 0))
        panel(surf, r, (17, 19, 26), PAINT, 8)
        text(surf, "SPEC SHEET", 28, (r.centerx, r.y + 14), PAINT, center=True)
        rows = [("WALKING SPEED", "%d" % m.speed if m.speed else "CANNOT WALK"),
                ("BOOST", "yes" if m.can_boost else "no"),
                ("HEAT CEILING", "%d" % m.heat_cap),
                ("VENTING", "%d / s" % m.vent),
                ("PLATE", "-%d per hit" % m.dr if m.dr else "none"),
                ("BRACING", "takes %d%%" % round(m.brace_factor * 100)),
                ("CORE", "%d hp" % m.hp["torso"]),
                ("CRIT", "%d%%" % round(m.crit * 100)),
                ("WARNING", "%.2f s" % m.warn),
                (word("rack", "RACK"),
                 ", ".join(pname(MOD_SLOT, MODULES[k]) for k in m.mods)
                 or "%d empty" % m.bays),
                (word("yard", "YARD"),
                 (pname(YARD_SLOT, YARD[self.run.yard - 1])
                  if self.run.yard else "nothing built"))]
        y = r.y + 54
        for k, v in rows:
            text(surf, k, 16, (r.x + 26, y), DIM)
            text(surf, v, fit(v, 17, r.w - 316), (r.x + 290, y), INK)
            y += 24
        y += 8
        pygame.draw.line(surf, LINE, (r.x + 20, y), (r.right - 20, y))
        y += 12
        text(surf, "SUSTAINED DAMAGE - what the reactor will pay for", 14,
             (r.x + 26, y), PAINT)
        y += 22
        best = 0.0
        for side in ("l", "r"):
            w = m.weapon(side)
            lab = "LEFT " if side == "l" else "RIGHT"
            if w is None:
                text(surf, lab + "  -", 15, (r.x + 26, y), FAINT)
                y += 22
                continue
            burst = (w.dmg * w.shots / max(0.05, w.cd * m.arm_stat(side, "cycle", 1.0))
                     if w.kind != "beam" else w.dmg)
            sustain = m.vent * w.dph
            best = max(best, sustain)
            text(surf, lab, 15, (r.x + 26, y), DIM)
            wn = pname("l_wpn" if side == "l" else "r_wpn", w)
            text(surf, wn, fit(wn, 15, 200), (r.x + 96, y), INK)
            text(surf, "burst %d/s" % round(burst), 14, (r.x + 300, y), DIM)
            text(surf, "sustain %d/s" % round(sustain), 14, (r.x + 430, y),
                 GOOD)
            y += 22
        y += 6
        text(surf, "Heat is shared. Two weapons burst harder, they do not "
             "sustain harder.", 13, (r.x + 26, y), FAINT, bold=False)
        y += 20
        kind = self.run.next_kind()
        if kind is not None and best > 0:
            secs = kind.hp / max(1.0, best)
            text(surf, "%s has %d hp - about %d seconds of perfect shooting."
                 % (kind.name, kind.hp, round(secs)), 14, (r.x + 26, y),
                 WARN if secs > 110 else DIM)
        text(surf, "TAB to close", 14, (r.centerx, r.bottom - 24), FAINT,
             center=True)


# ---------------------------------------------------------------------------
# THE SCREENS EITHER SIDE OF A FIGHT
# ---------------------------------------------------------------------------
class Brief:
    """Landfall. Here is what is coming, here is what you finished."""

    def __init__(self, run, kind):
        self.run = run
        self.kind = kind
        self.t = 0.0
        self.buttons = []

    def stand_cost(self):
        """Always worse than losing the fight, or nobody would ever fight -
        but not so much worse that it is never the right call."""
        return int(self.kind.rampage + self.kind.wreck * 4)

    def draw(self, surf, mouse):
        run, k = self.run, self.kind
        surf.fill(BG)
        sky(surf, self.t)
        pygame.draw.rect(surf, (10, 11, 16), (0, 0, W, 120))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((8, 9, 14, 150))
        surf.blit(ov, (0, 0))
        draw_kaiju(surf, k, W - 380, H - 120, 0.92, self.t, self.t * 2.0, 1.0,
                   -1, 0.0, 0.0, 0.0, 0.35 + 0.25 * math.sin(self.t * 2))
        text(surf, "LANDFALL", 20, (60, 44), BAD)
        text(surf, k.name, 66, (60, 66), INK)
        text(surf, k.title.upper(), 20, (60, 136), PAINT)
        y = 182
        for line in wrap(k.note, 18, 560):
            text(surf, line, 18, (60, y), DIM, bold=False)
            y += 24
        y += 14
        rows = [("HEALTH", "%d" % k.hp), ("SPEED", "%d" % k.speed),
                ("HIDE", "-%d per hit" % k.dr if k.dr else "soft"),
                ("POISE", "hard to stagger" if k.poise >= 1.6 else
                 "staggers" if k.poise <= 1.1 else "braced"),
                ("HARVEST", "%d scrap  %d alloy" % (k.scrap, k.alloy)
                 if k.scrap else "nothing left to salvage")]
        for a, b in rows:
            text(surf, a, 15, (60, y), FAINT)
            text(surf, b, 17, (190, y - 1), INK)
            y += 24
        y += 16
        text(surf, "IT WILL WALK TO THE CITY. IT WILL ONLY STOP FOR YOU.",
             17, (60, y), WARN)

        m = run.mech
        p = pygame.Rect(56, 404, 470, 172)
        panel(surf, p, (16, 18, 25), LINE, 6)
        text(surf, "%s - %d%% %s" % (word("machine", "THE MACHINE"),
                                      round(m.completion() * 100),
                                      word("built", "BUILT")),
             19, (p.x + 14, p.y + 10), PAINT)
        ls = []
        ls.append("WALK %d" % m.speed if m.speed
                  else "NO %s - IT CANNOT MOVE" % sock_label("legs"))
        wl, wr = m.weapon("l"), m.weapon("r")
        ls.append("LEFT  " + (pname("l_wpn", wl) if wl
                              else word("empty", "EMPTY")))
        ls.append("RIGHT " + (pname("r_wpn", wr) if wr
                              else word("empty", "EMPTY")))
        ls.append("CORE %d HP   PLATE -%d   %s %d @ %d/s"
                  % (m.hp["torso"], m.dr, word("heat", "HEAT"),
                     m.heat_cap, m.vent))
        for i, s in enumerate(ls):
            text(surf, s, 16, (p.x + 14, p.y + 40 + i * 26),
                 INK if not s.startswith("NO LEGS") else BAD)
        broken = [sock_label(s) for s in SOCKETS if m.fit[s] is not None
                  and m.hp[s] <= 0]
        if broken:
            text(surf, "STILL " + word("wrecked", "WRECKED") + ": "
                 + ", ".join(broken), 14,
                 (p.x + 14, p.bottom - 26), BAD)
        rk = pygame.Rect(p.x, p.bottom + 8, p.w, 76)
        panel(surf, rk, (16, 18, 25), LINE, 6)
        text(surf, word("rack", "THE RACK"), 15, (rk.x + 14, rk.y + 7), PAINT)
        if not m.mods:
            text(surf, "Nothing in the bays.", 14, (rk.x + 110, rk.y + 8),
                 FAINT)
        for i, k in enumerate(m.mods):
            mod = MODULES[k]
            text(surf, pname(MOD_SLOT, mod), 14,
                 (rk.x + 14, rk.y + 26 + i * 16), INK)
            eff = peffect(mod)
            text(surf, eff, fit(eff, 12, rk.w - 200),
                 (rk.x + 190, rk.y + 27 + i * 16), CORE)

        self.buttons = []
        ready = m.ready()
        b1 = Button(pygame.Rect(56, 672, 300, 58),
                    word("deploy", "DEPLOY") + ("" if ready else " ANYWAY"),
                    ("go", None),
                    tone=PAINT if ready else RUST, primary=True)
        b2 = Button(pygame.Rect(372, 672, 300, 58),
                    "STAND DOWN  -%d CITY" % self.stand_cost(),
                    ("stand", None), tone=BAD)
        self.buttons = [b1, b2]
        for b in self.buttons:
            b.hover(mouse)
            b.draw(surf, 24)
        if not ready:
            text(surf, "Nothing to walk on or nothing to hit with.", 15,
                 (686, 694), BAD)

    def click(self, pos):
        for b in self.buttons:
            if b.hit(pos):
                SFX.play("click", 0.6)
                return b.key[0]
        return None


class After:
    """What the night cost. The only screen that is allowed to be slow."""

    def __init__(self, run, fight, lines, ending=None):
        self.run = run
        self.fight = fight
        self.lines = lines
        self.ending = ending
        self.t = 0.0
        self.btn = Button(pygame.Rect(W // 2 - 160, H - 118, 320, 62),
                          "BACK TO THE YARD", ("go", None), primary=True)

    def draw(self, surf, mouse):
        surf.fill(BG)
        sky(surf, 0.0)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((8, 9, 14, 170))
        surf.blit(ov, (0, 0))
        won = self.fight is None or self.fight.over == "won"
        title = "HELD" if won else "THE LINE BROKE"
        text(surf, title, 62, (W // 2, 74), GOOD if won else BAD, center=True)
        y = 176
        for line in self.lines:
            text(surf, line, 22, (W // 2, y), INK, center=True)
            y += 32
        if self.fight is not None:
            f = self.fight
            y += 16
            stats = [("DAMAGE DEALT", "%d" % int(f.dealt)),
                     ("DAMAGE TAKEN", "%d" % int(f.taken)),
                     ("TIME", "%d:%02d" % (int(f.t) // 60, int(f.t) % 60))]
            for a, b in stats:
                text(surf, a, 15, (W // 2 - 20, y), FAINT, right=True)
                text(surf, b, 18, (W // 2 + 20, y - 1), DIM, left=True)
                y += 26
        m = self.run.mech
        draw_mech_front(surf, m, W // 2, H - 150, 0.46, {}, self.t)
        self.btn.label = ("SEE HOW IT ENDED" if self.ending
                          else "BACK TO THE YARD")
        self.btn.hover(mouse)
        self.btn.draw(surf, 24)
        if not self.ending and marks() > 0:
            self.shop_btn = Button(pygame.Rect(W // 2 - 170, H - 54, 340, 38),
                                   "THE HENDRAS ARE HERE - %d MARKS"
                                   % marks(), ("shop", None), tone=ALLOY_C)
            self.shop_btn.hover(mouse)
            self.shop_btn.draw(surf, 17)
        else:
            self.shop_btn = None

    def click(self, pos):
        if getattr(self, "shop_btn", None) and self.shop_btn.hit(pos):
            SFX.play("click", 0.6)
            return "shop"
        if self.btn.hit(pos):
            SFX.play("click", 0.6)
            return "go"
        return None



# ---------------------------------------------------------------------------
# SIGNING
#
# The first decision of a run, and the only one you cannot take back. It
# picks your body, your vocabulary and - because the two companies only
# ever fight each other - the whole of the opposing roster.
# ---------------------------------------------------------------------------
class Choose:
    CARD_W, CARD_H = 470, 536

    def __init__(self):
        self.t = 0.0
        self.hot = None
        self.cards = {}
        self.demo = {}
        for key in ("keal", "ryez"):
            set_house(key)
            m = Mech()
            for s, v in (("legs", 2), ("torso", 2), ("l_arm", 2),
                         ("r_arm", 1), ("head", 2), ("reactor", 2),
                         ("l_wpn", "pile"), ("r_wpn", "auto"),
                         ("armour", 1)):
                m.install(s, v)
            self.demo[key] = m
        set_house("keal")

    def rects(self):
        y = 146
        gap = 60
        left = W // 2 - self.CARD_W - gap // 2
        return {"keal": pygame.Rect(left, y, self.CARD_W, self.CARD_H),
                "ryez": pygame.Rect(left + self.CARD_W + gap, y,
                                    self.CARD_W, self.CARD_H)}

    def draw(self, surf, mouse):
        surf.fill(BG)
        sky(surf, self.t * 0.1)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((8, 9, 14, 176))
        surf.blit(ov, (0, 0))
        text(surf, "SIGN WITH", 19, (W // 2, 26), DIM, center=True)
        text(surf, "ELEVEN YEARS OVER THE SAME WATERFRONT", 33,
             (W // 2, 58), INK, center=True)
        text(surf, "Whichever one you sign with, the other one's product "
             "walks up that road at you.", 16, (W // 2, 108), FAINT,
             center=True)
        self.cards = self.rects()
        self.hot = None
        for key, r in self.cards.items():
            if r.collidepoint(mouse):
                self.hot = key
        for key, r in self.cards.items():
            self.card(surf, key, r, key == self.hot)
        text(surf, "click a house, or 1 and 2      ESC goes back", 15,
             (W // 2, H - 30), FAINT, center=True)

    def card(self, surf, key, r, hot):
        ho = HOUSES[key]
        panel(surf, r, (22, 24, 32) if hot else (16, 18, 24),
              ho.colour if hot else LINE, 8, 2 if hot else 1)
        if hot:
            blit_glow(surf, (r.centerx, r.y + 110), 150, ho.colour, 26)
        ho.logo(surf, r.centerx, r.y + 96, 60, self.t, True)
        text(surf, ho.name, 38, (r.centerx, r.y + 166), ho.colour,
             center=True)
        text(surf, ho.tagline, 18, (r.centerx, r.y + 208), DIM, center=True)
        y = r.y + 240
        for line in wrap(ho.pitch, 15, r.w - 76)[:4]:
            text(surf, line, 15, (r.centerx, y), (168, 176, 196),
                 center=True, bold=False)
            y += 19
        pygame.draw.line(surf, LINE, (r.x + 40, r.y + 326),
                         (r.right - 40, r.y + 326))
        # what you make, drawn small, and what it will be standing against
        set_house(key)
        draw_mech_front(surf, self.demo[key], r.centerx - 108, r.bottom - 40,
                        0.33, {}, self.t)
        foe = roster_for(key)[5]
        if foe.family == "bio":
            draw_kaiju(surf, foe, r.centerx + 132, r.bottom - 40, 0.30,
                       self.t, self.t * 1.6, 0.7, -1)
        else:
            pose = Pose()
            pose.face = -1
            pose.walk = self.t * 1.6
            pose.moving = 0.7
            tint = foe.hide
            draw_mech_side(surf, foe.rig, r.centerx + 132, r.bottom - 40,
                           0.30 * foe.scale, self.t, pose,
                           tones={"main": tint, "dark": shade(tint, 0.6),
                                  "light": shade(tint, 1.3),
                                  "trim": mix(tint, KEAL_GOLD, 0.55),
                                  "plate": mix(tint, (150, 136, 112), 0.5),
                                  "hollow": tint})
        set_house("keal")
        text(surf, "YOU BUILD" if key == "keal" else "YOU GROW", 12,
             (r.centerx - 108, r.bottom - 26), FAINT, center=True)
        how = ("HANDS BUY SPEED" if key == "keal"
               else "HANDS BUY STABILITY")
        text(surf, how, 12, (r.centerx, r.y + 352), FAINT, center=True)
        text(surf, "YOU FIGHT", 12, (r.centerx + 132, r.bottom - 26), FAINT,
             center=True)
        names = roster_for(key)[0].name + "   then five more, ending   "             + foe.name
        text(surf, names, fit(names, 13, r.w - 60), (r.centerx, r.y + 336),
             ho.colour if hot else ho.dark, center=True)

    def click(self, pos):
        for key, r in self.rects().items():
            if r.collidepoint(pos):
                SFX.play("click", 0.7)
                return key
        return None


# ---------------------------------------------------------------------------
# THE NIGHT MARKET
#
# Two stalls under bulbs on a wire, the Hendras behind their counters facing
# out, and their stock laid out on the boards in front of them where you can
# pick a thing up and turn it over before you pay for it.
#
# Everybody here is drawn blocky and straight on, which is both the easiest
# thing to read at this size and the right look for two people who build
# things out of rectangles for a living.
# ---------------------------------------------------------------------------
SARAH_INK = (118, 176, 220)
JACK_GLASS = (128, 206, 176)

SKIN = (240, 226, 212)
SKIN_D = (206, 188, 174)
BULB = (255, 206, 132)

SARAH_HAIR = (48, 42, 56)
SARAH_SCARF = (128, 74, 172)
SARAH_WHITE = (238, 240, 245)
SARAH_BLACK = (34, 34, 41)

JACK_SUIT = (40, 40, 48)
JACK_LAPEL = (74, 76, 86)
JACK_SHIRT = (228, 231, 238)
JACK_BRASS = (172, 122, 64)
JACK_HAIR = (112, 78, 54)


def _blk(surf, x, y, w, h, col, edge=0.62, r=2):
    """A block with a darker edge. Everything here is made of these."""
    rect = pygame.Rect(int(x), int(y), int(w), int(h))
    pygame.draw.rect(surf, col, rect, border_radius=r)
    pygame.draw.rect(surf, shade(col, edge), rect, 1, border_radius=r)
    return rect


def draw_sarah_front(surf, cx, gy, h, t):
    """Black bob with the fringe across one eye, dark rectangular glasses, a
    purple scarf, and a jacket panelled white over black.

    Proportioned like the avatars they came from: the head is about as tall
    as the whole of the body you can see, which is what makes them read as
    two short people behind a counter rather than two tall ones."""
    u = h / 100.0
    bob = math.sin(t * 1.4) * 1.0 * u
    top = gy - 38 * u + bob                       # shoulders
    _blk(surf, cx - 32 * u, top, 64 * u, 50 * u, SARAH_BLACK, 0.7, 4)
    _blk(surf, cx - 32 * u, top, 64 * u, 12 * u, SARAH_WHITE, 0.7, 4)
    for sgn in (-1, 1):                           # arms, forward on the boards
        ax = cx + sgn * 38 * u
        _blk(surf, ax - 12 * u, top + 2 * u, 25 * u, 22 * u, SARAH_WHITE,
             0.7, 3)
        _blk(surf, ax - 12 * u, top + 12 * u, 25 * u, 7 * u, SARAH_BLACK,
             0.7, 2)
        _blk(surf, ax - 11 * u, top + 22 * u, 23 * u, 18 * u, SARAH_BLACK,
             0.7, 3)
        _blk(surf, cx + sgn * 25 * u - 8 * u, top + 35 * u, 17 * u, 10 * u,
             SKIN_D, 0.8, 3)
    for i in range(3):
        pygame.draw.circle(surf, (96, 96, 110), (cx, top + (22 + i * 9) * u),
                           1.8 * u)
    _blk(surf, cx - 10 * u, top - 9 * u, 20 * u, 12 * u, SKIN_D, 0.8, 2)
    sc = top - 1 * u                              # the scarf
    _blk(surf, cx - 25 * u, sc - 11 * u, 50 * u, 16 * u, SARAH_SCARF, 0.68, 5)
    _blk(surf, cx + 8 * u, sc + 2 * u, 13 * u, 20 * u,
         shade(SARAH_SCARF, 0.82), 0.68, 3)
    hb = sc - 11 * u                              # head sits on the scarf
    hh = 42 * u
    _blk(surf, cx - 23 * u, hb - hh, 46 * u, hh, SKIN, 0.8, 4)
    for sgn in (-1, 1):                           # brows, before the hair, so
        pygame.draw.line(surf, (58, 46, 46),      # the fringe covers one
                         (cx + sgn * 5 * u, hb - 31 * u),
                         (cx + sgn * 16 * u, hb - 33 * u),
                         max(2, int(2.3 * u)))
    for sgn in (-1, 1):                           # a bit of warmth in the face
        pygame.draw.circle(surf, (246, 206, 196),
                           (cx + sgn * 15 * u, hb - 11 * u), 3.2 * u)
    hair = SARAH_HAIR
    _blk(surf, cx - 26 * u, hb - hh - 5 * u, 52 * u, 12 * u, hair, 0.7, 5)
    pygame.draw.line(surf, (86, 78, 96),          # the stall lamp is overhead
                     (cx - 17 * u, hb - hh - 3 * u),
                     (cx + 15 * u, hb - hh - 4 * u), max(2, int(2.4 * u)))
    for sgn in (-1, 1):                           # the bob, flaring at the jaw
        pygame.draw.polygon(surf, hair, [
            (cx + sgn * 21 * u, hb - hh - 3 * u),
            (cx + sgn * 27 * u, hb - hh + 1 * u),
            (cx + sgn * 29 * u, hb + 2 * u),
            (cx + sgn * 19 * u, hb),
            (cx + sgn * 19 * u, hb - hh + 4 * u)])
    pygame.draw.polygon(surf, hair, [             # one eye, and only one
        (cx - 26 * u, hb - hh + 3 * u), (cx + 5 * u, hb - hh + 3 * u),
        (cx - 9 * u, hb - hh + 21 * u), (cx - 26 * u, hb - hh + 16 * u)])
    gl = hb - 23 * u                              # glasses
    pygame.draw.line(surf, (44, 44, 52), (cx - 18 * u, gl), (cx + 18 * u, gl),
                     max(1, int(2.0 * u)))
    for sgn in (-1, 1):
        r = pygame.Rect(cx + sgn * 10 * u - 8.5 * u, gl - 5 * u, 17 * u,
                        11 * u)
        pygame.draw.rect(surf, (176, 202, 224), r, border_radius=2)
        pygame.draw.rect(surf, (44, 44, 52), r, max(1, int(1.6 * u)),
                         border_radius=2)
    pygame.draw.circle(surf, (38, 34, 40), (cx + 10 * u, gl), 2.1 * u)
    pygame.draw.lines(surf, (88, 66, 70), False,  # and she is glad you came
                      [(cx - 11 * u, hb - 12 * u), (cx - 4 * u, hb - 6 * u),
                       (cx + 4 * u, hb - 6 * u), (cx + 11 * u, hb - 12 * u)],
                      max(2, int(2.1 * u)))


def draw_jack_front(surf, cx, gy, h, t):
    """Goggles pushed up on the forehead, a black suit over a white shirt,
    and a face somebody drew on in two strokes and a smile. Same short
    proportions as his sister."""
    u = h / 100.0
    bob = math.sin(t * 1.25 + 1.1) * 1.0 * u
    top = gy - 38 * u + bob
    _blk(surf, cx - 34 * u, top, 68 * u, 50 * u, JACK_SUIT, 0.7, 4)
    pygame.draw.polygon(surf, JACK_SHIRT, [       # shirt in the gap
        (cx - 10 * u, top), (cx + 10 * u, top),
        (cx + 7 * u, top + 30 * u), (cx - 7 * u, top + 30 * u)])
    for sgn in (-1, 1):                           # lapels
        pygame.draw.polygon(surf, JACK_LAPEL, [
            (cx + sgn * 11 * u, top), (cx + sgn * 29 * u, top),
            (cx + sgn * 22 * u, top + 26 * u),
            (cx + sgn * 8 * u, top + 14 * u)])
    _blk(surf, cx - 4 * u, top + 1 * u, 8 * u, 13 * u,
         shade(SARAH_SCARF, 0.5), 0.7, 2)         # the tie, his sister's colour
    for sgn in (-1, 1):
        ax = cx + sgn * 40 * u
        _blk(surf, ax - 12 * u, top + 2 * u, 25 * u, 23 * u, JACK_SUIT, 0.7, 3)
        _blk(surf, ax - 11 * u, top + 23 * u, 23 * u, 17 * u,
             shade(JACK_SUIT, 0.86), 0.7, 3)
        _blk(surf, cx + sgn * 26 * u - 8 * u, top + 35 * u, 17 * u, 10 * u,
             SKIN_D, 0.8, 3)
    _blk(surf, cx - 10 * u, top - 10 * u, 20 * u, 13 * u, SKIN_D, 0.8, 2)
    hb = top - 8 * u
    hh = 44 * u
    _blk(surf, cx - 23 * u, hb - hh, 46 * u, hh, SKIN, 0.8, 4)
    hair = JACK_HAIR                              # short, and it needs cutting
    _blk(surf, cx - 25 * u, hb - hh - 6 * u, 50 * u, 13 * u, hair, 0.6, 5)
    pygame.draw.line(surf, shade(hair, 1.30),     # the stall lamp is overhead
                     (cx - 18 * u, hb - hh - 4 * u),
                     (cx + 14 * u, hb - hh - 5 * u), max(2, int(2.6 * u)))
    pygame.draw.polygon(surf, hair, [             # swept over from his parting
        (cx - 25 * u, hb - hh + 2 * u), (cx + 6 * u, hb - hh - 3 * u),
        (cx + 23 * u, hb - hh + 3 * u), (cx + 23 * u, hb - hh + 8 * u),
        (cx - 25 * u, hb - hh + 7 * u)])
    for sgn in (-1, 1):                           # and short at the sides
        _blk(surf, cx + sgn * 23 * u - 4 * u, hb - hh + 2 * u, 8 * u, 11 * u,
             hair, 0.7, 2)
    gg = hb - hh + 11 * u                         # goggles, up on the brow
    _blk(surf, cx - 26 * u, gg - 5 * u, 52 * u, 13 * u, (50, 42, 37), 0.7, 3)
    for sgn in (-1, 1):
        c = (cx + sgn * 12 * u, gg + 1 * u)
        pygame.draw.circle(surf, (60, 51, 45), c, 9 * u)
        pygame.draw.circle(surf, JACK_BRASS, c, 7.2 * u)
        pygame.draw.circle(surf, shade(JACK_BRASS, 0.6), c, 4.1 * u)
        pygame.draw.circle(surf, (240, 216, 172),
                           (c[0] - 2 * u, c[1] - 2 * u), 1.8 * u)
    for sgn in (-1, 1):                           # two strokes, well clear
        pygame.draw.line(surf, (46, 40, 42), (cx + sgn * 4 * u, hb - 20 * u),
                         (cx + sgn * 16 * u, hb - 23 * u),
                         max(2, int(2.6 * u)))
        pygame.draw.circle(surf, (42, 38, 42),
                           (cx + sgn * 9 * u, hb - 15 * u), 2.4 * u)
    pygame.draw.lines(surf, (50, 42, 44), False,   # and a wide one
                      [(cx - 14 * u, hb - 12 * u), (cx - 5 * u, hb - 6 * u),
                       (cx + 5 * u, hb - 6 * u), (cx + 14 * u, hb - 12 * u)],
                      max(2, int(2.3 * u)))


# -- the goods --------------------------------------------------------------
def _sheet(surf, r, t, draw_lines):
    """A blueprint: dark blue paper, a border, and line work on it."""
    pygame.draw.rect(surf, (20, 40, 62), r, border_radius=3)
    pygame.draw.rect(surf, shade(SARAH_INK, 0.5), r, 1, border_radius=3)
    inner = r.inflate(-8, -8)
    pygame.draw.rect(surf, shade(SARAH_INK, 0.34), inner, 1)
    draw_lines(surf, inner)


def _jar(surf, box, t, col, body):
    """A specimen jar: glass, fluid, something in it, bubbles. Whatever box
    it is given, it keeps its own shape inside it."""
    w = min(box.w, int(box.h * 0.66))
    r = pygame.Rect(box.centerx - w // 2, box.y + 6, w, box.h - 12)
    pygame.draw.rect(surf, (22, 42, 42), r, border_radius=int(r.w * 0.22))
    fluid = r.inflate(-6, -10)
    fluid.y += 4
    pygame.draw.rect(surf, shade(col, 0.30), fluid,
                     border_radius=int(r.w * 0.18))
    body(surf, fluid, t)
    for i in range(5):
        bx = fluid.x + 4 + (i * 29) % max(6, fluid.w - 8)
        by = fluid.bottom - ((t * (18 + i * 7) + i * 23) % max(8, fluid.h))
        pygame.draw.circle(surf, shade(col, 1.25), (bx, by), 1.4)
    _blk(surf, r.x - 2, r.y - 5, r.w + 4, 8, (74, 92, 88), 0.7, 2)
    g = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(g, (200, 240, 235, 30), g.get_rect(),
                     border_radius=int(r.w * 0.22))
    pygame.draw.rect(g, (230, 250, 248, 46), (4, 6, 4, r.h - 18),
                     border_radius=2)
    surf.blit(g, r.topleft)


def draw_ware_icon(surf, r, w, t):
    """One thing on the boards, drawn at whatever size it is asked for."""
    k = w.key
    if k in ("bp_rail", "bp_hook"):
        wep = WEAPONS["rail" if k == "bp_rail" else "hook"]

        def lines(s, box):
            rig = Rig(s, box.centerx, box.bottom - box.h * 0.18,
                      box.h / 260.0)
            for pts, _ in shape_weapon(wep.key, "r", 3):
                rig.poly(pts, SARAH_INK, 1)
            for pts, _ in shape_arm(3, "r"):
                rig.poly(pts, shade(SARAH_INK, 0.62), 1)
            for i in range(3):
                y = box.y + 6 + i * 5
                pygame.draw.line(s, shade(SARAH_INK, 0.55),
                                 (box.x + 5, y), (box.x + box.w * 0.4, y), 1)
        _sheet(surf, r, t, lines)
        return
    if k == "spec_shriek":
        def body(s, f, tt):
            cx, cy = f.centerx, f.centery
            rr = f.w * 0.26 * (1.0 + 0.16 * math.sin(tt * 5.0))
            pygame.draw.circle(s, (206, 226, 250), (cx, cy), rr)
            for i in range(7):
                a = i * TAU / 7 + tt * 0.9
                pygame.draw.line(s, (170, 200, 240), (cx, cy),
                                 (cx + math.cos(a) * rr * 2.1,
                                  cy + math.sin(a) * rr * 1.7), 2)
        _jar(surf, r, t, (150, 190, 235), body)
        return
    if k == "spec_leech":
        def body(s, f, tt):
            cx, cy = f.centerx, f.centery + math.sin(tt * 1.3) * f.h * 0.06
            for i in range(4):
                a = tt * 0.8 + i * 1.57
                pygame.draw.circle(s, (238, 140, 150),
                                   (cx + math.cos(a) * f.w * 0.20,
                                    cy + math.sin(a) * f.h * 0.14),
                                   f.w * 0.13)
            pygame.draw.circle(s, (250, 186, 190), (cx, cy), f.w * 0.17)
        _jar(surf, r, t, (226, 120, 136), body)
        return
    if k == "spec_venom":
        def body(s, f, tt):
            cx, cy = f.centerx, f.centery
            pts = [(cx + f.w * 0.26 * math.cos(a) * (1 + 0.2 * math.sin(a * 3
                                                                       + tt)),
                    cy + f.h * 0.20 * math.sin(a))
                   for a in (i * TAU / 11 for i in range(11))]
            pygame.draw.polygon(s, RYEZ_ACID, pts)
            pygame.draw.polygon(s, shade(RYEZ_ACID, 0.6), pts, 2)
            pygame.draw.circle(s, (250, 250, 200),
                               (cx + f.w * 0.07, cy - f.h * 0.04), 2.4)
        _jar(surf, r, t, RYEZ_ACID, body)
        return
    # the standing orders: a small object apiece, all bought off a counter
    pygame.draw.rect(surf, (28, 30, 38), r, border_radius=4)
    pygame.draw.rect(surf, (60, 64, 78), r, 1, border_radius=4)
    cx, cy = r.centerx, r.centery
    s = r.h
    if k == "warchest":
        _blk(surf, cx - s * 0.32, cy - s * 0.16, s * 0.64, s * 0.36,
             (108, 84, 52), 0.6, 3)
        _blk(surf, cx - s * 0.34, cy - s * 0.26, s * 0.68, s * 0.14,
             (132, 104, 64), 0.6, 3)
        _blk(surf, cx - s * 0.06, cy - s * 0.12, s * 0.12, s * 0.16, PAINT,
             0.6, 2)
    elif k == "earlyshift":
        pygame.draw.circle(surf, (96, 102, 118), (cx, cy), s * 0.28)
        pygame.draw.circle(surf, (24, 26, 32), (cx, cy), s * 0.22)
        a = t * 1.6
        pygame.draw.line(surf, PAINT, (cx, cy),
                         (cx + math.cos(a) * s * 0.16,
                          cy + math.sin(a) * s * 0.16), 2)
        pygame.draw.line(surf, (200, 206, 220), (cx, cy),
                         (cx, cy - s * 0.19), 2)
    elif k == "sharptools":
        _blk(surf, cx - s * 0.34, cy - s * 0.12, s * 0.68, s * 0.30,
             (96, 74, 50), 0.6, 3)
        for i in range(4):
            x = cx - s * 0.24 + i * s * 0.16
            pygame.draw.line(surf, (188, 196, 210), (x, cy - s * 0.24),
                             (x, cy + s * 0.06), 2)
    elif k == "thickblood":
        _blk(surf, cx - s * 0.12, cy - s * 0.28, s * 0.24, s * 0.52,
             (36, 46, 46), 0.7, 3)
        _blk(surf, cx - s * 0.08, cy - s * 0.06, s * 0.16, s * 0.27,
             (214, 96, 108), 0.7, 2)
        _blk(surf, cx - s * 0.15, cy - s * 0.32, s * 0.30, s * 0.07,
             (78, 92, 90), 0.7, 2)
    elif k == "quicknerve":
        prev = None
        for i in range(14):
            f = i / 13.0
            p = (cx - s * 0.32 + f * s * 0.64,
                 cy + math.sin(f * 9.0 + t * 3.0) * s * 0.16)
            if prev:
                pygame.draw.line(surf, RYEZ_ACID, prev, p, 2)
            prev = p
    else:                                     # deepgut
        pygame.draw.circle(surf, (78, 54, 78), (cx, cy), s * 0.30)
        pygame.draw.circle(surf, (32, 22, 32), (cx, cy), s * 0.19)
        pygame.draw.circle(surf, HEART, (cx, cy),
                           s * 0.09 * (1 + 0.2 * math.sin(t * 2.6)))


def draw_market_night(surf, t):
    """The street the stalls are on: dark, wet, and lit by a wire of bulbs."""
    for i in range(0, H, 4):
        f = i / float(H)
        surf.fill(mix((14, 14, 26), (30, 22, 30), f ** 1.3), (0, i, W, 4))
    rnd = random.Random(11)
    for col, top, step in (((20, 20, 34), 210, 132), ((26, 25, 42), 300, 168)):
        for x in range(-40, W + 120, step):
            hgt = rnd.randint(90, 210)
            wdt = step - rnd.randint(18, 44)
            pygame.draw.rect(surf, col, (x, top - hgt, wdt, hgt + 60))
            for wy in range(top - hgt + 14, top + 20, 26):
                for wx in range(x + 10, x + wdt - 8, 20):
                    if (wx * 7 + wy * 3) % 5 < 2:
                        pygame.draw.rect(surf, (96, 82, 62), (wx, wy, 5, 7))
    sag = 26
    px = py = None
    for i in range(14):                              # the wire
        f = i / 13.0
        x = 20 + f * (W - 40)
        y = 34 + math.sin(f * math.pi) * sag
        if px is not None:
            pygame.draw.line(surf, (44, 42, 48), (px, py), (x, y), 2)
        px, py = x, y
    for i in range(13):                              # and the bulbs on it
        f = (i + 0.5) / 13.0
        x = 20 + f * (W - 40)
        y = 34 + math.sin(f * math.pi) * sag + 12
        sway = math.sin(t * 0.9 + i * 0.7) * 3
        pygame.draw.line(surf, (54, 52, 58), (x, y - 12), (x + sway, y), 1)
        pygame.draw.circle(surf, BULB, (x + sway, y + 4), 3.4)
        blit_glow(surf, (x + sway, y + 4), 26, BULB, 60)
    pygame.draw.rect(surf, (17, 16, 24), (0, H - 74, W, 74))
    for i in range(13):                              # the same bulbs, wet road
        f = (i + 0.5) / 13.0
        x = 20 + f * (W - 40) + math.sin(t * 0.9 + i * 0.7) * 3
        blit_glow(surf, (x, H - 40), 40, shade(BULB, 0.5), 26)


def draw_stall(surf, r, tone, t, seller):
    """Awning, lamp, counter. The stall is the frame for everything else."""
    panel(surf, r, (19, 18, 26), LINE, 8)
    aw = pygame.Rect(r.x + 4, r.y + 4, r.w - 8, 52)
    stripe = 34
    for i in range(0, aw.w, stripe):
        col = tone if (i // stripe) % 2 == 0 else shade(tone, 0.45)
        pygame.draw.rect(surf, shade(col, 0.8),
                         (aw.x + i, aw.y, min(stripe, aw.right - aw.x - i),
                          aw.h - 10))
    for i in range(0, aw.w - 10, 26):                # the scalloped hem
        pygame.draw.circle(surf, shade(tone, 0.62) if (i // 26) % 2
                           else shade(tone, 0.34),
                           (aw.x + i + 13, aw.bottom - 10), 13)
    pygame.draw.rect(surf, (40, 38, 46), (aw.x, aw.y, aw.w, 6))
    lamp = (r.centerx, r.y + 92)                     # a lamp over the counter
    pygame.draw.line(surf, (52, 50, 58), (lamp[0], aw.bottom - 8), lamp, 2)
    pygame.draw.polygon(surf, (62, 60, 70),
                        [(lamp[0] - 22, lamp[1]), (lamp[0] + 22, lamp[1]),
                         (lamp[0] + 9, lamp[1] - 16),
                         (lamp[0] - 9, lamp[1] - 16)])
    pygame.draw.circle(surf, BULB, (lamp[0], lamp[1] + 3), 4)
    blit_glow(surf, (lamp[0], lamp[1] + 14), 150, BULB, 44)
    seller(surf, r.centerx, r.y + 272, 176, t)
    top = pygame.Rect(r.x + 10, r.y + 272, r.w - 20, 16)
    pygame.draw.rect(surf, (96, 78, 56), top, border_radius=3)
    pygame.draw.rect(surf, (60, 48, 34), top, 1, border_radius=3)
    pygame.draw.rect(surf, (44, 36, 26), (r.x + 10, top.bottom, r.w - 20, 14))


class Bazaar:
    """The only screen in the game where nothing is trying to kill you."""

    SELLERS = (("sarah", "SARAH HENDRA", "she draws it", SARAH_INK,
                draw_sarah_front),
               ("jack", "JACK HENDRA", "he grows it", JACK_GLASS,
                draw_jack_front))

    def __init__(self, back="title"):
        self.t = 0.0
        self.back = back
        self.slots = []
        self.open = None            # the ware being turned over
        self.flash = {}
        self.btn = Button(pygame.Rect(W // 2 - 150, H - 48, 300, 36),
                          "BACK TO THE YARD" if back == "hangar" else "BACK",
                          ("go", None), primary=True)
        self.buy_btn = None

    def stall_rect(self, i):
        w = (W - 68) // 2
        return pygame.Rect(26 + i * (w + 16), 66, w, H - 136)

    def slot_rects(self, r, n):
        out = []
        gw, gh = (r.w - 24) / 3.0, 138
        for i in range(n):
            out.append(pygame.Rect(int(r.x + 12 + (i % 3) * gw),
                                   int(r.y + 318 + (i // 3) * (gh + 8)),
                                   int(gw - 8), gh))
        return out

    def panel_rect(self):
        return pygame.Rect(W // 2 - 330, H // 2 - 200, 660, 400)

    # -- frame -------------------------------------------------------------
    def draw(self, surf, mouse):
        draw_market_night(surf, self.t)
        text(surf, "THE NIGHT MARKET", 30, (24, 12), PAINT)
        text(surf, "the Hendras do not work for either company, and they "
             "will sell to both", 13, (24, 44), FAINT)
        text(surf, "%d MARKS" % marks(), 27, (W - 24, 12), INK, right=True)
        text(surf, "what the city pays for a body", 11, (W - 24, 42), FAINT,
             right=True)
        self.slots = []
        for i, (key, name, tag, col, art) in enumerate(self.SELLERS):
            r = self.stall_rect(i)
            draw_stall(surf, r, col, self.t, art)
            text(surf, name, 22, (r.centerx, r.y + 15), INK, center=True)
            text(surf, tag, 13, (r.centerx, r.y + 296), DIM, center=True)
            wares = [x for x in WARE_LIST if x.seller == key]
            for box, w in zip(self.slot_rects(r, len(wares)), wares):
                self.good(surf, box, w, col, mouse)
        self.btn.hover(mouse)
        self.btn.draw(surf, 19)
        if self.open is not None:
            self.inspect(surf, mouse)

    def good(self, surf, box, w, col, mouse):
        own = w.kind != "specimen" and has_ware(w.key)
        have = stock_of(w.key)
        hot = box.collidepoint(mouse) and self.open is None
        lift = 4 if hot else 0
        b = box.move(0, -lift)
        panel(surf, b, (30, 30, 40) if hot else (22, 22, 30),
              col if hot else (GOOD if own else LINE), 6)
        draw_ware_icon(surf, pygame.Rect(b.centerx - 34, b.y + 10, 68, 68),
                       w, self.t)
        nm = ware_name(w)
        afford = own or have or marks() >= w.cost
        text(surf, nm, fit(nm, 14, b.w - 12), (b.centerx, b.y + 84),
             INK if afford else FAINT, center=True)
        if own:
            text(surf, "BOUGHT", 13, (b.centerx, b.y + 104), GOOD,
                 center=True)
        else:
            text(surf, "%d MARKS" % w.cost, 13, (b.centerx, b.y + 104),
                 PAINT if marks() >= w.cost else BAD, center=True)
            if w.kind == "specimen" and have:
                text(surf, "x%d held" % have, 11, (b.centerx, b.y + 118),
                     GOOD, center=True)
        f = self.flash.get(w.key, 0.0)
        if f > 0.01:
            blit_glow(surf, b.center, b.h * 0.9, col, int(80 * f))
        self.slots.append((b, w.key))

    def inspect(self, surf, mouse):
        """Picked up off the boards and turned over."""
        w = WARES[self.open]
        col = SARAH_INK if w.seller == "sarah" else JACK_GLASS
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((6, 6, 12, 200))
        surf.blit(ov, (0, 0))
        r = self.panel_rect()
        panel(surf, r, (18, 18, 26), col, 10, 2)
        big = pygame.Rect(r.x + 26, r.y + 62, 250, 250)
        draw_ware_icon(surf, big, w, self.t)
        x = big.right + 26
        text(surf, ware_name(w), 30, (x, r.y + 40), INK)
        kind = {"blueprint": "A BLUEPRINT - yours for good, once drawn",
                "power": "A STANDING ORDER - every run, for good",
                "specimen": "A SPECIMEN - one jar, opened in the street"}
        text(surf, kind[w.kind], 13, (x, r.y + 78), col)
        y = r.y + 106
        for line in wrap(w.effect, 17, r.right - x - 30):
            text(surf, line, 17, (x, y), (214, 220, 234))
            y += 22
        y += 10
        for line in wrap(w.blurb, 14, r.right - x - 30):
            text(surf, line, 14, (x, y), DIM, bold=False)
            y += 18
        own = w.kind != "specimen" and has_ware(w.key)
        if w.kind == "specimen":
            have = stock_of(w.key)
            text(surf, "%d in the cupboard" % have, 14, (x, r.bottom - 98),
                 GOOD if have else FAINT)
        text(surf, "%d MARKS" % w.cost, 24, (x, r.bottom - 76),
             PAINT if marks() >= w.cost else BAD)
        lab = ("ALREADY BOUGHT" if own else
               "NOT ENOUGH MARKS" if marks() < w.cost else
               "BUY ANOTHER" if w.kind == "specimen" else "BUY IT")
        self.buy_btn = Button(pygame.Rect(x, r.bottom - 48, 230, 34), lab,
                              ("buy", w.key), enabled=can_buy(w.key),
                              tone=col, primary=can_buy(w.key))
        self.buy_btn.hover(mouse)
        self.buy_btn.draw(surf, 17)
        text(surf, "ESC to put it back", 13, (r.x + 26, r.bottom - 30), FAINT)

    def update(self, dt):
        self.t += dt
        for k in list(self.flash):
            self.flash[k] -= dt * 1.6
            if self.flash[k] <= 0:
                del self.flash[k]

    def click(self, pos):
        if self.open is not None:
            if self.buy_btn and self.buy_btn.hit(pos):
                if buy_ware(self.open):
                    self.flash[self.open] = 1.0
                    SFX.play("done", 0.7)
                else:
                    SFX.play("deny", 0.5)
                return None
            if not self.panel_rect().collidepoint(pos):
                self.open = None
                SFX.play("click", 0.4)
            return None
        if self.btn.hit(pos):
            SFX.play("click", 0.6)
            return "go"
        for box, key in self.slots:
            if box.collidepoint(pos):
                self.open = key
                SFX.play("click", 0.5)
                return None
        return None

    def back_out(self):
        """ESC puts the thing down first, and leaves the market second."""
        if self.open is not None:
            self.open = None
            return None
        return "go"


# ---------------------------------------------------------------------------
# THE FRONT DOOR
# ---------------------------------------------------------------------------
class Title:
    def __init__(self, save):
        self.save = save
        self.t = 0.0
        self.buttons = []
        self.demo = Mech()
        for k, v in (("legs", 2), ("torso", 2), ("l_arm", 2), ("r_arm", 1),
                     ("head", 2), ("reactor", 2), ("l_wpn", "pile"),
                     ("r_wpn", "auto"), ("armour", 1)):
            self.demo.install(k, v)

    def draw(self, surf, mouse):
        surf.fill(BG)
        sky(surf, self.t * 0.2)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((8, 9, 14, 160))
        surf.blit(ov, (0, 0))
        g = pygame.Rect(W - 470, 60, 420, 640)
        draw_gantry(surf, g, _TitleRun(self.demo), self.t)
        text(surf, "THE", 30, (74, 108), PAINT)
        text(surf, "GREAT", 96, (68, 132), INK)
        text(surf, "WORK", 96, (68, 224), INK)
        text(surf, "Build the mech. The kaiju will not wait.", 22,
             (74, 336), DIM)
        has = bool(self.save.get("run"))
        self.buttons = []
        y = 400
        if has:
            r = self.save["run"]
            self.buttons.append(Button(pygame.Rect(74, y, 330, 60),
                                       "CONTINUE - DAY %d" % r.get("day", 1),
                                       ("continue", None), primary=True))
            y += 74
        self.buttons.append(Button(pygame.Rect(74, y, 330, 60),
                                   "A NEW MACHINE" if has else "BEGIN",
                                   ("new", None), primary=not has))
        y += 74
        self.buttons.append(Button(pygame.Rect(74, y, 330, 60),
                                   "THE HENDRAS - %d MARKS" % marks(),
                                   ("shop", None), tone=ALLOY_C))
        y += 74
        self.buttons.append(Button(pygame.Rect(74, y, 330, 60), "QUIT",
                                   ("quit", None), tone=BAD))
        for b in self.buttons:
            b.hover(mouse)
            b.draw(surf, 24)
        best = self.save.get("best", {})
        if best:
            text(surf, "machines finished: %d      lost: %d      best run: "
                 "%d kaiju" % (best.get("wins", 0), best.get("losses", 0),
                               best.get("best_kills", 0)), 15,
                 (74, H - 54), FAINT)
        text(surf, "Every graphic and every note in this game is drawn or "
             "synthesised in code.", 13, (74, H - 30), (56, 60, 76))

    def click(self, pos):
        for b in self.buttons:
            if b.hit(pos):
                SFX.play("click", 0.6)
                return b.key[0]
        return None


class _TitleRun:
    """The gantry wants a run. On the title screen there is not one yet."""

    def __init__(self, mech):
        self.mech = mech
        self.jobs = [Job("r_arm", 2, "build", 5, 2)]
        self.jobs[0].done = 2.0
        self.free_crew = 1


class Ending:
    def __init__(self, run, won):
        self.run = run
        self.won = won
        self.t = 0.0
        self.btn = Button(pygame.Rect(W // 2 - 150, H - 96, 300, 58),
                          "THE FRONT DOOR", ("go", None))

    def draw(self, surf, mouse):
        surf.fill(BG)
        sky(surf, self.t * 0.15)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((8, 9, 14, 165))
        surf.blit(ov, (0, 0))
        r = self.run
        if self.won:
            text(surf, "THE GREAT WORK IS FINISHED", 50, (W // 2, 60), PAINT,
                 center=True)
            lines = [
                "The last one went back into the water in pieces.",
                "It took %d days, %d crew and most of a city." % (r.day, r.crew),
                "The machine is still standing in the yard.",
                "Somebody has started painting a name on it.",
            ]
        else:
            text(surf, "THERE IS NO CITY LEFT TO DEFEND", 42, (W // 2, 60),
                 BAD, center=True)
            lines = [
                "The yard went with the rest of it on day %d." % r.day,
                "%d of them came ashore. You put %d down."
                % (r.kaiju_index, r.killed),
                "The machine was %d%% finished." %
                round(r.mech.completion() * 100),
                "It was always going to be close.",
            ]
        for i, s in enumerate(lines):
            text(surf, s, 21, (W // 2, 132 + i * 30), INK if self.won else DIM,
                 center=True)
        draw_mech_front(surf, r.mech, W // 2, H - 150, 0.72, {}, self.t,
                        lit=self.won)
        stats = [("DAYS", str(r.day)), ("KAIJU DOWN", str(r.killed)),
                 ("CITY LEFT", "%d%%" % int(r.integrity)),
                 (word("spent", "SCRAP SPENT"), str(r.spent)),
                 (word("built", "BUILT"),
                  "%d%%" % round(r.mech.completion() * 100))]
        x = W // 2 - 300
        for a, b in stats:
            text(surf, b, 26, (x, 276), PAINT, center=True)
            text(surf, a, 12, (x, 306), FAINT, center=True)
            x += 150
        self.btn.hover(mouse)
        self.btn.draw(surf, 22)

    def click(self, pos):
        if self.btn.hit(pos):
            SFX.play("click", 0.6)
            return "go"
        return None


# ---------------------------------------------------------------------------
# THE LOOP
# ---------------------------------------------------------------------------
class App:
    def __init__(self):
        pygame.display.set_caption("THE GREAT WORK")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.state = "title"
        self.title = Title(load_save())
        self.choose = None
        self.bazaar = None
        self.run = None
        self.hangar = None
        self.fight = None
        self.brief = None
        self.after = None
        self.ending = None
        self.speed = 1
        self.paused = False
        self.running = True
        music("vigil")

    # -- moving between screens -------------------------------------------
    def begin_run(self, data=None, house_key="keal"):
        self.run = Run.from_json(data) if data else Run(house_key)
        set_house(self.run.house)
        self.hangar = Hangar(self.run)
        self.state = "hangar"
        music("yard")
        save_run(self.run)
        # a run resumed on the morning of a landfall goes straight out
        nl = self.run.next_landfall
        if nl is not None and self.run.day >= nl:
            self.to_brief()

    def to_brief(self):
        kind = self.run.next_kind()
        if kind is None:
            return
        self.brief = Brief(self.run, kind)
        self.state = "brief"
        music("landfall")
        SFX.play("alarm", 0.7)

    def to_fight(self):
        self.fight = Fight(self.run, self.brief.kind)
        self.state = "fight"
        self.speed = 1
        self.paused = False
        music("landfall")

    def finish_fight(self):
        ending, lines = self.run.resolve(self.fight)
        self.after = After(self.run, self.fight, lines, ending)
        self.state = "after"
        self.ending = ending
        music("vigil")
        if ending:
            record_end(self.run, ending == "victory")
        else:
            save_run(self.run)

    def stand_down(self):
        k = self.brief.kind
        cost = self.brief.stand_cost()
        self.run.integrity = clamp(self.run.integrity - cost, 0.0, 100.0)
        self.run.kaiju_index += 1
        lines = ["THE MACHINE STAYED IN THE GANTRY.",
                 "%s WALKED THROUGH THE CITY UNOPPOSED." % k.name,
                 "-%d CITY" % cost]
        ending = None
        if self.run.integrity <= 0:
            ending = "over"
        elif self.run.kaiju_index >= len(roster_for(self.run.house)):
            ending = "unfinished"
        else:
            lines.append("NEXT LANDFALL: DAY %d"
                         % SCHEDULE[self.run.kaiju_index])
        self.after = After(self.run, None, lines, ending)
        self.ending = ending
        self.state = "after"
        music("vigil")
        if ending:
            record_end(self.run, ending == "victory")
        else:
            save_run(self.run)

    def after_done(self):
        if self.ending:
            self.ending_screen = Ending(self.run, self.ending == "victory")
            self.state = "end"
        else:
            self.hangar = Hangar(self.run)
            self.state = "hangar"
            music("yard")

    def to_title(self):
        self.title = Title(load_save())
        self.state = "title"
        set_house("keal")
        music("vigil")

    # -- events -----------------------------------------------------------
    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_m:
                SFX.muted = not SFX.muted
                if SFX.muted:
                    music_stop()
                else:
                    music({"fight": "landfall", "brief": "landfall",
                           "hangar": "yard"}.get(self.state, "vigil"))
                return
            if ev.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                return
        if self.state == "title":
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.pick(self.title.click(ev.pos))
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE,
                                                          pygame.K_RETURN):
                self.pick("continue" if self.title.save.get("run") else "new")
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.running = False
        elif self.state == "shop":
            act = None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.bazaar.click(ev.pos)
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE,
                                                          pygame.K_SPACE,
                                                          pygame.K_RETURN):
                act = self.bazaar.back_out()
            if act == "go":
                if self.bazaar.back == "hangar" and self.run is not None:
                    self.hangar = Hangar(self.run)
                    self.state = "hangar"
                    music("yard")
                else:
                    self.to_title()
        elif self.state == "choose":
            picked = None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                picked = self.choose.click(ev.pos)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.to_title()
                elif ev.key in (pygame.K_1, pygame.K_KP1):
                    picked = "keal"
                elif ev.key in (pygame.K_2, pygame.K_KP2):
                    picked = "ryez"
            if picked:
                self.begin_run(None, picked)
        elif self.state == "hangar":
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.hangar.spec:
                    self.hangar.spec = False
                elif self.hangar.click(ev.pos) == "landfall":
                    self.to_brief()
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.hangar.spec or self.hangar.rack:
                        self.hangar.spec = False
                        self.hangar.rack = False
                    else:
                        save_run(self.run)
                        self.to_title()
                elif self.hangar.key(ev.key) == "landfall":
                    self.to_brief()
        elif self.state == "brief":
            act = None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.brief.click(ev.pos)
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE,
                                                          pygame.K_RETURN):
                act = "go"
            if act == "go":
                self.to_fight()
            elif act == "stand":
                self.stand_down()
        elif self.state == "fight":
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_p:
                    self.paused = not self.paused
                elif ev.key == pygame.K_f:
                    self.speed = 1 if self.speed >= 3 else self.speed + 1
                elif ev.key == pygame.K_ESCAPE:
                    self.paused = not self.paused
            if self.fight.over and self.fight.over_t > 1.2:
                if (ev.type == pygame.MOUSEBUTTONDOWN or
                        (ev.type == pygame.KEYDOWN and
                         ev.key in (pygame.K_SPACE, pygame.K_RETURN))):
                    self.finish_fight()
        elif self.state == "after":
            act = None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.after.click(ev.pos)
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE,
                                                          pygame.K_RETURN):
                act = "go"
            if act == "shop":
                self.to_shop("hangar")
            elif act:
                self.after_done()
        elif self.state == "end":
            act = None
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                act = self.ending_screen.click(ev.pos)
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE,
                                                          pygame.K_RETURN,
                                                          pygame.K_ESCAPE):
                act = "go"
            if act:
                self.run = None
                self.to_title()

    def to_shop(self, back):
        self.bazaar = Bazaar(back)
        self.state = "shop"
        music("vigil")

    def pick(self, act):
        if act == "shop":
            self.to_shop("title")
        elif act == "new":
            self.choose = Choose()
            self.state = "choose"
        elif act == "continue":
            self.begin_run(self.title.save.get("run"))
        elif act == "quit":
            self.running = False

    def fight_input(self):
        k = pygame.key.get_pressed()
        mb = pygame.mouse.get_pressed()
        return {
            "left": k[pygame.K_a] or k[pygame.K_LEFT],
            "right": k[pygame.K_d] or k[pygame.K_RIGHT],
            "brace": k[pygame.K_s] or k[pygame.K_DOWN],
            "boost": k[pygame.K_SPACE],
            "fire_l": k[pygame.K_j] or mb[0],
            "fire_r": k[pygame.K_k] or mb[2],
            "flush": k[pygame.K_v],
            "jar1": k[pygame.K_1], "jar2": k[pygame.K_2],
            "jar3": k[pygame.K_3],
        }

    # -- the frame --------------------------------------------------------
    def frame(self):
        dt = min(0.05, self.clock.tick(FPS) / 1000.0)
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            self.handle(ev)
        s = self.screen
        if self.state == "title":
            self.title.t += dt
            self.title.draw(s, mouse)
        elif self.state == "choose":
            self.choose.t += dt
            self.choose.draw(s, mouse)
        elif self.state == "shop":
            self.bazaar.update(dt)
            self.bazaar.draw(s, mouse)
        elif self.state == "hangar":
            self.hangar.update(dt)
            self.hangar.draw(s, mouse)
        elif self.state == "brief":
            self.brief.t += dt
            self.brief.draw(s, mouse)
        elif self.state == "fight":
            if not self.paused:
                steps = self.speed
                for _ in range(steps):
                    if self.fight.over and self.fight.over_t > 2.0:
                        break
                    self.fight.update(dt, self.fight_input())
            self.fight.draw(s)
            if self.speed > 1:
                text(s, "%dx" % self.speed, 18, (W - 16, H - 92), PAINT,
                     right=True)
            if self.paused:
                ov = pygame.Surface((W, H), pygame.SRCALPHA)
                ov.fill((6, 7, 12, 170))
                s.blit(ov, (0, 0))
                text(s, "PAUSED", 46, (W // 2, H // 2 - 30), INK, center=True)
                text(s, "P to go back out there", 18, (W // 2, H // 2 + 24),
                     DIM, center=True)
            elif self.fight.over and self.fight.over_t > 0.6:
                ov = pygame.Surface((W, H), pygame.SRCALPHA)
                ov.fill((6, 7, 12, 120))
                s.blit(ov, (0, 0))
                won = self.fight.over == "won"
                text(s, "IT IS DOWN" if won else "THE MACHINE IS DOWN", 54,
                     (W // 2, H // 2 - 40), GOOD if won else BAD, center=True)
                if self.fight.over_t > 1.2:
                    text(s, "press anything", 20, (W // 2, H // 2 + 30), DIM,
                         center=True)
        elif self.state == "after":
            self.after.t += dt
            self.after.draw(s, mouse)
        elif self.state == "end":
            self.ending_screen.t += dt
            self.ending_screen.draw(s, mouse)
        pygame.display.flip()

    def loop(self):
        while self.running:
            self.frame()


def main():
    pygame.init()
    try:
        pygame.display.set_mode((W, H))
    except pygame.error as e:
        print("no display:", e)
        return 1
    App().loop()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
