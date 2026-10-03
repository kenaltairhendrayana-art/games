"""
CAT CATALOGUE
=============
A dim room, a warm lamp, and a parcel on the way.

A cozy collecting game. You have a desk, a laptop and ten dollars. You
order a sack of cat cards off a website, you wait for the post, you cut
the tape, and whatever is inside comes to live in the room and earn its
keep. When you can afford the next parcel, you order the next parcel.

Duplicates are not waste - two of a breed take its card to level 2, four
more to level 3, and so on up to level 10, at which point that breed is
RETIRED from the catalogue and will never be sent to you again. A full
binder is twenty-four retired breeds and a shop with nothing left to sell.

Nothing ships beside this file. Every cat, every card, every parcel and
the website you order from are drawn here in code, and the music and the
sounds are synthesised at runtime.

Requirements: pygame-ce (or pygame)  ->  pip install pygame-ce
Run:                                     python cat_catalogue.py

THE FLAT
  Three rooms, and you walk between them.

  THE HALL        the front door, the mat, and whatever the post has left
  THE DESK        the lamp, the laptop you order from, and the binder
  THE CAT ROOM    the tree, the shelves, the basket, and the cats on them

  Your cats take the best spots first, in the order you have taken them
  furthest, and they go on earning wherever you happen to be standing.

CONTROLS
  Everything is clickable. The keys are shortcuts, not a second interface.
  A D  or the arrows   walk to the next room
  L  the laptop        B  the binder        O  go and get the post
  M  music             S  sounds            F11 fullscreen
  SPACE  flip the next card, or flip all of them
  ESC  back one screen, then the pause card
  Click a cat. It will tell you who it is.
"""

import json
import math
import os
import random
import sys
import time
from array import array

import pygame

TAU = math.tau

W, H = 1180, 760
FPS = 60

# ---------------------------------------------------------------------------
# THE LIGHT
#
# One lamp, one laptop, and nothing else. Every colour in the game is
# mixed for that: the darks are brown rather than grey, the brights are
# amber rather than white, and there is no pure white or pure black
# anywhere in the file. The final grade (see `grade()`) multiplies the
# whole frame by a warm vignette, so anything drawn near an edge is
# already dimmer than the same colour drawn under the lamp.
# ---------------------------------------------------------------------------
INK      = (16, 12, 11)        # the dark of the room, behind everything
ROOM     = (38, 28, 24)        # the far wall
ROOM_LO  = (26, 19, 17)        # the corners of it
WOOD     = (62, 42, 31)        # the desk
WOOD_HI  = (92, 63, 44)        # the edge of it, where the lamp lands
WOOD_LO  = (41, 27, 20)        # under it
RUG      = (74, 44, 40)        # the rug, a dull red
PAPER    = (226, 203, 170)     # card stock under a tungsten bulb
PAPER_LO = (191, 165, 132)
PAPER_HI = (245, 229, 202)
CREAM    = (247, 231, 203)     # the brightest thing that is not a light
TEA      = (201, 155, 101)     # labels, rules, hairlines
MUTED    = (142, 114, 92)      # text you are not meant to read first
DIM      = (104, 83, 68)
LAMP     = (255, 198, 122)     # the bulb
EMBER    = (238, 146, 78)      # the warm accent - prices, coins, totals
DEEP     = (28, 20, 18)        # panel fill
SCREEN   = (30, 26, 28)        # the laptop, which is in dark mode like
SCREEN_HI = (46, 40, 41)       # everything else at this hour
LINK     = (233, 173, 106)
GOOD     = (150, 184, 124)
BAD      = (196, 104, 90)

RARITY = (
    # name          colour             income/s at level 1
    ("COMMON",    (171, 152, 126), 0.05),
    ("UNCOMMON",  (126, 171, 131), 0.16),
    ("RARE",      (116, 150, 208), 0.45),
    ("PEDIGREE",  (184, 132, 208), 1.20),
    ("LEGEND",    (240, 178, 86),  3.00),
)
R_COMMON, R_UNCOMMON, R_RARE, R_PEDIGREE, R_LEGEND = range(5)

MAX_LEVEL = 10


def rarity_name(r):
    return RARITY[r][0]


def rarity_colour(r):
    return RARITY[r][1]


# ---------------------------------------------------------------------------
# SMALL TOOLS
# ---------------------------------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    """Blend two colours. t=0 is all a, t=1 is all b."""
    t = clamp(t, 0.0, 1.0)
    return (round(a[0] + (b[0] - a[0]) * t),
            round(a[1] + (b[1] - a[1]) * t),
            round(a[2] + (b[2] - a[2]) * t))


def shade(c, k):
    """Scale a colour's brightness, keeping it inside the byte range."""
    return (clamp(round(c[0] * k), 0, 255),
            clamp(round(c[1] * k), 0, 255),
            clamp(round(c[2] * k), 0, 255))


def warm(c, k=0.5):
    """Push a colour toward lamplight. Used on anything meant to look lit."""
    return mix(c, LAMP, k)


def money(v):
    """$12  $1,240  $8.40 - cents only while cents still matter."""
    if v >= 100 or abs(v - round(v)) < 0.005:
        return "$" + f"{int(round(v)):,}"
    if v >= 10:
        return "$" + f"{v:.1f}"
    return "$" + f"{v:.2f}"


def rate(v):
    if v >= 100:
        return f"{v:,.0f}/s"
    if v >= 10:
        return f"{v:.1f}/s"
    return f"{v:.2f}/s"


def clock_str(secs):
    """A delivery time, in the units a person would say it in."""
    secs = max(0, int(math.ceil(secs)))
    if secs >= 60:
        return f"{secs // 60}m {secs % 60:02d}s"
    return f"{secs}s"


_fonts = {}
_FAMILIES = {
    # The room is a book; the website is a terminal in a dark theme.
    "serif": "georgia,garamond,palatinolinotype,timesnewroman,dejavuserif,serif",
    "sans": "trebuchetms,verdana,segoeui,dejavusans,arial",
    "mono": "consolas,couriernew,dejavusansmono,monospace",
}


def font(size, bold=False, kind="serif"):
    key = (size, bold, kind)
    f = _fonts.get(key)
    if f is None:
        path = pygame.font.match_font(_FAMILIES[kind])
        f = pygame.font.Font(path, size) if path else pygame.font.SysFont(None, size)
        f.set_bold(bold)
        _fonts[key] = f
    return f


def fit(label, size, width, bold=False, kind="serif"):
    """The largest size up to `size` whose label fits inside `width`."""
    while size > 8 and font(size, bold, kind).size(label)[0] > width:
        size -= 1
    return size


def text(surf, s, size, pos, colour, center=False, right=False, left=False,
         shadow=True, bold=False, kind="serif", alpha=255, max_w=0):
    """One line, placed by one of four anchors. `max_w` shrinks it to fit.

    A label that overruns its own panel is the easiest way for this UI to
    go wrong and the hardest to notice, so fitting is part of drawing.
    """
    if max_w:
        size = fit(s, size, max_w, bold, kind)
    f = font(size, bold, kind)
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
        sh = f.render(s, True, INK)
        sh.set_alpha(min(alpha, 140))
        surf.blit(sh, (r.x + 1, r.y + 2))
    surf.blit(img, r)
    return r


def wrap(s, size, width, bold=False, kind="serif"):
    """Break a string into lines that fit `width`."""
    f = font(size, bold, kind)
    out, line = [], ""
    for word in s.split():
        trial = word if not line else line + " " + word
        if f.size(trial)[0] <= width:
            line = trial
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def paragraph(surf, s, size, pos, colour, width, leading=4, bold=False,
              kind="serif", alpha=255, center=False):
    x, y = pos
    for line in wrap(s, size, width, bold, kind):
        text(surf, line, size, (x + (width // 2 if center else 0), y), colour,
             center=center, bold=bold, kind=kind, alpha=alpha, shadow=False)
        y += size + leading
    return y


# ---------------------------------------------------------------------------
# LIGHT, DRAWN
# ---------------------------------------------------------------------------
_glows = {}


def glow(surf, pos, radius, colour, strength=1.0, steps=20):
    """A soft warm light, added to whatever is under it.

    The falloff is baked into the COLOUR and not into the alpha. pygame's
    BLEND_ADD ignores source alpha completely, so the usual trick - rings
    of constant colour at decreasing alpha - gives a flat saturated disc
    with a hard edge, which is not a light. Scaling the colour toward
    black instead means the outer rings add nothing and only the centre
    is bright.
    """
    radius = int(radius)
    if radius <= 0:
        return
    key = (radius, tuple(colour), round(strength, 2), steps)
    img = _glows.get(key)
    if img is None:
        img = pygame.Surface((radius * 2, radius * 2))
        img.set_colorkey((0, 0, 0))
        for i in range(steps, 0, -1):
            f = i / steps
            k = strength * (1.0 - f) ** 2.2
            pygame.draw.circle(img, shade(colour, k), (radius, radius),
                               max(1, int(radius * f)))
        _glows[key] = img
    surf.blit(img, (pos[0] - radius, pos[1] - radius),
              special_flags=pygame.BLEND_ADD)


_grade = None


def grade(surf, lamp=1.0):
    """The last thing done to every frame: a warm multiply and a vignette.

    This is what makes the room dim. Panels and text are drawn at honest
    brightness and then lose some of it here - more the further they sit
    from the lamp, which is up and left of centre.
    """
    global _grade
    if _grade is None:
        small = pygame.Surface((80, 52))
        cx, cy = 0.44, 0.34
        for y in range(52):
            for x in range(80):
                dx = (x / 79 - cx) * 1.18
                dy = (y / 51 - cy)
                d = math.sqrt(dx * dx + dy * dy) / 0.86
                k = clamp(1.06 - 0.80 * d * d, 0.22, 1.0)
                small.set_at((x, y), (clamp(int(255 * k), 0, 255),
                                      clamp(int(240 * k), 0, 255),
                                      clamp(int(218 * k), 0, 255)))
        _grade = pygame.transform.smoothscale(small, (W, H))
    if lamp >= 0.999:
        surf.blit(_grade, (0, 0), special_flags=pygame.BLEND_MULT)
    else:
        tmp = _grade.copy()
        tmp.fill(shade((255, 255, 255), lamp), special_flags=pygame.BLEND_MULT)
        surf.blit(tmp, (0, 0), special_flags=pygame.BLEND_MULT)


def panel(surf, r, fill=DEEP, edge=None, radius=10, shadow=True, alpha=255):
    """A card, a dialog, a shelf - everything in this game sits on one."""
    r = pygame.Rect(r)
    if shadow:
        sh = pygame.Surface((r.w + 16, r.h + 18), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 92), (8, 10, r.w, r.h),
                         border_radius=radius + 2)
        surf.blit(sh, (r.x - 4, r.y - 4))
    if alpha < 255:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*fill, alpha), (0, 0, r.w, r.h),
                         border_radius=radius)
        surf.blit(s, r.topleft)
    else:
        pygame.draw.rect(surf, fill, r, border_radius=radius)
    if edge:
        pygame.draw.rect(surf, edge, r, width=2, border_radius=radius)
    return r


def hairline(surf, x1, y, x2, colour=None, alpha=70):
    if x2 <= x1:
        return
    s = pygame.Surface((x2 - x1, 1), pygame.SRCALPHA)
    s.fill((*(colour or TEA), alpha))
    surf.blit(s, (x1, y))


def bar(surf, r, frac, fill, back=None, radius=4):
    r = pygame.Rect(r)
    pygame.draw.rect(surf, back or shade(fill, 0.22), r, border_radius=radius)
    w = int(r.w * clamp(frac, 0.0, 1.0))
    if w > 1:
        pygame.draw.rect(surf, fill, (r.x, r.y, w, r.h), border_radius=radius)


# ---------------------------------------------------------------------------
# BUTTONS
#
# A click target in this codebase is a drawable, and the draw loop runs
# after the hand-drawn content. A target whose style is "hit" draws
# NOTHING - that is the whole point of it - while one with a label draws a
# panel. Mixing the two up paints over the thing you just drew by hand,
# so the distinction lives in the class rather than in the caller's head.
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, key, style="plain", size=20, kind="serif",
                 enabled=True, note="", colour=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.key = key
        self.style = style
        self.size = size
        self.kind = kind
        self.enabled = enabled
        self.note = note
        self.colour = colour
        self.hot = False

    def hover(self, mouse):
        self.hot = self.enabled and self.rect.collidepoint(mouse)
        return self.hot

    def draw(self, surf):
        if self.style == "hit":
            return                   # a hit area is invisible, on purpose
        r = self.rect
        acc = self.colour or EMBER
        if self.style == "link":
            col = acc if self.enabled else DIM
            if self.hot:
                col = warm(col, 0.45)
            t = text(surf, self.label, self.size, r.center, col, center=True,
                     kind=self.kind, shadow=False)
            if self.hot:
                hairline(surf, t.left, t.bottom + 1, t.right, col, 160)
            return
        if not self.enabled:
            panel(surf, r, shade(DEEP, 0.85), shade(DIM, 0.6), radius=8,
                  shadow=False)
            text(surf, self.label, self.size, r.center, DIM, center=True,
                 kind=self.kind, max_w=r.w - 18)
            if self.note:
                text(surf, self.note, 13, (r.centerx, r.bottom - 10),
                     shade(DIM, 0.85), center=True, kind="mono", shadow=False)
            return
        if self.style == "solid":
            fill = mix(acc, INK, 0.28 if self.hot else 0.46)
            panel(surf, r, fill, warm(acc, 0.3) if self.hot else acc,
                  radius=8, shadow=False)
            lab = CREAM if self.hot else mix(CREAM, acc, 0.3)
        else:
            fill = mix(DEEP, acc, 0.22 if self.hot else 0.07)
            panel(surf, r, fill,
                  mix(TEA, acc, 0.5) if self.hot else shade(TEA, 0.55),
                  radius=8, shadow=False)
            lab = CREAM if self.hot else mix(CREAM, MUTED, 0.45)
        pad = 18
        if self.note:
            text(surf, self.label, self.size, (r.centerx, r.centery - 7), lab,
                 center=True, kind=self.kind, max_w=r.w - pad)
            text(surf, self.note, 13, (r.centerx, r.bottom - 12),
                 mix(lab, DEEP, 0.4), center=True, kind="mono", shadow=False)
        else:
            text(surf, self.label, self.size, r.center, lab, center=True,
                 kind=self.kind, max_w=r.w - pad)


# ---------------------------------------------------------------------------
# THE BREEDS
#
# Twenty-four of them, and the thing that matters here is that they differ
# in SHAPE and not only in colour. Every number in a `look` is a knob on
# the one drawing routine below: how wide the face sits, how far the ears
# stand, how much coat there is, what the tail does, how long the legs are.
# Two breeds that share a silhouette are a bug in this table, not in the
# drawing - which is why `cat_test.py sameness` strips the colour and the
# size off every portrait before it compares them.
#
#   size    overall scale, 0.85 small to 1.3 enormous
#   body    how heavy through the chest and haunches
#   facew   face width; a wedge is 0.86, a round British head is 1.22
#   cheek   how far the jowls spread past the skull
#   ear     ear height, and `fold` tips them forward and down
#   flat    a squashed muzzle, 0 normal, 1 Persian
#   fluff   coat length - it swells the silhouette and adds a ruff
#   legs    leg length; a Savannah is on stilts, a Persian is not
#   tail    "none" "pom" "plain" "plume"
#   eye     "round" or "almond", and the colour, or ("odd", a, b)
#   pat     the markings: see `_marks_*` below
# ---------------------------------------------------------------------------
class Breed:
    __slots__ = ("key", "name", "rarity", "origin", "note", "look")

    def __init__(self, key, name, rarity, origin, note, look):
        self.key = key
        self.name = name
        self.rarity = rarity
        self.origin = origin
        self.note = note
        self.look = look

    @property
    def base_rate(self):
        return RARITY[self.rarity][2]

    def rate_at(self, level):
        """A card earns its base rate once per level. Level 10 is ten cats."""
        return self.base_rate * level

    @property
    def colour(self):
        return rarity_colour(self.rarity)


def L(**kw):
    """One breed's look, with the ordinary cat as the default."""
    look = dict(size=1.0, body=1.0, facew=1.0, faceh=1.0, cheek=1.0, ear=1.0,
                fold=0.0, tuft=0.0, flat=0.0, fluff=0.25, legs=1.0,
                tail="plain", eyeshape="almond", eye=(188, 164, 74),
                coat=(126, 104, 86), mark=(78, 60, 48), belly=(196, 176, 150),
                pat="tabby", skin=0.0, curl=0.0, nose=(198, 128, 124))
    look.update(kw)
    return look


BREEDS = (
    # -- COMMON ------------------------------------------------------------
    Breed("dsh", "Domestic Shorthair", R_COMMON, "everywhere",
          "Has three names in this house and answers to none of them.",
          L(coat=(136, 110, 84), mark=(84, 62, 44), belly=(206, 186, 156),
            pat="tabby", eye=(190, 166, 80), body=0.98, facew=1.02,
            ear=1.08, legs=1.06, faceh=1.02)),
    Breed("dlh", "Domestic Longhair", R_COMMON, "everywhere",
          "A cloud that has learned where the warm spot is.",
          L(fluff=1.0, tail="plume", coat=(150, 118, 86), mark=(92, 64, 46),
            belly=(216, 196, 164), pat="tortie", body=1.04, facew=1.14,
            cheek=1.26, eye=(176, 150, 70), legs=0.78, faceh=0.92)),
    Breed("ash", "American Shorthair", R_COMMON, "the United States",
          "Built like a farm gate. Sleeps like one too.",
          L(coat=(150, 148, 142), mark=(84, 84, 82), belly=(206, 204, 198),
            pat="blotched", body=1.16, facew=1.14, cheek=1.2, legs=0.95,
            eye=(196, 174, 86), ear=0.92, fluff=0.2)),
    Breed("esh", "European Shorthair", R_COMMON, "the north of Europe",
          "Came in off a cold street and never mentioned it again.",
          L(coat=(126, 126, 124), mark=(70, 70, 72), belly=(190, 190, 188),
            pat="tabby", body=1.0, facew=1.0, faceh=1.0, cheek=1.02,
            eye=(156, 178, 110), ear=1.14, legs=1.0, fluff=0.52)),
    Breed("jbt", "Japanese Bobtail", R_COMMON, "Japan",
          "The tail is a pom-pom and the walk is all shoulders.",
          L(tail="pom", coat=(238, 226, 206), mark=(206, 128, 62),
            belly=(246, 238, 222), pat="bicolour", body=0.92, facew=0.94,
            legs=1.12, ear=1.1, eye=(196, 176, 92), fluff=0.22)),
    Breed("mnx", "Manx", R_COMMON, "the Isle of Man",
          "No tail at all, and absolutely no opinion about it.",
          L(tail="none", coat=(196, 138, 76), mark=(142, 88, 44),
            belly=(230, 206, 176), pat="tabby", body=1.2, facew=1.12,
            cheek=1.16, legs=0.86, fluff=0.34, eye=(190, 160, 72))),

    # -- UNCOMMON ----------------------------------------------------------
    Breed("bsh", "British Shorthair", R_UNCOMMON, "Britain",
          "A round grey full stop at the end of the sofa.",
          L(coat=(124, 134, 148), mark=(96, 106, 120), belly=(146, 156, 170),
            pat="solid", body=1.26, facew=1.24, faceh=0.96, cheek=1.3,
            ear=0.84, legs=0.84, fluff=0.3, eye=(214, 150, 60),
            eyeshape="round")),
    Breed("rbl", "Russian Blue", R_UNCOMMON, "Arkhangelsk",
          "Silver at the tips, so it looks lit even when it is not.",
          L(coat=(126, 142, 156), mark=(154, 170, 184), belly=(150, 166, 180),
            pat="smoke", body=0.86, facew=0.92, cheek=0.84, ear=1.24,
            legs=1.16, fluff=0.54, eye=(126, 188, 136), eyeshape="round")),
    Breed("sia", "Siamese", R_UNCOMMON, "Thailand",
          "Will tell you about the door at some length.",
          L(coat=(224, 206, 178), mark=(72, 54, 50), belly=(236, 222, 198),
            pat="point", body=0.86, facew=0.84, faceh=1.1, cheek=0.76,
            ear=1.3, legs=1.14, fluff=0.14, eye=(104, 164, 212),
            eyeshape="almond")),
    Breed("mcn", "Maine Coon", R_UNCOMMON, "Maine",
          "Takes up two cushions and considers that modest.",
          L(size=1.22, body=1.3, facew=1.1, cheek=1.12, ear=1.22, tuft=1.0,
            fluff=1.0, tail="plume", legs=1.0, coat=(142, 108, 76),
            mark=(86, 58, 40), belly=(214, 192, 158), pat="blotched",
            eye=(188, 158, 72))),
    Breed("rag", "Ragdoll", R_UNCOMMON, "California",
          "Picked up, goes completely liquid. Every time.",
          L(size=1.16, body=1.22, facew=1.06, cheek=0.98, ear=0.96,
            fluff=0.62, tail="plume", legs=1.06, coat=(232, 220, 200),
            mark=(104, 96, 110),
            belly=(242, 234, 218), pat="point", eye=(118, 160, 214),
            eyeshape="round")),
    Breed("sfd", "Scottish Fold", R_UNCOMMON, "Perthshire",
          "Ears folded flat, like it is listening to the floor.",
          L(fold=1.0, ear=0.7, body=1.12, facew=1.2, faceh=0.94, cheek=1.24,
            legs=0.88, fluff=0.42, coat=(144, 134, 124), mark=(92, 84, 78),
            belly=(198, 190, 180), pat="tabby", eye=(206, 160, 76),
            eyeshape="round")),

    # -- RARE --------------------------------------------------------------
    Breed("nfc", "Norwegian Forest", R_RARE, "Norway",
          "Dressed for weather this room will never have.",
          L(size=1.2, body=1.24, facew=1.0, faceh=1.08, ear=1.14, tuft=1.0,
            fluff=1.0, tail="plume", legs=1.04, coat=(58, 52, 52),
            mark=(238, 232, 220), belly=(240, 234, 222), pat="bicolour",
            eye=(150, 184, 110))),
    Breed("ben", "Bengal", R_RARE, "a laboratory in Yuba City",
          "Spotted like something far less comfortable.",
          L(size=1.06, body=1.1, facew=0.98, cheek=0.94, ear=0.9, legs=1.08,
            fluff=0.12, coat=(206, 160, 86), mark=(62, 48, 38),
            belly=(232, 208, 164), pat="spotted", eye=(142, 188, 128),
            eyeshape="almond")),
    Breed("aby", "Abyssinian", R_RARE, "the Nile, allegedly",
          "Ticked coat, so it changes colour as it turns.",
          L(size=0.98, body=1.0, facew=0.92, faceh=1.0, cheek=0.94,
            ear=1.2, legs=1.14, fluff=0.1, coat=(176, 114, 66),
            mark=(96, 56, 34), belly=(206, 152, 104), pat="ticked",
            eye=(206, 164, 70), eyeshape="almond")),
    Breed("per", "Persian", R_RARE, "Isfahan",
          "The face of a cat who has just been told something.",
          L(size=1.1, body=1.26, facew=1.3, faceh=0.92, cheek=1.34, ear=0.66,
            flat=1.0, fluff=1.0, tail="plume", legs=0.78,
            coat=(232, 212, 176), mark=(206, 180, 140), belly=(242, 228, 202),
            pat="smoke", eye=(216, 142, 64), eyeshape="round")),
    Breed("sph", "Sphynx", R_RARE, "Toronto",
          "Warm to the touch, which is the entire argument for it.",
          L(size=1.0, body=0.84, facew=0.94, faceh=1.06, cheek=0.72,
            ear=1.52, legs=1.1, fluff=0.0, skin=1.0, coat=(206, 160, 148),
            mark=(176, 128, 118), belly=(220, 180, 168), pat="solid",
            eye=(198, 190, 110), eyeshape="almond", nose=(190, 134, 130))),

    # -- PEDIGREE ----------------------------------------------------------
    Breed("sav", "Savannah", R_PEDIGREE, "a serval and a nerve",
          "Legs like a deer. Can reach the top of the bookcase, flat.",
          L(size=1.18, body=0.98, facew=0.86, faceh=1.06, cheek=0.78,
            ear=1.5, legs=1.42, fluff=0.1, coat=(214, 172, 96),
            mark=(44, 38, 34), belly=(234, 212, 168), pat="spotted",
            eye=(188, 180, 96), eyeshape="almond")),
    Breed("tan", "Turkish Angora", R_PEDIGREE, "Ankara",
          "Silk, mostly. Sheds it generously onto dark clothing.",
          L(size=1.04, body=0.9, facew=0.9, faceh=1.06, cheek=0.82, ear=1.2,
            fluff=0.9, tail="plume", legs=1.12, coat=(244, 236, 220),
            mark=(226, 214, 196), belly=(250, 244, 232), pat="solid",
            eye=(116, 170, 216), eyeshape="almond")),
    Breed("bir", "Birman", R_PEDIGREE, "a temple, by legend",
          "White gloves on all four feet, and it knows.",
          L(size=1.1, body=1.16, facew=1.0, faceh=1.06, cheek=0.96,
            ear=1.02, fluff=0.48, tail="plume", legs=1.08,
            coat=(234, 220, 196), mark=(96, 72, 70), belly=(244, 234, 216),
            pat="gloves", eye=(112, 156, 212), eyeshape="round")),
    Breed("dvx", "Devon Rex", R_PEDIGREE, "a tin mine in Devon",
          "A pixie in a second-hand jumper, two sizes too big.",
          L(size=0.88, body=0.82, facew=1.06, faceh=0.86, cheek=1.1, ear=1.56,
            legs=1.0, fluff=0.3, curl=1.0, coat=(150, 128, 120),
            mark=(104, 86, 80), belly=(196, 178, 168), pat="smoke",
            eye=(176, 188, 120), eyeshape="round")),

    # -- LEGEND ------------------------------------------------------------
    Breed("kma", "Khao Manee", R_LEGEND, "Siam, kept by kings",
          "One blue eye, one gold. The diamond eye, they called it.",
          L(size=1.02, body=0.88, facew=0.96, faceh=1.04, cheek=0.88,
            ear=1.08, legs=1.2, fluff=0.22, coat=(248, 242, 232),
            mark=(232, 226, 216), belly=(252, 248, 240), pat="solid",
            eye=("odd", (112, 168, 220), (222, 176, 72)), eyeshape="almond")),
    Breed("lyk", "Lykoi", R_LEGEND, "a feral litter in Tennessee",
          "Half-coated, so it comes with its own moonlight.",
          L(size=1.0, body=1.06, facew=1.06, faceh=0.96, cheek=1.04,
            ear=1.16, legs=0.94, fluff=0.56, skin=0.55, coat=(62, 58, 58),
            mark=(206, 200, 192), belly=(96, 92, 92), pat="roan",
            eye=(214, 170, 76), eyeshape="almond")),
    Breed("sok", "Sokoke", R_LEGEND, "the Arabuko forest",
          "The rarest coat in the book, and it was never bred for.",
          L(size=1.0, body=0.80, facew=0.88, faceh=1.02, cheek=0.78,
            ear=1.0, legs=1.36, fluff=0.04, coat=(178, 140, 100),
            mark=(74, 54, 40), belly=(206, 176, 136), pat="blotched",
            eye=(178, 182, 108), eyeshape="almond")),
)

