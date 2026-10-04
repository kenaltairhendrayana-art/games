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
binder is thirty-six retired breeds and a shop with nothing left to sell.

Nothing ships beside this file. Every cat, every card, every parcel and
the website you order from are drawn here in code, and the music and the
sounds are synthesised at runtime.

Requirements: pygame-ce (or pygame)  ->  pip install pygame-ce
Run:                                     python cat_catalogue.py

THE FLAT
  Three rooms, and you walk between them.

  THE HALL        the front door, the mat, and whatever the post has left
  THE DESK        the lamp, the laptop you order from, and the binder
  THE CAT ROOM    twice as wide as the window, and where they live

  The ten cats you have taken furthest live in the cat room and run
  their own day in it: they cross the floor, climb the tree, eat, drink,
  play, scratch, wash, prowl and sleep. Which of those they do is their
  BREED - a Bengal hunts the ball, a Persian finds the warmest square
  foot, a Maine Coon is never far from the bowls. Click one to find out
  who it is. The rest sleep on the furniture in the other two rooms, and
  all of them earn wherever you are standing.

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
    # The rates were set when the book held twenty-four breeds. At a
    # hundred they added up to two thousand a second and the back half of
    # the game was a player sitting on five million pounds with nothing
    # that could absorb it, so everything was cut to a third.
    #
    # Then the book went to a hundred and eighty-eight across four
    # series, and most of the new cats went in at the TOP of the ladder
    # to fill out the thin tiers - which bought x1.68 the income for
    # x1.24 the cards, and put the player back on nearly three million
    # by the end of a run, so everything was cut to 0.6 of what it was.
    #
    # That was too far at the top of the shop: a box at fifty-two thousand
    # is most of ten minutes of waiting before you can press the button,
    # and waiting to press a button is not the same as a decision. Back up
    # to 0.8, which is a third more a second than 0.6 was.
    ("COMMON",    (171, 152, 126), 0.0128),
    ("UNCOMMON",  (126, 171, 131), 0.044),
    ("RARE",      (116, 150, 208), 0.120),
    ("EXOTIC",    (124, 232, 236), 0.200),
    ("PEDIGREE",  (184, 132, 208), 0.320),
    ("CHAMPION",  (204, 74, 92),   0.504),
    ("LEGEND",    (240, 178, 86),  0.800),
    ("HEIRLOOM",  (172, 236, 88),  1.080),
    ("FOUNDATION", (72, 214, 170), 1.440),
    ("ARCHIVE",   (236, 236, 148), 2.080),
    ("UNLISTED",  (206, 214, 228), 0.680),
    ("CONVENTION", (238, 70, 174),  1.200),
)
(R_COMMON, R_UNCOMMON, R_RARE, R_EXOTIC, R_PEDIGREE, R_CHAMPION, R_LEGEND,
 R_HEIRLOOM, R_FOUNDATION, R_ARCHIVE, R_UNLISTED, R_EXPO) = range(12)
SOLD_RARITIES = 10         # the catalogue stocks the first ten of them

MAX_LEVEL = 10


def rarity_name(r):
    return RARITY[r][0]


def a_rarity(r):
    """"a legend", but "an exotic" - two of the tiers start with a vowel
    now and nothing on the ladder used to."""
    word = RARITY[r][0].lower()
    return ("an " if word[0] in "aeiou" else "a ") + word


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


def quantum(income):
    """How big a step the room's balance should move in.

    Rounding by MAGNITUDE is not enough: a balance of six thousand
    rounded to the nearest hundred still moves every two seconds when
    the cats are earning fifty a second, which is the thing that was
    hard to look at. So the step is set by the income instead - about
    four seconds of earnings, snapped to a 1-2-5 ladder so the numbers
    themselves stay tidy - and the display then changes at the same
    gentle rate whatever point of the game you are at.
    """
    step = max(1.0, income * 4.0)
    mag = 10.0 ** math.floor(math.log10(step))
    for m in (1, 2, 5):
        if step <= mag * m:
            return mag * m
    return mag * 10


def money_soft(v):
    """Money for the corner of the screen rather than for a checkout.

    A balance printed to the dollar at sixty frames a second is a slot
    machine: every digit moves, all the time, and the room stops being a
    quiet room. Above a thousand this rounds to three characters, so the
    number changes about once every twenty seconds and you can still see
    at a glance whether an Estate Lot is in reach. Prices and totals on
    the website keep using `money`, because that is where it matters to
    the dollar.
    """
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 10_000:
        return f"${v / 1000:.0f}k"
    if v >= 1_000:
        return f"${v / 1000:.1f}k"
    if v >= 100:
        return "$" + f"{int(v / 10) * 10:,}"   # to the nearest ten
    return "$" + f"{int(v):,}"


def rate_soft(v):
    """The same for a rate: two significant figures and no twitching."""
    if v >= 1000:
        return f"{v / 1000:.1f}k/s"
    if v >= 100:
        return f"{v:.0f}/s"
    if v >= 10:
        return f"{v:.0f}/s"
    if v >= 1:
        return f"{v:.1f}/s"
    return f"{v:.2f}/s"


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
# Thirty-six of them, and the thing that matters here is that they differ
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
# ---------------------------------------------------------------------------
# COATS
#
# A breed is not one colour. Each one comes in two to four coats, and
# which one turned up in the parcel is part of what you pulled: the card
# keeps the coat it arrived in, and the binder remembers every coat of
# that breed you have ever seen, which is a second collection inside the
# first one.
#
# A coat is a straight substitution of three colours - the coat, its
# markings and the belly - because the PATTERN belongs to the breed and
# must survive the recolour: a silver Bengal is still rosetted, and a
# chocolate Siamese is still pointed.
#
# And then there is the shiny. One card in a hundred and fifty comes out
# of the pack in a colour the catalogue does not list and will not
# explain, worth a quarter again in income and a permanent mark on the
# card. It is the same joke Pokemon has been running since 1999, and it
# works for the same reason: the odds are long enough that it is a story
# and short enough that it happens.
# ---------------------------------------------------------------------------
COAT_FAMILY = {
    "silver":    ((170, 172, 178), (104, 106, 114), (216, 218, 224)),
    "red":       ((200, 140, 78), (144, 90, 46), (234, 208, 178)),
    "black":     ((64, 60, 60), (40, 38, 40), (98, 94, 94)),
    "blue":      ((124, 134, 148), (94, 104, 118), (168, 178, 192)),
    "cream":     ((234, 216, 186), (206, 186, 152), (246, 236, 216)),
    "lilac":     ((170, 154, 158), (128, 112, 118), (208, 196, 198)),
    "chocolate": ((120, 86, 64), (74, 50, 36), (180, 148, 120)),
    "white":     ((244, 240, 232), (222, 218, 210), (250, 248, 244)),
    "charcoal":  ((86, 84, 88), (52, 50, 54), (126, 124, 128)),
    # ivory has to be a long way from white or the two of them are the
    # same cat with two names on it
    "ivory":     ((226, 208, 170), (192, 172, 134), (242, 230, 204)),
    "brown":     ((128, 100, 74), (78, 58, 42), (186, 162, 134)),
    # these three exist as shiny colours too; a coat family is a colour,
    # not a tier, and a breed may perfectly well come in one of them
    "fawn":      ((212, 186, 154), (164, 132, 100), (238, 222, 200)),
    "golden":    ((218, 178, 104), (158, 116, 52), (242, 222, 180)),
    # no "lavender" here: it is a shiny colour, and as an ordinary coat
    # it sits on top of both lilac and silver
    "cinnamon":  ((182, 122, 78), (124, 72, 42), (220, 180, 142)),
    "gold":      ((214, 176, 108), (150, 112, 56), (238, 218, 180)),
    "peach":     ((232, 192, 166), (190, 142, 112), (244, 222, 206)),
    "champagne": ((222, 202, 172), (170, 142, 110), (238, 226, 206)),
    "blue mink": ((160, 162, 170), (112, 114, 124), (198, 200, 206)),
    "blue point": ((226, 224, 226), (118, 128, 146), (240, 240, 242)),
    "black and white": ((60, 58, 60), (240, 238, 234), (244, 242, 238)),
    "white and black": ((240, 238, 234), (60, 58, 60), (246, 244, 242)),
    "grey and white": ((132, 132, 134), (240, 238, 234), (244, 242, 240)),
    "white and red": ((240, 238, 232), (192, 118, 70), (246, 244, 240)),
    "dilute calico": ((238, 234, 228), (150, 156, 168), (246, 244, 240)),
    "grey":      ((134, 134, 132), (82, 82, 84), (192, 192, 190)),
    "smoke":     ((98, 94, 100), (58, 56, 62), (152, 148, 154)),
}
SHINY_IN = 150               # one pack card in this many
SHINY_BONUS = 1.25           # ... and it earns this much again


# The shiny coats. Turning a coat round the colour wheel gave a cat that
# was emerald or magenta, which is a different game: these are real cat
# colours, every one of them something you could actually meet, and rare
# enough that nobody would expect one in a paper sack. What marks a shiny
# out is not that it is impossible - it is the sparkle, the gold frame,
# and the fact that you have opened a hundred and fifty cards without
# seeing one.
SHINY_COATS = (
    ("snow",         (246, 245, 243), (210, 214, 222), (252, 252, 251)),
    ("silver smoke", (178, 180, 186), (88, 90, 98), (226, 228, 232)),
    ("golden",       (218, 178, 104), (158, 116, 52), (242, 222, 180)),
    ("cinnamon",     (184, 120, 76), (124, 70, 40), (222, 180, 140)),
    ("fawn",         (212, 186, 154), (164, 132, 100), (238, 222, 200)),
    ("chocolate",    (116, 80, 56), (72, 46, 30), (176, 144, 114)),
    ("lavender",     (186, 172, 180), (134, 120, 132), (220, 210, 216)),
    ("ebony",        (56, 54, 58), (34, 33, 36), (92, 90, 96)),
    ("amber",        (202, 150, 76), (140, 92, 38), (232, 200, 152)),
    ("blue cream",   (160, 164, 178), (208, 172, 138), (212, 214, 222)),
)


def _colour_gap(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


_shiny_of = {}


def shiny_coat(breed):
    """Which rare colour THIS breed turns up in, and its name.

    Fixed per breed, so a shiny Bengal is always the same shiny Bengal
    and people can tell each other what to look for. Never a colour the
    breed already comes in, or the rarest card in the game would look
    like the second cheapest - and spread evenly across the ten, because
    taking them in hash order gave five snows and five ebonies.
    """
    if not _shiny_of:
        used = {row[0]: 0 for row in SHINY_COATS}
        for i, b in enumerate(ALL_BREEDS):
            # Eligibility is a question about COLOUR, not about names.
            # Checking the names let a Maine Coon whose coats include
            # "black" be given the shiny called "ebony", and the two of
            # them were the same cat.
            own = [coat_colours(b, k) for k in range(len(b.coats))]
            best = None
            for j, (name, c, m, bl) in enumerate(SHINY_COATS):
                gap = min(_colour_gap(c, o[0]) + _colour_gap(m, o[1]) * 0.5
                          for o in own)
                # A breed with four coats of its own already covers most
                # of the space, so the bar for "a different colour" has
                # to be one a pixel comparison agrees with rather than
                # one that leaves snow as the only answer for half the
                # book. `cat_test.py coats` is the arbiter.
                if gap < 72:
                    continue
                rank = (used[name], -int(gap // 40),
                        (j - i * 3) % len(SHINY_COATS))
                if best is None or rank < best[0]:
                    best = (rank, name, (c, m, bl))
            if best is None:                 # nothing clear: take the
                far = max(                   # furthest away there is
                    SHINY_COATS,
                    key=lambda row: min(_colour_gap(row[1], o[0])
                                        for o in own))
                best = ((0, 0), far[0], (far[1], far[2], far[3]))
            used[best[1]] += 1
            _shiny_of[b.key] = (best[1], best[2])
    return _shiny_of[breed.key]


def coat_colours(breed, variant=0, shiny=False):
    """The three colours this card is drawn in."""
    P = breed.look
    base = (P["coat"], P["mark"], P["belly"])
    names = breed.coats
    if 0 < variant < len(names):
        fam = COAT_FAMILY.get(names[variant])
        if fam:
            base = fam
    if shiny:
        return shiny_coat(breed)[1]
    return base


def coat_name(breed, variant=0, shiny=False, full=False):
    if shiny:
        return "shiny " + shiny_coat(breed)[0] if full else "shiny"
    names = breed.coats
    return names[variant] if 0 <= variant < len(names) else names[0]


# What a cat is LIKE, which is a different question from what it looks
# like. Nine temperaments; every breed has one, and it decides what that
# cat spends its day doing in the cat room, how fast it crosses the
# floor, how long it stays put, and which bit of furniture it makes for
# when it has the choice.
#
#   acts    how often it picks each thing to do, relative to the others
#   likes   the furniture it heads for first
#   speed   how fast it crosses a room
#   stay    how long it sticks at one thing, in seconds
TEMPERS = {
    "sleeper": dict(
        label="sleeps through most of it",
        acts={"sleep": 7, "loaf": 3, "groom": 2, "watch": 1, "sit": 1,
              "scratch": 1, "drink": 1, "eat": 1, "hide": 2, "sniff": 1},
        likes=("bed", "warm", "perch"), speed=0.62, stay=(22, 50)),
    "hunter": dict(
        label="hunts everything that moves",
        acts={"play": 7, "prowl": 4, "watch": 2, "eat": 1, "sleep": 1,
              "scratch": 3, "drink": 1, "climb": 2, "chatter": 3, "hide": 1},
        likes=("toy", "floor", "perch", "bird"), speed=1.35, stay=(7, 16)),
    "climber": dict(
        label="will be found somewhere high",
        acts={"watch": 6, "loaf": 3, "prowl": 2, "sleep": 2, "play": 1,
              "scratch": 2, "eat": 1, "drink": 1, "climb": 5, "chatter": 2},
        likes=("perch", "wall"), speed=1.15, stay=(12, 28)),
    "glutton": dict(
        label="is never far from the bowls",
        acts={"eat": 5, "drink": 2, "sleep": 4, "loaf": 3, "prowl": 1,
              "scratch": 1, "groom": 1, "hide": 1, "sniff": 2},
        likes=("food", "water", "bed"), speed=0.85, stay=(10, 24)),
    "groomer": dict(
        label="washes, and washes again",
        acts={"groom": 6, "loaf": 3, "watch": 2, "sleep": 2, "sit": 2,
              "scratch": 1, "drink": 1, "eat": 1, "hide": 1, "chatter": 1, "sniff": 2},
        likes=("perch", "bed"), speed=0.9, stay=(12, 26)),
    "shadow": dict(
        label="keeps to the edges of the room",
        acts={"prowl": 5, "watch": 3, "sleep": 3, "groom": 2,
              "scratch": 2, "eat": 1, "drink": 1, "hide": 4, "climb": 1, "chatter": 1, "sniff": 2},
        likes=("box", "floor", "perch", "tunnel"), speed=1.05,
        stay=(9, 20)),
    "lap": dict(
        label="wants to be where you are",
        acts={"loaf": 5, "sit": 3, "groom": 2, "sleep": 2, "play": 2,
              "scratch": 1, "eat": 1, "drink": 1, "hide": 1, "chatter": 1, "sniff": 2},
        likes=("chair", "bed", "floor"), speed=1.0, stay=(14, 30)),
    "busy": dict(
        label="has a list and is working through it",
        acts={"scratch": 5, "play": 4, "prowl": 3, "eat": 2, "watch": 2,
              "drink": 1, "groom": 1, "climb": 2, "chatter": 2, "sniff": 3},
        likes=("post", "toy", "floor"), speed=1.25, stay=(6, 14)),
    "warmth": dict(
        label="finds the warmest thing in the room",
        acts={"sleep": 5, "loaf": 4, "groom": 2, "watch": 1, "sit": 2,
              "scratch": 1, "eat": 1, "drink": 1, "hide": 2},
        likes=("warm", "bed", "chair"), speed=0.8, stay=(20, 44)),
}


class Breed:
    __slots__ = ("key", "name", "rarity", "origin", "note", "look", "temper",
                 "habit", "coats")

    def __init__(self, key, name, rarity, origin, note, look, temper="lap",
                 habit="", coats=("as listed",)):
        self.key = key
        self.name = name
        self.rarity = rarity
        self.origin = origin
        self.note = note
        self.look = look
        self.temper = temper
        self.habit = habit
        self.coats = coats          # [0] is the one the catalogue lists

    @property
    def temperament(self):
        return TEMPERS[self.temper]

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
    """One breed's look, with the ordinary cat as the default.

          eyeshape="almond")),
    went in, nothing complained, and that breed quietly kept the
    default eyes. At
    a hundred breeds a typo like that is never going to be spotted by
    eye, so it raises.
    """
    look = dict(size=1.0, body=1.0, facew=1.0, faceh=1.0, cheek=1.0, ear=1.0,
                fold=0.0, tuft=0.0, flat=0.0, fluff=0.25, legs=1.0,
                tail="plain", eyeshape="almond", eye=(188, 164, 74),
                earcurl=0.0, collar=None,
                coat=(126, 104, 86), mark=(78, 60, 48), belly=(196, 176, 150),
                pat="tabby", skin=0.0, curl=0.0, nose=(198, 128, 124))
    bad = set(kw) - set(look)
    if bad:
        raise KeyError(f"no such look: {sorted(bad)}")
    look.update(kw)
    return look


BREEDS = (
    # -- COMMON ------------------------------------------------------------
    Breed("dsh", "Domestic Shorthair", R_COMMON, "everywhere",
          "Has three names in this house and answers to none of them.",
          L(coat=(136, 110, 84), mark=(84, 62, 44), belly=(206, 186, 156),
            pat="tabby", eye=(190, 166, 80), body=0.98, facew=1.02,
            ear=1.08, legs=1.06, faceh=1.02),
          "busy",
          "Checks every room in order, then starts again.",
          ("brown tabby", "silver", "red", "black")),
    Breed("dlh", "Domestic Longhair", R_COMMON, "everywhere",
          "A cloud that has learned where the warm spot is.",
          L(fluff=1.0, tail="plume", coat=(150, 118, 86), mark=(92, 64, 46),
            belly=(216, 196, 164), pat="tortie", body=1.04, facew=1.14,
            cheek=1.26, eye=(176, 150, 70), legs=0.78, faceh=0.92),
          "sleeper",
          "Sheds on the one chair nobody is allowed to sit in.",
          ("tortoiseshell", "cream", "blue", "red")),
    Breed("ash", "American Shorthair", R_COMMON, "the United States",
          "Built like a farm gate. Sleeps like one too.",
          L(coat=(150, 148, 142), mark=(84, 84, 82), belly=(206, 204, 198),
            pat="blotched", body=1.16, facew=1.14, cheek=1.2, legs=0.95,
            eye=(196, 174, 86), ear=0.92, fluff=0.2),
          "glutton",
          "Hears a bowl from two rooms away.",
          ("silver tabby", "brown", "blue", "cream")),
    Breed("esh", "European Shorthair", R_COMMON, "the north of Europe",
          "Came in off a cold street and never mentioned it again.",
          L(coat=(126, 126, 124), mark=(70, 70, 72), belly=(190, 190, 188),
            pat="tabby", body=1.0, facew=1.0, faceh=1.0, cheek=1.02,
            eye=(156, 178, 110), ear=1.14, legs=1.0, fluff=0.52),
          "shadow",
          "Sits just outside the lamplight, watching the lamp.",
          ("grey tabby", "red", "silver", "black")),
    Breed("jbt", "Japanese Bobtail", R_COMMON, "Japan",
          "The tail is a pom-pom and the walk is all shoulders.",
          L(tail="pom", coat=(238, 226, 206), mark=(206, 128, 62),
            belly=(246, 238, 222), pat="bicolour", body=0.92, facew=0.94,
            legs=1.12, ear=1.1, eye=(196, 176, 92), fluff=0.22),
          "hunter",
          "Carries the ball about and leaves it in the bowl.",
          ("calico", "red", "black", "cream")),
    Breed("mnx", "Manx", R_COMMON, "the Isle of Man",
          "No tail at all, and absolutely no opinion about it.",
          L(tail="none", coat=(196, 138, 76), mark=(142, 88, 44),
            belly=(230, 206, 176), pat="tabby", body=1.2, facew=1.12,
            cheek=1.16, legs=0.86, fluff=0.34, eye=(190, 160, 72)),
          "lap",
          "Gets in the box. Always the box.",
          ("red", "black", "blue", "silver")),

    Breed("bom", "Bombay", R_COMMON, "Louisville, out of a Burmese",
          "A patent-leather shadow with two copper coins in it.",
          L(coat=(58, 56, 58), mark=(38, 36, 38), belly=(84, 82, 84),
            pat="solid", body=0.96, facew=1.0, faceh=1.04, cheek=0.96,
            ear=1.08, legs=1.16, fluff=0.1, eye=(214, 160, 56),
            eyeshape="round"),
          "shadow",
          "Can only be found by the eyes, and only when it wants to be.",
          ("sable black", "charcoal", "smoke")),
    Breed("mun", "Munchkin", R_COMMON, "Rayville, Louisiana",
          "All of the cat, two thirds of the ground clearance.",
          L(coat=(150, 124, 96), mark=(96, 72, 52), belly=(214, 196, 168),
            pat="tabby", body=1.08, facew=1.02, cheek=1.0, ear=1.06,
            legs=0.46, fluff=0.3, eye=(186, 162, 76)),
          "busy",
          "Cannot reach the counter, and has not stopped trying.",
          ("brown tabby", "silver", "cream", "black")),

    # -- UNCOMMON ----------------------------------------------------------
    Breed("bsh", "British Shorthair", R_UNCOMMON, "Britain",
          "A round grey full stop at the end of the sofa.",
          L(coat=(124, 134, 148), mark=(96, 106, 120), belly=(146, 156, 170),
            pat="solid", body=1.26, facew=1.24, faceh=0.96, cheek=1.3,
            ear=0.84, legs=0.84, fluff=0.3, eye=(214, 150, 60),
            eyeshape="round"),
          "sleeper",
          "Settles into a loaf and holds it like a job.",
          ("british blue", "lilac", "cream", "black")),
    Breed("rbl", "Russian Blue", R_UNCOMMON, "Arkhangelsk",
          "Silver at the tips, so it looks lit even when it is not.",
          L(coat=(126, 142, 156), mark=(154, 170, 184), belly=(150, 166, 180),
            pat="smoke", body=0.86, facew=0.92, cheek=0.84, ear=1.24,
            legs=1.16, fluff=0.54, eye=(126, 188, 136), eyeshape="round"),
          "shadow",
          "Behind the curtain, eyes only, for an hour.",
          ("archangel blue", "silver")),
    Breed("sia", "Siamese", R_UNCOMMON, "Thailand",
          "Will tell you about the door at some length.",
          L(coat=(224, 206, 178), mark=(72, 54, 50), belly=(236, 222, 198),
            pat="point", body=0.86, facew=0.84, faceh=1.1, cheek=0.76,
            ear=1.3, legs=1.14, fluff=0.14, eye=(104, 164, 212),
            eyeshape="almond"),
          "lap",
          "Follows you room to room, narrating the journey.",
          ("seal point", "chocolate", "blue", "lilac")),
    Breed("mcn", "Maine Coon", R_UNCOMMON, "Maine",
          "Takes up two cushions and considers that modest.",
          L(size=1.22, body=1.3, facew=1.1, cheek=1.12, ear=1.22, tuft=1.0,
            fluff=1.0, tail="plume", legs=1.0, coat=(142, 108, 76),
            mark=(86, 58, 40), belly=(214, 192, 158), pat="blotched",
            eye=(188, 158, 72)),
          "glutton",
          "Eats, then sits by the bowl in case of seconds.",
          ("brown tabby", "silver", "black", "red")),
    Breed("rag", "Ragdoll", R_UNCOMMON, "California",
          "Picked up, goes completely liquid. Every time.",
          L(size=1.16, body=1.22, facew=1.06, cheek=0.98, ear=0.96,
            fluff=0.62, tail="plume", legs=1.06, coat=(232, 220, 200),
            mark=(104, 96, 110),
            belly=(242, 234, 218), pat="point", eye=(118, 160, 214),
            eyeshape="round"),
          "lap",
          "Goes completely liquid wherever it is picked up.",
          ("blue point", "chocolate", "lilac", "cream")),
    Breed("sfd", "Scottish Fold", R_UNCOMMON, "Perthshire",
          "Ears folded flat, like it is listening to the floor.",
          L(fold=1.0, ear=0.7, body=1.12, facew=1.2, faceh=0.94, cheek=1.24,
            legs=0.88, fluff=0.42, coat=(144, 134, 124), mark=(92, 84, 78),
            belly=(198, 190, 180), pat="tabby", eye=(206, 160, 76),
            eyeshape="round"),
          "sleeper",
          "Sleeps on its back with its feet in the air.",
          ("grey tabby", "blue", "cream", "red")),

    Breed("cha", "Chartreux", R_UNCOMMON, "a French monastery, they say",
          "Blue, and smiling about something it will not say.",
          L(coat=(118, 132, 142), mark=(92, 104, 114), belly=(158, 172, 182),
            pat="smoke", body=1.16, facew=1.12, faceh=1.04, cheek=1.14,
            ear=1.06, legs=1.04, fluff=0.56, eye=(226, 158, 58),
            eyeshape="round"),
          "sleeper",
          "Sits on the warm side of the room with its feet tucked in.",
          ("monastery blue", "silver", "smoke")),
    Breed("bur", "Burmese", R_UNCOMMON, "Rangoon, by way of San Francisco",
          "A brick wrapped in silk, and about as easy to move.",
          L(coat=(126, 92, 68), mark=(88, 60, 44), belly=(176, 142, 112),
            pat="smoke", body=1.14, facew=1.08, faceh=0.94, cheek=1.1,
            ear=1.0, legs=0.94, fluff=0.14, eye=(216, 176, 64),
            eyeshape="round"),
          "lap",
          "Is on you. Was on you. Will be on you again shortly.",
          ("sable", "blue", "lilac", "silver")),
    Breed("tvn", "Turkish Van", R_UNCOMMON, "the shores of Lake Van",
          "White all over except the cap and the tail, and it swims.",
          L(size=1.18, body=1.26, facew=1.08, faceh=0.92, cheek=1.22,
            ear=0.94, legs=0.92, fluff=0.34, tail="plume",
            coat=(242, 238, 230), mark=(194, 114, 62), belly=(248, 246, 240),
            pat="van", eye=(198, 174, 86)),
          "hunter",
          "Gets in the sink. Turns the tap on. Deals with the consequences.",
          ("auburn van", "cream", "charcoal")),

    # -- RARE --------------------------------------------------------------
    Breed("nfc", "Norwegian Forest", R_RARE, "Norway",
          "Dressed for weather this room will never have.",
          L(size=1.2, body=1.24, facew=1.0, faceh=1.08, ear=1.14, tuft=1.0,
            fluff=1.0, tail="plume", legs=1.04, coat=(58, 52, 52),
            mark=(238, 232, 220), belly=(240, 234, 222), pat="bicolour",
            eye=(150, 184, 110)),
          "climber",
          "Takes the high shelf and surveys the floor.",
          ("black and white", "red", "silver", "charcoal")),
    Breed("ben", "Bengal", R_RARE, "a laboratory in Yuba City",
          "Spotted like something far less comfortable.",
          L(size=1.06, body=1.1, facew=0.98, cheek=0.94, ear=0.9, legs=1.08,
            fluff=0.12, coat=(206, 160, 86), mark=(62, 48, 38),
            belly=(232, 208, 164), pat="spotted", eye=(142, 188, 128),
            eyeshape="almond"),
          "hunter",
          "Has opinions about the ball, and acts on them.",
          ("golden rosette", "silver", "charcoal")),
    Breed("aby", "Abyssinian", R_RARE, "the Nile, allegedly",
          "Ticked coat, so it changes colour as it turns.",
          L(size=0.98, body=1.0, facew=0.92, faceh=1.0, cheek=0.94,
            ear=1.2, legs=1.14, fluff=0.1, coat=(176, 114, 66),
            mark=(96, 56, 34), belly=(206, 152, 104), pat="ticked",
            eye=(206, 164, 70), eyeshape="almond"),
          "climber",
          "Is on top of the thing you just put down.",
          ("ruddy", "red", "blue", "silver")),
    Breed("per", "Persian", R_RARE, "Isfahan",
          "The face of a cat who has just been told something.",
          L(size=1.1, body=1.26, facew=1.3, faceh=0.92, cheek=1.34, ear=0.66,
            flat=1.0, fluff=1.0, tail="plume", legs=0.78,
            coat=(232, 212, 176), mark=(206, 180, 140), belly=(242, 228, 202),
            pat="smoke", eye=(216, 142, 64), eyeshape="round"),
          "sleeper",
          "Picked the warmest square foot and stayed in it.",
          ("cream", "white", "blue", "chocolate")),
    Breed("sph", "Sphynx", R_RARE, "Toronto",
          "Warm to the touch, which is the entire argument for it.",
          L(size=1.0, body=0.84, facew=0.94, faceh=1.06, cheek=0.72,
            ear=1.52, legs=1.1, fluff=0.0, skin=1.0, coat=(206, 160, 148),
            mark=(176, 128, 118), belly=(220, 180, 168), pat="solid",
            eye=(198, 190, 110), eyeshape="almond", nose=(190, 134, 130)),
          "warmth",
          "On the radiator, under a blanket, against a lamp.",
          ("bare pink", "blue", "black", "ivory")),

    Breed("mau", "Egyptian Mau", R_CHAMPION, "the Nile, actually",
          "Spotted on the hair, not the skin. The only one that is.",
          L(size=1.02, body=0.96, facew=0.94, faceh=1.04, cheek=0.9,
            ear=1.12, legs=1.22, fluff=0.1, coat=(168, 170, 174),
            mark=(50, 48, 50), belly=(214, 216, 220), pat="spotted",
            eye=(146, 196, 150), eyeshape="almond"),
          "hunter",
          "Fastest thing in the flat, and it knows the corners.",
          ("silver spotted", "smoke", "chocolate")),
    Breed("acl", "American Curl", R_RARE, "a stray in Lakewood",
          "The ears turn back, as if it has heard something behind it.",
          L(size=1.0, body=1.0, facew=1.04, faceh=1.0, cheek=1.0, ear=1.2,
            earcurl=1.0, legs=1.04, fluff=0.5, tail="plume",
            coat=(206, 176, 136), mark=(142, 108, 72), belly=(234, 216, 188),
            pat="tabby", eye=(176, 184, 108)),
          "groomer",
          "Washes the ears first, and takes a while about it.",
          ("honey tabby", "chocolate", "silver", "cream")),
    Breed("slk", "Selkirk Rex", R_RARE, "a shelter kitten in Montana",
          "A sheep in cat form, and the curls go all the way down.",
          L(size=1.1, body=1.24, facew=1.18, faceh=0.96, cheek=1.22,
            ear=0.88, legs=0.86, fluff=0.96, curl=1.0, tail="plume",
            coat=(198, 186, 174), mark=(150, 138, 128), belly=(226, 218, 208),
            pat="smoke", eye=(200, 168, 72), eyeshape="round"),
          "sleeper",
          "Needs brushing. Does not agree that it needs brushing.",
          ("platinum curl", "cream", "blue", "chocolate")),

    # -- PEDIGREE ----------------------------------------------------------
    Breed("sav", "Savannah", R_CHAMPION, "a serval and a nerve",
          "Legs like a deer. Can reach the top of the bookcase, flat.",
          L(size=1.18, body=0.98, facew=0.86, faceh=1.06, cheek=0.78,
            ear=1.5, legs=1.42, fluff=0.1, coat=(214, 172, 96),
            mark=(44, 38, 34), belly=(234, 212, 168), pat="spotted",
            eye=(188, 180, 96), eyeshape="almond"),
          "climber",
          "Can reach the top of the bookcase, flat-footed.",
          ("golden spotted", "silver", "charcoal")),
    Breed("tan", "Turkish Angora", R_PEDIGREE, "Ankara",
          "Silk, mostly. Sheds it generously onto dark clothing.",
          L(size=1.04, body=0.9, facew=0.9, faceh=1.06, cheek=0.82, ear=1.2,
            fluff=0.9, tail="plume", legs=1.12, coat=(244, 236, 220),
            mark=(226, 214, 196), belly=(250, 244, 232), pat="solid",
            eye=(116, 170, 216), eyeshape="almond"),
          "groomer",
          "Washes one paw for ten minutes, then the other.",
          ("white", "ivory", "blue")),
    Breed("bir", "Birman", R_PEDIGREE, "a temple, by legend",
          "White gloves on all four feet, and it knows.",
          L(size=1.1, body=1.16, facew=1.0, faceh=1.06, cheek=0.96,
            ear=1.02, fluff=0.48, tail="plume", legs=1.08,
            coat=(234, 220, 196), mark=(96, 72, 70), belly=(244, 234, 216),
            pat="gloves", eye=(112, 156, 212), eyeshape="round"),
          "groomer",
          "Keeps the white gloves white. It takes work.",
          ("seal point", "blue", "chocolate", "lilac")),
    Breed("dvx", "Devon Rex", R_PEDIGREE, "a tin mine in Devon",
          "A pixie in a second-hand jumper, two sizes too big.",
          L(size=0.88, body=0.82, facew=1.06, faceh=0.86, cheek=1.1, ear=1.56,
            legs=1.0, fluff=0.3, curl=1.0, coat=(150, 128, 120),
            mark=(104, 86, 80), belly=(196, 178, 168), pat="smoke",
            eye=(176, 188, 120), eyeshape="round"),
          "busy",
          "Into the toy basket, out of it, into it again.",
          ("mouse grey", "black", "cream", "white")),

    Breed("toy", "Toyger", R_PEDIGREE, "a breeder with a tiger in mind",
          "Bred to look like something that could eat it.",
          L(size=1.14, body=1.24, facew=1.12, faceh=0.92, cheek=1.16,
            ear=0.74, legs=0.86, fluff=0.12, coat=(198, 146, 70),
            mark=(44, 34, 28), belly=(226, 192, 140), pat="tabby",
            eye=(190, 150, 62), eyeshape="almond"),
          "hunter",
          "Stalks the hall rug for the practice.",
          ("tiger stripe", "golden", "charcoal")),
    Breed("sgp", "Singapura", R_PEDIGREE, "a drain in Singapore",
          "The smallest of them, with the ears and eyes of a larger cat.",
          L(size=0.80, body=0.86, facew=1.08, faceh=0.96, cheek=0.96,
            ear=1.44, legs=0.94, fluff=0.08, coat=(206, 178, 140),
            mark=(132, 100, 70), belly=(230, 212, 184), pat="ticked",
            eye=(200, 176, 80), eyeshape="round"),
          "climber",
          "Fits in a shoe, sleeps in the shoe, defends the shoe.",
          ("sepia agouti", "fawn", "ivory")),
    Breed("neb", "Nebelung", R_CHAMPION, "Denver, out of a long-haired blue",
          "Mist with a tail on it. Keeps to the people it has chosen.",
          L(size=1.04, body=0.80, facew=0.92, faceh=1.08, cheek=0.80,
            ear=1.38, legs=1.26, fluff=1.0, tail="plume",
            coat=(130, 146, 160), mark=(162, 178, 192), belly=(168, 184, 198),
            pat="smoke", eye=(130, 190, 140), eyeshape="almond"),
          "shadow",
          "Watches the room from the doorway for an hour before entering.",
          ("mist blue", "silver", "charcoal")),

    Breed("ser", "Serengeti", R_CHAMPION, "a Bengal and an Oriental",
          "Legs like scaffolding and ears you could signal with.",
          L(size=1.1, body=0.84, facew=0.84, faceh=1.08, cheek=0.74,
            ear=1.54, legs=1.3, fluff=0.06, coat=(196, 176, 120),
            mark=(48, 44, 40), belly=(226, 212, 176), pat="spotted",
            eye=(214, 198, 92), eyeshape="round"),
          "climber",
          "Goes over the furniture rather than round it.",
          ("spotted gold", "silver", "charcoal"), ),
    Breed("kur", "Kurilian Bobtail", R_CHAMPION, "the islands north of Japan",
          "A pom-pom tail on a cat built like a hiking boot.",
          L(size=1.12, body=1.28, facew=1.1, faceh=0.98, cheek=1.18,
            ear=1.0, legs=1.1, fluff=0.66, tail="pom",
            coat=(164, 134, 96), mark=(96, 72, 50), belly=(220, 202, 172),
            pat="blotched", eye=(176, 184, 104)),
          "hunter",
          "Brings things back. Has never been asked to.",
          ("forest tabby", "red", "silver", "cream")),

    # -- LEGEND ------------------------------------------------------------
    Breed("kma", "Khao Manee", R_LEGEND, "Siam, kept by kings",
          "One blue eye, one gold. The diamond eye, they called it.",
          L(size=1.02, body=0.88, facew=0.96, faceh=1.04, cheek=0.88,
            ear=1.08, legs=1.2, fluff=0.22, coat=(248, 242, 232),
            mark=(232, 226, 216), belly=(252, 248, 240), pat="solid",
            eye=("odd", (112, 168, 220), (222, 176, 72)), eyeshape="almond"),
          "groomer",
          "Sits in the window like something on display.",
          ("diamond white", "ivory")),
    Breed("lyk", "Lykoi", R_LEGEND, "a feral litter in Tennessee",
          "Half-coated, so it comes with its own moonlight.",
          L(size=1.0, body=1.06, facew=1.06, faceh=0.96, cheek=1.04,
            ear=1.16, legs=0.94, fluff=0.56, skin=0.55, coat=(62, 58, 58),
            mark=(206, 200, 192), belly=(96, 92, 92), pat="roan",
            eye=(214, 170, 76), eyeshape="almond"),
          "shadow",
          "Works the edges of the room at a trot.",
          ("roan", "charcoal", "silver")),
    # -- FOUNDATION ---
    Breed("cha2", "Chausie", R_FOUNDATION, "a jungle cat, three generations back",
          "Foundation stock. Half the registry will not take it yet.",
          L(size=1.3, body=1.2, facew=1.0, faceh=1.04, cheek=1.04,
            ear=1.16, legs=1.2, fluff=0.22, coat=(140, 110, 72),
            mark=(58, 46, 36), belly=(190, 166, 130), pat="ticked",
            eye=(226, 190, 78), eyeshape="almond"),
          "hunter",
          "Clears the kitchen counter from a standing start.",
          ("grizzled brown", "black", "silver")),
    Breed("saf", "Safari", R_FOUNDATION, "a Geoffroy cat and a very long wait",
          "Perhaps a hundred of them exist. This is one of the hundred.",
          L(size=1.28, body=0.92, facew=0.88, faceh=1.12, cheek=0.8,
            ear=1.24, legs=1.42, fluff=0.08, coat=(186, 168, 132),
            mark=(44, 40, 38), belly=(224, 212, 184), pat="spotted",
            eye=(188, 200, 110), eyeshape="round"),
          "shadow",
          "Watches the whole room from the one place you cannot see it.",
          ("rosetted fawn", "silver", "charcoal")),

    Breed("lev", "Ukrainian Levkoy", R_LEGEND, "Kyiv, this century",
          "Bald, and the ears fold in. There is nothing else like it.",
          L(size=1.0, body=0.9, facew=1.0, faceh=1.08, cheek=0.8, ear=1.0,
            fold=1.0, legs=1.12, fluff=0.0, skin=1.0, coat=(198, 164, 150),
            mark=(162, 128, 116), belly=(216, 188, 174), pat="solid",
            eye=(186, 196, 128), eyeshape="almond", nose=(186, 136, 130)),
          "warmth",
          "Owns three jumpers and is wearing the warmest one.",
          ("bare fawn", "blue", "charcoal")),
    Breed("sok", "Sokoke", R_LEGEND, "the Arabuko forest",
          "The rarest coat in the book, and it was never bred for.",
          L(size=1.0, body=0.80, facew=0.88, faceh=1.02, cheek=0.78,
            ear=1.0, legs=1.36, fluff=0.04, coat=(178, 140, 100),
            mark=(74, 54, 40), belly=(206, 176, 136), pat="blotched",
            eye=(178, 182, 108), eyeshape="almond"),
          "hunter",
          "Patrols. Stops. Patrols the other way.",
          ("brown blotched", "silver", "chocolate")),
)

# ---------------------------------------------------------------------------
# THE REST OF THE BOOK
#
# Sixty more, written as a table rather than sixty more constructor calls,
# because at this length the shape of the data matters more than the shape
# of the code. Column order is the one the Breed takes:
#
#   key  name  rarity  origin  note  temper  habit  coats  look
#
# The look column is the whole point of the table: a hundred cats have to
# differ from each other in SHAPE, and the only way to see whether they do
# is to have the numbers in one place where they can be read down a column
# and compared. `cat_test.py sameness` is the judge of it.
# ---------------------------------------------------------------------------
_MORE = (
    # -- COMMON -------------------------------------------------------------
    ("dsh2", "Farm Tabby", R_COMMON, "a barn in the west country",
     "Works for board. Has never once been indoors in daylight.",
     "hunter", "Brings things to the back step and waits to be praised.",
     ("brown tabby", "red", "silver"),
     dict(body=0.92, facew=0.96, faceh=1.04, cheek=0.9, ear=1.18,
          legs=1.22, fluff=0.22, coat=(140, 118, 88), mark=(88, 68, 48),
          belly=(206, 188, 158),
          pat="tabby", eye=(186, 166, 84))),
    ("tux", "Tuxedo Moggy", R_COMMON, "everywhere, always",
     "Dressed for an occasion that never comes.",
     "lap", "Sits on the one chair with a cushion on it.",
     ("black and white", "grey and white", "charcoal"),
     dict(body=1.08, facew=1.1, faceh=0.98, cheek=1.1, ear=0.96,
          legs=1.14, fluff=0.3, coat=(58, 56, 58), mark=(242, 240, 236),
          belly=(246, 244, 240),
          pat="bicolour", eye=(200, 176, 80), eyeshape="round")),
    ("ging", "Ginger Moggy", R_COMMON, "the end of every street",
     "Ninety per cent of them are toms, and all of them know it.",
     "glutton", "Eats, sleeps, eats again, and is somehow still thin.",
     ("marmalade", "cream", "silver"),
     dict(body=1.1, facew=1.12, cheek=1.12, ear=0.98, legs=0.96, fluff=0.28,
          coat=(204, 142, 76), mark=(150, 92, 42), belly=(236, 212, 180),
          pat="tabby", eye=(196, 168, 72))),
    ("calico", "Calico Moggy", R_COMMON, "a litter nobody planned",
     "Three colours, and a different cat on each side.",
     "shadow", "Watches from under the furniture until it is sure.",
     ("calico", "dilute calico", "cream"),
     dict(size=0.92, body=0.86, facew=0.94, faceh=1.04, cheek=0.9,
          ear=1.12, legs=1.1, fluff=0.36, coat=(242, 238, 230),
          mark=(78, 66, 58), belly=(248, 246, 242),
          pat="tortie", eye=(176, 158, 86))),
    ("dragon", "Dragon Li", R_COMMON, "China, and a very long way back",
     "The oldest working cat in the world, and still working.",
     "hunter", "Patrols the skirting boards like a watchman.",
     ("golden tabby", "brown", "silver"),
     dict(size=1.08, body=1.04, facew=0.96, faceh=1.1, cheek=0.94,
          ear=1.12, legs=1.26, fluff=0.14, coat=(176, 148, 96),
          mark=(96, 76, 50),
          belly=(216, 196, 158), pat="tabby", eye=(188, 196, 110))),
    ("aeg", "Aegean", R_COMMON, "the harbours of the Cyclades",
     "Fishes. Actually fishes, with its feet, out of the water.",
     "busy", "Supervises the sink and everything that happens in it.",
     ("white and red", "white and black", "cream"),
     dict(body=0.9, facew=0.92, faceh=1.06, cheek=0.86, ear=1.24,
          legs=1.3, fluff=0.34, tail="plume", coat=(240, 236, 228),
          mark=(188, 112, 66),
          belly=(248, 246, 240), pat="bicolour", eye=(176, 186, 110))),
    ("brz", "Brazilian Shorthair", R_COMMON, "the streets of Rio",
     "Lean, loud, and entirely unbothered by weather.",
     "lap", "Finds the sunniest tile and holds it all afternoon.",
     ("red tabby", "black", "blue", "cream"),
     dict(size=0.96, body=0.82, facew=0.9, faceh=1.1, cheek=0.82,
          ear=1.3, legs=1.24, fluff=0.08, tail="whip", coat=(188, 136, 82),
          mark=(118, 72, 40),
          belly=(224, 198, 164), pat="tabby", eye=(180, 192, 104))),
    ("arab", "Arabian Mau", R_COMMON, "the desert edge of the Gulf",
     "Built for forty degrees in the shade, and there is no shade.",
     "shadow", "Goes out at dusk and comes back at dawn, saying nothing.",
     ("sand", "white and red", "black"),
     dict(body=0.94, facew=0.94, faceh=1.06, cheek=0.88, ear=1.3,
          legs=1.22, fluff=0.08, coat=(214, 196, 158), mark=(150, 128, 92),
          belly=(238, 228, 204), pat="tabby", eye=(198, 182, 96))),
    ("poly", "American Polydactyl", R_COMMON, "a dockside in Key West",
     "Six toes a foot, which it uses for doors.",
     "busy", "Has worked out the cupboard. All of the cupboards.",
     ("brown tabby", "black and white", "red"),
     dict(size=1.1, body=1.26, facew=1.16, faceh=0.96, cheek=1.24,
          ear=0.9, legs=0.88, fluff=0.4, coat=(132, 112, 90),
          mark=(82, 64, 48), belly=(208, 190, 164),
          pat="tabby", eye=(190, 170, 78))),
    ("brit2", "British Longhair", R_COMMON, "Britain, with more coat",
     "The round grey full stop, after a winter indoors.",
     "sleeper", "Occupies a cushion the way weather occupies a county.",
     ("blue", "cream", "silver", "black"),
     dict(body=1.26, facew=1.22, faceh=0.96, cheek=1.3, ear=0.84, legs=0.84,
          fluff=0.86, tail="plume", coat=(126, 136, 150),
          mark=(98, 108, 122), belly=(150, 160, 174), pat="smoke",
          eye=(214, 150, 60), eyeshape="round")),

    # -- UNCOMMON -----------------------------------------------------------
    ("ori", "Oriental Shorthair", R_UNCOMMON, "a Siamese without the points",
     "All ears and opinions, in rather a lot of colours.",
     "lap", "Narrates the entire evening from the arm of the chair.",
     ("ebony", "blue", "red", "lilac"),
     dict(size=0.98, body=0.78, facew=0.8, faceh=1.14, cheek=0.72, ear=1.48,
          legs=1.2, fluff=0.08, tail="whip", coat=(62, 58, 60),
          mark=(40, 38, 40), belly=(92, 88, 90), pat="solid",
          eye=(150, 196, 128), eyeshape="almond")),
    ("bali", "Balinese", R_UNCOMMON, "a long-haired Siamese litter",
     "The points, the voice, and a tail like a feather duster.",
     "lap", "Follows, comments, and sits down on the thing you need.",
     ("seal point", "blue", "chocolate", "lilac"),
     dict(size=1.0, body=0.84, facew=0.84, faceh=1.1, cheek=0.76, ear=1.3,
          legs=1.14, fluff=0.68, tail="plume", coat=(228, 212, 184),
          mark=(74, 56, 52), belly=(240, 228, 206), pat="point",
          eye=(104, 164, 212), eyeshape="almond")),
    ("tonk", "Tonkinese", R_UNCOMMON, "a Burmese and a Siamese",
     "Halfway between two arguments, and pleased about it.",
     "lap", "Arrives on your lap the moment you sit down. Every time.",
     ("natural mink", "blue mink", "champagne"),
     dict(body=0.9, facew=0.92, faceh=1.06, cheek=0.88, ear=1.22,
          legs=1.14, fluff=0.14, coat=(166, 136, 104), mark=(104, 78, 60),
          belly=(206, 184, 156), pat="point", eye=(126, 186, 196),
          eyeshape="almond")),
    ("snow", "Snowshoe", R_UNCOMMON, "a Siamese litter with white feet",
     "Points, and then four white boots nobody ordered.",
     "lap", "Puts one white foot on you and leaves it there.",
     ("seal point", "blue point", "chocolate"),
     dict(size=1.08, body=1.06, facew=1.02, faceh=1.04, cheek=1.0,
          ear=1.1, legs=1.22, fluff=0.3, coat=(230, 218, 196),
          mark=(88, 68, 64),
          belly=(244, 236, 220), pat="gloves", eye=(110, 162, 212),
          eyeshape="round")),
    ("himal", "Himalayan", R_UNCOMMON, "a Persian and a Siamese",
     "A Persian that took the points and kept the face.",
     "sleeper", "Has not moved since lunch and does not intend to.",
     ("seal point", "blue", "cream", "chocolate"),
     dict(size=1.04, body=1.14, facew=1.18, faceh=0.98, cheek=1.2,
          ear=0.8, flat=0.7, fluff=0.86, tail="plume", legs=0.9,
          coat=(236, 224, 200), mark=(96, 74, 70), belly=(246, 238, 220),
          pat="point", eye=(112, 160, 214), eyeshape="round")),
    ("exotic", "Exotic Shorthair", R_UNCOMMON, "a Persian in a hurry",
     "The Persian face on a coat you can actually brush.",
     "sleeper", "Breathes audibly on the warm end of the sofa.",
     ("cream", "blue", "silver", "red"),
     dict(size=1.06, body=1.24, facew=1.28, faceh=0.9, cheek=1.32, ear=0.7,
          flat=1.0, fluff=0.3, legs=0.8, coat=(226, 206, 176),
          mark=(176, 152, 122), belly=(240, 226, 202), pat="smoke",
          eye=(214, 148, 62), eyeshape="round")),
    ("ragam", "Ragamuffin", R_UNCOMMON, "a Ragdoll that went its own way",
     "Enormous, and entirely unaware of it.",
     "lap", "Goes limp in whichever direction it is picked up.",
     ("red and white", "blue", "cream", "chocolate"),
     dict(size=1.24, body=1.34, facew=1.22, faceh=0.94, cheek=1.3,
          ear=0.8, fluff=0.62, tail="plume", legs=0.84,
          coat=(226, 200, 172), mark=(168, 118, 80),
          belly=(240, 226, 206), pat="bicolour", eye=(140, 180, 128),
          eyeshape="round")),
    ("sib", "Siberian", R_UNCOMMON, "the forests east of the Urals",
     "Triple-coated, and it has opinions about open windows.",
     "climber", "Is on the top of the bookcase. Was not seen going up.",
     ("brown tabby", "silver", "red", "black"),
     dict(size=1.2, body=1.26, facew=1.08, faceh=1.02, cheek=1.12, ear=1.0,
          tuft=1.0, fluff=1.0, tail="plume", legs=1.02,
          coat=(150, 118, 84), mark=(92, 66, 44), belly=(216, 196, 164),
          pat="tabby", eye=(168, 186, 112))),
    ("neva", "Neva Masquerade", R_UNCOMMON, "the Neva, in a mask",
     "A Siberian in a mask, which is a sentence that makes sense in Russia.",
     "sleeper", "Sleeps where the heating pipe runs under the floor.",
     ("seal point", "blue", "red"),
     dict(size=1.18, body=1.22, facew=1.06, faceh=1.04, cheek=1.08,
          ear=1.04, fluff=0.96, tail="plume", legs=1.0,
          coat=(234, 222, 198), mark=(92, 72, 70), belly=(244, 236, 218),
          pat="point", eye=(108, 164, 212))),
    ("amb", "American Bobtail", R_UNCOMMON, "a roadside motel in Arizona",
     "A short tail, a long body, and the walk of something wild.",
     "hunter", "Carries one toy from room to room for days at a time.",
     ("brown tabby", "silver", "red", "black"),
     dict(size=1.14, body=1.2, facew=1.1, faceh=0.98, cheek=1.12, ear=1.02,
          legs=1.08, fluff=0.5, tail="bob", coat=(154, 126, 92),
          mark=(94, 70, 48), belly=(214, 194, 164), pat="tabby",
          eye=(184, 164, 90))),
    ("pixie", "Pixie-bob", R_UNCOMMON, "the Cascades, allegedly",
     "Looks like something that came down off the mountain.",
     "shadow", "Walks the edge of the room and never the middle of it.",
     ("brown spotted", "charcoal", "silver"),
     dict(size=1.16, body=1.24, facew=1.16, faceh=0.96, cheek=1.2, ear=0.9,
          tuft=1.0, legs=1.06, fluff=0.4, tail="bob", coat=(168, 136, 96),
          mark=(74, 56, 42), belly=(214, 192, 158), pat="spotted",
          eye=(188, 176, 96))),
    ("cymric", "Cymric", R_UNCOMMON, "the Isle of Man, with a coat on",
     "No tail at all, and a great deal of everything else.",
     "sleeper", "Rolls onto its back and stays there for an hour.",
     ("brown tabby", "red", "silver", "cream"),
     dict(body=1.24, facew=1.14, cheek=1.18, legs=0.86, fluff=0.94,
          tail="none", coat=(162, 132, 96), mark=(100, 74, 50),
          belly=(220, 200, 170), pat="tabby", eye=(190, 164, 76))),
    ("ocicat", "Ocicat", R_UNCOMMON, "an accident in a Siamese programme",
     "Spotted like a wild cat and soft as a cushion.",
     "busy", "Opens the bathroom door and announces the fact.",
     ("tawny", "chocolate", "silver", "blue"),
     dict(size=1.14, body=1.0, facew=0.94, faceh=1.08, cheek=0.9,
          ear=1.22, legs=1.3, fluff=0.08, coat=(196, 164, 108),
          mark=(74, 56, 40), belly=(228, 206, 168), pat="spotted",
          eye=(184, 174, 92), eyeshape="almond")),

    # -- RARE ---------------------------------------------------------------
    ("korat", "Korat", R_RARE, "Thailand, given in pairs for luck",
     "Silver-blue, heart-faced, and never sold - only given.",
     "lap", "Picks one person in the flat and treats the rest as weather.",
     ("silver blue",),
     dict(body=1.04, facew=1.14, faceh=0.94, cheek=1.1, ear=1.06, legs=0.98,
          fluff=0.22, coat=(132, 146, 158), mark=(104, 118, 130),
          belly=(166, 180, 192), pat="solid", eye=(142, 196, 140),
          eyeshape="round")),
    ("havana", "Havana Brown", R_RARE, "a London breeding programme",
     "One colour only, and the whiskers are brown as well.",
     "lap", "Puts a paw on your wrist while you are trying to type.",
     ("chocolate",),
     dict(body=1.1, facew=1.04, faceh=1.0, cheek=1.06, ear=1.04,
          legs=1.0, fluff=0.18, coat=(110, 76, 56), mark=(74, 48, 34),
          belly=(150, 114, 88), pat="solid", eye=(140, 196, 128),
          eyeshape="round")),
    ("burmilla", "Burmilla", R_RARE, "one unlocked door in 1981",
     "A Burmese and a Chinchilla met by accident. This is the result.",
     "groomer", "Keeps the silver immaculate and resents the floor.",
     ("silver shaded", "golden", "blue"),
     dict(body=0.94, facew=0.98, faceh=1.06, cheek=0.9, ear=1.16,
          legs=1.2, fluff=0.5, coat=(216, 214, 210), mark=(126, 124, 128),
          belly=(238, 238, 236),
          pat="smoke", eye=(150, 190, 120), eyeshape="round")),
    ("aussie", "Australian Mist", R_RARE, "Sydney, out of three breeds",
     "Spots under a haze, like weather over a map.",
     "lap", "Wants to be carried. Will wait by your feet until it is.",
     ("brown mist", "blue", "gold", "peach"),
     dict(body=1.22, facew=1.18, faceh=0.94, cheek=1.2, ear=0.92,
          legs=0.88, fluff=0.28, coat=(188, 160, 124), mark=(118, 94, 70),
          belly=(222, 202, 174),
          pat="spotted", eye=(154, 192, 128), eyeshape="round")),
    ("laperm", "LaPerm", R_RARE, "a cherry orchard in Oregon",
     "Born bald, comes back in ringlets.",
     "busy", "Sheds curls on everything and looks pleased about it.",
     ("red curl", "silver", "chocolate", "blue"),
     dict(body=1.0, facew=1.0, faceh=1.02, cheek=1.0, ear=1.14, legs=1.04,
          fluff=0.74, curl=1.0, tail="plume", coat=(196, 142, 94),
          mark=(136, 90, 56), belly=(226, 198, 168), pat="tabby",
          eye=(178, 186, 110))),
    ("cornish", "Cornish Rex", R_RARE, "a Cornish barn, 1950",
     "No guard hairs at all. Feels like warm suede.",
     "busy", "Runs the length of the flat for no stated reason.",
     ("silver", "cream", "black", "blue"),
     dict(size=0.94, body=0.8, facew=0.86, faceh=1.12, cheek=0.74, ear=1.5,
          legs=1.24, fluff=0.1, curl=1.0, tail="whip", coat=(176, 172, 170),
          mark=(118, 114, 114), belly=(212, 210, 208), pat="smoke",
          eye=(186, 190, 118), eyeshape="round")),
    ("germ", "German Rex", R_RARE, "a Berlin hospital garden",
     "The older curl, and the steadier one.",
     "lap", "Settles against your leg and goes off like a kettle.",
     ("blue", "black", "cream"),
     dict(body=0.98, facew=1.04, faceh=0.98, cheek=1.04, ear=1.18,
          legs=1.0, fluff=0.3, curl=1.0, coat=(124, 134, 146),
          mark=(92, 102, 114), belly=(162, 172, 184), pat="smoke",
          eye=(188, 174, 88), eyeshape="round")),
    ("wire", "American Wirehair", R_RARE, "one kitten in a New York barn",
     "Every hair bent, including the whiskers. One barn, one cat, once.",
     "shadow", "Takes the high shelf and watches the door from it.",
     ("brown tabby", "silver", "red"),
     dict(body=1.1, facew=1.1, cheek=1.12, ear=0.98, legs=1.0, fluff=0.36,
          curl=1.0, coat=(146, 124, 98), mark=(92, 72, 52),
          belly=(206, 190, 164), pat="tabby", eye=(192, 170, 82))),
    ("somali", "Somali", R_RARE, "an Abyssinian with a long coat",
     "A fox, if a fox were a cat and knew where the food was.",
     "climber", "Is on top of the door. The door is open.",
     ("ruddy", "red", "blue", "fawn"),
     dict(size=1.02, body=0.96, facew=0.92, faceh=1.04, cheek=0.88,
          ear=1.3, legs=1.2, fluff=0.8, tail="plume", coat=(180, 118, 68),
          mark=(102, 60, 36), belly=(212, 160, 110), pat="ticked",
          eye=(206, 164, 70), eyeshape="almond")),
    ("thai", "Thai", R_RARE, "Wichien Maat, the original",
     "The old Siamese, before anyone narrowed the face.",
     "lap", "Tells the room about the weather at four in the morning.",
     ("seal point", "blue", "chocolate"),
     dict(body=1.0, facew=1.04, faceh=1.0, cheek=1.02, ear=1.14, legs=1.04,
          fluff=0.16, tail="kink", coat=(228, 212, 186), mark=(76, 58, 54),
          belly=(240, 228, 206), pat="point", eye=(104, 164, 212),
          eyeshape="round")),
    ("colour", "Colourpoint Shorthair", R_RARE, "a Siamese in sixteen colours",
     "The points, in colours the registry argued about for years.",
     "lap", "Has chosen the chair you were going to sit in.",
     ("red point", "cream", "lilac", "chocolate"),
     dict(body=0.88, facew=0.86, faceh=1.1, cheek=0.78, ear=1.32, legs=1.16,
          fluff=0.12, tail="whip", coat=(234, 222, 200), mark=(190, 112, 74),
          belly=(244, 236, 220), pat="point", eye=(108, 168, 214),
          eyeshape="almond")),
    ("sey", "Seychellois", R_RARE, "the islands, by way of a breeder",
     "Points, and white thrown over the top like a sheet.",
     "shadow", "Behind the curtain. Has been for some time.",
     ("seal and white", "blue", "red"),
     dict(size=1.0, body=0.86, facew=0.84, faceh=1.12, cheek=0.76, ear=1.36,
          legs=1.18, fluff=0.14, tail="whip", coat=(240, 236, 228),
          mark=(84, 64, 60), belly=(248, 246, 242), pat="van",
          eye=(106, 166, 212), eyeshape="almond")),
    ("ceylon", "Ceylon", R_RARE, "the hill country of Sri Lanka",
     "Ticked sand with a ringed tail. Barely anyone has one.",
     "hunter", "Hunts the stair rail at speed, nightly.",
     ("sand ticked", "silver", "fawn"),
     dict(size=0.94, body=0.9, facew=0.94, faceh=1.0, cheek=0.9, ear=1.18,
          legs=1.08, fluff=0.1, coat=(206, 184, 146), mark=(128, 104, 74),
          belly=(230, 216, 188), pat="ticked", eye=(176, 188, 110))),

    # -- PEDIGREE -----------------------------------------------------------
    ("peter", "Peterbald", R_PEDIGREE, "St Petersburg, 1994",
     "Bald, or nearly, on the frame of an Oriental.",
     "warmth", "Under the blanket within four seconds of it appearing.",
     ("bare fawn", "blue", "chocolate"),
     dict(size=1.0, body=0.78, facew=0.82, faceh=1.14, cheek=0.7, ear=1.52,
          legs=1.26, fluff=0.0, skin=1.0, tail="whip", coat=(210, 174, 156),
          mark=(176, 140, 124), belly=(224, 192, 176), pat="solid",
          eye=(188, 196, 116), eyeshape="almond", nose=(190, 134, 130))),
    ("donskoy", "Donskoy", R_PEDIGREE, "Rostov-on-Don",
     "Bald by a different gene, and wrinkled with it.",
     "warmth", "Sleeps on the router because it is warm.",
     ("bare pink", "silver", "fawn"),
     dict(body=0.92, facew=1.0, faceh=1.04, cheek=0.86, ear=1.36, legs=1.08,
          fluff=0.0, skin=1.0, coat=(206, 166, 150), mark=(172, 132, 118),
          belly=(220, 186, 170), pat="solid", eye=(196, 188, 112),
          eyeshape="almond", nose=(188, 132, 128))),
    ("bambino", "Bambino", R_PEDIGREE, "a Sphynx and a Munchkin",
     "Bald and four inches off the ground.",
     "busy", "Cannot get on the sofa. Has a plan about it.",
     ("bare pink", "blue", "cream"),
     dict(size=0.9, body=0.94, facew=0.96, faceh=1.02, cheek=0.8, ear=1.44,
          legs=0.48, fluff=0.0, skin=1.0, coat=(208, 170, 154),
          mark=(174, 136, 122), belly=(222, 190, 174), pat="solid",
          eye=(192, 192, 114), eyeshape="almond", nose=(188, 132, 128))),
    ("minskin", "Minskin", R_PEDIGREE, "Boston, out of four breeds",
     "Bald body, furred points, short legs. Somebody meant this.",
     "warmth", "Found the radiator on day one and has not left it.",
     ("fawn point", "blue", "silver"),
     dict(size=0.9, body=1.0, facew=1.0, faceh=1.0, cheek=0.9, ear=1.3,
          legs=0.5, fluff=0.08, skin=0.6, coat=(216, 190, 168),
          mark=(140, 108, 96), belly=(230, 208, 190), pat="point",
          eye=(178, 190, 120), eyeshape="round")),
    ("napoleon", "Minuet", R_PEDIGREE, "a Persian and a Munchkin",
     "The flat face, three inches off the carpet.",
     "sleeper", "Sleeps in the middle of the floor, in everyone's way.",
     ("cream", "silver", "blue", "red"),
     dict(size=0.96, body=1.18, facew=1.24, faceh=0.94, cheek=1.26, ear=0.74,
          flat=0.8, legs=0.5, fluff=0.8, tail="plume", coat=(230, 212, 182),
          mark=(180, 158, 128), belly=(242, 230, 208), pat="smoke",
          eye=(214, 150, 62), eyeshape="round")),
    ("kinkalow", "Kinkalow", R_PEDIGREE, "a Munchkin and an American Curl",
     "Short legs, curled ears, and a complete lack of doubt.",
     "busy", "Climbs what it cannot reach, slowly, and gets there.",
     ("brown tabby", "cream", "black"),
     dict(size=0.92, body=1.02, facew=1.02, cheek=1.0, ear=1.22,
          earcurl=1.0, legs=0.5, fluff=0.36, coat=(164, 136, 104),
          mark=(102, 78, 56), belly=(216, 198, 170), pat="tabby",
          eye=(184, 174, 94))),
    ("dwelf", "Dwelf", R_PEDIGREE, "three mutations in one cat",
     "Bald, short-legged, curl-eared. There are not many.",
     "warmth", "Is inside your dressing gown. It was on the hook.",
     ("bare fawn", "silver", "blue"),
     dict(size=0.88, body=0.94, facew=1.0, faceh=1.0, cheek=0.84, ear=1.38,
          earcurl=1.0, legs=0.48, fluff=0.0, skin=1.0, coat=(206, 168, 152),
          mark=(172, 134, 120), belly=(220, 188, 172), pat="solid",
          eye=(190, 190, 112), eyeshape="round", nose=(188, 132, 128))),
    ("foldex", "Foldex", R_PEDIGREE, "Quebec, out of an Exotic",
     "The folded ear on the flat face. Round, and then rounder.",
     "sleeper", "A loaf, on the warm side of the room, indefinitely.",
     ("cream", "blue", "silver", "red"),
     dict(size=1.04, body=1.2, facew=1.28, faceh=0.92, cheek=1.32,
          fold=1.0, ear=0.72, flat=0.8, legs=0.88, fluff=0.5,
          coat=(224, 206, 178), mark=(170, 150, 124), belly=(240, 228, 206),
          pat="smoke", eye=(212, 152, 64), eyeshape="round")),
    ("chantilly", "Chantilly-Tiffany", R_PEDIGREE, "thought extinct twice",
     "Chocolate, long-coated, and twice given up for lost.",
     "lap", "Sits beside you, not on you, and keeps up a commentary.",
     ("chocolate", "blue", "cinnamon"),
     dict(size=1.08, body=1.1, facew=1.04, faceh=1.0, cheek=1.04, ear=1.06,
          fluff=0.88, tail="plume", legs=1.0, coat=(112, 80, 58),
          mark=(74, 50, 34), belly=(166, 132, 104), pat="smoke",
          eye=(204, 174, 76))),
    ("york", "York Chocolate", R_PEDIGREE, "a farm in New York state",
     "Chocolate, farm-bred, and nearly gone again.",
     "hunter", "Patrols the hall at dusk with great seriousness.",
     ("chocolate", "lilac", "white"),
     dict(size=1.16, body=1.24, facew=1.14, faceh=0.96, cheek=1.18,
          ear=0.94, fluff=0.72, tail="plume", legs=0.92,
          coat=(104, 74, 56),
          mark=(68, 46, 32), belly=(158, 126, 100), pat="solid",
          eye=(198, 178, 84))),
    ("ojos", "Ojos Azules", R_PEDIGREE, "a feral colony in New Mexico",
     "Blue eyes on any colour of cat at all, which should not happen.",
     "shadow", "Watches from the dark, and the eyes give it away.",
     ("brown tabby", "black", "red"),
     dict(body=1.18, facew=1.14, faceh=0.96, cheek=1.18, ear=0.92,
          legs=0.9, fluff=0.44, coat=(138, 114, 88), mark=(86, 66, 48),
          belly=(206, 188, 160), pat="tabby", eye=(96, 158, 222),
          eyeshape="round")),

    # -- CHAMPION -----------------------------------------------------------
    ("cheetoh", "Cheetoh", R_CHAMPION, "an Ocicat and a Bengal",
     "Spotted twice over, and it walks like something on a documentary.",
     "hunter", "Stalks the hall rug in a crouch and means it.",
     ("golden spotted", "silver", "charcoal"),
     dict(size=1.16, body=1.1, facew=0.98, faceh=1.0, cheek=0.96, ear=1.0,
          legs=1.2, fluff=0.08, coat=(206, 170, 100), mark=(54, 42, 34),
          belly=(232, 210, 168), pat="spotted", eye=(186, 180, 94),
          eyeshape="almond")),
    ("highland", "Highlander", R_CHAMPION, "a curl and a jungle line",
     "Curled ears, bobbed tail, and the shoulders of a prop forward.",
     "busy", "Rearranges the room nightly and tells nobody.",
     ("brown spotted", "silver", "charcoal"),
     dict(size=1.2, body=1.26, facew=1.14, faceh=0.96, cheek=1.2, ear=1.1,
          earcurl=1.0, legs=1.1, fluff=0.3, tail="bob",
          coat=(176, 144, 102), mark=(70, 54, 40), belly=(218, 196, 164),
          pat="spotted", eye=(196, 182, 96))),
    ("kanaani", "Kanaani", R_CHAMPION, "Jerusalem, out of a desert cat",
     "Half a wildcat by design, and it shows in the shoulders.",
     "shadow", "Chooses the one spot in the room with a view of both doors.",
     ("desert spotted", "silver", "cinnamon"),
     dict(size=1.18, body=1.0, facew=0.92, faceh=1.08, cheek=0.86, ear=1.34,
          legs=1.3, fluff=0.08, coat=(206, 186, 140), mark=(96, 76, 54),
          belly=(230, 216, 184), pat="spotted", eye=(190, 196, 108),
          eyeshape="almond")),
    ("jungle", "Jungle Curl", R_CHAMPION, "a jungle cat and a curl",
     "Wild lines, curled ears, and a great deal of leg.",
     "climber", "Gets to the top of the door frame. Sits there.",
     ("ticked bronze", "charcoal", "silver"),
     dict(size=1.22, body=1.0, facew=0.9, faceh=1.1, cheek=0.84, ear=1.3,
          earcurl=1.0, legs=1.34, fluff=0.1, coat=(166, 132, 86),
          mark=(86, 62, 42), belly=(208, 184, 146), pat="ticked",
          eye=(214, 186, 86), eyeshape="almond")),
    ("mekong", "Mekong Bobtail", R_CHAMPION, "the old Siamese court cats",
     "The points, and the kinked bobtail they were famous for.",
     "lap", "Keeps one eye on you and both ears on the kitchen.",
     ("seal point", "blue", "chocolate"),
     dict(body=1.0, facew=1.0, faceh=1.02, cheek=0.98, ear=1.12, legs=1.1,
          fluff=0.2, tail="bob", coat=(230, 216, 190), mark=(80, 60, 56),
          belly=(242, 232, 212), pat="point", eye=(106, 166, 212),
          eyeshape="almond")),
    ("ural", "Ural Rex", R_CHAMPION, "the Urals, before the war",
     "Waved coat, old line, and almost none of them left.",
     "groomer", "Washes the wave back into place, over and over.",
     ("blue and white", "black", "silver"),
     dict(body=1.02, facew=1.04, faceh=1.0, cheek=1.02, ear=1.08, legs=1.02,
          fluff=0.52, curl=1.0, coat=(128, 138, 150), mark=(238, 236, 232),
          belly=(242, 240, 238), pat="bicolour", eye=(176, 186, 110))),
    ("toybob", "Toybob", R_CHAMPION, "Rostov, and the size of a kitten",
     "Stays kitten-sized its whole life. Weighs as much as a book.",
     "lap", "Sleeps in a slipper. Fits, with room to spare.",
     ("seal point", "silver", "cream"),
     dict(size=0.74, body=0.92, facew=1.04, faceh=0.96, cheek=0.96,
          ear=1.06, legs=0.9, fluff=0.22, tail="bob", coat=(228, 214, 190),
          mark=(86, 66, 62), belly=(240, 230, 212), pat="point",
          eye=(110, 164, 210), eyeshape="round")),

    # -- LEGEND -------------------------------------------------------------
    ("sokoke2", "Khadzonzo", R_LEGEND, "the Arabuko-Sokoke forest",
     "The forest name for the forest cat, from before it was a breed.",
     "hunter", "Hunts the same circuit of the flat every single night.",
     ("brown blotched", "silver"),
     dict(size=1.0, body=0.82, facew=0.9, faceh=1.02, cheek=0.8, ear=1.08,
          legs=1.32, fluff=0.04, tail="whip", coat=(174, 138, 98),
          mark=(72, 52, 38), belly=(204, 174, 134), pat="blotched",
          eye=(178, 182, 108), eyeshape="almond")),
    ("suphalak", "Suphalak", R_LEGEND, "a Thai poem about cats",
     "Solid copper, named in a manuscript six hundred years old.",
     "lap", "Follows the sun round the flat and takes you with it.",
     ("copper",),
     dict(body=1.16, facew=1.12, faceh=0.94, cheek=1.14, ear=0.96,
          legs=0.94, fluff=0.1, coat=(146, 84, 48), mark=(100, 54, 28),
          belly=(190, 126, 80), pat="solid", eye=(212, 170, 68),
          eyeshape="almond")),
    ("ninja", "Sam Sawet", R_LEGEND, "a Thai village, unregistered",
     "The grey one from the poem that nobody has standardised.",
     "shadow", "Is in the room. You will find out later.",
     ("smoke grey", "charcoal"),
     dict(size=0.94, body=0.88, facew=1.0, faceh=1.0, cheek=0.96,
          ear=1.12, legs=1.04, fluff=0.26, tail="kink",
          coat=(104, 102, 106), mark=(66, 64, 68),
          belly=(146, 144, 148), pat="smoke", eye=(176, 194, 126),
          eyeshape="almond")),
    ("elf", "Elf Cat", R_LEGEND, "a Sphynx and an American Curl",
     "Bald, with the ears turned back. Perhaps two hundred exist.",
     "warmth", "Is in the airing cupboard. The door was shut.",
     ("bare fawn", "blue", "silver"),
     dict(size=1.0, body=0.86, facew=0.94, faceh=1.06, cheek=0.74, ear=1.5,
          earcurl=1.0, legs=1.1, fluff=0.0, skin=1.0, coat=(208, 168, 152),
          mark=(174, 134, 120), belly=(222, 190, 172), pat="solid",
          eye=(196, 192, 112), eyeshape="almond", nose=(188, 132, 128))),

    # -- FOUNDATION ---------------------------------------------------------
    ("caracat", "Caracat", R_FOUNDATION, "a caracal and a very long argument",
     "A caracal crossed into a house cat. The registries are not speaking.",
     "hunter", "Takes the top of the wardrobe in one go, from the floor.",
     ("desert tawny", "charcoal"),
     dict(size=1.34, body=1.08, facew=0.9, faceh=1.14, cheek=0.86, ear=1.6,
          tuft=1.0, legs=1.44, fluff=0.1, coat=(196, 154, 104),
          mark=(78, 58, 42), belly=(224, 198, 158), pat="ticked",
          eye=(216, 184, 80), eyeshape="almond")),
    ("genetta", "Genetta", R_FOUNDATION, "a genet, in outline only",
     "Short legs, long spotted body, and a tail twice the cat.",
     "shadow", "Pours itself under the door gap and is gone.",
     ("spotted silver", "charcoal", "gold"),
     dict(size=1.0, body=1.16, facew=0.94, faceh=1.0, cheek=0.9, ear=1.16,
          legs=0.46, fluff=0.1, tail="whip", coat=(190, 182, 164),
          mark=(58, 54, 52), belly=(222, 216, 202), pat="spotted",
          eye=(188, 186, 104), eyeshape="almond")),
)


def _build_more():
    out = []
    for key, name, rar, origin, note, temper, habit, coats, look in _MORE:
        out.append(Breed(key, name, rar, origin, note, L(**look), temper,
                         habit, coats))
    return tuple(out)


# ---------------------------------------------------------------------------
# THE TWO NEW TIERS, AND THE CATS IN THEM
#
# EXOTIC and HEIRLOOM were added to the ladder with nothing standing on
# them, which is not a balance problem but a crash: `roll` picks a tier
# by weight and then picks a breed out of it, and an empty tier is an
# empty list to choose from. These are the cats that live there, plus
# four more spread across the rungs that were already busy.
# ---------------------------------------------------------------------------
NEW_BREEDS = (
    # -- EXOTIC: the ones that look like they got out of somewhere ------
    Breed("chau", "Marsh Runner", R_EXOTIC, "the reed beds of the Nile",
          "Half again as long as it has any need to be.",
          L(size=1.18, body=1.26, facew=0.94, faceh=1.06, cheek=0.88,
            ear=1.28, legs=1.30, fluff=0.08, tail="plain",
            coat=(150, 118, 76), mark=(92, 68, 40), belly=(210, 186, 150),
            pat="ticked", eye=(206, 184, 86), eyeshape="almond"),
          "hunter", "Covers the whole flat at a trot, twice an hour.",
          ("grizzled tabby", "black", "silver")),
    Breed("cara", "The Hillside Lynx", R_EXOTIC, "a dry hillside",
          "The ears have tufts on them and it knows exactly how that looks.",
          L(size=1.14, body=0.96, facew=1.00, faceh=1.04, cheek=0.94,
            ear=1.46, tuft=1.0, legs=1.18, fluff=0.14, tail="plain",
            coat=(198, 142, 92), mark=(146, 96, 54), belly=(234, 210, 180),
            pat="solid", eye=(188, 196, 96), eyeshape="almond"),
          "climber", "Sits somewhere high with the tufts up, listening.",
          ("sand", "charcoal", "blue")),
    Breed("serv", "Serval Cross", R_EXOTIC, "two generations off the wild",
          "Legs like a deer and no sense of scale at all.",
          L(size=1.26, body=0.90, facew=0.90, faceh=1.12, cheek=0.84,
            ear=1.40, legs=1.44, fluff=0.06, tail="bob",
            coat=(214, 176, 100), mark=(70, 58, 46), belly=(242, 228, 202),
            pat="spotted", eye=(198, 182, 92), eyeshape="almond"),
          "busy", "Clears the kitchen counter from a standing start.",
          ("golden spotted", "silver", "charcoal")),
    Breed("jcrl", "Backward Ears", R_EXOTIC, "a hybrid programme in Nevada",
          "The ears go backwards, which takes some getting used to.",
          L(size=1.04, body=1.06, facew=1.06, faceh=0.98, cheek=1.10,
            ear=1.16, earcurl=1.0, legs=0.98, fluff=0.58, tail="plume",
            coat=(120, 100, 88), mark=(68, 56, 50), belly=(196, 180, 166),
            pat="blotched", eye=(150, 190, 128), eyeshape="round"),
          "shadow", "Watches from the doorway with its ears turned round.",
          ("smoke tabby", "charcoal", "chocolate")),
    Breed("dlnx", "Desert Lynx", R_EXOTIC, "the scrub at the edge of town",
          "Short at the back, tufted at the top, and entirely unbothered.",
          L(size=1.10, body=1.08, facew=1.12, faceh=0.94, cheek=1.18,
            ear=1.22, tuft=0.8, legs=0.86, fluff=0.36, tail="none",
            coat=(176, 150, 116), mark=(112, 92, 68), belly=(226, 212, 190),
            pat="blotched", eye=(176, 190, 104), eyeshape="round"),
          "warmth", "Finds the one square of sun and stays in it.",
          ("desert tabby", "silver", "fawn")),
    Breed("soko", "The Bark Cat", R_EXOTIC, "a forest on the Kenyan coast",
          "Marked like bark, and about as easy to spot against it.",
          L(size=0.98, body=1.12, facew=0.96, faceh=1.00, cheek=0.92,
            ear=1.10, legs=1.14, fluff=0.04, tail="whip",
            coat=(162, 128, 92), mark=(94, 68, 44), belly=(214, 192, 164),
            pat="blotched", eye=(170, 182, 104), eyeshape="almond"),
          "hunter", "Is somewhere in the room. You will find it eventually.",
          ("bark tabby", "brown", "cinnamon")),
    Breed("pbsp", "Punjabi Spotted", R_EXOTIC, "a village outside Amritsar",
          "Spotted twice over, which is more than anybody asked for.",
          L(size=1.00, body=1.00, facew=1.08, faceh=1.00, cheek=1.06,
            ear=0.92, legs=1.00, fluff=0.72, tail="plume",
            coat=(206, 182, 136), mark=(118, 92, 62), belly=(238, 226, 206),
            pat="spotted", eye=(142, 184, 140), eyeshape="round"),
          "groomer", "Washes one spot at a time, in order.",
          ("wheat spotted", "golden", "ivory")),
    Breed("mach", "Machbagral", R_EXOTIC, "a river delta",
          "Will get into water on purpose, which nobody can explain.",
          L(size=1.06, body=1.18, facew=1.14, faceh=0.92, cheek=1.24,
            ear=0.84, legs=0.80, fluff=0.20, tail="kink",
            coat=(132, 128, 120), mark=(78, 76, 72), belly=(190, 188, 182),
            pat="ticked", eye=(150, 178, 190), eyeshape="round"),
          "glutton", "Drinks from the tap. Will not drink from the bowl.",
          ("river grey", "red", "ivory")),

    # -- HEIRLOOM: cards somebody kept -----------------------------------
    Breed("gran", "The Grandmother's Persian", R_HEIRLOOM, "a card in a drawer",
          "Printed in 1961 and kept flat ever since.",
          L(size=1.20, body=1.08, facew=1.26, faceh=0.86, cheek=1.30,
            ear=0.70, flat=1.0, legs=0.72, fluff=0.96, tail="plume",
            coat=(232, 222, 206), mark=(192, 178, 158), belly=(248, 244, 238),
            pat="smoke", eye=(206, 160, 96), eyeshape="round"),
          "sleeper", "Occupies the middle of the bed and will not be moved.",
          ("antique cream", "blue", "chocolate")),
    Breed("blue12", "The Nineteen-Twelve Blue", R_HEIRLOOM, "the first catalogue",
          "The oldest card anybody has a photograph of.",
          L(size=1.06, body=1.02, facew=1.10, faceh=0.98, cheek=1.12,
            ear=0.90, legs=0.92, fluff=0.42, tail="plain",
            coat=(132, 142, 158), mark=(92, 102, 118), belly=(198, 206, 218),
            pat="solid", eye=(214, 178, 94), eyeshape="round"),
          "lap", "Sits upright beside you like it is being photographed.",
          ("old blue", "silver", "charcoal")),
    Breed("rose", "The Rosette Winner", R_HEIRLOOM, "a show in 1974",
          "Won everything there was to win and then retired to a cushion.",
          L(size=1.12, body=0.94, facew=1.04, faceh=1.08, cheek=1.00,
            ear=1.08, legs=1.06, fluff=0.80, tail="plume",
            coat=(198, 164, 104), mark=(120, 88, 48), belly=(240, 224, 194),
            pat="tabbywhite", eye=(176, 194, 110), eyeshape="almond",
            collar=(206, 170, 84)),
          "groomer", "Poses. There is no other word for it.",
          ("rosette gold", "red", "cream")),
    Breed("last", "The Last Of The Line", R_HEIRLOOM, "a breeder who stopped",
          "There will not be any more of these.",
          L(size=0.92, body=1.14, facew=0.98, faceh=1.10, cheek=0.94,
            ear=1.26, legs=0.88, fluff=0.26, tail="kink",
            coat=(84, 78, 88), mark=(50, 46, 54), belly=(140, 134, 146),
            pat="roan", eye=(168, 206, 164), eyeshape="almond"),
          "shadow", "Keeps to itself, and keeps an eye on everything.",
          ("ash", "red", "ivory")),

    # -- and four on rungs that were already busy ------------------------
    Breed("shed", "Shed Cat", R_COMMON, "the bottom of somebody's garden",
          "Lives in a shed. Considers the shed a career.",
          L(size=1.02, body=1.16, facew=1.06, faceh=0.96, cheek=1.14,
            ear=0.96, legs=0.84, fluff=0.30, tail="bob",
            coat=(138, 126, 110), mark=(88, 80, 70), belly=(198, 190, 178),
            pat="tabby", eye=(160, 178, 112), eyeshape="round"),
          "sleeper", "Sleeps on whatever was last put down.",
          ("dust tabby", "silver", "blue")),
    Breed("harb", "Harbour Tabby", R_UNCOMMON, "the end of a pier",
          "Fed by eleven boats and loyal to none of them.",
          L(size=1.08, body=1.04, facew=0.98, faceh=1.04, cheek=0.96,
            ear=1.24, legs=1.08, fluff=0.16, tail="whip",
            coat=(118, 122, 128), mark=(72, 76, 82), belly=(186, 190, 196),
            pat="tabbywhite", eye=(142, 176, 186), eyeshape="almond"),
          "busy", "Patrols. There is no other word for that either.",
          ("harbour grey", "black and white", "silver")),
    Breed("shad", "Silver Shaded", R_CHAMPION, "a breeder in Surrey",
          "Tipped with black, so it changes colour when it moves.",
          L(size=1.04, body=0.98, facew=1.14, faceh=0.94, cheek=1.16,
            ear=0.86, legs=0.90, fluff=0.88, tail="plume",
            coat=(236, 234, 230), mark=(126, 124, 128), belly=(250, 249, 247),
            pat="smoke", eye=(132, 186, 140), eyeshape="round"),
          "groomer", "Washes in the light where it shows best.",
          ("silver shaded", "golden", "blue")),
    Breed("sire", "The Champion's Sire", R_LEGEND, "the line behind the line",
          "Never shown. Every winner for a decade goes back to it.",
          L(size=1.16, body=1.10, facew=1.16, faceh=0.96, cheek=1.22,
            ear=1.02, legs=0.96, fluff=0.52, tail="plain",
            coat=(108, 92, 80), mark=(62, 52, 44), belly=(176, 162, 146),
            pat="solid", eye=(212, 184, 92), eyeshape="almond"),
          "lap", "Sits in the best chair as though it were always his.",
          ("seal brown", "black", "chocolate")),
)


MORE_BREEDS = (
    # -- ARCHIVE: the copies the company kept -----------------------------
    Breed("plate", "Plate One", R_ARCHIVE, "the top of the first sheet",
          "The first cat ever printed, in the corner where the ink ran.",
          L(size=1.08, body=1.26, facew=1.08, faceh=1.00, cheek=1.08,
            ear=1.36, legs=0.66, fluff=0.44, tail="kink",
            coat=(214, 198, 160), mark=(146, 128, 96), belly=(242, 234, 216),
            pat="tabbywhite", eye=(188, 174, 100), eyeshape="almond"),
          "lap", "Sits very still, as though being drawn.",
          ("ink and cream", "silver", "blue")),
    Breed("museum", "The Museum Copy", R_ARCHIVE, "a drawer in a basement",
          "Behind glass, in a building with a cloakroom.",
          L(size=1.22, body=1.12, facew=1.18, faceh=0.92, cheek=1.26,
            ear=0.76, flat=0.7, legs=0.78, fluff=0.92, tail="plume",
            coat=(216, 206, 190), mark=(160, 148, 132), belly=(244, 240, 234),
            pat="smoke", eye=(142, 178, 200), eyeshape="round"),
          "sleeper", "Settles somewhere and becomes part of the furniture.",
          ("dust and silver", "blue", "chocolate")),
    Breed("proof", "The Proof Sheet", R_ARCHIVE, "a printer's bin",
          "Should have been destroyed. Was not.",
          L(size=0.94, body=0.88, facew=0.92, faceh=1.14, cheek=0.86,
            ear=1.38, legs=1.26, fluff=0.10, tail="whip",
            coat=(238, 232, 212), mark=(88, 84, 80), belly=(248, 246, 240),
            pat="van", eye=(206, 196, 110), eyeshape="almond"),
          "shadow", "Appears in rooms you were sure you had shut.",
          ("off-white", "silver", "charcoal")),
    Breed("fndr", "The Founder's Cat", R_ARCHIVE, "a photograph on a wall",
          "Belonged to the man whose name is on the catalogue.",
          L(size=1.14, body=1.22, facew=1.04, faceh=1.02, cheek=1.02,
            ear=1.14, legs=0.88, fluff=0.30, tail="bob",
            coat=(132, 112, 88), mark=(78, 62, 46), belly=(198, 180, 154),
            pat="ticked", eye=(214, 190, 96), eyeshape="almond",
            collar=(206, 170, 84)),
          "climber", "Takes the highest seat in the room without asking.",
          ("sepia", "brown", "cinnamon")),

    # -- FOUNDATION ------------------------------------------------------
    Breed("pair", "The Original Pair", R_FOUNDATION, "a crate off a ship",
          "Two cats in 1903, and everything since.",
          L(size=1.10, body=1.06, facew=1.12, faceh=0.96, cheek=1.16,
            ear=0.94, legs=0.92, fluff=0.66, tail="plume",
            coat=(170, 142, 110), mark=(104, 82, 58), belly=(226, 208, 184),
            pat="blotched", eye=(170, 190, 120), eyeshape="round"),
          "warmth", "Picks the warmest corner and holds it against all comers.",
          ("ship's tabby", "red", "blue")),
    Breed("linez", "Line Zero", R_FOUNDATION, "before the records start",
          "Nobody knows where this one came from either.",
          L(size=0.96, body=0.92, facew=0.94, faceh=1.12, cheek=0.90,
            ear=1.32, legs=1.22, fluff=0.14, tail="kink",
            coat=(70, 68, 74), mark=(44, 42, 48), belly=(118, 114, 122),
            pat="solid", eye=(226, 198, 100), eyeshape="almond"),
          "shadow", "Walks the edge of every room, once, then settles.",
          ("pitch", "charcoal", "smoke")),
    Breed("import", "The First Import", R_FOUNDATION, "a quarantine shed",
          "Six weeks in a shed and then a hundred years of descendants.",
          L(size=1.18, body=1.16, facew=1.00, faceh=1.04, cheek=0.98,
            ear=1.08, legs=1.10, fluff=0.22, tail="plain",
            coat=(188, 160, 112), mark=(118, 92, 56), belly=(232, 216, 188),
            pat="spotted", eye=(182, 196, 106), eyeshape="almond"),
          "hunter", "Treats the hallway as a distance to be covered quickly.",
          ("harvest", "golden", "silver")),

    # -- HEIRLOOM --------------------------------------------------------
    Breed("wartime", "The Wartime Card", R_HEIRLOOM, "a tin under a floor",
          "Printed on the wrong paper because there was no other paper.",
          L(size=1.00, body=1.10, facew=1.06, faceh=0.98, cheek=1.10,
            ear=0.88, legs=0.82, fluff=0.48, tail="bob",
            coat=(158, 146, 124), mark=(100, 92, 76), belly=(214, 206, 190),
            pat="roan", eye=(164, 182, 128), eyeshape="round"),
          "sleeper", "Sleeps through everything, which is the point of it.",
          ("utility grey", "blue", "cream")),
    Breed("xmas58", "A Christmas Present, 1958", R_HEIRLOOM, "under a tree",
          "Still has the tape on the back of it.",
          L(size=0.90, body=0.98, facew=1.16, faceh=0.94, cheek=1.20,
            ear=1.04, legs=0.76, fluff=0.70, tail="pom",
            coat=(204, 148, 112), mark=(236, 230, 222), belly=(244, 238, 230),
            pat="bicolour", eye=(148, 186, 142), eyeshape="round"),
          "lap", "Arrives on a lap within a minute of anybody sitting down.",
          ("ribbon red", "cream", "silver")),
    Breed("framed", "The Framed One", R_HEIRLOOM, "a hallway in Lancashire",
          "Somebody put this in a frame and hung it in a hall.",
          L(size=1.16, body=0.94, facew=1.02, faceh=1.06, cheek=0.98,
            ear=1.20, legs=1.14, fluff=0.84, tail="plume",
            coat=(124, 134, 152), mark=(78, 86, 104), belly=(194, 202, 216),
            pat="smoke", eye=(214, 184, 92), eyeshape="almond"),
          "groomer", "Washes in front of the mirror, which cannot be an accident.",
          ("hall blue", "silver", "charcoal")),

    # -- LEGEND ----------------------------------------------------------
    Breed("frostc", "The Frost Cat", R_LEGEND, "a hallway in 1981",
          "An accident between two pedigrees that turned out beautifully.",
          L(size=1.02, body=1.00, facew=1.12, faceh=0.96, cheek=1.14,
            ear=0.92, legs=0.94, fluff=0.62, tail="plume",
            coat=(230, 228, 222), mark=(140, 138, 142), belly=(246, 246, 244),
            pat="smoke", eye=(150, 194, 136), eyeshape="round"),
          "groomer", "Sits where the light catches the tipping.",
          ("silver tipped", "golden", "chocolate")),
    Breed("chartreux", "The Blue Monk", R_LEGEND, "a monastery in France",
          "Blue, smiling, and entirely silent about it.",
          L(size=1.12, body=1.20, facew=1.20, faceh=0.90, cheek=1.28,
            ear=0.80, legs=0.78, fluff=0.28, tail="plain",
            coat=(132, 146, 160), mark=(96, 108, 122), belly=(190, 202, 214),
            pat="solid", eye=(222, 178, 86), eyeshape="round"),
          "lap", "Follows you from room to room and says nothing at all.",
          ("monastery blue", "silver", "charcoal")),
    Breed("ussuri", "Ussuri", R_LEGEND, "the Amur river",
          "Barely a domestic cat and does not pretend otherwise.",
          L(size=1.20, body=1.14, facew=0.96, faceh=1.08, cheek=0.90,
            ear=1.26, legs=1.24, fluff=0.18, tail="whip",
            coat=(158, 134, 98), mark=(88, 70, 48), belly=(212, 196, 170),
            pat="blotched", eye=(196, 186, 92), eyeshape="almond"),
          "hunter", "Patrols the far end of the room and watches the near one.",
          ("river tabby", "brown", "silver")),

    # -- CHAMPION --------------------------------------------------------
    Breed("bakery", "The Bakery Cat", R_CHAMPION, "behind a bread counter",
          "Round, tailless, and warm from standing near the ovens.",
          L(size=1.06, body=1.08, facew=1.14, faceh=0.94, cheek=1.20,
            ear=0.84, legs=0.80, fluff=0.90, tail="none",
            coat=(176, 160, 136), mark=(112, 100, 82), belly=(228, 218, 202),
            pat="tabby", eye=(176, 188, 110), eyeshape="round"),
          "warmth", "Rounds itself off on the warmest surface available.",
          ("flour tabby", "red", "blue")),
    Breed("orchard", "The Orchard Cat", R_CHAMPION, "under the apple trees",
          "Short at the back and convinced it is something wilder.",
          L(size=1.14, body=1.30, facew=1.08, faceh=0.98, cheek=1.12,
            ear=1.16, tuft=0.9, legs=0.62, fluff=0.40, tail="bob",
            coat=(150, 126, 96), mark=(90, 72, 52), belly=(206, 188, 164),
            pat="spotted", eye=(182, 174, 100), eyeshape="almond"),
          "busy", "Carries things from room to room with no plan for them.",
          ("orchard tabby", "silver", "cinnamon")),
    Breed("tiffanie", "Tiffanie", R_CHAMPION, "a London breeder",
          "A Burmilla that kept growing its coat.",
          L(size=1.00, body=1.10, facew=1.06, faceh=1.02, cheek=1.04,
            ear=1.40, legs=0.68, fluff=0.96, tail="pom",
            coat=(198, 168, 124), mark=(132, 104, 70), belly=(236, 222, 200),
            pat="ticked", eye=(166, 192, 124), eyeshape="round"),
          "groomer", "Spends most of the evening on the coat.",
          ("apricot", "chocolate", "blue")),

    # -- PEDIGREE --------------------------------------------------------
    Breed("javanese", "Javanese", R_PEDIGREE, "a cattery in Ontario",
          "A Siamese that went the long way round.",
          L(size=0.98, body=0.88, facew=0.90, faceh=1.16, cheek=0.84,
            ear=1.34, legs=1.18, fluff=0.52, tail="plume",
            coat=(228, 216, 192), mark=(112, 92, 86), belly=(244, 238, 228),
            pat="point", eye=(120, 172, 206), eyeshape="almond"),
          "busy", "Talks the whole way across the room and back.",
          ("red point", "charcoal", "silver")),
    Breed("orilong", "Oriental Longhair", R_PEDIGREE, "an English cattery",
          "Angles, mostly, with a tail on the end.",
          L(size=1.04, body=0.86, facew=0.88, faceh=1.18, cheek=0.82,
            ear=1.42, legs=1.28, fluff=0.60, tail="plume",
            coat=(146, 124, 102), mark=(92, 76, 62), belly=(204, 188, 170),
            pat="ticked", eye=(150, 196, 122), eyeshape="almond"),
          "climber", "Is on top of the wardrobe. It was always going to be.",
          ("havana", "silver", "lilac")),
    Breed("singa", "The Drain Cat", R_PEDIGREE, "a storm drain in Singapore",
          "The smallest cat in the book and the loudest about it.",
          L(size=0.72, body=0.94, facew=1.08, faceh=1.00, cheek=1.04,
            ear=1.30, legs=0.88, fluff=0.12, tail="plain",
            coat=(206, 182, 146), mark=(138, 112, 80), belly=(238, 226, 206),
            pat="ticked", eye=(176, 190, 112), eyeshape="round"),
          "lap", "Sits on the one thing you were about to pick up.",
          ("sepia agouti", "ivory", "fawn")),

    # -- EXOTIC ----------------------------------------------------------
    Breed("bare", "The Bare One", R_EXOTIC, "a draughty flat",
          "No coat at all, and warmer than anything that has one.",
          L(size=1.00, body=1.04, facew=1.10, faceh=0.98, cheek=1.06,
            ear=1.36, legs=1.04, fluff=0.0, skin=1.0, curl=0.0, tail="whip",
            coat=(206, 168, 158), mark=(170, 130, 122), belly=(224, 194, 186),
            pat="solid", eye=(160, 186, 150), eyeshape="almond"),
          "warmth", "Is under the blanket. Was always under the blanket.",
          ("bare pink", "charcoal", "blue")),
    Breed("kinka", "The Low One", R_EXOTIC, "a breeder's experiment",
          "Short legs, curled ears, and no apparent downside.",
          L(size=0.80, body=1.10, facew=1.10, faceh=0.96, cheek=1.12,
            ear=1.08, earcurl=1.0, legs=0.58, fluff=0.34, tail="plain",
            coat=(142, 132, 124), mark=(88, 80, 74), belly=(202, 194, 186),
            pat="tabby", eye=(178, 186, 124), eyeshape="round"),
          "busy", "Gets everywhere, slowly, and arrives pleased.",
          ("mushroom", "silver", "red")),

    # -- RARE ------------------------------------------------------------
    Breed("anatol", "Anatolian", R_RARE, "the shore of Lake Van",
          "Swims, which nobody asked it to do.",
          L(size=1.08, body=1.02, facew=1.00, faceh=1.02, cheek=1.00,
            ear=1.12, legs=1.06, fluff=0.44, tail="plume",
            coat=(240, 236, 230), mark=(188, 182, 174), belly=(248, 246, 244),
            pat="van", eye=(152, 188, 198), eyeshape="almond"),
          "hunter", "Is in the bath. There is no water in it, but still.",
          ("van white", "red", "silver")),
    Breed("stool", "The Footstool", R_RARE, "in front of the fire",
          "Bald and short-legged, and entirely untroubled by either.",
          L(size=0.76, body=1.14, facew=1.06, faceh=1.00, cheek=1.08,
            ear=1.28, legs=0.56, fluff=0.0, skin=1.0, tail="plain",
            coat=(212, 176, 166), mark=(176, 138, 130), belly=(230, 202, 194),
            pat="solid", eye=(170, 180, 142), eyeshape="round"),
          "warmth", "Sits on the radiator shelf like a loaf proving.",
          ("bare cream", "charcoal", "red")),

    # -- UNCOMMON --------------------------------------------------------
    Breed("pillow", "The Pillow Cat", R_UNCOMMON, "the spare room",
          "Folded ears on a round face, which is a lot of round.",
          L(size=0.96, body=1.06, facew=1.22, faceh=0.90, cheek=1.26,
            ear=0.92, fold=1.0, legs=0.82, fluff=0.56, tail="plain",
            coat=(186, 170, 148), mark=(124, 110, 92), belly=(232, 222, 206),
            pat="tabby", eye=(166, 184, 136), eyeshape="round"),
          "sleeper", "Folds up on the nearest soft thing and stays folded.",
          ("oatmeal", "blue", "cream")),
)


# The book, in tier order, which is the order the binder reads in.
BREEDS = tuple(sorted(BREEDS + _build_more() + NEW_BREEDS + MORE_BREEDS,
                      key=lambda b: (b.rarity, b.name)))


# ---------------------------------------------------------------------------
# THE ONES THAT ARE NOT IN THE CATALOGUE
#
# Five cats the shop has never heard of and will never send. They turn up
# at the front door instead, one at a time, with a long wait between
# them, and they do not appear in the binder at all until the first one
# is standing on the mat. Nothing about the shop, the packs, the odds or
# the ending counts them: the binder is still thirty-six, and these are
# whatever else happened while you were filling it.
#
# The first is somebody's actual cat, drawn from a photograph.
# ---------------------------------------------------------------------------
SECRETS = (
    Breed("kam", "Kucing Kampung", R_UNLISTED, "a doorway in Jakarta",
          "Walked in off the step, looked round once, and stayed.",
          L(size=1.02, body=0.98, facew=1.02, faceh=1.02, cheek=0.98,
            ear=1.18, legs=1.08, fluff=0.18, tail="plain",
            coat=(150, 136, 112), mark=(84, 74, 60), belly=(248, 246, 242),
            pat="tabbywhite", eye=(152, 176, 108), eyeshape="round",
            nose=(186, 128, 124), collar=(230, 138, 162)),
          "lap",
          "Sits just inside the door, facing out, in case of weather.",
          ("tabby and white", "silver", "red")),
    Breed("chp", "The Chip Shop Cat", R_UNLISTED, "the queue, every Friday",
          "Belongs to the street. Is fed by the whole of it.",
          L(size=1.16, body=1.3, facew=1.14, faceh=0.94, cheek=1.26,
            ear=0.86, legs=0.84, fluff=0.4, coat=(206, 146, 78),
            mark=(150, 94, 44), belly=(238, 214, 182), pat="tabby",
            eye=(200, 170, 70), eyeshape="round"),
          "glutton",
          "Has four homes and eats at all of them.",
          ("marmalade", "cream", "charcoal")),
    Breed("dck", "The Dockyard Tom", R_UNLISTED, "the container port",
          "One ear short, one eye narrowed, and entirely in charge.",
          L(size=1.1, body=1.18, facew=1.2, faceh=0.96, cheek=1.3, ear=0.92,
            legs=1.0, fluff=0.22, coat=(108, 106, 104), mark=(66, 64, 64),
            belly=(156, 154, 152), pat="tabby", eye=(198, 162, 66),
            eyeshape="almond"),
          "shadow",
          "Walks the whole flat at three in the morning. Checking.",
          ("storm grey", "charcoal", "silver")),
    Breed("lib", "The Library Cat", R_UNLISTED, "between the shelves",
          "Sleeps on whatever you were about to read.",
          L(size=1.0, body=1.02, facew=1.0, faceh=1.06, cheek=1.0, ear=1.1,
            legs=1.0, fluff=0.82, tail="plume", coat=(94, 88, 96),
            mark=(236, 232, 226), belly=(240, 236, 230), pat="bicolour",
            eye=(140, 186, 150), eyeshape="round"),
          "sleeper",
          "Chooses the warmest lap in the room and does not negotiate.",
          ("ink and paper", "charcoal", "silver")),
    Breed("nbs", "The Night Bus Cat", R_UNLISTED, "the last bus, every night",
          "Gets on at the terminus. Nobody knows where it gets off.",
          L(size=1.04, body=0.9, facew=0.94, faceh=1.06, cheek=0.86,
            ear=1.3, legs=1.22, fluff=0.12, coat=(54, 52, 56),
            mark=(36, 34, 38), belly=(78, 76, 82), pat="smoke",
            eye=(232, 196, 92), eyeshape="almond"),
          "shadow",
          "Is in the room. Was not in the room. Is in the room again.",
          ("midnight", "charcoal", "smoke")),
)

# ---------------------------------------------------------------------------
# THE FIVE THEY PRINT FOR THE HALL
#
# Convention exclusives. They are not in the catalogue, they are not on
# the resale site, and no amount of money will get you one: the only
# place these are printed is the show, and the only way to a pack of
# them is to stand in the queue, know a forgery when you see one, or
# talk a man by a fire door down to a number he can live with.
#
# Unlike the five that turn up at the door, these are in the binder from
# the start, as five empty slots with a heading over them. That is the
# whole point of them - a thing you cannot have yet is only a reason to
# go back on Saturday if you know it is there.
# ---------------------------------------------------------------------------
EXPO_BREEDS = (
    Breed("bis", "Best In Show", R_EXPO, "the top table, every year",
          "Has been brushed for four hours and would like you to know it.",
          L(size=1.24, body=1.06, facew=1.14, faceh=0.96, cheek=1.22,
            ear=0.78, legs=0.84, fluff=0.98, tail="plume",
            coat=(238, 234, 228), mark=(196, 188, 180), belly=(252, 251, 249),
            pat="smoke", eye=(126, 176, 206), eyeshape="round",
            nose=(214, 164, 162)),
          "groomer",
          "Settles where the light is best and waits to be admired.",
          ("show silver", "chocolate", "blue")),
    Breed("hal", "The Hall Cat", R_EXPO, "behind the fire door",
          "Lives in the venue. Hears the shutters go up from four "
          "rooms away.",
          # First draft of this was lean, long-legged and whip-tailed,
          # which is the Brazilian Shorthair to within 0.967 of its own
          # outline - the same cat twice, under two names. The shape it
          # has now was picked by measuring six of them against all 109
          # others and taking the one with the most room round it.
          L(size=0.9, body=1.06, facew=1.12, faceh=0.94, cheek=1.1,
            ear=1.42, legs=0.7, fluff=0.3, tail="pom",
            coat=(88, 92, 98), mark=(58, 62, 68), belly=(132, 136, 142),
            pat="ticked", eye=(214, 206, 92), eyeshape="almond"),
          "shadow",
          "Knows every door in the building and uses the ones you cannot.",
          ("hall grey", "ivory", "red")),
    Breed("jdg", "The Judge\'s Own", R_EXPO, "under the top table",
          "Cannot be entered, for reasons everybody has agreed not to "
          "discuss.",
          L(size=1.02, body=1.24, facew=1.18, faceh=0.92, cheek=1.32,
            ear=0.88, legs=0.78, fluff=0.34, tail="bob",
            coat=(176, 140, 96), mark=(112, 84, 54), belly=(234, 216, 190),
            pat="blotched", eye=(142, 182, 120), eyeshape="round",
            collar=(206, 170, 84)),
          "lap",
          "Sits on the paperwork. The paperwork gets done round it.",
          ("honey tabby", "charcoal", "silver")),
    Breed("trs", "The Trestle Table Tabby", R_EXPO, "on the merchandise",
          "Asleep on the thing you were going to buy.",
          L(size=1.1, body=1.34, facew=1.0, faceh=1.0, cheek=1.04,
            ear=1.02, legs=0.9, fluff=0.2, tail="plain",
            coat=(142, 122, 100), mark=(86, 70, 56), belly=(206, 188, 164),
            pat="tabby", eye=(170, 154, 86), eyeshape="almond"),
          "sleeper",
          "Finds the one flat surface anybody needed and takes it.",
          ("table tabby", "blue", "white")),
    Breed("que", "The Queue Cat", R_EXPO, "four hundred people deep",
          "Works the line from the front to the back and back again.",
          L(size=0.88, body=0.94, facew=0.96, faceh=1.12, cheek=0.9,
            ear=1.18, legs=1.04, fluff=0.46, tail="pom",
            coat=(214, 160, 98), mark=(238, 234, 230), belly=(246, 240, 232),
            pat="van", eye=(196, 168, 72), eyeshape="round"),
          "glutton",
          "Has been fed by eleven strangers and is working on a twelfth.",
          ("ginger and white", "black and white", "grey and white")),
)

# ---------------------------------------------------------------------------
# THE KITTEN SERIES
#
# The second collection. It does not exist until the first one is
# finished - the company announces it the day you own all hundred - and
# then the website grows a page it did not have, with three products on
# it that take you back to an empty binder.
#
# They are kittens, so they share a build: big head, big ears, short
# legs, not much cat. That is the problem with a themed set and the
# reason this one is twelve and not thirty. Everything that CAN vary
# inside "kitten" is pushed as far as it goes - seven kinds of tail,
# fluff from nothing to a dandelion, ears from folded to enormous - and
# the pairwise check in cat_test.py is what says whether it worked.
# ---------------------------------------------------------------------------
KITTENS = (
    Breed("sock", "The Sock Thief", R_COMMON, "under the bed, with it",
          "Has one. Will not be giving it back.",
          L(size=0.74, body=0.92, facew=1.16, faceh=0.94, cheek=1.04,
            ear=1.14, legs=0.72, fluff=0.22, tail="plain",
            coat=(154, 132, 106), mark=(96, 78, 60), belly=(214, 198, 174),
            pat="tabby", eye=(146, 180, 112), eyeshape="round"),
          "hunter",
          "Takes one sock from every wash and hides it somewhere new.",
          ("brown tabby", "silver", "blue")),
    Breed("wks", "Three Weeks Old", R_COMMON, "a cardboard box in a kitchen",
          "Walks like the floor is new to it, which it is.",
          L(size=0.62, body=0.80, facew=1.22, faceh=1.00, cheek=1.12,
            ear=0.80, legs=0.60, fluff=0.52, tail="pom",
            coat=(186, 176, 164), mark=(140, 128, 118), belly=(238, 234, 228),
            pat="solid", eye=(132, 164, 196), eyeshape="round"),
          "sleeper",
          "Sleeps in a heap, wakes, falls over, sleeps again.",
          ("dove grey", "cream", "white")),
    Breed("gout", "The One That Got Out", R_UNCOMMON, "the gap in the fence",
          "Found at the end of the road, entirely pleased with itself.",
          L(size=0.80, body=1.04, facew=1.06, faceh=0.96, cheek=0.94,
            ear=1.30, legs=0.90, fluff=0.10, tail="whip",
            coat=(118, 112, 110), mark=(74, 70, 70), belly=(176, 170, 166),
            pat="ticked", eye=(206, 184, 86), eyeshape="almond"),
          "shadow",
          "Is at the door the moment it opens, every time, without fail.",
          ("storm grey", "black", "red")),
    Breed("sbx", "Shoebox Number Four", R_UNCOMMON, "the fourth box along",
          "One of five, and the one that climbed out first.",
          L(size=0.78, body=0.98, facew=1.10, faceh=1.04, cheek=1.08,
            ear=1.02, legs=0.78, fluff=0.76, tail="plume",
            coat=(206, 158, 96), mark=(238, 232, 224), belly=(244, 238, 230),
            pat="bicolour", eye=(188, 166, 92), eyeshape="round"),
          "lap",
          "Climbs into whatever has most recently been emptied.",
          ("ginger and white", "cream", "grey and white")),
    Breed("loud", "The Loud One", R_RARE, "the whole street, at four a.m.",
          "Has a great deal to say and says all of it.",
          L(size=0.76, body=0.88, facew=0.98, faceh=1.14, cheek=0.86,
            ear=1.44, legs=0.86, fluff=0.06, tail="kink",
            coat=(222, 210, 188), mark=(96, 80, 76), belly=(240, 234, 222),
            pat="point", eye=(118, 174, 206), eyeshape="almond"),
          "busy",
          "Announces every room it enters, including ones it has left.",
          ("seal point", "blue point", "chocolate")),
    Breed("fsnw", "First Snow", R_RARE, "a doorstep in January",
          "White, and under the impression that this is remarkable.",
          L(size=0.82, body=1.00, facew=1.14, faceh=0.98, cheek=1.14,
            ear=0.74, legs=0.68, fluff=0.94, tail="plume",
            coat=(244, 242, 238), mark=(216, 212, 206), belly=(250, 250, 248),
            pat="solid", eye=(128, 186, 198), eyeshape="round"),
          "warmth",
          "Finds the radiator within a minute of arriving anywhere.",
          ("white", "ivory", "cream")),
    Breed("clmb", "The Climber", R_PEDIGREE, "the top of the curtains",
          "Got up there. Has not worked out the rest of it.",
          L(size=0.84, body=0.90, facew=1.00, faceh=1.02, cheek=0.92,
            ear=1.20, legs=1.02, fluff=0.28, tail="plain",
            coat=(142, 116, 150), mark=(92, 74, 100), belly=(206, 194, 212),
            pat="smoke", eye=(206, 190, 96), eyeshape="almond"),
          "climber",
          "Is always one shelf higher than you last looked.",
          ("lilac smoke", "blue", "charcoal")),
    Breed("quiet", "The Quiet One", R_PEDIGREE, "behind the washing machine",
          "Says nothing. Misses nothing.",
          L(size=0.72, body=1.10, facew=1.04, faceh=1.08, cheek=1.00,
            ear=0.88, legs=0.66, fluff=0.40, tail="bob",
            coat=(88, 84, 92), mark=(56, 54, 60), belly=(140, 136, 146),
            pat="roan", eye=(150, 196, 142), eyeshape="round"),
          "groomer",
          "Watches the room from the one place you would not look.",
          ("charcoal", "silver", "blue")),
    Breed("runt", "The Runt", R_CHAMPION, "the end of the row",
          "Smallest of the litter and first to every bowl.",
          L(size=0.58, body=1.06, facew=1.24, faceh=0.90, cheek=1.22,
            ear=0.96, legs=0.62, fluff=0.18, tail="none",
            coat=(176, 142, 96), mark=(118, 88, 54), belly=(228, 208, 180),
            pat="blotched", eye=(182, 198, 106), eyeshape="round"),
          "glutton",
          "Eats as though somebody is about to take the bowl away.",
          ("honey", "charcoal", "blue")),
    Breed("mitt", "Four White Mittens", R_CHAMPION, "a breeder's back room",
          "Four of them, and the papers to prove it.",
          L(size=0.88, body=0.96, facew=1.08, faceh=1.00, cheek=1.06,
            ear=1.06, legs=0.94, fluff=0.62, tail="plume",
            coat=(104, 88, 94), mark=(246, 244, 240), belly=(248, 246, 242),
            pat="gloves", eye=(126, 170, 204), eyeshape="round"),
          "lap",
          "Puts one white foot on you and considers the matter settled.",
          ("seal mitted", "blue", "chocolate")),
    Breed("bkit", "Best Kitten In Show", R_LEGEND, "the junior class",
          "Eleven weeks old and already insufferable about it.",
          L(size=0.92, body=1.02, facew=1.18, faceh=0.92, cheek=1.18,
            ear=0.82, legs=0.74, fluff=0.90, tail="plume",
            coat=(238, 226, 206), mark=(198, 180, 152), belly=(250, 246, 240),
            pat="tabbywhite", eye=(214, 186, 88), eyeshape="round"),
          "groomer",
          "Sits in the best light in the room and waits to be noticed.",
          ("show cream", "chocolate", "blue")),
    Breed("spot", "The Spotted One", R_EXOTIC, "a litter nobody expected",
          "Came out spotted. Neither parent is spotted.",
          L(size=0.86, body=1.00, facew=1.06, faceh=0.98, cheek=1.02,
            ear=1.24, legs=0.92, fluff=0.12, tail="whip",
            coat=(212, 180, 120), mark=(104, 80, 52), belly=(240, 226, 202),
            pat="spotted", eye=(186, 192, 100), eyeshape="almond"),
          "hunter", "Stalks the other ones from behind the sofa.",
          ("wheat spotted", "silver", "cinnamon")),
    Breed("tuft", "Tufts", R_EXOTIC, "a hybrid litter in a spare room",
          "The ears arrived before the rest of it did.",
          L(size=0.80, body=0.92, facew=1.10, faceh=1.00, cheek=1.06,
            ear=1.48, tuft=1.0, legs=0.80, fluff=0.30, tail="pom",
            coat=(190, 150, 104), mark=(126, 92, 58), belly=(232, 214, 188),
            pat="ticked", eye=(170, 190, 112), eyeshape="round"),
          "climber", "Gets somewhere high and then cannot get down.",
          ("sand", "red", "fawn")),
    Breed("keep", "The One They Kept", R_HEIRLOOM, "a litter of six",
          "Five went to homes. This one was already asleep on the sofa.",
          L(size=0.90, body=1.08, facew=1.20, faceh=0.90, cheek=1.24,
            ear=0.76, legs=0.70, fluff=0.86, tail="plume",
            coat=(224, 206, 180), mark=(170, 148, 118), belly=(246, 240, 230),
            pat="tabbywhite", eye=(196, 164, 98), eyeshape="round"),
          "lap", "Has chosen a person and the matter is closed.",
          ("old cream", "blue", "silver")),
    Breed("pud", "The Puddle Kitten", R_COMMON, "a wet car park",
          "Found in weather nobody should be found in.",
          L(size=0.68, body=0.96, facew=1.14, faceh=0.96, cheek=1.08,
            ear=1.06, legs=0.76, fluff=0.08, tail="kink",
            coat=(108, 104, 100), mark=(66, 64, 62), belly=(166, 162, 158),
            pat="tabby", eye=(152, 184, 156), eyeshape="round"),
          "glutton", "Eats like the car park might come back.",
          ("wet grey", "black", "silver")),
    Breed("win", "The Window Kitten", R_RARE, "a flat across the road",
          "Spends all day watching a window that is not yours.",
          L(size=0.84, body=0.86, facew=0.94, faceh=1.16, cheek=0.88,
            ear=1.32, legs=1.08, fluff=0.66, tail="plume",
            coat=(214, 206, 196), mark=(118, 104, 96), belly=(242, 238, 232),
            pat="point", eye=(126, 178, 210), eyeshape="almond"),
          "climber", "Is on the windowsill. Has always been on the windowsill.",
          ("frost point", "blue point", "cream")),
    Breed("bold", "The Bold One", R_CHAMPION, "the front of the box",
          "First out, first up, first into everything.",
          L(size=0.94, body=1.12, facew=1.02, faceh=0.94, cheek=1.00,
            ear=1.14, legs=1.00, fluff=0.24, tail="bob",
            coat=(166, 120, 78), mark=(102, 68, 40), belly=(224, 200, 170),
            pat="blotched", eye=(200, 178, 88), eyeshape="almond"),
          "busy", "Has already done whatever you were about to stop it doing.",
          ("copper tabby", "red", "charcoal")),
    Breed("plate2", "Plate One, Reprinted", R_ARCHIVE, "the second sheet",
          "They ran it again, smaller, and nobody has forgiven them.",
          L(size=0.76, body=0.98, facew=1.14, faceh=0.96, cheek=1.10,
            ear=0.98, legs=0.78, fluff=0.50, tail="plain",
            coat=(220, 206, 172), mark=(152, 136, 106), belly=(244, 238, 222),
            pat="tabbywhite", eye=(184, 172, 104), eyeshape="round"),
          "lap", "Sits in the middle of whatever is being read.",
          ("ink and cream", "blue", "silver")),
    Breed("ffoal", "The Foundation Kitten", R_FOUNDATION, "a line being started",
          "Everything after this one is descended from it.",
          L(size=0.88, body=1.06, facew=1.00, faceh=1.08, cheek=0.96,
            ear=1.30, legs=0.94, fluff=0.20, tail="plain",
            coat=(176, 148, 104), mark=(104, 80, 50), belly=(226, 208, 180),
            pat="spotted", eye=(196, 190, 100), eyeshape="almond"),
          "climber", "Is already on the shelf you were going to use.",
          ("harvest", "silver", "red")),
    Breed("legk", "The Prizewinner's Kitten", R_LEGEND, "a cardboard box at a show",
          "Eight weeks old with a rosette already pinned to the box.",
          L(size=0.92, body=0.90, facew=1.04, faceh=1.06, cheek=1.00,
            ear=1.12, legs=1.10, fluff=0.78, tail="plume",
            coat=(222, 194, 146), mark=(146, 112, 68), belly=(244, 232, 210),
            pat="tabbywhite", eye=(182, 198, 116), eyeshape="almond"),
          "groomer", "Washes in front of anybody who stops to look.",
          ("rosette gold", "cream", "chocolate")),
    Breed("pedk", "The Papers Kitten", R_PEDIGREE, "a folder of documents",
          "Came with more paperwork than a car.",
          L(size=0.82, body=0.90, facew=0.92, faceh=1.18, cheek=0.86,
            ear=1.38, legs=1.02, fluff=0.40, tail="whip",
            coat=(226, 212, 190), mark=(104, 86, 80), belly=(242, 236, 226),
            pat="point", eye=(126, 176, 208), eyeshape="almond"),
          "busy", "Has opinions and shares all of them.",
          ("seal point", "blue", "silver")),
    Breed("rark", "The Shy One", R_RARE, "behind the boiler",
          "Took three weeks to come out and has not gone back.",
          L(size=0.78, body=1.16, facew=1.02, faceh=1.04, cheek=0.98,
            ear=0.86, legs=0.66, fluff=0.54, tail="bob",
            coat=(96, 92, 100), mark=(60, 58, 64), belly=(152, 148, 158),
            pat="roan", eye=(160, 198, 150), eyeshape="round"),
          "shadow", "Watches from under something, and will not be moved.",
          ("slate", "charcoal", "blue")),
    Breed("unck", "The Noisy One", R_UNCOMMON, "the top of the stairs",
          "Found the stairs. Has told the whole house about the stairs.",
          L(size=0.72, body=0.88, facew=1.00, faceh=1.14, cheek=0.90,
            ear=1.40, legs=0.86, fluff=0.16, tail="kink",
            coat=(150, 140, 130), mark=(94, 88, 82), belly=(206, 198, 190),
            pat="ticked", eye=(166, 190, 132), eyeshape="almond"),
          "busy", "Announces the stairs again.",
          ("stair grey", "red", "cream")),
    Breed("heirk", "The Hand-Me-Down", R_HEIRLOOM, "a second-hand basket",
          "Came with the basket, which came with the house.",
          L(size=0.86, body=1.04, facew=1.18, faceh=0.92, cheek=1.22,
            ear=0.80, legs=0.72, fluff=0.92, tail="pom",
            coat=(206, 192, 170), mark=(150, 136, 114), belly=(240, 234, 224),
            pat="smoke", eye=(150, 182, 164), eyeshape="round"),
          "sleeper", "Sleeps in the basket it arrived in and nowhere else.",
          ("old wool", "blue", "cream")),
    Breed("exok", "The Odd One Out", R_EXOTIC, "a litter of ordinary cats",
          "Nobody can account for the ears.",
          L(size=0.84, body=1.02, facew=1.04, faceh=0.98, cheek=1.00,
            ear=1.44, earcurl=1.0, legs=0.96, fluff=0.22, tail="bob",
            coat=(164, 140, 112), mark=(100, 82, 62), belly=(216, 200, 178),
            pat="blotched", eye=(188, 180, 108), eyeshape="almond"),
          "hunter", "Hears the tin opening from two rooms away.",
          ("toast", "silver", "charcoal")),
    Breed("under", "The Understudy", R_ARCHIVE, "the second-best negative",
          "Photographed on the same afternoon and never printed.",
          L(size=0.82, body=1.22, facew=1.04, faceh=1.06, cheek=1.00,
            ear=1.40, legs=0.64, fluff=0.28, tail="whip",
            coat=(206, 196, 178), mark=(142, 132, 114), belly=(238, 234, 226),
            pat="ticked", eye=(180, 170, 104), eyeshape="almond"),
          "shadow", "Sits just out of the light, watching the lit part.",
          ("negative grey", "red", "blue")),
    Breed("photo", "The One In The Photograph", R_LEGEND, "a framed picture",
          "Somebody kept the photograph. Nobody kept the cat's name.",
          L(size=0.96, body=0.86, facew=1.16, faceh=0.92, cheek=1.24,
            ear=0.72, legs=1.20, fluff=0.94, tail="pom",
            coat=(230, 218, 198), mark=(168, 150, 124), belly=(246, 242, 234),
            pat="bicolour", eye=(138, 178, 198), eyeshape="round"),
          "groomer", "Sits where a photograph would have been taken from.",
          ("sepia cream", "charcoal", "blue")),
    Breed("first", "The First Litter", R_FOUNDATION, "the beginning of a line",
          "Every cat in the catalogue goes back to one of these.",
          L(size=0.86, body=1.18, facew=1.12, faceh=1.06, cheek=1.10,
            ear=1.34, legs=0.82, fluff=0.34, tail="kink",
            coat=(196, 164, 112), mark=(128, 98, 58), belly=(236, 220, 192),
            pat="spotted", eye=(206, 196, 110), eyeshape="almond"),
          "climber",
          "Behaves as though the flat has always belonged to it.",
          ("old gold", "silver", "cinnamon")),
)
# ---------------------------------------------------------------------------
# THE THIRD SERIES: THE WORKING CATS
#
# Cats with jobs. Announced when the kittens are all in, the same way the
# kittens were announced when the catalogue was.
# ---------------------------------------------------------------------------
WORKING = (
    Breed("ship", "The Ship's Cat", R_COMMON, "a cargo deck",
          "Signed on at Rotterdam and has not been ashore since.",
          L(size=1.04, body=1.14, facew=1.02, faceh=0.98, cheek=1.06,
            ear=1.00, legs=0.94, fluff=0.24, tail="plain",
            coat=(128, 124, 118), mark=(80, 78, 74), belly=(192, 188, 182),
            pat="tabbywhite", eye=(150, 180, 190), eyeshape="almond"),
          "busy", "Walks the whole flat twice before settling anywhere.",
          ("deck grey", "black and white", "red")),
    Breed("mill", "The Mill Cat", R_COMMON, "between the looms",
          "Deaf as a post, which in a mill is an advantage.",
          L(size=0.98, body=1.08, facew=1.16, faceh=0.92, cheek=1.22,
            ear=0.78, legs=0.80, fluff=0.60, tail="pom",
            coat=(196, 186, 170), mark=(132, 124, 110), belly=(234, 228, 218),
            pat="solid", eye=(132, 170, 196), eyeshape="round"),
          "sleeper", "Sleeps through everything, including you.",
          ("cotton white", "cream", "silver")),
    Breed("pub", "The Pub Cat", R_UNCOMMON, "the end of the bar",
          "Has a stool. Nobody else sits on the stool.",
          L(size=1.14, body=1.24, facew=1.20, faceh=0.90, cheek=1.28,
            ear=0.82, legs=0.76, fluff=0.34, tail="plain",
            coat=(178, 136, 92), mark=(116, 82, 48), belly=(228, 206, 178),
            pat="tabby", eye=(176, 186, 104), eyeshape="round"),
          "glutton", "Appears whenever anything is unwrapped.",
          ("bitter brown", "red", "cream")),
    Breed("signal", "The Signal Box Cat", R_UNCOMMON, "beside the levers",
          "Knows the timetable better than the man who works there.",
          L(size=0.96, body=0.92, facew=1.24, faceh=0.88, cheek=1.30,
            ear=0.74, legs=1.18, fluff=0.90, tail="whip",
            coat=(104, 108, 114), mark=(64, 68, 74), belly=(168, 172, 178),
            pat="ticked", eye=(206, 188, 92), eyeshape="almond"),
          "climber", "Sits where it can see the door and the window at once.",
          ("signal grey", "black", "silver")),
    Breed("church", "The Church Cat", R_RARE, "the back of the nave",
          "Attends everything. Contributes nothing.",
          L(size=1.08, body=1.00, facew=1.06, faceh=1.04, cheek=1.04,
            ear=0.90, legs=0.96, fluff=0.88, tail="plume",
            coat=(70, 68, 72), mark=(44, 42, 46), belly=(124, 120, 126),
            pat="solid", eye=(180, 200, 150), eyeshape="round"),
          "groomer", "Washes in the quietest corner of the room.",
          ("vestry black", "charcoal", "blue")),
    Breed("bodega", "The Bodega Cat", R_RARE, "on top of the crisps",
          "Lives on the counter and is the reason there are no mice.",
          L(size=0.88, body=1.18, facew=1.10, faceh=0.94, cheek=1.14,
            ear=1.20, legs=0.70, fluff=0.18, tail="kink",
            coat=(202, 158, 102), mark=(134, 96, 54), belly=(236, 218, 190),
            pat="blotched", eye=(184, 180, 100), eyeshape="round"),
          "hunter", "Sits on whatever is for sale.",
          ("shop ginger", "cream", "silver")),
    Breed("light", "The Lighthouse Cat", R_EXOTIC, "ninety-two steps up",
          "Goes up at dusk and comes down at dawn, every day, for years.",
          L(size=1.20, body=0.88, facew=0.92, faceh=1.14, cheek=0.86,
            ear=1.30, legs=1.36, fluff=0.42, tail="plume",
            coat=(226, 220, 208), mark=(150, 144, 136), belly=(244, 242, 236),
            pat="van", eye=(140, 184, 204), eyeshape="almond"),
          "climber", "Is at the top of something. Always.",
          ("lamp white", "silver", "blue")),
    Breed("theatre", "The Theatre Cat", R_PEDIGREE, "the wings, stage left",
          "Walks on during the second act. Every night. On purpose.",
          L(size=1.02, body=0.94, facew=1.00, faceh=1.08, cheek=0.98,
            ear=1.14, legs=1.10, fluff=0.76, tail="plume",
            coat=(142, 118, 148), mark=(90, 72, 96), belly=(206, 190, 210),
            pat="smoke", eye=(214, 190, 96), eyeshape="almond"),
          "busy", "Crosses the room at the least convenient moment.",
          ("curtain mauve", "charcoal", "silver")),
    Breed("hotel", "The Hotel Cat", R_PEDIGREE, "the lobby, by the fire",
          "On the register. Has a room number.",
          L(size=1.16, body=1.06, facew=1.18, faceh=0.92, cheek=1.24,
            ear=0.80, legs=0.84, fluff=0.94, tail="plume",
            coat=(214, 192, 158), mark=(148, 124, 92), belly=(242, 232, 214),
            pat="tabbywhite", eye=(160, 192, 128), eyeshape="round",
            collar=(206, 170, 84)),
          "lap", "Chooses the best seat in the room and keeps it warm.",
          ("lobby gold", "cream", "chocolate")),
    Breed("brew", "The Brewery Cat", R_CHAMPION, "between the barrels",
          "Three hundred years of these, in a row, in that cellar.",
          L(size=1.10, body=1.28, facew=1.08, faceh=0.96, cheek=1.12,
            ear=1.06, legs=0.74, fluff=0.28, tail="bob",
            coat=(118, 96, 76), mark=(70, 56, 42), belly=(182, 164, 144),
            pat="roan", eye=(190, 178, 96), eyeshape="almond"),
          "shadow", "Keeps to the dark end and watches the lit one.",
          ("cellar brown", "black", "silver")),
    Breed("station", "The Station Cat", R_LEGEND, "platform two",
          "Has a plaque. Had a funeral. Has a successor.",
          L(size=1.06, body=0.84, facew=1.12, faceh=0.96, cheek=1.18,
            ear=0.72, legs=1.32, fluff=0.96, tail="pom",
            coat=(160, 146, 122), mark=(98, 88, 70), belly=(220, 210, 192),
            pat="tabby", eye=(198, 186, 100), eyeshape="round",
            collar=(170, 170, 176)),
          "lap", "Greets everybody who comes in, then goes back to sleep.",
          ("platform tabby", "silver", "red")),
    Breed("market", "The Market Cat", R_HEIRLOOM, "under the fish stall",
          "Every trader says it is theirs. It is nobody's.",
          L(size=1.22, body=1.16, facew=1.00, faceh=1.02, cheek=1.00,
            ear=1.28, legs=1.14, fluff=0.20, tail="whip",
            coat=(186, 170, 140), mark=(112, 100, 78), belly=(230, 222, 204),
            pat="spotted", eye=(176, 194, 110), eyeshape="almond"),
          "glutton", "Is wherever food has most recently been opened.",
          ("market tabby", "red", "charcoal")),
)


# ---------------------------------------------------------------------------
# THE FOURTH SERIES: THE OLD GUARD
#
# Cats that have been at it a long time. The last series the company has
# in it, and the one it charges most for.
# ---------------------------------------------------------------------------
OLD_GUARD = (
    Breed("threeleg", "The Three-Legged One", R_RARE, "a bad winter, years ago",
          "Manages perfectly well and would rather not discuss it.",
          L(size=1.00, body=1.30, facew=1.22, faceh=0.88, cheek=1.28,
            ear=0.74, legs=0.60, fluff=0.30, tail="bob",
            coat=(146, 138, 128), mark=(92, 86, 80), belly=(204, 198, 190),
            pat="blotched", eye=(168, 186, 120), eyeshape="round"),
          "sleeper", "Picks one spot a day and commits to it.",
          ("weathered tabby", "silver", "blue")),
    Breed("deaf", "The Deaf One", R_RARE, "a quiet house",
          "Has not heard a tin open in four years and still knows.",
          L(size=1.06, body=0.96, facew=1.22, faceh=0.90, cheek=1.26,
            ear=0.72, legs=0.86, fluff=0.82, tail="plume",
            coat=(240, 238, 234), mark=(196, 194, 190), belly=(249, 248, 246),
            pat="solid", eye=(138, 180, 200), eyeshape="round"),
          "glutton", "Arrives at the bowl before anybody has touched it.",
          ("old white", "cream", "silver")),
    Breed("ear", "The One With The Ear", R_EXOTIC, "a disagreement in 2009",
          "Won, by all accounts.",
          L(size=1.12, body=1.22, facew=1.14, faceh=0.92, cheek=1.26,
            ear=0.88, legs=0.82, fluff=0.16, tail="kink",
            coat=(116, 112, 106), mark=(70, 68, 64), belly=(176, 172, 166),
            pat="ticked", eye=(204, 180, 88), eyeshape="almond"),
          "shadow", "Walks the edges at night, checking.",
          ("scar grey", "black", "red")),
    Breed("mouser", "The Retired Mouser", R_PEDIGREE, "a barn, formerly",
          "Did forty years of it. Does not intend to do any more.",
          L(size=1.18, body=1.26, facew=1.10, faceh=0.96, cheek=1.16,
            ear=1.02, legs=0.70, fluff=0.44, tail="plain",
            coat=(154, 126, 94), mark=(94, 74, 52), belly=(212, 194, 170),
            pat="tabby", eye=(182, 190, 102), eyeshape="round"),
          "warmth", "Lies by the warmest thing and watches the mice go by.",
          ("barn tabby", "silver", "cream")),
    Breed("twenty", "The Twenty-Year-Old", R_CHAMPION, "the same chair, since 2005",
          "Older than the chair. Older than the house, nearly.",
          L(size=0.94, body=1.04, facew=1.18, faceh=0.94, cheek=1.22,
            ear=0.84, legs=0.74, fluff=0.90, tail="plume",
            coat=(212, 206, 196), mark=(158, 152, 142), belly=(242, 240, 236),
            pat="smoke", eye=(170, 190, 150), eyeshape="round"),
          "sleeper", "Has not moved. Will not move. Is fine.",
          ("frosted", "blue", "cream")),
    Breed("slow", "The Slow Walk", R_CHAMPION, "the length of the hall",
          "Gets there. Takes its time about it.",
          L(size=1.08, body=1.30, facew=1.04, faceh=1.00, cheek=1.08,
            ear=1.10, legs=0.64, fluff=0.36, tail="plain",
            coat=(132, 118, 104), mark=(82, 72, 62), belly=(196, 184, 170),
            pat="roan", eye=(176, 188, 128), eyeshape="almond"),
          "lap", "Arrives eventually and stays once it has.",
          ("ash tabby", "charcoal", "red")),
    Breed("remember", "The One Who Remembers", R_LEGEND, "the old flat",
          "Still goes to where the radiator used to be.",
          L(size=1.02, body=0.90, facew=0.96, faceh=1.14, cheek=0.90,
            ear=1.26, legs=1.20, fluff=0.68, tail="plume",
            coat=(96, 104, 120), mark=(60, 66, 80), belly=(164, 174, 190),
            pat="smoke", eye=(214, 186, 94), eyeshape="almond"),
          "shadow", "Sits in a spot that used to be warm.",
          ("memory blue", "charcoal", "silver")),
    Breed("winter", "The Last Winter", R_HEIRLOOM, "a cold February",
          "Everybody thought that was it. It was not.",
          L(size=1.14, body=1.08, facew=1.16, faceh=0.94, cheek=1.20,
            ear=0.78, legs=0.92, fluff=0.96, tail="plume",
            coat=(222, 226, 232), mark=(164, 170, 180), belly=(246, 248, 250),
            pat="smoke", eye=(148, 186, 196), eyeshape="round"),
          "warmth", "Finds the radiator within seconds of arriving anywhere.",
          ("hoarfrost", "blue", "silver")),
    Breed("sun", "The Sunbather", R_FOUNDATION, "wherever the light is",
          "Has followed the sun round one room for fifteen years.",
          L(size=1.10, body=1.18, facew=1.12, faceh=0.94, cheek=1.18,
            ear=0.90, legs=0.80, fluff=0.50, tail="plain",
            coat=(222, 180, 118), mark=(152, 112, 62), belly=(242, 226, 198),
            pat="tabby", eye=(198, 190, 104), eyeshape="round"),
          "warmth", "Moves four times a day, with the light, and no further.",
          ("sunlit", "blue", "charcoal")),
    Breed("grand", "Grandmother", R_ARCHIVE, "four generations back",
          "Everything in the cat room is descended from this one.",
          L(size=1.24, body=1.12, facew=1.24, faceh=0.88, cheek=1.30,
            ear=0.74, flat=0.5, legs=0.76, fluff=0.98, tail="plume",
            coat=(200, 190, 176), mark=(142, 134, 122), belly=(238, 234, 228),
            pat="tortie", eye=(176, 196, 142), eyeshape="round",
            collar=(206, 170, 84)),
          "lap", "Sits in the middle of the room and lets it happen round her.",
          ("old tortie", "cream", "blue")),
)

KITTEN_BY_RARITY = tuple(tuple(b for b in KITTENS if b.rarity == r)
                         for r in range(SOLD_RARITIES))
KITTEN_KEYS = frozenset(b.key for b in KITTENS)


_BOOKS = {}
_BOOK_KEYS = {}


class Series:
    """One collection: a set of cats, a shelf in the shop, and the series
    that has to be finished before it is announced.

    This started as `if series == "kitten" else`, in four places, which
    was fine for two collections and is the wrong shape for four.
    Everything that walks a collection - rolling a card, retiring a
    breed, deciding whether a product is still worth selling, drawing
    the binder - reads this.
    """
    __slots__ = ("key", "name", "cats", "by_rarity", "keys", "after",
                 "shelf", "blurb", "news")

    def __init__(self, key, name, cats, after=None, shelf=None, blurb="",
                 news=()):
        self.key = key
        self.name = name
        self.cats = cats
        self.after = after          # the series that unlocks this one
        self.shelf = shelf          # its page in the shop, if it has one
        self.blurb = blurb
        self.news = news            # the three screens that announce it
        self.by_rarity = tuple(tuple(b for b in cats if b.rarity == r)
                               for r in range(SOLD_RARITIES))
        self.keys = frozenset(b.key for b in cats)


SERIES_TAB = {"kitten": "KITTENS", "working": "WORKING CATS",
              "old": "OLD GUARD"}

SERIES = (
    Series("cat", "the catalogue", BREEDS, shelf="standard",
           blurb="The book itself."),
    Series("kitten", "the Kitten Series", KITTENS, after="cat",
           shelf="kitten",
           blurb="Twelve - and then some - new cards, none of them in the "
                 "old book.",
           news=(("A hundred of a hundred.",
                  "Every breed in the catalogue, in a binder, on a desk, in "
                  "a flat you have nearly paid for. There is nothing left "
                  "in the book to find."),
                 ("MEOWRDER would like a word.",
                  "The email came at nine minutes past midnight, which is "
                  "when these things are sent. They have been working on "
                  "something. They are very excited about it. They would "
                  "like you to be excited about it too."),
                 ("The Kitten Series.",
                  "New cards, none of them in the old book, and a page on "
                  "the website that was not there this morning. You know "
                  "exactly what this is. You are going to buy them "
                  "anyway."))),
    Series("working", "the Working Cats", WORKING, after="kitten",
           shelf="working",
           blurb="Cats with jobs. Every one of them is somebody's, and "
                 "none of them is anybody's.",
           news=(("Every kitten, in the book.",
                  "Two collections finished, and the second one took longer "
                  "than the first, which they will have known it would."),
                 ("They have sent another email.",
                  "Same hour, same tone, a different font. There is a "
                  "phrase in the second paragraph about honouring the cats "
                  "that work for a living, and underneath it a price."),
                 ("The Working Cats.",
                  "A ship's cat, a mill cat, a cat with a plaque on "
                  "platform two. Twelve cards about labour, sold at a "
                  "margin."))),
    Series("old", "the Old Guard", OLD_GUARD, after="working",
           shelf="old",
           blurb="Cats that have been at it a long time, on the thickest "
                 "card the company has ever cut.",
           news=(("Three collections, finished.",
                  "The binder does not shut properly any more. You have "
                  "stopped trying to make it."),
                 ("The last one, they say.",
                  "They have said that before. This time the email is "
                  "shorter, and there is a photograph of an old cat in a "
                  "chair, and it is quite hard to be cynical about it."),
                 ("The Old Guard.",
                  "Ten cats that have done their time, on card you could "
                  "stand a cup on. They are not cheap and nobody pretends "
                  "they are."))),
)
BY_SERIES = {x.key: x for x in SERIES}

ALL_BREEDS = (BREEDS + SECRETS + EXPO_BREEDS + KITTENS + WORKING
              + OLD_GUARD)
BY_KEY = {b.key: b for b in ALL_BREEDS}
# The two counters on the binder used to be "everything that is not a
# stray" and "the strays". A third kind of cat that is neither breaks
# that in the quietest possible way - "104 of 100 breeds" - so what
# counts as a catalogue breed is now the catalogue, and not a process of
# elimination.
LISTED = frozenset(b.key for b in BREEDS)

# The kittens go INTO the binder rather than beside it: once the series
# is announced the book is a hundred and twelve, sorted together by tier
# the same way the first hundred are, and the counter on the cover says
# so. What it cannot do is say so from the start - a hundred and twelve
# slots on day one would give away that there is a second series before
# anybody has earned the right to be told, and twelve of them could
# never be filled. So there are two books and the state picks one.
BOOK = tuple(sorted(BREEDS + KITTENS, key=lambda b: (b.rarity, b.name)))
BOOK_KEYS = LISTED | KITTEN_KEYS
BY_RARITY = tuple(tuple(b for b in BREEDS if b.rarity == r)
                  for r in range(SOLD_RARITIES))


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
# One routine, thirty-six sets of numbers. It is built once per breed,
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
    lbot = h * 0.95
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


# A hundred breeds will not fit through the handful of knobs that held
# forty: squeeze them all through the same ones and the silhouettes start
# landing on top of each other whatever the numbers say. A tail is a
# quarter of an outline on its own, so there are seven of them now.
#
#   none   nothing at all        pom    a ball (the Japanese Bobtail)
#   bob    a short thick stub    kink   a long one with a hook in it
#   plain  the ordinary one      whip   long and very thin
#   plume  long and very thick
TAIL_LEN = {"plain": 1.0, "plume": 1.0, "whip": 1.18, "kink": 1.0,
            "bob": 0.40}
TAIL_FAT = {"plain": 1.0, "plume": 1.5, "whip": 0.58, "kink": 0.9,
            "bob": 1.5}


def _bell(P, w, h):
    """The two sides of the sitting body, and where its base is.

    The coat bumps follow these points, so a longhair swells along its
    own outline instead of around a circle somewhere inside it.
    """
    body, fluff, legs = P["body"], P["fluff"], P["legs"]
    cx = w * 0.5
    # Leg length used to change nothing about a sitting cat, because the
    # legs are drawn INSIDE the body outline - which made a Munchkin and
    # an ordinary moggy the same silhouette. A short-legged cat sits as a
    # low wide loaf and a long-legged one sits tall and narrow with its
    # forelegs showing below the body, and now the outline says so.
    top = h * (0.34 + 0.055 * (1.0 - legs))
    bot = h * (0.93 - 0.045 * (legs - 1.0))
    wide = 1.0 + 0.13 * (1.0 - legs)
    htop = w * 0.175 * body * (1.0 + 0.18 * fluff) * wide
    hbot = w * 0.300 * body * (1.0 + 0.08 * fluff) * wide
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
    fat = TAIL_FAT.get(tail, 1.0)
    run = TAIL_LEN.get(tail, 1.0)
    out = []
    if pose == "curl":
        thick = h * (0.05 + 0.04 * fluff) * fat
        n = 18
        for i in range(n):
            f = i / (n - 1)
            a = -0.10 + f * 2.7 * run
            out.append((w * (0.56 + 0.37 * math.cos(a)),
                        h * (0.74 + 0.26 * math.sin(a)),
                        thick * (0.6 + 0.4 * (1 - f))))
        return out
    thick = h * (0.028 + 0.026 * fluff) * fat
    n = 22
    for i in range(n):
        f = i / (n - 1)
        a = -0.35 + f * 2.2 * run
        tx = w * 0.5 + w * (0.19 * body + 0.155 * math.sin(a))
        ty = h * (0.90 - 0.48 * run * f ** 1.2)
        if tail == "kink" and f > 0.82:      # the hook in the end
            tx += w * 0.10 * (f - 0.82) / 0.18
            ty += h * 0.05 * (f - 0.82) / 0.18
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
        elif P["earcurl"] > 0.4:
            # ... and a curled ear goes the other way: it stands up and
            # then bends BACK over itself, away from the face, which is
            # the whole of what an American Curl is.
            out.append(("poly", [
                (bx - sx * ew * 0.72, by + eh * 0.22),
                (bx - sx * ew * 0.10, by - eh * 0.88),
                (bx + sx * ew * 0.62, by - eh * 1.02),
                (bx + sx * ew * 0.96, by - eh * 0.52),
                (bx + sx * ew * 0.52, by - eh * 0.46),
                (bx + sx * ew * 0.86, by + eh * 0.10)]))
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


def _stand_metrics(P, w, h):
    """Every part of the side view measured in one place.

    Four routines need these numbers - the body, the markings, the tail
    and the head - and when they each worked them out for themselves the
    tail came out as a crescent floating behind the cat.
    """
    leg = h * 0.27 * (0.86 + 0.24 * P["legs"])
    bh = h * 0.37 * (0.9 + 0.2 * P["body"]) * (1 + 0.08 * P["fluff"])
    back = h - leg
    top = back - bh
    body = pygame.Rect(w * 0.20, top, w * 0.58, bh)
    return leg, bh, top, back, body


def _tail_path_stand(P, w, h):
    """Up off the hip and over, which is how a cat on its feet carries it."""
    if P["tail"] in ("none", "pom"):
        return []
    leg, bh, top, back, body = _stand_metrics(P, w, h)
    fat = TAIL_FAT.get(P["tail"], 1.0)
    run = TAIL_LEN.get(P["tail"], 1.0)
    thick = h * (0.028 + 0.024 * P["fluff"]) * fat
    p0 = (body.x + w * 0.03, top + bh * 0.42)
    p1 = (body.x - w * 0.16 * run, top + bh * 0.10)
    p2 = (body.x - w * 0.06 * run, top - h * 0.24 * run)
    out = []
    for i in range(20):
        f = i / 19
        g = 1 - f
        x = g * g * p0[0] + 2 * g * f * p1[0] + f * f * p2[0]
        y = g * g * p0[1] + 2 * g * f * p1[1] + f * f * p2[1]
        out.append((x, y, thick * (0.62 + 0.38 * (1 - f))))
    return out


def _shapes_stand(P, w, h):
    """On its feet, side on, facing right.

    The third pose, and the one the cat room needed: a sitting cat slid
    across a floor is a cardboard cut-out being dragged, and everything
    worth doing in that room - eating, playing, scratching, prowling -
    happens on four legs.
    """
    fluff = P["fluff"]
    leg, bh, top, back, body = _stand_metrics(P, w, h)
    out = []
    for tx, ty, tr in _tail_path_stand(P, w, h):
        out.append(("circle", (tx, ty), tr))
    if P["tail"] == "pom":
        out.append(("circle", (body.x - w * 0.01, top + bh * 0.30),
                    h * 0.07 * (1 + fluff)))

    lw = w * 0.055
    for lx in (0.30, 0.64):              # the far pair, behind the body
        out.append(("ellipse", (w * lx, back - bh * 0.22, lw, leg * 1.04)))
        out.append(("ellipse", (w * lx - lw * 0.2, h - leg * 0.17,
                                lw * 1.4, leg * 0.19)))
    out.append(("ellipse", body))
    out.append(("ellipse", (w * 0.52, top - bh * 0.07, w * 0.30, bh * 1.10)))
    out.append(("ellipse", (w * 0.26, top + bh * 0.04, w * 0.26, bh * 1.02)))
    lw2 = w * 0.062
    for lx in (0.24, 0.58):              # the near pair
        out.append(("ellipse", (w * lx, back - bh * 0.26, lw2, leg * 1.08)))
        out.append(("ellipse", (w * lx - lw2 * 0.22, h - leg * 0.19,
                                lw2 * 1.46, leg * 0.21)))
    if fluff > 0.3:                      # a ruff, round the shoulders
        rw = w * (0.15 + 0.08 * fluff)
        out.append(("ellipse", (w * 0.70 - rw * 0.5, top - bh * 0.14,
                                rw, bh * 0.94)))
    return out


def _head_box_stand(P, w, h):
    leg, bh, top, back, body = _stand_metrics(P, w, h)
    hw = w * 0.30 * P["facew"]
    hh = h * 0.34 * P["faceh"]
    return pygame.Rect(round(w * 0.80 - hw * 0.5), round(top - hh * 0.52),
                       round(hw), round(hh))


def _shapes_head_stand(P, w, h):
    out = []
    hb = _head_box_stand(P, w, h)
    ear = P["ear"]
    eh = hb.h * 0.60 * ear
    ew = hb.w * 0.44 * (0.8 + 0.3 * ear)
    # the neck, so the head is not balanced on a corner
    out.append(("ellipse", (hb.centerx - hb.w * 0.62, hb.centery,
                            hb.w * 0.9, hb.h * 0.9)))
    for bx, lean in ((hb.centerx - hb.w * 0.30, -0.55),
                     (hb.centerx + hb.w * 0.14, 0.3)):
        by = hb.y + hb.h * 0.26
        if P["fold"] > 0.4:
            out.append(("ellipse", (bx - ew * 0.5, by - eh * 0.30,
                                    ew, eh * 0.84)))
        else:
            out.append(("poly", [
                (bx - ew * 0.46, by + eh * 0.20),
                (bx + lean * ew * 0.55, by - eh),
                (bx + ew * 0.52, by + eh * 0.06)]))
    out.append(("ellipse", hb))
    ch = hb.w * 0.46 * P["cheek"]
    out.append(("ellipse", (hb.x + hb.w * 0.02, hb.y + hb.h * 0.42,
                            ch, hb.h * 0.56)))
    mw = hb.w * (0.50 - 0.14 * P["flat"])
    mh = hb.h * (0.40 - 0.12 * P["flat"])
    out.append(("ellipse", (hb.right - mw * 0.72, hb.bottom - mh * 1.06,
                            mw, mh)))
    return out


def _stand_marks(surf, P, w, h, hb, rng):
    """One routine for every pattern, laid out along a flank.

    The sitting markings are built around a bell-shaped front view and
    would put a cat's spine where its shoulder is when it turns sideways,
    so the side view gets its own - simplified, because it is seen at a
    third the size and usually moving.
    """
    pat = P["pat"]
    c = P["mark"]
    leg, bh, top, back, body = _stand_metrics(P, w, h)

    if pat in ("solid", "smoke", "ticked", "roan"):
        s2 = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s2, (*P["belly"], 120),
                            (body.x + body.w * 0.12, body.centery,
                             body.w * 0.76, body.h * 0.60))
        if pat == "smoke":
            pygame.draw.ellipse(s2, (*c, 70), (body.x, top - 2,
                                               body.w, body.h * 0.62))
        if pat in ("ticked", "roan"):
            for _ in range(130):
                x = rng.uniform(body.x - w * 0.04, body.right + w * 0.08)
                y = rng.uniform(top - h * 0.04, h * 0.95)
                g = pygame.Surface((2, max(2, round(h * 0.02))),
                                   pygame.SRCALPHA)
                g.fill((*c, rng.randint(60, 150)))
                s2.blit(g, (round(x), round(y)))
        surf.blit(s2, (0, 0))
    elif pat in ("tabby", "blotched"):
        lw = max(2, round(h * 0.024))
        for i in range(7):
            f = i / 6
            x = body.x + body.w * (0.10 + 0.76 * f)
            pygame.draw.line(surf, c, (round(x), round(top + bh * 0.08)),
                             (round(x - w * 0.014), round(back - bh * 0.06)),
                             lw)
        for i, (tx, ty, tr) in enumerate(_tail_path_stand(P, w, h)):
            if (i // 3) % 2 == 0:
                pygame.draw.circle(surf, c, (round(tx), round(ty)), round(tr))
        for k in range(3):
            pygame.draw.line(surf, c,
                             (round(hb.x + hb.w * (0.18 + 0.15 * k)),
                              round(hb.y + hb.h * 0.08)),
                             (round(hb.x + hb.w * (0.24 + 0.15 * k)),
                              round(hb.y + hb.h * 0.32)), 2)
    elif pat == "spotted":
        for row in range(4):
            fy = row / 3
            y = top + bh * (0.20 + 0.58 * fy)
            for i in range(7 - row % 2):
                fx = (i + 0.4 + (row % 2) * 0.3) / 7
                x = body.x + body.w * (0.08 + 0.84 * fx)
                r = w * (0.018 - 0.005 * fy) * rng.uniform(0.8, 1.3)
                pygame.draw.ellipse(surf, c, (x - r, y - r * 0.8,
                                              r * 2, r * 1.6))
    elif pat in ("point", "gloves"):
        s2 = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s2, (*c, 225), (hb.x - hb.w * 0.08, hb.y,
                                            hb.w * 1.16, hb.h * 1.2))
        for lx in (0.24, 0.30, 0.58, 0.64):
            pygame.draw.ellipse(s2, (*c, 215), (w * lx - 2, h - leg * 0.78,
                                                w * 0.07, leg * 0.8))
        for tx, ty, tr in _tail_path_stand(P, w, h):
            pygame.draw.circle(s2, (*c, 205), (round(tx), round(ty)),
                               round(tr))
        surf.blit(s2, (0, 0))
        if pat == "gloves":
            for lx in (0.24, 0.30, 0.58, 0.64):
                pygame.draw.ellipse(surf, P["belly"],
                                    (w * lx - w * 0.014, h - leg * 0.2,
                                     w * 0.086, leg * 0.22))
    elif pat == "tabbywhite":
        P2 = dict(P)
        P2["pat"] = "tabby"
        _stand_marks(surf, P2, w, h, hb, rng)
        _stand_marks_white(surf, dict(P, mark=P["belly"]), w, h, hb)
    elif pat == "van":
        _marks_van(surf, P, w, h, hb, rng, "stand")
    elif pat == "bicolour":
        s2 = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s2, (*c, 255), (body.x + body.w * 0.08,
                                            body.centery - bh * 0.04,
                                            body.w * 0.82, bh * 0.60))
        for lx in (0.24, 0.30, 0.58, 0.64):
            pygame.draw.ellipse(s2, (*c, 255), (w * lx - w * 0.014,
                                                h - leg * 0.40,
                                                w * 0.086, leg * 0.42))
        pygame.draw.ellipse(s2, (*c, 255), (hb.x + hb.w * 0.40,
                                            hb.y + hb.h * 0.44,
                                            hb.w * 0.64, hb.h * 0.62))
        surf.blit(s2, (0, 0))
    else:                                  # tortie
        ginger = (206, 134, 66)
        for i in range(12):
            col = c if i % 2 else ginger
            x = rng.uniform(body.x, body.right)
            y = rng.uniform(top, back)
            rw = w * rng.uniform(0.04, 0.09)
            rh = h * rng.uniform(0.05, 0.11)
            s2 = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s2, (*col, 220), (x - rw, y - rh,
                                                  rw * 2, rh * 2))
            surf.blit(s2, (0, 0))


def _face_side(surf, P, w, h, hb, shut, shine=0.0):
    """One eye, one ear lining, and a nose on the front of the muzzle."""
    ew = hb.w * 0.21
    eh = hb.h * (0.17 if P["eyeshape"] == "round" else 0.13)
    ex = hb.centerx + hb.w * 0.16
    ey = hb.centery - hb.h * 0.06
    eye = P["eye"]
    col = eye[2] if eye[0] == "odd" else eye
    _eye(surf, P, ex, ey, ew, eh, col, shut, shine)
    if P["fold"] < 0.4:
        inner = mix(P["nose"], P["coat"], 0.35)
        ear = P["ear"]
        eh2 = hb.h * 0.56 * ear
        ew2 = hb.w * 0.46 * (0.8 + 0.3 * ear)
        bx = hb.centerx + hb.w * 0.16
        by = hb.y + hb.h * 0.24
        pygame.draw.polygon(surf, inner, [
            (round(bx - ew2 * 0.24), round(by + eh2 * 0.06)),
            (round(bx + ew2 * 0.16), round(by - eh2 * 0.66)),
            (round(bx + ew2 * 0.30), round(by + eh2 * 0.02))])
    mw = hb.w * (0.52 - 0.14 * P["flat"])
    nx = hb.right - mw * 0.12
    ny = hb.bottom - hb.h * (0.32 - 0.10 * P["flat"])
    nr = hb.w * 0.09
    pygame.draw.polygon(surf, P["nose"], [
        (round(nx - nr), round(ny - nr * 0.4)),
        (round(nx + nr * 0.5), round(ny - nr * 0.2)),
        (round(nx - nr * 0.2), round(ny + nr * 0.8))])
    pygame.draw.arc(surf, shade(P["mark"], 0.75),
                    (nx - nr * 2.2, ny, nr * 2.4, nr * 1.8), 3.3, 5.6, 2)
    wh = pygame.Surface((w, h), pygame.SRCALPHA)
    for k in range(3):
        y0 = ny + nr * (0.1 + k * 0.5)
        pygame.draw.line(wh, (*CREAM, int(90 + 70 * shine)),
                         (round(nx - nr), round(y0)),
                         (round(nx + hb.w * (0.45 + 0.08 * k)),
                          round(y0 - hb.h * (0.12 - k * 0.08))), 1)
    surf.blit(wh, (0, 0))


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


def _marks_van(surf, P, w, h, hb, rng, pose='sit'):
    """A white cat with its colour kept to the cap and the tail.

    The one pattern where the BASE is the white and the markings are the
    only colour on the animal, which is why it reads from across a room.
    """
    c = P["mark"]
    s2 = pygame.Surface((w, h), pygame.SRCALPHA)
    if pose == "stand":
        pygame.draw.ellipse(s2, (*c, 240), (hb.x + hb.w * 0.06, hb.y - 2,
                                            hb.w * 0.92, hb.h * 0.62))
    else:
        pygame.draw.ellipse(s2, (*c, 240), (hb.centerx - hb.w * 0.46,
                                            hb.y - hb.h * 0.04,
                                            hb.w * 0.92, hb.h * 0.56))
        for sx in (-1, 1):            # the cap comes down over each ear
            pygame.draw.ellipse(s2, (*c, 240),
                                (hb.centerx + sx * hb.w * 0.34 - hb.w * 0.2,
                                 hb.y - hb.h * 0.16, hb.w * 0.4, hb.h * 0.4))
    path = (_tail_path_stand(P, w, h) if pose == "stand"
            else _tail_path(P, w, h, pose))
    for tx, ty, tr in path:
        pygame.draw.circle(s2, (*c, 235), (round(tx), round(ty)),
                           round(tr * 1.05))
    surf.blit(s2, (0, 0))
    _belly_wash(surf, P, w, h, 60)


def _marks_solid(surf, P, w, h, hb, rng, pose='sit'):
    _belly_wash(surf, P, w, h, 95)


def _marks_tabbywhite(surf, P, w, h, hb, rng, pose='sit'):
    """Stripes, and then the white over the top of them.

    The commonest cat in the world and the one pattern the table could
    not make: bicolour paints white over a plain coat, tabby draws
    stripes on one, and a cat off a doorstep is both at once. The white
    comes from the belly colour so the stripes can keep the mark colour.
    """
    _marks_tabby(surf, P, w, h, hb, rng, pose)
    white = dict(P)
    white["mark"] = P["belly"]
    if pose == "stand":
        _stand_marks_white(surf, white, w, h, hb)
    else:
        _marks_bicolour(surf, white, w, h, hb, rng, pose)


def _stand_marks_white(surf, P, w, h, hb):
    c = P["mark"]
    leg, bh, top, back, body = _stand_metrics(P, w, h)
    s2 = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s2, (*c, 255), (body.x + body.w * 0.08,
                                        body.centery - bh * 0.04,
                                        body.w * 0.82, bh * 0.60))
    for lx in (0.24, 0.30, 0.58, 0.64):
        pygame.draw.ellipse(s2, (*c, 255), (w * lx - w * 0.014,
                                            h - leg * 0.40,
                                            w * 0.086, leg * 0.42))
    pygame.draw.ellipse(s2, (*c, 255), (hb.x + hb.w * 0.40,
                                        hb.y + hb.h * 0.44,
                                        hb.w * 0.64, hb.h * 0.62))
    surf.blit(s2, (0, 0))


_MARKS = {"tabby": _marks_tabby, "blotched": _marks_blotched,
          "tabbywhite": _marks_tabbywhite,
          "spotted": _marks_spotted, "ticked": _marks_ticked,
          "point": _marks_point, "gloves": _marks_gloves,
          "bicolour": _marks_bicolour, "tortie": _marks_tortie,
          "van": _marks_van,
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
    if pose == "sit" and P.get("earcurl", 0) > 0.4:
        inner = mix(P["nose"], P["coat"], 0.35)
        eh2 = hb.h * 0.62 * P["ear"]
        ew2 = hb.w * 0.34 * (0.8 + 0.3 * P["ear"])
        for sx in (-1, 1):
            bx = hb.centerx + sx * hb.w * 0.34
            by = hb.y + hb.h * 0.30
            pygame.draw.polygon(surf, inner, [
                (round(bx - sx * ew2 * 0.30), round(by + eh2 * 0.06)),
                (round(bx + sx * ew2 * 0.02), round(by - eh2 * 0.60)),
                (round(bx + sx * ew2 * 0.46), round(by - eh2 * 0.60)),
                (round(bx + sx * ew2 * 0.30), round(by - eh2 * 0.08))])
    elif pose == "sit" and P["fold"] < 0.4:
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


def _collar(surf, P, w, h, hb, pose, level, acc, head_prims=()):
    """A collar at level 4, a tag at 7, and a bell when it retires.

    Drawn as a RING and not as an arc across the chest. A strap that
    stops at the edge of the neck is a bib: it reads as something lying
    on the cat rather than something fastened round it. So the whole
    ellipse is drawn - the far side of it as well as the near side - and
    then the head and cheeks are erased out of it, which is what puts
    the back of the band behind the neck where it belongs.

    The erase is a mask blitted with BLEND_RGBA_MIN: white everywhere
    except the head, which is transparent, so the minimum of the two
    alphas leaves the collar showing only where the head is not.
    """
    if level < COLLAR_AT:
        return
    # Leather first, rarity second. Taking the rarity colour straight
    # gave the uncommon breeds a green strap, which reads as a fish.
    # A breed may name its own colour instead, and then it is worn as
    # given - somebody chose it in a shop rather than the house buying
    # another brown strap.
    col = P.get("collar") or mix(RUG, acc, 0.30)
    lip = mix(col, CREAM, 0.42)
    band = pygame.Surface((w, h), pygame.SRCALPHA)

    if pose == "curl":
        bw = hb.w * 1.02
        br = pygame.Rect(hb.centerx - bw * 0.42, hb.bottom - hb.h * 0.26,
                         bw, hb.h * 0.55)
        tk = max(4, round(h * 0.05))
        pygame.draw.arc(band, shade(col, 0.45), br.inflate(2, 2), 3.88, 5.62,
                        tk + 2)
        pygame.draw.arc(band, col, br, 3.9, 5.6, tk)
        surf.blit(band, (0, 0))
        return

    # ONLY the near half of the ring is drawn - the far half is behind
    # the neck, and drawing it anyway left a complete circle lying on top
    # of the fur like a saucer. The ends of the arc sit at the widest
    # part of the ellipse, which is exactly where a strap goes out of
    # sight. Which half is "near" depends on which way the cat is facing:
    # head on it is the lower half, side on it is the half toward you.
    if pose == "stand":
        # a neck seen from the side is a cylinder end-on, so its collar
        # is a tall narrow ellipse and not a flat one
        cx = hb.x + hb.w * 0.10
        cy = hb.bottom - hb.h * 0.10
        bw, bh = hb.w * 0.46, hb.h * 1.05
        tk = max(4, round(h * 0.044))
        lo, hi = 1.62, 4.66
        tag_at = (cx - bw * 0.16, cy + bh * 0.46)
    else:
        cx = hb.centerx
        cy = hb.bottom + h * 0.014
        bw, bh = hb.w * 0.80, h * 0.150
        tk = max(5, round(h * 0.050))
        lo, hi = 3.12, TAU
        tag_at = (cx, cy + bh * 0.5 + tk * 0.3)

    br = pygame.Rect(round(cx - bw * 0.5), round(cy - bh * 0.5),
                     round(bw), round(bh))
    pygame.draw.arc(band, shade(col, 0.42), br.inflate(3, 3), lo - 0.02,
                    hi, tk + 3)
    pygame.draw.arc(band, col, br, lo, hi, tk)
    pygame.draw.arc(band, lip, br.inflate(0, -max(2, tk - 2)),
                    lo + 0.38, hi - 0.28, max(2, tk // 3))

    # take the head out of it: that is the whole trick
    if head_prims:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 255))
        _paint(mask, head_prims, (0, 0, 0, 0))
        band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(band, (0, 0))

    # the buckle sits on the near side, off to one side of the throat
    bx = cx - bw * (0.26 if pose != "stand" else 0.34)
    by = cy + bh * (0.30 if pose != "stand" else 0.10)
    pygame.draw.rect(surf, mix(LAMP, TEA, 0.4),
                     (round(bx), round(by), max(4, round(h * 0.035)),
                      max(4, round(h * 0.030))), border_radius=2)

    if level >= TAG_AT:
        tx, ty = tag_at
        r = max(4, round(h * 0.036))
        pygame.draw.line(surf, shade(col, 0.6), (round(tx), round(ty - r)),
                         (round(tx), round(ty)), 2)
        if level >= BELL_AT:
            pygame.draw.circle(surf, mix(LAMP, EMBER, 0.35),
                               (round(tx), round(ty)), r)
            pygame.draw.circle(surf, shade(EMBER, 0.65),
                               (round(tx), round(ty)), r, 1)
            pygame.draw.line(surf, shade(EMBER, 0.5),
                             (tx - r * 0.6, ty + r * 0.3),
                             (tx + r * 0.6, ty + r * 0.3), 2)
            pygame.draw.circle(surf, mix(CREAM, LAMP, 0.4),
                               (round(tx - r * 0.3), round(ty - r * 0.35)),
                               max(1, r // 3))
        else:
            pygame.draw.circle(surf, mix(TEA, LAMP, 0.4),
                               (round(tx), round(ty)), r)
            pygame.draw.circle(surf, shade(TEA, 0.6), (round(tx), round(ty)),
                               r, 1)


# -- one finished cat -------------------------------------------------------
_cats = {}
CAT_RATIO = 0.95          # a sitting cat is this much wider than it is tall


def cat_surface(breed, pose="sit", height=140, shut=False, level=1,
                variant=0, shiny=False):
    """A cat at a level in a coat, built once and cached."""
    level = int(clamp(level, 1, MAX_LEVEL))
    key = (breed.key, pose, int(height), shut, level, variant, bool(shiny))
    got = _cats.get(key)
    if got is not None:
        return got
    look = breed.look
    if variant or shiny:
        coat, mark, belly = coat_colours(breed, variant, shiny)
        look = dict(look)
        look["coat"], look["mark"], look["belly"] = coat, mark, belly
    P = groom(look, level)
    shine = (level - 1) / (MAX_LEVEL - 1)
    h = max(24, int(height * P["size"]))
    if pose == "curl":
        h = int(h * 0.66)
        w = int(h * 1.42)
    elif pose == "stand":
        h = int(h * 0.80)
        w = int(h * 1.46)
    else:
        w = int(h * CAT_RATIO)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    sil = pygame.Surface((w, h), pygame.SRCALPHA)

    head_prims = []
    if pose == "curl":
        prims = _shapes_curl(P, w, h)
        hb = _head_box_curl(P, w, h)
        head_prims = [("ellipse", hb)]
        prims = prims + head_prims
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
    elif pose == "stand":
        head_prims = _shapes_head_stand(P, w, h)
        prims = _shapes_stand(P, w, h) + head_prims
        hb = _head_box_stand(P, w, h)
    else:
        head_prims = _shapes_head(P, w, h)
        prims = _shapes_sit(P, w, h) + head_prims
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
    if pose == "stand":
        _stand_marks(marks, P, w, h, hb, random.Random(breed.key))
    else:
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
    if pose == "stand":
        cr = pygame.Surface((w, h), pygame.SRCALPHA)
        leg, bh, top, back, body = _stand_metrics(P, w, h)
        for lx in (0.30, 0.64):          # the far legs, in shadow
            pygame.draw.ellipse(cr, (*shade(P["coat"], 0.5), 110),
                                (w * lx, back - bh * 0.2, w * 0.055, leg))
        surf.blit(cr, (0, 0))
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

    if shiny:
        sp = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(breed.key + "shiny")
        for _ in range(9):
            a = rng.uniform(0, TAU)
            rr = rng.uniform(0.3, 0.52)
            px = w * (0.5 + math.cos(a) * rr)
            py = h * (0.5 + math.sin(a) * rr * 0.9)
            k = rng.uniform(0.5, 1.0)
            r0 = max(2, int(h * 0.028 * k))
            pygame.draw.line(sp, (*CREAM, 210), (px - r0, py), (px + r0, py), 2)
            pygame.draw.line(sp, (*CREAM, 210), (px, py - r0), (px, py + r0), 2)
            pygame.draw.circle(sp, (*mix(CREAM, LAMP, 0.4), 150),
                               (round(px), round(py)), max(1, r0 // 3))
        surf.blit(sp, (0, 0))
    if pose == "stand":
        _face_side(surf, P, w, h, hb, shut, shine)
    else:
        _face(surf, P, w, h, hb, shut or pose == "curl", pose, shine)
    _collar(surf, P, w, h, hb, pose, level, rarity_colour(breed.rarity),
            head_prims)
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
    """One breed in your binder: its level, its coat, and what it has seen.

    `coat` is the one this card is drawn in - the coat it arrived in, or
    the shiny that replaced it. `seen` is a bitmask of every coat of this
    breed that has ever come out of a parcel, which is the second
    collection: a breed can be finished at level 10 and still be missing
    a colour.
    """
    __slots__ = ("level", "dupes", "pulled", "coat", "seen", "shiny")

    def __init__(self, level=1, dupes=0, pulled=1, coat=0, seen=None,
                 shiny=False):
        self.level = level
        self.dupes = dupes
        self.pulled = pulled
        self.coat = coat
        self.seen = (1 << coat) if seen is None else seen
        self.shiny = shiny

    def saw(self, variant):
        self.seen |= 1 << variant

    def coats_seen(self, breed):
        return sum(1 for i in range(len(breed.coats)) if self.seen >> i & 1)

    @property
    def maxed(self):
        return self.level >= MAX_LEVEL

    @property
    def need(self):
        return dupes_for(self.level)

    def give_one(self):
        """Hand one copy of this card to somebody else - the exact
        reverse of taking one in.

        A level is made of copies, so giving one back either comes off
        the duplicates in hand or, if there are none, drops a level and
        leaves the duplicates one short of the level you came down from.
        Returns False when there is nothing to give: a card at level one
        with no duplicates behind it is the card itself, and the swap
        board does not take those.
        """
        if self.dupes > 0:
            self.dupes -= 1
            self.pulled -= 1
            return True
        if self.level <= 1:
            return False
        self.level -= 1
        self.dupes = max(0, dupes_for(self.level) - 1)
        self.pulled -= 1
        return True

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
                 "floor", "blurb", "reviews", "shelf", "shiny_mult",
                 "fresh_coats", "expo", "series")

    def __init__(self, key, name, price, cards, weights, ship, floor,
                 blurb, reviews, shelf="standard", shiny_mult=1.0,
                 fresh_coats=False, expo=0.0, series="cat"):
        self.key = key
        self.name = name
        self.price = price
        self.cards = cards
        self.weights = weights
        self.ship = ship            # seconds, by standard post
        self.floor = floor          # the last card is at least this rarity
        self.blurb = blurb
        self.reviews = reviews
        self.shelf = shelf          # "standard" is the ladder; the rest
        self.shiny_mult = shiny_mult    # are on the other page
        self.fresh_coats = fresh_coats
        self.expo = expo            # chance per card of one of the five
        self.series = series        # which collection it draws from


PACKS = (
    Pack("sack", "Paper Sack of Strays", 10, 2, (86, 13, 1, 0, 0, 0, 0, 0, 0, 0), 25,
         R_COMMON,
         "Two cards in a paper sack, folded over twice and stapled. "
         "Mostly the cats you could meet on the way to the shop.",
         (("vastly better than the bin it came from", 4),
          ("one was damp. still a cat.", 3))),
    Pack("box", "Shelf Box", 25, 3, (56, 33, 10, 4, 1, 0, 0, 0, 0, 0), 55,
         R_COMMON,
         "Three cards in a proper box with a window in the lid. The kind "
         "of thing a corner shop keeps by the till.",
         (("the lid window is a nice touch", 5),
          ("got a Russian Blue first go. no notes.", 5),
          ("three commons. the dice do what they like.", 3))),
    Pack("case", "Pedigree Case", 85, 5, (30, 37, 24, 11, 7, 1, 1, 0, 0, 0), 90,
         R_UNCOMMON,
         "Five cards in a hinged case with a felt tray, and a guarantee "
         "printed inside the lid: nothing in here is quite ordinary.",
         (("the felt smells like a library", 5),
          ("bought six. opened six. no regrets, slight debt.", 4))),
    Pack("crate", "Breeders Crate", 250, 9, (10, 32, 34, 18, 16, 5, 3, 1, 0, 0), 140,
         R_RARE,
         "Nine cards, wood wool, and a crowbar you are expected to own. "
         "One card in here is rare or better. It says so on the lid.",
         (("arrived with actual straw in it", 5),
          ("my Bengal came out of one of these", 5),
          ("the crowbar is not included, which they do say", 4))),
    Pack("lot", "The Estate Lot", 600, 15, (0, 17, 34, 22, 26, 12, 10, 4, 1, 0), 200,
         R_PEDIGREE,
         "Fifteen cards from a collection being broken up. No commons at "
         "all, and the last card is pedigree or legend. Sold as seen.",
         (("the whole binder in four orders. rude.", 5),
          ("Khao Manee. I had to sit down.", 5),
          ("expensive. correct, but expensive.", 4))),
    Pack("shelf", "The Whole Shelf", 1500, 34, (0, 10, 30, 21, 28, 16, 14, 6, 2, 1), 300,
         R_PEDIGREE,
         "Somebody has died and the whole shelf is being sold in one go. "
         "Thirty-four cards, nothing ordinary in it, and a long wait.",
         (("four of these and I was done", 5),
          ("took eleven minutes to arrive. worth every one.", 5),
          ("the box is enormous. the cat sleeps in it now.", 5))),

    # ---- the other page: four things that are not on the ladder -------
    Pack("bin", "The Returns Bin", 60, 8, (62, 38, 0, 0, 0, 0, 0, 0, 0, 0), 70, R_COMMON,
         "Eight cards somebody else sent back. Ordinary cats, by the "
         "handful, and nothing above uncommon has ever been found in one.",
         (("it is exactly what it says it is", 4),
          ("six domestic shorthairs. I needed six domestic shorthairs.", 5)),
         shelf="special"),
    Pack("swatch", "The Swatch Book", 450, 6, (26, 34, 22, 12, 10, 4, 3, 1, 1, 0), 120,
         R_UNCOMMON,
         "Six cards chosen for their COLOUR. The house picks coats you "
         "have not seen before, wherever it still can.",
         (("filled four gaps in one box", 5),
          ("the only way I finished the Ragdoll page", 5),
          ("pricey for what it is, unless you need what it is", 4)),
         shelf="special", fresh_coats=True),
    Pack("odd", "The Oddity Crate", 900, 4, (10, 26, 30, 17, 18, 8, 7, 3, 1, 0), 150, R_RARE,
         "Four cards the sorters set aside and could not say why. Shinies "
         "turn up in here eight times as often as they do anywhere else.",
         (("two shinies out of nine crates. I am not complaining.", 5),
          ("nine crates.", 3),
          ("my snow Bengal came out of one of these", 5)),
         shelf="special", shiny_mult=8.0),
    Pack("single", "The Single", 1800, 1, (0, 0, 0, 0, 0, 0, 9, 4, 1, 0), 180, R_LEGEND,
         "One card in a stiff sleeve, and it is a legend. Which legend is "
         "not something the shop is prepared to discuss beforehand.",
         (("expensive. certain. I have bought four.", 5),
          ("got the Lykoi I had been chasing for an hour", 5)),
         shelf="special"),
)
BY_PACK = {p.key: p for p in PACKS}
KITTEN_PACKS = (
    Pack("kstart", "The Kitten Series Starter", 500, 6,
         (54, 28, 13, 6, 4, 1, 0, 0, 0, 0), 60, R_COMMON,
         "Six cards and a fold-out sheet showing all twelve of them, with "
         "the ones nobody has photographed yet drawn in by hand.",
         (("back to square one and loving it", 5),
          ("the fold-out is better than the cards", 4)),
         shelf="kitten", series="kitten"),
    Pack("kboost", "A Kitten Series Booster", 2400, 12,
         (22, 28, 25, 14, 14, 7, 3, 1, 1, 0), 150, R_RARE,
         "Twelve cards of the new series, and the foil on the wrapper is "
         "a different foil, which everybody has an opinion about.",
         (("the foil is wrong and they know it is wrong", 2),
          ("pulled The Runt first go. worth it.", 5),
          ("same cats, smaller. somehow that is enough.", 4)),
         shelf="kitten", series="kitten"),
    Pack("klitter", "The Whole Litter", 9000, 30,
         (8, 18, 26, 17, 22, 14, 9, 4, 3, 1), 280, R_CHAMPION,
         "Thirty cards in a long box with a window down the side. The "
         "closest the company has come to admitting it knows exactly "
         "what it is doing.",
         (("six hundred quid of kittens. no notes.", 5),
          ("they have done it again and i have fallen for it again", 4)),
         shelf="kitten", series="kitten"),
)
WORKING_PACKS = (
    Pack("wstart", "The Working Cats Starter", 800, 6,
         (34, 26, 18, 9, 8, 4, 1, 0, 0, 0), 70, R_COMMON,
         "Six cards and a sheet of facts about working animals that "
         "reads as though it was written to be read aloud in a school.",
         (("the facts sheet is doing a lot of lifting", 3),
          ("got the ship's cat first go", 5)),
         shelf="working", series="working"),
    Pack("wboost", "A Working Cats Booster", 3400, 12,
         (12, 18, 22, 14, 16, 10, 6, 2, 0, 0), 170, R_RARE,
         "Twelve cards, and the wrapper has a rope border on it that "
         "nobody asked for and everybody rather likes.",
         (("the rope border is the best thing they have done", 5),
          ("four pub cats. FOUR.", 2),
          ("the station cat card made me put it down for a minute", 5)),
         shelf="working", series="working"),
    Pack("wcase", "The Whole Shift", 11000, 28,
         (6, 10, 18, 14, 20, 16, 10, 6, 0, 0), 300, R_CHAMPION,
         "Twenty-eight cards in a tin with a hinge, which is the first "
         "tin the company has ever done and will not be the last.",
         (("the tin. the TIN.", 5),
          ("i did not need this and i have bought three", 4)),
         shelf="working", series="working"),
)
OLD_PACKS = (
    Pack("ostart", "The Old Guard Starter", 2000, 5,
         (0, 0, 30, 20, 20, 18, 8, 3, 1, 0), 90, R_RARE,
         "Five cards on board so thick the sleeve will not take two of "
         "them, and a note about how long each cat has been at it.",
         (("five cards for six thousand. and yet.", 3),
          ("the card stock is absurd and i love it", 5)),
         shelf="old", series="old"),
    Pack("oboost", "An Old Guard Booster", 6000, 10,
         (0, 0, 18, 14, 18, 20, 14, 8, 6, 2), 200, R_PEDIGREE,
         "Ten of them, and a foil on the wrapper that looks like frost "
         "on a window, which is either very clever or an accident.",
         (("pulled Grandmother. sat down for a bit.", 5),
          ("the frost foil is clever and they know it", 4)),
         shelf="old", series="old"),
    Pack("ocase", "The Long Service Box", 18000, 22,
         (0, 0, 10, 10, 16, 20, 18, 12, 10, 4), 340, R_CHAMPION,
         "Twenty-two cards in a wooden box with a sliding lid. The most "
         "expensive thing on the website and they are not embarrassed "
         "about it in the slightest.",
         (("fifty-two thousand pounds of cats", 5),
          ("the sliding lid is worth half of it", 4)),
         shelf="old", series="old"),
)
for _p in WORKING_PACKS + OLD_PACKS:
    BY_PACK[_p.key] = _p
PACKS = PACKS + WORKING_PACKS + OLD_PACKS

for _p in KITTEN_PACKS:
    BY_PACK[_p.key] = _p
PACKS = PACKS + KITTEN_PACKS

SHELVES = ("standard", "special")


def series_breeds(series):
    """The collection a pack draws from."""
    return BY_SERIES[series].cats if series in BY_SERIES else BREEDS


def series_rarity(series):
    return (BY_SERIES[series].by_rarity if series in BY_SERIES
            else BY_RARITY)


SERIES_NAME = {x.key: x.name for x in SERIES}


def packs_on(shelf):
    return [p for p in PACKS if p.shelf == shelf]

# ---------------------------------------------------------------------------
# THE CONVENTION
#
# Every Saturday, across town: three trestle tables, a hall full of people
# who want the same cards you do, and a man by the door selling at five
# times the price. Nothing here can be ordered. The limited packs are won
# by standing in the right queue, knowing a fake when you see one, and
# talking a scalper down - which is the whole point of the day out, and
# the reason the website cannot sell you everything.
#
# One go at each table per convention. The hall shuts at midnight and the
# tables reset for next week.
# ---------------------------------------------------------------------------
CONV_PACKS = (
    Pack("expo", "The Convention Exclusive", 0, 20, (0, 6, 22, 17, 26, 20, 20, 9, 6, 3),
         0, R_CHAMPION,
         "Twenty cards printed for the hall and nowhere else. They do not "
         "post these and they never will.",
         (("queued an hour. would queue again.", 5),
          ("two foundation cards out of one pack", 5)),
         shelf="convention", expo=0.075),
    Pack("judge", "The Judge's Table", 0, 10, (0, 0, 10, 12, 24, 30, 26, 13, 10, 4),
         0, R_LEGEND,
         "Ten cards the judges put aside at the end of the show, every one "
         "of them a cat that won something.",
         (("the only place a foundation card is a sure thing", 5),
          ("they check you know what you are looking at first", 4)),
         shelf="convention", expo=0.055),
    Pack("lotA", "The Auction Lot", 0, 18, (0, 4, 18, 14, 22, 18, 14, 6,
                                             3, 1), 0, R_CHAMPION,
         "Eighteen cards knocked down to you in front of a room full of "
         "people who wanted them. The auctioneer does not care either "
         "way; everybody else does.",
         (("worth it for the look on his face", 5),
          ("paid over the odds in front of witnesses", 3)),
         shelf="convention", expo=0.06),
    Pack("quiz", "The Quizmaster's Shelf", 0, 12, (0, 0, 14, 16, 24, 22,
                                                   14, 6, 3, 1), 0, R_LEGEND,
         "Twelve cards off the shelf behind the quiz table, handed over "
         "by somebody who plainly expected to keep them.",
         (("he did not think anybody would get three", 5),
          ("i have never been so pleased about a cat", 5)),
         shelf="convention", expo=0.05),
    Pack("scalp", "The Scalped Pack", 4200, 15, (0, 10, 26, 18, 24, 18, 18, 8, 4, 2),
         0, R_PEDIGREE,
         "Fifteen cards from a man by the fire door who will not say where "
         "he got them. Face value is four thousand two hundred.",
         (("he wanted twenty-one for this", 2),
          ("talked him down. felt like a win. was it a win?", 4)),
         shelf="convention", shiny_mult=2.0, expo=0.035),
)
for _p in CONV_PACKS:
    BY_PACK[_p.key] = _p
PACKS = PACKS + CONV_PACKS

SCALP_MULT = 5.0           # what he asks before you talk him down

# key, name, who runs it, what it gives you, the game it takes
STALLS = (
    ("queue", "THE EXCLUSIVES QUEUE", "a volunteer with a clipboard",
     "expo", "queue",
     "Four hundred people want twenty packs. Get to the table before "
     "the rope goes across."),
    ("fake", "THE AUTHENTICATION DESK", "a judge with a loupe",
     "judge", "fake",
     "Three of these four cards came off a printer in somebody's garage. "
     "Point at the one that did not."),
    ("scalp", "THE MAN BY THE FIRE DOOR", "a scalper",
     "scalp", "haggle",
     "He has what you want and he knows it. Whatever you talk him down "
     "to is what you pay - and he walks if you waste his afternoon."),
    ("auction", "THE AUCTION", "an auctioneer who has done this before",
     "lotA", "auction",
     "Eighteen cards on the block and a room full of people who want "
     "them. Raise until the rest stop, and not one bid further."),
    ("quiz", "THE QUIZ TABLE", "a man who wrote the book",
     "quiz", "quiz",
     "Three questions about the catalogue. He has the shelf behind him "
     "and no intention of parting with any of it."),
)

# Three tables fit in the hall and there are five of them, so each
# convention is a different three. Seeded off the week, so it is the same
# three all day and a different three next Saturday.
STALLS_OUT = 3


def stalls_on(week):
    rng = random.Random(week * 2749 + 11)
    return tuple(sorted(rng.sample(range(len(STALLS)), STALLS_OUT)))

# Shipping. The cheap one is slow and the fast one is a luxury, which is
# the only decision the shop ever asks you to make.
POST = 0                    # the index of standard post in SHIPPING
SHIPPING = (
    ("post", "Standard post", 0.00, 1.00, "it gets there when it gets there"),
    ("track", "Tracked courier", 0.12, 0.60, "a van, and a number to watch"),
    ("cab", "Same-hour cab", 0.45, 0.33, "someone drives it over now"),
)
# ---------------------------------------------------------------------------
# THINGS FOR THE FLAT
#
# The other half of the website: eight things that are not cards. Each
# one is bought once, costs more than the last, turns up in a room where
# you can see it, and makes every cat in the flat earn a little more -
# which is the honest version of what they are for. A warm, fed, amused
# cat earns its keep; that is the whole economy of this game stated as a
# piece of furniture.
#
#   where   the room it appears in, so buying one changes the view
#   gain    added to the income multiplier, which starts at 1.0
# ---------------------------------------------------------------------------
class Upgrade:
    __slots__ = ("key", "name", "price", "gain", "where", "blurb")

    def __init__(self, key, name, price, gain, where, blurb):
        self.key = key
        self.name = name
        self.price = price
        self.gain = gain
        self.where = where
        self.blurb = blurb


UPGRADES = (
    Upgrade("bowlmat", "A Proper Feeding Mat", 120, 0.04, "cats",
            "Wipe-clean, slightly too large, and the bowls stop sliding "
            "across the floor at six in the morning."),
    Upgrade("fountain", "The Water Fountain", 420, 0.06, "cats",
            "Running water, which they will drink from in preference to "
            "the bowl you filled thirty seconds ago."),
    Upgrade("rug", "A Thicker Rug", 1100, 0.07, "study",
            "Wool, and deep enough to knead. The desk chair no longer "
            "squeaks on the boards either."),
    Upgrade("radcover", "A Radiator Shelf", 2600, 0.09, "hall",
            "A plank and two brackets over the hall radiator, which is "
            "all a cat has ever wanted from carpentry."),
    Upgrade("perch", "The Window Catio", 5200, 0.08, "cats",
            "A box of a balcony on the cat room window. They sit in it "
            "and watch the street like a pair of magistrates."),
    Upgrade("heatbed", "A Heated Bed", 11000, 0.09, "cats",
            "Thermostatic, washable, and warmer than you are, which "
            "settles a long-running argument about laps."),
    Upgrade("gramo", "The Gramophone", 26000, 0.10, "study",
            "Plays something slow in the corner. The whole flat sleeps "
            "better, including you."),
    Upgrade("skylight", "A Skylight", 60000, 0.12, "cats",
            "Somebody comes and cuts a hole in the roof. The sun moves "
            "across the floor all day and they follow it round."),
)
BY_UPGRADE = {u.key: u for u in UPGRADES}


# ---------------------------------------------------------------------------
# THE RESALE SITE
#
# The other website. MEOWRDER sells sealed packs cheaply and slowly; this
# one sells whatever somebody already opened, immediately, at whatever
# they think they can get. Most of the people on it bought twenty of
# something at retail on the day it came out and have been sitting on
# them since, and they price accordingly.
#
# It exists because by the back half of a collection the thing you are
# short of is not money, it is the four breeds you have never seen and
# the post only carrying so many parcels an hour. This is the valve: you
# can have exactly the card you want, right now, for an amount of money
# that should make you think about it.
#
# Two rules keep it from eating the game it is bolted onto:
#
#   - A SEALED BOX GOES IN THE POST, like anything else in a box. It
#     takes a slot on the round and it takes its time. Otherwise the
#     throughput the whole economy is built on stops meaning anything -
#     an instant thirty-four card lot at six times the price is still
#     five times faster than the post, and the post is the game.
#   - A SINGLE CARD IS HANDED OVER. One card cannot break throughput
#     whatever it costs, and "they will not post a four-figure card" is
#     true of every real version of this.
#
# The stock turns over once a day and is saved with everything else, so
# you cannot reload until the listing you wanted is a reasonable price.
# ---------------------------------------------------------------------------

# name, what they add on, and what they are like about it
SELLERS = (
    ("a collector clearing a shelf", 1.35, 3,
     "Downsizing. Priced to go and honest about the corners."),
    ("the shop on the high street", 2.1, 4,
     "A real shop with a real counter. They still want a margin."),
    ("CARDB0ARD_K1NGD0M", 5.5, 9,
     "Bought a case on release day. Has not opened one since."),
    ("mint_only_1998", 7.0, 9,
     "Everything is mint. Everything is sleeved. Everything is dear."),
    ("@flipthiscat", 9.0, 8,
     "Buys at the convention door and lists it before he gets home."),
    ("THE VAULT (do not lowball)", 12.0, 6,
     "Will not take offers. Will relist it next week for more."),
)
SELLER_HONEST = 2          # the first two are not scalpers, and are scarce

LOTS_ON_SITE = 6           # how many listings there are at any one time

# A private seller with a roll of tape is slower than a warehouse, and
# never faster. This matters more than it looks: the three packs the
# convention gives out are posted in NO time at all, because they are
# handed to you at a table - and a listing for one of those went straight
# into the parcels pile without ever being in the post. The best boxes in
# the game, instantly, for money. Everything bought second hand waits.
RESALE_SLOW = 1.5
RESALE_MIN_SHIP = 220.0


def card_worth(breed, level, shiny):
    """What a card is worth before anybody marks it up.

    Rarity is a ladder and so is level, but level is the steeper of the
    two: a Legend at ten is most of a binder's worth of duplicates and is
    priced like it. This is not the income it earns - a card that paid
    for itself would make the whole site a money printer rather than a
    money hole.
    """
    base = 420.0 * (1.85 ** breed.rarity)
    base *= 1.0 + 0.42 * (level - 1) ** 1.3
    if shiny:
        base *= 5.0
    return base


def resale_ship(pack, qty=1):
    """How long a box off the site takes to turn up."""
    return max(RESALE_MIN_SHIP, ship_time(pack, POST, qty) * RESALE_SLOW)


def pack_worth(pack):
    """What a sealed pack is worth to the person reselling it.

    The two the convention gives away have no price at all, which does
    not stop anybody listing one - so a pack with no price is valued on
    what is in it instead.
    """
    if pack.price:
        return float(pack.price)
    tot = sum(pack.weights) or 1
    ev = sum(pack.weights[r] / tot * RARITY[r][2]
             for r in range(SOLD_RARITIES))
    return 2600.0 * ev * pack.cards


# What turns up on the site is not what is easiest to get hold of: a
# listing for a Shelf Box is a listing nobody reads. The boxes worth
# reselling are the ones the website will not sell you.
PACK_PULL = {"standard": 1, "special": 3, "convention": 6, "resale": 6}
# ... except for the loft, which is not stock at all
NEVER_STOCKED = ("attic",)
ATTIC_ODDS = 0.11          # of a day having one on it


class Lot:
    """One listing. `kind` is "card" or "pack"."""
    __slots__ = ("kind", "key", "level", "coat", "shiny", "qty", "seller",
                 "price", "sold")

    def __init__(self, kind, key, seller, price, level=1, coat=0,
                 shiny=False, qty=1, sold=False):
        self.kind = kind
        self.key = key
        self.seller = seller
        self.price = price
        self.level = level
        self.coat = coat
        self.shiny = shiny
        self.qty = qty
        self.sold = sold

    def to_row(self):
        return [self.kind, self.key, self.seller, round(self.price, 2),
                self.level, self.coat, int(self.shiny), self.qty,
                int(self.sold)]

    @staticmethod
    def from_row(r):
        try:
            lot = Lot(r[0], r[1], int(r[2]), float(r[3]), int(r[4]),
                      int(r[5]), bool(r[6]), int(r[7]), bool(r[8]))
        except (TypeError, ValueError, IndexError):
            return None
        if lot.kind == "card" and lot.key not in BY_KEY:
            return None
        if lot.kind == "pack" and lot.key not in BY_PACK:
            return None
        return lot

    @property
    def markup(self):
        return SELLERS[self.seller][1]

    def words(self):
        if self.kind == "pack":
            pack = BY_PACK[self.key]
            return f"{pack.name}" + (f" x{self.qty}" if self.qty > 1 else "")
        b = BY_KEY[self.key]
        return f"{b.name}, level {self.level}"


# The packs that only ever turn up second hand: nobody sells these new
# because nobody ever sold them new.
RESALE_PACKS = (
    Pack("shoebox", "A Shoebox From a House Clearance", 900, 26,
         (54, 28, 12, 6, 4, 1, 1, 0, 0, 0), 240, R_COMMON,
         "Somebody's aunt kept these in a shoebox under a bed for twenty "
         "years. Mostly moggies, one or two corners gone soft, and every "
         "so often something nobody in that house knew they had.",
         (("forty per cent of it is the same cat", 2),
          ("found a Foundation card in the bottom. worth the lot.", 5)),
         shelf="resale"),
    Pack("hoard", "Somebody's Whole Collection", 9000, 72,
         (22, 26, 24, 14, 14, 8, 5, 2, 1, 0), 420, R_LEGEND,
         "All of it, in one go, because they are moving and it will not "
         "fit in the van. Seventy-two cards and no sorting.",
         (("two hours to put away. no regrets.", 5),
          ("he cried when he handed it over. so did i, later.", 4)),
         shelf="resale"),
    Pack("attic", "Everything I Had As A Kid", 6400, 160,
         (72, 19, 6, 3, 2, 1, 0, 0, 0, 0), 430, R_COMMON,
         "Four carrier bags out of a loft, emptied into one box. A "
         "hundred and sixty cards, most of them cats you could meet on "
         "the way to the shop, and a great many of them twice - but it "
         "comes as one parcel, and that is the part that matters.",
         (("nine hours sorting it. found four i had never seen.", 5),
          ("eleven ginger moggies. ELEVEN.", 2),
          ("he said his mum wanted the loft back", 5)),
         shelf="resale"),
    Pack("graded", "One Card, Graded, Sealed", 5600, 1,
         (0, 0, 0, 0, 0, 26, 48, 27, 26, 12), 180, R_CHAMPION,
         "One card in a hard case with a number on it. You are paying for "
         "the number and the certainty, and you know it.",
         (("the certainty is the product", 4),
          ("paid five thousand for a cat i already had", 1)),
         shelf="resale"),
)
for _p in RESALE_PACKS:
    BY_PACK[_p.key] = _p
PACKS = PACKS + RESALE_PACKS


def _pick_seller(rng):
    """Most of them are scalpers, because most of them are."""
    weights = [sl[2] for sl in SELLERS]
    total = sum(weights)
    pick = rng.uniform(0, total)
    acc = 0
    for i, w in enumerate(weights):
        acc += w
        if pick <= acc:
            return i
    return len(SELLERS) - 1


def roll_lots(state, rng):
    """A day's stock. Four cards and two boxes, give or take.

    The cards lean toward breeds you have not got, because a listing for
    something already in your binder at a level below the one you have is
    a listing nobody would read twice.
    """
    # Nothing off the books is ever for sale. The five that are not in
    # the binder until one turns up are not in anybody's shop either -
    # the whole point of them is that you cannot go and get one, and a
    # scalper listing one is the one way round that. Both pools are cut
    # from the same list so neither of them can drift: the first draft
    # kept unlisted out of the breeds you are MISSING and let them
    # straight back in through the ones you already own.
    sellable = [b for b in BREEDS if b.rarity != R_UNLISTED]
    missing = [b for b in sellable if b.key not in state.cards]
    owned = [b for b in sellable if b.key in state.cards]
    attic = rng.random() < ATTIC_ODDS
    lots = []
    for i in range(LOTS_ON_SITE + today(state.played).lots):
        seller = _pick_seller(rng)
        mark = SELLERS[seller][1]
        if i == LOTS_ON_SITE - 1 and attic:
            # whoever is selling this is clearing a loft, not flipping:
            # it comes off one of the two who are not taking the mick
            seller = rng.randrange(SELLER_HONEST)
            price = round(pack_worth(BY_PACK["attic"]) * SELLERS[seller][1]
                          * rng.uniform(0.9, 1.15))
            lots.append(Lot("pack", "attic", seller, price, qty=1))
            continue
        if i >= LOTS_ON_SITE - 2:                   # the boxes
            pool = []
            for pk in PACKS:
                if pk.key in NEVER_STOCKED:
                    continue
                pool += [pk] * PACK_PULL.get(pk.shelf, 1)
            pack = rng.choice(pool)
            qty = rng.choice((1, 1, 1, 2))
            price = round(pack_worth(pack) * qty * mark
                          * rng.uniform(0.9, 1.15))
            lots.append(Lot("pack", pack.key, seller, price, qty=qty))
            continue
        pool = missing if (missing and rng.random() < 0.62) else owned
        if not pool:
            pool = sellable
        b = rng.choice(pool)
        # a seller listing a level ten is a seller who finished one
        level = min(MAX_LEVEL, 1 + int(rng.random() ** 2.4 * MAX_LEVEL))
        shiny = rng.random() < 0.08
        coat = rng.randrange(len(coat_colours(b)))
        price = round(card_worth(b, level, shiny) * mark
                      * rng.uniform(0.86, 1.19))
        lots.append(Lot("card", b.key, seller, price, level, coat, shiny))
    rng.shuffle(lots)
    return lots


# ---------------------------------------------------------------------------
# THINGS FOR THE CARDS
#
# The flat page sells furniture, which is for the cats. This is for the
# cards: sleeves, a binder, a loupe, a price guide. None of it is a
# decision you agonise over - every one is a few per cent - and that is
# deliberate. The point of a shelf like this is that it is always worth
# buying the next one and never worth saving up for it.
#
# Three of them pay a little more per second, which is the same lever the
# flat pulls. The other three pull levers nothing else touches: what the
# shiny odds are, what the resale site costs you, and whether you are
# allowed to be wrong once at the authentication desk. A page of six
# income bonuses would not be a page, it would be a number with six
# names.
# ---------------------------------------------------------------------------
class Merch:
    __slots__ = ("key", "name", "price", "blurb", "income", "shiny",
                 "resale", "loupe")

    def __init__(self, key, name, price, blurb, income=0.0, shiny=1.0,
                 resale=1.0, loupe=False):
        self.key = key
        self.name = name
        self.price = price
        self.blurb = blurb
        self.income = income
        self.shiny = shiny
        self.resale = resale
        self.loupe = loupe

    @property
    def effect(self):
        if self.income:
            return f"+{self.income * 100:.0f}% a second"
        if self.shiny != 1.0:
            return f"shinies x{self.shiny:.2f}"
        if self.resale != 1.0:
            return f"{(1 - self.resale) * 100:.0f}% off resale"
        return "one wrong answer"


MERCH = (
    Merch("sleeves", "A Hundred Card Sleeves", 700,
          "Acid free, and the exact size of the cards. They stop looking "
          "like they have been in somebody's pocket, because they have.",
          income=0.03),
    Merch("binder", "A Four-Ring Binder", 2800,
          "Nine pockets to a page and a strap that shuts. The shoebox has "
          "done its bit and can go back under the bed.",
          income=0.05),
    Merch("tops", "Rigid Toploaders", 7500,
          "For the ones you would be upset about. Somehow the good ones "
          "turn up more often once there is somewhere to put them.",
          shiny=1.20),
    Merch("loupe", "A Jeweller's Loupe", 16000,
          "Ten times, with a light in it. At the authentication desk it "
          "buys you exactly one wrong answer, which is one more than you "
          "get now.",
          loupe=True),
    Merch("guide", "The Price Guide, This Year's", 26000,
          "Everything in it, with a number beside it. You stop being the "
          "one in the conversation who does not know what things go for.",
          resale=0.90),
    Merch("case", "A Glass-Fronted Display Case", 44000,
          "Lit from inside, on the wall where the television was. They "
          "sit in front of it in the evenings, which cannot be a "
          "coincidence.",
          income=0.08),
)
BY_MERCH = {m.key: m for m in MERCH}


# ---------------------------------------------------------------------------
# THE SWAP BOARD
#
# The third website, and the only one that does not take money.
#
# People post what they have and what they want. You give copies of
# something you have too many of and you get something you have none of,
# which is what everybody who has ever collected anything has done. A
# level is made of copies, so paying in copies comes off your levels -
# that is the price, and it is a real one: you go backwards on a cat you
# have been feeding for an hour to go forwards on one you have never
# seen.
#
# Nothing here is for sale and nothing here can be rushed. The board
# turns over with the day, like the resale site, and is seeded the same
# way so a reload is not a reroll.
# ---------------------------------------------------------------------------
SWAPPERS = (
    ("a steady trader", 1.0,
     "Posts what they have, says what they want, and does not haggle."),
    ("completist_1994", 1.15,
     "Four cards off a full set for nine years running."),
    ("THE SWAP KING", 1.5,
     "Calls every deal generous. None of them are generous."),
    ("a nervous first-timer", 0.85,
     "Has read the rules twice and would rather not get this wrong."),
)
SWAPS_ON_BOARD = 5


def swap_price(want, give):
    """How many copies of `want` a trader asks for one `give`.

    Priced off the gap between the two tiers, because that is the whole
    negotiation: nobody gives up a Foundation card for one common, and
    nobody wants nine commons for a common.
    """
    gap = give.rarity - want.rarity
    return int(clamp(round(2 + gap * 1.6), 1, 12))


class Swap:
    """One post on the board: copies of theirs for copies of yours."""
    __slots__ = ("give", "want", "cost", "who", "done")

    def __init__(self, give, want, cost, who, done=False):
        self.give = give        # breed key they are offering
        self.want = want        # breed key they want copies of
        self.cost = cost        # how many copies
        self.who = who
        self.done = done

    def to_row(self):
        return [self.give, self.want, self.cost, self.who, int(self.done)]

    @staticmethod
    def from_row(r):
        try:
            sw = Swap(r[0], r[1], int(r[2]), int(r[3]), bool(r[4]))
        except (TypeError, ValueError, IndexError):
            return None
        if sw.give not in BY_KEY or sw.want not in BY_KEY:
            return None
        return sw


def roll_swaps(state, rng):
    """A day of posts, built against the binder as it stands.

    An offer nobody could take is not an offer, so what they ask for is
    always something you own and what they give is weighted towards
    something you do not. On an empty binder there is nothing to trade
    with and the board says so rather than inventing something.
    """
    book = state.book
    mine = [b for b in book if b.key in state.cards]
    if not mine:
        return []
    missing = [b for b in book if b.key not in state.cards]
    day = today(state.played)
    out = []
    for _ in range(SWAPS_ON_BOARD + day.swaps):
        want = rng.choice(mine)
        pool = missing if (missing and rng.random() < 0.75) else book
        give = rng.choice(pool)
        if give.key == want.key:
            continue
        who = rng.randrange(len(SWAPPERS))
        cost = max(1, round(swap_price(want, give) * SWAPPERS[who][1]
                            * day.haggle))
        out.append(Swap(give.key, want.key, cost, who))
    return out


# ---------------------------------------------------------------------------
# THE ONLINE AUCTIONS
#
# The other half of the resale site, and the only thing in the game that
# happens while you are not looking at it.
#
# The auction at the convention is a room: you raise, the room answers,
# and it is over inside a minute. This is the opposite. You put a number
# on something and then go and do something else, and other people bid
# against you in your absence. Coming back to find you have been outbid
# by four hundred pounds with ninety seconds left is the entire feeling
# being sold here.
#
# Nothing is held in escrow. The money leaves when the hammer falls, and
# if it is not there when it falls, somebody else gets it and the whole
# thing was for nothing.
# ---------------------------------------------------------------------------
BIDDERS = (
    ("sleeve_and_toploader", 0.9),
    ("Margaret (collects tabbies)", 0.7),
    ("NO LOWBALLERS", 1.25),
    ("a dealer, obviously", 1.1),
    ("quietbidder44", 0.8),
)
LOTS_LIVE = 4              # how many are running at once
BID_STEP = 0.08            # each raise is this much of the starting price


class Auction:
    """One lot, running against the clock."""
    __slots__ = ("kind", "key", "level", "coat", "shiny", "qty", "price",
                 "start", "ends", "mine", "who", "heat")

    def __init__(self, kind, key, price, ends, level=1, coat=0, shiny=False,
                 qty=1, mine=False, who=0, heat=0.5, start=None):
        self.kind = kind
        self.key = key
        self.price = price
        self.start = price if start is None else start
        self.ends = ends            # the moment of play it closes at
        self.level = level
        self.coat = coat
        self.shiny = shiny
        self.qty = qty
        self.mine = mine            # whether the high bid is yours
        self.who = who              # who holds it if it is not
        self.heat = heat            # how badly the room wants this one

    def to_row(self):
        return [self.kind, self.key, round(self.price, 2), round(self.ends, 2),
                self.level, self.coat, int(self.shiny), self.qty,
                int(self.mine), self.who, round(self.heat, 3),
                round(self.start, 2)]

    @staticmethod
    def from_row(r):
        try:
            a = Auction(r[0], r[1], float(r[2]), float(r[3]), int(r[4]),
                        int(r[5]), bool(r[6]), int(r[7]), bool(r[8]),
                        int(r[9]), float(r[10]), float(r[11]))
        except (TypeError, ValueError, IndexError):
            return None
        if a.kind == "card" and a.key not in BY_KEY:
            return None
        if a.kind == "pack" and a.key not in BY_PACK:
            return None
        return a

    @property
    def step(self):
        return max(1.0, round(self.start * BID_STEP))

    def left(self, played):
        return max(0.0, self.ends - played)

    def words(self):
        if self.kind == "pack":
            pk = BY_PACK[self.key]
            return pk.name + (f" x{self.qty}" if self.qty > 1 else "")
        return f"{BY_KEY[self.key].name}, level {self.level}"


def roll_auction(state, rng, played):
    """One lot, priced off what it is and ending in a few minutes."""
    sellable = [b for b in state.book if b.rarity != R_UNLISTED]
    if not sellable:
        return None
    if rng.random() < 0.28:
        pool = [pk for pk in PACKS if pk.price and pk.key not in NEVER_STOCKED]
        pk = rng.choice(pool)
        qty = rng.choice((1, 1, 2))
        worth = pack_worth(pk) * qty
        return Auction("pack", pk.key, round(worth * rng.uniform(0.25, 0.5)),
                       played + rng.uniform(100, 280), qty=qty,
                       heat=rng.uniform(0.3, 1.0))
    missing = [b for b in sellable if b.key not in state.cards]
    b = rng.choice(missing if (missing and rng.random() < 0.6) else sellable)
    level = min(MAX_LEVEL, 1 + int(rng.random() ** 2.2 * MAX_LEVEL))
    shiny = rng.random() < 0.07
    worth = card_worth(b, level, shiny)
    return Auction("card", b.key, round(worth * rng.uniform(0.25, 0.5)),
                   played + rng.uniform(100, 280), level=level,
                   coat=rng.randrange(len(coat_colours(b))), shiny=shiny,
                   heat=rng.uniform(0.3, 1.0))


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


def ship_cost(pack, qty, mode, unit=None):
    """Postage is a slice of the price, so it follows the price down."""
    unit = pack.price if unit is None else unit
    return round(unit * qty * SHIPPING[mode][2], 2)


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
# ---------------------------------------------------------------------------
# THE CALENDAR
#
# Six minutes at the desk is a day, seven days is a week, and the week
# ends on a Saturday with a convention across town. Time only runs while
# you are playing: the point of a calendar here is not to simulate a
# year, it is to make "next Saturday" mean something, and a Saturday that
# arrives while the game is shut would be a Saturday you missed.
# ---------------------------------------------------------------------------
DAY = 360.0                # seconds of play to a day
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday")
CONVENTION_DAY = 5         # Saturday
WEEK_START = 3             # day one of a collection is a Thursday


def day_of(played):
    return int(played // DAY)


def weekday_of(played):
    return (day_of(played) + WEEK_START) % 7


def date_words(played):
    d = day_of(played) + WEEK_START
    return f"{DAY_NAMES[d % 7]}, week {d // 7 + 1}"


def convention_open(played):
    return weekday_of(played) == CONVENTION_DAY


def until_convention(played):
    """Seconds until the hall next opens. Zero while it is open."""
    if convention_open(played):
        return 0.0
    into = played - day_of(played) * DAY
    days = (CONVENTION_DAY - weekday_of(played)) % 7 or 7
    return days * DAY - into


def until_midnight(played):
    """Seconds left of today. The resale site restocks on the hour that
    the day turns over, which is the same hour the convention ends."""
    return DAY - (played - day_of(played) * DAY)


def until_shut(played):
    """Seconds of convention left. Zero when there is none on."""
    if not convention_open(played):
        return 0.0
    return DAY - (played - day_of(played) * DAY)


# ---------------------------------------------------------------------------
# WHAT DAY IT IS
#
# The calendar existed to make "next Saturday" mean something. Six of the
# seven days did nothing with it, which made a week a thing you waited
# out rather than a thing you planned around.
#
# Every weekday does something now. None of it is large - a quarter off,
# a faster post, better odds on a shiny - and that is deliberate: the
# point is that there is a reason to order the dear thing on a Monday and
# the risky thing on a Friday, not that any single day is worth
# rearranging an evening for. Wednesday does nothing at all on purpose,
# because a week with no quiet day in it has no rhythm.
# ---------------------------------------------------------------------------
class Day:
    __slots__ = ("name", "blurb", "sale", "ship", "shiny", "lots", "swaps",
                 "haggle")

    def __init__(self, name, blurb="", sale=1.0, ship=1.0, shiny=1.0,
                 lots=0, swaps=0, haggle=1.0):
        self.name = name
        self.blurb = blurb
        self.sale = sale        # off everything on the website
        self.ship = ship        # how long the post takes
        self.shiny = shiny      # the odds on a shiny
        self.lots = lots        # extra listings on the resale site
        self.swaps = swaps      # extra posts on the swap board
        self.haggle = haggle    # what the board asks for, in copies

    @property
    def quiet(self):
        return (not self.name
                and self.sale == self.ship == self.shiny == self.haggle == 1.0
                and not self.lots and not self.swaps)


DAYS = (
    Day("STOCKTAKE", "a quarter off everything on the website, because "
                     "somebody has to count it all on Tuesday",
        sale=0.75),
    Day("SECOND POST", "two rounds today, so everything ordered gets "
                       "there in two thirds of the time",
        ship=0.66),
    Day("", "nothing on"),
    Day("NEW IN", "the resale site has had a clear-out and there is twice "
                  "as much on it",
        lots=6),
    Day("LATE NIGHT", "the printers run a night shift and the foil comes "
                      "out wrong twice as often as it should",
        shiny=2.0),
    Day("THE CONVENTION", "across town, all day, and nothing in it can be "
                          "ordered"),
    Day("THE SWAP MEET", "twice as many posts on the board, and everybody "
                         "is feeling generous about it",
        swaps=5, haggle=0.7),
)


def today(played):
    return DAYS[weekday_of(played)]


def price_of(pack, state):
    """What the website is asking for this today."""
    return round(pack.price * today(state.played).sale)


FIRST_STRAY = 330.0        # seconds of play before the first one comes
STRAY_GAP = (520.0, 820.0)  # ... and how long between the ones after it

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


def roll_coat(breed, rng, card=None, fresh=False):
    """Which coat came in the parcel.

    The listed one turns up as often as all the others put together, so
    a breed still looks like itself - unless the box is a Swatch Book,
    which goes looking for a colour of that breed you have never seen.
    """
    if len(breed.coats) < 2:
        return 0
    if fresh and card is not None:
        unseen = [i for i in range(len(breed.coats))
                  if not (card.seen >> i & 1)]
        if unseen:
            return rng.choice(unseen)
    return 0 if rng.random() < 0.5 else rng.randrange(1, len(breed.coats))


class Pull:
    """One card out of one parcel, and what it did to the binder.

    kind is "new" for a breed you did not have, "dupe" for one that moved
    its card along, "level" for one that finished a level, and "maxed" for
    a copy of something already retired - which the shop only sends by
    accident, and only at the very end.
    """
    __slots__ = ("breed", "kind", "level", "before", "sub", "coat", "shiny",
                 "new_coat")

    def __init__(self, breed, kind, level, before, sub=False, coat=0,
                 shiny=False, new_coat=False):
        self.breed = breed
        self.kind = kind
        self.level = level
        self.before = before
        self.sub = sub
        self.coat = coat
        self.shiny = shiny
        self.new_coat = new_coat


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
        self.shinies = 0
        self.played = 0.0
        self.first_run = True
        self.music = True
        self.sound = True
        self.seen_end = False
        self.club = 0               # memberships bought, 0 to 3
        self.things = set()         # furnishings bought for the flat
        self.wings = 0              # how many walls have come down
        self.spares = 0             # copies of retired breeds, for swapping
        self.out = {"cat"}          # the collections that exist
        self.told = set()           # ... and the ones announced to you
        self.seen_intro = False     # the four screens before the first pack
        self.kit = set()            # sleeves, binders, a loupe
        self.bids = []              # auctions running on the resale site
        self.won_lots = []          # what closed in your favour this tick
        self.won_bids = 0
        self.swaps = []             # what is on the swap board today
        self.swaps_day = -1
        self.swapped = 0            # how many deals you have done
        self.lots = []              # what is on the resale site today
        self.lots_day = -1          # ... and which day that was
        self.conv_done = set()      # stalls played at this convention
        self.conv_week = -1         # which convention that was
        self.conv_wins = 0
        self.stray = None           # a cat on the mat, waiting to be let in
        self.stray_t = FIRST_STRAY
        self.strays = 0             # how many have been taken in
        self.area = "study"         # the room you were last standing in
        self.away = 0.0             # what the cats earned while you were out

    # -- the numbers --------------------------------------------------------
    @property
    def comfort(self):
        """What the flat adds to every cat in it. 1.0 is bare boards."""
        return 1.0 + sum(BY_UPGRADE[k].gain for k in self.things
                         if k in BY_UPGRADE)

    @property
    def gear(self):
        """What the sleeves and the binder add, on top of the flat."""
        return 1.0 + sum(BY_MERCH[k].income for k in self.kit
                         if k in BY_MERCH)

    @property
    def shiny_gear(self):
        out = 1.0
        for k in self.kit:
            if k in BY_MERCH:
                out *= BY_MERCH[k].shiny
        return out

    @property
    def resale_gear(self):
        out = 1.0
        for k in self.kit:
            if k in BY_MERCH:
                out *= BY_MERCH[k].resale
        return out

    @property
    def has_loupe(self):
        return any(BY_MERCH[k].loupe for k in self.kit if k in BY_MERCH)

    @property
    def income(self):
        raw = sum(BY_KEY[k].rate_at(c.level) * (SHINY_BONUS if c.shiny else 1)
                  for k, c in self.cards.items())
        return raw * self.comfort * self.gear

    @property
    def owned(self):
        """Breeds from the CATALOGUE. The strays are counted on their own,
        or thirty-two listed breeds and five cats off the street would
        add up to a finished binder."""
        return sum(1 for k in self.cards if k in self.book_keys)

    @property
    def strays_owned(self):
        return sum(1 for k in self.cards if BY_KEY[k].rarity == R_UNLISTED)

    @property
    def expo_owned(self):
        return sum(1 for k in self.cards if BY_KEY[k].rarity == R_EXPO)

    @property
    def kittens_owned(self):
        return sum(1 for k in self.cards if k in KITTEN_KEYS)

    @property
    def big_room(self):
        """Kept because a good deal of this file still asks it."""
        return self.wings > 0

    @property
    def next_wing(self):
        return WINGS[self.wings] if self.wings < len(WINGS) else None

    @property
    def kittens(self):
        """Kept because a great deal of this file and its tests ask it."""
        return "kitten" in self.out

    @property
    def series(self):
        return tuple(x for x in SERIES if x.key in self.out)

    @property
    def book(self):
        """The binder, as it stands: every collection that exists, in one
        order, which is what the cover counts."""
        key = frozenset(self.out)
        got = _BOOKS.get(key)
        if got is None:
            cats = []
            for x in SERIES:
                if x.key in key:
                    cats += list(x.cats)
            got = tuple(sorted(cats, key=lambda b: (b.rarity, b.name)))
            _BOOKS[key] = got
        return got

    @property
    def book_keys(self):
        key = frozenset(self.out)
        got = _BOOK_KEYS.get(key)
        if got is None:
            got = frozenset().union(*(x.keys for x in SERIES
                                      if x.key in key))
            _BOOK_KEYS[key] = got
        return got

    def series_full(self, key):
        """Every cat in that collection, owned.

        The bar for the NEXT series, so it is measured against that
        collection and never against the binder - measuring against the
        binder would move the finish line the moment you crossed it, and
        each announcement would fire once and then look wrong for ever.
        """
        return all(b.key in self.cards for b in BY_SERIES[key].cats)

    @property
    def catalogue_full(self):
        return self.series_full("cat")

    def due(self):
        """The next collection the company owes you, if any."""
        for x in SERIES:
            if x.key not in self.out and x.after in self.out \
                    and self.series_full(x.after):
                return x
        return None

    @property
    def slots(self):
        """How many parcels may be in the post at once."""
        return MAX_IN_TRANSIT + self.club

    @property
    def retired(self):
        return sum(1 for k, c in self.cards.items()
                   if c.maxed and k in self.book_keys)

    @property
    def complete(self):
        return self.retired >= len(self.book)

    def can_hold(self, key):
        """A breed the shop may still send: one you have not finished."""
        c = self.cards.get(key)
        return c is None or not c.maxed

    def live_rarities(self, series="cat"):
        return {b.rarity for b in series_breeds(series)
                if self.can_hold(b.key)}

    def sellable(self, pack):
        """Whether the website will still take an order for this.

        A pack is withdrawn when nothing it advertises is left to send -
        once the last legend and the last pedigree have retired, there is
        no Estate Lot to sell, and the catalogue says so. It is the whole
        shape of the last hour: the shop empties from the top down, and
        the final cards come out of a paper sack, which is where the
        first ones came from.
        """
        live = self.live_rarities(pack.series)
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
        self.won_lots = self.run_auctions(dt)
        nxt = self.due()
        if nxt is not None:
            self.out.add(nxt.key)
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
        unit = price_of(pack, self)
        cost = unit * qty + ship_cost(pack, qty, mode, unit)
        if (cost > self.money + 1e-6 or len(self.orders) >= self.slots
                or not self.sellable(pack)):
            return None
        self.money -= cost
        self.spent += cost
        o = Order(self.next_num, pack.key, qty,
                  ship_time(pack, mode, qty) * today(self.played).ship,
                  cost, mode)
        self.next_num += 1
        self.orders.append(o)
        return o

    # -- the resale site ----------------------------------------------
    def refresh_lots(self, rng=None):
        """New stock when the day turns, and not before.

        Seeded off the day and nothing else, so reloading the save you
        made thirty seconds ago gets you the same six listings at the
        same six prices. A market you can reroll is not a market, it is
        a slot machine with no handle.
        """
        day = day_of(self.played)
        if self.lots_day == day and self.lots:
            return False
        self.lots_day = day
        self.lots = roll_lots(self, rng or random.Random(day * 7919 + 13))
        return True

    # -- the auctions ---------------------------------------------------
    def run_auctions(self, dt, rng=None):
        """Keep the board full, let the room bid, and drop the hammer.

        Returns whatever was won, so the game can say so. This is the one
        thing in here that happens whether or not anybody is looking at
        the page it happens on.
        """
        rng = rng or random
        won = []
        while len(self.bids) < LOTS_LIVE:
            a = roll_auction(self, rng, self.played)
            if a is None:
                break
            self.bids.append(a)
        for a in list(self.bids):
            if self.played >= a.ends:
                self.bids.remove(a)
                if a.mine:
                    got = self.take_auction(a, rng)
                    if got is not None:
                        won.append((a, got))
                continue
            # somebody else goes again, less often the dearer it gets
            over = a.price / max(1.0, a.start)
            chance = a.heat * 0.055 * dt / max(1.0, over ** 1.7)
            if rng.random() < chance:
                a.price += a.step
                a.mine = False
                a.who = rng.randrange(len(BIDDERS))
        return won

    def bid_on(self, a):
        """Put your hand up. The money does not move until it closes."""
        if a.mine or a.ends <= self.played:
            return False
        nxt = a.price + a.step if a.price > a.start else a.price
        if self.money + 1e-6 < nxt:
            return False
        a.price = nxt
        a.mine = True
        return True

    def take_auction(self, a, rng=None):
        """The hammer falls and the money leaves - if it is there."""
        if self.money + 1e-6 < a.price:
            return None
        if a.kind == "pack" and len(self.orders) >= self.slots:
            return None
        self.money -= a.price
        self.spent += a.price
        self.won_bids += 1
        if a.kind == "pack":
            pack = BY_PACK[a.key]
            o = Order(self.next_num, pack.key, a.qty,
                      resale_ship(pack, a.qty), a.price, POST)
            self.next_num += 1
            self.orders.append(o)
            return o
        b = BY_KEY[a.key]
        card = self.cards.get(a.key)
        if card is None:
            card = Card(level=a.level, coat=a.coat, shiny=a.shiny)
            card.saw(a.coat)
            self.cards[a.key] = card
            self.cards_pulled += 1
            if a.shiny:
                self.shinies += 1
            return Pull(b, "new", card.level, 0, False, a.coat, a.shiny, True)
        before = card.level
        card.saw(a.coat)
        first_shiny = a.shiny and not card.shiny
        if first_shiny:
            card.shiny = True
            card.coat = a.coat
            self.shinies += 1
        if a.level > card.level:
            card.level = a.level
            card.dupes = 0
        else:
            card.add_dupe()
        self.cards_pulled += 1
        return Pull(b, "level" if card.level > before else "dupe",
                    card.level, before, False, a.coat, first_shiny, False)

    # -- the swap board ------------------------------------------------
    def refresh_swaps(self, rng=None):
        day = day_of(self.played)
        if self.swaps_day == day and self.swaps:
            return False
        self.swaps_day = day
        self.swaps = roll_swaps(self, rng or random.Random(day * 6151 + 29))
        return True

    def copies_of(self, key):
        """How many copies of a card you could hand over without giving
        away the card itself."""
        c = self.cards.get(key)
        if c is None:
            return 0
        n = c.dupes
        for lv in range(1, c.level):
            n += dupes_for(lv)
        return n

    def can_swap(self, sw):
        return (not sw.done and sw.want in self.cards
                and self.copies_of(sw.want) >= sw.cost)

    def take_swap(self, sw):
        """Hand over the copies, take the card.

        What comes back is a Pull, the same as a card out of a packet,
        because as far as the binder is concerned that is what it is.
        """
        if not self.can_swap(sw):
            return None
        card = self.cards[sw.want]
        for _ in range(sw.cost):
            if not card.give_one():
                return None
        sw.done = True
        self.swapped += 1
        b = BY_KEY[sw.give]
        got = self.cards.get(sw.give)
        if got is None:
            coat = roll_coat(b, random.Random(sw.give), None, False)
            got = Card(coat=coat)
            got.saw(coat)
            self.cards[sw.give] = got
            return Pull(b, "new", 1, 0, False, coat, False, True)
        before = got.level
        lv = got.add_dupe()
        return Pull(b, "level" if lv else "dupe", got.level, before,
                    False, got.coat, False, False)

    def lot_cost(self, lot):
        """What it comes to. A box still has to be posted."""
        if lot.kind == "pack":
            return round(lot.price * self.resale_gear
                         + ship_cost(BY_PACK[lot.key], lot.qty, POST))
        return round(lot.price * self.resale_gear)

    def can_take(self, lot):
        if lot.sold or self.money + 1e-6 < self.lot_cost(lot):
            return False
        if lot.kind == "pack":
            return len(self.orders) < self.slots
        return True

    def take_lot(self, lot, rng=None):
        """Buy a listing.

        A box joins the round like any other order. A single card is
        handed over there and then - and if it is better than the one in
        your binder, the binder takes the better of the two, which is
        the entire reason anybody pays these prices.
        """
        if not self.can_take(lot):
            return None
        cost = self.lot_cost(lot)
        self.money -= cost
        self.spent += cost
        lot.sold = True
        if lot.kind == "pack":
            pack = BY_PACK[lot.key]
            o = Order(self.next_num, pack.key, lot.qty,
                      resale_ship(pack, lot.qty), cost, POST)
            self.next_num += 1
            self.orders.append(o)
            return o
        b = BY_KEY[lot.key]
        card = self.cards.get(lot.key)
        if card is None:
            card = Card(level=lot.level, coat=lot.coat, shiny=lot.shiny)
            card.saw(lot.coat)
            self.cards[lot.key] = card
            self.cards_pulled += 1
            if lot.shiny:
                self.shinies += 1
            return Pull(b, "new", card.level, 0, False, lot.coat, lot.shiny,
                        True)
        before = card.level
        fresh = not (card.seen >> lot.coat & 1)
        card.saw(lot.coat)
        first_shiny = lot.shiny and not card.shiny
        if first_shiny:
            card.shiny = True
            card.coat = lot.coat
            self.shinies += 1
        if lot.level > card.level:
            card.level = lot.level
            card.dupes = 0
        else:
            card.add_dupe()
        self.cards_pulled += 1
        return Pull(b, "level" if card.level > before else "dupe",
                    card.level, before, False, lot.coat, first_shiny, fresh)

    # -- the convention -----------------------------------------------
    @property
    def week(self):
        return day_of(self.played) // 7

    def convention(self):
        """True while the hall is open. It shuts when the day does."""
        return convention_open(self.played)

    def conv_refresh(self):
        """Each Saturday is its own convention, with its own three goes."""
        if self.conv_week != self.week:
            self.conv_week = self.week
            self.conv_done = set()

    def conv_played(self, key):
        return key in self.conv_done

    def conv_take(self, key, pack, qty=1):
        """A stall has been played. Whatever was won lands straight away -
        nothing at a convention goes in the post."""
        self.conv_done.add(key)
        if pack is not None:
            self.parcels.append((pack.key, qty))
            self.conv_wins += 1

    def stray_tick(self, dt, rng):
        """Is there a cat at the door? Returns its key the moment there is.

        One at a time, and it does not leave: a cat you have not noticed
        yet is still a cat on the mat when you next walk through the hall.
        """
        if self.stray:
            return None
        self.stray_t -= dt
        if self.stray_t > 0:
            return None
        new = [b.key for b in SECRETS if b.key not in self.cards]
        pool = new or [b.key for b in SECRETS if b.key in self.cards]
        if not pool:
            self.stray_t = STRAY_GAP[1]
            return None
        self.stray = rng.choice(pool)
        return self.stray

    def take_in(self, rng):
        """Let it in. Returns (breed, kind, level) or None."""
        key = self.stray
        if key is None or key not in BY_KEY:
            return None
        b = BY_KEY[key]
        card = self.cards.get(key)
        if card is None:
            self.cards[key] = Card()
            out = (b, "new", 1)
        else:
            lv = card.add_dupe()
            out = (b, "level" if lv else "dupe", card.level)
        self.stray = None
        self.stray_t = rng.uniform(*STRAY_GAP)
        self.strays += 1
        return out

    def buy_thing(self, up):
        """Buy a furnishing. They are one-offs, and they never come out."""
        if up.key in self.things or up.price > self.money + 1e-6:
            return False
        self.money -= up.price
        self.spent += up.price
        self.things.add(up.key)
        return True

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
        live = self.live_rarities(pack.series)
        by_rarity = series_rarity(pack.series)
        if not live:
            return None, False
        weights = list(pack.weights)
        if last:
            for r in range(pack.floor):
                weights[r] = 0
        pool = [(r, weights[r]) for r in range(SOLD_RARITIES)
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
        choices = [b for b in by_rarity[rarity] if self.can_hold(b.key)]
        return rng.choice(choices), sub

    def open_pack(self, pack, qty, rng):
        """Returns one Pull per card in the parcel."""
        out = []
        for n in range(qty):
            for i in range(pack.cards):
                if pack.expo and rng.random() < pack.expo:
                    b, sub = rng.choice(EXPO_BREEDS), False
                else:
                    b, sub = self.roll(pack, rng, last=(i == pack.cards - 1))
                if b is None:
                    break
                card = self.cards.get(b.key)
                coat = roll_coat(b, rng, card, pack.fresh_coats)
                shiny = (rng.random()
                         < pack.shiny_mult * self.shiny_gear
                         * today(self.played).shiny / SHINY_IN)
                if card is None:
                    card = Card(coat=coat, shiny=shiny)
                    self.cards[b.key] = card
                    out.append(Pull(b, "new", 1, 0, sub, coat, shiny, True))
                else:
                    fresh = not (card.seen >> coat & 1)
                    card.saw(coat)
                    first_shiny = shiny and not card.shiny
                    if first_shiny:
                        card.shiny = True     # it keeps the better coat
                        card.coat = coat
                    before = card.level
                    spare = card.maxed      # another copy of a finished one
                    lv = card.add_dupe()
                    if spare:
                        self.spares += 1
                    out.append(Pull(b, "maxed" if spare else
                                    "level" if lv else "dupe", card.level,
                                    before, sub, coat, first_shiny, fresh))
                self.cards_pulled += 1
                if shiny:
                    self.shinies += 1
            self.packs_opened += 1
        return out

    # -- disk ---------------------------------------------------------------
    def to_dict(self):
        return {
            "v": 1,
            "money": round(self.money, 4),
            "cards": {k: [c.level, c.dupes, c.pulled, c.coat, c.seen,
                          int(c.shiny)]
                      for k, c in self.cards.items()},
            "orders": [[o.num, o.pack, o.qty, round(o.left, 2), o.paid, o.mode]
                       for o in self.orders],
            "parcels": [[p, q] for p, q in self.parcels],
            "next_num": self.next_num,
            "earned": round(self.earned, 3),
            "spent": round(self.spent, 3),
            "packs_opened": self.packs_opened,
            "cards_pulled": self.cards_pulled,
            "shinies": self.shinies,
            "played": round(self.played, 1),
            "music": self.music,
            "sound": self.sound,
            "seen_end": self.seen_end,
            "club": self.club,
            "things": sorted(self.things),
            "wings": self.wings,
            "spares": self.spares,
            "out": sorted(self.out),
            "told": sorted(self.told),
            "seen_intro": self.seen_intro,
            "kit": sorted(self.kit),
            "bids": [a.to_row() for a in self.bids],
            "won_bids": self.won_bids,
            "swaps": [w.to_row() for w in self.swaps],
            "swaps_day": self.swaps_day,
            "swapped": self.swapped,
            "lots": [lot.to_row() for lot in self.lots],
            "lots_day": self.lots_day,
            "conv_done": sorted(self.conv_done),
            "conv_week": self.conv_week,
            "conv_wins": self.conv_wins,
            "stray": self.stray,
            "stray_t": round(self.stray_t, 1),
            "strays": self.strays,
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
                coat = int(v[3]) if len(v) > 3 else 0
                coat = int(clamp(coat, 0, len(BY_KEY[k].coats) - 1))
                seen = int(v[4]) if len(v) > 4 else (1 << coat)
                s.cards[k] = Card(int(clamp(int(v[0]), 1, MAX_LEVEL)),
                                  max(0, int(v[1])), max(1, int(v[2])),
                                  coat, seen,
                                  bool(v[5]) if len(v) > 5 else False)
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
        s.shinies = int(d.get("shinies", 0))
        s.played = float(d.get("played", 0))
        s.music = bool(d.get("music", True))
        s.sound = bool(d.get("sound", True))
        s.seen_end = bool(d.get("seen_end", False))
        s.club = int(clamp(int(d.get("club", 0)), 0, len(CLUB)))
        s.things = {k for k in (d.get("things") or []) if k in BY_UPGRADE}
        s.wings = int(clamp(int(d.get("wings", 0)), 0, len(WINGS)))
        if d.get("big_room") and not s.wings:   # saved before it was a ladder
            s.wings = 1
        s.spares = int(d.get("spares", 0))
        s.out = {k for k in (d.get("out") or ()) if k in BY_SERIES}
        s.told = {k for k in (d.get("told") or ()) if k in BY_SERIES}
        if d.get("kittens"):        # saved before there were four of them
            s.out.add("kitten")
        if d.get("seen_news"):
            s.told.add("kitten")
        s.out.add("cat")
        s.seen_intro = bool(d.get("seen_intro"))
        s.kit = {k for k in (d.get("kit") or ()) if k in BY_MERCH}
        s.bids = [x for x in (Auction.from_row(r)
                              for r in (d.get("bids") or ()))
                  if x is not None]
        s.won_bids = int(d.get("won_bids", 0))
        s.swaps = [x for x in (Swap.from_row(r)
                               for r in (d.get("swaps") or ()))
                   if x is not None]
        s.swaps_day = int(d.get("swaps_day", -1))
        s.swapped = int(d.get("swapped", 0))
        s.lots = [x for x in (Lot.from_row(r) for r in (d.get("lots") or ()))
                  if x is not None]
        s.lots_day = int(d.get("lots_day", -1))
        s.conv_done = set(d.get("conv_done") or ())
        s.conv_week = int(d.get("conv_week", -1))
        s.conv_wins = int(d.get("conv_wins", 0))
        st_key = d.get("stray")
        s.stray = st_key if st_key in BY_KEY else None
        s.stray_t = float(d.get("stray_t", FIRST_STRAY))
        s.strays = int(d.get("strays", 0))
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
    """Write the collection, unless this process has no business writing.

    cat_test.py stubs this out, with a comment about how a harness
    quietly eats a save file. Throwaway scripts - rendering a screen,
    driving a scene to look at it - do not, and one of them overwrote a
    real collection with seventy-four synthetic cards: a Game loads the
    save in its constructor, and anything that then presses a button
    which calls `save` writes whatever is in memory straight over it.

    Discipline did not work, so this does not rely on it. A headless
    process is a process with no window, which this game cannot be
    played in, so it is a process that must not save.
    """
    if os.environ.get("SDL_VIDEODRIVER") == "dummy"             or os.environ.get("CATALOGUE_READONLY"):
        return
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
    """A list of floats, normalised, clipped and handed to the mixer in
    whatever shape the mixer actually came up in.

    pre_init ASKS for one channel. SDL is allowed to refuse, and on this
    machine it does - get_init() comes back (22050, -16, 2). A mono
    buffer handed to a stereo mixer is read as interleaved pairs: half
    the samples go left, half go right, and the whole thing runs out in
    half the time at twice the pitch. Nothing errors. It just sounds
    thin and fast, which is easy to put down to it having been
    synthesised in the first place, and it was true of every sound in
    this game for as long as there have been sounds in it.

    Telling SDL not to change the format would fix it here and break on
    the next machine with no mono device, so the buffer is doubled to
    match instead - with a strided slice assignment, because doing it a
    sample at a time costs more than building the music did.
    """
    peak = max(0.001, max(abs(v) for v in samples))
    k = min(1.0, 0.92 / peak) * gain
    mono = array("h", (int(max(-32000, min(32000, v * k * 32000)))
                       for v in samples))
    got = pygame.mixer.get_init()
    chans = got[2] if got else 1
    if chans > 1:
        data = array("h", bytes(len(mono) * 2 * chans))
        for c in range(chans):
            data[c::chans] = mono
    else:
        data = mono
    return pygame.mixer.Sound(buffer=data.tobytes())


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
    if name == "shiny":                 # a chime that keeps going up
        out = []
        for f in (659.25, 987.77, 1318.5, 1760.0, 2093.0):
            out += _note(f, 0.20, "bell", 0.42, 0.01, 0.9)
        tail = _note(1318.5, 1.6, "bell", 0.5)
        for i, v in enumerate(tail):
            j = int(0.5 * RATE) + i
            if j < len(out):
                out[j] += v
            else:
                out.append(v)
        return _to_sound(out, 0.6)
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


MUSIC_GAIN = 0.30          # how hard the loop is built...
MUSIC_VOL = 0.42           # ...and how far the fader is pushed up after


# -- the music --------------------------------------------------------------
# Seventy-two to the minute, swung, with the big light off.
#
# Four jazz chords on an electric piano that has been through a tape
# machine, brushes on the drums behind them, and a record crackling under
# the lot of it. Everything is deliberately dull: the loop runs through a
# one-pole lowpass at the end so nothing on it is bright, the hats sit
# under the piano rather than on top, and the whole thing is mixed low
# enough that you can hold a conversation over it. It is wallpaper. If
# you can hum it back after an hour it is too loud.
#
# The four chords do not resolve, which is the same trick the old pad
# used - you cannot loop a resolution twenty times without hearing the
# join. The last chord's tail wraps onto the head of the buffer (see
# `_mix`), so there is no gap at the seam either.
BPM = 72.0
BEAT = 60.0 / BPM                  # 0.833s
BAR = BEAT * 4                     # 3.33s, and eight of them to the loop
STEP = BAR / 16                    # a sixteenth
SWING = 0.17                       # how late the off-beat eighth sits

# A table beats math.sin by about three to one in a loop this size, and
# at eleven bits the error it adds is quieter than the vinyl is. For this
# of all genres that is not a compromise.
_SIN_N = 2048
_SIN = tuple(math.sin(TAU * i / _SIN_N) for i in range(_SIN_N))

# name, the bass under it, and a voicing kept inside one octave in the
# middle of the register - a chord spread over three octaves reads as
# "piano", and this is meant to read as "somebody's record"
LOFI_BARS = (
    ("Am9",   110.00, (261.63, 329.63, 392.00, 493.88)),   # C  E  G  B
    ("Dm7",    73.42, (293.66, 349.23, 440.00, 523.25)),   # D  F  A  C
    ("Fmaj7",  87.31, (261.63, 329.63, 349.23, 440.00)),   # C  E  F  A
    ("Em7",    82.41, (246.94, 293.66, 329.63, 392.00)),   # B  D  E  G
)
CHORD_BARS = 2                     # how long each one is held

# Where the kit plays, on a sixteenth grid. Boom-bap: the kick leans on
# the one and lands late in the bar, the snare is on two and four and is
# brushed rather than hit, and the hats run in swung eighths.
KICKS = (0, 6, 10)
SNARES = (4, 12)
HATS = (0, 2, 4, 6, 8, 10, 12, 14)


def _rhodes(freq, dur, vol=0.3, seed=0):
    """An electric piano: a sine with a bell on the front of it that dies
    away long before the note does, a slow tremolo, and a tape machine
    underneath drifting the pitch by a part in a thousand.

    The drift is why the phase is accumulated rather than computed from
    the sample index - you cannot wobble a note you are addressing by
    multiplication.

    Nine of these are six seconds each and the loop is built while the
    player waits, so the inner loop has no math.exp in it: a decay is a
    constant you multiply by, and calling exp a hundred and thirty-five
    thousand times to find that constant again is most of the cost of the
    whole piece of music. The tape LFO is stepped every sixty-four
    samples for the same reason - it turns a third of a cycle a second
    and nothing about it needs sample resolution.
    """
    n = int(dur * RATE)
    out = [0.0] * n
    rng = random.Random(seed)
    step = freq * _SIN_N / RATE
    det = step * 1.0015             # a second voice, barely apart
    wob = TAU * rng.uniform(0.21, 0.34) / RATE
    wph = rng.uniform(0, TAU)
    tstep = 4.6 * _SIN_N / RATE     # the tremolo, in table steps
    # decays, as the per-sample constant each one comes down to
    d_bell = math.exp(-9.0 / n)
    d_body = math.exp(-2.4 / n)
    d_amp = math.exp(-2.1 / n)
    e_bell = e_body = e_amp = 1.0
    drift = 1.0
    p = q = 0.0
    sin_t = _SIN
    for i in range(n):
        if not i & 63:
            drift = 1.0 + 0.0016 * math.sin(wph + wob * i)
        p += step * drift
        q += det * drift
        ip = int(p)
        a = sin_t[ip & 2047] + 0.55 * sin_t[int(q) & 2047]
        # the bell on the attack, which is what makes it a Rhodes and not
        # an organ, and the third harmonic under it for body
        bell = 0.40 * sin_t[(ip << 2) & 2047] * e_bell
        body = 0.16 * sin_t[(ip << 1) & 2047] * e_body
        trem = 0.90 + 0.10 * sin_t[int(i * tstep) & 2047]
        e = e_amp * trem
        if i < 180:                 # a soft edge, or it clicks
            e *= i / 180
        out[i] = (a + bell + body) * e * vol
        e_bell *= d_bell
        e_body *= d_body
        e_amp *= d_amp
    return out


def _kick(vol=0.9):
    """A sine falling from a hundred and ten to forty in a tenth of a
    second, which is the whole of a kick drum."""
    n = int(0.34 * RATE)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        f = i / n
        hz = 42.0 + 72.0 * math.exp(-18.0 * f)
        p += hz * _SIN_N / RATE
        out[i] = _SIN[int(p) & 2047] * math.exp(-7.5 * f) * vol
    return out


def _snare(vol=0.34):
    """Brushes, not sticks: mostly a dull hiss with just enough tone
    under it to say which drum it is."""
    n = int(0.22 * RATE)
    out = [0.0] * n
    rng = random.Random(7)
    last = 0.0
    p = 0.0
    for i in range(n):
        f = i / n
        last = last * 0.62 + rng.uniform(-1, 1) * 0.38
        p += 186.0 * _SIN_N / RATE
        tone = 0.35 * _SIN[int(p) & 2047] * math.exp(-16.0 * f)
        out[i] = (last + tone) * math.exp(-9.0 * f) * vol
    return out


def _hat(vol=0.12, shut=True):
    """Noise, filtered down until it is a tick rather than a hiss."""
    n = int((0.07 if shut else 0.19) * RATE)
    out = [0.0] * n
    rng = random.Random(11)
    hi = 0.0
    prev = 0.0
    for i in range(n):
        v = rng.uniform(-1, 1)
        hi = v - prev + hi * 0.55       # a dull highpass, so it is not bass
        prev = v
        out[i] = hi * math.exp(-(26.0 if shut else 9.0) * i / n) * vol
    return out


def _vinyl(n, vol=0.030, seed=3):
    """The record this is supposedly coming off: a bed of surface noise
    with the odd click in it. Nothing else on the loop says "lofi" as
    plainly as this does, and it costs one pass of the buffer."""
    rng = random.Random(seed)
    out = [0.0] * n
    last = 0.0
    for i in range(n):
        last = last * 0.86 + rng.uniform(-1, 1) * 0.14
        out[i] = last * vol
    # and the clicks, about ten a second, each one a dozen samples long
    for _ in range(int(n / RATE * 11)):
        at = rng.randrange(n)
        amp = rng.uniform(0.3, 1.0) * vol * 9
        for k in range(14):
            if at + k < n:
                out[at + k] += amp * math.exp(-0.45 * k) * rng.uniform(-1, 1)
    return out


def _lowpass(buf, a):
    """One pole, in place. This is the single thing that turns a pile of
    synthesis into something that sounds like it is in the next room."""
    y = 0.0
    for i, v in enumerate(buf):
        y += a * (v - y)
        buf[i] = y
    return buf


_music = None


def music_loop():
    global _music
    if _music is not None or not _audio:
        return _music
    bars = len(LOFI_BARS) * CHORD_BARS
    n = int(bars * BAR * RATE)
    buf = [0.0] * n

    kick, snare, hat = _kick(), _snare(), _hat()
    cache = {}
    for ci, (name, bass, voicing) in enumerate(LOFI_BARS):
        at = int(ci * CHORD_BARS * BAR * RATE)
        # the chord, rolled rather than struck - no two fingers land at
        # the same moment on a record anybody wants to listen to
        for v, f in enumerate(voicing):
            note = cache.get(f)
            if note is None:
                note = _rhodes(f, CHORD_BARS * BAR * 0.92, 0.26, seed=int(f))
                cache[f] = note
            _mix(buf, at + int(v * 0.035 * RATE), note, 0.52)
            # and again, quietly, half a bar later, so the chord breathes
            _mix(buf, at + int((BAR * 1.5 + v * 0.03) * RATE), note, 0.17)
        low = cache.get(("bass", bass))
        if low is None:
            low = _note(bass, BAR * 0.85, "low", 0.52, 0.03, 0.55)
            cache[("bass", bass)] = low
        for b in range(CHORD_BARS):
            _mix(buf, at + int(b * BAR * RATE), low, 0.46)
            # the fifth, late in the bar, which is the whole bass part
            fifth = cache.get(("bass", bass * 1.5))
            if fifth is None:
                fifth = _note(bass * 1.5, BAR * 0.35, "low", 0.5, 0.03, 0.6)
                cache[("bass", bass * 1.5)] = fifth
            _mix(buf, at + int((b * BAR + BEAT * 2.5) * RATE), fifth, 0.28)

        # the kit, two bars of it per chord
        for b in range(CHORD_BARS):
            bar_at = at + int(b * BAR * RATE)
            last = ci == len(LOFI_BARS) - 1 and b == CHORD_BARS - 1
            for st in KICKS:
                _mix(buf, bar_at + int(st * STEP * RATE), kick, 0.50)
            if last:                 # a pickup into the top of the loop
                _mix(buf, bar_at + int(14 * STEP * RATE), kick, 0.34)
            for st in SNARES:
                _mix(buf, bar_at + int(st * STEP * RATE), snare, 0.62)
            for st in HATS:
                late = SWING * STEP if (st // 2) % 2 else 0.0
                quiet = 0.78 if (st // 2) % 2 else 1.0
                _mix(buf, bar_at + int((st * STEP + late) * RATE), hat,
                     0.55 * quiet)

    _mix(buf, 0, _vinyl(n), 1.0)
    # warm it: everything above a few kilohertz goes, which is most of
    # what a listener would call "bright" and all of what they would call
    # "a computer made this"
    _lowpass(buf, 0.34)
    try:
        _music = _to_sound(buf, MUSIC_GAIN)
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
        m.set_volume(MUSIC_VOL)
        m.play(loops=-1)
        _music_on = True
    elif not on and _music_on:
        m.stop()
        _music_on = False


def init_audio():
    """Open the mixer, and then believe what it says about itself.

    pre_init is a request, not an instruction: SDL is allowed to hand
    back a different rate and a different number of channels, and on a
    machine with no mono device it will. Everything here is synthesised
    against RATE, so the one thing that must not happen is RATE saying
    22050 while the device runs at 44100 - every note would come out an
    octave high and nobody would know why. Ask, then take what you are
    given and build to that instead.
    """
    global _audio, RATE
    try:
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.mixer.init()
        got = pygame.mixer.get_init()
        if got:
            RATE = got[0]
        _audio = True
    except pygame.error:
        _audio = False
    return _audio


# ---------------------------------------------------------------------------
# A CARD
#
# Paper, a window with a cat in it, and a rule along the bottom. The
# rarity is in the border and in one word, never in the paper, because a
# binder of thirty-six differently coloured cards looks like a toy and
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
              show_rate=True, shut=False, variant=0, shiny=False, fake=None):
    rect = pygame.Rect(rect)
    acc = mix(rarity_colour(breed.rarity), LAMP, 0.45) if shiny \
        else rarity_colour(breed.rarity)
    grade = 4 if maxed else grade_of(level)
    # better paper as it goes: a stray comes on card, a retired breed
    # comes on something you would frame
    if breed.rarity == R_UNLISTED:
        # Not printed on paper at all. The catalogue has no card for
        # these, so the ones you end up with are black stock and silver
        # ink, and they do not sit in the grid with the rest.
        stock = mix(INK, acc, 0.10 + 0.02 * grade)
    else:
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
                      min(card_cat_height(rect), win.h - 5), shut, level,
                      variant, shiny)
    surf.blit(img, img.get_rect(midbottom=(win.centerx, win.bottom - 4)))
    surf.set_clip(old)
    pygame.draw.rect(surf, mix(acc, INK if grade < 3 else LAMP,
                               0.45 if grade < 3 else 0.30), win, width=1,
                     border_radius=4)

    # The level, as a number, in the corner of the window. The pips along
    # the foot say the same thing, but counting ten dots is not reading,
    # and this is the one part of the card that moves on EVERY level and
    # not only at a grade.
    if shiny:                       # the one the catalogue cannot explain
        pygame.draw.rect(surf, mix(LAMP, CREAM, 0.35), rect, width=3,
                         border_radius=7)
        chip = pygame.Rect(0, 0, min(64, rect.w - 26), 17)
        chip.midtop = (rect.centerx, win.bottom - 20)
        pygame.draw.rect(surf, mix(LAMP, acc, 0.3), chip, border_radius=4)
        text(surf, "SHINY", 11, chip.center, mix(INK, acc, 0.1), center=True,
             kind="mono", bold=True, shadow=False)
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
    # black stock needs silver ink; the paper colours vanish on it
    dark = breed.rarity == R_UNLISTED
    ink = mix(CREAM, acc, 0.3) if dark else mix(INK, acc, 0.22)
    quiet = mix(CREAM, acc, 0.5) if dark else mix(INK, acc, 0.4)
    faint = mix(CREAM, INK, 0.5) if dark else mix(INK, acc, 0.3)
    nm = breed.name
    if fake == "name":          # a letter doubled, the way a bad copy goes
        nm = nm[:2] + nm[1] + nm[2:]
    text(surf, nm, fit(nm, 17, inner.w - 6),
         (rect.centerx, name_y + 8), ink, center=True, shadow=False)
    hairline(surf, inner.x + 8, row_y - 3, inner.right - 8,
             mix(INK, acc, 0.5), 60)
    said_rarity = (breed.rarity if fake != "rarity"
                   else (breed.rarity + 2) % SOLD_RARITIES)
    text(surf, rarity_name(said_rarity), 11 if not compact else 9,
         (inner.x + 4, row_y + (2 if compact else 0)),
         mix(CREAM, acc, 0.5) if breed.rarity == R_UNLISTED
         else mix(INK, acc, 0.45), kind="mono", shadow=False,
         max_w=inner.w - (56 if show_rate else 8))
    if show_rate and not compact:
        said_rate = breed.rate_at(min(MAX_LEVEL, level + 3)
                                  if fake == "rate" else level)
        text(surf, rate(said_rate), 11,
             (inner.right - 4, row_y + 6), faint, right=True,
             kind="mono", shadow=False)

    if compact:
        pass
    elif maxed:
        ban = pygame.Rect(inner.x + 14, sub_y, inner.w - 28, 15)
        pygame.draw.rect(surf, mix(acc, LAMP, 0.42), ban, border_radius=3)
        pygame.draw.rect(surf, mix(acc, INK, 0.35), ban, width=1,
                         border_radius=3)
        text(surf, "RETIRED", 11, (rect.centerx, sub_y + 6),
             mix(CREAM, acc, 0.4) if dark else mix(INK, acc, 0.25),
             center=True, kind="mono", shadow=False)
    else:
        # The coat name needs room it does not have on a binder card:
        # at 118 pixels wide there are fifty left after the dupe count,
        # and "black and white" does not go in fifty whatever size it is
        # shrunk to. Below that width the count wins - it is the one that
        # changes - and the name is on the card when you open it.
        if (len(breed.coats) > 1 or shiny) and inner.w >= 150:
            text(surf, coat_name(breed, variant, shiny, full=shiny), 11,
                 (inner.x + 4, sub_y),
                 mix(CREAM, LAMP if shiny else acc, 0.45) if dark
                 else mix(INK, LAMP if shiny else acc, 0.35),
                 kind="mono", shadow=False, max_w=inner.w - 58)
        if level < MAX_LEVEL:
            text(surf, f"{dupes} of {dupes_for(level)}", 11,
                 (inner.right - 4, sub_y + 6), quiet,
                 right=True, kind="mono", shadow=False)

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
         shade(TEA, 0.55), center=True, kind="mono", shadow=False,
         max_w=rect.w - 8)
    return rect


# ---------------------------------------------------------------------------
# WHAT THE SHOP SENDS
# ---------------------------------------------------------------------------
def _crimp(surf, r, col, top=True, teeth=9):
    """The heat-sealed end of a wrapper: the one detail that says this is
    a packet of cards and not a small cardboard box."""
    h = max(3, int(r.h * 0.10))
    y = r.y if top else r.bottom - h
    pts = []
    for i in range(teeth * 2 + 1):
        x = r.x + r.w * i / (teeth * 2)
        pts.append((x, y + (0 if i % 2 else h)))
    pts += [(r.right, y + h if top else y), (r.x, y + h if top else y)]
    pygame.draw.polygon(surf, col, pts)


def _wrapper(surf, r, acc, seed=0, foil=False):
    """One sealed pack. Paper, a band of colour across the middle, a cat
    on the front and a crimp at each end."""
    r = pygame.Rect(r)
    base = mix(acc, PAPER, 0.42 if not foil else 0.20)
    pygame.draw.rect(surf, shade(base, 0.76), r.move(1, 2), border_radius=3)
    pygame.draw.rect(surf, base, r, border_radius=3)
    _crimp(surf, r, shade(base, 0.82), True)
    _crimp(surf, r, shade(base, 0.82), False)
    # the band, and the window in it
    band = pygame.Rect(r.x, r.y + r.h * 0.34, r.w, max(6, r.h * 0.26))
    pygame.draw.rect(surf, mix(acc, INK, 0.18), band)
    pygame.draw.line(surf, mix(acc, CREAM, 0.45), (r.x, band.y),
                     (r.right, band.y), 1)
    # a cat on the front, small enough to be a mark rather than a picture
    cx, cy = r.centerx, band.centery
    rad = max(3, int(min(r.w, band.h) * 0.30))
    pygame.draw.circle(surf, mix(acc, CREAM, 0.55), (cx, cy), rad)
    for sx in (-1, 1):
        pygame.draw.polygon(surf, mix(acc, CREAM, 0.55), [
            (cx + sx * rad * 0.45, cy - rad * 0.55),
            (cx + sx * rad * 1.05, cy - rad * 1.35),
            (cx + sx * rad * 1.05, cy - rad * 0.30)])
    if foil:                    # a sheen down one corner, for the dear ones
        sh = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.polygon(sh, (*mix(CREAM, LAMP, 0.4), 60), [
            (r.w * 0.52, 0), (r.w * 0.80, 0), (r.w * 0.34, r.h),
            (r.w * 0.06, r.h)])
        surf.blit(sh, r.topleft)
        pygame.draw.rect(surf, mix(LAMP, CREAM, 0.4), r, width=1,
                         border_radius=3)


def _sleeved_card(surf, r, acc):
    """Not a packet. One card, in a rigid sleeve, which is what you are
    paying for when a product holds exactly one of them."""
    pygame.draw.rect(surf, mix(TEA, CREAM, 0.30), r, border_radius=3)
    inner = r.inflate(-max(4, r.w * 0.16), -max(4, r.h * 0.12))
    pygame.draw.rect(surf, mix(PAPER, acc, 0.12), inner, border_radius=2)
    win = pygame.Rect(inner.x + 2, inner.y + 2, inner.w - 4, inner.h * 0.56)
    pygame.draw.rect(surf, mix(acc, INK, 0.70), win, border_radius=2)
    cx, cy = win.centerx, win.centery + win.h * 0.10
    rad = max(3, int(win.h * 0.30))
    pygame.draw.circle(surf, mix(acc, CREAM, 0.5), (cx, int(cy)), rad)
    for sx in (-1, 1):
        pygame.draw.polygon(surf, mix(acc, CREAM, 0.5), [
            (cx + sx * rad * 0.45, cy - rad * 0.55),
            (cx + sx * rad * 1.05, cy - rad * 1.35),
            (cx + sx * rad * 1.05, cy - rad * 0.30)])
    pygame.draw.rect(surf, shade(mix(TEA, CREAM, 0.30), 0.7), r, width=2,
                     border_radius=3)


def pack_accent(pack):
    """The colour of a product, from the average card in it.

    Not the floor and not the best card: the AVERAGE. It makes the
    catalogue a colour ladder you can read down without reading a word
    of it, which is what the thumbnails are for.
    """
    tot = sum(pack.weights) or 1
    ev = sum(r * w for r, w in enumerate(pack.weights)) / tot
    return rarity_colour(int(clamp(round(ev), 0, SOLD_RARITIES - 1)))


def draw_pack_art(surf, rect, pack, t=0.0):
    """Every product in both shops, drawn as what it actually is: sealed
    packets of cards.

    They used to be boxes, cases and crates - nine hand-drawn shapes and
    a blank for everything added since, which by now was seven of them.
    One wrapper, repeated and sized, covers the lot and means a new
    product has art the moment it exists. What tells them apart is how
    many packets there are, how big they are, and the colour of the
    average card inside.
    """
    rect = pygame.Rect(rect)
    acc = pack_accent(pack)
    packs = packs_in(pack.cards)
    foil = pack.shiny_mult > 1.0 or pack.floor >= R_CHAMPION

    if pack.cards <= 1:                      # one card, in a hard sleeve
        r = pygame.Rect(0, 0, int(rect.h * 0.52), int(rect.h * 0.78))
        r.center = rect.center
        _sleeved_card(surf, r, acc)
        return

    show = int(clamp(packs, 1, 5))
    # a wrapper is roughly two to three cards wide; more of them in the
    # same thumbnail means each one is drawn smaller, which is how a
    # Whole Shelf reads as bigger than a Shelf Box at a glance
    ph = int(rect.h * (0.86 if show == 1 else 0.80 if show < 4 else 0.72))
    pw = int(min(rect.w * 0.92 / (show * 0.62 + 0.38), ph * 0.70))
    step = pw * 0.62 if show > 1 else 0
    total = pw + step * (show - 1)
    x0 = rect.centerx - total / 2
    for i in range(show):
        r = pygame.Rect(0, 0, pw, ph)
        r.midbottom = (int(x0 + pw / 2 + step * i),
                       rect.bottom - int(rect.h * 0.06) - (i % 2) * 2)
        _wrapper(surf, r, acc, i, foil)

    if packs > 5:
        # too many to show: strap the brick up and say how many
        band = pygame.Rect(rect.x + rect.w * 0.06,
                           rect.centery - rect.h * 0.08,
                           rect.w * 0.88, max(7, rect.h * 0.16))
        pygame.draw.rect(surf, mix(WOOD, EMBER, 0.25), band)
        pygame.draw.rect(surf, shade(WOOD, 0.7), band, width=1)
        if band.h >= 11:
            text(surf, f"x{packs}", min(12, int(band.h) - 1), band.center,
                 warm(CREAM, 0.15), center=True, kind="mono", shadow=False)

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
AREAS = ("conv", "hall", "study", "cats")
AREA_NAME = {"conv": "THE CONVENTION", "hall": "THE HALL",
             "study": "THE DESK", "cats": "THE CAT ROOM"}
# How wide each room is. Only the cat room is wider than the window onto
# it, and walking inside it slides the camera rather than the room.
AREA_WIDE = {"conv": W, "hall": W, "study": W, "cats": 2000}

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
STRAY_AT = (892, 700)        # beside the mat, out of the way of the post

# ---------------------------------------------------------------------------
# THE CAT ROOM
#
# Twice as wide as the screen, so you walk along it, and the only room in
# the flat where the cats are not ornaments: they cross the floor, climb
# the tree, eat, drink, play, scratch, wash and sleep, and which of those
# they do is decided by the breed's temperament rather than by a dice
# roll shared between all of them.
#
# A spot is a piece of furniture a cat can occupy. Its KIND says what can
# be done there, and nothing else in here needs to know what the drawing
# looks like - which is what lets the furniture move without the
# behaviour noticing.
# ---------------------------------------------------------------------------
CATS_W = 2000              # the room is wider than the window onto it
CATS_FLOOR = 556           # where the wall stops and the boards start
CAT_WALK_Y = 728           # the line cats walk along
TREE_X = 790
TREE2_X = 1880

SPOT_ACTS = {
    "perch": ("watch", "loaf", "sleep", "groom"),
    "wall": ("climb", "watch", "loaf", "sleep"),
    "plant": ("sniff", "watch", "loaf"),
    "beam": ("climb", "watch", "sleep", "loaf"),
    "hay": ("sleep", "hide", "loaf"),
    "run": ("prowl", "play", "watch"),
    "tunnel": ("hide", "play", "sleep"),
    "bird": ("chatter", "watch", "sit"),
    "bed": ("sleep", "loaf", "groom"),
    "chair": ("sleep", "loaf", "groom", "sit"),
    "box": ("sleep", "loaf", "watch"),
    "warm": ("sleep", "loaf", "groom"),
    "food": ("eat",),
    "water": ("drink",),
    "toy": ("play",),
    "post": ("scratch",),
    "floor": ("prowl", "groom", "sit", "play"),
}

# kind, x, baseline y, which way it faces, how big a cat sits there, name
ROOM_SPOTS = (
    ("perch", 252, 362, 1, 120, "the windowsill"),
    ("perch", 492, 356, -1, 104, "the low shelf"),
    ("perch", 636, 254, 1, 104, "the high shelf"),
    ("perch", TREE_X - 56, 372, -1, 118, "the cat tree"),
    ("perch", TREE_X + 30, 238, 1, 108, "the top of the cat tree"),
    ("post", TREE_X - 62, 552, 1, 132, "the sisal post"),
    ("bed", 392, 424, 1, 126, "the blanket chest"),
    ("bed", 272, 712, 1, 142, "the basket"),
    ("food", 566, 716, -1, 126, "the food bowl"),
    ("water", 648, 716, -1, 126, "the water bowl"),
    ("toy", 452, 730, 1, 130, "the ball"),
    ("floor", 940, 732, 1, 138, "the rug"),
    ("perch", 1292, 320, 1, 118, "the second window"),
    ("warm", 1296, 436, -1, 112, "the radiator shelf"),
    ("perch", 1486, 392, 1, 116, "the back of the chair"),
    ("chair", 1572, 548, -1, 140, "the armchair"),
    ("box", 1744, 550, 1, 128, "the box fort"),
    ("toy", 1648, 730, -1, 130, "the feather"),
    ("floor", 1802, 732, 1, 134, "the floorboards"),
    ("post", TREE2_X - 58, 548, 1, 130, "the scratching post"),
    ("perch", 1872, 232, -1, 106, "the bookshelf"),
    # Twelve residents and two patches of open floor meant a shadow
    # could never prowl and a lap cat could never just sit: there was
    # nowhere to do it. The room is two thousand pixels wide; it can
    # spare some floor.
    ("floor", 352, 742, 1, 136, "the middle of the room"),
    ("floor", 1180, 736, -1, 134, "the boards by the door"),
    ("floor", 1456, 744, 1, 132, "in front of the chair"),
    ("chair", 1660, 604, -1, 130, "the arm of the chair"),
    ("bed", 1116, 700, 1, 136, "the folded blanket"),
)
ROOM_BASE = len(ROOM_SPOTS)      # everything past here is through the wall

# The back room. These are APPENDED, and that is deliberate: a resident
# holds its spot as an index into this tuple, so anything inserted in the
# middle would move every cat in a saved room onto different furniture.
BACK_SPOTS = (
    ("bird", 2146, 316, 1, 112, "the bird window"),
    ("wall", 2066, 468, 1, 104, "the bottom step"),
    ("wall", 2182, 386, -1, 102, "the middle step"),
    ("wall", 2298, 302, 1, 100, "the top step"),
    ("floor", 2104, 736, 1, 136, "the new boards"),
    ("toy", 2246, 730, 1, 130, "the spring"),
    ("tunnel", 2338, 700, -1, 124, "the mouth of the tunnel"),
    ("tunnel", 2532, 700, 1, 122, "the far end of the tunnel"),
    ("post", 2596, 556, 1, 130, "the tall post"),
    ("chair", 2706, 566, -1, 142, "the sofa"),
    ("chair", 2870, 526, -1, 118, "the arm of the sofa"),
    ("bed", 2462, 470, -1, 124, "the hammock"),
    ("floor", 2634, 742, -1, 134, "the sunny patch"),
    ("water", 2930, 716, -1, 118, "the second water bowl"),
)
ROOM_SPOTS = ROOM_SPOTS + BACK_SPOTS

# The garden room, 2960 to 3860. Glass, flagstones and too many plants.
GARDEN_SPOTS = (
    ("post", 3002, 556, -1, 126, "the post by the step"),
    ("plant", 3012, 616, 1, 124, "the big fern"),
    ("perch", 3094, 420, -1, 112, "the plant shelf"),
    ("perch", 3200, 288, 1, 106, "the top of the trellis"),
    ("floor", 3180, 740, 1, 134, "the warm flagstones"),
    ("plant", 3262, 648, -1, 122, "the herb pots"),
    ("perch", 3348, 352, 1, 110, "the glass ledge"),
    ("chair", 3444, 556, -1, 138, "the wicker chair"),
    ("bed", 3540, 628, 1, 130, "the cushion by the door"),
    ("toy", 3626, 732, -1, 128, "the ball of twine"),
    ("water", 3712, 718, -1, 122, "the watering can"),
    ("food", 3790, 740, 1, 128, "the bowl by the garden door"),
)

# The loft, 3860 to 4760. Beams, two skylights and other people's boxes.
LOFT_SPOTS = (
    ("floor", 3960, 742, -1, 132, "the top of the ladder"),
    ("beam", 3922, 300, 1, 104, "the low beam"),
    ("beam", 4040, 236, -1, 102, "the high beam"),
    ("perch", 4140, 470, 1, 108, "the water tank"),
    ("beam", 4160, 300, 1, 104, "the cross beam"),
    ("warm", 4250, 640, -1, 120, "the flue"),
    ("perch", 4262, 420, -1, 110, "the skylight ledge"),
    ("box", 4352, 560, 1, 128, "the tea chest"),
    ("box", 4452, 620, -1, 126, "the suitcase"),
    ("bed", 4542, 600, 1, 130, "the old eiderdown"),
    ("food", 4640, 738, 1, 128, "the saucer by the hatch"),
    ("post", 4700, 560, 1, 128, "the roof post"),
)

# The sanctuary, 4760 to 5960. A barn with a stove in it.
SANCT_SPOTS = (
    ("hay", 4822, 620, 1, 132, "the hay bales"),
    ("food", 4872, 718, -1, 124, "the long trough"),
    ("hay", 4930, 548, -1, 128, "the top bale"),
    ("water", 4962, 718, 1, 124, "the water trough"),
    ("warm", 5040, 600, 1, 124, "the stove"),
    ("post", 5470, 556, 1, 128, "the post by the beds"),
    ("bed", 5142, 652, -1, 130, "the first bed in the row"),
    ("toy", 5182, 734, -1, 128, "the rope"),
    ("bed", 5232, 652, 1, 130, "the second bed"),
    ("tunnel", 5302, 700, -1, 124, "the straw tunnel"),
    ("bed", 5322, 652, -1, 130, "the third bed"),
    ("bed", 5412, 652, 1, 130, "the fourth bed"),
    ("perch", 5502, 420, -1, 112, "the hay loft"),
    ("chair", 5600, 596, -1, 136, "the keeper's chair"),
    ("perch", 5604, 336, 1, 108, "the rafters"),
    ("post", 5700, 560, 1, 130, "the barn post"),
    ("run", 5800, 742, -1, 134, "the outdoor run"),
    ("run", 5892, 742, 1, 132, "the far end of the run"),
)

ROOM_SPOTS = ROOM_SPOTS + GARDEN_SPOTS + LOFT_SPOTS + SANCT_SPOTS

# ---------------------------------------------------------------------------
# WHAT THE FLAT BECOMES
#
# Four of these, bought in order, each one a wall taken out or a door
# unlocked. They are the only thing in the game that money buys purely to
# look at: not one of them earns a penny. What they buy is room, and cats
# to put in it, and places for those cats to be.
#
# The last one is not in the flat at all. By the time anybody can afford
# it there is nothing left in the shop worth wanting and a great deal of
# money doing nothing, which is exactly the point at which somebody
# starts looking at outbuildings.
# ---------------------------------------------------------------------------
class Wing:
    __slots__ = ("key", "name", "price", "wide", "cap", "spots", "blurb")

    def __init__(self, key, name, price, wide, cap, spots, blurb):
        self.key = key
        self.name = name
        self.price = price
        self.wide = wide        # pixels of room it adds
        self.cap = cap          # cats it adds
        self.spots = spots      # how many places, appended in this order
        self.blurb = blurb


WINGS = (
    Wing("back", "Knock Through to the Back Room", 120000, 960, 8, 14,
         "The flat next door has been empty for a year and the landlord "
         "would rather have one tenant than none. Take it and take the "
         "wall out."),
    Wing("garden", "The Garden Room", 400000, 900, 6, 12,
         "A glass lean-to on the back, with a door that is never quite "
         "shut and flagstones that hold the heat until ten at night."),
    Wing("loft", "The Loft Conversion", 1200000, 900, 6, 12,
         "A ladder, two skylights and eighty years of other people's "
         "boxes. They are up there within a minute of the hatch opening."),
    Wing("sanct", "The Sanctuary", 3000000, 1200, 14, 18,
         "The barn at the end of the lane, a stove in it, and room for "
         "every cat that turns up at the door for as long as there are "
         "cats that turn up at doors."),
)
BY_WING = {w.key: w for w in WINGS}
CATS_W_BIG = CATS_W + sum(w.wide for w in WINGS)


def wing_x(i):
    """Where a wing starts, along the room."""
    return CATS_W + sum(w.wide for w in WINGS[:i])

ACT_POSE = {"sleep": "curl", "loaf": "sit", "sit": "sit", "watch": "sit",
            "groom": "sit", "eat": "stand", "drink": "stand",
            "play": "stand", "scratch": "stand", "prowl": "stand",
            "climb": "stand", "hide": "curl", "chatter": "sit",
            "sniff": "sit"}
ACT_WORD = {"sleep": "asleep", "loaf": "loafing", "sit": "sitting",
            "watch": "watching", "groom": "washing", "eat": "eating",
            "drink": "drinking", "play": "playing", "scratch": "scratching",
            "prowl": "prowling", "climb": "climbing", "hide": "hiding",
            "chatter": "chattering", "sniff": "sniffing"}
# The preposition was picked off the pose - "on" for anything sitting,
# "at" for anything standing - which reads right for every act there was
# and wrong for all three of the new ones. A cat is not hiding ON a
# tunnel.
ACT_PREP = {"climb": "up", "hide": "in", "chatter": "at", "prowl": "along",
            "sniff": "at"}


class Resident:
    """One cat living in the cat room, and what it is up to."""
    __slots__ = ("breed", "level", "spot", "act", "timer", "x", "y",
                 "state", "phase", "face", "home", "seed", "coat", "shiny")

    def __init__(self, breed, level, spot, seed, coat=0, shiny=False):
        self.breed = breed
        self.level = level
        self.coat = coat
        self.shiny = shiny
        self.spot = spot
        self.act = "loaf"
        self.timer = 2.0 + seed % 7
        self.state = "rest"
        self.phase = 0.0
        self.face = ROOM_SPOTS[spot][3]
        self.home = spot
        self.seed = seed
        self.x = ROOM_SPOTS[spot][1]
        self.y = ROOM_SPOTS[spot][2]

    @property
    def size(self):
        return ROOM_SPOTS[self.spot][4]

    @property
    def pose(self):
        return "stand" if self.state != "rest" else ACT_POSE[self.act]

    @property
    def doing(self):
        if self.state != "rest":
            return "on its way to " + ROOM_SPOTS[self.spot][5]
        prep = ACT_PREP.get(self.act,
                            "at" if ACT_POSE[self.act] == "stand" else "on")
        return f"{ACT_WORD[self.act]} {prep} {ROOM_SPOTS[self.spot][5]}"


def _elevated(spot):
    return ROOM_SPOTS[spot][2] < CAT_WALK_Y - 24


class CatRoom:
    """The simulation. It runs whether or not you are in the room, which
    is why there is always something going on when you walk in."""

    def __init__(self):
        self.res = []
        self.keys = ()
        self.rng = random.Random(11)
        self.toy_t = 0.0
        self.view = 0.0        # where the camera is, so cats can prefer it
        self.nspots = ROOM_BASE

    def sync(self, state, cap):
        """Rebuild the residents when the set of cats in here changes."""
        self.nspots = room_spot_count(state)
        want = tuple(b.key for b in room_cats(state)[:cap])
        if want == self.keys:
            for r in self.res:                 # levels and coats move
                card = state.cards.get(r.breed.key)
                if card:
                    r.level, r.coat, r.shiny = (card.level, card.coat,
                                                card.shiny)
            return
        for r in self.res:              # nothing may sit past the wall
            if r.spot >= self.nspots:
                r.spot = r.home = self.rng.randrange(self.nspots)
                r.x = ROOM_SPOTS[r.spot][1]
                r.y = ROOM_SPOTS[r.spot][2]
        taken = set()
        res = []
        for i, k in enumerate(want):
            b = BY_KEY[k]
            spot = self._pick_spot(b, None, taken)
            if i < 4 and ROOM_SPOTS[spot][1] > W - 60:
                near = [j for j in range(len(ROOM_SPOTS))
                        if j not in taken and ROOM_SPOTS[j][1] < W - 60]
                if near:
                    spot = self.rng.choice(near)
            taken.add(spot)
            c = state.cards[k]
            r = Resident(b, c.level, spot, i * 37 + 5, c.coat, c.shiny)
            r.act = self.rng.choice(SPOT_ACTS[ROOM_SPOTS[spot][0]])
            res.append(r)
        self.res = res
        self.keys = want

    # -- choosing what to do next ------------------------------------------
    def _pick_spot(self, breed, act, taken):
        """A spot this cat would like, free, and able to host the act.

        Weighted toward the part of the room you are standing in. Without
        that, a room twice as wide as the window with three cats in it is
        an empty room with three cats round the corner, which is exactly
        what it looked like.
        """
        T = breed.temperament
        pool = []
        for i, (kind, x, y, face, size, name) in enumerate(
                ROOM_SPOTS[:self.nspots]):
            if i in taken:
                continue
            if act is not None and act not in SPOT_ACTS[kind]:
                continue
            weight = 3.0 if kind in T["likes"] else 1.0
            if self.view - 80 <= x <= self.view + W + 80:
                weight *= 3.5 if T is TEMPERS["lap"] else 2.2
            pool.append((i, weight))
        if not pool:
            return self.rng.randrange(self.nspots)
        total = sum(wt for _, wt in pool)
        pick = self.rng.uniform(0, total)
        acc = 0.0
        for i, wt in pool:
            acc += wt
            if pick <= acc:
                return i
        return pool[-1][0]

    def _choose(self, r):
        T = r.breed.temperament
        taken = {o.spot for o in self.res if o is not r}
        acts = [(a, w) for a, w in T["acts"].items()
                if any(a in SPOT_ACTS[ROOM_SPOTS[i][0]]
                       for i in range(self.nspots) if i not in taken)]
        if not acts:
            acts = [("loaf", 1)]
        total = sum(w for _, w in acts)
        pick = self.rng.uniform(0, total)
        acc = 0.0
        act = acts[-1][0]
        for a, w in acts:
            acc += w
            if pick <= acc:
                act = a
                break
        spot = self._pick_spot(r.breed, act, taken)
        lo, hi = T["stay"]
        r.timer = self.rng.uniform(lo, hi) * 0.55
        r.act = act
        if spot == r.spot:
            r.state = "rest"
            r.face = ROOM_SPOTS[spot][3]
            return
        r.spot = spot
        r.phase = 0.0
        r.state = "down" if r.y < CAT_WALK_Y - 24 else "walk"

    # -- time ---------------------------------------------------------------
    def update(self, dt, state, cap, view=None):
        if view is not None:
            self.view = view
        self.sync(state, cap)
        self.toy_t += dt
        for r in self.res:
            T = r.breed.temperament
            if r.state == "rest":
                r.timer -= dt
                if r.act == "prowl":           # prowling is not standing still
                    r.x += r.face * 26 * dt * T["speed"]
                    home_x = ROOM_SPOTS[r.spot][1]
                    if abs(r.x - home_x) > 110:
                        r.face = 1 if r.x < home_x else -1
                    r.y = CAT_WALK_Y
                if r.timer <= 0:
                    self._choose(r)
            elif r.state == "down":
                r.phase += dt * 2.6
                top = ROOM_SPOTS[r.home][2] if r.home < len(ROOM_SPOTS) else r.y
                f = min(1.0, r.phase)
                r.y = top + (CAT_WALK_Y - top) * f
                r.x += (ROOM_SPOTS[r.spot][1] - r.x) * 0.04 * f
                if f >= 1.0:
                    r.state = "walk"
                    r.phase = 0.0
            elif r.state == "walk":
                tx = ROOM_SPOTS[r.spot][1]
                r.face = 1 if tx > r.x else -1
                r.x += r.face * 118 * T["speed"] * dt
                r.y = CAT_WALK_Y
                if abs(tx - r.x) < 8:
                    r.x = tx
                    if _elevated(r.spot):
                        r.state = "up"
                        r.phase = 0.0
                    else:
                        r.state = "rest"
                        r.home = r.spot
                        r.y = ROOM_SPOTS[r.spot][2]
                        r.face = ROOM_SPOTS[r.spot][3]
            else:                               # "up", a hop onto something
                r.phase += dt * 2.2
                f = min(1.0, r.phase)
                top = ROOM_SPOTS[r.spot][2]
                r.y = CAT_WALK_Y + (top - CAT_WALK_Y) * (f ** 0.7)
                if f >= 1.0:
                    r.state = "rest"
                    r.home = r.spot
                    r.y = top
                    r.face = ROOM_SPOTS[r.spot][3]

    def tally(self):
        """What the room is doing, for the line under the room name."""
        out = {}
        for r in self.res:
            word = ACT_WORD[r.act] if r.state == "rest" else "on the move"
            out[word] = out.get(word, 0) + 1
        return out

    # -- drawing ------------------------------------------------------------
    def rect_of(self, r):
        img = cat_surface(r.breed, r.pose, r.size, level=r.level,
                          variant=r.coat, shiny=r.shiny)
        return img.get_rect(midbottom=(round(r.x), round(r.y)))

    def draw(self, surf, t):
        for r in self.res:
            if in_view(r.x - 120, r.x + 120):
                self._draw_one(surf, r, t)

    def _draw_one(self, surf, r, t):
        ph = t * 1.4 + r.seed
        # A blink is one frame in thirty and a breath was one and a bit
        # pixels; at this size neither of them read as a living thing, so
        # the resting animations are two or three times what a cat
        # actually does.
        shut = r.act == "sleep" or (math.sin(t * 0.9 + r.seed) > 0.955)
        img = cat_surface(r.breed, r.pose, r.size, shut, r.level,
                          r.coat, r.shiny)
        iw, ih = img.get_size()
        dy = 0.0
        sx = 1.0
        sy = 1.0 + (0.030 if r.act == "sleep" else 0.018) * \
            math.sin(ph * (0.6 if r.act == "sleep" else 1.0))
        if r.state in ("walk", "down", "up") or r.act == "prowl":
            dy = -abs(math.sin(t * 7.0 + r.seed)) * ih * 0.035
            sy = 1.0 + 0.02 * math.sin(t * 14.0 + r.seed)
        elif r.act in ("eat", "drink"):
            dy = abs(math.sin(t * (3.4 if r.act == "eat" else 2.2) + r.seed)) \
                * ih * 0.07
        elif r.act == "play":
            dy = -abs(math.sin(t * 5.0 + r.seed)) * ih * 0.06
            sx = 1.0 + 0.03 * math.sin(t * 5.0 + r.seed)
        elif r.act == "scratch":
            sy = 1.0 + 0.055 * abs(math.sin(t * 4.4 + r.seed))
            dy = -ih * 0.02 * abs(math.sin(t * 4.4 + r.seed))
        if r.state == "rest" and r.act in ("loaf", "sit", "watch"):
            # every so often it looks round the room
            look = math.sin(t * 0.21 + r.seed * 1.7)
            if look > 0.72:
                r.face = -ROOM_SPOTS[r.spot][3]
            elif look < -0.72:
                r.face = ROOM_SPOTS[r.spot][3]
            dy += math.sin(t * 0.8 + r.seed) * ih * 0.012
        if abs(sy - 1.0) > 0.001 or abs(sx - 1.0) > 0.001:
            img = pygame.transform.smoothscale(
                img, (max(2, int(iw * sx)), max(2, int(ih * sy))))
        if r.face < 0:
            img = pygame.transform.flip(img, True, False)
        if r.act == "groom" and r.state == "rest":
            img = pygame.transform.rotate(img, math.sin(t * 1.6 + r.seed) * 7)
        rect = img.get_rect(midbottom=(round(r.x), round(r.y + dy)))

        sh = pygame.Surface((max(4, iw), 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 85), (0, 0, max(4, iw), 12))
        surf.blit(sh, (round(r.x - iw / 2), round(r.y - 7)))
        surf.blit(img, rect)
        self._extras(surf, r, rect, t)

    def _extras(self, surf, r, rect, t):
        """The small drawn evidence that an activity is happening."""
        if r.state != "rest":
            return
        if r.act == "sleep":
            k = (t * 0.5 + r.seed) % 4.0
            if k < 2.2:
                a = int(170 * (1 - k / 2.2))
                y = rect.top - 6 - k * 16
                text(surf, "z", 13 + int(k * 3),
                     (rect.centerx + r.face * 18 + k * 6, y),
                     (*CREAM[:3],), center=True, kind="serif", alpha=a)
        elif r.act == "scratch":
            for i in range(3):
                y = rect.y + rect.h * (0.3 + 0.12 * i)
                x = rect.centerx + r.face * rect.w * 0.42
                pygame.draw.line(surf, mix(PAPER, WOOD, 0.4),
                                 (x, y + math.sin(t * 9 + i) * 3),
                                 (x + r.face * 14, y + 8), 2)
        elif r.act == "play":
            sw = math.sin(t * 5.0 + r.seed)
            if sw > 0:
                x = rect.centerx + r.face * rect.w * 0.38
                y = rect.centery + rect.h * 0.12
                pygame.draw.arc(surf, mix(CREAM, r.breed.look["coat"], 0.4),
                                (x - 12, y - 12, 24, 24),
                                0.2 if r.face > 0 else 2.4,
                                1.6 if r.face > 0 else 3.8, 3)
        elif r.act in ("eat", "drink"):
            x = rect.centerx + r.face * rect.w * 0.34
            for i in range(2):
                rr = 4 + ((t * 2 + i) % 2) * 5
                col = (118, 150, 208) if r.act == "drink" else (176, 132, 96)
                pygame.draw.circle(surf, col, (round(x), round(r.y - 6)),
                                   round(rr), 1)


def _cat_window(surf, r, t, seed=4):
    pygame.draw.rect(surf, (18, 22, 34), r)
    rng = random.Random(seed)
    for i in range(24):
        s = pygame.Surface((2, 2), pygame.SRCALPHA)
        s.fill((*CREAM, int(70 + 70 * abs(math.sin(t * 0.3 + i)))))
        surf.blit(s, (r.x + rng.randrange(6, r.w - 6),
                      r.y + rng.randrange(6, r.h - 6)))
    pygame.draw.rect(surf, WOOD, r, width=8)
    pygame.draw.line(surf, WOOD, (r.centerx, r.y), (r.centerx, r.bottom), 5)
    sill = pygame.Rect(r.x - 22, r.bottom - 2, r.w + 44, 18)
    pygame.draw.rect(surf, WOOD_HI, sill, border_radius=3)
    for sx, cx in ((-1, r.x - 10), (1, r.right + 10)):
        pygame.draw.polygon(surf, mix(RUG, WOOD, 0.4), [
            (cx, r.y - 14), (cx + sx * 46, r.y - 14),
            (cx + sx * 34, r.bottom - 6), (cx, r.bottom - 6)])
    return sill


# ---------------------------------------------------------------------------
# THE BACK ROOM
#
# Everything from x=2000 on, and only drawn when the wall is down. It is
# laid out against BACK_SPOTS the same way the front room is laid out
# against the first twenty-seven: the hammock is drawn where the hammock
# spot is, so a cat asleep in it is asleep in the thing you can see.
# ---------------------------------------------------------------------------
BACK_X = CATS_W            # where the old wall was


def _feeder(surf, x, y, t):
    """A feeder on a bracket outside the window, and whatever is on it.

    The birds are the point of the window. A cat chattering at an empty
    pane is a cat doing nothing."""
    pygame.draw.line(surf, shade(WOOD, 0.6), (x, y - 54), (x, y), 3)
    pygame.draw.polygon(surf, mix(WOOD, RUG, 0.3),
                        [(x - 22, y), (x + 22, y), (x + 15, y + 26),
                         (x - 15, y + 26)])
    pygame.draw.line(surf, shade(WOOD, 0.5), (x - 26, y), (x + 26, y), 3)
    for i in range(2):
        # two of them, hopping about on their own clock
        ph = t * 0.9 + i * 2.1
        bx = x - 14 + i * 28 + math.sin(ph) * 5
        by = y - 8 + (2 if math.sin(ph * 3) > 0.4 else 0)
        col = (176, 150, 112) if i else (150, 128, 108)
        pygame.draw.ellipse(surf, col, (bx - 7, by - 6, 14, 11))
        pygame.draw.circle(surf, col, (round(bx + 5), round(by - 7)), 4)
        pygame.draw.polygon(surf, shade(col, 0.7),
                            [(bx - 6, by - 4), (bx - 13, by + 1),
                             (bx - 5, by + 2)])


def _hammock(surf, x, y):
    """Slung between two brackets. The sag is drawn, not implied."""
    lo, hi = x - 86, x + 86
    for k, col in ((6, shade(RUG, 0.6)), (0, mix(RUG, WOOD, 0.35))):
        pts = []
        for i in range(17):
            f = i / 16
            px = lo + (hi - lo) * f
            pts.append((px, y + 26 + k + 30 * math.sin(math.pi * f)))
        pygame.draw.lines(surf, col, False, pts, 9)
    for sx in (lo, hi):
        pygame.draw.line(surf, shade(WOOD_HI, 0.8), (sx, y - 34),
                         (sx, y + 30), 4)
        pygame.draw.circle(surf, shade(WOOD, 0.7), (round(sx), round(y - 34)),
                           5)


def _sofa_back(surf, r):
    """The part of the sofa the cats sit in front of or on top of."""
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.14), (r.x, r.y, r.w, r.h - 40),
                     border_radius=16)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.04),
                     (r.x + 18, r.y + 16, r.w - 36, r.h - 78),
                     border_radius=12)
    for i in range(3):               # three cushions, one of them sat on
        cx = r.x + 40 + i * (r.w - 80) / 3
        pygame.draw.rect(surf, mix(RUG, LAMP, 0.09),
                         (cx, r.y + 24, (r.w - 80) / 3 - 10, r.h - 96),
                         border_radius=10)
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.4),
                     (r.x, r.bottom - 54, r.w, 30), border_radius=10)
    # the far arm, which a cat can sit on because it is drawn behind them
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.11),
                     (r.right - 44, r.y + 56, 44, 116), border_radius=14)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.16),
                     (r.right - 42, r.y + 58, 40, 16), border_radius=8)


def _backroom(surf, state, t):
    """The room through the wall, drawn behind the cats in it."""
    x0 = BACK_X
    # the knocked-through opening: a reveal, a lintel, and the bricks
    arch = pygame.Rect(x0 - 26, 92, 54, CATS_FLOOR - 92)
    pygame.draw.rect(surf, shade(WOOD_LO, 0.62), arch)
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.35), (x0 - 30, 78, 62, 22),
                     border_radius=3)
    for i in range(9):
        hairline(surf, x0 - 24, 112 + i * 46, x0 + 24, WOOD_HI, 26)
    # the back room is a touch lighter than the front: it has the window
    glow(surf, (x0 + 180, 300), 420, mix(LAMP, CREAM, 0.25), 0.11)
    glow(surf, (x0 + 760, 420), 360, mix(LAMP, EMBER, 0.3), 0.09)

    _rug(surf, pygame.Rect(x0 + 520, 640, 420, 150), mix(RUG, EMBER, 0.18))

    # the bird window, with the sill the cat sits on
    win = pygame.Rect(x0 + 80, 180, 132, 136)
    _cat_window(surf, win, t, seed=9)
    _feeder(surf, x0 + 262, 236, t)

    # the climbing steps, going up the wall away from the opening
    for sx, sy in ((2066, 468), (2182, 386), (2298, 302)):
        sh = pygame.Rect(sx - 52, sy, 104, 15)
        pygame.draw.rect(surf, WOOD_HI, sh, border_radius=3)
        pygame.draw.rect(surf, shade(WOOD, 0.74),
                         (sh.x, sh.bottom - 5, sh.w, 5))
        pygame.draw.rect(surf, mix(RUG, WOOD, 0.4),
                         (sh.x + 10, sh.y - 5, sh.w - 20, 6),
                         border_radius=2)
        for bx in (sh.x + 12, sh.right - 16):
            pygame.draw.line(surf, shade(WOOD, 0.6), (bx, sh.bottom),
                             (bx, sh.bottom + 16), 3)

    # the hammock, under the middle step
    _hammock(surf, 2462, 470)

    # the tall post: sisal all the way up, with a saucer on top
    post = pygame.Rect(2596 - 17, 556, 34, CAT_WALK_Y - 556 + 14)
    pygame.draw.rect(surf, mix(WOOD, PAPER, 0.28), post, border_radius=4)
    for i in range(int(post.h / 7)):
        hairline(surf, post.x, post.y + i * 7, post.right,
                 shade(WOOD, 0.72), 40)
    pygame.draw.ellipse(surf, mix(RUG, WOOD, 0.3),
                        (post.centerx - 46, post.y - 16, 92, 28))

    # the sofa
    _sofa_back(surf, pygame.Rect(2628, 470, 264, 200))

    # the second water bowl
    bowl = pygame.Rect(2930 - 26, CAT_WALK_Y - 14, 52, 20)
    pygame.draw.ellipse(surf, shade(TEA, 0.7), bowl)
    pygame.draw.ellipse(surf, (74, 104, 140), bowl.inflate(-10, -7))

    # the spring, which is the cheapest toy in the flat and the best
    for i in range(6):
        yy = CAT_WALK_Y - 4 - i * 7
        pygame.draw.ellipse(surf, mix(EMBER, LAMP, 0.25 + i * 0.07),
                            (2246 - 16 + (i % 2) * 5, yy, 32, 11), 3)

    # the tunnel, back half - the front of it goes on after the cats
    tun = pygame.Rect(2320, CAT_WALK_Y - 66, 230, 76)
    pygame.draw.rect(surf, mix((96, 104, 112), LAMP, 0.18), tun,
                     border_radius=30)
    pygame.draw.rect(surf, mix((120, 128, 134), LAMP, 0.2),
                     (tun.x, tun.y, tun.w, 16), border_radius=8)
    for sx in (tun.x + 14, tun.right - 14):
        pygame.draw.ellipse(surf, shade(INK, 1.5),
                            (sx - 26, tun.y + 6, 52, 64))


def _backroom_front(surf):
    """The near wall of the tunnel and the near arm of the sofa, drawn
    after the cats so they are inside them rather than behind them."""
    tun = pygame.Rect(2320, CAT_WALK_Y - 66, 230, 76)
    body = pygame.Rect(tun.x + 44, tun.y + 20, tun.w - 88, tun.h - 20)
    pygame.draw.rect(surf, mix((96, 104, 112), LAMP, 0.16), body,
                     border_radius=18)
    pygame.draw.rect(surf, mix((120, 128, 134), LAMP, 0.2),
                     (body.x, body.y, body.w, 12), border_radius=6)
    for i in range(3):
        hx = body.x + 22 + i * (body.w - 44) / 2
        pygame.draw.arc(surf, mix((136, 144, 150), LAMP, 0.22),
                        (hx - 15, body.y - 2, 30, body.h * 2), 4.0, 5.42, 6)
    arm = pygame.Rect(2628, 470, 264, 200)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.11),
                     (arm.x, arm.y + 56, 44, 116), border_radius=14)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.04),
                     (arm.x + 44, arm.bottom - 48, arm.w - 88, 30),
                     border_radius=8)

def _plant(surf, x, y, h, col, seed=0):
    """A pot with something green coming out of it."""
    rng = random.Random(seed)
    pot = pygame.Rect(x - h * 0.22, y - h * 0.26, h * 0.44, h * 0.26)
    for i in range(9):
        a = -2.6 + i * 0.36 + rng.uniform(-0.12, 0.12)
        ln = h * rng.uniform(0.45, 0.80)
        tip = (pot.centerx + math.cos(a) * ln * 0.7,
               pot.y - abs(math.sin(a)) * ln)
        pygame.draw.line(surf, mix(col, INK, 0.1 + 0.2 * (i % 3)),
                         (pot.centerx, pot.y), tip, 3)
        pygame.draw.circle(surf, col, (round(tip[0]), round(tip[1])), 5)
    pygame.draw.rect(surf, mix(EMBER, WOOD, 0.35), pot, border_radius=3)
    pygame.draw.rect(surf, mix(EMBER, LAMP, 0.2),
                     (pot.x, pot.y, pot.w, 7), border_radius=2)


def _garden(surf, state, t):
    """Glass on three sides, flagstones, and far too many plants."""
    x0 = wing_x(1)
    pygame.draw.rect(surf, mix(DEEP, (46, 56, 58), 0.6),
                     (x0, 0, 900, CATS_FLOOR))
    # the glass roof and wall, with the night behind it
    for i in range(7):
        gx = x0 + 40 + i * 120
        pane = pygame.Rect(gx, 90, 104, CATS_FLOOR - 170)
        pygame.draw.rect(surf, (20, 26, 32), pane)
        sh = pygame.Surface(pane.size, pygame.SRCALPHA)
        pygame.draw.polygon(sh, (*mix(CREAM, LAMP, 0.4), 16),
                            [(0, pane.h), (pane.w * 0.7, 0),
                             (pane.w, 0), (pane.w * 0.3, pane.h)])
        surf.blit(sh, pane.topleft)
        pygame.draw.rect(surf, mix(WOOD, TEA, 0.3), pane, width=4)
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.3), (x0, 74, 900, 20))
    glow(surf, (x0 + 450, 300), 520, mix(LAMP, CREAM, 0.2), 0.09)

    # flagstones, which hold the heat until ten at night
    pygame.draw.rect(surf, mix(WOOD_LO, TEA, 0.18),
                     (x0, CATS_FLOOR, 900, H - CATS_FLOOR))
    rng = random.Random(21)
    for row in range(5):
        for col in range(8):
            fx = x0 + 10 + col * 112 + (56 if row % 2 else 0)
            fy = CATS_FLOOR + 8 + row * 42
            if fy < H:
                pygame.draw.rect(surf, mix(WOOD_LO, CREAM,
                                           0.10 + rng.random() * 0.07),
                                 (fx, fy, 104, 36), border_radius=4)

    # the trellis, up the near wall
    for i in range(9):
        pygame.draw.line(surf, mix(WOOD, RUG, 0.4),
                         (x0 + 150 + i * 14, 250), (x0 + 220 + i * 14, 560), 3)
        pygame.draw.line(surf, mix(WOOD, RUG, 0.4),
                         (x0 + 220 - i * 14, 250), (x0 + 150 - i * 14, 560), 3)
    pygame.draw.rect(surf, WOOD_HI, (x0 + 76, 436, 120, 12),
                     border_radius=2)   # the plant shelf
    pygame.draw.rect(surf, WOOD_HI, (x0 + 330, 368, 110, 12),
                     border_radius=2)   # the glass ledge

    _plant(surf, x0 + 52, 632, 150, (104, 148, 96), 1)
    _plant(surf, x0 + 302, 664, 120, (122, 160, 104), 2)
    _plant(surf, x0 + 136, 436, 96, (96, 142, 102), 3)
    _plant(surf, x0 + 240, 304, 86, (112, 152, 98), 4)

    # the wicker chair, the cushion and the watering can
    ch = pygame.Rect(x0 + 426, 560, 150, 110)
    pygame.draw.rect(surf, mix(WOOD, PAPER, 0.3), ch, border_radius=12)
    for i in range(7):
        hairline(surf, ch.x + 6, ch.y + 10 + i * 13, ch.right - 6,
                 shade(WOOD, 0.7), 40)
    pygame.draw.ellipse(surf, mix(RUG, LAMP, 0.1),
                        (x0 + 556, 636, 120, 44))
    can = pygame.Rect(x0 + 736, 692, 44, 34)
    pygame.draw.rect(surf, mix(TEA, CREAM, 0.25), can, border_radius=4)
    pygame.draw.line(surf, mix(TEA, CREAM, 0.25), (can.right, can.y + 8),
                     (can.right + 22, can.bottom), 5)
    # the post by the step
    gp = pygame.Rect(x0 + 28, 556, 30, CAT_WALK_Y - 556 + 14)
    pygame.draw.rect(surf, mix(WOOD, PAPER, 0.26), gp, border_radius=3)
    for i in range(int(gp.h / 7)):
        hairline(surf, gp.x, gp.y + i * 7, gp.right, shade(WOOD, 0.72), 40)
    pygame.draw.ellipse(surf, mix(RUG, WOOD, 0.3),
                        (gp.centerx - 40, gp.y - 14, 80, 26))

    # the door that is never quite shut
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.2), (x0 + 820, 230, 70, 326))
    pygame.draw.rect(surf, shade(WOOD, 0.7), (x0 + 820, 230, 70, 326),
                     width=3)
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.3), (x0 + 756, 736, 110, 22),
                     border_radius=4)


def _loft(surf, state, t):
    """A ladder, two skylights and eighty years of other people's boxes."""
    x0 = wing_x(2)
    pygame.draw.rect(surf, mix(INK, WOOD, 0.22), (x0, 0, 900, CATS_FLOOR))
    # the roof, sloping in from both sides
    pygame.draw.polygon(surf, shade(WOOD_LO, 0.74),
                        [(x0, 0), (x0 + 240, 0), (x0, 330)])
    pygame.draw.polygon(surf, shade(WOOD_LO, 0.74),
                        [(x0 + 900, 0), (x0 + 660, 0), (x0 + 900, 330)])
    for bx, by, bw in ((x0 + 60, 312, 240), (x0 + 178, 248, 240),
                       (x0 + 298, 312, 240)):
        pygame.draw.rect(surf, mix(WOOD, RUG, 0.18), (bx, by, bw, 16),
                         border_radius=2)
        pygame.draw.rect(surf, shade(WOOD, 0.72), (bx, by + 11, bw, 5))
    # two skylights, and the only light in here
    for sx in (x0 + 330, x0 + 610):
        sk = pygame.Rect(sx, 110, 150, 110)
        pygame.draw.rect(surf, (22, 28, 38), sk)
        rng = random.Random(sx)
        for i in range(10):
            pygame.draw.circle(surf, mix(CREAM, INK, 0.3),
                               (sk.x + rng.randrange(8, sk.w - 8),
                                sk.y + rng.randrange(8, sk.h - 8)), 1)
        pygame.draw.rect(surf, mix(WOOD, TEA, 0.3), sk, width=5)
        glow(surf, (sk.centerx, sk.bottom + 120), 300,
             mix(LAMP, CREAM, 0.3), 0.10)
    pygame.draw.rect(surf, shade(WOOD_LO, 0.9),
                     (x0, CATS_FLOOR, 900, H - CATS_FLOOR))
    for i in range(9):
        hairline(surf, x0, CATS_FLOOR + 12 + i * 26, x0 + 900, WOOD_HI, 24)

    # the hatch and the top of the ladder
    pygame.draw.rect(surf, shade(INK, 1.4), (x0 + 110, CAT_WALK_Y + 4, 110,
                                             H - CAT_WALK_Y - 4))
    for i in range(3):
        pygame.draw.rect(surf, mix(WOOD, PAPER, 0.2),
                         (x0 + 116, CAT_WALK_Y + 10 + i * 16, 98, 7),
                         border_radius=2)
    # the water tank, the flue and a stack of boxes
    pygame.draw.rect(surf, mix(TEA, WOOD, 0.4), (x0 + 240, 486, 120, 74),
                     border_radius=5)
    pygame.draw.rect(surf, shade(TEA, 0.7), (x0 + 240, 486, 120, 74),
                     width=3, border_radius=5)
    pygame.draw.rect(surf, mix(WOOD, INK, 0.3), (x0 + 374, 400, 34, 260))
    rng = random.Random(9)
    for bx, by, bw, bh in ((x0 + 470, 576, 130, 92), (x0 + 486, 500, 100, 76),
                           (x0 + 580, 622, 120, 86)):
        face = mix(WOOD, PAPER, 0.16)
        pygame.draw.rect(surf, face, (bx, by, bw, bh), border_radius=3)
        pygame.draw.rect(surf, shade(face, 0.74), (bx, by, bw, bh), width=2,
                         border_radius=3)
        tape = pygame.Rect(bx + 8, by + bh // 2 - 6, bw - 16, 12)
        pygame.draw.rect(surf, mix(face, LAMP, 0.22), tape, border_radius=2)
    # the eiderdown, and the roof post
    pygame.draw.ellipse(surf, mix(RUG, LAMP, 0.08), (x0 + 636, 614, 150, 56))
    pygame.draw.rect(surf, mix(WOOD, PAPER, 0.24),
                     (x0 + 826, 556, 30, CAT_WALK_Y - 556 + 14),
                     border_radius=3)


def _sanctuary(surf, state, t):
    """The barn at the end of the lane, with a stove in it."""
    x0 = wing_x(3)
    pygame.draw.rect(surf, mix(INK, WOOD, 0.3), (x0, 0, 1200, CATS_FLOOR))
    # stone, up to the eaves
    rng = random.Random(33)
    for row in range(11):
        for col in range(14):
            sx = x0 + 8 + col * 86 + (43 if row % 2 else 0)
            sy = 40 + row * 46
            if sy < CATS_FLOOR - 20:
                pygame.draw.rect(surf, mix(shade(WOOD_LO, 0.62), CREAM,
                                           0.02 + rng.random() * 0.045),
                                 (sx, sy, 80, 40), border_radius=5)
    # the roof trusses
    for i in range(4):
        tx = x0 + 150 + i * 300
        pygame.draw.polygon(surf, mix(WOOD, RUG, 0.12),
                            [(tx - 150, 304), (tx, 146), (tx + 150, 304),
                             (tx + 130, 304), (tx, 176), (tx - 130, 304)])
        pygame.draw.line(surf, shade(WOOD, 0.74), (tx, 176), (tx, 300), 7)
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.18), (x0, 296, 1200, 18))
    pygame.draw.rect(surf, shade(WOOD, 0.66), (x0, 310, 1200, 5))
    glow(surf, (x0 + 280, 600), 420, mix(LAMP, EMBER, 0.45), 0.16)
    glow(surf, (x0 + 820, 420), 420, mix(LAMP, CREAM, 0.25), 0.09)

    pygame.draw.rect(surf, shade(WOOD_LO, 0.84),
                     (x0, CATS_FLOOR, 1200, H - CATS_FLOOR))
    for i in range(9):
        hairline(surf, x0, CATS_FLOOR + 12 + i * 26, x0 + 1200, WOOD_HI, 20)

    # hay, stacked
    for hx, hy, hw, hh in ((x0 + 40, 636, 140, 92), (x0 + 120, 564, 130, 84)):
        pygame.draw.rect(surf, mix((176, 150, 88), WOOD, 0.25),
                         (hx, hy, hw, hh), border_radius=4)
        for i in range(6):
            hairline(surf, hx + 6, hy + 10 + i * 13, hx + hw - 6,
                     mix((214, 190, 120), LAMP, 0.2), 34)
        pygame.draw.rect(surf, shade(WOOD, 0.7), (hx, hy + hh // 2 - 4, hw, 8))

    # the stove, which is the warmest thing in the game
    st_r = pygame.Rect(x0 + 240, 584, 104, 144)
    pygame.draw.rect(surf, shade(INK, 1.5), st_r, border_radius=6)
    pygame.draw.rect(surf, shade(TEA, 0.5), st_r, width=3, border_radius=6)
    door = pygame.Rect(st_r.x + 18, st_r.y + 40, 68, 60)
    pygame.draw.rect(surf, mix(EMBER, LAMP, 0.6), door, border_radius=4)
    glow(surf, door.center, 230, mix(EMBER, LAMP, 0.55), 0.42)
    pygame.draw.rect(surf, mix(LAMP, CREAM, 0.3), door, width=2,
                     border_radius=4)
    pygame.draw.rect(surf, shade(INK, 1.6), (st_r.centerx - 11, 300, 22, 300))

    # the row of beds
    for i in range(4):
        bx = x0 + 330 + i * 90
        pygame.draw.ellipse(surf, mix(RUG, WOOD, 0.3), (bx, 648, 84, 46))
        pygame.draw.ellipse(surf, mix(RUG, LAMP, 0.1), (bx + 8, 654, 68, 34))

    # the hay loft and the rafters
    pygame.draw.rect(surf, WOOD_HI, (x0 + 690, 436, 180, 14),
                     border_radius=2)
    pygame.draw.rect(surf, shade(WOOD, 0.7), (x0 + 690, 446, 180, 6))
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.2), (x0 + 760, 348, 220, 14),
                     border_radius=2)
    # the keeper's chair and the barn post
    ch = pygame.Rect(x0 + 770, 596, 140, 110)
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.3), ch, border_radius=10)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.06),
                     (ch.x + 12, ch.y + 12, ch.w - 24, ch.h - 50),
                     border_radius=8)
    pygame.draw.rect(surf, mix(WOOD, PAPER, 0.22),
                     (x0 + 926, 560, 32, CAT_WALK_Y - 560 + 14),
                     border_radius=3)

    # the post by the beds
    sp = pygame.Rect(x0 + 696, 556, 32, CAT_WALK_Y - 556 + 14)
    pygame.draw.rect(surf, mix(WOOD, PAPER, 0.22), sp, border_radius=3)
    for i in range(int(sp.h / 7)):
        hairline(surf, sp.x, sp.y + i * 7, sp.right, shade(WOOD, 0.7), 40)
    pygame.draw.ellipse(surf, mix(RUG, WOOD, 0.28),
                        (sp.centerx - 42, sp.y - 14, 84, 26))

    # the door to the run, standing open, and the night outside
    door = pygame.Rect(x0 + 1000, 300, 180, 256)
    pygame.draw.rect(surf, (16, 20, 28), door)
    rngs = random.Random(5)
    for i in range(16):
        pygame.draw.circle(surf, mix(CREAM, INK, 0.35),
                           (door.x + rngs.randrange(8, door.w - 8),
                            door.y + rngs.randrange(8, door.h - 8)), 1)
    pygame.draw.rect(surf, shade(WOOD, 0.6), door, width=6)
    for i in range(7):
        pygame.draw.line(surf, mix(TEA, WOOD, 0.4),
                         (door.x + 14 + i * 24, door.y + 6),
                         (door.x + 14 + i * 24, door.bottom - 6), 2)
    text(surf, "THE RUN", 13, (door.centerx, door.bottom + 16), TEA,
         center=True, kind="mono")

def _catroom_front(surf, state, t):
    """The parts of the room that are in FRONT of the cats.

    Drawn after them, which is the whole difference between a cat in a
    box and a cat standing against a picture of a box. The same goes for
    the basket and the near arm of the chair.
    """
    bask = pygame.Rect(176, 648, 196, 84)
    pygame.draw.arc(surf, mix(WOOD_HI, PAPER, 0.3),
                    (bask.x, bask.y + 2, bask.w, bask.h - 2), 3.34, 6.08, 15)
    for i in range(12):
        x = bask.x + 14 + i * 15
        f = (x - bask.centerx) / (bask.w / 2)
        y = bask.centery + math.sqrt(max(0.0, 1 - f * f)) * (bask.h / 2) - 7
        pygame.draw.line(surf, shade(WOOD, 0.85), (x, y - 6), (x + 5, y + 6), 2)

    box = pygame.Rect(1668, 440, 160, 116)
    front = pygame.Rect(box.x, box.y + 54, box.w, box.h - 54)
    pygame.draw.rect(surf, (150, 116, 80), front, border_radius=3)
    pygame.draw.rect(surf, shade((150, 116, 80), 0.74), front, width=2,
                     border_radius=3)
    pygame.draw.line(surf, shade((150, 116, 80), 0.86),
                     (front.x + 16, front.centery),
                     (front.right - 16, front.centery), 2)

    ch = pygame.Rect(1430, 404, 300, 200)
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.22), (ch.x, ch.y + 64, 46, 110),
                     border_radius=14)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.06),
                     (ch.x + 46, ch.bottom - 54, ch.w - 92, 34),
                     border_radius=8)
    if state.wings >= 1:
        _backroom_front(surf)


def _catroom(surf, state, t):
    """The whole room, drawn at its full width; the camera takes a window
    onto it. Everything is laid out against ROOM_SPOTS, so a cat asleep
    on the armchair is asleep on the armchair that is drawn here.

    It is drawn at one of two widths: the room on its own, or the room
    with the wall at the far end taken out.
    """
    wide = surf.get_width()
    surf.fill(INK)
    for y in range(0, CATS_FLOOR, 4):
        f = y / CATS_FLOOR
        pygame.draw.rect(surf, mix((28, 21, 20), (46, 34, 30), f ** 0.7),
                         (0, y, wide, 4))
    for x in range(0, wide, 52):
        s = pygame.Surface((2, CATS_FLOOR), pygame.SRCALPHA)
        s.fill((*WOOD_HI, 16))
        surf.blit(s, (x, 0))
    pygame.draw.rect(surf, shade(WOOD_LO, 0.78), (0, CATS_FLOOR, wide,
                                                  H - CATS_FLOOR))
    for i in range(8):
        y = CATS_FLOOR + 12 + i * 30
        if y < H:
            hairline(surf, 0, y, wide, WOOD_HI, 30)
    pygame.draw.rect(surf, shade(WOOD_HI, 0.55), (0, CATS_FLOOR - 10,
                                                  wide, 10))
    for i, draw in enumerate((_backroom, _garden, _loft, _sanctuary)):
        if state.wings > i and in_view(wing_x(i),
                                       wing_x(i) + WINGS[i].wide):
            draw(surf, state, t)
    _rug(surf, pygame.Rect(120, 626, 420, 150), mix(RUG, WOOD, 0.3))
    _rug(surf, pygame.Rect(760, 640, 500, 170), mix(RUG, EMBER, 0.12))
    _rug(surf, pygame.Rect(1560, 636, 420, 150), mix(RUG, WOOD, 0.22))
    if "skylight" in state.things:
        # a hole in the roof, and the square of sun it drops on the floor
        sq = [(1040, 0), (1300, 0), (1420, CATS_FLOOR + 40),
              (1080, CATS_FLOOR + 40)]
        beam = pygame.Surface((CATS_W, H), pygame.SRCALPHA)
        pygame.draw.polygon(beam, (*LAMP, 22), sq)
        surf.blit(beam, (0, 0))
        glow(surf, (1250, CATS_FLOOR + 120), 320, mix(LAMP, CREAM, 0.3),
             0.16)

    # a string of warm bulbs the whole length of the room
    lastx = lasty = None
    for i in range(23):
        f = i / 22
        x = 40 + f * (CATS_W - 80)
        y = 54 + math.sin(f * math.pi * 2.4) * 30
        if lastx is not None:
            pygame.draw.line(surf, shade(WOOD, 1.1), (lastx, lasty), (x, y), 2)
        lastx, lasty = x, y
        tw = 0.72 + 0.28 * math.sin(t * 1.6 + i * 1.1)
        glow(surf, (x, y + 8), 26, LAMP, 0.34 * tw)
        pygame.draw.circle(surf, mix(LAMP, CREAM, 0.3), (int(x), int(y + 8)), 4)

    _cat_window(surf, pygame.Rect(140, 150, 240, 190), t)

    for sx, sy, sw in ((414, 358, 176), (556, 256, 168)):
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
    for i in range(int(post.h // 9)):
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
    sway = math.sin(t * 1.1) * 26
    pygame.draw.line(surf, shade(TEA, 0.7), (plat2.x + 20, plat2.bottom),
                     (plat2.x + 20 + sway, plat2.bottom + 86), 2)
    pygame.draw.circle(surf, mix(EMBER, PAPER, 0.3),
                       (int(plat2.x + 20 + sway), int(plat2.bottom + 92)), 11)

    # the blanket chest
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

    # the basket, the bowls, and the ball
    bask = pygame.Rect(176, 648, 196, 84)
    pygame.draw.ellipse(surf, mix(WOOD_HI, PAPER, 0.3), bask)
    pygame.draw.ellipse(surf, mix(WOOD, PAPER, 0.18),
                        bask.inflate(-24, -30).move(0, -6))
    for i in range(12):
        x = bask.x + 10 + i * 15
        pygame.draw.line(surf, shade(WOOD, 0.9), (x, bask.y + 24),
                         (x + 6, bask.bottom - 10), 2)
    mat = pygame.Rect(512, 700, 200, 34)
    if "bowlmat" in state.things:       # wipe-clean, slightly too large
        mat = pygame.Rect(484, 694, 258, 44)
        pygame.draw.rect(surf, mix(PAPER, RUG, 0.4), mat, border_radius=8)
        pygame.draw.rect(surf, mix(PAPER, WOOD, 0.3), mat.inflate(-10, -10),
                         width=2, border_radius=6)
    pygame.draw.rect(surf, mix(WOOD_LO, EMBER, 0.12), mat, border_radius=6)
    for bx, col in ((540, (166, 126, 96)), (622, (138, 150, 164))):
        pygame.draw.ellipse(surf, mix(col, LAMP, 0.1), (bx, 702, 58, 24))
        pygame.draw.ellipse(surf, shade(col, 0.6), (bx + 7, 706, 44, 14))
    if "fountain" in state.things:      # running water, endlessly
        f = pygame.Rect(726, 686, 54, 50)
        pygame.draw.rect(surf, mix(PAPER, (138, 150, 164), 0.5), f,
                         border_radius=6)
        pygame.draw.rect(surf, mix(PAPER, WOOD, 0.3), f, width=2,
                         border_radius=6)
        for i in range(4):
            yy = f.y + 10 + ((t * 36 + i * 9) % 26)
            pygame.draw.line(surf, (142, 178, 206), (f.centerx - 5, yy),
                             (f.centerx + 5, yy + 3), 2)
        pygame.draw.ellipse(surf, (120, 156, 188),
                            (f.x + 6, f.bottom - 14, f.w - 12, 10))
    if "heatbed" in state.things:       # warmer than you are
        bed = pygame.Rect(1086, 672, 150, 62)
        pygame.draw.ellipse(surf, mix(RUG, EMBER, 0.3), bed)
        pygame.draw.ellipse(surf, mix(RUG, LAMP, 0.18), bed.inflate(-26, -22))
        glow(surf, bed.center, 110, mix(LAMP, EMBER, 0.55),
             0.12 + 0.02 * math.sin(t * 1.3))
    jig = math.sin(t * 2.3) * 3
    pygame.draw.circle(surf, mix(GOOD, PAPER, 0.3), (int(452 + jig), 726), 11)
    pygame.draw.circle(surf, shade(mix(GOOD, PAPER, 0.3), 0.7),
                       (int(452 + jig), 726), 11, 2)

    # ---- the far half ----------------------------------------------------
    sill2 = _cat_window(surf, pygame.Rect(1212, 140, 170, 180), t, seed=9)
    if "perch" in state.things:         # a box of a balcony on the window
        cat_io = pygame.Rect(1192, 300, 210, 96)
        pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.1), cat_io,
                         border_radius=4)
        pygame.draw.rect(surf, shade(WOOD, 0.8), cat_io, width=3,
                         border_radius=4)
        for i in range(7):
            x = cat_io.x + 12 + i * 30
            pygame.draw.line(surf, shade(WOOD, 0.9), (x, cat_io.y + 4),
                             (x, cat_io.bottom - 4), 2)
        pygame.draw.rect(surf, mix(RUG, LAMP, 0.1),
                         (cat_io.x + 8, cat_io.bottom - 18, cat_io.w - 16,
                          12), border_radius=4)
    rad = pygame.Rect(1222, 436, 150, 84)
    pygame.draw.rect(surf, mix(PAPER, WOOD, 0.55), rad, border_radius=4)
    for i in range(7):
        pygame.draw.rect(surf, mix(PAPER, WOOD, 0.42),
                         (rad.x + 7 + i * 20, rad.y + 5, 12, rad.h - 10),
                         border_radius=3)
    pygame.draw.rect(surf, shade(WOOD, 0.9), rad, width=2, border_radius=4)
    glow(surf, (rad.centerx, rad.centery), 120, mix(LAMP, EMBER, 0.6), 0.10)
    pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.2),
                     (rad.x - 10, rad.y - 14, rad.w + 20, 14),
                     border_radius=3)

    # the armchair, which is the best seat in the flat
    ch = pygame.Rect(1430, 404, 300, 200)
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.25), (ch.x + 10, ch.y + 60,
                                                  ch.w - 20, ch.h - 40),
                     border_radius=12)
    pygame.draw.rect(surf, mix(RUG, EMBER, 0.14),
                     (ch.x + 26, ch.y, ch.w - 52, 120), border_radius=16)
    for sx in (ch.x, ch.right - 46):      # the arms
        pygame.draw.rect(surf, mix(RUG, WOOD, 0.18), (sx, ch.y + 64, 46, 110),
                         border_radius=14)
    pygame.draw.rect(surf, mix(RUG, LAMP, 0.10),
                     (ch.x + 50, ch.y + 96, ch.w - 100, 54), border_radius=10)
    for lx in (ch.x + 16, ch.right - 28):
        pygame.draw.rect(surf, shade(WOOD, 0.8), (lx, ch.bottom - 16, 12, 22))
    thr = pygame.Rect(ch.x + 150, ch.y + 40, 120, 90)
    pygame.draw.rect(surf, mix((132, 108, 126), LAMP, 0.1), thr,
                     border_radius=6)

    # a box fort, and a feather on the floor in front of it
    box = pygame.Rect(1668, 440, 160, 116)
    pygame.draw.rect(surf, (150, 116, 80), box, border_radius=3)
    pygame.draw.rect(surf, shade((150, 116, 80), 0.74), box, width=2,
                     border_radius=3)
    hole = pygame.Rect(box.x + 42, box.y + 30, 76, 86)
    pygame.draw.ellipse(surf, shade(INK, 1.5), hole)
    pygame.draw.polygon(surf, (168, 132, 94), [
        (box.x, box.y + 6), (box.right, box.y + 6),
        (box.right - 16, box.y - 16), (box.x + 16, box.y - 16)])
    fx = 1648 + math.sin(t * 1.7) * 5
    pygame.draw.line(surf, mix(TEA, CREAM, 0.2), (fx, 736), (fx + 30, 700), 2)
    for i in range(5):
        pygame.draw.line(surf, mix(EMBER, CREAM, 0.3),
                         (fx + 30, 700), (fx + 38 + i * 3, 684 + i * 6), 2)

    # the second scratching post, and a shelf over it
    pbase = pygame.Rect(TREE2_X - 60, CATS_FLOOR - 18, 126, 20)
    pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.2), pbase, border_radius=3)
    ppost = pygame.Rect(TREE2_X - 18, 300, 36, CATS_FLOOR - 300)
    pygame.draw.rect(surf, mix(PAPER, WOOD, 0.5), ppost)
    for i in range(int(ppost.h // 9)):
        y = ppost.y + 5 + i * 9
        pygame.draw.line(surf, mix(PAPER, WOOD, 0.66), (ppost.x, y),
                         (ppost.right, y - 3), 3)
    pygame.draw.circle(surf, mix(RUG, EMBER, 0.2), (TREE2_X, 294), 14)
    shelf = pygame.Rect(1790, 232, 180, 14)
    pygame.draw.rect(surf, WOOD_HI, shelf, border_radius=2)
    pygame.draw.rect(surf, shade(WOOD, 0.75), (shelf.x, shelf.bottom - 4,
                                               shelf.w, 4))
    rng = random.Random(6)
    bx = shelf.x + 10
    while bx < shelf.x + 86:
        hgt = rng.randrange(34, 54)
        wid = rng.randrange(8, 14)
        pygame.draw.rect(surf, mix(rng.choice((RUG, WOOD_HI, (86, 74, 96))),
                                   LAMP, 0.10),
                         (bx, shelf.y - hgt, wid, hgt), border_radius=2)
        bx += wid + 2

    edge = pygame.Surface((160, H), pygame.SRCALPHA)
    for x in range(160):
        a = int(24 * (1 - x / 159) ** 2)
        pygame.draw.line(edge, (*LAMP, a), (x, 0), (x, H))
    surf.blit(edge, (0, 0))


# Where a cat may be in the two rooms that are NOT the cat room, best
# spot first: the top of the cat tree is a better
# address than the floor by the bowls, and the cats you have taken
# furthest get first refusal.
SPOTS = (
    ("study", 1022, 452, "sit", 150),     # the desk, beside the binder
    ("hall", 946, 410, "sit", 116),       # the console table by the door
    ("study", 642, 174, "sit", 96),       # the shelf, at the clear end
    ("study", 958, 274, "curl", 124),     # the study windowsill
    ("hall", 290, 640, "curl", 132),      # down inside the box
    ("study", 676, 726, "curl", 172),     # the middle of the rug
    ("study", 414, 606, "sit", 124),      # the near edge of the rug
)
ROOM_CAP = 12                 # how many cats live in the cat room itself
BIG_CAP = ROOM_CAP + sum(w.cap for w in WINGS)   # ... with every wall down


def room_cap(state):
    """How many of them the cat room holds - which is the whole point of
    knocking the wall through, and the reason this is a question and not
    a constant any more."""
    return ROOM_CAP + sum(w.cap for w in WINGS[:state.wings])


def room_spot_count(state):
    """How much of ROOM_SPOTS is reachable. The back room's places are
    appended, so this is a count rather than a filter."""
    return ROOM_BASE + sum(w.spots for w in WINGS[:state.wings])


def cats_wide(state):
    return CATS_W + sum(w.wide for w in WINGS[:state.wings])


def area_wide(area, state):
    return cats_wide(state) if area == "cats" else AREA_WIDE[area]


def room_cats(state):
    """The cats the flat shows, in the order they get the good spots."""
    got = [(c.level, BY_KEY[k].rarity, k) for k, c in state.cards.items()]
    got.sort(reverse=True)
    return [BY_KEY[k] for _, _, k in got[:room_cap(state) + len(SPOTS)]]


def cats_in(state, area):
    """(breed, spot) for every cat that lives in this room.

    The cat room is not in here: its residents move about and are owned
    by CatRoom. These are the ones further down the list, asleep on the
    furniture in the other two rooms.
    """
    if area == "cats":
        return []
    out = []
    for b, spot in zip(room_cats(state)[room_cap(state):], SPOTS):
        if spot[0] == area:
            out.append((b, spot))
    return out


def cat_look(state, b):
    """(level, coat, shiny) for a breed, as its card in the binder says.

    The rooms used to draw every cat in the colour the catalogue lists,
    so a shiny you had pulled was shiny on its card and ordinary on the
    windowsill. One lookup, used everywhere a cat is drawn outside a
    card, keeps the two in step.
    """
    card = state.cards.get(b.key)
    if card is None:
        return 1, 0, False
    return card.level, card.coat, card.shiny


def cat_level(state, b):
    return cat_look(state, b)[0]


def cat_rect(b, spot, look=(1, 0, False)):
    _, x, y, pose, hgt = spot
    if isinstance(look, int):
        look = (look, 0, False)
    lv, coat, shiny = look
    img = cat_surface(b, pose, hgt, level=lv, variant=coat, shiny=shiny)
    return img.get_rect(midbottom=(x, y))


def draw_cats(surf, state, area, t):
    for i, (b, spot) in enumerate(cats_in(state, area)):
        _, x, y, pose, hgt = spot
        blink = math.sin(t * 0.7 + i * 2.1) > 0.985
        lv, coat, shiny = cat_look(state, b)
        img = cat_surface(b, pose, hgt, blink, lv, coat, shiny)
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

    if "radcover" in state.things:      # a shelf over the hall radiator
        sh = pygame.Rect(112, 440, 224, 14)
        pygame.draw.rect(surf, mix(WOOD_HI, PAPER, 0.18), sh,
                         border_radius=3)
        pygame.draw.rect(surf, shade(WOOD, 0.8), (sh.x, sh.bottom - 4,
                                                  sh.w, 4))
        for bx in (sh.x + 16, sh.right - 22):
            pygame.draw.line(surf, shade(WOOD, 0.75), (bx, sh.bottom),
                             (bx, sh.bottom + 12), 3)
        glow(surf, (sh.centerx, sh.bottom + 40), 150,
             mix(LAMP, EMBER, 0.6), 0.09)
    _mat(surf, state.parcels, t)
    if state.stray:
        b = BY_KEY[state.stray]
        img = cat_surface(b, "sit", 140, False, 1)
        r = img.get_rect(midbottom=STRAY_AT)
        sh = pygame.Surface((r.w, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, r.w, 14))
        surf.blit(sh, (r.x, STRAY_AT[1] - 8))
        surf.blit(img, r)
        glow(surf, (r.centerx, r.centery), 150, mix(LAMP, CREAM, 0.3),
             0.09 + 0.03 * math.sin(t * 2.0))
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


def _binder(surf, t, hot=False, owned=0, total=None):
    # `total` used to default to 24, which was the number of breeds
    # on the day this was written. The spine then went on saying
    # 24 of 24 while the binder itself said 24 of 36.
    total = len(BREEDS) if total is None else total   # callers pass it
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
    if "rug" in state.things:
        _rug(surf, pygame.Rect(180, 580, 840, 200), mix(RUG, EMBER, 0.18))
        _rug(surf, pygame.Rect(300, 616, 600, 130), mix(RUG, WOOD, 0.3))
    if "gramo" in state.things:         # something slow, in the corner
        g = pygame.Rect(1066, 470, 96, 78)
        pygame.draw.rect(surf, mix(WOOD, RUG, 0.3), g, border_radius=4)
        pygame.draw.ellipse(surf, shade(INK, 1.6), (g.x + 14, g.y + 10,
                                                    68, 30))
        pygame.draw.circle(surf, mix(TEA, CREAM, 0.2),
                           (g.centerx, g.y + 25), 5)
        horn = [(g.centerx + 8, g.y + 8), (g.right + 30, g.y - 54),
                (g.right + 54, g.y - 30), (g.centerx + 26, g.y + 14)]
        pygame.draw.polygon(surf, mix(LAMP, TEA, 0.45), horn)
        pygame.draw.polygon(surf, shade(TEA, 0.6), horn, 2)
        for i in range(3):
            a = int(90 * (1 - ((t * 0.5 + i * 0.33) % 1.0)))
            yy = g.y - 60 - ((t * 26 + i * 22) % 70)
            text(surf, "~", 15, (g.right + 46 + i * 10, yy),
                 mix(LAMP, CREAM, 0.3), alpha=a, shadow=False)
    _lamp(surf, t)
    _laptop(surf, t, unread=len(state.orders))
    _binder(surf, t, owned=state.owned, total=len(state.book))
    _grass(surf, t)
    draw_cats(surf, state, "study", t)


# ---------------------------------------------------------------------------
# THE CAT ROOM
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# THE HALL ACROSS TOWN
# ---------------------------------------------------------------------------
CONV_FLOOR = 520
STALL_X = (212, 576, 940)         # where the three tables stand


# The people in the hall. Everything about one of them comes out of its
# seed, so the same person is the same person every frame and no two
# standing next to each other are the same shape. It is four hundred
# rounded rectangles either way; the difference is whether it reads as a
# crowd or as one man printed four hundred times.
SKINS = ((236, 198, 166), (214, 172, 138), (182, 138, 104),
         (146, 104, 76), (104, 74, 56), (72, 50, 40))
HAIRS = ((38, 32, 30), (70, 48, 34), (124, 86, 52), (176, 142, 92),
         (196, 198, 202), (142, 60, 44))


def _person(surf, x, y, h, col, t, seed, skin=0.55):
    """One of the four hundred people who want the same cards you do."""
    rng = random.Random(int(seed * 1000) & 0xFFFF)
    sway = math.sin(t * 1.1 + seed) * 2
    bob = math.sin(t * 1.7 + seed * 2) * 2
    build = rng.uniform(0.38, 0.56)          # how broad across the shoulders
    coat = rng.uniform(0.62, 0.86)           # and how far down the coat goes
    w = h * build
    hx = x + sway * 1.2
    hy = y - h * (coat + 0.10) + bob
    hr = max(2, round(h * rng.uniform(0.13, 0.17)))

    body = pygame.Rect(x - w / 2 + sway, y - h * coat + bob, w, h * coat)
    pygame.draw.rect(surf, col, body, border_radius=int(w * 0.34))
    if h >= 54 and rng.random() < 0.45:      # a coat that hangs open
        pygame.draw.line(surf, shade(col, 0.82), (body.centerx, body.y + 6),
                         (body.centerx, body.bottom - 4), 2)
    if h >= 54 and rng.random() < 0.3:       # somebody carrying a bag
        bag = pygame.Rect(body.right - 4, body.centery, h * 0.16, h * 0.20)
        pygame.draw.rect(surf, shade(col, 0.76), bag, border_radius=3)
        pygame.draw.line(surf, shade(col, 0.7), (body.centerx, body.y + 4),
                         (bag.centerx, bag.y), 2)

    tone = SKINS[rng.randrange(len(SKINS))] if skin > 0.3 else col
    face = mix(col, tone, clamp(skin, 0.0, 1.0))
    pygame.draw.circle(surf, face, (round(hx), round(hy)), hr)
    if h < 40:
        return                               # too far off to have a haircut

    hair = mix(col, HAIRS[rng.randrange(len(HAIRS))], 0.72)
    style = rng.randrange(5)
    if style == 0:                           # cropped
        pygame.draw.ellipse(surf, hair, (hx - hr, hy - hr * 1.12,
                                         hr * 2, hr * 1.25))
    elif style == 1:                         # long, down past the jaw
        pygame.draw.ellipse(surf, hair, (hx - hr * 1.12, hy - hr * 1.1,
                                         hr * 2.24, hr * 2.5))
        pygame.draw.circle(surf, face, (round(hx), round(hy + hr * 0.18)),
                           round(hr * 0.86))
    elif style == 2:                         # tied up
        pygame.draw.ellipse(surf, hair, (hx - hr, hy - hr * 1.1,
                                         hr * 2, hr * 1.2))
        pygame.draw.circle(surf, hair, (round(hx - hr * 0.1),
                                        round(hy - hr * 1.5)),
                           round(hr * 0.56))
    elif style == 3:                         # a woolly hat
        pygame.draw.ellipse(surf, mix(col, LAMP, 0.25),
                            (hx - hr * 1.1, hy - hr * 1.5,
                             hr * 2.2, hr * 1.7))
        pygame.draw.rect(surf, mix(col, CREAM, 0.3),
                         (hx - hr * 1.1, hy - hr * 0.5, hr * 2.2, hr * 0.42),
                         border_radius=2)
    elif style == 4:                         # a cap, peak forward
        pygame.draw.ellipse(surf, hair, (hx - hr, hy - hr * 1.1,
                                         hr * 2, hr * 1.1))
        pygame.draw.ellipse(surf, mix(col, INK, 0.2),
                            (hx - hr * 1.6, hy - hr * 0.86,
                             hr * 2.1, hr * 0.5))
    if h >= 70 and rng.random() < 0.22:      # and a few with a beard
        pygame.draw.ellipse(surf, hair, (hx - hr * 0.72, hy + hr * 0.1,
                                         hr * 1.44, hr * 1.2))


def _crowd(surf, t):
    rng = random.Random(17)
    rows = ((CONV_FLOOR + 36, 92, 0.42), (CONV_FLOOR + 96, 118, 0.62),
            (CONV_FLOOR + 170, 150, 0.85))
    for ry, hh, lit in rows:
        x = -40
        while x < W + 60:
            col = mix(rng.choice(((74, 66, 78), (86, 64, 58), (62, 72, 86),
                                  (92, 78, 56), (70, 60, 64))),
                      LAMP, 0.10 * lit)
            _person(surf, x, ry, hh * rng.uniform(0.9, 1.12), col, t,
                    rng.random() * 9)
            x += hh * rng.uniform(0.62, 0.95)


def _stall(surf, x, title, who, t, taken):
    """A trestle table with a cloth, a stack of boxes and a person behind."""
    top = pygame.Rect(x - 150, CONV_FLOOR - 6, 300, 18)
    cloth = pygame.Rect(top.x + 6, top.bottom - 2, top.w - 12, 96)
    _person(surf, x, CONV_FLOOR - 4, 148, mix(RUG, WOOD, 0.3), t, x * 0.01)
    pygame.draw.rect(surf, mix(RUG, EMBER, 0.18), cloth)
    for i in range(7):
        hairline(surf, cloth.x, cloth.y + 12 + i * 12, cloth.right,
                 mix(PAPER, RUG, 0.3), 26)
    pygame.draw.rect(surf, WOOD_HI, top, border_radius=3)
    pygame.draw.rect(surf, shade(WOOD, 0.8), (top.x, top.bottom - 5,
                                              top.w, 5))
    for i in range(3):
        bx = top.x + 22 + i * 78
        by = top.y - 30 - (i % 2) * 8
        pygame.draw.rect(surf, mix(WOOD, EMBER, 0.2) if not taken
                         else shade(WOOD, 0.7), (bx, by, 62, 32),
                         border_radius=3)
        pygame.draw.rect(surf, mix(LAMP, EMBER, 0.3) if not taken
                         else shade(TEA, 0.5), (bx + 8, by + 8, 46, 6),
                         border_radius=2)
    # the banner over the table
    ban = pygame.Rect(x - 168, 150, 336, 54)
    pygame.draw.rect(surf, mix(RUG, WOOD, 0.25), ban, border_radius=6)
    pygame.draw.rect(surf, mix(EMBER, LAMP, 0.3), ban, width=2,
                     border_radius=6)
    text(surf, title, 17, (ban.centerx, ban.y + 10), warm(CREAM, 0.2),
         center=True, kind="mono", max_w=ban.w - 24)
    text(surf, who, 12, (ban.centerx, ban.y + 32), MUTED, center=True,
         kind="mono", max_w=ban.w - 24)
    for sx in (ban.x + 30, ban.right - 30):
        pygame.draw.line(surf, shade(TEA, 0.6), (sx, 88), (sx, ban.y), 2)
    return pygame.Rect(top.x, top.y - 54, top.w, cloth.bottom - top.y + 54)


def _convention(surf, state, t):
    surf.fill(INK)
    for y in range(0, CONV_FLOOR, 4):
        f = y / CONV_FLOOR
        pygame.draw.rect(surf, mix((30, 26, 30), (52, 44, 44), f ** 0.7),
                         (0, y, W, 4))
    # strip lights, the one thing a hall like this has plenty of
    for i in range(5):
        x = 110 + i * 240
        pygame.draw.rect(surf, mix(WOOD, LAMP, 0.25), (x - 60, 44, 120, 10),
                         border_radius=4)
        glow(surf, (x, 60), 150, mix(LAMP, CREAM, 0.35), 0.16)
    pygame.draw.line(surf, shade(WOOD_LO, 1.2), (0, 88), (W, 88), 5)
    for x in range(0, W, 46):
        pygame.draw.line(surf, shade(WOOD_LO, 1.0), (x, 88), (x + 23, 104), 2)
        pygame.draw.line(surf, shade(WOOD_LO, 1.0), (x + 46, 88),
                         (x + 23, 104), 2)
    # the rest of the show, too far away to be worth walking to
    rng = random.Random(41)
    for far in (0, 1):
        by = 262 + far * 82
        bh = 58 + far * 26
        x = -30
        while x < W + 40:
            bw = rng.randint(90, 170)
            tone = 0.12 + 0.10 * far
            pygame.draw.rect(surf, mix(DEEP, WOOD, tone),
                             (x, by, bw - 12, bh), border_radius=3)
            pygame.draw.rect(surf, mix(DEEP, EMBER, tone * 0.8),
                             (x, by, bw - 12, 9), border_radius=3)
            glow(surf, (x + bw * 0.4, by + 6), int(bw * 0.5),
                 mix(LAMP, EMBER, 0.4), 0.05 + 0.03 * far)
            x += bw
        # and the backs of the heads in front of them
        hx = -20
        while hx < W + 30:
            _person(surf, hx, by + bh + 12, 30 + far * 14,
                    mix(DEEP, (70, 62, 66), 0.3 + 0.2 * far), t,
                    rng.random() * 9, skin=0.10 + 0.08 * far)
            hx += rng.uniform(17, 26) + far * 6
    pygame.draw.rect(surf, shade(WOOD_LO, 0.9), (0, CONV_FLOOR, W,
                                                 H - CONV_FLOOR))
    for i in range(9):
        hairline(surf, 0, CONV_FLOOR + 14 + i * 26, W, WOOD_HI, 22)

    haze = pygame.Surface((W, CONV_FLOOR - 150), pygame.SRCALPHA)
    for i in range(0, haze.get_height(), 3):
        a = int(46 * (1.0 - i / haze.get_height()) ** 1.4)
        pygame.draw.rect(haze, (*mix(WOOD, EMBER, 0.2), a), (0, i, W, 3))
    surf.blit(haze, (0, 150))

    for slot, which in enumerate(stalls_on(state.week)):
        key, title, who, pack_key, game, blurb = STALLS[which]
        _stall(surf, STALL_X[slot], title, who, t, key in state.conv_done)
    _crowd(surf, t)

    # the doors home, on the right
    pygame.draw.rect(surf, mix(WOOD, RUG, 0.3), (W - 70, 150, 70, 370))
    pygame.draw.rect(surf, shade(WOOD, 0.7), (W - 70, 150, 70, 370), width=3)
    text(surf, "WAY", 13, (W - 35, 300), TEA, center=True, kind="mono")
    text(surf, "OUT", 13, (W - 35, 318), TEA, center=True, kind="mono")


_AREA_DRAW = {"conv": _convention, "hall": _hall,
              "study": _study, "cats": _catroom}
_scratch = None
_wide = None


_VIEW = (-10 ** 6, 10 ** 6)     # the slice of a wide room on screen


def in_view(lo, hi):
    return hi > _VIEW[0] and lo < _VIEW[1]


def draw_area(surf, area, state, t, cam=0.0, room=None):
    """Draw a room into `surf`, taking the camera into account.

    A room no wider than the window is drawn straight onto it. The cat
    room is drawn once at full width onto a spare surface and then
    blitted through the window, which is also what keeps its hit areas
    honest: everything in there is in room coordinates until the moment
    it is shown.
    """
    wide = area_wide(area, state)
    if wide <= W:
        _AREA_DRAW[area](surf, state, t)
        return
    global _wide, _VIEW
    if _wide is None or _wide.get_width() != wide:
        _wide = pygame.Surface((wide, H))
    _VIEW = (cam - 60, cam + W + 60)
    old_clip = _wide.get_clip()
    _wide.set_clip(pygame.Rect(int(cam) - 60, 0, W + 120, H))
    _AREA_DRAW[area](_wide, state, t)
    if room is not None:
        room.draw(_wide, t)
    if area == "cats":
        _catroom_front(_wide, state, t)
    _wide.set_clip(old_clip)
    _VIEW = (-10 ** 6, 10 ** 6)
    surf.blit(_wide, (-int(cam), 0))


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
    "the cat room is wider than the window - keep walking",
    "every breed has its own temperament. click one and see",
    "the post lands in the hall - go and get it",
    "the post is not the only thing that comes to the door",
    "click a cat. any cat",
    "the laptop is the only way to get cards",
    "the specials page sells four things the ladder does not",
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
        self.scene = "intro" if not self.state.seen_intro else "room"
        self.beat = 0               # which of the four screens
        self.beat_t = 0.0
        self.area = self.state.area
        self.pan = 0.0              # 1 while a room slides past, else 0
        self.pan_from = None
        self.pan_dir = 1
        self.cam = 0.0              # how far along a wide room you are
        self.cam_to = 0.0
        self.room = CatRoom()       # the cat room runs its own simulation
        self.mini = None            # the minigame being played, if any
        self.news_for = None        # the series being announced, if any
        self.focus = None           # a cat you have clicked on
        self.focus_t = 0.0
        self.t = 0.0
        self.buttons = []
        self.toasts = []
        self.floats = []
        self.was_conv = self.state.convention()
        self.autosave = 0.0
        self.coin_timer = 0.0
        self.since_coin = 0.0
        # The balance the SCREEN shows, which is not the balance the game
        # holds. Two things make a counter hard to look at: it restreams
        # sixty times a second, and in a proportional face every digit
        # that changes shifts the ones beside it. So this one steps once
        # a second and is drawn in a monospace, and the number sits still
        # between steps instead of boiling.
        self.shown = self.state.money        # stepped, for the room
        self.shown_exact = self.state.money  # to the dollar, for the shop
        self.shown_t = 0.0
        self.hint = 0.0
        self.hint_i = 0
        self.full = False

        # the website
        self.tab = "catalogue"
        self.site = "meowrder"
        self.bay = "buy"            # which half of the resale site
        self.product = None
        self.qty = 1
        self.mode = 0
        self.seen_shop = False

        # opening a parcel
        self.open_pack_key = None
        self.open_qty = 1
        self.pulls = []
        self.flipped = 0
        self.pack_i = 0             # which pack of the parcel is open
        self.lid = 0.0
        self.cut = False
        self.deal = 0.0

        # the binder
        self.page = 0
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

    def can_enter(self, area):
        """The hall across town is only there on a Saturday."""
        return area != "conv" or self.state.convention()

    def go_area(self, area, quiet=False):
        """Walk to another room. The slide IS the walk: there is no figure
        to follow about, because the flat is yours and you are the one
        carrying the camera through it."""
        if area == self.area or area not in AREAS or self.scene != "room":
            return
        if not self.can_enter(area):
            self.toast("the hall is shut",
                       f"the convention is on {DAY_NAMES[CONVENTION_DAY]}s"
                       f" - {clock_str(until_convention(self.state.played))}"
                       f" to go", TEA, 6.0)
            return
        self.pan_dir = 1 if AREAS.index(area) > AREAS.index(self.area) else -1
        self.pan_from = self.area
        self.pan = 1.0
        self.area = area
        self.state.area = area
        # you come into a wide room from the side you walked in from
        span = area_wide(area, self.state) - W
        self.cam_to = span if (self.pan_dir < 0 and span > 0) else 0.0
        self.cam = self.cam_to
        if not quiet:
            self.beep("step")

    def walk(self, d):
        """One step. In a room wider than the window that means sliding
        the camera along it; only at the end of a room do you leave it."""
        span = area_wide(self.area, self.state) - W
        if span > 0:
            if d > 0 and self.cam_to < span - 1:
                self.cam_to = min(span, self.cam_to + W * 0.78)
                self.beep("step")
                return
            if d < 0 and self.cam_to > 1:
                self.cam_to = max(0, self.cam_to - W * 0.78)
                self.beep("step")
                return
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
            elif self.flipped < len(self.this_pack()):
                self.flip_all() if self.flipped else self.flip_next()
            else:
                self.next_pack()
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
        elif name == "stray":
            self.let_in()
        elif name == "stall":
            self.start_mini(val)
        elif name == "mini":
            self.mini_press(val)
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
        elif name == "thing":
            up = BY_UPGRADE[val]
            if self.state.buy_thing(up):
                self.beep("level")
                self.shown_exact = self.state.money
                self.toast(up.name + " is in",
                           f"every cat earns {up.gain * 100:.0f}% more",
                           GOOD, 9.0)
                self.save()
        elif name == "site":
            self.site = val
            self.product = None
            self.beep("page")
        elif name == "lot":
            self.buy_lot(val)
        elif name == "swap":
            self.do_swap(val)
        elif name == "bay":
            self.bay = val
            self.beep("page")
        elif name == "bid":
            self.place_bid(val)
        elif name == "news":
            if val == "skip":
                self.end_news()
            else:
                self.news_next()
        elif name == "intro":
            if val == "skip":
                self.end_intro()
            else:
                self.intro_next()
        elif name == "merch":
            self.buy_merch(val)
        elif name == "bigroom":
            self.take_the_room()
        elif name == "club":
            if self.state.join_club():
                self.shown_exact = self.state.money
                self.shown = self.state.money
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
        elif name == "nextpack":
            self.next_pack()
        elif name == "next":
            self.finish_open()
            self.start_open()
        elif name == "leave":
            self.leave_open()
        elif name == "page":
            self.page = int(val)
            self.pick = None
            self.beep("page")
        elif name == "pick":
            self.pick = None if self.pick == val else val
        elif name == "music":
            self.state.music = not self.state.music
            music(self.state.music)
        elif name == "sound":
            self.state.sound = not self.state.sound
        elif name == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    # -- the day out ----------------------------------------------------
    def start_mini(self, key):
        st = self.state
        st.conv_refresh()
        if st.conv_played(key) or not st.convention():
            return
        if key not in {STALLS[i][0] for i in stalls_on(st.week)}:
            return                      # that one is not out this week
        stall = next(x for x in STALLS if x[0] == key)
        self.mini = Mini(stall[4], key, random.Random(), st)
        self.beep("page")
        self.go("mini")

    def mini_press(self, what):
        """Every move in every one of the three games comes through here."""
        m = self.mini
        if m is None:
            return
        if what == "leave" or m.done:
            self.finish_mini()
            return
        if m.kind == "queue" and what == "stop":
            lo, hi = m.band_rect()
            if lo <= m.pos <= hi:
                m.won += 1
                self.beep("coin")
            else:
                m.lost = True
                self.beep("flip")
            m.stage += 1
            if m.lost or m.stage >= m.rounds:
                m.done = True
        elif m.kind == "fake" and isinstance(what, int):
            if what == m.real_index():
                m.won += 1
                self.beep("coin")
                m.stage += 1
                if m.stage >= m.rounds:
                    m.done = True
                else:
                    m.deal_fakes(random.Random(), self.state)
            elif m.spare:
                m.spare -= 1
                self.beep("page")
                m.deal_fakes(random.Random(), self.state)
            else:
                m.lost = True
                m.done = True
                self.beep("flip")
        elif m.kind == "auction" and what in ("raise", "pass"):
            if what == "pass":
                m.lost = True
                m.done = True
                self.beep("flip")
                return
            m.bid += AUCTION_STEP
            # the room thins out as the price climbs, and the chance of
            # somebody going again falls with it
            if random.random() < m.rival ** (1 + m.stage * 0.9):
                m.stage += 1
                m.said = random.choice((
                    "a hand goes up at the back",
                    "the woman in the anorak again",
                    "somebody by the door, without looking up",
                    "the man who bought the last three lots"))
                self.beep("page")
            else:
                m.won = 1
                m.done = True
                self.beep("coin")
        elif m.kind == "quiz" and isinstance(what, int):
            if what == m.right:
                m.won += 1
                m.stage += 1
                self.beep("coin")
                if m.stage >= m.rounds:
                    m.done = True
                else:
                    m.set_question(random.Random(), self.state)
            else:
                m.lost = True
                m.done = True
                self.beep("flip")
        elif m.kind == "haggle" and what in ("up", "down", "offer"):
            if what == "up":
                m.guess = int(clamp(m.guess + 5, 5, 95))
                return
            if what == "down":
                m.guess = int(clamp(m.guess - 5, 5, 95))
                return
            m.tries -= 1
            if m.guess == m.secret or abs(m.guess - m.secret) <= 2:
                m.won = 1
                m.done = True
                self.beep("coin")
            elif m.tries <= 0:
                m.lost = True
                m.done = True
                self.beep("flip")
            else:
                m.said = ("he laughs: more than that"
                          if m.guess < m.secret else
                          "he shrugs: you are over the odds")

    def finish_mini(self):
        """Hand over whatever was won, and close the stall for the day."""
        m = self.mini
        self.mini = None
        self.go("room")
        if m is None:
            return
        stall = next(x for x in STALLS if x[0] == m.stall)
        pack = BY_PACK[stall[3]]
        st = self.state
        won = m.done and not m.lost and m.won >= m.rounds
        if m.kind == "auction":
            price = AUCTION_FLOOR + m.bid
            if won and st.money >= price:
                st.money -= price
                st.spent += price
                st.conv_take(m.stall, pack)
                self.beep("shiny")
                self.toast("knocked down to you",
                           f"{money(price)} - and a room full of people who "
                           f"wanted it", mix(LAMP, CREAM, 0.3), 10.0)
            elif won:
                st.conv_take(m.stall, None)
                self.toast("you could not cover the bid",
                           f"it went for {money(price)}", BAD, 8.0)
            else:
                st.conv_take(m.stall, None)
                self.toast("somebody else got it",
                           "you stopped bidding and they did not", TEA, 8.0)
            self.save()
            return
        if m.kind == "haggle":
            # he sells either way; the game is only ever what it costs you
            price = pack.price * SCALP_MULT * ((m.guess / 100.0) if won
                                               else 1.0)
            if st.money >= price:
                st.money -= price
                st.spent += price
                st.conv_take(m.stall, pack)
                self.beep("shiny" if won else "coin")
                self.toast("you bought the scalped pack",
                           f"{money(price)}" + (" - he took your offer"
                                                if won else
                                                " - he would not come down"),
                           GOOD if won else BAD, 9.0)
            else:
                st.conv_take(m.stall, None)
                self.toast("you could not afford him",
                           f"he wanted {money(price)}", BAD, 8.0)
        elif won:
            st.conv_take(m.stall, pack)
            self.beep("shiny")
            self.toast("you got one", f"{pack.name} - straight into your "
                                      f"bag, no post", mix(LAMP, CREAM, 0.3),
                       10.0)
        else:
            st.conv_take(m.stall, None)
            self.toast("that is the lot", "the table is cleared out until "
                                          "next week", TEA, 8.0)
        self.save()

    def place_bid(self, i):
        st = self.state
        if not 0 <= i < len(st.bids):
            return
        a = st.bids[i]
        if st.bid_on(a):
            self.beep("coin")

    def do_swap(self, i):
        st = self.state
        if not 0 <= i < len(st.swaps):
            return
        w = st.swaps[i]
        gave = BY_KEY[w.want].name
        got = st.take_swap(w)
        if got is None:
            return
        self.beep("shiny" if got.kind == "new" else "level")
        word = ("that is a new one" if got.kind == "new" else
                f"up to level {got.level}" if got.kind == "level"
                else "one you already had")
        self.toast(f"swapped for {got.breed.name}",
                   f"{w.cost} copies of {gave} gone - {word}",
                   mix(LAMP, CREAM, 0.3), 10.0)
        self.save()

    def buy_lot(self, i):
        st = self.state
        if not 0 <= i < len(st.lots):
            return
        lot = st.lots[i]
        got = st.take_lot(lot)
        if got is None:
            return
        if lot.kind == "pack":
            self.beep("coin")
            self.toast("bought off somebody else",
                       f"{lot.words()} - {clock_str(got.left)} in the post",
                       mix(TEA, CREAM, 0.2), 9.0)
        else:
            self.beep("shiny" if lot.shiny else "level")
            word = ("that is a new one" if got.kind == "new" else
                    f"straight to level {got.level}" if got.kind == "level"
                    else "one you already had")
            self.toast(f"{got.breed.name} is yours", word,
                       mix(LAMP, CREAM, 0.3), 10.0)
        self.save()

    def buy_merch(self, key):
        st = self.state
        m = BY_MERCH.get(key)
        if m is None or key in st.kit or st.money < m.price:
            return
        st.money -= m.price
        st.spent += m.price
        st.kit.add(key)
        self.beep("level")
        self.toast(m.name.lower() + ", then", m.effect,
                   mix(LAMP, CREAM, 0.3), 8.0)
        self.save()

    def take_the_room(self):
        """Buy the next room along. They only come in order."""
        st = self.state
        w = st.next_wing
        if w is None or st.money < w.price:
            return
        st.money -= w.price
        st.spent += w.price
        st.wings += 1
        self.room.sync(st, room_cap(st))
        self.beep("shiny")
        last = st.next_wing is None
        self.toast(w.name.lower() + ", then",
                   f"room for {room_cap(st)} of them now"
                   + (" - and nowhere left to grow" if last else ""),
                   mix(LAMP, CREAM, 0.3), 12.0)
        self.save()

    def let_in(self):
        """Open the door. The one thing in this game that costs nothing."""
        got = self.state.take_in(random.Random())
        if got is None:
            return
        b, kind, level = got
        self.beep("shiny" if kind == "new" else "new")
        if kind == "new":
            self.toast(f"{b.name} came in",
                       "not in the catalogue, and never was",
                       mix(LAMP, CREAM, 0.3), 14.0)
        else:
            self.toast(f"{b.name} is back",
                       f"level {level} now" if kind == "level"
                       else "and wants feeding", mix(LAMP, CREAM, 0.3), 9.0)
        self.save()

    def pet(self, key):
        """Click a cat and it tells you who it is, what it is like, and
        what it is doing. In the cat room that opens the card at the
        bottom of the screen; elsewhere it is a line over its head."""
        card = self.state.cards.get(key)
        if card is None:
            return
        self.beep("purr")
        if self.area == "cats":
            for res in self.room.res:
                if res.breed.key == key:
                    self.focus = key
                    self.focus_t = 7.0
                    r = self.room.rect_of(res).move(-int(self.cam), 0)
                    self.floats.append(Float(r.centerx, r.y - 6, "purr",
                                             warm(CREAM, 0.1)))
                    return
        for b, spot in cats_in(self.state, self.area):
            if b.key == key:
                r = cat_rect(b, spot, cat_look(self.state, b))
                self.floats.append(Float(r.centerx, r.y - 6,
                                         f"{b.name}, level {card.level}",
                                         warm(CREAM, 0.1)))

    def draw_focus(self, s):
        """The card at the foot of the cat room: who this one is."""
        if not self.focus or self.focus_t <= 0:
            return
        res = next((r for r in self.room.res
                    if r.breed.key == self.focus), None)
        if res is None:
            return
        b = res.breed
        a = clamp(self.focus_t, 0, 1)
        r = pygame.Rect(W // 2 - 300, H - 118, 600, 86)
        acc = rarity_colour(b.rarity)
        panel(s, r, mix(DEEP, acc, 0.10), shade(acc, 0.7), radius=10,
              alpha=int(238 * a))
        img = cat_surface(b, "sit", 74, False, res.level, res.coat,
                          res.shiny)
        s.blit(img, img.get_rect(midbottom=(r.x + 52, r.bottom - 8)))
        text(s, b.name, 22, (r.x + 98, r.y + 10), warm(CREAM, 0.2),
             alpha=int(255 * a))
        text(s, f"level {res.level}", 13, (r.right - 16, r.y + 16), acc,
             right=True, kind="mono", alpha=int(255 * a))
        text(s, b.temperament["label"], 14, (r.x + 98, r.y + 36),
             warm(EMBER, 0.2), kind="mono", alpha=int(255 * a))
        text(s, b.habit, 13, (r.x + 98, r.y + 56), MUTED, kind="mono",
             alpha=int(240 * a), max_w=r.w - 320)
        text(s, res.doing, 13, (r.right - 16, r.y + 38), TEA,
             right=True, kind="mono", alpha=int(255 * a),
             max_w=r.w - 330)

    # -- ordering -----------------------------------------------------------
    def place_order(self):
        pack = BY_PACK[self.product]
        o = self.state.order(pack, self.qty, self.mode)
        if o is None:
            return
        self.shown_exact = self.state.money  # spending shows at once
        q = quantum(self.state.income)
        self.shown = math.floor(self.state.money / q) * q
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
        self.pack_i = 0
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

    def this_pack(self):
        """The twenty (or fewer) cards on the table right now."""
        lo = self.pack_i * PACK_SIZE
        return self.pulls[lo:lo + PACK_SIZE]

    def next_pack(self):
        if (self.pack_i + 1) * PACK_SIZE < len(self.pulls):
            self.pack_i += 1
            self.flipped = 0
            self.deal = 0.0
            self.beep("page")

    def flip_next(self):
        here = self.this_pack()
        if self.flipped >= len(here):
            return
        p = here[self.flipped]
        self.flipped += 1
        self.beep("flip", 0.8)
        if p.shiny:
            self.beep("shiny")
            self.toast(f"a shiny {p.breed.name}",
                       f"{shiny_coat(p.breed)[0]} - one card in {SHINY_IN}, "
                       f"and it earns a quarter again",
                       mix(LAMP, CREAM, 0.3), 12.0)
        elif p.kind == "new":
            self.beep("legend" if p.breed.rarity >= R_PEDIGREE else "new")
            self.toast(f"{p.breed.name} is new",
                       f"{rarity_name(p.breed.rarity).lower()} - "
                       f"{rate(p.breed.base_rate)} to start",
                       rarity_colour(p.breed.rarity), 6.0)
        elif p.new_coat and len(p.breed.coats) > 1:
            self.beep("level")
            self.toast(f"{p.breed.name} in {coat_name(p.breed, p.coat)}",
                       "a coat of theirs you had not seen",
                       rarity_colour(p.breed.rarity), 6.0)
        elif p.kind == "level":
            self.beep("level")
            if p.level >= MAX_LEVEL:
                self.toast(f"{p.breed.name} is retired",
                           "level 10 - the shop will not send another",
                           LAMP, 7.0)

    def flip_all(self):
        while self.flipped < len(self.this_pack()):
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
        if self.scene in ("intro", "news"):
            self.beat_t += dt
        self.shown_t -= dt
        if self.shown_t <= 0:
            self.shown_t = 0.9
            self.shown_exact = self.state.money
            q = quantum(self.state.income)
            self.shown = math.floor(self.state.money / q) * q
        self.pan = max(0.0, self.pan - dt * 3.1)
        self.cam += (self.cam_to - self.cam) * min(1.0, dt * 7.0)
        self.room.update(dt, self.state, room_cap(self.state),
                         self.cam if self.area == "cats" else None)
        if self.mini is not None:
            self.mini.update(dt)
        st_conv = self.state.convention()
        if st_conv != self.was_conv:
            self.was_conv = st_conv
            if st_conv:
                self.state.conv_refresh()
                self.beep("bell")
                self.toast("the convention is on today",
                           "out of the hall door and left", EMBER, 12.0)
            elif self.area == "conv":
                self.toast("the hall has shut", "same time next week", TEA,
                           8.0)
        if self.area == "conv" and not st_conv:
            self.go_area("hall", quiet=True)
        if self.focus_t > 0:
            self.focus_t = max(0.0, self.focus_t - dt)
        st = self.state
        before = st.income
        landed = st.tick(dt)
        for a, got in st.won_lots:
            self.beep("shiny")
            if a.kind == "pack":
                self.toast("you won the auction",
                           f"{a.words()} for {money(a.price)} - "
                           f"{clock_str(got.left)} in the post",
                           mix(LAMP, CREAM, 0.3), 12.0)
            else:
                self.toast(f"{got.breed.name} is yours",
                           f"won at {money(a.price)}"
                           + (" - that is a new one" if got.kind == "new"
                              else ""), mix(LAMP, CREAM, 0.3), 12.0)
        # Read AFTER the clock has run. The flag is set inside State.tick
        # now, so checking it earlier in this method put the announcement
        # one frame behind the thing it announces - invisible at sixty a
        # second, and plainly wrong the moment anything steps the game
        # once, which is how the test found it.
        untold = [x for x in st.series if x.news and x.key not in st.told]
        if untold and self.scene == "room" and not self.pan:
            self.news_for = untold[0].key
            self.beat, self.beat_t = 0, 0.0
            self.beep("shiny")
            self.go("news")
        for o in landed:
            self.beep("bell" if len(landed) == 1 else "thud")
            self.toast(f"order #{o.num} is here",
                       f"{BY_PACK[o.pack].name} - on the mat in the hall",
                       EMBER, 7.0)
        self.full = len(st.orders) >= st.slots

        came = st.stray_tick(dt, random.Random())
        if came:
            self.beep("bell")
            self.toast("something is at the door",
                       "it is sitting on the step, in the hall",
                       mix(LAMP, CREAM, 0.3), 14.0)

        # The number that floats off a cat is the money that actually
        # arrived since the last one, not a plausible-looking figure.
        self.since_coin += st.income * dt
        # One every few seconds, not one every half second: the point of
        # them is to show that the cats are earning, not to keep score.
        self.coin_timer -= dt
        if self.coin_timer <= 0 and st.income > 0 and self.scene == "room":
            self.coin_timer = random.uniform(3.4, 7.0)
            here = cats_in(st, self.area)
            if here:
                b, spot = random.choice(here)
                r = cat_rect(b, spot, cat_look(st, b))
                self.floats.append(Float(r.centerx + random.uniform(-14, 14),
                                         r.y - 10,
                                         "+" + money_soft(self.since_coin),
                                         mix(LAMP, TEA, 0.35)))
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
        elif self.scene == "intro":
            self.draw_intro(s)
        elif self.scene == "news":
            self.draw_news(s)
        elif self.scene == "mini":
            self.draw_mini(s)
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
            a = int(190 * clamp(f.life / 1.6, 0, 1))
            text(s, f.text, 13, (f.x, f.y), f.colour, center=True,
                 kind="mono", alpha=a, shadow=False)

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
            draw_area(sc, self.pan_from, st, t, 0.0, self.room)
            s.blit(sc, (int(-self.pan_dir * W * (1.0 - f)), 0))
            draw_area(sc, self.area, st, t, self.cam, self.room)
            s.blit(sc, (int(self.pan_dir * W * f), 0))
            self.draw_hud(s)
            return
        draw_area(s, self.area, st, t, self.cam, self.room)
        self.hotspots(s)
        self.draw_hud(s)
        if self.area == "cats":
            self.draw_focus(s)

    def hotspots(self, s):
        """What can be touched in the room you are standing in."""
        st = self.state
        mouse = pygame.mouse.get_pos()
        if self.area == "conv":
            spots = []
            for slot, which in enumerate(stalls_on(st.week)):
                key, title, who, pk, game, blurb = STALLS[which]
                r = pygame.Rect(STALL_X[slot] - 150, CONV_FLOOR - 60,
                                300, 162)
                done = st.conv_played(key)
                spots.append((r, "played this one" if done else "have a go",
                              ("stall", key)))
            spots = tuple(spots)
        elif self.area == "study":
            spots = ((LAPTOP_R, "order some cards", ("laptop", None)),
                     (BINDER_R, "the binder", ("binder", None)))
        elif self.area == "hall":
            r = MAT_R.inflate(0, 72).move(0, -36)
            spots = [(r, "open a parcel" if st.parcels else "nothing today",
                      ("mat", None))]
            if st.stray:
                img = cat_surface(BY_KEY[st.stray], "sit", 140, False, 1)
                spots.append((img.get_rect(midbottom=STRAY_AT),
                              "let it in", ("stray", None)))
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
            r = cat_rect(b, spot, cat_look(st, b))
            self.buttons.append(Button(r, "", ("cat", b.key), "hit"))
            if r.collidepoint(mouse):
                card = st.cards[b.key]
                text(s, f"{b.name}  lv {card.level}", 14,
                     (r.centerx, r.y - 16), warm(CREAM, 0.15), center=True,
                     kind="mono")
        if self.area == "cats":
            screen = pygame.Rect(0, 0, W, H)
            for res in self.room.res:
                r = self.room.rect_of(res).move(-int(self.cam), 0)
                if not screen.colliderect(r):
                    continue          # it is round the corner of the room
                self.buttons.append(Button(r, "", ("cat", res.breed.key),
                                           "hit"))
                if r.collidepoint(mouse):
                    text(s, f"{res.breed.name}  lv {res.level}", 14,
                         (r.centerx, r.y - 16), warm(CREAM, 0.15),
                         center=True, kind="mono")
                    text(s, res.doing, 12, (r.centerx, r.y - 1), TEA,
                         center=True, kind="mono")

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
        r = pygame.Rect(22, 18, 250, 72)
        panel(s, r, mix(DEEP, INK, 0.3), shade(TEA, 0.3), radius=10, alpha=206)
        text(s, money_soft(self.shown), 29, (r.x + 15, r.y + 11),
             mix(CREAM, TEA, 0.38), kind="mono")
        text(s, rate_soft(st.income), 13, (r.right - 13, r.y + 26),
             mix(EMBER, TEA, 0.55), right=True, kind="mono")
        line = f"{st.owned}/{len(st.book)} breeds   {st.retired} retired"
        if st.comfort > 1.001:
            line += f"   flat +{int(round(st.comfort * 100 - 100))}%"
        day = today(st.played)
        when = date_words(st.played) + ("" if day.quiet
                                        else "  -  " + day.name)
        text(s, when, 12, (r.right - 13, r.y + 44),
             mix(TEA, CREAM, 0.1) if st.convention() else
             warm(EMBER, 0.2) if not day.quiet else shade(MUTED, 0.9),
             right=True, kind="mono", shadow=False)
        text(s, line, 12, (r.x + 15, r.y + 48), shade(MUTED, 0.9),
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
                shut = a == "conv" and not st.convention()
                self.buttons.append(Button(r, AREA_NAME[a], ("go", a),
                                           "hit" if on else "link", 14,
                                           kind="mono",
                                           colour=shade(TEA, 0.55) if shut
                                           else TEA))
                if a == "conv":
                    if shut:
                        note = f"in {clock_str(until_convention(st.played))}"
                        col = shade(MUTED, 0.85)
                    else:
                        note = f"on now - {clock_str(until_shut(st.played))}"
                        col = mix(EMBER, CREAM, 0.35)
                    text(s, note, 11, (r.centerx, r.bottom + 3), col,
                         center=True, kind="mono", shadow=False)
                x += wdt
            if self.area == "cats" and self.room.res:
                tal = self.room.tally()
                bits = [f"{v} {k}" for k, v in
                        sorted(tal.items(), key=lambda kv: -kv[1])[:3]]
                text(s, f"{len(self.room.res)} cats in here: "
                        + ", ".join(bits), 13, (W // 2, 80), TEA,
                     center=True, kind="mono", max_w=W - 440)
            if st.stray and self.area != "hall":
                text(s, "there is a cat at the front door", 13,
                     (W // 2, 80 + (20 if self.area == "cats" else 0)),
                     mix(LAMP, CREAM, 0.35), center=True, kind="mono")
            elif st.parcels and self.area != "hall":
                word = "parcel" if len(st.parcels) == 1 else "parcels"
                text(s, f"{len(st.parcels)} {word} on the mat, in the hall",
                     13, (W // 2, 58 + (20 if self.area == "cats" else 0)),
                     warm(EMBER, 0.2), center=True, kind="mono")
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


SITES = (("meowrder", "MEOWRDER", "meowrder.example"),
         ("purrbay", "PURRBAY", "purrbay.example"),
         ("swap", "THE SWAP BOARD", "catswap.example"))


# ---------------------------------------------------------------------------
# HOW IT STARTS
#
# Four screens before the first pack. The flat is empty because you have
# just bought it and it took everything; the one thing in it that works
# is the laptop, and the laptop is how the rest of the game happens.
#
# It plays once, on a new collection, and is skippable from the first
# frame. An intro you cannot get out of is a thing people remember about
# a game for the wrong reason.
# ---------------------------------------------------------------------------
INTRO = (
    ("The flat is yours.",
     "So is the mortgage, the gap where a sofa should be, and a box in "
     "the hall marked KITCHEN that turned out to be books."),
    ("The removal men took the rest.",
     "They took it in cash, at the door, in a sum that was not the sum "
     "on the quote. There is {money} in the account until Friday."),
    ("Which is when you remember the cards.",
     "A man at work had one in a plastic sleeve and would not put it "
     "down. He said the good ones go for thousands. He said it twice."),
    ("{money} is a paper sack of them, posted.",
     "It is Thursday. The post comes once a day, the flat is empty, and "
     "you have nothing else on."),
)


def _intro_room(surf, t, beat, lit):
    """An empty room with the light off and a laptop on the floor.

    `lit` runs 0 to 1 across the four screens: the room starts as a shape
    in the dark and ends with the screen on, which is the only light in
    it and the only thing in the game that matters yet.
    """
    surf.fill(INK)
    floor = 556
    for y in range(0, floor, 4):
        f = y / floor
        pygame.draw.rect(surf, mix((22, 18, 18), (44, 34, 30),
                                   (f ** 0.7) * (0.45 + 0.55 * lit)),
                         (0, y, W, 4))
    pygame.draw.rect(surf, shade(WOOD_LO, 0.52 + 0.3 * lit),
                     (0, floor, W, H - floor))
    for i in range(9):
        hairline(surf, 0, floor + 14 + i * 26, W, WOOD_HI,
                 int(10 + 18 * lit))

    # a bulb on a flex, no shade, because the shades are in a box
    pygame.draw.line(surf, shade(WOOD_LO, 1.4), (300, 0), (300, 150), 2)
    glow(surf, (300, 160), int(190 + 90 * lit), mix(LAMP, CREAM, 0.3),
         0.10 + 0.14 * lit)
    pygame.draw.circle(surf, mix(LAMP, CREAM, 0.5), (300, 160), 11)

    # the boxes, stacked where the removal men left them
    rng = random.Random(4)
    for bx, by, bw, bh in ((120, 392, 150, 120), (128, 300, 128, 96),
                           (286, 404, 168, 108), (860, 382, 176, 130),
                           (884, 286, 138, 100), (1040, 420, 120, 92)):
        face = mix(WOOD, PAPER, 0.18 + 0.1 * lit)
        pygame.draw.rect(surf, face, (bx, by, bw, bh), border_radius=3)
        pygame.draw.rect(surf, shade(face, 0.76), (bx, by, bw, bh), width=2,
                         border_radius=3)
        pygame.draw.line(surf, shade(face, 0.84), (bx + bw // 2, by),
                         (bx + bw // 2, by + bh), 2)
        tape = pygame.Rect(bx + 10, by + bh // 2 - 7, bw - 20, 14)
        pygame.draw.rect(surf, mix(face, LAMP, 0.25), tape, border_radius=2)
        text(surf, rng.choice(("KITCHEN", "BOOKS", "MISC", "BEDROOM",
                               "FRAGILE")), 11, tape.center,
             shade(INK, 1.5), center=True, kind="mono", shadow=False)

    # the laptop, open on the floorboards, which is where it lives for now
    lap = pygame.Rect(W // 2 - 128, 560, 256, 132)
    pygame.draw.polygon(surf, shade(WOOD, 0.6),
                        [(lap.x - 22, lap.bottom), (lap.right + 22,
                                                    lap.bottom),
                         (lap.right - 6, lap.bottom - 14),
                         (lap.x + 6, lap.bottom - 14)])
    scr = pygame.Rect(lap.x + 8, lap.y - 4, lap.w - 16, 118)
    pygame.draw.rect(surf, shade(WOOD_LO, 1.1), scr.inflate(10, 10),
                     border_radius=6)
    pygame.draw.rect(surf, mix(SCREEN, LAMP, 0.10 + 0.30 * lit), scr,
                     border_radius=4)
    glow(surf, (scr.centerx, scr.centery), int(150 + 230 * lit),
         mix(LAMP, CREAM, 0.4), 0.06 + 0.26 * lit)
    for i in range(4):               # the website, too far away to read
        wr = pygame.Rect(scr.x + 14, scr.y + 16 + i * 22, scr.w - 28, 10)
        pygame.draw.rect(surf, mix(SCREEN_HI, EMBER, 0.1 + 0.3 * lit),
                         (wr.x, wr.y, wr.w * (0.9 - i * 0.14), wr.h),
                         border_radius=3)

    # a cat on top of the boxes, which is not your cat and has not been
    # invited, and is the first one in the game
    if beat >= 2:
        a = clamp((lit - 0.3) * 2.4, 0.0, 1.0)
        # cat_surface caches what it builds, so this copies before it
        # paints - darkening the cached one would darken that cat in the
        # binder, in the room and on every card it ever appears on
        img = cat_surface(BY_KEY["dsh"], "sit", 92, level=1).copy()
        dark = pygame.Surface(img.get_size(), pygame.SRCALPHA)
        dark.fill((*mix(INK, WOOD, 0.3), 255))
        img.blit(dark, (0, 0), None, pygame.BLEND_RGBA_MULT)
        img.set_alpha(int(210 * a))
        surf.blit(img, img.get_rect(midbottom=(953, 292)))


# ---------------------------------------------------------------------------
# THE ANNOUNCEMENT
#
# Three screens, the day the hundredth breed goes in the book. The first
# is the binder finished, the second is the email, and the third is what
# the email was about.
#
# It does NOT play the moment the flag flips. You finish the catalogue by
# opening a parcel, so the moment it happens you are almost always
# halfway through a pack with cards still face down - and cutting away
# from that would eat them. The series exists immediately, because the
# website has to have the page; the cutscene waits until you are back in
# a room, and `seen_news` is saved so it cannot be missed by quitting.
# ---------------------------------------------------------------------------
NEWS = (
    ("A hundred of a hundred.",
     "Every breed in the catalogue, in a binder, on a desk, in a flat you "
     "have nearly paid for. There is nothing left in the book to find."),
    ("MEOWRDER would like a word.",
     "The email came at nine minutes past midnight, which is when these "
     "things are sent. They have been working on something. They are very "
     "excited about it. They would like you to be excited about it too."),
    ("The Kitten Series.",
     "Twelve new cards, none of them in the old book, and a page on the "
     "website that was not there this morning. You know exactly what this "
     "is. You are going to buy them anyway."),
)


def _news_scene(surf, t, beat, f, cats=()):
    """`f` is 0 to 1 through the current screen."""
    surf.fill(INK)
    for y in range(0, H, 6):
        pygame.draw.rect(surf, mix((26, 20, 20), (48, 36, 32),
                                   (y / H) ** 0.8), (0, y, W, 6))
    glow(surf, (W // 2, 300), 520, mix(LAMP, EMBER, 0.35), 0.12 + 0.06 * f)

    if beat == 0:
        # the binder, shut, with everything in it
        book = pygame.Rect(W // 2 - 190, 300, 380, 270)
        panel(surf, book, mix(RUG, WOOD, 0.45), shade(RUG, 1.2), radius=12)
        inner = book.inflate(-30, -30)
        pygame.draw.rect(surf, mix(DEEP, WOOD, 0.35), inner, width=3,
                         border_radius=8)
        spine = pygame.Rect(book.x, book.y, 26, book.h)
        pygame.draw.rect(surf, shade(RUG, 0.82), spine,
                         border_top_left_radius=12,
                         border_bottom_left_radius=12)
        for i in range(3):
            c = (spine.centerx, book.y + 66 + i * 70)
            pygame.draw.circle(surf, shade(INK, 1.4), c, 9)
            pygame.draw.circle(surf, mix(TEA, CREAM, 0.35), c, 9, 3)
        stamp = pygame.Rect(0, 0, 150, 56)
        stamp.center = (book.centerx, book.centery)
        pygame.draw.rect(surf, mix(LAMP, CREAM, 0.3), stamp, width=3,
                         border_radius=6)
        text(surf, "FULL", 30, stamp.center,
             mix(LAMP, CREAM, 0.35), center=True, kind="mono")
        text(surf, "THE CATALOGUE, COMPLETE", 13,
             (book.centerx, book.bottom - 36), mix(PAPER, WOOD, 0.4),
             center=True, kind="mono")

    elif beat == 1:
        # the email, on the laptop, at nine minutes past midnight
        win = pygame.Rect(W // 2 - 300, 290, 600, 290)
        panel(surf, win, SCREEN, shade(SCREEN_HI, 1.4), radius=10)
        bar = pygame.Rect(win.x, win.y, win.w, 40)
        pygame.draw.rect(surf, shade(SCREEN_HI, 0.8), bar,
                         border_top_left_radius=10, border_top_right_radius=10)
        for i, c in enumerate(((168, 96, 86), (176, 150, 92),
                               (118, 150, 112))):
            pygame.draw.circle(surf, c, (bar.x + 22 + i * 18, bar.centery), 5)
        text(surf, "inbox - 1 new", 13, (bar.centerx, bar.centery),
             mix(TEA, CREAM, 0.2), center=True, kind="mono", shadow=False)
        text(surf, "00:09", 12, (bar.right - 18, bar.centery), DIM,
             right=True, kind="mono", shadow=False)
        text(surf, "MEOWRDER", 24, (win.x + 24, win.y + 58),
             warm(EMBER, 0.25))
        text(surf, "A SECOND SERIES", 15, (win.x + 24, win.y + 92),
             mix(CREAM, TEA, 0.2), kind="mono")
        hairline(surf, win.x + 24, win.y + 116, win.right - 24, TEA, 60)
        rng = random.Random(6)
        for i in range(5):           # the body, too far away to read
            wr = pygame.Rect(win.x + 24, win.y + 132 + i * 20,
                             int((win.w - 48) * rng.uniform(0.45, 1.0)), 9)
            if i * 20 + 132 < win.h - 40:
                pygame.draw.rect(surf, shade(SCREEN_HI, 1.5), wr,
                                 border_radius=4)
        seal = pygame.Rect(win.right - 150, win.bottom - 62, 126, 38)
        pygame.draw.rect(surf, mix(EMBER, LAMP, 0.3), seal, border_radius=6)
        text(surf, "READ MORE", 14, seal.center, shade(INK, 1.4),
             center=True, kind="mono", shadow=False)

    else:
        # the new ones, coming up out of the dark one at a time
        show = cats[:6]
        wide = len(show) * 150
        x0 = W // 2 - wide // 2 + 75
        for i, b in enumerate(show):
            on = clamp((f * len(show) + 0.6) - i, 0.0, 1.0)
            img = cat_surface(b, "sit", 150, level=3).copy()
            dark = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            tone = mix((38, 32, 34), (255, 250, 246), on)
            dark.fill((*tone, 255))
            img.blit(dark, (0, 0), None, pygame.BLEND_RGBA_MULT)
            img.set_alpha(int(150 + 105 * on))
            surf.blit(img, img.get_rect(midbottom=(x0 + i * 150, 540)))
        if len(cats) > len(show):
            text(surf, f"and {len(cats) - len(show)} more", 14,
                 (W // 2, 560), MUTED, center=True, kind="mono")


def _browser(surf, title, host="meowrder.example"):
    panel(surf, SHOP_R, SCREEN, shade(SCREEN_HI, 1.4), radius=10)
    bar_r = pygame.Rect(SHOP_R.x, SHOP_R.y, SHOP_R.w, 44)
    pygame.draw.rect(surf, shade(SCREEN_HI, 0.8), bar_r,
                     border_top_left_radius=10, border_top_right_radius=10)
    for i, c in enumerate(((168, 96, 86), (176, 150, 92), (118, 150, 112))):
        pygame.draw.circle(surf, c, (bar_r.x + 24 + i * 20, bar_r.centery), 6)
    pill = pygame.Rect(bar_r.x + 96, bar_r.y + 9, bar_r.w - 180, 26)
    pygame.draw.rect(surf, shade(SCREEN, 1.3), pill, border_radius=13)
    text(surf, host + "/" + title, 14,
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
        if self.site == "swap":
            _browser(s, "board", "catswap.example")
            self._bookmarks(s)
            self.draw_swaps(s)
            return
        if self.site == "purrbay":
            _browser(s, "listings", "purrbay.example")
            self._bookmarks(s)
            self.draw_resale(s)
            return
        _browser(s, "catalogue" if not self.product else
                 "catalogue/" + self.product)
        self._bookmarks(s)

        # masthead
        x, y = PAGE_R.x + 18, PAGE_R.y + 6
        text(s, "MEOWRDER", 30, (x, y), warm(EMBER, 0.25))
        text(s, "cards, by post, since 1998", 13, (x + 186, y + 16), DIM,
             kind="mono", left=True, shadow=False)
        text(s, money(self.shown_exact), 24, (PAGE_R.right - 18, y + 14),
             mix(CREAM, TEA, 0.3), right=True, kind="mono")
        text(s, f"{len(st.orders)}/{st.slots} parcels in the post", 12,
             (PAGE_R.right - 18, y + 36), MUTED if not self.full else BAD,
             right=True, kind="mono", shadow=False)
        day = today(st.played)
        if not day.quiet:
            tag = text(s, day.name, 14, (x + 196, y + 34),
                       warm(EMBER, 0.25) if day.sale < 1 else
                       mix(LAMP, CREAM, 0.3), left=True, kind="mono")
            text(s, day.blurb, 12, (tag.right + 12, y + 35), MUTED,
                 left=True, kind="mono",
                 max_w=max(80, (PAGE_R.right - 230) - (tag.right + 12)))
        hairline(s, x, y + 50, PAGE_R.right - 18, TEA, 60)

        # Nine products do not fit one page at a size anybody can read,
        # and the four odd ones are not rungs on the ladder anyway: they
        # are things you go looking for when you want a particular thing.
        # Two rows: the pages that sell cards, and the pages that do
        # not. One row held five of these and then seven; at four
        # collections it would be ten, and the last of them printed
        # straight through the link back to the room. A row each means a
        # fifth series costs the shop nothing.
        cards_row = [("catalogue", "CATALOGUE"), ("specials", "SPECIALS")]
        cards_row += [(x.shelf, SERIES_TAB.get(x.key, x.key.upper()))
                      for x in st.series if x.key != "cat"]
        rest_row = [("home", "THE FLAT"), ("merch", "MERCH"),
                    ("room", "THE ROOM"), ("orders", "ORDERS"),
                    ("club", "THE CLUB")]
        for row, items in ((0, cards_row), (1, rest_row)):
            tx = x
            for key, label in items:
                lab = label + (f" ({len(st.orders)})" if key == "orders"
                               and st.orders else "")
                wdt = font(15, False, "mono").size(lab)[0] + 18
                r = pygame.Rect(tx, y + 58 + row * 32, wdt, 28)
                on = self.tab == key
                if on:
                    pygame.draw.rect(s, mix(SCREEN_HI, EMBER, 0.2), r,
                                     border_radius=6)
                self.buttons.append(Button(r, lab, ("tab", key),
                                           "link" if not on else "hit", 15,
                                           kind="mono",
                                           colour=CREAM if on else TEA))
                if on:
                    text(s, lab, 15, r.center, warm(CREAM, 0.2), center=True,
                         kind="mono", shadow=False)
                tx += wdt + 5
        self.buttons.append(Button((PAGE_R.right - 124, y + 90, 116, 28),
                                   "< the room", ("scene", "room"),
                                   "link", 15, kind="mono", colour=TEA))

        body = pygame.Rect(PAGE_R.x + 18, y + 126, PAGE_R.w - 36,
                           PAGE_R.bottom - (y + 126) - 8)
        shown = next((x for x in SERIES if x.shelf == self.tab
                      and x.key != "cat"), None)
        if shown is not None and shown.key not in st.out:
            self.tab, shown = "catalogue", None

        # The product page wins over the tab it was opened from.
        #
        # It used to be the LAST branch of this chain, below every tab
        # that has no products in it, which worked only because those
        # tabs can never have a product open: switching tab clears it.
        # The kitten page broke that the moment it was added above the
        # check - you could open a kitten product and the list would
        # redraw over it, so there was no ORDER button anywhere and the
        # whole series was unbuyable. Nothing about the state refused
        # the sale; the page to make it simply never rendered.
        if self.product and self.product in BY_PACK:
            self.draw_product(s, body)
        elif shown is not None:
            got = sum(1 for k in st.cards if k in shown.keys)
            text(s, shown.name.upper(), 22, (body.x, body.y),
                 warm(CREAM, 0.2))
            text(s, f"{shown.blurb}  You have {got} of "
                    f"{len(shown.cats)}.", 13, (body.x, body.y + 28),
                 MUTED, kind="mono", max_w=body.w)
            self.draw_catalogue(s, pygame.Rect(body.x, body.y + 46,
                                               body.w, body.h - 46),
                                shown.shelf)
        elif self.tab == "merch":
            self.draw_merch(s, body)
        elif self.tab == "room":
            self.draw_room_page(s, body)
        elif self.tab == "orders":
            self.draw_orders(s, body)
        elif self.tab == "home":
            self.draw_home(s, body)
        elif self.tab == "club":
            self.draw_club(s, body)
        else:
            self.draw_catalogue(s, body, "special" if self.tab == "specials"
                                else "standard")

    # -- two sites, one laptop ---------------------------------------------
    def _bookmarks(self, s):
        """The bar under the address bar. The second site is the whole
        reason the first one has a name."""
        bx = SHOP_R.x + 96
        for key, label, host in SITES:
            on = self.site == key
            wdt = font(12, False, "mono").size(label)[0] + 22
            r = pygame.Rect(bx, SHOP_R.y + 44, wdt, 22)
            if on:
                pygame.draw.rect(s, mix(SCREEN_HI, EMBER, 0.22), r,
                                 border_bottom_left_radius=5,
                                 border_bottom_right_radius=5)
            self.buttons.append(Button(r, label, ("site", key),
                                       "hit" if on else "link", 12,
                                       kind="mono",
                                       colour=CREAM if on else DIM))
            if on:
                text(s, label, 12, r.center, warm(CREAM, 0.2), center=True,
                     kind="mono", shadow=False)
            bx += wdt + 6

    # -- the swap board ----------------------------------------------------
    def draw_swaps(self, s):
        """Five posts. Nothing here costs money and nothing can be rushed."""
        st = self.state
        st.refresh_swaps()
        x, y = PAGE_R.x + 18, PAGE_R.y + 6
        tr = text(s, "THE SWAP BOARD", 30, (x, y), mix(GOOD, CREAM, 0.35))
        text(s, "copies for copies, no money", 13, (tr.right + 14, y + 16),
             DIM, kind="mono", left=True, shadow=False)
        text(s, f"{st.swapped} swaps done", 14,
             (PAGE_R.right - 18, y + 16), mix(CREAM, TEA, 0.3), right=True,
             kind="mono")
        hairline(s, x, y + 50, PAGE_R.right - 18, TEA, 60)
        text(s, "A level is made of copies, so what you hand over comes off "
                "your levels. Nobody here posts twice.", 12, (x, y + 60),
             MUTED, kind="mono", max_w=PAGE_R.w - 220)
        text(s, f"the board changes in {clock_str(until_midnight(st.played))}",
             12, (PAGE_R.right - 18, y + 60), TEA, right=True, kind="mono",
             shadow=False)
        self.buttons.append(Button((PAGE_R.right - 124, y + 82, 116, 26),
                                   "< the room", ("scene", "room"),
                                   "link", 15, kind="mono", colour=TEA))

        body = pygame.Rect(PAGE_R.x + 18, y + 114, PAGE_R.w - 36,
                           PAGE_R.bottom - (y + 114) - 8)
        if not st.swaps:
            text(s, "nothing on the board", 20, (body.centerx, body.y + 40),
                 MUTED, center=True, kind="mono")
            text(s, "you need a card of your own before anybody will swap "
                    "with you", 13, (body.centerx, body.y + 72), DIM,
                 center=True, kind="mono")
            return
        rowh = body.h // max(1, len(st.swaps))
        for i, w in enumerate(st.swaps):
            self._swap_row(s, pygame.Rect(body.x, body.y + i * rowh,
                                          body.w, rowh - 8), w, i)

    def _swap_row(self, s, r, w, i):
        st = self.state
        give, want = BY_KEY[w.give], BY_KEY[w.want]
        have = st.copies_of(w.want)
        can = st.can_swap(w)
        panel(s, r, mix(SCREEN_HI, EMBER, 0.10 if w.done else 0.03),
              shade(EMBER, 0.7) if w.done else shade(SCREEN_HI, 1.4),
              radius=8, shadow=False)
        name, greed, blurb = SWAPPERS[w.who]
        text(s, name, 15, (r.x + 14, r.y + 8),
             mix(TEA, CREAM, 0.3), kind="mono", max_w=260)
        text(s, blurb, 11, (r.x + 14, r.y + 28), shade(MUTED, 0.9),
             kind="mono", max_w=270)
        # what they want, in the middle
        wx = r.x + 300
        text(s, "WANTS", 11, (wx, r.y + 8), MUTED, kind="mono")
        text(s, f"{w.cost} x {want.name}", 17, (wx, r.y + 24),
             rarity_colour(want.rarity), max_w=230)
        text(s, f"you have {have} spare" + ("" if have == 1 else "s"), 12,
             (wx, r.y + 48), GOOD if have >= w.cost else BAD, kind="mono")
        # what they give
        gx = r.x + 560
        text(s, "GIVES", 11, (gx, r.y + 8), MUTED, kind="mono")
        text(s, give.name, 17, (gx, r.y + 24), rarity_colour(give.rarity),
             max_w=230)
        text(s, rarity_name(give.rarity).lower()
             + ("" if give.key in st.cards else " - not in your binder"), 12,
             (gx, r.y + 48), mix(LAMP, CREAM, 0.3)
             if give.key not in st.cards else MUTED, kind="mono", max_w=230)
        if w.done:
            text(s, "SWAPPED", 14, (r.right - 24, r.centery), GOOD,
                 right=True, kind="mono")
        else:
            why = ("" if w.want in st.cards else "you have not got one")
            if not why and have < w.cost:
                why = f"{w.cost - have} copies short"
            if why:
                text(s, why, 11, (r.right - 24, r.bottom - 16), BAD,
                     right=True, kind="mono")
            self.buttons.append(Button(
                (r.right - 130, r.centery - 18, 110, 36), "SWAP",
                ("swap", i), "solid", 16, kind="mono", enabled=can))

    # -- the resale site ---------------------------------------------------
    def draw_resale(self, s):
        """Six listings, most of them somebody taking you for a ride."""
        st = self.state
        st.refresh_lots()
        x, y = PAGE_R.x + 18, PAGE_R.y + 6
        text(s, "PURRBAY", 30, (x, y), mix(TEA, CREAM, 0.45))
        text(s, "cards people already own", 13, (x + 150, y + 16), DIM,
             kind="mono", left=True, shadow=False)
        text(s, money(self.shown_exact), 24, (PAGE_R.right - 18, y + 14),
             mix(CREAM, TEA, 0.3), right=True, kind="mono")
        text(s, f"{len(st.orders)}/{st.slots} parcels in the post", 12,
             (PAGE_R.right - 18, y + 36), MUTED if not self.full else BAD,
             right=True, kind="mono", shadow=False)
        hairline(s, x, y + 50, PAGE_R.right - 18, TEA, 60)
        text(s, "Sealed boxes go in the post like anything else. Single "
                "cards they will meet you for - that is what you are paying "
                "the extra for.", 12, (x, y + 60), MUTED, kind="mono",
             max_w=PAGE_R.w - 220)
        if self.bay == "buy":
            text(s, f"stock changes in "
                    f"{clock_str(until_midnight(st.played))}", 12,
                 (PAGE_R.right - 18, y + 60), TEA, right=True, kind="mono",
                 shadow=False)
        self.buttons.append(Button((PAGE_R.right - 190, y + 78, 180, 26),
                                   "< back to the room", ("scene", "room"),
                                   "link", 15, kind="mono", colour=TEA))
        tx = x
        for key, label in (("buy", "BUY IT NOW"), ("bid", "AUCTIONS")):
            lab = label + (f" ({sum(1 for a in st.bids if a.mine)})"
                           if key == "bid" and any(a.mine for a in st.bids)
                           else "")
            wdt = font(15, False, "mono").size(lab)[0] + 18
            r = pygame.Rect(tx, y + 80, wdt, 26)
            on = self.bay == key
            if on:
                pygame.draw.rect(s, mix(SCREEN_HI, EMBER, 0.2), r,
                                 border_radius=6)
                text(s, lab, 15, r.center, warm(CREAM, 0.2), center=True,
                     kind="mono", shadow=False)
            self.buttons.append(Button(r, lab, ("bay", key),
                                       "hit" if on else "link", 15,
                                       kind="mono",
                                       colour=CREAM if on else TEA))
            tx += wdt + 6
        if self.bay == "bid":
            self.draw_bids(s, pygame.Rect(PAGE_R.x + 18, y + 118,
                                          PAGE_R.w - 36,
                                          PAGE_R.bottom - (y + 118) - 8))
            return

        body = pygame.Rect(PAGE_R.x + 18, y + 118, PAGE_R.w - 36,
                           PAGE_R.bottom - (y + 118) - 8)
        cols, rows = 3, 2
        gw, gh = body.w // cols, body.h // rows
        for i, lot in enumerate(st.lots[:cols * rows]):
            r = pygame.Rect(body.x + (i % cols) * gw, body.y + (i // cols) * gh,
                            gw - 14, gh - 14)
            self._lot_tile(s, r, lot, i)

    def draw_bids(self, s, body):
        """What is running, what it stands at, and how long you have."""
        st = self.state
        if not st.bids:
            text(s, "nothing under the hammer", 20,
                 (body.centerx, body.y + 40), MUTED, center=True,
                 kind="mono")
            return
        rowh = body.h // max(1, len(st.bids))
        for i, a in enumerate(st.bids):
            r = pygame.Rect(body.x, body.y + i * rowh, body.w - 8, rowh - 8)
            self._bid_row(s, r, a, i)

    def _bid_row(self, s, r, a, i):
        st = self.state
        left = a.left(st.played)
        soon = left < 45
        panel(s, r, mix(SCREEN_HI, EMBER, 0.12 if a.mine else 0.03),
              shade(GOOD, 0.8) if a.mine else
              shade(BAD, 0.7) if soon else shade(SCREEN_HI, 1.4),
              radius=8, shadow=False)
        pic = pygame.Rect(r.x + 10, r.y + 8, 74, r.h - 16)
        if a.kind == "card":
            draw_card(s, pic, BY_KEY[a.key], a.level, variant=a.coat,
                      shiny=a.shiny, show_rate=False)
        else:
            draw_pack_art(s, pic, BY_PACK[a.key])
        tx = pic.right + 14
        text(s, a.words(), 18, (tx, r.y + 10), CREAM, max_w=300)
        sub_line = (f"{BY_PACK[a.key].cards * a.qty} cards, in the post"
                    if a.kind == "pack" else
                    coat_name(BY_KEY[a.key], a.coat, a.shiny, full=a.shiny))
        text(s, sub_line, 12, (tx, r.y + 34),
             mix(LAMP, CREAM, 0.3) if a.shiny else MUTED, kind="mono",
             max_w=300)
        if a.mine:
            who, col = "you are the high bidder", GOOD
        elif a.price <= a.start:
            who, col = "no bids yet", MUTED
        else:
            who, col = f"{BIDDERS[a.who][0]} is ahead of you", BAD
        text(s, who, 12, (tx, r.y + 54), col, kind="mono", max_w=320)

        mx = r.x + 470
        text(s, "STANDS AT", 11, (mx, r.y + 10), MUTED, kind="mono")
        text(s, money(a.price), 24, (mx, r.y + 26),
             warm(EMBER, 0.2) if not a.mine else GOOD)
        text(s, f"closes in {clock_str(left)}", 13, (mx, r.y + 58),
             BAD if soon else TEA, kind="mono")

        nxt = a.price + a.step if a.price > a.start else a.price
        if a.mine:
            text(s, "nothing to do but wait", 12, (r.right - 24, r.centery),
                 GOOD, right=True, kind="mono")
        else:
            can = st.money >= nxt
            text(s, f"bid {money(nxt)}", 13,
                 (r.right - 24, r.centery - 26),
                 mix(TEA, CREAM, 0.2) if can else BAD, right=True,
                 kind="mono")
            self.buttons.append(Button(
                (r.right - 150, r.centery - 10, 130, 36), "BID",
                ("bid", i), "solid", 16, kind="mono", enabled=can))

    def _lot_tile(self, s, r, lot, i):
        st = self.state
        name, mark, _weight, _blurb = SELLERS[lot.seller]
        honest = lot.seller < SELLER_HONEST
        panel(s, r, mix(SCREEN_HI, EMBER, 0.03 if not lot.sold else 0.10),
              shade(SCREEN_HI, 1.4), radius=8, shadow=False)
        pic = pygame.Rect(r.x + 10, r.y + 10, 92, 128)
        if lot.kind == "card":
            b = BY_KEY[lot.key]
            draw_card(s, pic, b, lot.level, dupes=0, variant=lot.coat,
                      shiny=lot.shiny, show_rate=False)
        else:
            draw_pack_art(s, pic, BY_PACK[lot.key])
        tx = pic.right + 12
        tw = r.right - tx - 10
        rare = lot.kind == "pack" and lot.key in NEVER_STOCKED
        if rare:
            rib = pygame.Rect(r.x + 8, r.y - 9, r.w - 16, 19)
            pygame.draw.rect(s, mix(LAMP, EMBER, 0.35), rib, border_radius=5)
            text(s, "SOMEBODY IS CLEARING THEIR LOFT", 11, rib.center,
                 shade(INK, 1.4), center=True, kind="mono", shadow=False)
        text(s, lot.words(), 17, (tx, r.y + 10), CREAM, max_w=tw)
        sub_line = (f"{BY_PACK[lot.key].cards} cards, one parcel"
                    if rare else
                    "sealed, in the post" if lot.kind == "pack"
                    else coat_name(BY_KEY[lot.key], lot.coat, lot.shiny,
                                   full=lot.shiny))
        text(s, sub_line, 12, (tx, r.y + 32),
             mix(LAMP, CREAM, 0.3) if lot.shiny else MUTED, kind="mono",
             max_w=tw)
        text(s, name, 12, (tx, r.y + 52), TEA, kind="mono", max_w=tw)
        text(s, f"{mark:.2g}x over the odds" if not honest
             else f"{mark:.2g}x - about fair", 11, (tx, r.y + 70),
             GOOD if honest else BAD, kind="mono", max_w=tw)
        paragraph(s, _blurb, 11, (tx, r.y + 90), shade(MUTED, 0.9), tw, 4,
                  kind="mono")
        cost = st.lot_cost(lot)
        text(s, money(cost), 22, (tx, r.bottom - 58),
             warm(EMBER, 0.2) if not lot.sold else MUTED)
        if lot.sold:
            text(s, "SOLD - TO YOU", 13, (tx, r.bottom - 28), GOOD,
                 kind="mono")
        else:
            why = ("" if st.money >= cost else "you cannot afford it")
            if not why and lot.kind == "pack" and len(st.orders) >= st.slots:
                why = "the round is full"
            if why:
                text(s, why, 11, (tx, r.bottom - 26), BAD, kind="mono",
                     max_w=tw)
            self.buttons.append(Button(
                (r.right - 102, r.bottom - 44, 90, 32), "BUY IT",
                ("lot", i), "solid", 15, kind="mono",
                enabled=st.can_take(lot)))

    # -- the list of things to buy -----------------------------------------
    def draw_catalogue(self, s, body, shelf="standard"):
        st = self.state
        rows = packs_on(shelf)
        if shelf == "special":
            text(s, "Four things that are not on the ladder. None is a good "
                    "deal by the card; each is the only way to go looking "
                    "for one particular thing.", 13,
                 (body.x, body.y + 2), MUTED, kind="mono", max_w=body.w)
            body = pygame.Rect(body.x, body.y + 24, body.w, body.h - 24)
        rowh = (body.h - 6) // len(rows)
        for i, p in enumerate(rows):
            r = pygame.Rect(body.x, body.y + i * rowh, body.w, rowh - 8)
            live = st.sellable(p)
            ask = price_of(p, st)
            afford = st.money >= ask and not self.full
            panel(s, r, mix(SCREEN_HI, EMBER, 0.05 if live else 0.0),
                  shade(SCREEN_HI, 1.5), radius=8, shadow=False)
            art = pygame.Rect(r.x + 10, r.y + 8, 104, r.h - 16)
            draw_pack_art(s, art, p, self.t)
            col = CREAM if live else DIM
            text(s, p.name, 21, (art.right + 16, r.y + 10), col)
            # Six rungs on a page that used to hold five: the blurb now
            # has to stop where the line of stats begins rather than
            # running through it. Draw only the lines that fit.
            blurb_y = r.y + 34
            room = (r.bottom - 26) - blurb_y
            lines = wrap(p.blurb, 13, 520, kind="mono")
            fit_n = max(1, room // 16)
            for k, line in enumerate(lines[:fit_n]):
                if k == fit_n - 1 and len(lines) > fit_n:
                    line = line.rstrip(" .,") + "..."
                text(s, line, 13, (art.right + 16, blurb_y + k * 16),
                     MUTED if live else shade(DIM, 0.9), kind="mono",
                     shadow=False)
            text(s, f"{p.cards} card" + ("s" if p.cards > 1 else "")
                 + (f", {parcel_words(p.cards)}" if p.cards > PACK_SIZE
                    else ""), 13,
                 (art.right + 16, r.bottom - 22),
                 mix(TEA, CREAM, 0.2), kind="mono", shadow=False)
            text(s, f"ships in {clock_str(p.ship * today(st.played).ship)}",
                 13,
                 (art.right + 196, r.bottom - 22), DIM, kind="mono",
                 shadow=False)
            _stars(s, 5 - i // 2, (art.right + 330, r.bottom - 16))
            text(s, f"{(i + 2) * 307 % 900 + 104:,} reviews", 12,
                 (art.right + 420, r.bottom - 16), DIM, kind="mono",
                 shadow=False, left=True)
            if live:
                if ask < p.price:
                    was = text(s, money(p.price), 15,
                               (r.right - 150, r.y + 10), shade(MUTED, 0.9),
                               right=True, kind="mono")
                    pygame.draw.line(s, shade(MUTED, 0.9),
                                     (was.x - 2, was.centery),
                                     (was.right + 2, was.centery), 1)
                text(s, money(ask), 26, (r.right - 150, r.y + 18),
                     warm(EMBER, 0.2), right=True)
            btn = pygame.Rect(r.right - 132, r.centery - 19, 118, 38)
            if not live:
                self.buttons.append(Button(btn, "WITHDRAWN", ("tab", shelf),
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
        unit = price_of(p, st)          # what it is today, not on the box
        # back to the shelf it is actually on, not always the front page
        back = ("specials" if p.shelf == "special"
                else p.shelf if any(x.shelf == p.shelf and x.key != "cat"
                                    for x in SERIES)
                else "catalogue")
        self.buttons.append(Button((body.x, body.y, 160, 24),
                                   "< everything else", ("tab", back),
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
        y = paragraph(s, p.blurb, 14, (right.x, right.y + 38),
                      mix(TEA, CREAM, 0.3), right.w - 10, 3,
                      kind="mono") + 8

        # the odds, drawn as the shop would have to print them
        text(s, "WHAT IS IN IT", 13, (right.x, y), TEA, kind="mono",
             shadow=False)
        y += 20
        tot = sum(p.weights)
        # The pitch comes from how many rows there are going to be. At
        # seven tiers this column fitted with nothing to spare, and the
        # comment below said so; at nine, a crate that sells eight of
        # them pushed PLACE ORDER down onto the postage options.
        rows = sum(1 for r in range(SOLD_RARITIES) if p.weights[r])
        extras = 1 + (1 if p.fresh_coats else 0) + (1 if p.shiny_mult > 1
                                                    else 0)
        choices_y = body.bottom - 226
        room = choices_y - y - 20 - extras * 18
        pitch = int(clamp(room / max(1, rows), 11, 18))
        for r in range(SOLD_RARITIES):
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
            y += pitch
        y += 4
        text(s, f"the last card is {rarity_name(p.floor).lower()} or better",
             12, (right.x, y + 6), mix(TEA, CREAM, 0.1), kind="mono",
             shadow=False)
        y += 20
        if p.fresh_coats:
            text(s, "the house picks coats you have not seen", 12,
                 (right.x, y + 6), warm(GOOD, 0.2), kind="mono", shadow=False)
            y += 16
        if p.shiny_mult > 1:
            text(s, f"shinies turn up {p.shiny_mult:.0f} times as often - "
                    f"about one card in {SHINY_IN / p.shiny_mult:.0f}", 12,
                 (right.x, y + 6), warm(LAMP, 0.1), kind="mono", shadow=False)
            y += 16
        y += 4

        # quantity and postage, which is the only choice the shop offers
        y = choices_y
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
            text(s, clock_str(ship_time(p, m, self.qty)
                              * today(st.played).ship), 14,
                 (r.x + 210, r.centery), mix(TEA, CREAM, 0.2), left=True,
                 kind="mono", shadow=False)
            fee_v = ship_cost(p, self.qty, m, unit)
            text(s, "free" if fee_v <= 0 else "+" + money(fee_v), 14,
                 (r.right - 12, r.centery), GOOD if fee_v <= 0 else EMBER,
                 right=True, kind="mono", shadow=False)
            self.buttons.append(Button(r, "", ("mode", m), "hit"))
            y += 38
        text(s, SHIPPING[self.mode][1].lower() + " - " + SHIPPING[self.mode][4],
             12, (right.x + 112, y - 2), DIM, kind="mono", shadow=False)

        # the total, and the one button that spends money
        total = unit * self.qty + ship_cost(p, self.qty, self.mode, unit)
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

    # -- things for the flat ------------------------------------------------
    def draw_home(self, s, body):
        """Eight things that are not cards, in a column you work down."""
        st = self.state
        text(s, f"the flat is at {int(round(st.comfort * 100 - 100))}% "
                f"over bare boards", 15, (body.x, body.y),
             warm(EMBER, 0.2), kind="mono")
        text(s, "Every one of these is bought once, turns up in a room, "
                "and makes every cat in the flat earn a little more.", 13,
             (body.x, body.y + 22), MUTED, kind="mono", max_w=body.w)
        top = body.y + 52
        rowh = (body.bottom - top) // 4
        for i, u in enumerate(UPGRADES):
            col, row = divmod(i, 4)
            r = pygame.Rect(body.x + col * (body.w // 2 + 8),
                            top + row * rowh, body.w // 2 - 16, rowh - 10)
            have = u.key in st.things
            panel(s, r, mix(SCREEN_HI, EMBER, 0.12 if have else 0.03),
                  shade(EMBER, 0.7) if have else shade(SCREEN_HI, 1.4),
                  radius=8, shadow=False)
            text(s, u.name, 18, (r.x + 14, r.y + 8),
                 warm(CREAM, 0.2) if have else CREAM, max_w=r.w - 120)
            paragraph(s, u.blurb, 12, (r.x + 14, r.y + 30), MUTED,
                      r.w - 130, 3, kind="mono")
            text(s, f"+{u.gain * 100:.0f}%", 15, (r.right - 14, r.y + 14),
                 GOOD if have else mix(TEA, CREAM, 0.2), right=True,
                 kind="mono")
            if have:
                text(s, "IN THE FLAT", 12, (r.right - 14, r.bottom - 18),
                     GOOD, right=True, kind="mono")
            else:
                text(s, money(u.price), 20, (r.right - 116, r.bottom - 32),
                     warm(EMBER, 0.2), right=True)
                self.buttons.append(Button(
                    (r.right - 104, r.bottom - 42, 90, 30), "BUY",
                    ("thing", u.key), "solid", 15, kind="mono",
                    enabled=st.money >= u.price))

    # -- things for the cards ------------------------------------------
    def draw_merch(self, s, body):
        """Six small things, in a column you work down. None of them is a
        decision; all of them are worth having."""
        st = self.state
        bits = []
        if st.gear > 1.001:
            bits.append(f"+{(st.gear - 1) * 100:.0f}% a second")
        if st.shiny_gear > 1.001:
            bits.append(f"shinies one in {SHINY_IN / st.shiny_gear:.0f}")
        if st.resale_gear < 0.999:
            bits.append(f"{(1 - st.resale_gear) * 100:.0f}% off resale")
        if st.has_loupe:
            bits.append("one wrong answer at the desk")
        text(s, "   ".join(bits) if bits else "nothing but a shoebox so far",
             15, (body.x, body.y), warm(EMBER, 0.2), kind="mono",
             max_w=body.w - 20)
        text(s, "For the cards rather than the cats. Bought once, and they "
                "apply to the whole collection.", 13, (body.x, body.y + 22),
             MUTED, kind="mono", max_w=body.w)
        top = body.y + 52
        rowh = (body.bottom - top) // 3
        for i, m in enumerate(MERCH):
            col, row = divmod(i, 3)
            r = pygame.Rect(body.x + col * (body.w // 2 + 8),
                            top + row * rowh, body.w // 2 - 16, rowh - 10)
            have = m.key in st.kit
            panel(s, r, mix(SCREEN_HI, EMBER, 0.12 if have else 0.03),
                  shade(EMBER, 0.7) if have else shade(SCREEN_HI, 1.4),
                  radius=8, shadow=False)
            text(s, m.name, 18, (r.x + 14, r.y + 8),
                 warm(CREAM, 0.2) if have else CREAM, max_w=r.w - 130)
            paragraph(s, m.blurb, 12, (r.x + 14, r.y + 30), MUTED,
                      r.w - 130, 3, kind="mono")
            text(s, m.effect, 14, (r.right - 14, r.y + 14),
                 GOOD if have else mix(TEA, CREAM, 0.2), right=True,
                 kind="mono")
            if have:
                text(s, "IN THE BOX ROOM", 12, (r.right - 14, r.bottom - 18),
                     GOOD, right=True, kind="mono")
            else:
                text(s, money(m.price), 20, (r.right - 116, r.bottom - 32),
                     warm(EMBER, 0.2), right=True)
                self.buttons.append(Button(
                    (r.right - 104, r.bottom - 42, 90, 30), "BUY",
                    ("merch", m.key), "solid", 15, kind="mono",
                    enabled=st.money >= m.price))

    # -- the wall at the end of the cat room ---------------------------
    def draw_room_page(self, s, body):
        """Four rooms, in order, and the only things in the shop that are
        not for the cats to use but for you to watch them use."""
        st = self.state
        text(s, "WHAT THE FLAT BECOMES", 22, (body.x, body.y),
             warm(CREAM, 0.2))
        text(s, "Bought in order, one wall at a time. Not one of them "
                "earns a penny; what they buy is room, and cats to put in "
                "it.", 13, (body.x, body.y + 28), MUTED, kind="mono",
             max_w=body.w - 20)
        top = body.y + 56
        rowh = (body.bottom - top) // len(WINGS)
        for i, w in enumerate(WINGS):
            r = pygame.Rect(body.x, top + i * rowh, body.w - 8, rowh - 8)
            have = i < st.wings
            nxt = i == st.wings
            panel(s, r, mix(SCREEN_HI, EMBER,
                            0.14 if have else 0.06 if nxt else 0.02),
                  shade(EMBER, 0.7) if have else
                  shade(SCREEN_HI, 1.4) if nxt else shade(SCREEN_HI, 1.1),
                  radius=9, shadow=False)
            head = warm(CREAM, 0.2) if have else CREAM if nxt else MUTED
            text(s, w.name, 19, (r.x + 18, r.y + 10), head, max_w=r.w - 230)
            paragraph(s, w.blurb, 12, (r.x + 18, r.y + 34),
                      MUTED if nxt or have else shade(MUTED, 0.75),
                      r.w - 260, 3, kind="mono")
            cap_to = ROOM_CAP + sum(x.cap for x in WINGS[:i + 1])
            text(s, f"+{w.cap} cats, to {cap_to}    +{w.spots} places"
                    f"    +{w.wide} across", 12,
                 (r.x + 18, r.bottom - 22),
                 GOOD if have else mix(TEA, CREAM, 0.25) if nxt
                 else shade(MUTED, 0.8), kind="mono")
            if have:
                text(s, "DONE", 15, (r.right - 20, r.y + 16), GOOD,
                     right=True, kind="mono")
            elif nxt:
                text(s, money(w.price), 22, (r.right - 150, r.y + 22),
                     warm(EMBER, 0.2), right=True)
                self.buttons.append(Button(
                    (r.right - 140, r.y + 10, 120, 36), "TAKE IT",
                    ("bigroom", None), "solid", 16, kind="mono",
                    enabled=st.money >= w.price))
            else:
                text(s, money(w.price), 16, (r.right - 20, r.y + 20),
                     shade(MUTED, 0.85), right=True, kind="mono")
                text(s, "the one above first", 11,
                     (r.right - 20, r.y + 40), shade(MUTED, 0.7),
                     right=True, kind="mono")

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
# A parcel is not a heap. Twenty cards to a pack and twenty packs to a
# box, the way trading cards have always been sold - and the reason it is
# done that way is the reason it is done here: a hundred and seventy
# cards dealt onto one table is not an opening, it is a wall, and you
# cannot see a single one of them. You open a pack. Then you open the
# next pack.
PACK_SIZE = 20
BOX_PACKS = 20


def packs_in(cards):
    """How many packs a number of cards comes to."""
    return max(1, (cards + PACK_SIZE - 1) // PACK_SIZE)


def parcel_words(cards):
    """What is in the parcel, said in boxes and packs."""
    packs = packs_in(cards)
    boxes, rest = divmod(packs, BOX_PACKS)
    bits = []
    if boxes:
        bits.append(f"{boxes} box" + ("es" if boxes > 1 else ""))
    if rest or not boxes:
        bits.append(f"{rest or packs} pack" + ("s" if (rest or packs) > 1
                                               else ""))
    return " and ".join(bits)


def pack_label(index, cards):
    """Where you are in the parcel: pack 3 of 9, or box 2, pack 3 of 20."""
    packs = packs_in(cards)
    if packs <= 1:
        return ""
    if packs <= BOX_PACKS:
        return f"pack {index + 1} of {packs}"
    box, within = divmod(index, BOX_PACKS)
    left = min(BOX_PACKS, packs - box * BOX_PACKS)
    return (f"box {box + 1} of {packs_in(cards) // BOX_PACKS + 1}"
            f"   pack {within + 1} of {left}")


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
        if self.cut and len(self.pulls) > PACK_SIZE:
            text(s, parcel_words(len(self.pulls)), 13, (W // 2, 72), MUTED,
                 center=True, kind="mono")

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

        here = self.this_pack()
        label = pack_label(self.pack_i, len(self.pulls))
        if label:
            text(s, label, 15, (W // 2, 90), TEA, center=True, kind="mono")
        area = pygame.Rect(90, 116, W - 180, 492)
        rects = deal_grid(len(here), area)
        dealt = int(self.deal * len(here) * 1.8) + 1
        for i, (p, r) in enumerate(zip(here, rects)):
            if i >= dealt:
                continue
            if i < self.flipped:
                card = self.state.cards.get(p.breed.key)
                pop = 1.0
                if i == self.flipped - 1:
                    pop = 1.0 + 0.06 * max(0.0, math.sin(self.t * 9) * 0.4)
                rr = r.inflate(int(r.w * (pop - 1)), int(r.h * (pop - 1)))
                if p.shiny:
                    glow(s, rr.center, int(rr.w * 1.25),
                         mix(LAMP, CREAM, 0.25),
                         0.30 + 0.08 * math.sin(self.t * 4))
                elif p.breed.rarity >= R_RARE:
                    glow(s, rr.center, int(rr.w * 0.9),
                         rarity_colour(p.breed.rarity), 0.22)
                draw_card(s, rr, p.breed, p.level,
                          card.dupes if card else 0,
                          maxed=bool(card and card.maxed),
                          variant=p.coat, shiny=p.shiny or
                          bool(card and card.shiny and p.coat == card.coat))
                word, col = KIND_WORDS[p.kind]
                if p.kind == "dupe" and card and card.maxed:
                    word, col = KIND_WORDS["maxed"]
                if p.shiny:
                    word, col = "SHINY", mix(LAMP, CREAM, 0.3)
                elif p.new_coat and p.kind != "new" and len(p.breed.coats) > 1:
                    word, col = "NEW COAT", GOOD
                lab = word
                if p.shiny or (p.new_coat and p.kind != "new"
                               and len(p.breed.coats) > 1):
                    pass
                elif p.kind == "level":
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

        left = len(here) - self.flipped
        more = (self.pack_i + 1) * PACK_SIZE < len(self.pulls)
        if left:
            self.buttons.append(Button((W // 2 - 230, H - 86, 210, 48),
                                       "FLIP ONE", ("flip", self.flipped),
                                       "plain", 18, kind="mono"))
            self.buttons.append(Button((W // 2 + 20, H - 86, 210, 48),
                                       f"FLIP ALL {left}", ("flipall", None),
                                       "solid", 18, kind="mono"))
        elif more:
            done = (self.pack_i + 1) * PACK_SIZE
            news = sum(1 for p in self.pulls[:done] if p.kind == "new")
            shn = sum(1 for p in self.pulls[:done] if p.shiny)
            bits = [f"{done} of {len(self.pulls)} cards"]
            if news:
                bits.append(f"{news} new")
            if shn:
                bits.append(f"{shn} SHINY")
            text(s, "   ".join(bits), 16, (W // 2, H - 104), TEA,
                 center=True, kind="mono")
            self.buttons.append(Button((W // 2 - 150, H - 86, 300, 48),
                                       "THE NEXT PACK", ("nextpack", None),
                                       "solid", 19, kind="mono"))
        else:
            news = sum(1 for p in self.pulls if p.kind == "new")
            ups = sum(1 for p in self.pulls if p.kind == "level")
            shn = sum(1 for p in self.pulls if p.shiny)
            coats = sum(1 for p in self.pulls
                        if p.new_coat and p.kind != "new")
            bits = []
            if shn:
                bits.append(f"{shn} SHINY")
            if news:
                bits.append(f"{news} new")
            if coats:
                bits.append(f"{coats} new coat{'s' if coats > 1 else ''}")
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
        shiny_n = sum(1 for c in st.cards.values() if c.shiny)
        strays_n = st.strays_owned
        expo_n = st.expo_owned
        text(s, f"{st.owned} of {len(st.book)} breeds    "
                + (f"{expo_n} from the hall    " if expo_n else "")
                + (f"{strays_n} stray{'s' if strays_n > 1 else ''}    "
                   if strays_n else "")
                + f"{st.retired} retired"
                + (f"    {shiny_n} shiny" if shiny_n else "")
                + f"    {rate_soft(st.income)}", 15,
             (inner.right - 20, inner.y + 22), TEA, right=True, kind="mono")
        hairline(s, inner.x + 20, inner.y + 46, inner.right - 20, TEA, 60)

        # Eighteen to a spread, which is a spread. The twenty-four
        # breeds this started with went on one page because paging a
        # binder to look at six more cats is not what a binder is for;
        # thirty-six do not fit at a size you can tell them apart at.
        # 500 and not 540: the third row has to end clear of the page
        # buttons, which `cat_test.py layout` is what noticed
        area = pygame.Rect(inner.x + 20, inner.y + 58, inner.w - 40, 500)
        cols, rows, gap, vgap = 8, 3, 12, 18
        per = cols * rows
        # The last page does not exist until one of them is standing on
        # the mat. An empty page of question marks would say "there are
        # five more of these", which is the one thing it must not say.
        found = [b for b in SECRETS if b.key in st.cards]
        book = st.book
        book_pages = (len(book) + per - 1) // per
        pages = book_pages + 1 + (1 if found else 0)
        self.page = int(clamp(self.page, 0, pages - 1))
        expo_page = self.page == book_pages
        secret_page = bool(found) and self.page == pages - 1
        cw = (area.w - (cols - 1) * gap) // cols
        ch = int(cw * 1.4)
        gx = area.centerx - (cols * cw + (cols - 1) * gap) // 2
        gy = area.centery - (rows * ch + (rows - 1) * vgap) // 2
        shown = (found if secret_page else
                 list(EXPO_BREEDS) if expo_page else
                 book[self.page * per:(self.page + 1) * per])
        if expo_page:
            got = st.expo_owned
            text(s, "PRINTED FOR THE HALL", 20, (inner.centerx, area.y + 10),
                 rarity_colour(R_EXPO), center=True, kind="mono")
            text(s, f"{got} of {len(EXPO_BREEDS)} - the show prints these "
                    f"and nobody else is allowed to", 13,
                 (inner.centerx, area.y + 38), MUTED, center=True,
                 kind="mono")
            gx = area.centerx - (len(shown) * cw + (len(shown) - 1) * gap) // 2
            gy = area.y + 86
        elif secret_page:
            text(s, "NOT IN THE CATALOGUE", 20, (inner.centerx, area.y + 10),
                 mix(LAMP, CREAM, 0.35), center=True, kind="mono")
            text(s, f"{len(found)} that turned up at the door, and were "
                    f"let in", 13, (inner.centerx, area.y + 38), MUTED,
                 center=True, kind="mono")
            # a short row, centred, under its own heading
            gx = area.centerx - (len(shown) * cw + (len(shown) - 1) * gap) // 2
            gy = area.y + 86
        for i, b in enumerate(shown):
            r, c = divmod(i, cols)
            rect = pygame.Rect(gx + c * (cw + gap), gy + r * (ch + vgap),
                               cw, ch)
            card = st.cards.get(b.key)
            if card:
                draw_card(s, rect, b, card.level, card.dupes, card.maxed,
                          variant=card.coat, shiny=card.shiny)
            else:
                draw_unknown(s, rect, b)
            self.buttons.append(Button(rect, "", ("pick", b.key), "hit"))
            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(s, mix(EMBER, LAMP, 0.3), rect.inflate(6, 6),
                                 width=2, border_radius=8)

        for i in range(pages):
            r = pygame.Rect(inner.centerx - (pages * 90) // 2 + i * 90,
                            inner.bottom - 96, 80, 30)
            on = self.page == i
            last = found and i == pages - 1
            expo = i == book_pages
            lab = ("strays" if last else "the hall" if expo
                   else f"page {i + 1}")
            self.buttons.append(Button(r, lab, ("page", i),
                                       "solid" if on else "plain", 14,
                                       kind="mono",
                                       colour=mix(LAMP, CREAM, 0.3) if last
                                       else rarity_colour(R_EXPO) if expo
                                       else None))
        left = [b for b in book if b.key not in st.cards]
        if expo_page:
            short = [b for b in EXPO_BREEDS if b.key not in st.cards]
            note = ("every one of them, and not one by post"
                    if not short else
                    f"{len(short)} still to find, and only one place to "
                    f"look")
        elif secret_page:
            note = ("five of them have been seen in this city"
                    if len(found) < len(SECRETS)
                    else "all five, and not one of them was ordered")
        elif st.complete:
            note = "every breed retired - the catalogue has nothing left"
        elif left:
            note = (f"{len(left)} still to find, the rarest of them "
                    f"{a_rarity(max(b.rarity for b in left))}")
        else:
            note = (f"{len(book) - st.retired} still to take to level 10")
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
        r = pygame.Rect(W // 2 - 380, H // 2 - 236, 760, 472)
        acc = rarity_colour(b.rarity)
        panel(s, r, mix(DEEP, acc, 0.06), shade(acc, 0.6), radius=12)
        glow(s, (r.x + 150, r.centery), 220, acc, 0.14)
        cr = pygame.Rect(r.x + 36, r.centery - 160, 212, 296)
        if card:
            draw_card(s, cr, b, card.level, card.dupes, card.maxed,
                      variant=card.coat, shiny=card.shiny)
        else:
            draw_unknown(s, cr, b)

        x = cr.right + 36
        text(s, b.name, 34, (x, r.y + 30), warm(CREAM, 0.2))
        text(s, rarity_name(b.rarity), 15, (x, r.y + 74), acc, kind="mono")
        text(s, "from " + b.origin, 14, (x + 150, r.y + 74), MUTED,
             kind="mono", shadow=False)
        paragraph(s, b.note, 16, (x, r.y + 104), mix(TEA, CREAM, 0.35),
                  r.right - x - 40, 5)
        text(s, "TEMPERAMENT", 12, (x, r.y + 160), TEA, kind="mono",
             shadow=False)
        text(s, b.temperament["label"], 15, (x + 124, r.y + 158),
             warm(EMBER, 0.2), kind="mono")
        paragraph(s, b.habit, 13, (x, r.y + 182), MUTED,
                  r.right - x - 40, 4, kind="mono")
        y = r.y + 230
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
            if len(b.coats) > 1:
                text(s, f"COATS  {card.coats_seen(b)} of {len(b.coats)}", 12,
                     (x, y + 146), TEA, kind="mono", shadow=False)
                sx = x + 120
                for i, cname in enumerate(b.coats):
                    got = card.seen >> i & 1
                    col = coat_colours(b, i)[0]
                    sw = pygame.Rect(sx, y + 142, 20, 20)
                    pygame.draw.rect(s, col if got else shade(DEEP, 1.4), sw,
                                     border_radius=4)
                    pygame.draw.rect(s, mix(col, INK, 0.4) if got
                                     else shade(TEA, 0.4), sw, width=1,
                                     border_radius=4)
                    if i == card.coat and not card.shiny:
                        pygame.draw.rect(s, warm(CREAM, 0.1),
                                         sw.inflate(6, 6), width=1,
                                         border_radius=5)
                    sx += 26
                if card.shiny:
                    sw = pygame.Rect(sx + 6, y + 142, 20, 20)
                    pygame.draw.rect(s, shiny_coat(b)[1][0], sw,
                                     border_radius=4)
                    pygame.draw.rect(s, warm(CREAM, 0.1), sw.inflate(6, 6),
                                     width=1, border_radius=5)
                    text(s, coat_name(b, card.coat, True, full=True), 11,
                         (sw.right + 8, sw.centery), mix(LAMP, CREAM, 0.3),
                         left=True, kind="mono", shadow=False)
                else:
                    text(s, coat_name(b, card.coat), 11,
                         (x + 120, y + 168), MUTED, kind="mono",
                         shadow=False)
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
# THREE SMALL GAMES
#
# None of them is a game in its own right; each is a thing you have to do
# with your hands before the hall will give you a pack it would not sell
# you. They are deliberately short - a convention lasts six minutes and
# there are three tables - and every one of them can be lost.
# ---------------------------------------------------------------------------
class Mini:
    """The state of whichever game is being played."""
    __slots__ = ("kind", "stall", "stage", "rounds", "won", "lost", "t",
                 "pos", "dir", "band", "cards", "pick", "secret", "guess",
                 "tries", "said", "done", "spare", "bid", "rival",
                 "ask", "opts", "right")

    def __init__(self, kind, stall, rng, state):
        self.kind = kind
        self.stall = stall
        self.stage = 0
        self.rounds = {"queue": 3, "fake": 2, "quiz": 3}.get(kind, 1)
        self.won = 0
        self.lost = False
        self.done = False
        # the loupe is worth exactly one mistake, and only at the desk
        self.spare = 1 if (kind == "fake" and state.has_loupe) else 0
        self.t = 0.0
        self.pos = 0.0
        self.dir = 1.0
        self.band = 0.30
        self.cards = []
        self.pick = -1
        self.said = ""
        self.tries = 5
        self.secret = rng.randrange(20, 81)
        self.guess = 50
        # the auction: what it stands at, and how deep the room is
        self.bid = 0
        self.rival = rng.uniform(0.55, 0.85)
        # the quiz: a question, four answers and which one is right
        self.ask = ""
        self.opts = []
        self.right = 0
        if kind == "fake":
            self.deal_fakes(rng, state)
        elif kind == "quiz":
            self.set_question(rng, state)

    # -- spot the fake --------------------------------------------------
    def deal_fakes(self, rng, state):
        """Four of a breed, three of them wrong in one small way each."""
        pool = [b for b in BREEDS if b.rarity >= R_RARE] or list(BREEDS)
        b = rng.choice(pool)
        tells = rng.sample(("rarity", "name", "rate"), 3)
        self.cards = [{"breed": b, "tell": None}]
        for tell in tells:
            self.cards.append({"breed": b, "tell": tell})
        rng.shuffle(self.cards)
        self.pick = -1

    # -- the quiz --------------------------------------------------------
    def set_question(self, rng, state):
        """One question about the catalogue, with four cats under it.

        The answer is in the binder, which is the point: this is the one
        table that pays out for having read the thing you have spent the
        whole game filling in.
        """
        pool = [b for b in BREEDS if b.rarity >= R_RARE]
        four = rng.sample(pool, 4)
        pick = rng.randrange(3)
        if pick == 0:
            self.ask = "Which of these is the rarest?"
            best = max(four, key=lambda b: b.rarity)
            self.right = four.index(best)
            if sum(1 for b in four if b.rarity == best.rarity) > 1:
                self.ask = "Which of these earns the most at level one?"
                best = max(four, key=lambda b: b.base_rate)
                self.right = four.index(best)
        elif pick == 1:
            self.ask = "Which of these is the most ordinary?"
            worst = min(four, key=lambda b: b.rarity)
            self.right = four.index(worst)
            if sum(1 for b in four if b.rarity == worst.rarity) > 1:
                self.ask = "Which of these earns the least at level one?"
                worst = min(four, key=lambda b: b.base_rate)
                self.right = four.index(worst)
        else:
            want = rng.choice(four)
            self.ask = f"Which of these is {a_rarity(want.rarity)}?"
            same = [b for b in four if b.rarity == want.rarity]
            if len(same) > 1:
                four = rng.sample([b for b in pool
                                   if b.rarity != want.rarity], 3) + [want]
                rng.shuffle(four)
            self.right = four.index(want)
        self.opts = four

    def real_index(self):
        return next(i for i, c in enumerate(self.cards) if c["tell"] is None)

    # -- time ------------------------------------------------------------
    def update(self, dt):
        self.t += dt
        if self.kind == "queue" and not self.done:
            speed = 0.78 + 0.26 * self.stage
            self.pos += self.dir * speed * dt
            if self.pos > 1.0:
                self.pos, self.dir = 1.0, -1.0
            elif self.pos < 0.0:
                self.pos, self.dir = 0.0, 1.0

    def band_rect(self):
        half = self.band * 0.5 * (1.0 - 0.22 * self.stage)
        return 0.5 - half, 0.5 + half


MINI_TITLE = {"queue": "GET TO THE TABLE", "fake": "WHICH ONE IS REAL",
              "haggle": "TALK HIM DOWN", "auction": "BID FOR IT",
              "quiz": "THREE QUESTIONS"}

AUCTION_STEP = 1200        # what one raise costs
AUCTION_FLOOR = 2400       # where the bidding opens


# ---------------------------------------------------------------------------
# THE TWO OVERLAYS
#
# A pause card, which is also where the rules are written down, and an
# ending, which is the only screen in the game you cannot get back to.
# ---------------------------------------------------------------------------
RULES = (
    ("the laptop", "Order boxes. Six on the ladder, four more on the "
                   "specials page, and slow post is free."),
    ("duplicates", "Two of a breed take it to level 2, four more to 3, "
                   "six to 4, and so on by twos."),
    ("every level", "Better paper, a brighter frame, and a cat in better "
                    "condition. A collar at 4, a tag at 7, a bell at 10."),
    ("coats", "Every breed comes in two to four. The binder remembers "
              "each one you have seen, and one card in 150 is a shiny."),
    ("level 10", "The breed retires. The shop takes it off the page and "
                 "will never send it again."),
    ("the post", "Four parcels at a time. The delivery club is the only "
                 "thing that raises it."),
    ("the flat", "The website also sells furniture. Each piece turns up "
                 "in a room and every cat in the place earns more."),
    ("the flat", "Three rooms: the hall where the post lands, the desk, "
                 "and the cat room. A and D, or click the names."),
    ("the cat room", "Twice as wide as the window. The ten you have taken "
                     "furthest live there and run their own day."),
    ("temperament", "Every breed has one, and it decides what that cat "
                    "does with its day. Click a cat to see it."),
)


class MenuMixin:
    def draw_intro(self, s):
        """One screen at a time, with the light coming up as it goes."""
        beat = int(clamp(self.beat, 0, len(INTRO) - 1))
        lit = (beat + min(1.0, self.beat_t / 1.1)) / len(INTRO)
        _intro_room(s, self.t, beat, lit)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 120))
        s.blit(dim, (0, 0))

        head, body = INTRO[beat]
        money_s = money(START_MONEY)
        head = head.format(money=money_s)
        body = body.format(money=money_s)
        fade = int(255 * min(1.0, self.beat_t / 0.75))
        r = pygame.Rect(W // 2 - 330, 150, 660, 180)
        text(s, head, 30, (r.centerx, r.y), warm(CREAM, 0.2), center=True,
             alpha=fade, max_w=r.w)
        paragraph(s, body, 16, (r.x, r.y + 44), mix(TEA, CREAM, 0.25), r.w,
                  4, kind="mono", center=True, alpha=fade)

        for i in range(len(INTRO)):
            d = pygame.Rect(48 + i * 18, H - 56, 10, 10)
            pygame.draw.rect(s, warm(CREAM, 0.1) if i <= beat
                             else shade(TEA, 0.45), d, border_radius=5)
        last = beat == len(INTRO) - 1
        self.buttons.append(Button((W - 266, H - 74, 226, 46),
                                   "ORDER A PACK" if last else "NEXT",
                                   ("intro", "next"), "solid", 18,
                                   kind="mono"))
        if not last:
            self.buttons.append(Button((W - 150, 26, 120, 30),
                                       "skip this", ("intro", "skip"),
                                       "link", 14, kind="mono", colour=TEA))

    def draw_news(self, s):
        """The three screens that announce a collection. Which collection
        is `news_for`; the screens are its own."""
        show = BY_SERIES.get(self.news_for)
        if show is None or not show.news:
            self.go("room")
            return
        NEWS = show.news
        beat = int(clamp(self.beat, 0, len(NEWS) - 1))
        f = min(1.0, self.beat_t / 1.4)
        _news_scene(s, self.t, beat, f, show.cats)
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 96))
        s.blit(dim, (0, 0))
        head, body = NEWS[beat]
        fade = int(255 * min(1.0, self.beat_t / 0.8))
        r = pygame.Rect(W // 2 - 340, 92, 680, 160)
        text(s, head, 32, (r.centerx, r.y), warm(CREAM, 0.2), center=True,
             alpha=fade, max_w=r.w)
        paragraph(s, body, 16, (r.x, r.y + 46), mix(TEA, CREAM, 0.25), r.w,
                  4, kind="mono", center=True, alpha=fade)
        for i in range(len(NEWS)):
            d = pygame.Rect(48 + i * 18, H - 56, 10, 10)
            pygame.draw.rect(s, warm(CREAM, 0.1) if i <= beat
                             else shade(TEA, 0.45), d, border_radius=5)
        last = beat == len(NEWS) - 1
        self.buttons.append(Button((W - 266, H - 74, 226, 46),
                                   "GO AND LOOK" if last else "NEXT",
                                   ("news", "next"), "solid", 18,
                                   kind="mono"))
        if not last:
            self.buttons.append(Button((W - 150, 26, 120, 30),
                                       "skip this", ("news", "skip"),
                                       "link", 14, kind="mono", colour=TEA))

    def news_next(self):
        show = BY_SERIES.get(self.news_for)
        NEWS = show.news if show else ()
        if not NEWS or self.beat >= len(NEWS) - 1:
            self.end_news()
            return
        self.beat += 1
        self.beat_t = 0.0
        self.beep("page")

    def end_news(self):
        show = BY_SERIES.get(self.news_for)
        if show is not None:
            self.state.told.add(show.key)
            self.toast(f"{show.name} is up",
                       f"a new page on the website, and {len(show.cats)} "
                       f"empty slots in the binder",
                       mix(LAMP, CREAM, 0.3), 14.0)
        self.news_for = None
        self.go("room")
        self.go_area("study", quiet=True)
        self.save()

    def intro_next(self):
        if self.beat >= len(INTRO) - 1:
            self.end_intro()
            return
        self.beat += 1
        self.beat_t = 0.0
        self.beep("page")

    def end_intro(self):
        self.state.seen_intro = True
        self.go("room")
        self.go_area("study", quiet=True)
        self.toast("ten pounds and a laptop",
                   "the shop is on the desk - order a paper sack",
                   mix(LAMP, CREAM, 0.3), 14.0)
        self.save()

    def draw_mini(self, s):
        """Whichever of the three is being played, on the hall behind it."""
        m = self.mini
        if m is None:
            self.go("room")
            return
        self.draw_room(s)
        del self.buttons[:]
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((8, 6, 6, 212))
        s.blit(dim, (0, 0))
        stall = next(x for x in STALLS if x[0] == m.stall)
        r = pygame.Rect(W // 2 - 400, 110, 800, 480)
        panel(s, r, mix(DEEP, WOOD, 0.3), shade(TEA, 0.5), radius=12)
        text(s, MINI_TITLE[m.kind], 30, (r.centerx, r.y + 20),
             warm(CREAM, 0.2), center=True)
        text(s, stall[2], 13, (r.centerx, r.y + 58), TEA, center=True,
             kind="mono")
        paragraph(s, stall[5], 14, (r.x + 60, r.y + 84),
                  mix(TEA, CREAM, 0.3), r.w - 120, 5, kind="mono",
                  center=True)

        if m.kind == "queue":
            self._mini_queue(s, m, r)
        elif m.kind == "fake":
            self._mini_fake(s, m, r)
        elif m.kind == "auction":
            self._mini_auction(s, m, r)
        elif m.kind == "quiz":
            self._mini_quiz(s, m, r)
        else:
            self._mini_haggle(s, m, r)

        if m.done:
            won = not m.lost and m.won >= m.rounds
            if m.kind == "auction":
                word = ("going, going, gone" if won
                        else "somebody else wanted it more")
            elif m.kind == "quiz":
                word = ("three out of three" if won
                        else "he looks almost sorry")
            elif m.kind == "haggle":
                word = ("he shakes on it" if won
                        else "he will not come down")
            else:
                word = "you got one" if won else "the table is cleared out"
            text(s, word, 22, (r.centerx, r.bottom - 92),
                 GOOD if won else BAD, center=True)
            self.buttons.append(Button((r.centerx - 120, r.bottom - 62, 240,
                                        44), "LEAVE THE TABLE",
                                       ("mini", "leave"), "solid", 18,
                                       kind="mono"))

    def _mini_queue(self, s, m, r):
        """A rope with one gap in it, and you going up and down the line
        looking for it. Every round the line moves faster and the gap gets
        narrower, which is roughly what being four hundredth in a queue of
        four hundred feels like."""
        bar = pygame.Rect(r.x + 90, r.y + 248, r.w - 180, 30)
        lo, hi = m.band_rect()
        win = pygame.Rect(bar.x + bar.w * lo, bar.y, bar.w * (hi - lo), bar.h)
        rng = random.Random(5)
        x = bar.x + 6
        while x < bar.right:
            through = win.x - 8 < x < win.right + 8
            _person(s, x, bar.y - 6, 54,
                    mix((76, 68, 72), WOOD, 0.3 if through else 0.0),
                    0.0 if through else m.t, rng.random() * 9)
            x += rng.uniform(26, 38)
        pygame.draw.rect(s, shade(DEEP, 1.5), bar, border_radius=8)
        pygame.draw.rect(s, mix(GOOD, DEEP, 0.4), win, border_radius=8)
        pygame.draw.rect(s, GOOD, win, width=2, border_radius=8)
        text(s, "THE GAP", 11, (win.centerx, bar.bottom + 6), GOOD,
             center=True, kind="mono")
        ry = bar.y + 4            # the rope, over the top of them
        pygame.draw.line(s, shade(WOOD_HI, 0.9), (bar.x, ry), (win.x, ry), 3)
        pygame.draw.line(s, shade(WOOD_HI, 0.9), (win.right, ry),
                         (bar.right, ry), 3)
        x = bar.x + bar.w * m.pos
        pygame.draw.rect(s, warm(CREAM, 0.1), (x - 3, bar.y - 16, 6,
                                               bar.h + 26), border_radius=3)
        pygame.draw.circle(s, warm(CREAM, 0.1), (int(x), int(bar.y - 22)), 7)
        text(s, f"round {min(m.stage + 1, m.rounds)} of {m.rounds}"
                f"    {m.won} through", 14, (r.centerx, bar.bottom + 34),
             TEA, center=True, kind="mono")
        text(s, "stop on the gap three times and you are at the table", 13,
             (r.centerx, bar.bottom + 56), MUTED, center=True, kind="mono")
        if not m.done:
            self.buttons.append(Button((r.centerx - 110, r.bottom - 112, 220,
                                        52), "NOW", ("mini", "stop"),
                                       "solid", 22, kind="mono"))

    def _mini_fake(self, s, m, r):
        """Four of one breed. Three came off somebody's printer, and each
        of those three is wrong in one printed line - so every row has an
        odd one out, and the card with no odd line on it is the real one."""
        cw, gap = 150, 22
        gx = r.centerx - (4 * cw + 3 * gap) // 2
        for i, c in enumerate(m.cards):
            rect = pygame.Rect(gx + i * (cw + gap), r.y + 148, cw, 206)
            draw_card(s, rect, c["breed"], 6, dupes=2, fake=c["tell"])
            self.buttons.append(Button(rect, "", ("mini", i), "hit"))
            if rect.collidepoint(pygame.mouse.get_pos()) and not m.done:
                pygame.draw.rect(s, warm(CREAM, 0.1), rect.inflate(8, 8),
                                 width=2, border_radius=9)
        text(s, "the name, the tier, the rate - a forgery gets one of the "
                "three wrong", 13, (r.centerx, r.y + 368), MUTED,
             center=True, kind="mono")
        if m.spare:
            text(s, "the loupe is good for one wrong answer", 13,
                 (r.centerx, r.y + 408), GOOD, center=True, kind="mono")
        text(s, f"round {min(m.stage + 1, m.rounds)} of {m.rounds}", 14,
             (r.centerx, r.y + 390), TEA, center=True, kind="mono")

    def _mini_auction(self, s, m, r):
        """The room bids against you. Every raise is money you will pay
        if nobody goes again, so the game is knowing when it has
        stopped."""
        price = AUCTION_FLOOR + m.bid
        text(s, "the lot stands at", 14, (r.centerx, r.y + 150), TEA,
             center=True, kind="mono")
        can = self.state.money >= price
        text(s, money(price), 54, (r.centerx, r.y + 196),
             warm(CREAM, 0.2) if can else BAD, center=True)
        if not m.done:
            text(s, (f"{m.stage} other" + ("" if m.stage == 1 else "s")
                     + " still bidding") if m.stage else
                 "nobody has gone against you yet", 14,
                 (r.centerx, r.y + 250), MUTED, center=True, kind="mono")
        if m.said and not m.done:
            text(s, m.said, 16, (r.centerx, r.y + 282), EMBER, center=True,
                 kind="mono")
        if not can:
            text(s, "more than you have", 13, (r.centerx, r.y + 312), BAD,
                 center=True, kind="mono")
        if not m.done:
            text(s, "raise again and the room may go with you - stop and "
                    "somebody else takes it", 13, (r.centerx, r.y + 344),
                 MUTED, center=True, kind="mono")
        if not m.done:
            self.buttons.append(Button((r.centerx - 230, r.bottom - 112, 210,
                                        52), f"RAISE {money(AUCTION_STEP)}",
                                       ("mini", "raise"), "solid", 18,
                                       kind="mono"))
            self.buttons.append(Button((r.centerx + 20, r.bottom - 112, 210,
                                        52), "LET IT GO", ("mini", "pass"),
                                       "plain", 18, kind="mono"))

    def _mini_quiz(self, s, m, r):
        """Three questions whose answers are all in the binder."""
        text(s, m.ask, 22, (r.centerx, r.y + 132), warm(CREAM, 0.2),
             center=True, max_w=r.w - 80)
        cw, gap = 150, 22
        gx = r.centerx - (4 * cw + 3 * gap) // 2
        for i, b in enumerate(m.opts):
            rect = pygame.Rect(gx + i * (cw + gap), r.y + 170, cw, 206)
            known = b.key in self.state.cards
            if known:
                card = self.state.cards[b.key]
                draw_card(s, rect, b, card.level, card.dupes,
                          card.maxed, variant=card.coat, shiny=card.shiny)
            else:
                draw_unknown(s, rect, b)
                text(s, b.name, fit(b.name, 15, cw - 16),
                     (rect.centerx, rect.bottom - 30), TEA, center=True)
            self.buttons.append(Button(rect, "", ("mini", i), "hit"))
            if rect.collidepoint(pygame.mouse.get_pos()) and not m.done:
                pygame.draw.rect(s, warm(CREAM, 0.1), rect.inflate(8, 8),
                                 width=2, border_radius=9)
        text(s, f"question {min(m.stage + 1, m.rounds)} of {m.rounds}"
                f"    {m.won} right", 14, (r.centerx, r.y + 390), TEA,
             center=True, kind="mono")
        text(s, "one wrong and he keeps the shelf", 13,
             (r.centerx, r.y + 412), MUTED, center=True, kind="mono")

    def _mini_haggle(self, s, m, r):
        """He has a number in his head. You have five goes at it, and
        whatever you talk him down to is what comes out of your pocket."""
        ask = BY_PACK["scalp"].price * SCALP_MULT
        text(s, f"he is asking {money(ask)}", 20, (r.centerx, r.y + 148),
             BAD, center=True, kind="mono")
        text(s, "your offer", 14, (r.centerx, r.y + 184), TEA, center=True,
             kind="mono")
        text(s, f"{m.guess}%", 54, (r.centerx, r.y + 228), warm(CREAM, 0.2),
             center=True)
        due = ask * m.guess / 100.0
        text(s, f"= {money(due)}", 20, (r.centerx, r.y + 278),
             mix(LAMP, CREAM, 0.3) if self.state.money >= due else BAD,
             center=True, kind="mono")
        if m.said:
            text(s, m.said, 16, (r.centerx, r.y + 308), EMBER, center=True,
                 kind="mono")
        text(s, f"{m.tries} goes left", 14, (r.centerx, r.y + 336), TEA,
             center=True, kind="mono")
        text(s, "run out of goes and he walks - then it is the full "
                "asking price", 13, (r.centerx, r.y + 358), MUTED,
             center=True, kind="mono")
        if not m.done:
            self.buttons.append(Button((r.centerx - 220, r.bottom - 112, 90,
                                        52), "-5", ("mini", "down"),
                                       "plain", 20, kind="mono"))
            self.buttons.append(Button((r.centerx + 130, r.bottom - 112, 90,
                                        52), "+5", ("mini", "up"), "plain",
                                       20, kind="mono"))
            self.buttons.append(Button((r.centerx - 110, r.bottom - 112, 220,
                                        52), "OFFER IT", ("mini", "offer"),
                                       "solid", 20, kind="mono"))

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

        y = r.y + 104
        for name, line in RULES:
            text(s, name, 15, (r.x + 34, y), warm(EMBER, 0.15), kind="mono",
                 max_w=146)
            paragraph(s, line, 13, (r.x + 188, y), mix(TEA, CREAM, 0.3),
                      r.w - 232, 4, kind="mono")
            y += 46
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
                  "Thirty-six breeds, every one of them taken to level ten "
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
                (f"{sum(1 for c in st.cards.values() if c.shiny)}",
                 "of them shiny"),
                (f"{st.strays_owned}", "let in at the door"))
        for i, (big, small) in enumerate(rows):
            x = r.centerx + (i - (len(rows) - 1) / 2) * 136
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