BY_KEY = {b.key: b for b in BREEDS}
BY_RARITY = tuple(tuple(b for b in BREEDS if b.rarity == r) for r in range(5))


# ---------------------------------------------------------------------------
# WHAT A LEVEL LOOKS LIKE
#
# A cat on level 1 has just come out of a paper sack. By level 10 it has
# been fed, brushed and kept for a long time, and it should be possible
# to see that across the room without reading the number.
#
# The levelling does NOT get its own drawing code. It moves the same
# knobs the breed table moves - coat, condition, fluff, size - so a
# groomed cat cannot come out a shape the routine does not already know
# how to make, and a breed that looks wrong at level 10 is wrong at level
# 1 as well. The only things grooming adds that the table has no column
# for are the collar, the tag and the bell, and those are worn, not grown.
#
# Five grades, because a change you cannot see is not a reward:
#     1-2  a stray      3-4  settling in    5-6  kept
#     7-9  somebody-s   10   retired, and it knows
# ---------------------------------------------------------------------------
GRADE_AT = (1, 3, 5, 7, 10)
GRADE_NAME = ("off the street", "settling in", "kept", "well kept",
              "retired")
COLLAR_AT = 4            # a collar
TAG_AT = 7               # ... with a tag on it
BELL_AT = 10             # ... and a bell


def grade_of(level):
    """0 to 4. What a cat and its card look like at this level."""
    g = 0
    for i, need in enumerate(GRADE_AT):
        if level >= need:
            g = i
    return g


def _dull(c, k):
    """Pull a colour toward its own grey. A coat in poor condition is not
    a darker coat, it is a greyer one - which is the thing that actually
    reads at the size these are drawn."""
    g = round(c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11)
    return mix(c, (g, g, g), k)


def groom(P, level):
    """The same breed, better kept. Returns a look, not a drawing."""
    f = (clamp(level, 1, MAX_LEVEL) - 1) / (MAX_LEVEL - 1)
    out = dict(P)
    out["coat"] = mix(_dull(shade(P["coat"], 0.74), 0.72),
                      warm(P["coat"], 0.08), f)
    out["belly"] = mix(_dull(shade(P["belly"], 0.78), 0.66), P["belly"], f)
    out["mark"] = mix(_dull(shade(P["mark"], 0.82), 0.58), P["mark"], f)
    out["body"] = P["body"] * (0.90 + 0.12 * f)
    out["fluff"] = P["fluff"] * (0.82 + 0.26 * f)
    out["size"] = P["size"] * (0.94 + 0.07 * f)
    out["nick"] = 1.0 if level < GRADE_AT[1] else 0.0
    out["bib"] = 1.0 if level >= GRADE_AT[3] else 0.0
    return out


# ---------------------------------------------------------------------------
# DRAWING A CAT
#
# One routine, twenty-four sets of numbers. It is built once per breed,
# pose and size into a cached surface, because a cat is expensive to draw
# and cheap to blit: the animation in the room is a squash, a blink and a
# tail, applied to a finished cat.
#
# The pattern is painted on a second surface and masked by a WHITE copy of
# the silhouette with BLEND_RGBA_MIN. Masking with the coloured body
# instead would take the minimum of the two colours channel by channel and
# quietly darken every marking.
# ---------------------------------------------------------------------------
def _shapes_sit(P, w, h):
    """The body of a sitting cat, seen from the front and slightly above.

    Returns primitives, in paint order. Everything here is part of the
    silhouette, which means everything here can carry markings.
    """
    body, legs, fluff = P["body"], P["legs"], P["fluff"]
    cx = w * 0.5
    out = []

    # the tail, behind everything
    tail = P["tail"]
    if tail != "none":
        if tail == "pom":
            out.append(("circle", (cx + w * 0.27 * body, h * 0.85),
                        h * 0.075 * (1 + fluff)))
        else:
            for i, (tx, ty, tr) in enumerate(_tail_path(P, w, h)):
                out.append(("circle", (tx, ty), tr))

    # The sitting body is a bell: narrow across the shoulders, wide at the
    # base where the back legs are folded under. Two stacked ellipses read
    # as a snowman, which is the shape this started as.
    left, right, hbot, bot = _bell(P, w, h)
    out.append(("poly", left + right[::-1]))
    out.append(("ellipse", (cx - hbot, bot - h * 0.11, hbot * 2, h * 0.13)))

    # hind paws out at the sides, front legs down the middle
    out.append(("ellipse", (cx - hbot * 0.98, h * 0.875,
                            w * 0.17, h * 0.085)))
    out.append(("ellipse", (cx + hbot * 0.98 - w * 0.17, h * 0.875,
                            w * 0.17, h * 0.085)))
    lw = w * 0.125
    ltop = h * (0.66 - 0.05 * legs)
    lbot = h * 0.925
    for sx in (-1, 1):
        lx = cx + sx * w * 0.115 * body - lw * 0.5
        out.append(("ellipse", (lx, ltop, lw, lbot - ltop)))
        out.append(("ellipse", (lx - lw * 0.18, lbot - h * 0.045,
                                lw * 1.36, h * 0.075)))

    # the ruff, which is the whole difference between a shorthair and not
    if fluff > 0.3:
        rw = w * (0.42 + 0.26 * fluff) * body
        out.append(("ellipse", (cx - rw * 0.5, h * 0.36, rw, h * 0.23)))

    return out


def _bell(P, w, h):
    """The two sides of the sitting body, and where its base is.

    The coat bumps follow these points, so a longhair swells along its
    own outline instead of around a circle somewhere inside it.
    """
    body, fluff = P["body"], P["fluff"]
    cx = w * 0.5
    top, bot = h * 0.34, h * 0.93
    htop = w * 0.175 * body * (1.0 + 0.18 * fluff)
    hbot = w * 0.300 * body * (1.0 + 0.08 * fluff)
    left, right = [], []
    n = 16
    for i in range(n + 1):
        f = i / n
        y = top + (bot - top) * f
        hw = htop + (hbot - htop) * (f ** 0.78)
        left.append((cx - hw, y))
        right.append((cx + hw, y))
    return left, right, hbot, bot


def _tail_path(P, w, h, pose="sit"):
    """Where the tail lies, as (x, y, radius) down its length.

    One function and both poses, because the MARKINGS have to find the
    tail too. When this returned only the sitting path, a point breed
    asleep on the windowsill wore its dark tail as a club across its own
    ribs - two bits of code disagreeing about where a thing is, which is
    the way this UI always goes wrong.
    """
    body, fluff, tail = P["body"], P["fluff"], P["tail"]
    if tail in ("none", "pom"):
        return []
    out = []
    if pose == "curl":
        thick = h * (0.05 + 0.04 * fluff) * (1.45 if tail == "plume" else 1.0)
        n = 18
        for i in range(n):
            f = i / (n - 1)
            a = -0.10 + f * 2.7
            out.append((w * (0.56 + 0.37 * math.cos(a)),
                        h * (0.74 + 0.26 * math.sin(a)),
                        thick * (0.6 + 0.4 * (1 - f))))
        return out
    thick = h * (0.028 + 0.026 * fluff) * (1.5 if tail == "plume" else 1.0)
    n = 22
    for i in range(n):
        f = i / (n - 1)
        a = -0.35 + f * 2.2
        tx = w * 0.5 + w * (0.19 * body + 0.155 * math.sin(a))
        ty = h * (0.90 - 0.48 * f ** 1.2)
        out.append((tx, ty, thick * (0.60 + 0.40 * (1 - f * 0.5))))
    return out


def _head_box(P, w, h):
    """Where the head sits, as a rect. The ears and the face hang off this."""
    hw = w * 0.56 * P["facew"]
    hh = h * 0.39 * P["faceh"]
    return pygame.Rect(round(w * 0.5 - hw * 0.5), round(h * 0.085),
                       round(hw), round(hh))


def _shapes_head(P, w, h):
    out = []
    hb = _head_box(P, w, h)
    ear = P["ear"]
    eh = hb.h * 0.62 * ear
    ew = hb.w * 0.34 * (0.8 + 0.3 * ear)
    for sx in (-1, 1):
        bx = hb.centerx + sx * hb.w * 0.34
        by = hb.y + hb.h * 0.30
        if P["fold"] > 0.4:
            # A folded ear is a flap lying forward and DOWN over its own
            # opening: a wide low lobe on the corner of the skull, not a
            # small triangle, which is what it looked like at first.
            out.append(("ellipse", (bx - ew * 0.80, by - eh * 0.44,
                                    ew * 1.60, eh * 1.05)))
        elif sx > 0 and P.get("nick"):
            # The tipped ear. Every cat that has lived outside has one,
            # and it is drawn as a flat top rather than a small notch
            # because at 70 pixels tall a notch is one grey pixel.
            tip_x = bx + sx * ew * 0.42
            out.append(("poly", [
                (bx - sx * ew * 0.72, by + eh * 0.22),
                (tip_x - ew * 0.26, by - eh * 0.60),
                (tip_x + ew * 0.20, by - eh * 0.48),
                (bx + sx * ew * 0.86, by + eh * 0.10)]))
        else:
            tip_x = bx + sx * ew * 0.42
            out.append(("poly", [
                (bx - sx * ew * 0.72, by + eh * 0.22),
                (tip_x, by - eh),
                (bx + sx * ew * 0.86, by + eh * 0.10)]))
    # the skull, then the cheeks spreading past it
    out.append(("ellipse", hb))
    ch = hb.w * 0.34 * P["cheek"]
    for sx in (-1, 1):
        out.append(("ellipse", (hb.centerx + sx * hb.w * 0.30 - ch * 0.5,
                                hb.y + hb.h * 0.50, ch, hb.h * 0.52)))
    # the muzzle - a Persian has almost none
    mw = hb.w * (0.46 - 0.12 * P["flat"])
    mh = hb.h * (0.30 - 0.12 * P["flat"])
    out.append(("ellipse", (hb.centerx - mw * 0.5,
                            hb.bottom - mh * (1.25 - 0.45 * P["flat"]),
                            mw, mh)))
    return out


def _shapes_curl(P, w, h):
    """Asleep: a comma on a cushion, head down on its own front paws.

    Seen from the side and slightly above. The head goes at the LEFT,
    low, resting where the tail comes round to meet it - a sleeping cat
    is a closed circuit, which is the whole charm of the shape.
    """
    body, fluff = P["body"], P["fluff"]
    out = []
    # the tail, round the front of the body and up to the chin
    if P["tail"] != "none":
        thick = h * (0.055 + 0.045 * fluff) * \
            (1.45 if P["tail"] == "plume" else 1.0)
        n = 16
        for i in range(n):
            f = i / (n - 1)
            a = -0.35 + f * 2.25          # from the right flank, round
            out.append(("circle", (w * (0.60 + 0.37 * math.cos(a)),
                                   h * (0.70 + 0.30 * math.sin(a))),
                        thick * (0.6 + 0.4 * (1 - f))))
    # the back, a long low arc
    bw = w * 0.80 * (0.94 + 0.10 * body)
    bh = h * 0.70 * (0.92 + 0.14 * body)
    out.append(("ellipse", (w * 0.20, h - bh - h * 0.02, bw, bh)))
    # the haunch, which is what makes it a sleeping cat and not a loaf
    out.append(("ellipse", (w * 0.56, h * 0.42, w * 0.40, h * 0.46)))
    # the front paws, tucked under the chin
    out.append(("ellipse", (w * 0.14, h * 0.80, w * 0.26, h * 0.17)))
    # and the tail last, because it comes round the FRONT of the paws
    if P["tail"] == "pom":
        out.append(("circle", (w * 0.88, h * 0.76), h * 0.11 * (1 + fluff)))
    for tx, ty, tr in _tail_path(P, w, h, "curl"):
        out.append(("circle", (tx, ty), tr))
    return out


def _head_box_curl(P, w, h):
    hw = w * 0.36 * P["facew"]
    hh = h * 0.44 * P["faceh"]
    return pygame.Rect(round(w * 0.06), round(h * 0.42), round(hw), round(hh))


def _as_rect(v):
    if isinstance(v, pygame.Rect):
        return v
    x, y, w, h = v
    return pygame.Rect(round(x), round(y), max(2, round(w)), max(2, round(h)))


def _paint(surf, prims, colour):
    for p in prims:
        if p[0] == "ellipse":
            pygame.draw.ellipse(surf, colour, _as_rect(p[1]))
        elif p[0] == "circle":
            pygame.draw.circle(surf, colour,
                               (round(p[1][0]), round(p[1][1])),
                               max(1, round(p[2])))
        else:
            pygame.draw.polygon(surf, colour, [(round(x), round(y))
                                               for x, y in p[1]])


# -- the markings -----------------------------------------------------------
# Each of these paints onto a transparent surface which is then clipped to
# the silhouette, so they can and do overhang the body; that is what the
# mask is for. `rng` is seeded off the breed key, so a tortie is a
# different tortie from every other tortie and the same one every run.
def _belly_wash(surf, P, w, h, strength=130):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*P["belly"], strength),
                        (w * 0.30, h * 0.52, w * 0.40, h * 0.40))
    pygame.draw.ellipse(s, (*P["belly"], strength // 2),
                        (w * 0.26, h * 0.46, w * 0.48, h * 0.30))
    surf.blit(s, (0, 0))


def _marks_tabby(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h)
    # Mackerel stripes run OUT from the spine and down over the flank.
    # Drawn as straight verticals they read as a prison uniform, which is
    # what the first version of this looked like.
    c = P["mark"]
    lw = max(2, round(w * 0.028))
    for sx in (-1, 1):
        for i in range(4):
            y0 = h * (0.40 + 0.11 * i)
            pts = []
            for j in range(8):
                g = j / 7.0
                pts.append((w * 0.5 + sx * (w * 0.02 + w * 0.30 * P["body"] * g),
                            y0 + h * 0.22 * g * g + h * 0.02 * math.sin(g * 3)))
            pygame.draw.lines(surf, c, False,
                              [(round(a), round(b)) for a, b in pts], lw)
    # the M every tabby wears on its forehead
    y = hb.y + hb.h * 0.26
    for sx in (-1, 1):
        for k in range(3):
            x0 = hb.centerx + sx * (hb.w * 0.06 + k * hb.w * 0.11)
            pygame.draw.line(surf, c, (round(x0), round(y - k * 2)),
                             (round(x0 + sx * hb.w * 0.05),
                              round(y + hb.h * 0.16)), 2)
    path = _tail_path(P, w, h, pose)
    for i, (tx, ty, tr) in enumerate(path):
        if (i // 3) % 2 == 0:
            pygame.draw.circle(surf, c, (round(tx), round(ty)), round(tr))


def _marks_blotched(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h)
    c = P["mark"]
    lw = max(2, round(w * 0.020))
    for sx in (-1, 1):
        cx = w * 0.5 + sx * w * 0.19 * P["body"]
        for k in range(2):
            r = w * (0.040 + k * 0.045)
            pygame.draw.arc(surf, c, (cx - r, h * 0.74 - r, r * 2, r * 2),
                            -1.3, 3.4, lw)
        for k in range(3):           # bars curving down off the shoulder
            y = h * (0.44 + k * 0.058)
            pts = [(w * 0.5 + sx * w * 0.03,  y),
                   (w * 0.5 + sx * w * 0.13 * P["body"], y + h * 0.018),
                   (w * 0.5 + sx * w * 0.23 * P["body"], y + h * 0.058)]
            pygame.draw.lines(surf, c, False,
                              [(round(a), round(b)) for a, b in pts], lw)
    y = hb.y + hb.h * 0.26
    for sx in (-1, 1):
        for k in range(3):
            x0 = hb.centerx + sx * (hb.w * 0.07 + k * hb.w * 0.10)
            pygame.draw.line(surf, c, (round(x0), round(y)),
                             (round(x0 + sx * hb.w * 0.04),
                              round(y + hb.h * 0.15)), 2)


def _marks_spotted(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h, 110)
    c = P["mark"]
    for row in range(8):
        fy = row / 7.0
        y = h * (0.40 + fy * 0.52)
        n = 7 - (row % 2)
        for i in range(n):
            fx = (i + 0.5 + (row % 2) * 0.3) / n
            x = w * (0.16 + fx * 0.68)
            r = w * (0.026 - 0.008 * fy) * rng.uniform(0.75, 1.3)
            pygame.draw.ellipse(surf, c, (x - r, y - r * 0.82, r * 2, r * 1.64))
    for sx in (-1, 1):
        for k in range(3):
            pygame.draw.line(surf, c,
                             (round(hb.centerx + sx * (hb.w * 0.08 + k * hb.w * 0.10)),
                              round(hb.y + hb.h * 0.24)),
                             (round(hb.centerx + sx * (hb.w * 0.10 + k * hb.w * 0.10)),
                              round(hb.y + hb.h * 0.40)), 2)


def _marks_ticked(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h, 150)
    c = P["mark"]
    for _ in range(190):
        x = rng.uniform(w * 0.12, w * 0.88)
        y = rng.uniform(h * 0.18, h * 0.96)
        L2 = h * rng.uniform(0.015, 0.035)
        s = pygame.Surface((3, max(2, round(L2))), pygame.SRCALPHA)
        s.fill((*c, 150))
        surf.blit(s, (round(x), round(y)))


def _marks_point(surf, P, w, h, hb, rng, pose='sit', gloves=False):
    c = P["mark"]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    # the mask: muzzle, round the eyes, up the bridge
    mw, mh = hb.w * 0.76, hb.h * 0.62
    pygame.draw.ellipse(s, (*c, 235), (hb.centerx - mw * 0.5,
                                       hb.bottom - mh * 0.86, mw, mh))
    pygame.draw.ellipse(s, (*c, 190), (hb.centerx - hb.w * 0.17,
                                       hb.y + hb.h * 0.22,
                                       hb.w * 0.34, hb.h * 0.52))
    # ears
    for sx in (-1, 1):
        pygame.draw.ellipse(s, (*c, 230),
                            (hb.centerx + sx * hb.w * 0.34 - hb.w * 0.24,
                             hb.y - hb.h * 0.30, hb.w * 0.48, hb.h * 0.62))
    # the front legs and the tail, found the same way the body finds them
    lw = w * 0.125
    for sx in (-1, 1):
        lx = w * 0.5 + sx * w * 0.115 * P["body"] - lw * 0.5
        pygame.draw.ellipse(s, (*c, 215), (lx - 1, h * 0.70, lw + 2, h * 0.26))
    for tx, ty, tr in _tail_path(P, w, h, pose):
        pygame.draw.circle(s, (*c, 200), (round(tx), round(ty)), round(tr))
    surf.blit(s, (0, 0))
    if gloves:
        g = pygame.Surface((w, h), pygame.SRCALPHA)
        for sx in (-1, 1):
            pygame.draw.ellipse(g, (*P["belly"], 255),
                                (w * 0.5 + sx * w * 0.115 * P["body"] - lw * 0.7,
                                 h * 0.855, lw * 1.4, h * 0.085))
            pygame.draw.ellipse(g, (*P["belly"], 255),
                                (w * 0.5 + sx * w * 0.30 * P["body"] - w * 0.085,
                                 h * 0.87, w * 0.17, h * 0.085))
        surf.blit(g, (0, 0))


def _marks_gloves(surf, P, w, h, hb, rng, pose='sit'):
    _marks_point(surf, P, w, h, hb, rng, pose, gloves=True)


def _marks_bicolour(surf, P, w, h, hb, rng, pose='sit'):
    c = P["mark"]                     # the white, on a dark base
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*c, 255), (w * 0.31, h * 0.44, w * 0.38, h * 0.48))
    lw = w * 0.125
    for sx in (-1, 1):
        pygame.draw.ellipse(s, (*c, 255),
                            (w * 0.5 + sx * w * 0.115 * P["body"] - lw * 0.7,
                             h * 0.74, lw * 1.4, h * 0.22))
        pygame.draw.ellipse(s, (*c, 255),
                            (w * 0.5 + sx * w * 0.30 * P["body"] - w * 0.09,
                             h * 0.86, w * 0.18, h * 0.09))
    # a blaze down the nose, off to one side the way they always are
    pygame.draw.ellipse(s, (*c, 255), (hb.centerx - hb.w * 0.26,
                                       hb.y + hb.h * 0.42,
                                       hb.w * 0.52, hb.h * 0.64))
    for k in range(5):               # a blaze, narrowing as it goes up
        f = k / 4.0
        bw = hb.w * (0.19 - 0.09 * f)
        pygame.draw.ellipse(s, (*c, 255),
                            (hb.centerx - hb.w * 0.02 - bw,
                             hb.y + hb.h * (0.44 - 0.33 * f),
                             bw * 2, hb.h * 0.22))
    surf.blit(s, (0, 0))


def _marks_tortie(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h, 90)
    ginger = (206, 134, 66)
    for i in range(16):
        c = P["mark"] if i % 2 else ginger
        x = rng.uniform(w * 0.14, w * 0.86)
        y = rng.uniform(h * 0.14, h * 0.94)
        rw = w * rng.uniform(0.07, 0.15)
        rh = h * rng.uniform(0.06, 0.13)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*c, 225), (x - rw, y - rh, rw * 2, rh * 2))
        surf.blit(s, (0, 0))


def _marks_smoke(surf, P, w, h, hb, rng, pose='sit'):
    """A shaded undercoat: pale at the belly, deep over the shoulders."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(14):
        f = i / 13.0
        a = int(16 + 58 * (1 - f))
        pygame.draw.ellipse(s, (*P["mark"], a),
                            (w * (0.10 + 0.07 * f), h * (0.10 + 0.10 * f),
                             w * (0.80 - 0.14 * f), h * (0.56 - 0.10 * f)))
    surf.blit(s, (0, 0))
    _belly_wash(surf, P, w, h, 120)


def _marks_roan(surf, P, w, h, hb, rng, pose='sit'):
    """Half a coat. The pale hairs are scattered, and the mask is bare."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*P["belly"], 150),
                        (hb.centerx - hb.w * 0.42, hb.y + hb.h * 0.34,
                         hb.w * 0.84, hb.h * 0.68))
    surf.blit(s, (0, 0))
    for _ in range(260):
        x = rng.uniform(w * 0.10, w * 0.95)
        y = rng.uniform(h * 0.08, h * 0.97)
        g = pygame.Surface((2, max(2, round(h * rng.uniform(0.012, 0.03)))),
                           pygame.SRCALPHA)
        g.fill((*P["mark"], rng.randint(60, 170)))
        surf.blit(g, (round(x), round(y)))


def _marks_solid(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h, 95)


_MARKS = {"tabby": _marks_tabby, "blotched": _marks_blotched,
          "spotted": _marks_spotted, "ticked": _marks_ticked,
          "point": _marks_point, "gloves": _marks_gloves,
          "bicolour": _marks_bicolour, "tortie": _marks_tortie,
          "smoke": _marks_smoke, "roan": _marks_roan, "solid": _marks_solid}


# -- the face ---------------------------------------------------------------
def _eye(surf, P, cx, cy, rw, rh, colour, shut, shine=0.0):
    if shut:
        pygame.draw.arc(surf, shade(P["mark"], 0.8),
                        (cx - rw, cy - rh * 0.8, rw * 2, rh * 1.6),
                        3.5, 6.0, max(2, round(rh * 0.4)))
        return
    if P["eyeshape"] == "round":
        pygame.draw.ellipse(surf, (248, 240, 226),
                            (cx - rw, cy - rh, rw * 2, rh * 2))
        pygame.draw.ellipse(surf, colour,
                            (cx - rw * 0.94, cy - rh * 0.94,
                             rw * 1.88, rh * 1.88))
    else:
        pts = []
        for i in range(9):          # upper lid, lifted at the outer corner
            f = i / 8.0
            pts.append((cx - rw + rw * 2 * f,
                        cy - math.sin(f * math.pi) * rh * 0.95 - rh * 0.1 * f))
        for i in range(9):
            f = 1.0 - i / 8.0
            pts.append((cx - rw + rw * 2 * f,
                        cy + math.sin(f * math.pi) * rh * 0.78 - rh * 0.1 * f))
        pygame.draw.polygon(surf, colour, [(round(a), round(b))
                                           for a, b in pts])
    # a dim room means a wide pupil, which is most of what makes these read
    pr_w, pr_h = rw * 0.46, rh * 0.74
    pygame.draw.ellipse(surf, (18, 14, 16),
                        (cx - pr_w, cy - pr_h, pr_w * 2, pr_h * 2))
    pygame.draw.circle(surf, (252, 240, 216),
                       (round(cx - rw * 0.30), round(cy - rh * 0.36)),
                       max(1, round(rw * (0.17 + 0.09 * shine))))
    if shine > 0.5:                   # a second catchlight, from the lamp
        pygame.draw.circle(surf, (250, 234, 206),
                           (round(cx + rw * 0.34), round(cy + rh * 0.30)),
                           max(1, round(rw * 0.09)))


def _face(surf, P, w, h, hb, shut, pose="sit", shine=0.0):
    ew = hb.w * (0.19 + 0.03 * P["flat"])
    eh = hb.h * (0.15 if P["eyeshape"] == "round" else 0.12) * \
        (1.18 if P["ear"] > 1.4 else 1.0)
    ey = hb.y + hb.h * (0.50 if P["flat"] > 0.5 else 0.46)
    eye = P["eye"]
    cols = (eye[1], eye[2]) if eye[0] == "odd" else (eye, eye)
    for i, sx in enumerate((-1, 1)):
        _eye(surf, P, hb.centerx + sx * hb.w * 0.235, ey, ew, eh, cols[i],
             shut, shine)

    # ear insides, which an upright ear shows and a folded one does not.
    # Only on a sitting cat: a curled one wears its ears somewhere else
    # entirely, and drawing these there puts tufts in mid-air.
    if pose != "sit":
        pass
    elif P["fold"] >= 0.4:
        eh2 = hb.h * 0.62 * P["ear"]
        ew2 = hb.w * 0.34 * (0.8 + 0.3 * P["ear"])
        for sx in (-1, 1):
            bx = hb.centerx + sx * hb.w * 0.34
            by = hb.y + hb.h * 0.30
            pygame.draw.arc(surf, shade(P["coat"], 0.6),
                            (bx - ew2 * 0.72, by - eh2 * 0.40,
                             ew2 * 1.44, eh2 * 0.95), 3.4, 6.1, 2)
    if pose == "sit" and P["fold"] < 0.4:
        inner = mix(P["nose"], P["coat"], 0.35)
        eh2 = hb.h * 0.62 * P["ear"]
        ew2 = hb.w * 0.34 * (0.8 + 0.3 * P["ear"])
        for sx in (-1, 1):
            bx = hb.centerx + sx * hb.w * 0.34
            by = hb.y + hb.h * 0.30
            pygame.draw.polygon(surf, inner, [
                (round(bx - sx * ew2 * 0.36), round(by + eh2 * 0.12)),
                (round(bx + sx * ew2 * 0.30), round(by - eh2 * 0.60)),
                (round(bx + sx * ew2 * 0.52), round(by + eh2 * 0.04))])
            if P["tuft"] > 0.5:
                for k in range(3):
                    pygame.draw.line(surf, mix(P["belly"], CREAM, 0.3),
                                     (round(bx - sx * ew2 * 0.2 + k * sx * 3),
                                      round(by + eh2 * 0.05)),
                                     (round(bx + sx * ew2 * (0.3 + 0.1 * k)),
                                      round(by - eh2 * (0.5 + 0.12 * k))), 2)

    # nose, mouth, whiskers
    ny = hb.bottom - hb.h * (0.30 - 0.10 * P["flat"])
    nw = hb.w * 0.11
    pygame.draw.polygon(surf, P["nose"], [
        (round(hb.centerx - nw), round(ny - nw * 0.5)),
        (round(hb.centerx + nw), round(ny - nw * 0.5)),
        (round(hb.centerx), round(ny + nw * 0.7))])
    mc = shade(P["mark"], 0.75)
    for sx in (-1, 1):
        pygame.draw.arc(surf, mc,
                        (hb.centerx + (0 if sx < 0 else nw * 0.2) - nw * 1.2,
                         ny + nw * 0.3, nw * 2.2, nw * 1.8),
                        3.5 if sx < 0 else 3.0, 6.0 if sx < 0 else 5.6, 2)
    wh = pygame.Surface((w, h), pygame.SRCALPHA)
    for sx in (-1, 1):
        for k in range(3):
            y0 = ny + nw * (0.1 + k * 0.45)
            pygame.draw.line(wh, (*CREAM, int(100 + 80 * shine)),
                             (round(hb.centerx + sx * nw * 0.9), round(y0)),
                             (round(hb.centerx + sx * hb.w * (0.62 + 0.06 * k)),
                              round(y0 - hb.h * (0.10 - k * 0.07))), 1)
    surf.blit(wh, (0, 0))

    if P["skin"] > 0.4:              # a bald cat is mostly wrinkles
        a = int(70 + 60 * P["skin"])
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for k in range(3):
            pygame.draw.arc(s, (*shade(P["mark"], 0.8), a),
                            (hb.centerx - hb.w * (0.26 - 0.04 * k),
                             hb.y + hb.h * (0.10 + 0.07 * k),
                             hb.w * (0.52 - 0.08 * k), hb.h * 0.3),
                            0.5, 2.7, 2)
        for k in range(2):
            pygame.draw.arc(s, (*shade(P["mark"], 0.8), a),
                            (w * (0.36 - 0.03 * k), h * (0.50 + 0.06 * k),
                             w * (0.28 + 0.06 * k), h * 0.2), 0.4, 2.8, 2)
        surf.blit(s, (0, 0))

    if P["curl"] > 0.4:              # a rex coat, in little waves
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(7)
        for _ in range(60):
            x = rng.uniform(w * 0.18, w * 0.82)
            y = rng.uniform(h * 0.40, h * 0.92)
            r = w * 0.035
            pygame.draw.arc(s, (*shade(P["mark"], 1.25), 120),
                            (x - r, y - r, r * 2, r * 2), 0.3, 2.9, 2)
        surf.blit(s, (0, 0))


def _collar(surf, P, w, h, hb, pose, level, acc):
    """A collar at level 4, a tag at 7, and a bell when it retires.

    Worn rather than grown, so it is drawn on top of the finished cat
    and takes the card's rarity colour - which is the one thread tying
    the animal to the paper it comes on.
    """
    if level < COLLAR_AT:
        return
    # Leather first, rarity second. Taking the rarity colour straight
    # gave the uncommon breeds a green strap, which reads as a fish.
    col = mix(RUG, acc, 0.30)
    lip = mix(col, CREAM, 0.42)         # the light along the top of it
    if pose == "curl":
        bw = hb.w * 1.02
        br = pygame.Rect(hb.centerx - bw * 0.42, hb.bottom - hb.h * 0.26,
                         bw, hb.h * 0.55)
        tk = max(4, round(h * 0.05))
        pygame.draw.arc(surf, shade(col, 0.45), br.inflate(2, 2), 3.88, 5.62,
                        tk + 2)
        pygame.draw.arc(surf, col, br, 3.9, 5.6, tk)
        return
    # Low enough to be on the neck and not across the mouth, and
    # narrower than the skull, or it reads as a moustache.
    # A strap round a neck: wider than the part you can see, so its ends
    # pass behind the jowls instead of stopping in mid air, and drawn
    # across a shallow arc rather than a deep one.
    bw = hb.w * 1.02
    bh = h * 0.13
    cy = hb.bottom + h * 0.052
    br = pygame.Rect(hb.centerx - bw * 0.5, cy - bh * 0.5, bw, bh)
    thick = max(5, round(h * 0.055))
    pygame.draw.arc(surf, shade(col, 0.45), br.inflate(3, 3), 3.84, 5.60,
                    thick + 3)
    pygame.draw.arc(surf, col, br, 3.86, 5.58, thick)
    pygame.draw.arc(surf, lip, br.inflate(0, -max(2, thick - 2)), 3.98, 5.46,
                    max(2, thick // 3))
    bx = hb.centerx - bw * 0.20       # a brass buckle, off to one side
    by = cy + bh * 0.12
    pygame.draw.rect(surf, mix(LAMP, TEA, 0.4),
                     (round(bx), round(by), max(4, round(h * 0.035)),
                      max(4, round(h * 0.030))), border_radius=2)
    if level >= TAG_AT:
        tx, ty = hb.centerx, cy + bh * 0.48 + thick * 0.4
        r = max(4, round(h * 0.036))
        if level >= BELL_AT:
            pygame.draw.circle(surf, mix(LAMP, EMBER, 0.35), (round(tx),
                                                              round(ty)), r)
            pygame.draw.circle(surf, shade(EMBER, 0.65), (round(tx),
                                                          round(ty)), r, 1)
            pygame.draw.line(surf, shade(EMBER, 0.5), (tx - r * 0.6, ty + r * 0.3),
                             (tx + r * 0.6, ty + r * 0.3), 2)
            pygame.draw.circle(surf, mix(CREAM, LAMP, 0.4),
                               (round(tx - r * 0.3), round(ty - r * 0.35)),
                               max(1, r // 3))
        else:
            pygame.draw.circle(surf, mix(TEA, LAMP, 0.4), (round(tx),
                                                           round(ty)), r)
            pygame.draw.circle(surf, shade(TEA, 0.6), (round(tx), round(ty)),
                               r, 1)


# -- one finished cat -------------------------------------------------------
_cats = {}
CAT_RATIO = 0.95          # a sitting cat is this much wider than it is tall


def cat_surface(breed, pose="sit", height=140, shut=False, level=1):
    """A cat at a level, built once and cached. The room animates by
    blitting this; nothing below here knows what a card is."""
    level = int(clamp(level, 1, MAX_LEVEL))
    key = (breed.key, pose, int(height), shut, level)
    got = _cats.get(key)
    if got is not None:
        return got
    P = groom(breed.look, level)
    shine = (level - 1) / (MAX_LEVEL - 1)
    h = max(24, int(height * P["size"]))
    if pose == "curl":
        h = int(h * 0.66)
        w = int(h * 1.42)
    else:
        w = int(h * CAT_RATIO)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    sil = pygame.Surface((w, h), pygame.SRCALPHA)

    if pose == "curl":
        prims = _shapes_curl(P, w, h)
        hb = _head_box_curl(P, w, h)
        prims = prims + [("ellipse", hb)]
        ear = hb.h * 0.52 * P["ear"]
        for sx, lean in ((-1, -0.22), (1, 0.16)):   # both ears, both up
            bx = hb.centerx + sx * hb.w * 0.30
            by = hb.y + hb.h * 0.22
            if P["fold"] > 0.4:
                prims.append(("ellipse", (bx - hb.w * 0.26, by - ear * 0.34,
                                          hb.w * 0.52, ear * 0.86)))
            else:
                prims.append(("poly", [
                    (bx - hb.w * 0.20, by + ear * 0.20),
                    (bx + hb.w * 0.08 + lean * hb.w, by - ear),
                    (bx + hb.w * 0.26, by + ear * 0.10)]))
    else:
        prims = _shapes_sit(P, w, h) + _shapes_head(P, w, h)
        hb = _head_box(P, w, h)

    _paint(surf, prims, P["coat"])
    _paint(sil, prims, (255, 255, 255))

    # a fluffy cat is fluffy at the EDGE, so the bumps go on the silhouette
    if P["fluff"] > 0.45:
        rng = random.Random(breed.key + "fluff")
        rr0 = h * (0.030 + 0.030 * P["fluff"])
        if pose == "curl":
            spots = [(w * 0.5 + math.cos(a) * w * 0.43,
                      h * 0.62 + math.sin(a) * h * 0.33)
                     for a in (i / 26 * TAU for i in range(26))]
        else:
            left, right, _, _ = _bell(P, w, h)
            spots = [p for p in left[3:] + right[3:]]
            hb0 = _head_box(P, w, h)
            spots += [(hb0.centerx + math.cos(a) * hb0.w * 0.50,
                       hb0.centery + math.sin(a) * hb0.h * 0.52)
                      for a in (0.4 + i / 10 * math.pi for i in range(11))]
        for px, py in spots:
            rr = round(rr0 * rng.uniform(0.75, 1.3))
            pygame.draw.circle(surf, P["coat"], (round(px), round(py)), rr)
            pygame.draw.circle(sil, (255, 255, 255), (round(px), round(py)), rr)

    marks = pygame.Surface((w, h), pygame.SRCALPHA)
    _MARKS[P["pat"]](marks, P, w, h, hb, random.Random(breed.key), pose)
    marks.blit(sil, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(marks, (0, 0))

    # the lamp is up and to the left of every cat in this game
    gradient = pygame.Surface((w, h))
    for y in range(h):
        f = y / max(1, h - 1)
        k = (1.14 + 0.10 * shine) - (0.46 - 0.06 * shine) * f
        pygame.draw.line(gradient, shade((255, 250, 242), k), (0, y), (w, y))
    surf.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Where one part of the cat lies in front of another, nothing in the
    # silhouette says so - it is all one colour. These are the creases a
    # person reads as legs, a chest and a chin.
    if pose == "sit":
        cr = pygame.Surface((w, h), pygame.SRCALPHA)
        dark = (*shade(P["coat"], 0.52), 92)
        lw2 = w * 0.125
        for sx in (-1, 1):           # the front legs catch the lamp
            lx = w * 0.5 + sx * w * 0.115 * P["body"] - lw2 * 0.5
            pygame.draw.ellipse(cr, (*CREAM, 26),
                                (lx, h * 0.68, lw2, h * 0.25))
        pygame.draw.line(cr, dark, (round(w * 0.5), round(h * 0.70)),
                         (round(w * 0.5), round(h * 0.90)),
                         max(2, round(w * 0.016)))
        for sx in (-1, 1):
            lx = w * 0.5 + sx * w * 0.115 * P["body"] + sx * w * 0.068
            pygame.draw.line(cr, dark, (round(lx), round(h * 0.70)),
                             (round(lx - sx * w * 0.012), round(h * 0.89)), 2)
        pygame.draw.arc(cr, (*shade(P["coat"], 0.55), 80),
                        (w * 0.5 - hb.w * 0.52, hb.bottom - hb.h * 0.30,
                         hb.w * 1.04, hb.h * 0.62), 3.5, 6.0,
                        max(2, round(h * 0.012)))
        surf.blit(cr, (0, 0))

    # An outline is what lets a dark cat read against a dark room.
    try:
        pts = pygame.mask.from_surface(sil).outline(2)
    except (ValueError, AttributeError):
        pts = []
    if len(pts) > 6:
        pygame.draw.lines(surf, mix(shade(P["coat"], 0.42), LAMP, 0.22 * shine),
                          True, pts, 2)

    if shine > 0.05 and pose == "sit":
        gl = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(gl, (*CREAM, int(10 + 26 * shine)),
                            (hb.x + hb.w * 0.12, hb.y - h * 0.01,
                             hb.w * 0.76, hb.h * 0.42))
        pygame.draw.ellipse(gl, (*CREAM, int(8 + 20 * shine)),
                            (w * 0.30, h * 0.46, w * 0.40, h * 0.16))
        gl.blit(sil, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(gl, (0, 0))
    if P.get("bib") and pose == "sit":
        bb = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(bb, (*mix(P["belly"], CREAM, 0.35), 120),
                            (w * 0.38, h * 0.50, w * 0.24, h * 0.22))
        bb.blit(sil, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(bb, (0, 0))

    _face(surf, P, w, h, hb, shut or pose == "curl", pose, shine)
    _collar(surf, P, w, h, hb, pose, level, rarity_colour(breed.rarity))
    _cats[key] = surf
    return surf


# ---------------------------------------------------------------------------
# WHAT A DUPLICATE IS WORTH
#
# Two of a breed take its card from level 1 to level 2. Four more take it
# to 3, six to 4, and so on: the step is always twice the level you are
# leaving. Ninety duplicates is a finished card, and a finished card is
# RETIRED - the shop will never send that breed again, which is the whole
# late game. Every pack you open after that is aimed at what is left.
# ---------------------------------------------------------------------------
def dupes_for(level):
    """Duplicates needed to leave `level`. 0 at the top, where it stops."""
    return 0 if level >= MAX_LEVEL else 2 * level


DUPES_TO_MAX = sum(2 * lv for lv in range(1, MAX_LEVEL))      # 90
CARDS_TO_MAX = DUPES_TO_MAX + 1                               # with the first


class Card:
    """One breed in your binder: what level it is and how far into the next."""
    __slots__ = ("level", "dupes", "pulled")

    def __init__(self, level=1, dupes=0, pulled=1):
        self.level = level
        self.dupes = dupes
        self.pulled = pulled

    @property
    def maxed(self):
        return self.level >= MAX_LEVEL

    @property
    def need(self):
        return dupes_for(self.level)

    def add_dupe(self):
        """Take one duplicate. Returns the new level, or 0 for no change."""
        self.pulled += 1
        if self.maxed:
            return 0
        self.dupes += 1
        levelled = 0
        while not self.maxed and self.dupes >= self.need:
            self.dupes -= self.need
            self.level += 1
            levelled = self.level
        if self.maxed:
            self.dupes = 0
        return levelled


# ---------------------------------------------------------------------------
# THE SHOP
#
# Five things to buy. Each tier is a better deal per dollar AND a better
# deal per minute than the one below it, so the shop is a ladder and the
# only question it ever asks is what you can afford yet. The cheap ones
# are not traps; they are the rungs.
#
# The pacing is held by two things and not by price. First, four parcels
# is all the post will carry at once, so cards arrive at a rate the money
# cannot rush. Second, shipping: slow post is free and a cab costs nearly
# half the order again, which is where a late collection full of money
# puts it. Both are measured in `cat_test.py value`.
# ---------------------------------------------------------------------------
class Pack:
    __slots__ = ("key", "name", "price", "cards", "weights", "ship",
                 "floor", "blurb", "reviews")

    def __init__(self, key, name, price, cards, weights, ship, floor,
                 blurb, reviews):
        self.key = key
        self.name = name
        self.price = price
        self.cards = cards
        self.weights = weights
        self.ship = ship            # seconds, by standard post
        self.floor = floor          # the last card is at least this rarity
        self.blurb = blurb
        self.reviews = reviews


PACKS = (
    Pack("sack", "Paper Sack of Strays", 10, 2, (86, 13, 1, 0, 0), 25,
         R_COMMON,
         "Two cards in a paper sack, folded over twice and stapled. "
         "Mostly the cats you could meet on the way to the shop.",
         (("vastly better than the bin it came from", 4),
          ("one was damp. still a cat.", 3))),
    Pack("box", "Shelf Box", 25, 3, (56, 33, 10, 1, 0), 55,
         R_COMMON,
         "Three cards in a proper box with a window in the lid. The kind "
         "of thing a corner shop keeps by the till.",
         (("the lid window is a nice touch", 5),
          ("got a Russian Blue first go. no notes.", 5),
          ("three commons. the dice do what they like.", 3))),
    Pack("case", "Pedigree Case", 85, 5, (30, 38, 24, 7, 1), 90,
         R_UNCOMMON,
         "Five cards in a hinged case with a felt tray, and a guarantee "
         "printed inside the lid: nothing in here is quite ordinary.",
         (("the felt smells like a library", 5),
          ("bought six. opened six. no regrets, slight debt.", 4))),
    Pack("crate", "Breeders Crate", 250, 9, (10, 32, 36, 18, 4), 140,
         R_RARE,
         "Nine cards, wood wool, and a crowbar you are expected to own. "
         "One card in here is rare or better. It says so on the lid.",
         (("arrived with actual straw in it", 5),
          ("my Bengal came out of one of these", 5),
          ("the crowbar is not included, which they do say", 4))),
    Pack("lot", "The Estate Lot", 600, 15, (0, 17, 38, 33, 12), 200,
         R_PEDIGREE,
         "Fifteen cards from a collection being broken up. No commons at "
         "all, and the last card is pedigree or legend. Sold as seen.",
         (("the whole binder in four orders. rude.", 5),
          ("Khao Manee. I had to sit down.", 5),
          ("expensive. correct, but expensive.", 4))),
)
BY_PACK = {p.key: p for p in PACKS}

# Shipping. The cheap one is slow and the fast one is a luxury, which is
# the only decision the shop ever asks you to make.
SHIPPING = (
    ("post", "Standard post", 0.00, 1.00, "it gets there when it gets there"),
    ("track", "Tracked courier", 0.12, 0.60, "a van, and a number to watch"),
    ("cab", "Same-hour cab", 0.45, 0.33, "someone drives it over now"),
)
MAX_IN_TRANSIT = 4

# The post will carry four parcels at a time, and no amount of money
# changes that - which is why a late collection ends up with more of it
# than it can spend. The one thing the shop sells that lifts the ceiling
# is its delivery club: three one-off memberships, each worth a parcel.
# Without it the last half hour is four slow parcels and a bank balance.
CLUB = (
    (2500, "The Doorstep Club",
     "A fifth parcel on the round, and a card at Christmas."),
    (12000, "Keyholder",
     "A sixth. The courier has your key and uses it quietly."),
    (45000, "Round the Back",
     "A seventh, left round the back under the mat you keep there."),
)


def ship_cost(pack, qty, mode):
    return round(pack.price * qty * SHIPPING[mode][2], 2)


BULK = 5                    # the most of one thing the shop will send at once


def ship_time(pack, mode, qty=1):
    """A bigger order takes proportionally longer to pack and post.

    Ordering five at once is a standing order, not a shortcut: it saves
    clicks and lets you walk away, and it is slightly SLOWER per card
    than four separate parcels, because four parcels is all the post
    will carry at a time either way.
    """
    return pack.ship * SHIPPING[mode][3] * (1.0 + 0.85 * (qty - 1))


# ---------------------------------------------------------------------------
# THE RUN
# ---------------------------------------------------------------------------
SAVE_NAME = "catalogue.json"
OFFLINE_CAP = 2 * 3600          # the most the cats will earn while away
START_MONEY = 10.0              # exactly one Paper Sack, which is the point


def _save_dir():
    """Never beside the game, which may sit in a read-only folder."""
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(root, "CatCatalogue")
    elif sys.platform == "darwin":
        d = os.path.expanduser("~/Library/Application Support/CatCatalogue")
    else:
        root = (os.environ.get("XDG_DATA_HOME")
                or os.path.expanduser("~/.local/share"))
        d = os.path.join(root, "cat-catalogue")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except OSError:
        return os.path.dirname(os.path.abspath(__file__))


class Order:
    __slots__ = ("num", "pack", "qty", "left", "paid", "mode")

    def __init__(self, num, pack, qty, left, paid, mode):
        self.num = num
        self.pack = pack            # a key, not a Pack - it has to serialise
        self.qty = qty
        self.left = left            # seconds until it lands on the mat
        self.paid = paid
        self.mode = mode

    @property
    def total(self):
        return ship_time(BY_PACK[self.pack], self.mode, self.qty)

    def stage(self):
        """What the tracking page says, which is four lies and an arrival."""
        f = 1.0 - clamp(self.left / max(0.001, self.total), 0.0, 1.0)
        if f < 0.22:
            return 0, "picked and packed"
        if f < 0.48:
            return 1, "collected from the depot"
        if f < 0.80:
            return 2, "out for delivery"
        return 3, "on your street"


class Pull:
    """One card out of one parcel, and what it did to the binder.

    kind is "new" for a breed you did not have, "dupe" for one that moved
    its card along, "level" for one that finished a level, and "maxed" for
    a copy of something already retired - which the shop only sends by
    accident, and only at the very end.
    """
    __slots__ = ("breed", "kind", "level", "before", "sub")

    def __init__(self, breed, kind, level, before, sub=False):
        self.breed = breed
        self.kind = kind
        self.level = level
        self.before = before
        self.sub = sub


class State:
    """Everything the game is, and the only thing that is written to disk."""

    def __init__(self):
        self.money = START_MONEY
        self.cards = {}             # breed key -> Card
        self.orders = []            # Order, in transit
        self.parcels = []           # (pack key, qty) waiting on the mat
        self.next_num = 1041        # order numbers start somewhere plausible
        self.earned = 0.0
        self.spent = 0.0
        self.packs_opened = 0
        self.cards_pulled = 0
        self.played = 0.0
        self.first_run = True
        self.music = True
        self.sound = True
        self.seen_end = False
        self.club = 0               # memberships bought, 0 to 3
        self.area = "study"         # the room you were last standing in
        self.away = 0.0             # what the cats earned while you were out

    # -- the numbers --------------------------------------------------------
    @property
    def income(self):
        return sum(BY_KEY[k].rate_at(c.level) for k, c in self.cards.items())

    @property
    def owned(self):
        return len(self.cards)

    @property
    def slots(self):
        """How many parcels may be in the post at once."""
        return MAX_IN_TRANSIT + self.club

    @property
    def retired(self):
        return sum(1 for c in self.cards.values() if c.maxed)

    @property
    def complete(self):
        return self.retired >= len(BREEDS)

    def can_hold(self, key):
        """A breed the shop may still send: one you have not finished."""
        c = self.cards.get(key)
        return c is None or not c.maxed

    def live_rarities(self):
        return {b.rarity for b in BREEDS if self.can_hold(b.key)}

    def sellable(self, pack):
        """Whether the website will still take an order for this.

        A pack is withdrawn when nothing it advertises is left to send -
        once the last legend and the last pedigree have retired, there is
        no Estate Lot to sell, and the catalogue says so. It is the whole
        shape of the last hour: the shop empties from the top down, and
        the final cards come out of a paper sack, which is where the
        first ones came from.
        """
        live = self.live_rarities()
        return any(pack.weights[r] > 0 for r in live)

    def missing(self, rarity):
        """Cards still owed at this rarity before every breed in it retires."""
        n = 0
        for b in BY_RARITY[rarity]:
            c = self.cards.get(b.key)
            if c is None:
                n += CARDS_TO_MAX
            elif not c.maxed:
                done = sum(2 * lv for lv in range(1, c.level)) + c.dupes
                n += DUPES_TO_MAX - done
        return n

    def tick(self, dt):
        gain = self.income * dt
        self.money += gain
        self.earned += gain
        self.played += dt
        landed = []
        for o in list(self.orders):
            o.left -= dt
            if o.left <= 0:
                self.orders.remove(o)
                self.parcels.append((o.pack, o.qty))
                landed.append(o)
        return landed

    # -- buying -------------------------------------------------------------
    def order(self, pack, qty, mode):
        cost = pack.price * qty + ship_cost(pack, qty, mode)
        if (cost > self.money + 1e-6 or len(self.orders) >= self.slots
                or not self.sellable(pack)):
            return None
        self.money -= cost
        self.spent += cost
        o = Order(self.next_num, pack.key, qty,
                  ship_time(pack, mode, qty), cost, mode)
        self.next_num += 1
        self.orders.append(o)
        return o

    def join_club(self):
        """Buy the next membership, if there is one and it is affordable."""
        if self.club >= len(CLUB):
            return False
        price = CLUB[self.club][0]
        if price > self.money + 1e-6:
            return False
        self.money -= price
        self.spent += price
        self.club += 1
        return True

    # -- opening ------------------------------------------------------------
    def roll(self, pack, rng, last=False):
        """One card, and whether the shop had to substitute for it.

        Retired breeds are out of the catalogue, so their weight goes to
        whatever is still being sold. If a parcel is already in the post
        when the last breed it advertised retires, the shop substitutes
        from further down the list rather than sending an empty box -
        which is why the opening screen can say SUBSTITUTED on a card.
        """
        live = self.live_rarities()
        if not live:
            return None, False
        weights = list(pack.weights)
        if last:
            for r in range(pack.floor):
                weights[r] = 0
        pool = [(r, weights[r]) for r in range(5)
                if r in live and weights[r] > 0]
        sub = False
        if not pool:
            pool = [(r, 1) for r in sorted(live)]
            sub = True
        total = sum(wt for _, wt in pool)
        pick = rng.uniform(0, total)
        rarity = pool[-1][0]
        acc = 0.0
        for r, wt in pool:
            acc += wt
            if pick <= acc:
                rarity = r
                break
        choices = [b for b in BY_RARITY[rarity] if self.can_hold(b.key)]
        return rng.choice(choices), sub

    def open_pack(self, pack, qty, rng):
        """Returns one Pull per card in the parcel."""
        out = []
        for n in range(qty):
            for i in range(pack.cards):
                b, sub = self.roll(pack, rng, last=(i == pack.cards - 1))
                if b is None:
                    break
                card = self.cards.get(b.key)
                if card is None:
                    self.cards[b.key] = Card()
                    out.append(Pull(b, "new", 1, 0, sub))
                else:
                    before = card.level
                    lv = card.add_dupe()
                    out.append(Pull(b, "level" if lv else "dupe", card.level,
                                    before, sub))
                self.cards_pulled += 1
            self.packs_opened += 1
        return out

    # -- disk ---------------------------------------------------------------
    def to_dict(self):
        return {
            "v": 1,
            "money": round(self.money, 4),
            "cards": {k: [c.level, c.dupes, c.pulled]
                      for k, c in self.cards.items()},
            "orders": [[o.num, o.pack, o.qty, round(o.left, 2), o.paid, o.mode]
                       for o in self.orders],
            "parcels": [[p, q] for p, q in self.parcels],
            "next_num": self.next_num,
            "earned": round(self.earned, 3),
            "spent": round(self.spent, 3),
            "packs_opened": self.packs_opened,
            "cards_pulled": self.cards_pulled,
            "played": round(self.played, 1),
            "music": self.music,
            "sound": self.sound,
            "seen_end": self.seen_end,
            "club": self.club,
            "area": self.area,
            "stamp": time.time(),
        }

    @classmethod
    def from_dict(cls, d):
        s = cls()
        s.first_run = False
        s.money = float(d.get("money", START_MONEY))
        for k, v in (d.get("cards") or {}).items():
            if k in BY_KEY:
                s.cards[k] = Card(int(clamp(int(v[0]), 1, MAX_LEVEL)),
                                  max(0, int(v[1])), max(1, int(v[2])))
        for row in (d.get("orders") or []):
            if row[1] in BY_PACK:
                s.orders.append(Order(int(row[0]), row[1], int(row[2]),
                                      float(row[3]), float(row[4]),
                                      int(clamp(int(row[5]), 0, 2))))
        for row in (d.get("parcels") or []):
            if row[0] in BY_PACK:
                s.parcels.append((row[0], int(row[1])))
        s.next_num = int(d.get("next_num", 1041))
        s.earned = float(d.get("earned", 0))
        s.spent = float(d.get("spent", 0))
        s.packs_opened = int(d.get("packs_opened", 0))
        s.cards_pulled = int(d.get("cards_pulled", 0))
        s.played = float(d.get("played", 0))
        s.music = bool(d.get("music", True))
        s.sound = bool(d.get("sound", True))
        s.seen_end = bool(d.get("seen_end", False))
        s.club = int(clamp(int(d.get("club", 0)), 0, len(CLUB)))
        s.area = d.get("area") if d.get("area") in AREAS else "study"

        # What happened while the game was shut. The cats went on earning,
        # capped at two hours, and the post went on being delivered - which
        # is not capped, because a parcel that is three days late is worse
        # than useless.
        gap = max(0.0, time.time() - float(d.get("stamp", time.time())))
        if gap > 1.0:
            paid = min(gap, OFFLINE_CAP)
            s.away = s.income * paid
            s.money += s.away
            s.earned += s.away
            for o in list(s.orders):
                o.left -= gap
                if o.left <= 0:
                    s.orders.remove(o)
                    s.parcels.append((o.pack, o.qty))
        return s


def load_state():
    try:
        with open(os.path.join(_save_dir(), SAVE_NAME), encoding="utf-8") as fh:
            return State.from_dict(json.load(fh))
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AttributeError):
        return State()


def save_state(state):
    try:
        path = os.path.join(_save_dir(), SAVE_NAME)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh)
        os.replace(tmp, path)       # a half-written save is a lost collection
    except OSError:
        pass


# ---------------------------------------------------------------------------
# SOUND
#
# There are no audio files. Nine sounds and one piece of music, built out
# of arithmetic the first time they are asked for, at a sample rate low
# enough that building them is not something you notice.
#
# Everything here is soft on purpose: the loudest thing in the game is a
# doorbell, and even that is two sine waves and a long tail.
# ---------------------------------------------------------------------------
RATE = 22050
_sounds = {}
_audio = False


def _env(i, n, attack=0.01, release=0.5):
    """Attack and release as a fraction of the note, never clicking."""
    a = max(1, int(n * attack))
    r = max(1, int(n * release))
    if i < a:
        return i / a
    if i > n - r:
        return max(0.0, (n - i) / r)
    return 1.0


def _mix(buf, start, samples, gain=1.0):
    n = len(buf)
    for i, v in enumerate(samples):
        j = start + i
        buf[j % n] += v * gain          # the tail wraps, so the loop seams


def _note(freq, dur, voice="soft", vol=0.5, attack=0.02, release=0.6):
    """One note. `voice` is how much of the harmonic series comes with it."""
    n = int(dur * RATE)
    out = [0.0] * n
    w = TAU * freq / RATE
    for i in range(n):
        e = _env(i, n, attack, release)
        p = w * i
        if voice == "soft":             # a stopped flute, near enough
            s = math.sin(p) + 0.22 * math.sin(p * 2) + 0.06 * math.sin(p * 3)
        elif voice == "bell":
            s = (math.sin(p) + 0.5 * math.sin(p * 2.76) +
                 0.25 * math.sin(p * 5.4))
            e *= math.exp(-3.2 * i / n)
        elif voice == "string":
            s = math.sin(p) + 0.3 * math.sin(p * 2) + 0.15 * math.sin(p * 4)
            e *= 0.8 + 0.2 * math.sin(TAU * 4.5 * i / RATE)
        else:                           # "low" - the bass, almost pure
            s = math.sin(p) + 0.12 * math.sin(p * 2)
        out[i] = s * e * vol
    return out


def _noise(dur, vol=0.3, lo=0.2, decay=3.0, seed=1):
    rng = random.Random(seed)
    n = int(dur * RATE)
    out = [0.0] * n
    last = 0.0
    for i in range(n):
        v = rng.uniform(-1, 1)
        last = last * lo + v * (1 - lo)          # a dull filter, for paper
        out[i] = last * math.exp(-decay * i / n) * vol
    return out


def _to_sound(samples, gain=1.0):
    peak = max(0.001, max(abs(v) for v in samples))
    k = min(1.0, 0.92 / peak) * gain
    data = array("h", (int(clamp(v * k, -1, 1) * 32000) for v in samples))
    snd = pygame.mixer.Sound(buffer=data.tobytes())
    return snd


def _build_sound(name):
    if name == "click":
        s = _note(880, 0.05, "soft", 0.3, 0.01, 0.9)
        return _to_sound(s, 0.35)
    if name == "page":
        return _to_sound(_noise(0.20, 0.5, 0.45, 4.0, 3), 0.5)
    if name == "tape":
        s = _noise(0.55, 0.6, 0.72, 1.4, 7)
        for i in range(len(s)):           # a rip wobbles as it goes
            s[i] *= 0.6 + 0.4 * math.sin(TAU * 11 * i / RATE)
        return _to_sound(s, 0.55)
    if name == "flip":
        return _to_sound(_noise(0.13, 0.5, 0.3, 9.0, 11), 0.45)
    if name == "coin":
        s = _note(1320, 0.10, "bell", 0.4)
        s += _note(1760, 0.14, "bell", 0.3)
        return _to_sound(s, 0.30)
    if name == "bell":                    # the door, two notes and a wait
        s = _note(660, 0.9, "bell", 0.6)
        s2 = _note(528, 1.5, "bell", 0.6)
        out = s + [0.0] * int(1.1 * RATE)
        for i, v in enumerate(s2):
            j = int(0.42 * RATE) + i
            if j < len(out):
                out[j] += v
        return _to_sound(out, 0.6)
    if name == "level":
        out = []
        for f in (523.25, 659.25, 783.99):
            out += _note(f, 0.16, "soft", 0.5, 0.01, 0.7)
        return _to_sound(out, 0.45)
    if name == "new":                     # a new breed: four notes, warm
        out = []
        for f in (392.0, 523.25, 659.25, 783.99):
            out += _note(f, 0.17, "soft", 0.5, 0.02, 0.6)
        return _to_sound(out, 0.5)
    if name == "legend":
        base = _note(523.25, 1.5, "bell", 0.5)
        for f, d in ((659.25, 0.12), (783.99, 0.24), (1046.5, 0.36)):
            part = _note(f, 1.2, "bell", 0.35)
            for i, v in enumerate(part):
                j = int(d * RATE) + i
                if j < len(base):
                    base[j] += v
        return _to_sound(base, 0.55)
    if name == "purr":
        n = int(1.4 * RATE)
        out = [0.0] * n
        for i in range(n):
            t = i / RATE
            amp = 0.5 + 0.5 * math.sin(TAU * 24 * t)
            out[i] = (math.sin(TAU * 42 * t) * 0.6 +
                      math.sin(TAU * 63 * t) * 0.2) * amp * _env(i, n, .2, .3)
        return _to_sound(out, 0.3)
    if name == "step":                    # one floorboard, once
        s = _note(96, 0.12, "low", 0.5, 0.004, 0.85)
        for i, v in enumerate(_noise(0.09, 0.3, 0.55, 9.0, 13)):
            s[i] += v
        return _to_sound(s, 0.32)
    if name == "thud":                    # a parcel landing on the mat
        s = _note(74, 0.30, "low", 0.8, 0.005, 0.9)
        for i, v in enumerate(_noise(0.18, 0.5, 0.6, 7.0, 5)):
            s[i] += v
        return _to_sound(s, 0.6)
    return None


def sound(name):
    if not _audio:
        return None
    s = _sounds.get(name)
    if s is None:
        try:
            s = _build_sound(name)
        except (pygame.error, ValueError, MemoryError):
            s = False
        _sounds[name] = s
    return s or None


def play(name, vol=1.0):
    s = sound(name)
    if s is not None:
        s.set_volume(vol)
        s.play()


# -- the music --------------------------------------------------------------
# One loop, twenty seconds, four chords that do not resolve. It is the
# sound of a room with the big light off; it is not supposed to be
# noticed. The last chord's tail wraps round onto the start of the buffer
# (see `_mix`), so the loop has no gap in it - the usual way a generated
# loop goes wrong is a quarter second of silence at the seam.
MUSIC_BARS = ((0, (220.00, 261.63, 329.63)),      # Am
              (1, (174.61, 220.00, 261.63)),      # F
              (2, (196.00, 246.94, 293.66)),      # G
              (3, (164.81, 196.00, 246.94)))      # Em
_music = None


def music_loop():
    global _music
    if _music is not None or not _audio:
        return _music
    bar = 5.0
    n = int(bar * len(MUSIC_BARS) * RATE)
    buf = [0.0] * n
    cache = {}
    for idx, chord in MUSIC_BARS:
        at = int(idx * bar * RATE)
        for v, f in enumerate(chord):
            key = (round(f, 2), "string")
            note = cache.get(key)
            if note is None:
                note = _note(f, bar * 1.7, "string", 0.30, 0.16, 0.42)
                cache[key] = note
            _mix(buf, at + int(v * 0.07 * RATE), note, 0.55)
        low = cache.get((chord[0] / 2, "low"))
        if low is None:
            low = _note(chord[0] / 2, bar * 1.25, "low", 0.5, 0.08, 0.5)
            cache[(chord[0] / 2, "low")] = low
        _mix(buf, at, low, 0.5)
        # one high note per bar, off the beat, like a clock in another room
        hi = _note(chord[-1] * 2, 1.1, "bell", 0.22, 0.01, 0.9)
        _mix(buf, at + int(bar * 0.62 * RATE), hi, 0.5)
    try:
        _music = _to_sound(buf, 0.42)
    except (pygame.error, ValueError, MemoryError):
        _music = False
    return _music or None


_music_on = False


def music(on):
    """Start or stop the loop. Called when the setting changes, not often."""
    global _music_on
    m = music_loop()
    if m is None:
        return
    if on and not _music_on:
        m.play(loops=-1)
        _music_on = True
    elif not on and _music_on:
        m.stop()
        _music_on = False


def init_audio():
    global _audio
    try:
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.mixer.init()
        _audio = True
    except pygame.error:
        _audio = False
    return _audio


# ---------------------------------------------------------------------------
# A CARD
#
# Paper, a window with a cat in it, and a rule along the bottom. The
# rarity is in the border and in one word, never in the paper, because a
# binder of twenty-four differently coloured cards looks like a toy and
# this is meant to look like something you would keep.
# ---------------------------------------------------------------------------
def _corner_ticks(surf, r, col, inset, length, wide=2):
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x = r.centerx + sx * (r.w // 2 - inset)
        y = r.centery + sy * (r.h // 2 - inset)
        pygame.draw.line(surf, col, (x, y), (x - sx * length, y), wide)
        pygame.draw.line(surf, col, (x, y), (x, y - sy * length), wide)


def _card_frame(surf, rect, inner, acc, stock, grade, maxed):
    """What the card is PRINTED on, which is the part that climbs.

    Grade 0 is a plain rule on plain stock. By grade 4 it has a foil
    frame, bracketed corners and a banner, and the whole thing is warm.
    The ornaments are all gated on the card being big enough to carry
    them: the binder is drawn at 117px wide and a flourish at that size
    is a smudge.
    """
    big = rect.w >= 108
    line = mix(stock, acc, 0.35 + 0.10 * grade)
    pygame.draw.rect(surf, line, inner, width=2, border_radius=5)

    if grade >= 1:                      # a second rule, and corner ticks
        pygame.draw.rect(surf, mix(stock, acc, 0.22), inner.inflate(-7, -7),
                         width=1, border_radius=4)
        if big:
            _corner_ticks(surf, inner, mix(stock, acc, 0.45), 2, 9)
    if grade >= 2 and big:              # foil corners
        foil = mix(acc, LAMP, 0.35)
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = inner.centerx + sx * inner.w // 2
            y = inner.centery + sy * inner.h // 2
            pygame.draw.polygon(surf, foil, [
                (x, y), (x - sx * 15, y), (x, y - sy * 15)])
    if grade >= 3 and big:              # brackets, and a line of guilloche
        br = mix(acc, INK, 0.35)
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = inner.centerx + sx * (inner.w // 2 - 6)
            y = inner.centery + sy * (inner.h // 2 - 6)
            pygame.draw.lines(surf, br, False,
                              [(x - sx * 16, y), (x, y), (x, y - sy * 16)], 2)
        for i in range(5):
            cx = rect.centerx - 34 + i * 17
            pygame.draw.arc(surf, mix(stock, acc, 0.5),
                            (cx - 9, rect.bottom - 26, 18, 14), 3.4, 6.1, 1)
    if maxed:                           # the retired frame, in foil
        gold = mix(LAMP, acc, 0.35)
        pygame.draw.rect(surf, gold, rect, width=3, border_radius=7)
        pygame.draw.rect(surf, mix(gold, stock, 0.45), rect.inflate(-7, -7),
                         width=1, border_radius=6)
        if big:
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                x = rect.centerx + sx * (rect.w // 2 - 7)
                y = rect.centery + sy * (rect.h // 2 - 7)
                pygame.draw.circle(surf, gold, (x, y), 4)
                pygame.draw.circle(surf, mix(gold, INK, 0.4), (x, y), 4, 1)


def card_cat_height(rect):
    return int(rect.h * 0.46)


def draw_card(surf, rect, breed, level=1, dupes=0, maxed=False, lit=1.0,
              show_rate=True, shut=False):
    rect = pygame.Rect(rect)
    acc = rarity_colour(breed.rarity)
    grade = 4 if maxed else grade_of(level)
    # better paper as it goes: a stray comes on card, a retired breed
    # comes on something you would frame
    stock = mix(PAPER, acc, 0.05 + 0.02 * grade)
    if grade >= 3:
        stock = mix(stock, LAMP, 0.05 + 0.05 * (grade - 3))
    panel(surf, rect, stock, None, radius=7)
    inner = rect.inflate(-10, -10)
    _card_frame(surf, rect, inner, acc, stock, grade, maxed)

    # Everything below the window is measured UP from the foot of the
    # card, so a small card in the binder and a big one in a parcel have
    # the same rows in the same order and nothing lands on anything else.
    # A card dealt out of a standing order of three Estate Lots is a
    # third the size of one in the binder, and at that size the rarity
    # and the rate print straight through each other. A small card drops
    # the rows it cannot hold rather than overlapping them.
    compact = rect.h < 150
    pip_y = rect.bottom - (8 if compact else 10)
    sub_y = pip_y - (0 if compact else 14)
    row_y = sub_y - (12 if compact else 13)
    name_y = row_y - (13 if compact else 16)

    # the window the cat sits in
    win = pygame.Rect(inner.x + 6, inner.y + 6, inner.w - 12,
                      max(30, name_y - 14 - (inner.y + 6)))
    pygame.draw.rect(surf, mix(acc, INK, 0.88 - 0.055 * grade), win,
                     border_radius=4)
    old = surf.get_clip()
    surf.set_clip(win)
    glow(surf, (win.centerx, win.centery + win.h * 0.10),
         int(win.w * (0.60 + 0.05 * grade)), mix(acc, LAMP, 0.55),
         (0.26 + 0.07 * grade) * lit)
    if grade >= 2:                 # a floor for it to sit on, not a void
        pygame.draw.ellipse(surf, mix(acc, INK, 0.62),
                            (win.x + win.w * 0.12, win.bottom - win.h * 0.20,
                             win.w * 0.76, win.h * 0.22))
    # never taller than the window it has to sit in, or the ears go
    img = cat_surface(breed, "sit",
                      min(card_cat_height(rect), win.h - 5), shut, level)
    surf.blit(img, img.get_rect(midbottom=(win.centerx, win.bottom - 4)))
    surf.set_clip(old)
    pygame.draw.rect(surf, mix(acc, INK if grade < 3 else LAMP,
                               0.45 if grade < 3 else 0.30), win, width=1,
                     border_radius=4)

    # The level, as a number, in the corner of the window. The pips along
    # the foot say the same thing, but counting ten dots is not reading,
    # and this is the one part of the card that moves on EVERY level and
    # not only at a grade.
    if rect.w >= 92:
        cw = int(clamp(rect.w * 0.21, 22, 32))
        chip = pygame.Rect(win.x + 4, win.y + 4, cw, int(cw * 0.64))
        face = (mix(LAMP, acc, 0.4) if maxed else
                mix(acc, PAPER, 0.25 + 0.12 * grade))
        pygame.draw.rect(surf, mix(face, INK, 0.25), chip.move(1, 1),
                         border_radius=4)
        pygame.draw.rect(surf, face, chip, border_radius=4)
        pygame.draw.rect(surf, mix(face, CREAM, 0.4), chip, width=1,
                         border_radius=4)
        text(surf, str(level), min(15, chip.h - 3), chip.center,
             mix(INK, acc, 0.15), center=True, kind="mono", bold=True,
             shadow=False)

    # name, rarity, and what it earns
    if grade >= 3 and rect.w >= 108:
        plate = pygame.Rect(inner.x + 10, name_y - 1, inner.w - 20, 19)
        pygame.draw.rect(surf, mix(stock, acc, 0.16), plate, border_radius=4)
        pygame.draw.rect(surf, mix(stock, acc, 0.42), plate, width=1,
                         border_radius=4)
    text(surf, breed.name, fit(breed.name, 17, inner.w - 6),
         (rect.centerx, name_y + 8), mix(INK, acc, 0.22), center=True,
         shadow=False)
    hairline(surf, inner.x + 8, row_y - 3, inner.right - 8,
             mix(INK, acc, 0.5), 60)
    text(surf, rarity_name(breed.rarity), 11 if not compact else 9,
         (inner.x + 4, row_y + (2 if compact else 0)),
         mix(INK, acc, 0.45), kind="mono", shadow=False)
    if show_rate and not compact:
        text(surf, rate(breed.rate_at(level)), 11,
             (inner.right - 4, row_y + 6), mix(INK, acc, 0.3), right=True,
             kind="mono", shadow=False)

    if compact:
        pass
    elif maxed:
        ban = pygame.Rect(inner.x + 14, sub_y, inner.w - 28, 15)
        pygame.draw.rect(surf, mix(acc, LAMP, 0.42), ban, border_radius=3)
        pygame.draw.rect(surf, mix(acc, INK, 0.35), ban, width=1,
                         border_radius=3)
        text(surf, "RETIRED", 11, (rect.centerx, sub_y + 6),
             mix(INK, acc, 0.25), center=True, kind="mono", shadow=False)
    elif level < MAX_LEVEL:
        text(surf, f"{dupes} of {dupes_for(level)}", 11,
             (rect.centerx, sub_y + 6), mix(INK, acc, 0.4), center=True,
             kind="mono", shadow=False)

    # the level, as ten pips along the foot of the card
    pw = (inner.w - 8) / MAX_LEVEL
    for i in range(MAX_LEVEL):
        full = i < level
        c = (mix(LAMP, acc, 0.35) if maxed else
             (mix(acc, INK, 0.25) if full else mix(stock, INK, 0.28)))
        pygame.draw.circle(surf, c,
                           (int(inner.x + 4 + pw * (i + 0.5)), pip_y),
                           (2 if compact else 3) if full else 2)
    if compact and maxed:
        pygame.draw.rect(surf, mix(LAMP, acc, 0.4), rect, width=2,
                         border_radius=7)
    return rect


def draw_card_back(surf, rect, t=0.0):
    """The back of every card in the catalogue: a cat, asleep, in a ring."""
    rect = pygame.Rect(rect)
    panel(surf, rect, mix(WOOD, EMBER, 0.12), None, radius=7)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(surf, mix(WOOD_HI, LAMP, 0.18), inner, width=2,
                     border_radius=5)
    cx, cy = rect.center
    r = int(min(rect.w, rect.h) * 0.22)
    pygame.draw.circle(surf, mix(WOOD_HI, LAMP, 0.1), (cx, cy), r, 2)
    # a curled sleeping cat, drawn small enough to read as a mark
    pygame.draw.arc(surf, mix(PAPER, WOOD, 0.3),
                    (cx - r * 0.8, cy - r * 0.6, r * 1.6, r * 1.3),
                    0.3, 5.6, 4)
    pygame.draw.circle(surf, mix(PAPER, WOOD, 0.3),
                       (int(cx - r * 0.45), int(cy - r * 0.1)),
                       max(3, int(r * 0.30)))
    for sx in (-1, 1):
        pygame.draw.polygon(surf, mix(PAPER, WOOD, 0.3), [
            (int(cx - r * 0.45 + sx * r * 0.22), int(cy - r * 0.28)),
            (int(cx - r * 0.45 + sx * r * 0.30), int(cy - r * 0.52)),
            (int(cx - r * 0.45 + sx * r * 0.06), int(cy - r * 0.36))])
    text(surf, "CAT CATALOGUE", 10, (cx, rect.bottom - 18),
         mix(PAPER, WOOD, 0.45), center=True, kind="mono", shadow=False)
    return rect


def draw_unknown(surf, rect, hint=None):
    """An empty slot in the binder: the shape of a cat and nothing else."""
    rect = pygame.Rect(rect)
    panel(surf, rect, shade(DEEP, 1.15), shade(TEA, 0.35), radius=7)
    inner = rect.inflate(-10, -10)
    win = pygame.Rect(inner.x + 6, inner.y + 6, inner.w - 12,
                      int(inner.h * 0.58))
    pygame.draw.rect(surf, shade(INK, 1.3), win, border_radius=4)
    if hint is not None:
        img = cat_surface(hint, "sit", card_cat_height(rect), level=1)
        sil = img.copy()
        sil.fill(shade(DEEP, 1.6), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(sil, sil.get_rect(midbottom=(win.centerx, win.bottom - 4)))
    text(surf, "?", 30, win.center, shade(TEA, 0.5), center=True, shadow=False)
    text(surf, "not in the binder", 11, (rect.centerx, win.bottom + 16),
         shade(TEA, 0.55), center=True, kind="mono", shadow=False)
    return rect


# ---------------------------------------------------------------------------
# WHAT THE SHOP SENDS
# ---------------------------------------------------------------------------
def draw_pack_art(surf, rect, pack, t=0.0):
    """Five things, five shapes. The shop is a shape before it is a price."""
    rect = pygame.Rect(rect)
    k = pack.key
    acc = rarity_colour(min(4, pack.floor + 1))
    if k == "sack":
        body = pygame.Rect(rect.x + rect.w * 0.18, rect.y + rect.h * 0.22,
                           rect.w * 0.64, rect.h * 0.70)
        pygame.draw.rect(surf, (182, 152, 112), body, border_radius=3)
        pygame.draw.polygon(surf, (196, 166, 124), [
            (body.x, body.y), (body.right, body.y),
            (body.right - 6, body.y - rect.h * 0.12),
            (body.x + 6, body.y - rect.h * 0.12)])
        pygame.draw.line(surf, (146, 118, 86), (body.x + 4, body.y + 2),
                         (body.right - 4, body.y + 2), 2)
        for i in range(3):
            x = body.x + body.w * (0.3 + 0.2 * i)
            pygame.draw.line(surf, (150, 140, 148), (x, body.y - 4),
                             (x, body.y + 3), 3)
        pygame.draw.line(surf, (160, 132, 98), (body.centerx, body.y + 10),
                         (body.centerx, body.bottom - 8), 1)
    elif k == "box":
        body = pygame.Rect(rect.x + rect.w * 0.12, rect.y + rect.h * 0.30,
                           rect.w * 0.76, rect.h * 0.56)
        pygame.draw.rect(surf, (168, 124, 86), body, border_radius=3)
        pygame.draw.rect(surf, (190, 144, 100),
                         (body.x, body.y, body.w, body.h * 0.34),
                         border_radius=3)
        win = pygame.Rect(body.centerx - body.w * 0.22,
                          body.y + body.h * 0.08, body.w * 0.44,
                          body.h * 0.20)
        pygame.draw.rect(surf, mix(PAPER, acc, 0.2), win, border_radius=2)
        pygame.draw.rect(surf, (120, 86, 58), body, width=2, border_radius=3)
    elif k == "case":
        body = pygame.Rect(rect.x + rect.w * 0.10, rect.y + rect.h * 0.32,
                           rect.w * 0.80, rect.h * 0.50)
        pygame.draw.rect(surf, (74, 58, 72), body, border_radius=5)
        pygame.draw.rect(surf, (96, 76, 94),
                         (body.x, body.y, body.w, body.h * 0.46),
                         border_radius=5)
        pygame.draw.line(surf, (54, 42, 52), (body.x, body.centery),
                         (body.right, body.centery), 2)
        clasp = pygame.Rect(body.centerx - 9, body.centery - 7, 18, 14)
        pygame.draw.rect(surf, mix(LAMP, acc, 0.3), clasp, border_radius=3)
    elif k == "crate":
        body = pygame.Rect(rect.x + rect.w * 0.10, rect.y + rect.h * 0.28,
                           rect.w * 0.80, rect.h * 0.58)
        pygame.draw.rect(surf, (128, 92, 58), body, border_radius=2)
        for i in range(4):
            y = body.y + body.h * (0.12 + i * 0.25)
            pygame.draw.line(surf, (102, 72, 44), (body.x + 2, y),
                             (body.right - 2, y), 3)
        pygame.draw.line(surf, (102, 72, 44), (body.x + 3, body.y + 3),
                         (body.right - 3, body.bottom - 3), 3)
        pygame.draw.rect(surf, (92, 64, 40), body, width=2, border_radius=2)
    else:
        body = pygame.Rect(rect.x + rect.w * 0.07, rect.y + rect.h * 0.22,
                           rect.w * 0.86, rect.h * 0.66)
        pygame.draw.rect(surf, (156, 122, 86), body, border_radius=3)
        pygame.draw.rect(surf, (176, 140, 100),
                         (body.x, body.y, body.w, body.h * 0.26),
                         border_radius=3)
        pygame.draw.line(surf, (122, 96, 68), (body.centerx, body.y),
                         (body.centerx, body.bottom), 4)
        pygame.draw.line(surf, (122, 96, 68), (body.x, body.centery),
                         (body.right, body.centery), 4)
        lab = pygame.Rect(body.x + body.w * 0.14, body.centery - body.h * 0.10,
                          body.w * 0.34, body.h * 0.22)
        pygame.draw.rect(surf, mix(PAPER, acc, 0.15), lab, border_radius=2)
    return rect


def draw_parcel(surf, rect, seed=0, open_frac=0.0, num=0):
    """A box on the mat, and then a box with its lid cut open."""
    rect = pygame.Rect(rect)
    rng = random.Random(seed)
    board = (150, 114, 78)
    pygame.draw.rect(surf, board, rect, border_radius=4)
    pygame.draw.rect(surf, shade(board, 0.82), rect, width=2, border_radius=4)
    # the tape, down the middle and round the lid
    tape = mix(PAPER, board, 0.25)
    tw = max(6, rect.w // 12)
    lid = int(rect.h * 0.30)
    if open_frac <= 0.01:
        pygame.draw.rect(surf, tape,
                         (rect.centerx - tw // 2, rect.y, tw, rect.h))
        pygame.draw.line(surf, shade(board, 0.7), (rect.x, rect.y + lid),
                         (rect.right, rect.y + lid), 2)
    else:
        f = clamp(open_frac, 0, 1)
        flap = pygame.Rect(rect.x, rect.y + lid - int(lid * 1.6 * f),
                           rect.w, lid)
        pygame.draw.rect(surf, shade(INK, 1.6),
                         (rect.x + 3, rect.y + lid - 4, rect.w - 6, 10))
        pygame.draw.rect(surf, shade(board, 1.08), flap, border_radius=3)
        pygame.draw.rect(surf, shade(board, 0.8), flap, width=2,
                         border_radius=3)
    # the label, and a stamp in the corner
    lab = pygame.Rect(rect.x + rect.w * 0.12, rect.y + rect.h * 0.52,
                      rect.w * 0.52, rect.h * 0.30)
    pygame.draw.rect(surf, mix(PAPER, board, 0.18), lab, border_radius=2)
    for i in range(3):
        hairline(surf, lab.x + 5, lab.y + 7 + i * 7, lab.right - 6,
                 shade(INK, 2.0), 110)
    if num:
        text(surf, f"#{num}", 11, (lab.x + 5, lab.bottom - 14),
             shade(INK, 1.9), kind="mono", shadow=False)
    st = pygame.Rect(rect.right - rect.w * 0.26, rect.y + rect.h * 0.52,
                     rect.w * 0.17, rect.h * 0.20)
    pygame.draw.rect(surf, mix(EMBER, PAPER, 0.35), st)
    pygame.draw.rect(surf, shade(board, 0.7), st, width=1)
    return rect


# ---------------------------------------------------------------------------
# THE FLAT
#
# Three rooms side by side, and you walk between them. The hall is where
# the post lands, the desk is where the lamp and the laptop are, and the
# cat room is where the collection actually lives. Nothing here is a menu
# standing in for a place: a parcel is picked up in the hall because that
# is where the door is.
#
# Everything is a rectangle until the grade goes over it; what makes each
# one a room is where the light falls, and each has its own light - a bare
# pendant in the hall, the desk lamp, and a string of warm bulbs over the
# cat tree.
# ---------------------------------------------------------------------------
AREAS = ("hall", "study", "cats")
AREA_NAME = {"hall": "THE HALL", "study": "THE DESK", "cats": "THE CAT ROOM"}

# -- the desk ---------------------------------------------------------------
WALL_H = 400          # the desk surface starts here
DESK_FRONT = 452      # ... and its front edge is here
FLOOR_Y = 548

DESK_R = pygame.Rect(0, WALL_H, W, DESK_FRONT - WALL_H)
LAPTOP_R = pygame.Rect(286, 214, 288, 238)
BINDER_R = pygame.Rect(680, 352, 214, 92)

# -- the hall ---------------------------------------------------------------
HALL_FLOOR = 524
DOOR_R = pygame.Rect(424, 104, 318, 462)
MAT_R = pygame.Rect(410, 568, 346, 104)

# -- the cat room -----------------------------------------------------------
CATS_FLOOR = 556
TREE_X = 790

# Where a cat may be, best spot first: the top of the cat tree is a better
# address than the floor by the bowls, and the cats you have taken
# furthest get first refusal.
SPOTS = (
    ("study", 1022, 452, "sit", 150),     # the desk, beside the binder
    ("cats", TREE_X + 30, 238, "sit", 104),       # top of the cat tree
    ("cats", 254, 364, "curl", 128),      # the windowsill, in the curtains
    ("study", 642, 174, "sit", 96),       # the shelf, at the clear end
    ("cats", TREE_X - 56, 372, "curl", 124),      # the lower platform
    ("hall", 946, 410, "sit", 116),       # the console table by the door
    ("study", 958, 274, "curl", 124),     # the study windowsill
    ("cats", 486, 356, "sit", 94),        # the lower wall shelf
    ("cats", 272, 712, "curl", 152),      # the basket
    ("study", 676, 726, "curl", 172),     # the middle of the rug
    ("hall", 290, 640, "curl", 132),      # down inside the box
    ("cats", 606, 716, "sit", 126),       # waiting at the bowls
    ("study", 414, 606, "sit", 124),      # the near edge of the rug
    ("cats", 940, 730, "curl", 158),      # flat out on the rug
    ("cats", 632, 254, "curl", 112),      # the high shelf, where it is warm
    ("cats", 392, 426, "curl", 134),      # on the blanket chest
)


def room_cats(state):
    """The cats the flat shows, in the order they get the good spots."""
    got = [(c.level, BY_KEY[k].rarity, k) for k, c in state.cards.items()]
    got.sort(reverse=True)
    return [BY_KEY[k] for _, _, k in got[:len(SPOTS)]]


def cats_in(state, area):
    """(breed, spot) for every cat that lives in this room."""
    out = []
    for b, spot in zip(room_cats(state), SPOTS):
        if spot[0] == area:
            out.append((b, spot))
    return out


def cat_level(state, b):
    card = state.cards.get(b.key)
    return card.level if card else 1


def cat_rect(b, spot, level=1):
    _, x, y, pose, hgt = spot
    img = cat_surface(b, pose, hgt, level=level)
    return img.get_rect(midbottom=(x, y))


def draw_cats(surf, state, area, t):
    for i, (b, spot) in enumerate(cats_in(state, area)):
        _, x, y, pose, hgt = spot
        blink = math.sin(t * 0.7 + i * 2.1) > 0.985
        img = cat_surface(b, pose, hgt, blink, cat_level(state, b))
        breathe = 1.0 + 0.012 * math.sin(t * 1.3 + i)
        iw, ih = img.get_size()
        img = pygame.transform.smoothscale(img, (iw, max(2, int(ih * breathe))))
        r = img.get_rect(midbottom=(x, y))
        sh = pygame.Surface((iw, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, iw, 14))
        surf.blit(sh, (r.centerx - iw // 2, y - 8))
        surf.blit(img, r)


# ---------------------------------------------------------------------------
# PIECES EVERY ROOM USES
# ---------------------------------------------------------------------------
def _wallpaper(surf, bottom, top_col=ROOM_LO, low_col=ROOM, stripe=46):
    for y in range(0, bottom, 4):
        f = y / bottom
        pygame.draw.rect(surf, mix(top_col, low_col, f ** 0.7), (0, y, W, 4))
    for x in range(0, W, stripe):
        s = pygame.Surface((2, bottom), pygame.SRCALPHA)
        s.fill((*WOOD_HI, 16))
        surf.blit(s, (x, 0))


def _boards(surf, top, dark=0.72):
    pygame.draw.rect(surf, shade(WOOD_LO, dark), (0, top, W, H - top))
    for i in range(8):
        y = top + 12 + i * 30
        if y < H:
            hairline(surf, 0, y, W, WOOD_HI, 30)
    pygame.draw.rect(surf, shade(WOOD_HI, 0.55), (0, top - 10, W, 10))
    pygame.draw.rect(surf, shade(WOOD, 0.8), (0, top - 2, W, 3))


def _rug(surf, rect, col=RUG):
    pygame.draw.ellipse(surf, col, rect)
    pygame.draw.ellipse(surf, mix(col, LAMP, 0.12), rect.inflate(-44, -36))
    pygame.draw.ellipse(surf, mix(col, INK, 0.25), rect.inflate(-120, -94))


def _mat(surf, parcels, t, r=None):
    """The doormat, and whatever the post has left on it."""
    r = r or MAT_R
    pygame.draw.polygon(surf, (84, 64, 42), [
        (r.x + 22, r.y), (r.right - 22, r.y),
        (r.right, r.bottom), (r.x, r.bottom)])
    for i in range(10):
        f = i / 9
        y = r.y + 6 + i * 10
        inset = int(20 * (1 - f))
        hairline(surf, r.x + inset + 6, y, r.right - inset - 6,
                 mix(PAPER, WOOD, 0.45), 30)
    for i in range(9):
        f = (i + 0.5) / 9
        pygame.draw.line(surf, mix(PAPER, WOOD, 0.5),
                         (int(r.x + 22 + (r.w - 44) * f), r.y + 4),
                         (int(r.x + r.w * f), r.bottom - 4), 1)
    pygame.draw.polygon(surf, (62, 46, 30), [
        (r.x + 22, r.y), (r.right - 22, r.y),
        (r.right, r.bottom), (r.x, r.bottom)], 3)
    if not parcels:
        text(surf, "the mat", 13, (r.centerx, r.bottom - 14), shade(TEA, 0.5),
             center=True, kind="mono", shadow=False)
        return
    n = min(3, len(parcels))
    x0 = r.centerx - (n * 88 + (n - 1) * 8) // 2
    for i in range(n):
        bob = math.sin(t * 2.2 + i) * 1.5
        pr = pygame.Rect(x0 + i * 96, r.y - 24 + i * 9 + bob, 88, 72)
        draw_parcel(surf, pr, seed=i)
    if len(parcels) > 3:
        text(surf, f"+{len(parcels) - 3} more", 14,
             (r.right - 6, r.y - 34), CREAM, right=True, kind="mono")


# ---------------------------------------------------------------------------
# THE HALL
# ---------------------------------------------------------------------------
def _hall(surf, state, t):
    surf.fill(INK)
    _wallpaper(surf, HALL_FLOOR, (24, 19, 18), (40, 31, 28), 58)
    _boards(surf, HALL_FLOOR, 0.66)

    # the front door, which is the only way anything gets into this flat
    fr = DOOR_R.inflate(26, 18)
    fr.bottom = DOOR_R.bottom
    pygame.draw.rect(surf, shade(WOOD, 0.8), fr)
    pygame.draw.rect(surf, WOOD_HI, fr, width=3)
    d = DOOR_R
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.25), d)
    glass = pygame.Rect(d.x + 26, d.y + 24, d.w - 52, 108)
    pygame.draw.rect(surf, (30, 36, 50), glass)
    for i in range(4):                     # the street, through old glass
        gx = glass.x + 12 + i * (glass.w - 24) / 3
        glow(surf, (gx, glass.centery), 42, (120, 128, 150), 0.14)
    pygame.draw.rect(surf, shade(WOOD, 0.7), glass, width=6)
    pygame.draw.line(surf, shade(WOOD, 0.7), (glass.centerx, glass.y),
                     (glass.centerx, glass.bottom), 5)
    for i, (py, ph) in enumerate(((160, 140), (316, 140))):
        p = pygame.Rect(d.x + 30, d.y + py, d.w - 60, ph)
        pygame.draw.rect(surf, mix(WOOD, RUG, 0.18), p)
        pygame.draw.rect(surf, shade(WOOD, 0.72), p, width=3)
    # the letterbox, and the light coming under the door
    lb = pygame.Rect(d.centerx - 62, d.y + 288, 124, 18)
    pygame.draw.rect(surf, mix(TEA, WOOD, 0.4), lb, border_radius=3)
    pygame.draw.rect(surf, shade(INK, 1.4), lb.inflate(-10, -8), border_radius=2)
    pygame.draw.circle(surf, mix(LAMP, TEA, 0.5), (d.right - 34, d.centery), 9)
    pygame.draw.circle(surf, shade(TEA, 0.6), (d.right - 34, d.centery), 9, 2)
    under = pygame.Surface((d.w - 20, 10), pygame.SRCALPHA)
    under.fill((*LAMP, 34))
    surf.blit(under, (d.x + 10, d.bottom - 10))

    # coat hooks and a radiator on the left
    rail = pygame.Rect(96, 268, 266, 14)
    pygame.draw.rect(surf, WOOD_HI, rail, border_radius=3)
    for i in range(4):
        hx = rail.x + 30 + i * 68
        pygame.draw.line(surf, mix(TEA, CREAM, 0.2), (hx, rail.bottom),
                         (hx, rail.bottom + 12), 3)
        pygame.draw.circle(surf, mix(TEA, CREAM, 0.2),
                           (hx + 4, rail.bottom + 13), 4)
    for i, (cx, col, hgt) in enumerate(((150, (92, 70, 62), 150),
                                        (236, (68, 72, 84), 126),
                                        (318, (104, 76, 54), 96))):
        pygame.draw.polygon(surf, mix(col, LAMP, 0.08), [
            (cx - 6, rail.bottom + 10), (cx + 10, rail.bottom + 10),
            (cx + 30, rail.bottom + hgt), (cx - 26, rail.bottom + hgt)])
        pygame.draw.polygon(surf, shade(col, 0.8), [
            (cx - 6, rail.bottom + 10), (cx + 10, rail.bottom + 10),
            (cx + 30, rail.bottom + hgt), (cx - 26, rail.bottom + hgt)], 2)
    rad = pygame.Rect(118, 452, 212, 66)
    pygame.draw.rect(surf, mix(PAPER, WOOD, 0.55), rad, border_radius=4)
    for i in range(9):
        x = rad.x + 8 + i * 23
        pygame.draw.rect(surf, mix(PAPER, WOOD, 0.42), (x, rad.y + 5, 13,
                                                        rad.h - 10),
                         border_radius=3)
    pygame.draw.rect(surf, shade(WOOD, 0.9), rad, width=2, border_radius=4)
    # a cardboard box somebody never took to the recycling
    box = pygame.Rect(222, 600, 136, 80)
    pygame.draw.rect(surf, shade((146, 112, 78), 0.7), box, border_radius=3)
    pygame.draw.polygon(surf, (164, 128, 90), [
        (box.x, box.y + 6), (box.right, box.y + 6),
        (box.right - 14, box.y - 12), (box.x + 14, box.y - 12)])

    # the console table, with a lamp that is the only warm thing in here
    con = pygame.Rect(834, 410, 250, 16)
    pygame.draw.rect(surf, WOOD_HI, con, border_radius=3)
    for lx in (con.x + 16, con.right - 24):
        pygame.draw.rect(surf, shade(WOOD, 0.85), (lx, con.bottom, 10, 104))
    pygame.draw.rect(surf, shade(WOOD, 0.7), (con.x + 20, con.bottom + 70,
                                              con.w - 44, 8))
    lamp_x = con.x + 36
    pygame.draw.rect(surf, shade(WOOD_HI, 0.9), (lamp_x - 3, con.y - 44, 7, 44))
    sh = [(lamp_x - 26, con.y - 76), (lamp_x + 26, con.y - 76),
          (lamp_x + 34, con.y - 42), (lamp_x - 34, con.y - 42)]
    pygame.draw.polygon(surf, mix(WOOD, EMBER, 0.3), sh)
    pygame.draw.polygon(surf, mix(EMBER, LAMP, 0.4), sh, 2)
    glow(surf, (lamp_x, con.y - 36), 46, LAMP, 0.42)
    glow(surf, (lamp_x + 10, con.y + 10), 190, mix(LAMP, EMBER, 0.5), 0.22)
    # keys in a dish, and the post nobody has opened
    pygame.draw.ellipse(surf, mix(RUG, EMBER, 0.2),
                        (con.right - 92, con.y - 16, 62, 22))
    for i in range(3):
        pygame.draw.line(surf, mix(TEA, CREAM, 0.3),
                         (con.right - 78 + i * 9, con.y - 12),
                         (con.right - 74 + i * 9, con.y - 2), 2)
    for i in range(3):
        pygame.draw.rect(surf, mix(PAPER, WOOD, 0.2 + i * 0.1),
                         (con.right - 170 + i * 4, con.y - 8 - i * 4, 64, 10))

    # the ceiling pendant, bare and not very bright
    px = 352
    pygame.draw.line(surf, shade(WOOD, 0.9), (px, 0), (px, 84), 3)
    pend = [(px - 42, 84), (px + 42, 84), (px + 28, 130), (px - 28, 130)]
    pygame.draw.polygon(surf, mix(WOOD, EMBER, 0.22), pend)
    pygame.draw.polygon(surf, mix(EMBER, LAMP, 0.35), pend, 2)
    flick = 0.95 + 0.05 * math.sin(t * 1.7)
    glow(surf, (px, 136), 54, LAMP, 0.40 * flick)
    glow(surf, (px + 10, 340), 320, mix(LAMP, EMBER, 0.4), 0.17 * flick)
    glow(surf, (MAT_R.centerx, MAT_R.y - 10), 190, mix(LAMP, EMBER, 0.45),
         0.10 * flick)

    _mat(surf, state.parcels, t)
    draw_cats(surf, state, "hall", t)
    # the near wall of the box, over whoever has got into it
    front = pygame.Rect(box.x, box.y + 22, box.w, box.h - 22)
    pygame.draw.rect(surf, (146, 112, 78), front, border_radius=3)
    pygame.draw.rect(surf, shade((146, 112, 78), 0.76), front, width=2,
                     border_radius=3)
    pygame.draw.line(surf, shade((146, 112, 78), 0.86),
                     (front.x + 14, front.centery),
                     (front.right - 14, front.centery), 2)

    # the study, warm, through the doorway on the right
    edge = pygame.Surface((160, H), pygame.SRCALPHA)
    for x in range(160):
        a = int(26 * (x / 159) ** 2)
        pygame.draw.line(edge, (*LAMP, a), (x, 0), (x, H))
    surf.blit(edge, (W - 160, 0))


# ---------------------------------------------------------------------------
# THE DESK
# ---------------------------------------------------------------------------
def _wall(surf, t):
    for y in range(0, WALL_H, 4):
        f = y / WALL_H
        pygame.draw.rect(surf, mix(ROOM_LO, ROOM, f ** 0.7), (0, y, W, 4))
    for x in range(0, W, 46):           # wallpaper, almost not there
        s = pygame.Surface((2, WALL_H), pygame.SRCALPHA)
        s.fill((*WOOD_HI, 16))
        surf.blit(s, (x, 0))
    pygame.draw.line(surf, shade(WOOD, 0.7), (0, WALL_H - 2), (W, WALL_H - 2), 3)


def _window(surf, t):
    r = pygame.Rect(812, 52, 300, 208)
    pygame.draw.rect(surf, (18, 22, 34), r)
    rng = random.Random(9)
    for i in range(40):                  # a few stars, and no moon
        x = r.x + rng.randrange(6, r.w - 6)
        y = r.y + rng.randrange(6, r.h - 6)
        a = 60 + 90 * abs(math.sin(t * 0.4 + i))
        s = pygame.Surface((2, 2), pygame.SRCALPHA)
        s.fill((*CREAM, int(a)))
        surf.blit(s, (x, y))
    for i in range(14):                  # rain, slow and warm-lit
        x = r.x + (i * 37 + int(t * 46) % 37) % (r.w - 8) + 4
        y = r.y + int((t * 150 + i * 60) % (r.h - 10)) + 4
        pygame.draw.line(surf, (54, 62, 78), (x, y), (x - 2, y + 9), 1)
    pygame.draw.rect(surf, WOOD, r, width=9)
    pygame.draw.rect(surf, WOOD_HI, r, width=2)
    pygame.draw.line(surf, WOOD, (r.centerx, r.y), (r.centerx, r.bottom), 7)
    pygame.draw.line(surf, WOOD, (r.x, r.centery - 10), (r.right, r.centery - 10), 7)
    sill = pygame.Rect(r.x - 14, r.bottom - 2, r.w + 28, 16)
    pygame.draw.rect(surf, WOOD_HI, sill, border_radius=3)
    pygame.draw.rect(surf, shade(WOOD, 0.8), (sill.x, sill.bottom - 4,
                                              sill.w, 4))


def _shelf(surf):
    r = pygame.Rect(318, 174, 382, 13)
    pygame.draw.rect(surf, WOOD_HI, r, border_radius=2)
    pygame.draw.rect(surf, shade(WOOD, 0.75), (r.x, r.bottom - 4, r.w, 4))
    rng = random.Random(3)
    x = r.x + 14
    while x < r.x + 214:
        hgt = rng.randrange(46, 74)
        wid = rng.randrange(9, 17)
        col = mix(rng.choice((RUG, WOOD_HI, (86, 74, 96), (96, 86, 64))),
                  LAMP, 0.10)
        pygame.draw.rect(surf, col, (x, r.y - hgt, wid, hgt), border_radius=2)
        hairline(surf, x + 2, r.y - hgt + 8, x + wid - 2, PAPER, 70)
        x += wid + 2
    # a leaning one, because a shelf that tidy is nobody's shelf
    pygame.draw.polygon(surf, mix((84, 70, 58), LAMP, 0.1),
                        [(x + 2, r.y), (x + 16, r.y),
                         (x + 30, r.y - 52), (x + 16, r.y - 56)])


def _desk(surf):
    pygame.draw.rect(surf, WOOD, DESK_R)
    for y in range(WALL_H, DESK_FRONT, 3):
        f = (y - WALL_H) / max(1, DESK_FRONT - WALL_H)
        pygame.draw.rect(surf, mix(WOOD, WOOD_HI, 0.25 + 0.5 * f), (0, y, W, 3))
    pygame.draw.rect(surf, WOOD_HI, (0, DESK_FRONT - 7, W, 7))
    pygame.draw.rect(surf, WOOD_LO, (0, DESK_FRONT, W, FLOOR_Y - DESK_FRONT))
    for x in range(40, W, 180):          # the grain of the front panel
        s = pygame.Surface((1, FLOOR_Y - DESK_FRONT - 6), pygame.SRCALPHA)
        s.fill((*WOOD_HI, 26))
        surf.blit(s, (x, DESK_FRONT + 3))
    d = pygame.Rect(840, DESK_FRONT + 14, 260, 62)
    pygame.draw.rect(surf, shade(WOOD_LO, 1.2), d, border_radius=3)
    pygame.draw.rect(surf, shade(WOOD_HI, 0.8), (d.centerx - 24, d.centery - 3,
                                                 48, 7), border_radius=3)


def _floor(surf):
    pygame.draw.rect(surf, shade(WOOD_LO, 0.72), (0, FLOOR_Y, W, H - FLOOR_Y))
    for i in range(7):
        y = FLOOR_Y + 14 + i * 32
        hairline(surf, 0, y, W, WOOD_HI, 30)
    rug = pygame.Rect(220, 598, 760, 180)
    pygame.draw.ellipse(surf, RUG, rug)
    pygame.draw.ellipse(surf, mix(RUG, LAMP, 0.12), rug.inflate(-44, -36))
    pygame.draw.ellipse(surf, mix(RUG, INK, 0.25), rug.inflate(-120, -94))


def _lamp(surf, t, lit=1.0):
    """The only light in the game, and the reason for the whole palette."""
    base = (126, WALL_H - 4)
    pygame.draw.ellipse(surf, shade(WOOD_HI, 0.72),
                        (base[0] - 38, base[1] - 14, 76, 20))
    pygame.draw.ellipse(surf, mix(WOOD_HI, LAMP, 0.12),
                        (base[0] - 36, base[1] - 18, 72, 18))
    pygame.draw.line(surf, shade(WOOD_HI, 0.85), base, (126, 248), 6)
    pygame.draw.line(surf, shade(WOOD_HI, 0.85), (126, 250), (212, 206), 6)
    pygame.draw.circle(surf, mix(WOOD_HI, LAMP, 0.2), (126, 249), 6)
    shade_pts = [(196, 198), (240, 198), (262, 252), (178, 252)]
    pygame.draw.polygon(surf, mix(WOOD, EMBER, 0.32), shade_pts)
    pygame.draw.polygon(surf, mix(EMBER, LAMP, 0.45), shade_pts, 2)
    pygame.draw.line(surf, mix(LAMP, CREAM, 0.3), (178, 252), (262, 252), 3)
    bulb = (220, 256)
    flick = 0.94 + 0.06 * math.sin(t * 2.1) + 0.02 * math.sin(t * 7.3)
    glow(surf, bulb, 58, LAMP, 0.55 * flick * lit)
    glow(surf, (268, 372), 330, mix(LAMP, EMBER, 0.45), 0.30 * flick * lit)
    glow(surf, (268, 372), 150, mix(LAMP, EMBER, 0.3), 0.22 * flick * lit)
    pygame.draw.circle(surf, mix(LAMP, CREAM, 0.4), bulb, 7)
    # dust, which is the thing that makes a beam look like a beam
    rng = random.Random(21)
    for i in range(26):
        px = 150 + rng.random() * 260
        py = 230 + ((rng.random() * 200 + t * (6 + rng.random() * 9)) % 200)
        a = int(50 + 40 * math.sin(t + i))
        s = pygame.Surface((2, 2), pygame.SRCALPHA)
        s.fill((*LAMP, a))
        surf.blit(s, (px, py))


def _laptop(surf, t, hot=False, unread=0):
    r = LAPTOP_R
    lid = pygame.Rect(r.x + 18, r.y, r.w - 36, r.h - 44)
    pygame.draw.rect(surf, (46, 40, 42), lid.inflate(10, 10), border_radius=7)
    screen = lid.inflate(-14, -14)
    pygame.draw.rect(surf, SCREEN, screen, border_radius=3)
    glow(surf, screen.center, int(screen.w * 0.62),
         mix(LAMP, (160, 190, 220), 0.45), 0.16 + (0.05 if hot else 0))
    # what is on the screen, from across the room
    pygame.draw.rect(surf, mix(SCREEN_HI, EMBER, 0.25),
                     (screen.x + 8, screen.y + 8, screen.w - 16, 12),
                     border_radius=2)
    for i in range(3):
        y = screen.y + 30 + i * 26
        pygame.draw.rect(surf, SCREEN_HI,
                         (screen.x + 10, y, screen.w - 20, 20),
                         border_radius=2)
        pygame.draw.rect(surf, mix(EMBER, SCREEN, 0.4),
                         (screen.right - 48, y + 4, 32, 12), border_radius=2)
    base = pygame.Rect(r.x, r.bottom - 46, r.w, 20)
    pygame.draw.polygon(surf, (58, 50, 52), [
        (base.x + 14, base.y), (base.right - 14, base.y),
        (base.right, base.bottom), (base.x, base.bottom)])
    pygame.draw.rect(surf, (40, 34, 36), (base.x + 10, base.bottom - 4,
                                          base.w - 20, 4), border_radius=2)
    if unread:
        c = (base.right - 6, base.y - 2)
        glow(surf, c, 26, EMBER, 0.5)
        pygame.draw.circle(surf, EMBER, c, 11)
        text(surf, str(unread), 14, c, INK, center=True, bold=True,
             shadow=False)


def _binder(surf, t, hot=False, owned=0, total=24):
    r = BINDER_R
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.35), r, border_radius=5)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.18 if hot else 0.08), r, width=2,
                     border_radius=5)
    pygame.draw.rect(surf, shade(RUG, 0.7), (r.x + 16, r.y, 9, r.h))
    for i in range(3):
        pygame.draw.circle(surf, mix(TEA, CREAM, 0.3),
                           (r.x + 21, r.y + 22 + i * 24), 4)
    lab = pygame.Rect(r.x + 44, r.y + 20, r.w - 70, 50)
    pygame.draw.rect(surf, mix(PAPER, RUG, 0.18), lab, border_radius=3)
    text(surf, "THE BINDER", 16, (lab.centerx, lab.y + 14), shade(INK, 1.6),
         center=True, kind="mono", shadow=False)
    text(surf, f"{owned} of {total}", 14, (lab.centerx, lab.y + 34),
         mix(INK, RUG, 0.5), center=True, kind="mono", shadow=False)


def _grass(surf, t):
    """A pot of cat grass. There was a mug of coffee on this desk until
    somebody pointed out what caffeine does to a cat - in a room with
    five of them asleep on the furniture, the only thing left standing
    within reach has to be something they are allowed to chew."""
    pot = pygame.Rect(610, 402, 48, 40)
    rim = pygame.Rect(pot.x - 4, pot.y - 6, pot.w + 8, 14)
    blade = mix((112, 138, 88), LAMP, 0.22)
    rng = random.Random(12)
    for i in range(11):
        f = (i + 0.5) / 11
        x0 = pot.x + 8 + (pot.w - 16) * f
        lean = (f - 0.5) * 2.2 + rng.uniform(-0.35, 0.35)
        hgt = 34 + rng.uniform(-9, 14)
        sway = math.sin(t * 0.7 + i * 1.3) * 2.0
        pts = []
        for k in range(5):
            g = k / 4
            pts.append((x0 + lean * 13 * g * g + sway * g * g,
                        pot.y - 2 - hgt * g))
        pygame.draw.lines(surf, mix(blade, INK, 0.25 * (1 - f)), False,
                          [(round(a), round(b)) for a, b in pts], 3)
    pygame.draw.rect(surf, mix(RUG, EMBER, 0.22), pot,
                     border_bottom_left_radius=6, border_bottom_right_radius=6)
    pygame.draw.rect(surf, mix(RUG, EMBER, 0.34), rim, border_radius=3)
    pygame.draw.rect(surf, shade(mix(RUG, EMBER, 0.2), 0.7),
                     (rim.x + 3, rim.y + 3, rim.w - 6, 5), border_radius=2)


def _study(surf, state, t):
    surf.fill(INK)
    _wall(surf, t)
    _window(surf, t)
    _shelf(surf)
    _desk(surf)
    _floor(surf)
    _lamp(surf, t)
    _laptop(surf, t, unread=len(state.orders))
    _binder(surf, t, owned=state.owned)
    _grass(surf, t)
    draw_cats(surf, state, "study", t)


# ---------------------------------------------------------------------------
# THE CAT ROOM
# ---------------------------------------------------------------------------
def _catroom(surf, state, t):
    surf.fill(INK)
    _wallpaper(surf, CATS_FLOOR, (28, 21, 20), (46, 34, 30), 52)
    _boards(surf, CATS_FLOOR, 0.78)
    _rug(surf, pygame.Rect(760, 640, 500, 170), mix(RUG, EMBER, 0.12))
    _rug(surf, pygame.Rect(120, 626, 420, 150), mix(RUG, WOOD, 0.3))

    # a string of warm bulbs along the top of the wall
    for i in range(13):
        f = i / 12
        x = 40 + f * (W - 80)
        y = 54 + math.sin(f * math.pi) * 34
        if i:
            pygame.draw.line(surf, shade(WOOD, 1.1), (lastx, lasty), (x, y), 2)
        lastx, lasty = x, y
        tw = 0.72 + 0.28 * math.sin(t * 1.6 + i * 1.1)
        glow(surf, (x, y + 8), 26, LAMP, 0.34 * tw)
        pygame.draw.circle(surf, mix(LAMP, CREAM, 0.3), (int(x), int(y + 8)), 4)

    # the window, with the curtains open
    win = pygame.Rect(140, 150, 240, 190)
    pygame.draw.rect(surf, (18, 22, 34), win)
    rng = random.Random(4)
    for i in range(26):
        s = pygame.Surface((2, 2), pygame.SRCALPHA)
        s.fill((*CREAM, int(70 + 70 * abs(math.sin(t * 0.3 + i)))))
        surf.blit(s, (win.x + rng.randrange(6, win.w - 6),
                      win.y + rng.randrange(6, win.h - 6)))
    pygame.draw.rect(surf, WOOD, win, width=8)
    pygame.draw.line(surf, WOOD, (win.centerx, win.y), (win.centerx, win.bottom), 5)
    sill = pygame.Rect(win.x - 22, win.bottom - 2, win.w + 44, 18)
    pygame.draw.rect(surf, WOOD_HI, sill, border_radius=3)
    for sx, cx in ((-1, win.x - 10), (1, win.right + 10)):
        pygame.draw.polygon(surf, mix(RUG, WOOD, 0.4), [
            (cx, win.y - 14), (cx + sx * 46, win.y - 14),
            (cx + sx * 34, win.bottom - 6), (cx, win.bottom - 6)])

    # two shelves up the wall, in the way cats like
    for i, (sx, sy, sw) in enumerate(((414, 358, 176), (556, 256, 168))):
        r = pygame.Rect(sx, sy, sw, 12)
        pygame.draw.rect(surf, WOOD_HI, r, border_radius=2)
        pygame.draw.rect(surf, shade(WOOD, 0.75), (r.x, r.bottom - 4, r.w, 4))
        for bx in (r.x + 14, r.right - 20):
            pygame.draw.line(surf, shade(WOOD, 0.8), (bx, r.bottom),
                             (bx, r.bottom + 14), 3)

    # the cat tree
    base = pygame.Rect(TREE_X - 96, CATS_FLOOR - 24, 206, 26)
    pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.25), base, border_radius=4)
    post = pygame.Rect(TREE_X - 18, 250, 40, CATS_FLOOR - 250)
    pygame.draw.rect(surf, mix(PAPER, WOOD, 0.5), post)
    for i in range(int(post.h // 9)):      # sisal, wound round and round
        y = post.y + 5 + i * 9
        pygame.draw.line(surf, mix(PAPER, WOOD, 0.66), (post.x, y),
                         (post.right, y - 3), 3)
    plat1 = pygame.Rect(TREE_X - 128, 372, 150, 20)
    plat2 = pygame.Rect(TREE_X - 36, 238, 150, 20)
    for p in (plat1, plat2):
        pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.3), p, border_radius=5)
        pygame.draw.rect(surf, shade(WOOD, 0.8), (p.x, p.bottom - 5, p.w, 5),
                         border_radius=3)
    pygame.draw.rect(surf, mix(PAPER, WOOD, 0.5),
                     (plat1.centerx - 16, plat1.bottom, 32,
                      CATS_FLOOR - 24 - plat1.bottom))
    # a ball on a string, still swinging from earlier
    sway = math.sin(t * 1.1) * 26
    pygame.draw.line(surf, shade(TEA, 0.7), (plat2.x + 20, plat2.bottom),
                     (plat2.x + 20 + sway, plat2.bottom + 86), 2)
    pygame.draw.circle(surf, mix(EMBER, PAPER, 0.3),
                       (int(plat2.x + 20 + sway), int(plat2.bottom + 92)), 11)

    # a low chest, with the blankets nobody folds twice
    chest = pygame.Rect(316, 424, 250, 132)
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.3), chest, border_radius=4)
    pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.12),
                     (chest.x - 8, chest.y - 14, chest.w + 16, 18),
                     border_radius=4)
    for i in range(2):
        pygame.draw.rect(surf, shade(WOOD, 0.74),
                         (chest.x + 18 + i * 120, chest.y + 24, 96, 82),
                         border_radius=3)
        pygame.draw.circle(surf, mix(TEA, CREAM, 0.2),
                           (chest.x + 66 + i * 120, chest.y + 66), 5)
    for i, col in enumerate(((132, 108, 126), (154, 122, 92))):
        pygame.draw.rect(surf, mix(col, LAMP, 0.1),
                         (chest.right - 118, chest.y - 30 + i * 16, 104, 18),
                         border_radius=4)

    # a basket, two bowls and the toys that end up under everything
    bask = pygame.Rect(176, 648, 196, 84)
    pygame.draw.ellipse(surf, mix(WOOD_HI, PAPER, 0.3), bask)
    pygame.draw.ellipse(surf, mix(WOOD, PAPER, 0.18),
                        bask.inflate(-24, -30).move(0, -6))
    for i in range(12):
        x = bask.x + 10 + i * 15
        pygame.draw.line(surf, shade(WOOD, 0.9), (x, bask.y + 24),
                         (x + 6, bask.bottom - 10), 2)
    for i, (bx, col) in enumerate(((556, (138, 150, 164)), (628, (166, 126, 96)))):
        pygame.draw.ellipse(surf, mix(col, LAMP, 0.1), (bx, 712, 58, 24))
        pygame.draw.ellipse(surf, shade(col, 0.6), (bx + 7, 716, 44, 14))
    pygame.draw.circle(surf, mix(GOOD, PAPER, 0.3), (436, 726), 10)
    pygame.draw.ellipse(surf, mix(MUTED, PAPER, 0.2), (1052, 700, 40, 18))
    pygame.draw.line(surf, MUTED, (1052, 709), (1024, 716), 2)

    draw_cats(surf, state, "cats", t)
    # the near rim of the basket, drawn last so whoever is in it is in it
    pygame.draw.arc(surf, mix(WOOD_HI, PAPER, 0.3),
                    (bask.x, bask.y + 2, bask.w, bask.h - 2), 3.34, 6.08, 15)
    for i in range(12):
        x = bask.x + 14 + i * 15
        y = bask.centery + math.sqrt(max(0.0, 1 - ((x - bask.centerx) /
                                                   (bask.w / 2)) ** 2)) * \
            (bask.h / 2) - 7
        pygame.draw.line(surf, shade(WOOD, 0.85), (x, y - 6), (x + 5, y + 6), 2)

    edge = pygame.Surface((160, H), pygame.SRCALPHA)
    for x in range(160):
        a = int(24 * (1 - x / 159) ** 2)
        pygame.draw.line(edge, (*LAMP, a), (x, 0), (x, H))
    surf.blit(edge, (0, 0))


_AREA_DRAW = {"hall": _hall, "study": _study, "cats": _catroom}
_scratch = None


def draw_area(surf, area, state, t):
    _AREA_DRAW[area](surf, state, t)


def area_scratch():
    """One spare screen, for sliding one room off while another arrives."""
    global _scratch
    if _scratch is None:
        _scratch = pygame.Surface((W, H))
    return _scratch


# ---------------------------------------------------------------------------
# THE GAME
#
# Four screens: the room, the website, a parcel being opened, and the
# binder. The room is the only one that is a place; the other three are
# things you are holding.
# ---------------------------------------------------------------------------
HINTS = (
    "A and D walk between the hall, the desk and the cat room",
    "the post lands in the hall - go and get it",
    "click a cat. any cat",
    "the laptop is the only way to get cards",
    "duplicates are not waste - they are levels",
    "slow post is free, and the cats earn while it comes",
    "a breed at level 10 retires, and the shop stops sending it",
    "the post will only carry four parcels at a time",
)


class Toast:
    __slots__ = ("text", "sub", "life", "colour")

    def __init__(self, text, sub="", colour=None, life=5.0):
        self.text = text
        self.sub = sub
        self.life = life
        self.colour = colour or EMBER


class Float:
    __slots__ = ("x", "y", "text", "life", "colour")

    def __init__(self, x, y, text, colour):
        self.x = x
        self.y = y
        self.text = text
        self.life = 1.6
        self.colour = colour


class GameBase:
    def __init__(self, screen):
        self.screen = screen
        self.state = load_state()
        self.scene = "room"
        self.area = self.state.area
        self.pan = 0.0              # 1 while a room slides past, else 0
        self.pan_from = None
        self.pan_dir = 1
        self.t = 0.0
        self.buttons = []
        self.toasts = []
        self.floats = []
        self.autosave = 0.0
        self.coin_timer = 0.0
        self.since_coin = 0.0
        self.hint = 0.0
        self.hint_i = 0
        self.full = False

        # the website
        self.tab = "catalogue"
        self.product = None
        self.qty = 1
        self.mode = 0
        self.seen_shop = False

        # opening a parcel
        self.open_pack_key = None
        self.open_qty = 1
        self.pulls = []
        self.flipped = 0
        self.lid = 0.0
        self.cut = False
        self.deal = 0.0

        # the binder
        self.pick = None

        if self.state.first_run:
            self.toasts.append(Toast(
                "ten dollars and a laptop",
                "a paper sack of strays is ten dollars", EMBER, 14.0))
            self.toasts.append(Toast(
                "click the laptop",
                "it is the only way cards get into this room", LAMP, 14.0))
        if self.state.away > 0.5:
            self.toasts.append(Toast(
                f"while you were out: {money(self.state.away)}",
                "the cats kept earning, up to two hours of it", GOOD, 8.0))
        if self.state.parcels:
            self.toasts.append(Toast(
                f"{len(self.state.parcels)} parcel"
                f"{'s' if len(self.state.parcels) > 1 else ''} on the mat",
                "they came while you were out", EMBER, 8.0))

    # -- plumbing -----------------------------------------------------------
    def go(self, scene):
        if scene != self.scene:
            self.scene = scene
            self.buttons = []
            self.beep("page")

    def go_area(self, area, quiet=False):
        """Walk to another room. The slide IS the walk: there is no figure
        to follow about, because the flat is yours and you are the one
        carrying the camera through it."""
        if area == self.area or area not in AREAS or self.scene != "room":
            return
        self.pan_dir = 1 if AREAS.index(area) > AREAS.index(self.area) else -1
        self.pan_from = self.area
        self.pan = 1.0
        self.area = area
        self.state.area = area
        if not quiet:
            self.beep("step")

    def walk(self, d):
        i = AREAS.index(self.area) + d
        if 0 <= i < len(AREAS):
            self.walk_to(AREAS[i])

    def walk_to(self, area):
        self.go_area(area)

    def beep(self, name, vol=1.0):
        if self.state.sound:
            play(name, vol)

    def toast(self, text, sub="", colour=None, life=5.0):
        self.toasts.insert(0, Toast(text, sub, colour, life))
        del self.toasts[4:]

    def save(self):
        save_state(self.state)

    # -- the loop -----------------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()
        if self.state.music:
            music(True)
        running = True
        while running:
            dt = min(0.1, clock.tick(FPS) / 1000.0)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    running = self.key(e) is not False
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.click(e.pos)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        self.save()

    def key(self, e):
        k = e.key
        if k == pygame.K_ESCAPE:
            if self.scene == "room":
                self.go("menu")
            elif self.scene == "shop" and self.product:
                self.product = None
            elif self.scene == "open":
                self.leave_open()
            else:
                self.go("room")
        elif k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif k == pygame.K_m:
            self.state.music = not self.state.music
            music(self.state.music)
        elif k == pygame.K_s:
            self.state.sound = not self.state.sound
            self.beep("click")
        elif k == pygame.K_l and self.scene in ("room", "binder"):
            self.go("shop")
        elif k == pygame.K_b and self.scene in ("room", "shop"):
            self.go("binder")
        elif k in (pygame.K_LEFT, pygame.K_a) and self.scene == "room":
            self.walk(-1)
        elif k in (pygame.K_RIGHT, pygame.K_d) and self.scene == "room":
            self.walk(1)
        elif k == pygame.K_o and self.scene == "room":
            if self.state.parcels and self.area != "hall":
                self.go_area("hall")      # the post is by the front door
            else:
                self.start_open()
        elif k == pygame.K_SPACE and self.scene == "open":
            # first press turns one card over, the next turns the rest:
            # one for the ritual, one for the people who have done this
            # three hundred times
            if not self.cut:
                self.cut_tape()
            elif self.flipped < len(self.pulls):
                self.flip_all() if self.flipped else self.flip_next()
        return True

    def click(self, pos):
        for b in self.buttons:
            if b.enabled and b.rect.collidepoint(pos):
                self.press(b.key)
                return

    # -- what every button does --------------------------------------------
    def press(self, key):
        name, val = key
        if name != "flip":
            self.beep("click")
        if name == "scene":
            self.go(val)
        elif name == "laptop":
            self.go("shop")
        elif name == "binder":
            self.go("binder")
        elif name == "mat":
            self.start_open()
        elif name == "go":
            self.go_area(val)
        elif name == "cat":
            self.pet(val)
        elif name == "tab":
            self.tab = val
            self.product = None
        elif name == "product":
            self.product = val
            self.qty = 1
            self.mode = 0
            self.beep("page")
        elif name == "qty":
            self.qty = int(clamp(val, 1, BULK))
        elif name == "mode":
            self.mode = int(val)
        elif name == "place":
            self.place_order()
        elif name == "club":
            if self.state.join_club():
                self.beep("level")
                self.toast("welcome to " + CLUB[self.state.club - 1][1],
                           f"the post will carry {self.state.slots} parcels now",
                           GOOD)
        elif name == "cut":
            self.cut_tape()
        elif name == "flip":
            self.flip_next()
        elif name == "flipall":
            self.flip_all()
        elif name == "done":
            self.finish_open()
        elif name == "next":
            self.finish_open()
            self.start_open()
        elif name == "leave":
            self.leave_open()
        elif name == "pick":
            self.pick = None if self.pick == val else val
        elif name == "music":
            self.state.music = not self.state.music
            music(self.state.music)
        elif name == "sound":
            self.state.sound = not self.state.sound
        elif name == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def pet(self, key):
        """Click a cat and it tells you who it is. That is the whole
        feature, and it is the reason the cat room exists."""
        card = self.state.cards.get(key)
        if card is None:
            return
        self.beep("purr")
        for b, spot in cats_in(self.state, self.area):
            if b.key == key:
                r = cat_rect(b, spot, card.level)
                self.floats.append(Float(r.centerx, r.y - 6,
                                         f"{b.name}, level {card.level}",
                                         warm(CREAM, 0.1)))

    # -- ordering -----------------------------------------------------------
    def place_order(self):
        pack = BY_PACK[self.product]
        o = self.state.order(pack, self.qty, self.mode)
        if o is None:
            return
        self.beep("coin")
        self.toast(f"order #{o.num} placed",
                   f"{self.qty} x {pack.name} - "
                   f"{clock_str(o.left)} by {SHIPPING[self.mode][1].lower()}")
        self.product = None
        self.tab = "orders"
        self.save()

    # -- opening ------------------------------------------------------------
    def start_open(self):
        if not self.state.parcels:
            return
        key, qty = self.state.parcels.pop(0)
        self.open_pack_key = key
        self.open_qty = qty
        self.pulls = []
        self.flipped = 0
        self.lid = 0.0
        self.cut = False
        self.deal = 0.0
        self.go("open")

    def cut_tape(self):
        if self.cut:
            return
        self.cut = True
        self.beep("tape")
        rng = random.Random()
        self.pulls = self.state.open_pack(BY_PACK[self.open_pack_key],
                                          self.open_qty, rng)
        self.save()

    def flip_next(self):
        if self.flipped >= len(self.pulls):
            return
        p = self.pulls[self.flipped]
        self.flipped += 1
        self.beep("flip", 0.8)
        if p.kind == "new":
            self.beep("legend" if p.breed.rarity >= R_PEDIGREE else "new")
            self.toast(f"{p.breed.name} is new",
                       f"{rarity_name(p.breed.rarity).lower()} - "
                       f"{rate(p.breed.base_rate)} to start",
                       rarity_colour(p.breed.rarity), 6.0)
        elif p.kind == "level":
            self.beep("level")
            if p.level >= MAX_LEVEL:
                self.toast(f"{p.breed.name} is retired",
                           "level 10 - the shop will not send another",
                           LAMP, 7.0)

    def flip_all(self):
        while self.flipped < len(self.pulls):
            self.flip_next()

    def leave_open(self):
        """Walk away from a parcel. One that is still taped goes back on
        the mat - popping it off the pile before it is opened and then
        leaving the screen is otherwise a parcel paid for and lost."""
        if not self.cut:
            self.state.parcels.insert(0, (self.open_pack_key, self.open_qty))
        self.go("room")

    def finish_open(self):
        self.go("room")
        self.save()
        if self.state.complete and not self.state.seen_end:
            self.state.seen_end = True
            self.save()
            self.beep("legend")
            self.go("end")

    # -- time ---------------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.pan = max(0.0, self.pan - dt * 3.1)
        st = self.state
        before = st.income
        landed = st.tick(dt)
        for o in landed:
            self.beep("bell" if len(landed) == 1 else "thud")
            self.toast(f"order #{o.num} is here",
                       f"{BY_PACK[o.pack].name} - on the mat in the hall",
                       EMBER, 7.0)
        self.full = len(st.orders) >= st.slots

        # The number that floats off a cat is the money that actually
        # arrived since the last one, not a plausible-looking figure.
        self.since_coin += st.income * dt
        self.coin_timer -= dt
        if self.coin_timer <= 0 and st.income > 0 and self.scene == "room":
            self.coin_timer = clamp(2.2 - st.income * 0.02, 0.45, 2.2)
            here = cats_in(st, self.area)
            if here:
                b, spot = random.choice(here)
                r = cat_rect(b, spot, cat_level(st, b))
                self.floats.append(Float(r.centerx + random.uniform(-14, 14),
                                         r.y - 10,
                                         "+" + money(self.since_coin), LAMP))
                self.since_coin = 0.0
        for f in list(self.floats):
            f.life -= dt
            f.y -= dt * 22
            if f.life <= 0:
                self.floats.remove(f)
        for tst in list(self.toasts):
            tst.life -= dt
            if tst.life <= 0:
                self.toasts.remove(tst)

        if self.scene == "open" and self.cut:
            self.lid = min(1.0, self.lid + dt * 2.6)
            if self.lid >= 1.0:
                self.deal = min(1.0, self.deal + dt * 1.8)

        self.hint += dt
        if self.hint > 11:
            self.hint = 0
            self.hint_i = (self.hint_i + 1) % len(HINTS)

        self.autosave += dt
        if self.autosave > 20:
            self.autosave = 0
            self.save()

    # -- drawing ------------------------------------------------------------
    def draw(self):
        s = self.screen
        self.buttons = []
        if self.scene == "room":
            self.draw_room(s)
        elif self.scene == "shop":
            self.draw_shop(s)
        elif self.scene == "open":
            self.draw_open(s)
        elif self.scene == "menu":
            self.draw_menu(s)
        elif self.scene == "end":
            self.draw_end(s)
        else:
            self.draw_binder(s)
        for b in self.buttons:
            b.hover(pygame.mouse.get_pos())
            b.draw(s)
        self.draw_floats(s)
        grade(s)
        self.draw_toasts(s)

    def draw_floats(self, s):
        for f in self.floats:
            a = int(255 * clamp(f.life / 1.6, 0, 1))
            text(s, f.text, 15, (f.x, f.y), f.colour, center=True,
                 kind="mono", alpha=a)

    def draw_toasts(self, s):
        y = H - 24
        for t in self.toasts:
            a = clamp(t.life, 0, 1)
            wdt = 340
            r = pygame.Rect(W - wdt - 22, y - 54, wdt, 50)
            panel(s, r, mix(DEEP, t.colour, 0.10), shade(t.colour, 0.7),
                  radius=8, alpha=int(236 * a))
            text(s, t.text, 17, (r.x + 14, r.y + 9), warm(t.colour, 0.3),
                 alpha=int(255 * a))
            if t.sub:
                text(s, t.sub, 12, (r.x + 14, r.y + 29), MUTED,
                     kind="mono", alpha=int(230 * a), shadow=False,
                     max_w=wdt - 28)
            y -= 58

    # -- the flat -----------------------------------------------------------
    def draw_room(self, s):
        st = self.state
        t = self.t
        if self.pan > 0.001 and self.pan_from:
            f = self.pan ** 1.7              # eased, 1 down to 0
            sc = area_scratch()
            draw_area(sc, self.pan_from, st, t)
            s.blit(sc, (int(-self.pan_dir * W * (1.0 - f)), 0))
            draw_area(sc, self.area, st, t)
            s.blit(sc, (int(self.pan_dir * W * f), 0))
            self.draw_hud(s)
            return
        draw_area(s, self.area, st, t)
        self.hotspots(s)
        self.draw_hud(s)

    def hotspots(self, s):
        """What can be touched in the room you are standing in."""
        st = self.state
        mouse = pygame.mouse.get_pos()
        if self.area == "study":
            spots = ((LAPTOP_R, "order some cards", ("laptop", None)),
                     (BINDER_R, "the binder", ("binder", None)))
        elif self.area == "hall":
            r = MAT_R.inflate(0, 72).move(0, -36)
            spots = ((r, "open a parcel" if st.parcels else "nothing today",
                      ("mat", None)),)
        else:
            spots = ()
        for r, label, key in spots:
            self.buttons.append(Button(r, "", key, "hit"))
            if r.collidepoint(mouse):
                pygame.draw.rect(s, mix(EMBER, LAMP, 0.4), r, width=2,
                                 border_radius=6)
                text(s, label, 15, (r.centerx, r.y - 12), warm(CREAM, 0.2),
                     center=True, kind="mono")
        for b, spot in cats_in(st, self.area):
            r = cat_rect(b, spot, cat_level(st, b))
            self.buttons.append(Button(r, "", ("cat", b.key), "hit"))
            if r.collidepoint(mouse):
                card = st.cards[b.key]
                text(s, f"{b.name}  lv {card.level}", 14,
                     (r.centerx, r.y - 16), warm(CREAM, 0.15), center=True,
                     kind="mono")

        i = AREAS.index(self.area)
        if i > 0:
            self.buttons.append(Button((16, H // 2 - 46, 44, 92), "<",
                                       ("go", AREAS[i - 1]), "plain", 22,
                                       kind="mono"))
        if i < len(AREAS) - 1:
            self.buttons.append(Button((W - 60, H // 2 - 46, 44, 92), ">",
                                       ("go", AREAS[i + 1]), "plain", 22,
                                       kind="mono"))

    def draw_hud(self, s):
        st = self.state
        r = pygame.Rect(22, 18, 272, 78)
        panel(s, r, mix(DEEP, INK, 0.2), shade(TEA, 0.4), radius=10, alpha=228)
        text(s, money(st.money), 36, (r.x + 16, r.y + 10), warm(CREAM, 0.25))
        text(s, rate(st.income), 16, (r.right - 14, r.y + 28), EMBER,
             right=True, kind="mono")
        text(s, f"{st.owned}/{len(BREEDS)} breeds   "
                f"{st.retired} retired", 13, (r.x + 16, r.y + 54), MUTED,
             kind="mono", shadow=False)

        if self.scene == "room":
            x = W // 2 - sum(font(14, False, "mono").size(AREA_NAME[a])[0] + 34
                             for a in AREAS) // 2
            for a in AREAS:
                wdt = font(14, False, "mono").size(AREA_NAME[a])[0] + 34
                r = pygame.Rect(x, 22, wdt, 30)
                on = a == self.area
                if on:
                    panel(s, r, mix(DEEP, EMBER, 0.16), shade(EMBER, 0.7),
                          radius=8, shadow=False)
                    text(s, AREA_NAME[a], 14, r.center, warm(CREAM, 0.2),
                         center=True, kind="mono", shadow=False)
                self.buttons.append(Button(r, AREA_NAME[a], ("go", a),
                                           "hit" if on else "link", 14,
                                           kind="mono", colour=TEA))
                x += wdt
            if st.parcels and self.area != "hall":
                word = "parcel" if len(st.parcels) == 1 else "parcels"
                text(s, f"{len(st.parcels)} {word} on the mat, in the hall",
                     13, (W // 2, 58), warm(EMBER, 0.2), center=True,
                     kind="mono")
            text(s, HINTS[self.hint_i], 14, (W // 2, H - 26), shade(TEA, 0.8),
                 center=True, kind="mono",
                 alpha=int(200 * min(1.0, self.hint * 0.8)))
            self.buttons.append(Button((W - 142, 22, 56, 30),
                                       "MUS" if st.music else "mus",
                                       ("music", None), "plain", 14,
                                       kind="mono"))
            self.buttons.append(Button((W - 80, 22, 56, 30),
                                       "SFX" if st.sound else "sfx",
                                       ("sound", None), "plain", 14,
                                       kind="mono"))
            self.buttons.append(Button((W - 204, 22, 56, 30), "?",
                                       ("scene", "menu"), "plain", 16,
                                       kind="mono"))


# ---------------------------------------------------------------------------
# THE WEBSITE
#
# The shop is a laptop in the room, so it is drawn as one: the room is
# still there round the edges, dimmer, and the page sits inside a browser
# window. The site is in a dark theme because everything in this game is;
# a white page at this hour would be a flashbulb.
# ---------------------------------------------------------------------------
SHOP_R = pygame.Rect(84, 36, 1012, 690)
PAGE_R = pygame.Rect(SHOP_R.x + 14, SHOP_R.y + 56, SHOP_R.w - 28,
                     SHOP_R.h - 70)
def _star(surf, cx, cy, r, colour):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.46
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(surf, colour, [(round(x), round(y)) for x, y in pts])


def _stars(surf, n, pos, size=13, colour=None):
    """Five stars, filled as far as the rating goes. A shop without a
    star rating is not a shop anybody believes in."""
    col = colour or mix(EMBER, LAMP, 0.25)
    for i in range(5):
        _star(surf, pos[0] + 7 + i * 15, pos[1] + 6, 6.5,
              col if i < n else shade(DIM, 0.8))


def _browser(surf, title):
    panel(surf, SHOP_R, SCREEN, shade(SCREEN_HI, 1.4), radius=10)
    bar_r = pygame.Rect(SHOP_R.x, SHOP_R.y, SHOP_R.w, 44)
    pygame.draw.rect(surf, shade(SCREEN_HI, 0.8), bar_r,
                     border_top_left_radius=10, border_top_right_radius=10)
    for i, c in enumerate(((168, 96, 86), (176, 150, 92), (118, 150, 112))):
        pygame.draw.circle(surf, c, (bar_r.x + 24 + i * 20, bar_r.centery), 6)
    pill = pygame.Rect(bar_r.x + 96, bar_r.y + 9, bar_r.w - 180, 26)
    pygame.draw.rect(surf, shade(SCREEN, 1.3), pill, border_radius=13)
    text(surf, "meowrder.example/" + title, 14,
         (pill.x + 14, pill.centery), mix(TEA, CREAM, 0.2), left=True,
         kind="mono", shadow=False)
    text(surf, "23:41", 13, (bar_r.right - 22, bar_r.centery), DIM,
         right=True, kind="mono", shadow=False)


class ShopMixin:
    def draw_shop(self, s):
        self.draw_room(s)
        del self.buttons[:]                 # the room is scenery here
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 188))
        s.blit(dim, (0, 0))
        st = self.state
        _browser(s, "catalogue" if not self.product else
                 "catalogue/" + self.product)

        # masthead
        x, y = PAGE_R.x + 18, PAGE_R.y + 6
        text(s, "MEOWRDER", 30, (x, y), warm(EMBER, 0.25))
        text(s, "cards, by post, since 1998", 13, (x + 186, y + 16), DIM,
             kind="mono", left=True, shadow=False)
        text(s, money(st.money), 26, (PAGE_R.right - 18, y + 14), warm(CREAM, 0.2),
             right=True)
        text(s, f"{len(st.orders)}/{st.slots} parcels in the post", 12,
             (PAGE_R.right - 18, y + 36), MUTED if not self.full else BAD,
             right=True, kind="mono", shadow=False)
        hairline(s, x, y + 50, PAGE_R.right - 18, TEA, 60)

        tabs = (("catalogue", "CATALOGUE"), ("orders", "ORDERS"),
                ("club", "THE CLUB"))
        tx = x
        for key, label in tabs:
            lab = label + (f" ({len(st.orders)})" if key == "orders"
                           and st.orders else "")
            wdt = font(16, False, "mono").size(lab)[0] + 26
            r = pygame.Rect(tx, y + 60, wdt, 30)
            on = self.tab == key
            if on:
                pygame.draw.rect(s, mix(SCREEN_HI, EMBER, 0.2), r,
                                 border_radius=6)
            self.buttons.append(Button(r, lab, ("tab", key),
                                       "link" if not on else "hit", 16,
                                       kind="mono",
                                       colour=CREAM if on else TEA))
            if on:
                text(s, lab, 16, r.center, warm(CREAM, 0.2), center=True,
                     kind="mono", shadow=False)
            tx += wdt + 8
        self.buttons.append(Button((PAGE_R.right - 190, y + 60, 180, 30),
                                   "< back to the room", ("scene", "room"),
                                   "link", 15, kind="mono", colour=TEA))

        body = pygame.Rect(PAGE_R.x + 18, y + 102, PAGE_R.w - 36,
                           PAGE_R.bottom - (y + 102) - 8)
        if self.tab == "orders":
            self.draw_orders(s, body)
        elif self.tab == "club":
            self.draw_club(s, body)
        elif self.product:
            self.draw_product(s, body)
        else:
            self.draw_catalogue(s, body)

    # -- the list of things to buy -----------------------------------------
    def draw_catalogue(self, s, body):
        st = self.state
        rowh = (body.h - 6) // len(PACKS)
        for i, p in enumerate(PACKS):
            r = pygame.Rect(body.x, body.y + i * rowh, body.w, rowh - 8)
            live = st.sellable(p)
            afford = st.money >= p.price and not self.full
            panel(s, r, mix(SCREEN_HI, EMBER, 0.05 if live else 0.0),
                  shade(SCREEN_HI, 1.5), radius=8, shadow=False)
            art = pygame.Rect(r.x + 10, r.y + 8, 104, r.h - 16)
            draw_pack_art(s, art, p, self.t)
            col = CREAM if live else DIM
            text(s, p.name, 21, (art.right + 16, r.y + 10), col)
            paragraph(s, p.blurb, 13, (art.right + 16, r.y + 36),
                      MUTED if live else shade(DIM, 0.9), 520, 3, kind="mono")
            text(s, f"{p.cards} cards", 13, (art.right + 16, r.bottom - 22),
                 mix(TEA, CREAM, 0.2), kind="mono", shadow=False)
            text(s, f"ships in {clock_str(p.ship)}", 13,
                 (art.right + 116, r.bottom - 22), DIM, kind="mono",
                 shadow=False)
            _stars(s, 5 - i // 2, (art.right + 256, r.bottom - 16))
            text(s, f"{(i + 2) * 307 % 900 + 104:,} reviews", 12,
                 (art.right + 320, r.bottom - 16), DIM, kind="mono",
                 shadow=False, left=True)
            if live:
                text(s, money(p.price), 26, (r.right - 150, r.y + 18),
                     warm(EMBER, 0.2), right=True)
            btn = pygame.Rect(r.right - 132, r.centery - 19, 118, 38)
            if not live:
                self.buttons.append(Button(btn, "WITHDRAWN", ("tab", "catalogue"),
                                           "plain", 14, kind="mono",
                                           enabled=False))
                text(s, "nothing left in this line", 12,
                     (r.right - 14, r.y + 18), shade(BAD, 0.9), right=True,
                     kind="mono", shadow=False)
            else:
                self.buttons.append(Button(
                    btn, "ORDER", ("product", p.key), "solid", 17,
                    kind="mono", enabled=afford,
                    note="" if afford else ("post is full" if self.full
                                            else "not yet")))

    # -- one thing, in detail ----------------------------------------------
    def draw_product(self, s, body):
        st = self.state
        p = BY_PACK[self.product]
        self.buttons.append(Button((body.x, body.y, 160, 24),
                                   "< everything else", ("tab", "catalogue"),
                                   "link", 14, kind="mono", colour=TEA))
        body = pygame.Rect(body.x, body.y + 28, body.w, body.h - 28)
        left = pygame.Rect(body.x, body.y, 300, body.h)
        art = pygame.Rect(left.x, left.y, 300, 186)
        panel(s, art, shade(SCREEN_HI, 0.9), None, radius=8, shadow=False)
        draw_pack_art(s, art.inflate(-40, -24), p, self.t)
        text(s, "WHAT PEOPLE SAY", 13, (left.x, art.bottom + 14), TEA,
             kind="mono", shadow=False)
        ry = art.bottom + 36
        for line, stars in p.reviews:
            _stars(s, stars, (left.x, ry))
            ry = paragraph(s, '"' + line + '"', 13, (left.x, ry + 16), MUTED,
                           290, 3, kind="mono") + 10

        right = pygame.Rect(body.x + 330, body.y, body.w - 330, body.h)
        text(s, p.name, 28, (right.x, right.y), warm(CREAM, 0.2))
        y = paragraph(s, p.blurb, 14, (right.x, right.y + 38), mix(TEA, CREAM, 0.3),
                      right.w - 10, 4, kind="mono") + 8

        # the odds, drawn as the shop would have to print them
        text(s, "WHAT IS IN IT", 13, (right.x, y), TEA, kind="mono",
             shadow=False)
        y += 20
        tot = sum(p.weights)
        for r in range(5):
            if not p.weights[r]:
                continue
            c = rarity_colour(r)
            text(s, rarity_name(r), 13, (right.x, y + 7), c, kind="mono",
                 shadow=False)
            br = pygame.Rect(right.x + 96, y + 3, 200, 10)
            bar(s, br, p.weights[r] / tot, c, shade(SCREEN_HI, 1.2))
            text(s, f"{p.weights[r] * 100 // tot}%", 12,
                 (br.right + 10, y + 7), MUTED, kind="mono", shadow=False)
            n = sum(1 for b in BY_RARITY[r] if st.can_hold(b.key))
            text(s, f"{n} still in print", 12, (br.right + 56, y + 7),
                 DIM if n else shade(BAD, 0.9), kind="mono", shadow=False)
            y += 18
        text(s, f"the last card is {rarity_name(p.floor).lower()} or better",
             12, (right.x, y + 6), mix(TEA, CREAM, 0.1), kind="mono",
             shadow=False)
        y += 32

        # quantity and postage, which is the only choice the shop offers
        text(s, "HOW MANY", 13, (right.x, y), TEA, kind="mono", shadow=False)
        for i in range(1, BULK + 1):
            r = pygame.Rect(right.x + 96 + (i - 1) * 46, y - 6, 40, 28)
            on = self.qty == i
            self.buttons.append(Button(r, str(i), ("qty", i),
                                       "solid" if on else "plain", 15,
                                       kind="mono"))
        y += 36
        text(s, "POSTAGE", 13, (right.x, y + 6), TEA, kind="mono",
             shadow=False)
        for m, (key, label, fee, mult, note) in enumerate(SHIPPING):
            r = pygame.Rect(right.x + 96, y, 420, 34)
            on = self.mode == m
            if on:
                panel(s, r, mix(SCREEN_HI, EMBER, 0.14), shade(EMBER, 0.7),
                      radius=6, shadow=False)
            pygame.draw.circle(s, EMBER if on else DIM,
                               (r.x + 16, r.centery), 6, 0 if on else 1)
            text(s, label, 15, (r.x + 32, r.centery), CREAM if on else MUTED,
                 left=True, kind="mono", shadow=False)
            text(s, clock_str(ship_time(p, m, self.qty)), 14,
                 (r.x + 210, r.centery), mix(TEA, CREAM, 0.2), left=True,
                 kind="mono", shadow=False)
            fee_v = ship_cost(p, self.qty, m)
            text(s, "free" if fee_v <= 0 else "+" + money(fee_v), 14,
                 (r.right - 12, r.centery), GOOD if fee_v <= 0 else EMBER,
                 right=True, kind="mono", shadow=False)
            self.buttons.append(Button(r, "", ("mode", m), "hit"))
            y += 38
        text(s, SHIPPING[self.mode][1].lower() + " - " + SHIPPING[self.mode][4],
             12, (right.x + 112, y - 2), DIM, kind="mono", shadow=False)

        # the total, and the one button that spends money
        total = p.price * self.qty + ship_cost(p, self.qty, self.mode)
        y = body.bottom - 72
        hairline(s, right.x, y - 12, right.right - 10, TEA, 60)
        text(s, "TOTAL", 15, (right.x, y + 8), TEA, kind="mono", shadow=False)
        text(s, money(total), 30, (right.x + 150, y + 14), warm(EMBER, 0.2),
             right=True)
        can = total <= st.money + 1e-6 and not self.full and st.sellable(p)
        note = ("the post is full" if self.full else
                "not enough money yet" if total > st.money else "")
        self.buttons.append(Button((right.right - 230, y - 4, 220, 50),
                                   "PLACE ORDER", ("place", None), "solid",
                                   20, kind="mono", enabled=can, note=note))

    # -- what is in the post ------------------------------------------------
    def draw_orders(self, s, body):
        st = self.state
        if not st.orders:
            text(s, "nothing in the post", 22, (body.centerx, body.y + 60),
                 MUTED, center=True)
            text(s, "the catalogue is the other tab", 14,
                 (body.centerx, body.y + 96), DIM, center=True, kind="mono")
            if st.parcels:
                text(s, f"{len(st.parcels)} parcel"
                        f"{'s' if len(st.parcels) > 1 else ''} already on "
                        f"the mat, waiting to be opened", 15,
                     (body.centerx, body.y + 140), warm(EMBER, 0.2),
                     center=True, kind="mono")
            return
        for i, o in enumerate(st.orders):
            p = BY_PACK[o.pack]
            r = pygame.Rect(body.x, body.y + i * 76, body.w, 68)
            panel(s, r, shade(SCREEN_HI, 0.95), shade(SCREEN_HI, 1.4),
                  radius=8, shadow=False)
            text(s, f"#{o.num}", 16, (r.x + 14, r.y + 10), TEA, kind="mono")
            text(s, (f"{o.qty} x " if o.qty > 1 else "") + p.name, 19,
                 (r.x + 86, r.y + 8), CREAM)
            stage, words = o.stage()
            text(s, words, 13, (r.x + 86, r.y + 36), MUTED, kind="mono",
                 shadow=False)
            br = pygame.Rect(r.x + 420, r.y + 30, 380, 9)
            bar(s, br, 1.0 - o.left / max(0.001, o.total), EMBER,
                shade(SCREEN_HI, 1.3))
            for k in range(4):
                cx = br.x + br.w * (k + 1) / 4 - 2
                pygame.draw.circle(s, EMBER if k <= stage else DIM,
                                   (int(cx), br.centery), 4)
            text(s, SHIPPING[o.mode][1], 12, (r.x + 420, r.y + 12), DIM,
                 kind="mono", shadow=False)
            text(s, clock_str(o.left), 20, (r.right - 16, r.y + 22),
                 warm(CREAM, 0.1), right=True, kind="mono")
            text(s, "paid " + money(o.paid), 12, (r.right - 16, r.y + 46),
                 DIM, right=True, kind="mono", shadow=False)
        if self.full:
            text(s, "that is everything the post will carry at once", 14,
                 (body.centerx, body.bottom - 30), shade(BAD, 1.0),
                 center=True, kind="mono")

    # -- the club -----------------------------------------------------------
    def draw_club(self, s, body):
        st = self.state
        text(s, "THE DELIVERY CLUB", 24, (body.x, body.y), warm(CREAM, 0.2))
        paragraph(s, "Four parcels is what one round will carry. Membership "
                     "is a one-off, and each one is worth another parcel on "
                     "the round - which is the only thing in this shop that "
                     "money cannot otherwise buy.", 14,
                  (body.x, body.y + 34), MUTED, body.w - 20, 4, kind="mono")
        wdt = (body.w - 40) // 3
        for i, (price, name, blurb) in enumerate(CLUB):
            r = pygame.Rect(body.x + i * (wdt + 20), body.y + 120, wdt, 250)
            joined = st.club > i
            nxt = st.club == i
            panel(s, r, mix(SCREEN_HI, EMBER, 0.14 if joined else 0.03),
                  shade(EMBER, 0.8) if joined else shade(SCREEN_HI, 1.4),
                  radius=10, shadow=False)
            text(s, name, 22, (r.centerx, r.y + 18), warm(CREAM, 0.2),
                 center=True, max_w=r.w - 20)
            text(s, f"parcel {MAX_IN_TRANSIT + i + 1}", 13,
                 (r.centerx, r.y + 48), TEA, center=True, kind="mono")
            paragraph(s, blurb, 13, (r.x + 16, r.y + 80), MUTED, r.w - 32, 4,
                      kind="mono", center=True)
            text(s, money(price), 28, (r.centerx, r.y + 160),
                 warm(EMBER, 0.2), center=True)
            br = pygame.Rect(r.x + 24, r.bottom - 54, r.w - 48, 38)
            if joined:
                text(s, "JOINED", 17, br.center, GOOD, center=True,
                     kind="mono")
            else:
                self.buttons.append(Button(
                    br, "JOIN", ("club", None), "solid", 17, kind="mono",
                    enabled=nxt and st.money >= price,
                    note="" if nxt else "one at a time"))


# ---------------------------------------------------------------------------
# OPENING A PARCEL
#
# The best thirty seconds in the game, so it is the one part that is
# allowed to take its time: the tape, the lid, the cards face down, and
# then whatever was in there. A parcel of five cards gets big cards; a
# standing order of seventy-five gets a sheet of small ones, because
# flipping seventy-five cards one at a time is not a ritual, it is a job.
# ---------------------------------------------------------------------------
def deal_grid(n, area):
    """Where the cards go, and how big they are, for any size of parcel."""
    best = None
    for cols in range(1, 13):
        rows = (n + cols - 1) // cols
        cw = (area.w - (cols + 1) * 14) / cols
        ch = (area.h - (rows + 1) * 16) / rows
        w2 = min(cw, ch / 1.4, 184)
        if w2 < 44:
            continue
        if best is None or w2 > best[0]:
            best = (w2, cols, rows)
    if best is None:
        best = (44, 12, (n + 11) // 12)
    cw, cols, rows = best
    ch = cw * 1.4
    gx = area.centerx - (cols * cw + (cols - 1) * 14) / 2
    gy = area.centery - (rows * ch + (rows - 1) * 16) / 2
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        out.append(pygame.Rect(round(gx + c * (cw + 14)),
                               round(gy + r * (ch + 16)),
                               round(cw), round(ch)))
    return out


KIND_WORDS = {"new": ("NEW", GOOD), "level": ("LEVEL UP", LAMP),
              "dupe": ("+1", TEA), "maxed": ("RETIRED", LAMP)}


class OpenMixin:
    def draw_open(self, s):
        st = self.state
        self.draw_room(s)
        del self.buttons[:]
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 206))
        s.blit(dim, (0, 0))
        pack = BY_PACK[self.open_pack_key]
        glow(s, (W // 2, 330), 420, mix(LAMP, EMBER, 0.5), 0.16)

        title = pack.name + (f"  x{self.open_qty}" if self.open_qty > 1 else "")
        text(s, title, 30, (W // 2, 40), warm(CREAM, 0.2), center=True)

        if not self.cut:
            text(s, "cut the tape", 17, (W // 2, 82), TEA, center=True,
                 kind="mono")
            pr = pygame.Rect(W // 2 - 190, 180, 380, 300)
            bob = math.sin(self.t * 2.0) * 4
            pr.y += int(bob)
            draw_parcel(s, pr, seed=self.open_qty, num=0)
            self.buttons.append(Button(pr, "", ("cut", None), "hit"))
            if pr.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(s, mix(EMBER, LAMP, 0.4), pr, width=2,
                                 border_radius=5)
            self.buttons.append(Button((W // 2 - 110, 520, 220, 46),
                                       "CUT THE TAPE", ("cut", None), "solid",
                                       19, kind="mono"))
            self.buttons.append(Button((W // 2 - 110, 580, 220, 28),
                                       "leave it for now", ("leave", None),
                                       "link", 15, kind="mono", colour=TEA))
            return

        area = pygame.Rect(90, 108, W - 180, 500)
        rects = deal_grid(len(self.pulls), area)
        dealt = int(self.deal * len(self.pulls) * 1.8) + 1
        for i, (p, r) in enumerate(zip(self.pulls, rects)):
            if i >= dealt:
                continue
            if i < self.flipped:
                card = self.state.cards.get(p.breed.key)
                pop = 1.0
                if i == self.flipped - 1:
                    pop = 1.0 + 0.06 * max(0.0, math.sin(self.t * 9) * 0.4)
                rr = r.inflate(int(r.w * (pop - 1)), int(r.h * (pop - 1)))
                if p.breed.rarity >= R_RARE:
                    glow(s, rr.center, int(rr.w * 0.9),
                         rarity_colour(p.breed.rarity), 0.22)
                draw_card(s, rr, p.breed, p.level,
                          card.dupes if card else 0,
                          maxed=bool(card and card.maxed))
                word, col = KIND_WORDS[p.kind]
                if p.kind == "dupe" and card and card.maxed:
                    word, col = KIND_WORDS["maxed"]
                lab = word
                if p.kind == "level":
                    lab = f"LEVEL {p.level}"
                elif p.kind == "dupe" and card and not card.maxed:
                    lab = f"+1  {card.dupes}/{dupes_for(card.level)}"
                text(s, lab, max(11, min(15, r.w // 10)),
                     (rr.centerx, rr.bottom + 10), col, center=True,
                     kind="mono")
                if p.sub:
                    text(s, "substituted", 10, (rr.centerx, rr.bottom + 26),
                         DIM, center=True, kind="mono", shadow=False)
            else:
                draw_card_back(s, r, self.t)
                self.buttons.append(Button(r, "", ("flip", i), "hit"))

        left = len(self.pulls) - self.flipped
        if left:
            self.buttons.append(Button((W // 2 - 230, H - 86, 210, 48),
                                       "FLIP ONE", ("flip", self.flipped),
                                       "plain", 18, kind="mono"))
            self.buttons.append(Button((W // 2 + 20, H - 86, 210, 48),
                                       f"FLIP ALL {left}", ("flipall", None),
                                       "solid", 18, kind="mono"))
        else:
            news = sum(1 for p in self.pulls if p.kind == "new")
            ups = sum(1 for p in self.pulls if p.kind == "level")
            bits = []
            if news:
                bits.append(f"{news} new")
            if ups:
                bits.append(f"{ups} level{'s' if ups > 1 else ''}")
            bits.append(f"{len(self.pulls)} cards")
            text(s, "   ".join(bits), 17, (W // 2, H - 104), TEA,
                 center=True, kind="mono")
            if st.parcels:
                self.buttons.append(Button((W // 2 - 300, H - 86, 280, 48),
                                           "INTO THE BINDER", ("done", None),
                                           "plain", 18, kind="mono"))
                self.buttons.append(Button(
                    (W // 2 + 20, H - 86, 280, 48),
                    f"OPEN THE NEXT ({len(st.parcels)})", ("next", None),
                    "solid", 18, kind="mono"))
            else:
                self.buttons.append(Button((W // 2 - 150, H - 86, 300, 48),
                                           "INTO THE BINDER", ("done", None),
                                           "solid", 19, kind="mono"))


# ---------------------------------------------------------------------------
# THE BINDER
# ---------------------------------------------------------------------------
class BinderMixin:
    def draw_binder(self, s):
        st = self.state
        s.fill(INK)
        for y in range(0, H, 6):           # the table, under the binder
            pygame.draw.rect(s, mix(WOOD_LO, WOOD, (y / H) ** 0.8),
                             (0, y, W, 6))
        glow(s, (420, 180), 460, mix(LAMP, EMBER, 0.4), 0.18)
        book = pygame.Rect(40, 24, W - 80, H - 48)
        panel(s, book, mix(RUG, WOOD, 0.45), shade(RUG, 1.2), radius=12)
        inner = book.inflate(-26, -26)
        panel(s, inner, mix(DEEP, WOOD, 0.35), shade(TEA, 0.4), radius=8,
              shadow=False)

        text(s, "THE BINDER", 26, (inner.x + 20, inner.y + 12),
             warm(CREAM, 0.2))
        text(s, f"{st.owned} of {len(BREEDS)} breeds    "
                f"{st.retired} retired    {rate(st.income)}", 15,
             (inner.right - 20, inner.y + 22), TEA, right=True, kind="mono")
        hairline(s, inner.x + 20, inner.y + 46, inner.right - 20, TEA, 60)

        # The whole collection on one spread. Paging a binder of
        # twenty-four is a page turn to look at six cats, which is not
        # what a binder is for.
        area = pygame.Rect(inner.x + 20, inner.y + 62, inner.w - 40, 520)
        cols, gap = 8, 14
        cw = (area.w - (cols - 1) * gap) // cols
        ch = int(cw * 1.4)
        gx = area.centerx - (cols * cw + (cols - 1) * gap) // 2
        for i, b in enumerate(BREEDS):
            r, c = divmod(i, cols)
            rect = pygame.Rect(gx + c * (cw + gap), area.y + r * (ch + 16),
                               cw, ch)
            card = st.cards.get(b.key)
            if card:
                draw_card(s, rect, b, card.level, card.dupes, card.maxed)
            else:
                draw_unknown(s, rect, b)
            self.buttons.append(Button(rect, "", ("pick", b.key), "hit"))
            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(s, mix(EMBER, LAMP, 0.3), rect.inflate(6, 6),
                                 width=2, border_radius=8)

        left = [b for b in BREEDS if b.key not in st.cards]
        if st.complete:
            note = "every breed retired - the catalogue has nothing left"
        elif left:
            note = (f"{len(left)} still to find, the rarest of them a "
                    f"{rarity_name(max(b.rarity for b in left)).lower()}")
        else:
            note = (f"{len(BREEDS) - st.retired} still to take to level 10")
        text(s, note, 15, (inner.centerx, inner.bottom - 36), TEA,
             center=True, kind="mono")
        self.buttons.append(Button((inner.x + 20, inner.bottom - 52, 190, 34),
                                   "< back to the room", ("scene", "room"),
                                   "plain", 15, kind="mono"))
        self.buttons.append(Button((inner.right - 210, inner.bottom - 52, 190,
                                    34), "the catalogue >", ("scene", "shop"),
                                   "plain", 15, kind="mono"))
        if self.pick:
            self.draw_detail(s, BY_KEY[self.pick])

    def draw_detail(self, s, b):
        st = self.state
        card = st.cards.get(b.key)
        # The cards behind this are still click targets unless they are
        # taken away, and a click meant for the dark edge of the screen
        # would quietly pick a different cat.
        del self.buttons[:]
        self.buttons.append(Button((0, 0, W, H), "", ("pick", self.pick),
                                   "hit"))
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 200))
        s.blit(dim, (0, 0))
        r = pygame.Rect(W // 2 - 380, H // 2 - 210, 760, 420)
        acc = rarity_colour(b.rarity)
        panel(s, r, mix(DEEP, acc, 0.06), shade(acc, 0.6), radius=12)
        glow(s, (r.x + 150, r.centery), 220, acc, 0.14)
        cr = pygame.Rect(r.x + 36, r.centery - 148, 212, 296)
        if card:
            draw_card(s, cr, b, card.level, card.dupes, card.maxed)
        else:
            draw_unknown(s, cr, b)

        x = cr.right + 36
        text(s, b.name, 34, (x, r.y + 30), warm(CREAM, 0.2))
        text(s, rarity_name(b.rarity), 15, (x, r.y + 74), acc, kind="mono")
        text(s, "from " + b.origin, 14, (x + 150, r.y + 74), MUTED,
             kind="mono", shadow=False)
        paragraph(s, b.note, 16, (x, r.y + 104), mix(TEA, CREAM, 0.35),
                  r.right - x - 40, 5)
        y = r.y + 170
        hairline(s, x, y - 10, r.right - 40, TEA, 60)
        if card:
            text(s, f"LEVEL {card.level}", 26, (x, y), warm(CREAM, 0.1))
            if card.maxed:
                text(s, "retired - the shop will not send another", 14,
                     (x, y + 36), LAMP, kind="mono", shadow=False)
            else:
                need = dupes_for(card.level)
                br = pygame.Rect(x, y + 40, 300, 12)
                bar(s, br, card.dupes / need, acc, shade(DEEP, 1.6))
                text(s, f"{card.dupes} of {need} duplicates to level "
                        f"{card.level + 1}", 13, (x, y + 62), MUTED,
                     kind="mono", shadow=False)
            text(s, "earning " + rate(b.rate_at(card.level)), 16,
                 (x, y + 92), EMBER, kind="mono")
            if not card.maxed:
                text(s, f"at level 10: {rate(b.rate_at(MAX_LEVEL))}", 13,
                     (x + 200, y + 94), DIM, kind="mono", shadow=False)
            text(s, f"{card.pulled} copies pulled", 13, (x, y + 118), DIM,
                 kind="mono", shadow=False)
        else:
            text(s, "NOT IN THE BINDER", 24, (x, y), shade(TEA, 0.8))
            text(s, f"{rarity_name(b.rarity).lower()} - look in a pack that "
                    f"sells them", 14, (x, y + 38), MUTED, kind="mono",
                 shadow=False)
            text(s, f"would earn {rate(b.base_rate)} to start", 14,
                 (x, y + 62), DIM, kind="mono", shadow=False)
        self.buttons.append(Button((r.right - 130, r.bottom - 54, 104, 36),
                                   "CLOSE", ("pick", self.pick), "plain", 15,
                                   kind="mono"))



# ---------------------------------------------------------------------------
# THE TWO OVERLAYS
#
# A pause card, which is also where the rules are written down, and an
# ending, which is the only screen in the game you cannot get back to.
# ---------------------------------------------------------------------------
RULES = (
    ("the laptop", "Order packs. It is the only way cards come into the "
                   "room, and slow post is free."),
    ("duplicates", "Two of a breed take it to level 2, four more to 3, "
                   "six to 4, and so on by twos."),
    ("every level", "Better paper, a brighter frame, and a cat in better "
                    "condition. A collar at 4, a tag at 7, a bell at 10."),
    ("level 10", "The breed retires. The shop takes it off the page and "
                 "will never send it again."),
    ("the post", "Four parcels at a time. The delivery club is the only "
                 "thing that raises it."),
    ("the flat", "Three rooms: the hall where the post lands, the desk, "
                 "and the cat room. A and D, or click the names."),
    ("the cats", "The ones you have taken furthest take the best spots in "
                 "them, and they earn whether you watch or not."),
)


class MenuMixin:
    def draw_menu(self, s):
        self.draw_room(s)
        del self.buttons[:]
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 206))
        s.blit(dim, (0, 0))
        st = self.state
        r = pygame.Rect(W // 2 - 330, 68, 660, 624)
        panel(s, r, mix(DEEP, WOOD, 0.3), shade(TEA, 0.5), radius=12)
        glow(s, (r.centerx, r.y + 150), 300, mix(LAMP, EMBER, 0.5), 0.12)
        text(s, "CAT CATALOGUE", 36, (r.centerx, r.y + 26), warm(CREAM, 0.2),
             center=True)
        text(s, "a dim room, a warm lamp, and a parcel on the way", 15,
             (r.centerx, r.y + 70), TEA, center=True, kind="mono")
        hairline(s, r.x + 40, r.y + 100, r.right - 40, TEA, 70)

        y = r.y + 112
        for name, line in RULES:
            text(s, name, 16, (r.x + 36, y), warm(EMBER, 0.15), kind="mono",
                 max_w=140)
            paragraph(s, line, 14, (r.x + 186, y), mix(TEA, CREAM, 0.3),
                      r.w - 230, 4, kind="mono")
            y += 52
        hairline(s, r.x + 40, y - 4, r.right - 40, TEA, 70)

        y += 10
        text(s, "L laptop   B binder   O open a parcel   SPACE flip   "
                "M music   S sound   F11 full screen", 13,
             (r.centerx, y), DIM, center=True, kind="mono", shadow=False,
             max_w=r.w - 70)
        y += 26
        stats = (f"{clock_str(st.played)} at the desk",
                 f"{st.packs_opened} parcels opened",
                 f"{st.cards_pulled} cards",
                 f"{money(st.spent)} spent")
        text(s, "    ".join(stats), 14, (r.centerx, y), MUTED, center=True,
             kind="mono", shadow=False)

        self.buttons.append(Button((r.centerx - 250, r.bottom - 76, 150, 44),
                                   "MUSIC " + ("ON" if st.music else "OFF"),
                                   ("music", None), "plain", 16, kind="mono"))
        self.buttons.append(Button((r.centerx - 86, r.bottom - 76, 150, 44),
                                   "SOUND " + ("ON" if st.sound else "OFF"),
                                   ("sound", None), "plain", 16, kind="mono"))
        self.buttons.append(Button((r.centerx + 100, r.bottom - 76, 150, 44),
                                   "CLOSE", ("scene", "room"), "solid", 17,
                                   kind="mono"))
        self.buttons.append(Button((r.centerx - 70, r.bottom - 26, 140, 22),
                                   "quit the game", ("quit", None), "link",
                                   14, kind="mono", colour=MUTED))

    def draw_end(self, s):
        self.draw_room(s)
        del self.buttons[:]
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 190))
        s.blit(dim, (0, 0))
        st = self.state
        r = pygame.Rect(W // 2 - 340, 120, 680, 500)
        panel(s, r, mix(DEEP, WOOD, 0.34), mix(LAMP, EMBER, 0.4), radius=12)
        glow(s, (r.centerx, r.centery), 340, mix(LAMP, EMBER, 0.55), 0.14)
        text(s, "THE BINDER IS FULL", 38, (r.centerx, r.y + 34),
             warm(CREAM, 0.25), center=True)
        paragraph(s,
                  "Twenty-four breeds, every one of them taken to level ten "
                  "and retired. The catalogue has nothing left to send you: "
                  "every line on the page is withdrawn, and the laptop can "
                  "be shut.",
                  17, (r.x + 56, r.y + 96), mix(TEA, CREAM, 0.4), r.w - 112,
                  7)
        paragraph(s,
                  "The cats stay where they are. They go on earning, and "
                  "there is now nothing left to spend it on, which is a "
                  "fair description of a finished collection.",
                  15, (r.x + 56, r.y + 196), MUTED, r.w - 112, 6, kind="mono")
        hairline(s, r.x + 56, r.y + 282, r.right - 56, TEA, 70)
        rows = ((f"{clock_str(st.played)}", "at the desk"),
                (f"{st.packs_opened}", "parcels opened"),
                (f"{st.cards_pulled}", "cards pulled"),
                (money(st.spent), "spent on the post"))
        for i, (big, small) in enumerate(rows):
            x = r.centerx + (i - 1.5) * 150
            text(s, big, 24, (x, r.y + 304), warm(EMBER, 0.2), center=True,
                 max_w=124)
            text(s, small, 12, (x, r.y + 336), MUTED, center=True,
                 kind="mono", shadow=False)
        self.buttons.append(Button((r.centerx - 130, r.bottom - 76, 260, 48),
                                   "SIT IN THE ROOM", ("scene", "room"),
                                   "solid", 19, kind="mono"))


class Game(ShopMixin, OpenMixin, BinderMixin, MenuMixin, GameBase):
    """The screens, bolted onto the loop that owns the state."""


# ---------------------------------------------------------------------------
def main():
    init_audio()
    pygame.init()
    pygame.display.set_caption("Cat Catalogue")
    screen = pygame.display.set_mode((W, H))
    Game(screen).run()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
