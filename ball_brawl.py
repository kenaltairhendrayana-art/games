"""
BALL BRAWL
==========
Two balls. One arena. Pick a weapon and take the other one apart.

A versus-fight in the style of those "X vs Y" battle clips: two fighters
bounce around a walled arena, their weapons swing and fire on their own,
damage numbers pop off every hit, and one split bar across the top shows
who is winning. Red can be handed to a player instead of the CPU.

Requirements: pygame-ce (or pygame)  ->  pip install pygame-ce
Run:                                     python ball_brawl.py

There is a campaign too: five shapes on a ladder, each holding a weapon
you do not have yet. Beat one and you keep its prize, in versus as well.
Progress is saved outside the game folder and survives a reinstall.

CONTROLS
  Versus menu
    1 .. 7          the seven base weapons, red / Q .. U for blue
    click           any weapon, including the upgraded ones
    TAB             red fighter: CPU or PLAYER
    O               health orbs on / off
    C               open the campaign
    SPACE           fight
  Campaign
    up / down       choose a level (or 1 .. 9)
    left / right    choose your ball
    TAB             play it yourself, or watch
    C / ESC         back to versus
    SPACE           fight
  Fight  (only when you are the PLAYER)
    WASD / arrows   thrust
    mouse           aim the gun and the bow
    SPACE           dash
  Any time
    P               pause
    F               speed  1x / 2x / 3x
    M               mute
    R               restart the fight
    ESC             back out one screen
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
# THE BOARD
#
# Everything is sized off one window. The HUD owns the top strip, the arena
# owns the rest, and no drawing happens outside those two rectangles.
# ---------------------------------------------------------------------------
W, H = 1040, 760
HUD_H = 124
FPS = 60

# VIEW is the hole in the window you watch through and never changes.
# ARENA is the ground itself, which a level may make several times larger -
# then the view follows the fight around it. Everything physical is in
# arena coordinates; drawing adds the camera offset, same as screen shake.
VIEW = pygame.Rect(20, HUD_H, W - 40, H - HUD_H - 20)
ARENA = VIEW.copy()

BG      = (13, 14, 20)
PANEL   = (21, 23, 33)
GRID    = (29, 32, 45)
WALL    = (92, 100, 126)
INK     = (228, 233, 245)
DIM     = (126, 135, 158)
RED     = (238, 64, 72)
RED_D   = (110, 22, 28)
BLUE    = (58, 148, 246)
BLUE_D  = (20, 62, 124)
GOLD    = (255, 206, 84)
GREEN   = (86, 224, 138)

# Physics. Fighters are always under thrust, so drag and the speed clamp
# are what actually decide how fast the fight looks, not the acceleration.
#
# Billiard movement was tried here and reverted: at a constant speed a
# blade only ever touches in passing, so melee lost every matchup against
# a gun or a bow and the campaign could not be finished. Fighters steer.
ACCEL       = 980.0
PLAYER_ACC  = 1220.0
MAX_SPEED   = 530.0
MIN_SPEED   = 95.0
DRAG        = 0.60
DASH_SPEED  = 980.0
DASH_CD     = 2.2
DASH_TIME   = 0.16
BOUNCE      = 0.94
MAX_HP      = 900.0


# ---------------------------------------------------------------------------
# SMALL TOOLS
# ---------------------------------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def seg_dist(p, a, b):
    """Distance from point p to the segment a-b."""
    ab = b - a
    L2 = ab.length_squared()
    if L2 < 1e-9:
        return (p - a).length()
    t = clamp((p - a).dot(ab) / L2, 0.0, 1.0)
    return (p - (a + ab * t)).length()


def _side(a, b, c):
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def segs_close(a1, a2, b1, b2, rad):
    """Do two segments cross, or pass within rad of each other?

    A bullet covers 13 pixels in a frame and an arrow 17, so a point test
    against a sword blade misses most of the time - everything that moves
    fast is tested along the line it swept, not where it happens to have
    landed.
    """
    d1, d2 = _side(b1, b2, a1), _side(b1, b2, a2)
    d3, d4 = _side(a1, a2, b1), _side(a1, a2, b2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    return min(seg_dist(a1, b1, b2), seg_dist(a2, b1, b2),
               seg_dist(b1, a1, a2), seg_dist(b2, a1, a2)) <= rad


def shape_points(cx, cy, rad, sides, angle):
    """A regular polygon. Campaign enemies are cubes; you are always a ball."""
    return [(cx + math.cos(angle + i * TAU / sides) * rad,
             cy + math.sin(angle + i * TAU / sides) * rad)
            for i in range(sides)]


def unit(v, fallback=(1, 0)):
    L = v.length()
    return v / L if L > 1e-6 else Vector2(fallback)


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
        sh.set_alpha(alpha if alpha < 255 else 150)
        surf.blit(sh, (r.x + 2, r.y + 2))
    surf.blit(img, r)
    return r


_glows = {}


def glow(radius, colour, strength=100):
    """A soft additive disc, cached - used for every light in the game."""
    key = (radius, colour, strength)
    s = _glows.get(key)
    if s is None:
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = max(6, radius // 2)
        for i in range(steps, 0, -1):
            f = i / steps
            a = int(strength * (1.0 - f) ** 2.2)
            pygame.draw.circle(s, (*colour, a), (radius, radius), int(radius * f))
        _glows[key] = s
    return s


def blit_glow(surf, pos, radius, colour, strength=100):
    radius = max(2, int(radius))
    g = glow(radius, colour, strength)
    surf.blit(g, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_ADD)



# ---------------------------------------------------------------------------
# THE CITY
#
# One street corner, from above, at human scale: a fighter is a person, so
# a parked car is longer than it is, a doorway is its own size, and a
# building is six or eight of it across. At that scale a grid of blocks
# will not fit in the arena - what fits is an avenue, a side street, and
# the buildings along them, which is what you would actually see standing
# down there.
#
# Built once into a surface and blitted from then on, from a fixed seed on
# its own random stream: the streets never shimmer between frames, and
# generating them cannot shift the sequence the fight draws from. It all
# stays dark, because a fighter, a tracer and a damage number have to stay
# readable over it.
# ---------------------------------------------------------------------------
ASPHALT   = (22, 23, 30)      # road, darkest
PAVING    = (47, 49, 60)      # pavement, lightest ground
PAVELINE  = (53, 56, 67)
KERB      = (68, 72, 86)
ROADLINE  = (84, 88, 102)
CROSSWALK = (74, 78, 92)
SHADOW    = (15, 16, 22)
PARKLAND  = (25, 40, 31)
ROOFS = ((34, 36, 46), (38, 36, 46), (31, 34, 44), (36, 38, 48))
CARS = ((58, 62, 76), (74, 58, 60), (52, 66, 78), (66, 64, 54), (46, 50, 62))

_city_floors = {}


def _manhole(s, x, y, r=17):
    pygame.draw.circle(s, (32, 34, 42), (x, y), r)
    pygame.draw.circle(s, (54, 57, 68), (x, y), r, 2)
    pygame.draw.circle(s, (48, 51, 62), (x, y), r // 2, 1)


def _grate(s, x, y, flat=True):
    r = pygame.Rect(x - 20, y - 11, 40, 22) if flat else pygame.Rect(x - 11, y - 20, 22, 40)
    pygame.draw.rect(s, (30, 32, 40), r)
    pygame.draw.rect(s, (56, 59, 71), r, 2)
    if flat:
        for k in range(r.left + 5, r.right - 3, 6):
            pygame.draw.line(s, (50, 53, 64), (k, r.top + 4), (k, r.bottom - 4), 1)
    else:
        for k in range(r.top + 5, r.bottom - 3, 6):
            pygame.draw.line(s, (50, 53, 64), (r.left + 4, k), (r.right - 4, k), 1)


def _car(s, r, rng, flat=True):
    """A parked car, longer than a fighter - the clearest scale cue there is."""
    col = CARS[rng.randrange(len(CARS))]
    pygame.draw.rect(s, col, r, border_radius=6)
    pygame.draw.rect(s, mix(col, (0, 0, 0), 0.5), r, 2, border_radius=6)
    glass = mix(col, (16, 20, 30), 0.55)
    if flat:
        pygame.draw.rect(s, glass, r.inflate(-r.w // 2, -10), border_radius=3)
        pygame.draw.line(s, mix(col, (210, 216, 230), 0.3),
                         (r.left + 6, r.centery), (r.right - 6, r.centery), 1)
    else:
        pygame.draw.rect(s, glass, r.inflate(-10, -r.h // 2), border_radius=3)
        pygame.draw.line(s, mix(col, (210, 216, 230), 0.3),
                         (r.centerx, r.top + 6), (r.centerx, r.bottom - 6), 1)


def _arrow(s, x, y, facing):
    """A lane arrow. Painted at a person's length, it sets the scale."""
    col = mix(ROADLINE, ASPHALT, 0.25)
    pygame.draw.rect(s, col, (x - 6, y - 34, 12, 68))
    pygame.draw.polygon(s, col, [(x, y - 56 * facing),
                                 (x - 19, y - 26 * facing),
                                 (x + 19, y - 26 * facing)])


def _tree(s, x, y, rng):
    pit = pygame.Rect(x - 26, y - 26, 52, 52)
    pygame.draw.rect(s, (30, 32, 40), pit)
    pygame.draw.rect(s, KERB, pit, 2)
    for rad, col in ((30, (22, 36, 28)), (26, (27, 45, 33)), (15, (33, 55, 40))):
        pygame.draw.circle(s, col, (x - (30 - rad) // 3, y - (30 - rad) // 3), rad)


def _paving(s, area, rng):
    """Pavement: slabs, a kerb, and the things that live on one."""
    pygame.draw.rect(s, PAVING, area)
    for x in range(area.left + 52, area.right, 52):
        pygame.draw.line(s, PAVELINE, (x, area.top), (x, area.bottom - 1), 1)
    for y in range(area.top + 52, area.bottom, 52):
        pygame.draw.line(s, PAVELINE, (area.left, y), (area.right - 1, y), 1)


def _roof(s, r, rng):
    """A building from above. At this size the roof is a place, not a dot."""
    base = ROOFS[rng.randrange(len(ROOFS))]
    pygame.draw.rect(s, SHADOW, r.move(12, 12))      # sun over the shoulder
    pygame.draw.rect(s, base, r)
    lip = mix(base, (128, 134, 156), 0.38)
    pygame.draw.line(s, lip, r.topleft, (r.right - 1, r.top), 5)
    pygame.draw.line(s, lip, r.topleft, (r.left, r.bottom - 1), 5)
    pygame.draw.rect(s, mix(base, (0, 0, 0), 0.6), r, 3)
    dark = mix(base, (0, 0, 0), 0.34)
    pale = mix(base, (120, 126, 148), 0.20)

    para = r.inflate(-26, -26)                   # parapet walkway
    if para.w > 40 and para.h > 40:
        pygame.draw.rect(s, mix(base, (0, 0, 0), 0.22), para, 2)
    inner = r.inflate(-52, -52)
    if inner.w < 60 or inner.h < 50:
        return

    # the stairwell head and its door
    sw, sh = rng.randint(46, 64), rng.randint(40, 56)
    box = pygame.Rect(inner.left if rng.random() < 0.5 else inner.right - sw,
                      inner.top if rng.random() < 0.5 else inner.bottom - sh, sw, sh)
    pygame.draw.rect(s, dark, box)
    pygame.draw.rect(s, pale, box, 2)
    pygame.draw.rect(s, mix(base, (0, 0, 0), 0.55),
                     (box.centerx - 9, box.bottom - 6, 18, 6))

    # water tank on legs
    if rng.random() < 0.6:
        c = (rng.randint(inner.left + 30, inner.right - 30),
             rng.randint(inner.top + 28, inner.bottom - 28))
        pygame.draw.circle(s, dark, c, 22)
        pygame.draw.circle(s, pale, c, 22, 2)
        pygame.draw.circle(s, pale, c, 11, 1)

    # a row of air handlers
    if rng.random() < 0.75:
        y = rng.randint(inner.top + 8, max(inner.top + 8, inner.bottom - 30))
        x = inner.left + 10
        for _ in range(rng.randint(2, 3)):
            if x > inner.right - 34:
                break
            u = pygame.Rect(x, y, 28, 24)
            pygame.draw.rect(s, dark, u)
            pygame.draw.rect(s, pale, u, 2)
            x += 40

    for _ in range(rng.randint(0, 2)):               # skylights
        g = pygame.Rect(rng.randint(inner.left, max(inner.left, inner.right - 40)),
                        rng.randint(inner.top, max(inner.top, inner.bottom - 26)),
                        38, 24)
        pygame.draw.rect(s, mix(base, (140, 150, 180), 0.20), g)
        pygame.draw.rect(s, dark, g, 2)
        pygame.draw.line(s, dark, (g.centerx, g.top), (g.centerx, g.bottom), 1)


def _frontage(s, r, rng, along_top):
    """Doors and shopfronts where a building meets the pavement."""
    edge = r.bottom - 8 if along_top else r.top + 8
    x = r.left + 40
    while x < r.right - 70:
        w = rng.randint(34, 52)
        if rng.random() < 0.5:                   # a doorway with a step
            d = pygame.Rect(x, edge - 10 if along_top else edge - 6, w, 16)
            pygame.draw.rect(s, (30, 32, 40), d)
            pygame.draw.rect(s, (92, 96, 112), d, 2)
        else:                                    # an awning
            a = pygame.Rect(x, edge - 12 if along_top else edge - 4, w, 14)
            col = CARS[rng.randrange(len(CARS))]
            pygame.draw.rect(s, mix(col, (0, 0, 0), 0.35), a)
            pygame.draw.rect(s, mix(col, (200, 206, 220), 0.25), a, 1)
        x += w + rng.randint(50, 130)


def _district(w, h, seed):
    """One block of city: an avenue, a side street, and the buildings.

    Always drawn at the same scale whatever the arena measures - a bigger
    arena gets more districts, never a stretched one, or the fighters
    would stop being people-sized.
    """
    rng = random.Random(seed)
    s = pygame.Surface((w, h))
    s.fill(PAVING)

    road = pygame.Rect(0, 196, w, 208)               # the avenue
    side = pygame.Rect(690, road.bottom, 148, h - road.bottom)   # a side street

    # -- the buildings, and the pavement in front of them ------------------
    top = pygame.Rect(0, 0, w, road.top - 44)
    bot_l = pygame.Rect(0, road.bottom + 44, side.left - 44, h - road.bottom - 44)
    bot_r = pygame.Rect(side.right + 44, road.bottom + 44,
                        w - side.right - 44, h - road.bottom - 44)
    _paving(s, pygame.Rect(0, 0, w, h), rng)
    for strip, edge_top in ((top, True), (bot_l, False), (bot_r, False)):
        x = strip.left + 6
        while x < strip.right - 90:
            bw = min(rng.randint(250, 380), strip.right - 6 - x)
            if bw < 110:
                break
            b = pygame.Rect(x, strip.top + 6, bw, strip.h - 12)
            _roof(s, b, rng)
            _frontage(s, b, rng, edge_top)
            x += bw + rng.randint(14, 26)

    # -- pavement furniture, then the kerbs --------------------------------
    for y in (road.top - 24, road.bottom + 24):
        for x in range(120, w - 80, 250):
            if side.left - 60 < x < side.right + 60 and y > road.bottom:
                continue
            if rng.random() < 0.6:
                _tree(s, x + rng.randint(-30, 30), y, rng)
            else:
                _manhole(s, x, y, 14)
    for r in (pygame.Rect(0, road.top - 44, w, 44),
              pygame.Rect(0, road.bottom, w, 44)):
        pygame.draw.line(s, KERB, (r.left, r.top if r.top > road.top else r.bottom),
                         (r.right, r.top if r.top > road.top else r.bottom), 4)

    # -- the roadway -------------------------------------------------------
    pygame.draw.rect(s, ASPHALT, road)
    pygame.draw.rect(s, ASPHALT, side)
    pygame.draw.line(s, KERB, road.topleft, road.topright, 5)
    pygame.draw.line(s, KERB, (road.left, road.bottom), (side.left, road.bottom), 5)
    pygame.draw.line(s, KERB, (side.right, road.bottom), (road.right, road.bottom), 5)
    pygame.draw.line(s, KERB, side.topleft, side.bottomleft, 5)
    pygame.draw.line(s, KERB, side.topright, side.bottomright, 5)

    for x in range(20, w, 160):                      # centre line of the avenue
        pygame.draw.line(s, ROADLINE, (x, road.centery), (x + 90, road.centery), 9)
    pygame.draw.line(s, mix(ROADLINE, ASPHALT, 0.45),
                     (0, road.top + 16), (w, road.top + 16), 4)
    pygame.draw.line(s, mix(ROADLINE, ASPHALT, 0.45),
                     (0, road.bottom - 16), (side.left, road.bottom - 16), 4)

    cross = 430                                      # a zebra across the avenue
    for k in range(5):
        x = cross + k * 54
        pygame.draw.rect(s, CROSSWALK, (x, road.top + 14, 22, road.h - 28))
    for k in range(3):                               # and one over the side street
        y = side.top + 26 + k * 44
        pygame.draw.rect(s, CROSSWALK, (side.left + 14, y, side.w - 28, 18))

    _arrow(s, 250, road.centery - 40, 1)
    _arrow(s, 790, road.centery + 40, -1)
    _manhole(s, 220, road.centery + 54)
    _manhole(s, 880, road.centery - 46)
    _grate(s, 150, road.top + 12)
    _grate(s, 640, road.bottom - 12)
    _grate(s, side.left + 12, h - 90, flat=False)

    # parked along both kerbs, nose to tail
    zebra = (cross - 96, cross + 5 * 54 + 30)
    x = 40
    while x < w - 100:
        if not (zebra[0] < x < zebra[1]) and rng.random() < 0.85:
            _car(s, pygame.Rect(x, road.top + 26, 86, 40), rng)
        x += rng.randint(104, 150)
    x = 70
    while x < w - 100:
        if (not (zebra[0] < x < zebra[1])
                and not (side.left - 100 < x < side.right)
                and rng.random() < 0.85):
            _car(s, pygame.Rect(x, road.bottom - 66, 86, 40), rng)
        x += rng.randint(104, 150)
    if rng.random() < 0.8:
        _car(s, pygame.Rect(side.left + 14, h - 150, 40, 86), rng, flat=False)

    return s


def city_floor(w, h):
    """The arena floor. Built on first use per size, then reused."""
    if (w, h) in _city_floors:
        return _city_floors[(w, h)]
    cols = max(1, int(round(w / VIEW.w)))
    rows = max(1, int(round(h / VIEW.h)))
    xs = [w * c // cols for c in range(cols + 1)]
    ys = [h * r // rows for r in range(rows + 1)]
    s = pygame.Surface((w, h))
    for r in range(rows):
        for c in range(cols):
            tile = _district(xs[c + 1] - xs[c], ys[r + 1] - ys[r],
                             20260920 + r * 31 + c)
            s.blit(tile, (xs[c], ys[r]))
    _city_floors[(w, h)] = s
    return s


# ---------------------------------------------------------------------------
# NOISE
#
# Nothing ships beside this file, so every sound is a few thousand samples
# built at start-up. A machine with no audio device just gets silence.
# ---------------------------------------------------------------------------
class Sfx:
    RATE = 22050

    def __init__(self):
        self.ok = False
        self.muted = False
        self.bank = {}
        try:
            pygame.mixer.init(frequency=self.RATE, size=-16, channels=1, buffer=256)
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            return
        try:
            self.bank = {
                "cut":    self._mk(420, 70, kind="noise", vol=0.22, bend=-0.4),
                "shoot":  self._mk(680, 55, kind="saw", vol=0.16, bend=-0.6),
                "arrow":  self._mk(240, 130, kind="saw", vol=0.20, bend=0.8),
                "hit":    self._mk(160, 90, kind="noise", vol=0.26, bend=-0.5),
                "parry":  self._mk(1500, 90, kind="sine", vol=0.20, bend=1.4),
                "crit":   self._mk(900, 120, kind="sine", vol=0.24, bend=-0.7),
                "pickup": self._mk(520, 150, kind="sine", vol=0.20, bend=1.6),
                "ko":     self._mk(90, 600, kind="noise", vol=0.35, bend=-0.8),
                "click":  self._mk(760, 40, kind="sine", vol=0.15, bend=0.0),
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
# EFFECTS
# ---------------------------------------------------------------------------
class Particle:
    __slots__ = ("pos", "vel", "life", "full", "colour", "size", "grav")

    def __init__(self, pos, vel, life, colour, size=3.0, grav=0.0):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.life = self.full = life
        self.colour = colour
        self.size = size
        self.grav = grav

    def update(self, dt):
        self.life -= dt
        self.vel.y += self.grav * dt
        self.vel *= max(0.0, 1.0 - 2.0 * dt)
        self.pos += self.vel * dt
        return self.life > 0

    def draw(self, s, off):
        f = self.life / self.full
        r = max(1, int(self.size * f))
        p = (int(self.pos.x + off[0]), int(self.pos.y + off[1]))
        blit_glow(s, p, r * 2.2, self.colour, int(58 * f))
        pygame.draw.circle(s, mix(self.colour, (255, 255, 255), 0.35 * f), p, r)


class Floater:
    """A damage number, drifting up off the ball that just got hit."""
    __slots__ = ("pos", "vel", "life", "full", "colour", "txt", "size")

    def __init__(self, pos, amount, colour, crit=False):
        self.pos = Vector2(pos)
        self.vel = Vector2(random.uniform(-26, 26), random.uniform(-92, -64))
        self.life = self.full = 0.95 if crit else 0.7
        self.colour = GOLD if crit else colour
        self.txt = str(int(round(amount)))
        # the fighters are small now; a number must not outgrow one
        self.size = 27 if crit else 19

    def update(self, dt):
        self.life -= dt
        self.vel.y += 120 * dt
        self.pos += self.vel * dt
        return self.life > 0

    def draw(self, s, off):
        f = clamp(self.life / self.full, 0.0, 1.0)
        a = int(255 * min(1.0, f * 2.2))
        pop = 1.0 + 0.35 * (1.0 - f) ** 3
        text(s, self.txt, int(self.size * pop),
             (self.pos.x + off[0], self.pos.y + off[1]),
             self.colour, center=True, alpha=a)


# ---------------------------------------------------------------------------
# PROJECTILES
# ---------------------------------------------------------------------------
class Projectile:
    def __init__(self, owner, pos, vel, dmg, kind, crit_chance=0.10,
                 bounces=0, pierce=0, knock=60.0, size=4.0, life=3.0):
        self.owner = owner
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.dmg = dmg
        self.kind = kind
        self.crit_chance = crit_chance
        self.bounces = bounces
        self.pierce = pierce
        self.knock = knock
        self.size = size
        self.life = life
        self.dead = False
        self.hit = set()
        self.prev = Vector2(pos)

    def update(self, dt, world):
        self.life -= dt
        if self.life <= 0:
            self.dead = True
            return
        self.prev = Vector2(self.pos)
        self.pos += self.vel * dt

        # Walls. Bullets get a ricochet, arrows bury themselves.
        hit_wall = False
        if self.pos.x < ARENA.left + self.size:
            self.pos.x = ARENA.left + self.size
            self.vel.x = abs(self.vel.x)
            hit_wall = True
        elif self.pos.x > ARENA.right - self.size:
            self.pos.x = ARENA.right - self.size
            self.vel.x = -abs(self.vel.x)
            hit_wall = True
        if self.pos.y < ARENA.top + self.size:
            self.pos.y = ARENA.top + self.size
            self.vel.y = abs(self.vel.y)
            hit_wall = True
        elif self.pos.y > ARENA.bottom - self.size:
            self.pos.y = ARENA.bottom - self.size
            self.vel.y = -abs(self.vel.y)
            hit_wall = True
        if hit_wall:
            world.spark(self.pos, self.owner.colour, 5, speed=140)
            if self.bounces <= 0:
                self.dead = True
                return
            self.bounces -= 1
            self.vel *= 0.92

        for f in world.fighters:
            if f.team == self.owner.team or f in self.hit or f.hp <= 0:
                continue
            # tested along the swept line, not the landing point
            if seg_dist(f.pos, self.prev, self.pos) <= f.r + self.size:
                crit = random.random() < self.crit_chance
                dmg = self.dmg * (1.9 if crit else 1.0)
                f.take_damage(dmg, self.owner, world, crit=crit)
                f.vel += unit(self.vel) * (self.knock / f.weapon.MASS)
                world.spark(f.pos - unit(self.vel) * f.r, self.owner.colour,
                            10 if crit else 6, speed=220)
                self.hit.add(f)
                if self.pierce <= 0:
                    self.dead = True
                    return
                self.pierce -= 1
                self.vel *= 0.8

        for m in world.minions:
            if m.owner.team == self.owner.team or m.hp <= 0:
                continue
            if seg_dist(m.pos, self.prev, self.pos) <= m.r + self.size:
                m.hurt(self.dmg, world)
                if self.pierce <= 0:
                    self.dead = True
                    return
                self.pierce -= 1

    def draw(self, s, off):
        p = self.pos + Vector2(off)
        d = unit(self.vel)
        c = self.owner.colour
        if self.kind == "shell":
            pygame.draw.circle(s, mix(c, (0, 0, 0), 0.25),
                               (int(p.x), int(p.y)), int(self.size))
            pygame.draw.circle(s, mix(c, (255, 230, 180), 0.5),
                               (int(p.x - d.x * 2), int(p.y - d.y * 2)),
                               max(2, int(self.size * 0.5)))
            blit_glow(s, p, self.size * 2.4, (255, 200, 140), 80)
        elif self.kind == "arrow":
            tail = p - d * 22
            side = Vector2(-d.y, d.x)
            pygame.draw.line(s, mix(c, (255, 255, 255), 0.2), tail, p, 3)
            pygame.draw.polygon(s, (255, 255, 255),
                                [p + d * 7, p - d * 4 + side * 5, p - d * 4 - side * 5])
            pygame.draw.line(s, c, tail, tail + d * 6 + side * 5, 2)
            pygame.draw.line(s, c, tail, tail + d * 6 - side * 5, 2)
            blit_glow(s, p, 12, c, 60)
        else:
            blit_glow(s, p, 7, c, 55)
            pygame.draw.line(s, mix(c, BG, 0.5), p - d * 22, p, 4)
            pygame.draw.line(s, mix(c, (255, 255, 255), 0.8), p - d * 11, p, 2)


# ---------------------------------------------------------------------------
# WEAPONS
#
# A weapon owns the range its carrier wants to hold (PREF), what it does
# each frame, how it draws, and the body it rides on - size, weight, armour
# and health. The AI hangs off PREF: that one number is what makes a sword
# ball charge and a bow ball run.
# ---------------------------------------------------------------------------
class Weapon:
    NAME = "?"
    PREF = 200.0              # range the carrier tries to hold
    RADIUS = 26.0             # the heavy weapon makes a bigger target
    SPEED_MULT = 1.0          # the light weapon is the fast one
    DASH_MULT = 1.0           # multiplies the dash cooldown
    ARMOUR = 0.0              # ... and it soaks this share of every hit
    MASS = 1.0                # ... and shrugs off this much of the knockback
    HP_MULT = 1.0             # ... and a bigger body holds more of a beating
    ART_REF = 26.0            # the body size this weapon was drawn for
    BLURB = ("", "")
    PIPS = (0, 0, 0)          # damage / rate / reach, out of 5, for the menu

    def __init__(self, owner):
        self.owner = owner
        self.shots = 0

    def update(self, dt, world):
        pass

    def draw(self, s, off, world):
        pass


class Melee(Weapon):
    """Anything that swings around the ball and cuts what it touches.

    One set of blades, one hit cooldown each, and a parry window - the
    sword, the dagger and the hammer are the same machine with different
    numbers bolted on.
    """
    PREF = 0.0
    BLADES = 3
    REACH = 64.0
    SPIN = 4.7
    KNOCK = 40.0              # shoving the target away also ends the combo
    LUNGE = 55.0              # so the cut pulls the swordsman in instead
    DMG = (26.0, 37.0)
    HIT_CD = 0.32
    CRIT = 0.12
    PARRY_CD = 0.11
    PARRY_BAND = 9.0
    W_BASE = 4.0              # blade width at the hilt, and at the tip
    W_TIP = 1.3
    GUARD = 7.0

    def __init__(self, owner):
        super().__init__(owner)
        self.angle = random.uniform(0, TAU)
        self.cool = [0.0] * self.BLADES
        self.parry_cd = 0.0
        self.flash = 0.0

    def spin_rate(self):
        """Radians per second. A weapon may wind itself up."""
        return self.SPIN

    def segments(self):
        o = self.owner
        for i in range(self.BLADES):
            a = self.angle + i * TAU / self.BLADES
            d = Vector2(math.cos(a), math.sin(a))
            yield o.pos + d * (o.r + 4), o.pos + d * (o.r + self.REACH)

    def update(self, dt, world):
        o = self.owner
        self.angle = (self.angle + self.spin_rate() * dt) % TAU
        self.parry_cd = max(0.0, self.parry_cd - dt)
        self.flash = max(0.0, self.flash - dt * 5.0)
        targets = world.foes(o)
        for i, (a, b) in enumerate(self.segments()):
            self.cool[i] = max(0.0, self.cool[i] - dt)
            foe = None
            if self.cool[i] <= 0:
                for t in targets:          # whoever this blade is passing
                    if seg_dist(t.pos, a, b) <= t.r + 7:
                        foe = t
                        break
            if foe is not None:
                crit = random.random() < self.CRIT
                dmg = random.uniform(*self.DMG) * (1.8 if crit else 1.0)
                foe.take_damage(dmg, o, world, crit=crit)
                push = unit(foe.pos - o.pos)
                foe.vel += push * (self.KNOCK / foe.weapon.MASS)
                o.vel += push * (self.LUNGE / o.weapon.MASS)
                self.cool[i] = self.HIT_CD
                self.flash = 1.0
                world.spark(foe.pos - push * foe.r, o.colour, 8, speed=240)
                SFX.play("cut", 0.7)
            for m in world.minions:
                if m.owner.team != o.team and m.hp > 0:
                    if seg_dist(m.pos, a, b) <= m.r + 4:
                        m.hurt(random.uniform(*self.DMG), world)
                        self.flash = max(self.flash, 0.6)
            if self.parry_cd <= 0:
                for pr in world.projectiles:
                    if pr.owner.team == o.team or pr.dead:
                        continue
                    if segs_close(pr.prev, pr.pos, a, b, self.PARRY_BAND):
                        pr.dead = True
                        self.parry_cd = self.PARRY_CD
                        world.spark(pr.pos, (255, 255, 255), 9, speed=260)
                        world.shake = max(world.shake, 3.0)
                        SFX.play("parry", 0.45)
                        break

    def draw(self, s, off, world):
        o = self.owner
        ov = Vector2(off)
        k = o.r / self.ART_REF
        for a, b in self.segments():
            a, b = a + ov, b + ov
            d = unit(b - a)
            side = Vector2(-d.y, d.x)
            body = [a + side * self.W_BASE * k, b + side * self.W_TIP * k,
                    b - side * self.W_TIP * k, a - side * self.W_BASE * k]
            edge = mix(o.colour, (255, 255, 255), 0.55 + 0.45 * self.flash)
            pygame.draw.polygon(s, edge, body)
            pygame.draw.polygon(s, (255, 255, 255), body, 1)
            pygame.draw.line(s, (206, 211, 224), a + side * self.GUARD * k,
                             a - side * self.GUARD * k, max(2, int(3 * k)))
            pygame.draw.line(s, (72, 56, 44), a - d * 7 * k, a, max(2, int(5 * k)))
            if self.flash > 0.05:
                blit_glow(s, b, 26 * k, o.colour, int(90 * self.flash))


class Sword(Melee):
    NAME = "SWORD"
    RADIUS = 14.0
    ART_REF = 23.0
    SPEED_MULT = 1.22         # carries the least weight, so it runs you down
    DASH_MULT = 0.62
    BLURB = ("orbiting blades that cut on",
             "contact - and swat bullets down")
    PIPS = (4, 4, 1)

    BLADES = 3
    REACH = 64.0
    SPIN = 4.7
    KNOCK = 40.0
    LUNGE = 55.0
    DMG = (26.0, 37.0)
    HIT_CD = 0.32
    CRIT = 0.12
    PARRY_CD = 0.11
    PARRY_BAND = 9.0


class Dagger(Melee):
    NAME = "DAGGER"
    RADIUS = 12.0
    ART_REF = 20.0
    SPEED_MULT = 1.32         # the smallest, quickest thing in the arena
    DASH_MULT = 0.50
    MASS = 0.78               # and the easiest to shove off its line
    BLURB = ("four little knives, always",
             "turning - and no reach at all")
    PIPS = (1, 5, 1)

    # In a scrum, hit rate is set by how often a blade sweeps the target,
    # not by the cooldown - so what makes this fast is four of them, and
    # each cut stays small.
    BLADES = 4
    REACH = 47.0
    SPIN = 8.0
    KNOCK = 22.0
    LUNGE = 62.0
    DMG = (15.0, 21.0)
    HIT_CD = 0.16
    CRIT = 0.16
    PARRY_CD = 0.13
    PARRY_BAND = 7.0
    W_BASE = 3.0
    W_TIP = 1.1
    GUARD = 5.0


class Hammer(Melee):
    NAME = "HAMMER"
    RADIUS = 17.0
    ART_REF = 27.0
    SPEED_MULT = 1.06
    DASH_MULT = 1.35
    ARMOUR = 0.35             # too heavy for a bullet to matter much
    MASS = 2.8                # and too heavy to be pushed off its line
    BLURB = ("one slow head, and a body that",
             "shrugs off a third of everything")
    PIPS = (5, 1, 3)

    BLADES = 1
    REACH = 75.0
    SPIN = 3.0
    KNOCK = 330.0             # the knockback IS the weapon
    LUNGE = 0.0
    DMG = (78.0, 106.0)
    HIT_CD = 0.58
    CRIT = 0.12
    PARRY_CD = 0.45
    PARRY_BAND = 12.0

    def draw(self, s, off, world):
        o = self.owner
        ov = Vector2(off)
        k = o.r / self.ART_REF
        for a, b in self.segments():
            a, b = a + ov, b + ov
            d = unit(b - a)
            side = Vector2(-d.y, d.x)
            pygame.draw.line(s, (108, 78, 48), a - d * 6 * k, b - d * 10 * k,
                             max(3, int(7 * k)))
            head = [b + side * 14 * k - d * 16 * k, b + side * 14 * k + d * 9 * k,
                    b - side * 14 * k + d * 9 * k, b - side * 14 * k - d * 16 * k]
            face = mix((146, 152, 168), (255, 255, 255), 0.55 * self.flash)
            pygame.draw.polygon(s, face, head)
            pygame.draw.polygon(s, mix(o.colour, (255, 255, 255), 0.35), head, 2)
            pygame.draw.line(s, mix(face, (0, 0, 0), 0.35),
                             b + side * 14 * k - d * 3 * k,
                             b - side * 14 * k - d * 3 * k, 2)
            if self.flash > 0.05:
                blit_glow(s, b, 34 * k, o.colour, int(110 * self.flash))


class Gun(Weapon):
    NAME = "GUN"
    PREF = 330.0
    RADIUS = 16.0
    ART_REF = 26.0
    SPEED_MULT = 1.0
    DASH_MULT = 1.0
    BLURB = ("three-round bursts, and the",
             "bullets ricochet off the walls")
    PIPS = (2, 5, 4)

    DMG = (11.0, 15.5)
    SPEED = 880.0
    BURST = 3
    BURST_GAP = 0.09
    RELOAD = 0.56
    SPREAD = 0.046
    CRIT = 0.10

    def __init__(self, owner):
        super().__init__(owner)
        self.timer = random.uniform(0.1, 0.6)
        self.left = 0
        self.kick = 0.0

    def update(self, dt, world):
        o = self.owner
        self.kick = max(0.0, self.kick - dt * 7.0)
        self.timer -= dt
        if self.timer > 0 or o.hp <= 0 or world.state != "fight":
            return
        if self.left <= 0:
            self.left = self.BURST
        d = o.aim.rotate_rad(random.uniform(-self.SPREAD, self.SPREAD))
        muzzle = o.pos + d * (o.r + 20)
        world.projectiles.append(Projectile(
            o, muzzle, d * self.SPEED, random.uniform(*self.DMG), "bullet",
            crit_chance=self.CRIT, bounces=1, knock=45.0, size=7.0, life=2.4))
        o.vel -= d * 55.0
        self.shots += 1
        self.kick = 1.0
        world.spark(muzzle, mix(o.colour, (255, 240, 200), 0.6), 3, speed=150)
        SFX.play("shoot", 0.4)
        self.left -= 1
        self.timer = self.BURST_GAP if self.left > 0 else self.RELOAD

    def draw(self, s, off, world):
        o = self.owner
        d = o.aim
        side = Vector2(-d.y, d.x)
        k = o.r / self.ART_REF
        base = o.pos + Vector2(off) + d * (o.r + (2 - 5 * self.kick) * k)
        barrel = base + d * 26 * k
        pygame.draw.line(s, (46, 50, 62), base - side * 4 * k,
                         barrel - side * 4 * k, max(3, int(9 * k)))
        pygame.draw.line(s, (150, 158, 176), base, barrel, max(2, int(6 * k)))
        pygame.draw.line(s, (92, 99, 118), base - d * 4 * k + side * 2 * k,
                         base + d * 6 * k + side * 12 * k, max(2, int(7 * k)))
        pygame.draw.circle(s, (34, 37, 47), (int(barrel.x), int(barrel.y)),
                           max(1, int(3 * k)))
        if self.kick > 0.25:
            blit_glow(s, barrel + d * 6 * k, 18 * k * self.kick,
                      (255, 220, 150), int(150 * self.kick))


class Bow(Weapon):
    NAME = "BOW"
    PREF = 380.0
    RADIUS = 17.0
    ART_REF = 28.0
    SPEED_MULT = 0.88         # heaviest draw, slowest ball
    DASH_MULT = 1.25
    BLURB = ("a slow draw, then a heavy arrow",
             "that pierces and knocks you back")
    PIPS = (5, 1, 5)

    DMG = (55.0, 73.0)
    SPEED = 1000.0
    DRAW_TIME = 1.30
    CRIT = 0.15
    ARROWS = 1                # a volley of this many
    FAN = 0.0                 # spread across the volley, radians

    def __init__(self, owner):
        super().__init__(owner)
        self.charge = random.uniform(0.0, 0.4)

    def update(self, dt, world):
        o = self.owner
        if o.hp <= 0 or world.state != "fight":
            return
        self.charge += dt / self.DRAW_TIME
        if self.charge < 1.0:
            return
        self.charge = 0.0
        for i in range(self.ARROWS):
            off_a = 0.0 if self.ARROWS == 1 else (
                (i / (self.ARROWS - 1) - 0.5) * self.FAN)
            d = o.aim.rotate_rad(off_a + random.uniform(-0.02, 0.02))
            nock = o.pos + d * (o.r + 14)
            world.projectiles.append(Projectile(
                o, nock, d * self.SPEED, random.uniform(*self.DMG), "arrow",
                crit_chance=self.CRIT, bounces=0, pierce=1, knock=220.0,
                size=7.0, life=2.2))
            self.shots += 1
        d = o.aim
        o.vel -= d * 90.0
        world.spark(nock, mix(o.colour, (255, 255, 255), 0.5), 5, speed=180)
        SFX.play("arrow", 0.5)

    def draw(self, s, off, world):
        o = self.owner
        d = o.aim
        side = Vector2(-d.y, d.x)
        k = o.r / self.ART_REF
        c = o.pos + Vector2(off) + d * (o.r + 8 * k)
        pull = 16.0 * k * self.charge
        tip1, tip2 = c + side * 24 * k - d * 6 * k, c - side * 24 * k - d * 6 * k
        # limbs
        pygame.draw.lines(s, (122, 84, 46), False,
                          [tip1, c + side * 14 * k + d * 9 * k, c + d * 12 * k,
                           c - side * 14 * k + d * 9 * k, tip2], max(3, int(5 * k)))
        # string, pulled back by the draw
        knock_pt = c - d * pull
        pygame.draw.lines(s, (215, 220, 232), False, [tip1, knock_pt, tip2], 2)
        if self.charge > 0.08:
            shaft = knock_pt + d * (10 + 26 * self.charge) * k
            pygame.draw.line(s, mix(o.colour, (255, 255, 255), 0.4),
                             knock_pt, shaft, max(2, int(3 * k)))
            pygame.draw.polygon(s, (255, 255, 255),
                                [shaft + d * 6 * k, shaft - d * 3 * k + side * 4 * k,
                                 shaft - d * 3 * k - side * 4 * k])
        if self.charge > 0.86:
            blit_glow(s, c + d * 20 * k, 22 * k, o.colour,
                      int(120 * (self.charge - 0.86) / 0.14))


class Fists(Melee):
    NAME = "FISTS"
    RADIUS = 26.0             # no weapon to carry, so all of it is ball
    ART_REF = 26.0
    SPEED_MULT = 1.00
    DASH_MULT = 1.15
    ARMOUR = 0.34
    MASS = 2.2
    HP_MULT = 1.5             # all that ball is worth something
    BLURB = ("a big ball with two fists -",
             "no reach, but it hits back hard")
    PIPS = (4, 3, 2)

    BLADES = 2
    REACH = 44.0
    SPIN = 3.4
    KNOCK = 180.0             # a punch puts you somewhere else
    LUNGE = 35.0
    DMG = (34.0, 48.0)
    HIT_CD = 0.42
    CRIT = 0.12
    PARRY_CD = 0.30
    PARRY_BAND = 12.0

    def draw(self, s, off, world):
        o = self.owner
        ov = Vector2(off)
        k = o.r / self.ART_REF
        for a, b in self.segments():
            a, b = a + ov, b + ov
            d = unit(b - a)
            side = Vector2(-d.y, d.x)
            pygame.draw.line(s, mix(o.dark, o.colour, 0.55), a, b,
                             max(4, int(9 * k)))
            fr = max(5, int(11 * k))
            knuckle = mix(o.colour, (255, 255, 255), 0.25 + 0.5 * self.flash)
            pygame.draw.circle(s, knuckle, (int(b.x), int(b.y)), fr)
            pygame.draw.circle(s, mix(o.dark, (0, 0, 0), 0.35),
                               (int(b.x), int(b.y)), fr, 2)
            for n in (-1, 0, 1):
                q = b + d * fr * 0.5 + side * (n * fr * 0.44)
                pygame.draw.circle(s, mix(o.dark, (0, 0, 0), 0.2),
                                   (int(q.x), int(q.y)), max(1, int(fr * 0.2)))
            if self.flash > 0.05:
                blit_glow(s, b, 30 * k, o.colour, int(110 * self.flash))


class Summoner(Weapon):
    NAME = "SUMMONER"
    RADIUS = 22.0
    ART_REF = 22.0
    PREF = 300.0              # it would rather you came to it
    SPEED_MULT = 0.85
    DASH_MULT = 1.3
    ARMOUR = 0.18
    MASS = 1.8
    HP_MULT = 1.70
    BLURB = ("throws out little balls, and",
             "throws out more as it goes on")
    PIPS = (1, 3, 5)

    FIRST = 1.0               # first one arrives quickly
    GAP = 2.0                 # then this long between them ...
    RAMP = 0.045              # ... shrinking every second ...
    GAP_MIN = 0.80            # ... to this
    CAP = 5                   # this many alive at first ...
    CAP_EVERY = 10.0          # ... one more every this many seconds ...
    CAP_MAX = 13              # ... up to this
    PER_SUMMON = 1            # how many arrive at once
    MINION_SCALE = 1.0        # and how tough each one is

    def __init__(self, owner):
        super().__init__(owner)
        self.timer = self.FIRST
        self.ring = random.uniform(0, TAU)

    def update(self, dt, world):
        o = self.owner
        self.ring += dt * 1.6
        if o.hp <= 0 or world.state != "fight":
            return
        self.timer -= dt
        if self.timer > 0:
            return
        self.timer = max(self.GAP_MIN, self.GAP - self.RAMP * world.clock_t)
        cap = min(self.CAP_MAX,
                  self.CAP + int(world.clock_t / self.CAP_EVERY))
        if sum(1 for m in world.minions if m.owner is o) >= cap:
            return
        for _ in range(self.PER_SUMMON):
            a = random.uniform(0, TAU)
            d = Vector2(math.cos(a), math.sin(a))
            world.minions.append(Minion(o, o.pos + d * (o.r + 12),
                                        self.MINION_SCALE))
            self.shots += 1
            world.spark(o.pos + d * o.r, o.colour, 6, speed=170)
        SFX.play("pickup", 0.35)

    def draw(self, s, off, world):
        o = self.owner
        p = o.pos + Vector2(off)
        k = o.r / self.ART_REF
        for i in range(3):
            a = self.ring + i * TAU / 3
            q = p + Vector2(math.cos(a), math.sin(a)) * (o.r + 11 * k)
            pygame.draw.circle(s, mix(o.colour, (255, 255, 255), 0.4),
                               (int(q.x), int(q.y)), max(2, int(5 * k)))
            pygame.draw.circle(s, mix(o.dark, (0, 0, 0), 0.3),
                               (int(q.x), int(q.y)), max(2, int(5 * k)), 1)
        ready = clamp(1.0 - self.timer / max(0.2, self.GAP), 0.0, 1.0)
        if ready > 0.55:
            blit_glow(s, p, o.r * 1.5, o.colour, int(60 * (ready - 0.55) / 0.45))


class Flurry(Melee):
    NAME = "FLURRY"
    RADIUS = 13.0
    ART_REF = 20.0            # drawn at the dagger's proportions
    SPEED_MULT = 1.28
    DASH_MULT = 0.85
    MASS = 0.82
    BLURB = ("eight knives instead of four,",
             "and a lunge that spins them up")
    PIPS = (2, 5, 1)

    BLADES = 8                # twice the dagger, each one cutting less
    REACH = 42.0
    SPIN = 8.0
    DASH_SPIN = 20.0          # while lunging, it is a saw blade
    LUNGE_AT = 240.0          # how close before it throws itself at you
    KNOCK = 20.0
    LUNGE = 60.0
    DMG = (8.0, 12.0)
    HIT_CD = 0.20
    CRIT = 0.16
    PARRY_CD = 0.11
    PARRY_BAND = 8.0
    W_BASE = 2.6
    W_TIP = 1.0
    GUARD = 4.0

    def spin_rate(self):
        return self.DASH_SPIN if self.owner.dash_t > 0 else self.SPIN

    def update(self, dt, world):
        # The move belongs to the weapon: nothing else in the game dashes
        # on its own any more, so the flurry throws itself.
        o = self.owner
        foe = world.foe(o)
        if (foe and foe.hp > 0 and o.hp > 0 and not o.player
                and o.dash_cd <= 0 and world.state == "fight"
                and (foe.pos - o.pos).length() < self.LUNGE_AT):
            o.dash(unit(foe.pos - o.pos))
            world.spark(o.pos, o.colour, 8, speed=220)
            SFX.play("cut", 0.45)
        super().update(dt, world)

    def draw(self, s, off, world):
        super().draw(s, off, world)
        if self.owner.dash_t > 0:
            blit_glow(s, self.owner.pos + Vector2(off),
                      (self.owner.r + self.REACH) * 0.9, self.owner.colour, 55)


# ---------------------------------------------------------------------------
# THE SECOND TIER
#
# One upgrade per weapon, each the same idea taken further: more blades,
# more barrels, more of whatever made the original what it was. They cost
# something for it - weight, speed, or a longer wait between swings - and
# they are all won late, off the blocks carrying them.
# ---------------------------------------------------------------------------
class Greatsword(Sword):
    NAME = "GREATSWORD"
    RADIUS = 18.0             # a wider target than the sword
    ART_REF = 23.0
    SPEED_MULT = 0.90         # and far too heavy to chase with
    DASH_MULT = 1.25
    MASS = 1.5
    HP_MULT = 1.10
    BLURB = ("five long blades, swung slow -",
             "everything the sword is, doubled")
    PIPS = (5, 3, 4)

    BLADES = 5
    REACH = 78.0
    SPIN = 3.2
    DMG = (25.0, 35.0)        # each blade lands softer than the sword's
    HIT_CD = 0.40
    W_BASE = 5.0
    W_TIP = 1.6
    GUARD = 9.0


class Repeater(Gun):
    NAME = "REPEATER"
    RADIUS = 17.0
    ART_REF = 26.0
    SPEED_MULT = 0.96
    HP_MULT = 1.10
    BLURB = ("five-round bursts and half the",
             "reload - the gun, without pauses")
    PIPS = (3, 5, 4)

    DMG = (7.0, 10.0)
    BURST = 5
    BURST_GAP = 0.07
    RELOAD = 0.50
    SPREAD = 0.080            # it sprays; the gun aims


class Ballista(Bow):
    NAME = "BALLISTA"
    RADIUS = 19.0
    ART_REF = 28.0
    SPEED_MULT = 0.82
    MASS = 1.4
    HP_MULT = 1.15
    BLURB = ("three bolts in one volley, and",
             "a long wait to wind it back")
    PIPS = (5, 1, 5)

    ARROWS = 3
    FAN = 0.24
    DRAW_TIME = 2.02
    DMG = (30.0, 41.0)


class Maul(Hammer):
    NAME = "MAUL"
    RADIUS = 20.0
    ART_REF = 27.0
    SPEED_MULT = 0.86
    MASS = 3.2
    ARMOUR = 0.36
    HP_MULT = 1.15
    BLURB = ("a head at each end, so there is",
             "no safe side to stand on")
    PIPS = (5, 2, 5)

    BLADES = 2
    REACH = 74.0
    SPIN = 2.6
    DMG = (52.0, 70.0)
    HIT_CD = 0.68


class Gauntlets(Fists):
    NAME = "GAUNTLETS"
    RADIUS = 30.0
    ART_REF = 26.0
    SPEED_MULT = 0.84
    MASS = 2.6
    ARMOUR = 0.34
    HP_MULT = 1.55
    BLURB = ("four fists on a bigger ball -",
             "no gap left to slip through")
    PIPS = (4, 4, 2)

    BLADES = 4
    REACH = 44.0
    SPIN = 3.0
    DMG = (22.0, 31.0)
    HIT_CD = 0.42


class Brood(Summoner):
    NAME = "BROOD"
    RADIUS = 26.0
    ART_REF = 22.0
    SPEED_MULT = 0.78
    ARMOUR = 0.20
    HP_MULT = 1.70
    BLURB = ("sends them two at a time, and",
             "they take some killing")
    PIPS = (2, 4, 5)

    PER_SUMMON = 2
    MINION_SCALE = 1.5
    GAP = 3.0                 # two at a time, but you wait for them
    GAP_MIN = 1.1
    CAP = 4
    CAP_EVERY = 12.0
    CAP_MAX = 10


class Buster(Melee):
    """A slab of a blade, and two cannons bolted to the back of the ball.

    The only weapon that runs two systems at once: the blade swings on the
    melee machinery like everything else, and the cannons fire on their own
    timer regardless of what the blade is doing.
    """
    NAME = "BUSTER"
    RADIUS = 58.0             # it is the size of a building
    ART_REF = 27.0
    PREF = 0.0
    SPEED_MULT = 0.60
    DASH_MULT = 2.2
    MASS = 6.0
    ARMOUR = 0.45
    HP_MULT = 1.0             # the level supplies the health
    BLURB = ("a slab of a sword, and two",
             "cannons bolted on the back")
    PIPS = (5, 2, 5)

    BLADES = 1
    REACH = 150.0
    SPIN = 1.45
    KNOCK = 420.0
    LUNGE = 0.0
    DMG = (105.0, 145.0)
    HIT_CD = 1.0
    CRIT = 0.10
    PARRY_CD = 0.50
    PARRY_BAND = 24.0

    SALVO = 1.6               # seconds between salvos
    SHELL_DMG = (34.0, 46.0)
    SHELL_SPEED = 540.0
    SHELL_SPREAD = 0.05

    def __init__(self, owner):
        super().__init__(owner)
        self.salvo = 2.0
        self.muzzle = 0.0

    def mounts(self):
        """Where the two cannons sit: over each shoulder, facing back."""
        o = self.owner
        back = -o.aim
        side = Vector2(-back.y, back.x)
        for sgn in (-1, 1):
            yield (o.pos + back * (o.r * 0.45) + side * (o.r * 0.62 * sgn),
                   sgn)

    def update(self, dt, world):
        super().update(dt, world)
        o = self.owner
        self.muzzle = max(0.0, self.muzzle - dt * 4.0)
        if o.hp <= 0 or world.state != "fight":
            return
        self.salvo -= dt
        if self.salvo > 0:
            return
        self.salvo = self.SALVO
        for mount, _sgn in self.mounts():
            foe = world.foe(o)
            if foe is None:
                break
            aim = unit(o.lead(foe), o.aim)
            d = aim.rotate_rad(random.uniform(-self.SHELL_SPREAD,
                                              self.SHELL_SPREAD))
            world.projectiles.append(Projectile(
                o, mount, d * self.SHELL_SPEED,
                random.uniform(*self.SHELL_DMG), "shell",
                crit_chance=0.08, bounces=0, pierce=1, knock=260.0,
                size=10.0, life=3.0))
            self.shots += 1
            world.spark(mount, (255, 214, 150), 7, speed=210)
        self.muzzle = 1.0
        world.shake = max(world.shake, 7.0)
        SFX.play("arrow", 0.6)

    def draw(self, s, off, world):
        o = self.owner
        ov = Vector2(off)
        # the cannons first, so the blade passes over them
        for mount, sgn in self.mounts():
            m = mount + ov
            back = -o.aim
            side = Vector2(-back.y, back.x)
            barrel = m - back * (o.r * 0.55)
            pygame.draw.line(s, (60, 64, 78), m, barrel, max(5, int(o.r * 0.20)))
            pygame.draw.line(s, (128, 134, 152), m, barrel,
                             max(3, int(o.r * 0.13)))
            body = [m + side * o.r * 0.16 + back * o.r * 0.20,
                    m - side * o.r * 0.16 + back * o.r * 0.20,
                    m - side * o.r * 0.16 - back * o.r * 0.10,
                    m + side * o.r * 0.16 - back * o.r * 0.10]
            pygame.draw.polygon(s, (74, 78, 94), body)
            pygame.draw.polygon(s, mix(o.colour, (0, 0, 0), 0.3), body, 2)
            if self.muzzle > 0.1:
                blit_glow(s, barrel, o.r * 0.55 * self.muzzle,
                          (255, 208, 140), int(170 * self.muzzle))

        for a, b in self.segments():
            a, b = a + ov, b + ov
            d = unit(b - a)
            side = Vector2(-d.y, d.x)
            w0, w1 = o.r * 0.30, o.r * 0.26      # a slab, not a needle
            blade = [a + side * w0, b + side * w1 - d * 0,
                     b + side * w1 * 0.3 + d * o.r * 0.18,
                     b - side * w1 * 0.9, a - side * w0]
            face = mix((176, 182, 198), (255, 255, 255), 0.5 * self.flash)
            pygame.draw.polygon(s, face, blade)
            pygame.draw.polygon(s, mix(o.dark, (0, 0, 0), 0.4), blade, 3)
            pygame.draw.line(s, mix(face, (255, 255, 255), 0.6),
                             a + side * w0 * 0.2, b + side * w1 * 0.2, 2)
            grip = a - d * o.r * 0.30
            pygame.draw.line(s, (78, 60, 44), grip, a, max(5, int(o.r * 0.16)))
            pygame.draw.line(s, (196, 202, 216), a + side * o.r * 0.22,
                             a - side * o.r * 0.22, max(4, int(o.r * 0.10)))
            if self.flash > 0.05:
                blit_glow(s, b, o.r * 0.8, o.colour, int(120 * self.flash))


# bases first, then each one's upgrade in the same order
WEAPONS = (Sword, Dagger, Gun, Bow, Hammer, Fists, Summoner,
           Greatsword, Flurry, Repeater, Ballista, Maul,
           Gauntlets, Brood)
TIERS = len(WEAPONS) // 2
STARTERS = ("SWORD",)


# ---------------------------------------------------------------------------
# THE BALLS
# ---------------------------------------------------------------------------
class Fighter:
    def __init__(self, name, colour, dark, pos, weapon_cls, player=False,
                 shape=0, max_hp=MAX_HP, dmg_mult=1.0, speed_mult=1.0,
                 team=0):
        self.team = team
        self.name = name
        self.colour = colour
        self.dark = dark
        self.pos = Vector2(pos)
        self.vel = unit(Vector2(random.uniform(-1, 1), random.uniform(-1, 1))) * 260
        self.r = weapon_cls.RADIUS
        self.max_hp = max_hp * weapon_cls.HP_MULT
        self.hp = self.max_hp
        self.weapon = weapon_cls(self)
        self.player = player
        # campaign bosses are not balls, and they do not fight fair
        self.shape = shape            # 0 = a ball, 3+ = that many sides
        self.spin_a = random.uniform(0, TAU)
        self.dmg_mult = dmg_mult
        self.speed_mult = speed_mult
        self.aim = Vector2(1, 0)
        self.flash = 0.0
        self.trail = []
        self.strafe = random.choice((-1.0, 1.0))
        self.strafe_t = random.uniform(1.0, 2.5)
        self.dash_cd = 0.0
        self.dash_t = 0.0
        self.dealt = 0.0
        self.hits = 0

    # -- damage ------------------------------------------------------------
    def take_damage(self, amount, source, world, crit=False):
        if self.hp <= 0:
            return
        amount *= source.dmg_mult * (1.0 - self.weapon.ARMOUR)
        self.hp = max(0.0, self.hp - amount)
        self.flash = 1.0
        source.dealt += amount
        source.hits += 1
        world.floaters.append(
            Floater(self.pos + Vector2(0, -self.r - 8), amount, source.colour, crit))
        world.shake = max(world.shake, 3.0 + amount * 0.06 + (6.0 if crit else 0.0))
        world.hitstop = max(world.hitstop, 0.055 if crit else 0.02)
        SFX.play("crit" if crit else "hit", 0.55)
        if self.hp <= 0:
            world.knockout(self, source)

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    # -- steering ----------------------------------------------------------
    def wall_push(self):
        m = 120.0
        p = Vector2()
        if self.pos.x - ARENA.left < m:
            p.x += 1.0 - (self.pos.x - ARENA.left) / m
        if ARENA.right - self.pos.x < m:
            p.x -= 1.0 - (ARENA.right - self.pos.x) / m
        if self.pos.y - ARENA.top < m:
            p.y += 1.0 - (self.pos.y - ARENA.top) / m
        if ARENA.bottom - self.pos.y < m:
            p.y -= 1.0 - (ARENA.bottom - self.pos.y) / m
        return p

    def lead(self, foe):
        """Aim where the foe will be, not where it is."""
        speed = getattr(self.weapon, "SPEED", 0.0)
        to = foe.pos - self.pos
        if speed <= 0.0:
            return to
        t = to.length() / speed
        return (foe.pos + foe.vel * t * 0.85) - self.pos

    def dash(self, direction):
        self.vel = unit(direction, self.aim) * DASH_SPEED
        self.dash_cd = DASH_CD * self.weapon.DASH_MULT
        self.dash_t = DASH_TIME

    def control_ai(self, dt, world, foe):
        want = self.weapon.PREF
        to = foe.pos - self.pos
        d = to.length()
        n = unit(to)
        desire = Vector2()
        if d > want + 50:
            desire += n
        elif d < want - 50:
            desire -= n * 1.15
        self.strafe_t -= dt
        if self.strafe_t <= 0:
            self.strafe_t = random.uniform(1.2, 2.8)
            self.strafe = -self.strafe
        desire += Vector2(-n.y, n.x) * self.strafe * (0.45 if want <= 1 else 0.85)
        desire += self.wall_push() * 1.7
        if desire.length_squared() > 1e-6:
            self.vel += unit(desire) * ACCEL * dt
        if self.dash_cd <= 0 and random.random() < dt * (1.8 if want <= 1.0 else 0.9):
            if want <= 1.0 and d > 190:
                self.dash(n)
            elif want > 1.0 and d < want * 0.55:
                self.dash(-n)
        self.aim = unit(self.lead(foe), self.aim)

    def control_player(self, dt, world):
        keys = world.keys
        mv = Vector2()
        if keys:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                mv.x -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                mv.x += 1
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                mv.y -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                mv.y += 1
        if mv.length_squared() > 0:
            self.vel += unit(mv) * PLAYER_ACC * dt
        m = Vector2(world.mouse) - self.pos
        if m.length() > 10:
            self.aim = unit(m, self.aim)

    # -- frame -------------------------------------------------------------
    def update(self, dt, world):
        self.flash = max(0.0, self.flash - dt * 4.0)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.dash_t = max(0.0, self.dash_t - dt)
        foe = world.foe(self)
        if self.hp > 0:
            if self.player:
                self.control_player(dt, world)
            elif foe:
                self.control_ai(dt, world, foe)

        self.vel *= max(0.0, 1.0 - DRAG * dt)
        sp = self.vel.length()
        cap = (MAX_SPEED * self.weapon.SPEED_MULT * self.speed_mult
               * (1.9 if self.dash_t > 0 else 1.0))
        if sp > cap:
            self.vel.scale_to_length(cap)
        elif sp < MIN_SPEED and self.hp > 0:
            self.vel = unit(self.vel, (random.uniform(-1, 1),
                                       random.uniform(-1, 1))) * MIN_SPEED
        self.pos += self.vel * dt
        self.bounce_walls(world)

        self.spin_a += (0.5 + self.vel.length() * 0.004) * dt
        self.trail.append((self.pos.x, self.pos.y))
        if len(self.trail) > 15:
            self.trail.pop(0)
        if self.hp > 0:                   # a dead ball stops swinging
            self.weapon.update(dt, world)

    def bounce_walls(self, world):
        hard = 300.0
        if self.pos.x < ARENA.left + self.r:
            self.pos.x = ARENA.left + self.r
            if self.vel.x < 0:
                if -self.vel.x > hard:
                    world.spark(self.pos, self.colour, 5, speed=180)
                self.vel.x = -self.vel.x * BOUNCE
        elif self.pos.x > ARENA.right - self.r:
            self.pos.x = ARENA.right - self.r
            if self.vel.x > 0:
                if self.vel.x > hard:
                    world.spark(self.pos, self.colour, 5, speed=180)
                self.vel.x = -self.vel.x * BOUNCE
        if self.pos.y < ARENA.top + self.r:
            self.pos.y = ARENA.top + self.r
            if self.vel.y < 0:
                self.vel.y = -self.vel.y * BOUNCE
        elif self.pos.y > ARENA.bottom - self.r:
            self.pos.y = ARENA.bottom - self.r
            if self.vel.y > 0:
                self.vel.y = -self.vel.y * BOUNCE

    # -- drawing -----------------------------------------------------------
    def body_points(self, p, scale=1.0):
        """The outline of a non-ball fighter, or None for a ball."""
        if not self.shape:
            return None
        return shape_points(p.x, p.y, self.r * 1.24 * scale,
                            self.shape, self.spin_a)

    def draw(self, s, off, world):
        ov = Vector2(off)
        p = self.pos + ov
        # trail
        last = None
        for i, t in enumerate(self.trail):
            # skip points the ball barely moved between, or a slow ball
            # stacks fifteen glows on one spot and blows out white
            if last and abs(t[0] - last[0]) + abs(t[1] - last[1]) < 7:
                continue
            last = t
            f = (i + 1) / len(self.trail)
            blit_glow(s, (t[0] + ov.x, t[1] + ov.y), self.r * 0.52 * f,
                      self.colour, int(30 * f * f))

        if self.hp <= 0:
            husk = mix(self.dark, (44, 46, 56), 0.65)
            pts = self.body_points(p)
            if pts:
                pygame.draw.polygon(s, husk, pts)
                pygame.draw.polygon(s, mix(husk, (0, 0, 0), 0.45), pts, 2)
            else:
                pygame.draw.circle(s, husk, (int(p.x), int(p.y)), int(self.r))
                pygame.draw.circle(s, mix(husk, (0, 0, 0), 0.45),
                                   (int(p.x), int(p.y)), int(self.r), 2)
            split = mix(husk, (0, 0, 0), 0.55)
            seam = [(-0.58, -0.12), (-0.14, 0.06), (0.16, -0.28),
                    (0.14, 0.08), (0.54, 0.32)]
            pygame.draw.lines(s, split, False,
                              [(p.x + dx * self.r, p.y + dy * self.r)
                               for dx, dy in seam], 2)
            pygame.draw.line(s, split,
                             (p.x - 0.14 * self.r, p.y + 0.06 * self.r),
                             (p.x - 0.22 * self.r, p.y + 0.56 * self.r), 2)
            return

        blit_glow(s, p, int(self.r * 1.9), self.colour, 62)
        body = mix(self.dark, self.colour, 0.85)
        if self.flash > 0:
            # a small ball washed fully white stops reading as its own side
            body = mix(body, (255, 255, 255), 0.5 * self.flash)
        pts = self.body_points(p)
        lit = mix(body, (255, 255, 255), 0.35)
        rim = mix(self.dark, (0, 0, 0), 0.35)
        if pts:
            pygame.draw.polygon(s, body, pts)
            pygame.draw.polygon(s, lit, self.body_points(
                p + Vector2(-self.r * 0.16, -self.r * 0.18), 0.48))
            pygame.draw.polygon(s, rim, pts, 2)
        else:
            pygame.draw.circle(s, body, (int(p.x), int(p.y)), int(self.r))
            # a little shading so it reads as a ball, not a disc
            pygame.draw.circle(s, lit,
                               (int(p.x - self.r * 0.3), int(p.y - self.r * 0.33)),
                               int(self.r * 0.42))
            pygame.draw.circle(s, rim, (int(p.x), int(p.y)), int(self.r), 2)

        # health ring
        frac = clamp(self.hp / self.max_hp, 0.0, 1.0)
        rr = pygame.Rect(0, 0, self.r * 2 + 9, self.r * 2 + 9)
        rr.center = (int(p.x), int(p.y))
        pygame.draw.arc(s, mix(BG, self.dark, 0.8), rr, 0, TAU, 3)
        if frac > 0.01:
            pygame.draw.arc(s, self.colour, rr,
                            TAU * 0.25, TAU * 0.25 + TAU * frac, 3)
        if self.dash_t > 0:
            # a wide white halo buries a small ball instead of flagging it
            blit_glow(s, p, int(self.r * 2.1), (255, 255, 255), 48)

        self.weapon.draw(s, off, world)




# ---------------------------------------------------------------------------
# THE LITTLE ONES
#
# Summoned balls live beside the two fighters rather than among them: the
# whole game assumes exactly two, from who the HUD belongs to down to who
# won. A minion can be shot and cut like anything else, but it can never
# be the thing that wins or loses the fight.
# ---------------------------------------------------------------------------
class Minion:
    R = 8.0
    HP = 80.0
    DMG = (12.0, 17.0)
    HIT_CD = 0.55
    SPEED = 430.0             # faster than anything can run
    LIFE = 26.0

    def __init__(self, owner, pos, scale=1.0):
        self.owner = owner
        self.pos = Vector2(pos)
        self.vel = unit(Vector2(random.uniform(-1, 1),
                                random.uniform(-1, 1))) * self.SPEED
        self.scale = scale
        self.hp = self.HP * scale
        self.r = self.R * (1.0 + (scale - 1.0) * 0.5)
        self.cool = 0.0
        self.flash = 0.0
        self.life = self.LIFE

    BURST = (18.0, 26.0)
    BURST_R = 38.0

    def hurt(self, amount, world):
        self.hp -= amount
        self.flash = 1.0
        if self.hp > 0:
            return
        # it goes off when it dies, so clearing the swarm is not free
        world.spark(self.pos, self.owner.colour, 12, speed=240)
        world.shake = max(world.shake, 3.0)
        foe = world.foe(self.owner)
        if foe and foe.hp > 0:
            if (foe.pos - self.pos).length() <= self.BURST_R + foe.r:
                foe.take_damage(random.uniform(*self.BURST) * self.scale,
                                self.owner, world)
                foe.vel += unit(foe.pos - self.pos) * (120.0 / foe.weapon.MASS)

    def update(self, dt, world):
        self.life -= dt
        self.cool = max(0.0, self.cool - dt)
        self.flash = max(0.0, self.flash - dt * 4.0)
        if self.hp <= 0 or self.life <= 0 or self.owner.hp <= 0:
            return False

        foe = world.foe(self.owner)
        if foe and foe.hp > 0:
            self.vel += unit(foe.pos - self.pos) * 420.0 * dt
        self.vel.scale_to_length(self.SPEED)
        self.pos += self.vel * dt

        if self.pos.x < ARENA.left + self.r:
            self.pos.x, self.vel.x = ARENA.left + self.r, abs(self.vel.x)
        elif self.pos.x > ARENA.right - self.r:
            self.pos.x, self.vel.x = ARENA.right - self.r, -abs(self.vel.x)
        if self.pos.y < ARENA.top + self.r:
            self.pos.y, self.vel.y = ARENA.top + self.r, abs(self.vel.y)
        elif self.pos.y > ARENA.bottom - self.r:
            self.pos.y, self.vel.y = ARENA.bottom - self.r, -abs(self.vel.y)

        if foe and foe.hp > 0 and self.cool <= 0:
            if (foe.pos - self.pos).length() <= foe.r + self.r:
                foe.take_damage(random.uniform(*self.DMG) * self.scale,
                                self.owner, world)
                push = unit(self.pos - foe.pos)
                self.vel += push * 260
                self.cool = self.HIT_CD
        return True

    def draw(self, s, off):
        p = self.pos + Vector2(off)
        col = mix(self.owner.colour, (255, 255, 255), 0.45 * self.flash)
        fade = self.life < 4.0 and int(self.life * 6) % 2 == 0
        if fade:
            col = mix(col, BG, 0.5)
        blit_glow(s, p, self.r * 2.2, self.owner.colour, 45)
        pygame.draw.circle(s, col, (int(p.x), int(p.y)), int(self.r))
        pygame.draw.circle(s, mix(self.owner.dark, (0, 0, 0), 0.3),
                           (int(p.x), int(p.y)), int(self.r), 1)


# ---------------------------------------------------------------------------
# PICKUPS
# ---------------------------------------------------------------------------
class Orb:
    HEAL = 90.0

    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.life = 11.0
        self.r = 11.0
        self.t = random.uniform(0, TAU)

    def update(self, dt, world):
        self.life -= dt
        self.t += dt * 3.0
        for f in world.fighters:
            if f.hp > 0 and (f.pos - self.pos).length() < f.r + self.r:
                f.heal(self.HEAL)
                world.spark(self.pos, GREEN, 16, speed=260)
                world.floaters.append(
                    Floater(self.pos + Vector2(0, -18), self.HEAL, GREEN))
                SFX.play("pickup", 0.5)
                return False
        return self.life > 0

    def draw(self, s, off):
        p = self.pos + Vector2(off)
        pulse = 1.0 + 0.12 * math.sin(self.t)
        fade = 255 if self.life > 2.5 else int(120 + 135 * abs(math.sin(self.life * 9)))
        r = int(self.r * pulse)
        blit_glow(s, p, r * 2.3, GREEN, 75)
        col = (GREEN[0], GREEN[1], GREEN[2])
        pygame.draw.circle(s, mix(BG, col, 0.45), (int(p.x), int(p.y)), r)
        pygame.draw.circle(s, col, (int(p.x), int(p.y)), r, 2)
        bar = int(r * 0.62)
        thick = max(3, int(r * 0.34))
        surf = pygame.Surface((bar * 2, bar * 2), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*col, fade), (bar - thick // 2, 0, thick, bar * 2))
        pygame.draw.rect(surf, (*col, fade), (0, bar - thick // 2, bar * 2, thick))
        s.blit(surf, (p.x - bar, p.y - bar))


# ---------------------------------------------------------------------------
# THE LADDER
#
# Campaign progress is one number: how many levels have been cleared. Every
# unlock is derived from it, so a save file cannot contradict itself - the
# worst a missing or corrupt one can do is cost you progress.
# ---------------------------------------------------------------------------
def _save_dir():
    """Where progress goes. Never beside the game, which may be read-only."""
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(root, "BallBrawl")
    elif sys.platform == "darwin":
        d = os.path.expanduser("~/Library/Application Support/BallBrawl")
    else:
        root = (os.environ.get("XDG_DATA_HOME")
                or os.path.expanduser("~/.local/share"))
        d = os.path.join(root, "ball-brawl")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except OSError:
        return os.path.dirname(os.path.abspath(__file__))


SAVE_NAME = "progress.json"

CAMPAIGN = (
    dict(name="THE CUBE", sides=4, weapon=Dagger,
         colour=(156, 166, 188), dark=(56, 62, 80),
         hp=0.85, dmg=1.0, spd=1.0,
         brief="A block with four knives. Beat it and they are yours.",
         reward=("weapon", "DAGGER")),
    dict(name="THE BRICK", sides=4, weapon=Gun,
         colour=(104, 214, 178), dark=(20, 76, 64),
         hp=0.95, dmg=1.0, spd=1.02,
         brief="It has the gun, it keeps its distance, and you want the gun.",
         reward=("weapon", "GUN")),
    dict(name="THE SLAB", sides=4, weapon=Bow,
         colour=(244, 170, 70), dark=(110, 66, 14),
         hp=1.12, dmg=1.0, spd=0.95,
         brief="Heavy and patient. It shoots from the far wall and waits.",
         reward=("weapon", "BOW")),
    dict(name="THE DIE", sides=4, weapon=Hammer,
         colour=(186, 124, 246), dark=(70, 32, 110),
         hp=1.0, dmg=1.0, spd=1.02,
         brief="The hammer laughs at blades. Bring something that shoots.",
         reward=("weapon", "HAMMER")),
    dict(name="THE MONOLITH", sides=4, weapon=Hammer,
         colour=(198, 208, 230), dark=(76, 82, 100),
         hp=1.20, dmg=1.05, spd=0.92,
         brief="The last block on the ladder. It lands once and you feel it.",
         reward=("done", None)),
    dict(name="THE LATHE", sides=4, weapon=Flurry,
         colour=(240, 96, 152), dark=(108, 24, 62),
         hp=1.05, dmg=1.0, spd=1.05,
         brief="The cube came back with eight knives and somewhere to be.",
         reward=("weapon", "FLURRY")),
    dict(name="THE HIVE", sides=4, weapon=Summoner,
         colour=(126, 200, 246), dark=(28, 74, 112),
         hp=1.50, dmg=1.0, spd=0.95,
         brief="It never comes to you. It just keeps sending the little ones.",
         reward=("weapon", "SUMMONER")),
    dict(name="THE TITAN", sides=4, weapon=Fists,
         colour=(250, 124, 92), dark=(112, 38, 24),
         hp=1.25, dmg=1.0, spd=0.95,
         brief="Twice the block and twice the health. It brought no weapon.",
         reward=("weapon", "FISTS")),
    dict(name="THE BULWARK", sides=4, weapon=Greatsword,
         colour=(214, 206, 158), dark=(96, 88, 48),
         hp=1.10, dmg=1.0, spd=0.98,
         brief="The cube that grew up. Five blades and all the time it needs.",
         reward=("weapon", "GREATSWORD")),
    dict(name="THE BATTERY", sides=4, weapon=Repeater,
         colour=(120, 230, 196), dark=(24, 92, 76),
         hp=1.20, dmg=1.0, spd=1.02,
         brief="It does not stop firing long enough for you to cross.",
         reward=("weapon", "REPEATER")),
    dict(name="THE ENGINE", sides=4, weapon=Ballista,
         colour=(250, 186, 96), dark=(120, 74, 16),
         hp=1.30, dmg=1.0, spd=0.92,
         brief="Three bolts at a time, from the other end of the street.",
         reward=("weapon", "BALLISTA")),
    dict(name="THE ANVIL", sides=4, weapon=Maul,
         colour=(190, 198, 216), dark=(70, 76, 94),
         hp=1.35, dmg=1.0, spd=0.95,
         brief="Two heads, one shaft, and no side of it that is safe.",
         reward=("weapon", "MAUL")),
    dict(name="THE FORGE", sides=4, weapon=Gauntlets,
         colour=(252, 142, 104), dark=(118, 46, 28),
         hp=1.30, dmg=1.0, spd=0.95,
         brief="Four fists, and it has worked out where you like to stand.",
         reward=("weapon", "GAUNTLETS")),
    dict(name="THE NEST", sides=4, weapon=Brood,
         colour=(150, 170, 250), dark=(44, 60, 130),
         hp=1.60, dmg=1.0, spd=0.92,
         brief="The hive, but worse. They come two at a time and they last.",
         reward=("weapon", "BROOD")),
    dict(name="THE COLOSSUS", sides=4, weapon=Buster,
         colour=(236, 92, 72), dark=(104, 26, 20),
         hp=7.0, dmg=1.30, spd=0.70, arena=2.6, party=3,
         brief="It fills the street. Bring three, and keep them apart.",
         reward=("crown", None)),
)


def unlocked_weapons(cleared):
    """Weapon names available after clearing that many levels."""
    names = set(STARTERS)
    for lv in CAMPAIGN[:cleared]:
        kind, val = lv["reward"]
        if kind == "weapon":
            names.add(val)
    return names


def hp_bonus(cleared):
    """You toughen up as you climb - 5% more health per level cleared."""
    return 0.05 * min(cleared, len(CAMPAIGN))


def reward_label(lv):
    kind, val = lv["reward"]
    if kind == "weapon":
        return val
    return "THE CROWN" if kind == "crown" else "THE BELT"


def unlock_level(name):
    """Which level hands this weapon over - 0 if you start with it."""
    for i, lv in enumerate(CAMPAIGN):
        if lv["reward"] == ("weapon", name):
            return i + 1
    return 0


def load_progress():
    try:
        with open(os.path.join(_save_dir(), SAVE_NAME), encoding="utf-8") as fh:
            return int(clamp(int(json.load(fh).get("cleared", 0)),
                             0, len(CAMPAIGN)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def save_progress(cleared):
    try:
        with open(os.path.join(_save_dir(), SAVE_NAME), "w",
                  encoding="utf-8") as fh:
            json.dump({"cleared": int(cleared)}, fh)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# THE GAME
#
# One object holds the whole world and the four screens it can be showing.
# update() never touches a font or the display, so the fight can be run
# headless - which is how the matchups were balanced.
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.state = "menu"          # menu | campaign | fight | ko
        self.mode = "versus"         # versus | campaign
        self.paused = False
        self.speed = 1
        self.orbs_on = True
        self.human = False
        self.pick = [0, 0]           # weapon index for red, blue
        self.score = [0, 0]
        self.cleared = load_progress()
        self.level = min(self.cleared, len(CAMPAIGN) - 1)
        self.camp_pick = 0
        self.camp_party = [0, 0, 0]
        self.slot = 0
        self.camp_win = False
        self.unlock_text = ""
        self.fighters = []
        self.projectiles = []
        self.minions = []
        self.particles = []
        self.floaters = []
        self.orbs = []
        self.shake = 0.0
        self.hitstop = 0.0
        self.slowmo = 0.0
        self.flash_t = 0.0
        self.clock_t = 0.0
        self.banner_t = 0.0
        self.winner = None
        self.orb_timer = 7.0
        self.order = 0
        self.cam = Vector2()
        self.keys = None
        self.mouse = (W // 2, H // 2)

    # -- world -------------------------------------------------------------
    def foes(self, f):
        """Everyone still standing on the other side."""
        return [o for o in self.fighters if o.team != f.team and o.hp > 0]

    def foe(self, f):
        """The nearest of them: what a weapon aims at and a ball steers to."""
        best, near = None, 1e18
        for o in self.foes(f):
            d = (o.pos - f.pos).length_squared()
            if d < near:
                best, near = o, d
        if best is not None:
            return best
        for o in self.fighters:        # all of them down: keep facing one
            if o.team != f.team:
                return o
        return None

    def team_of(self, side):
        return [f for f in self.fighters if f.team == side]

    def spark(self, pos, colour, n, speed=200.0):
        for _ in range(n):
            a = random.uniform(0, TAU)
            v = Vector2(math.cos(a), math.sin(a)) * random.uniform(0.25, 1.0) * speed
            self.particles.append(Particle(pos, v, random.uniform(0.18, 0.48),
                                           colour, random.uniform(2.0, 4.5)))

    def start_fight(self):
        global ARENA
        lv = (CAMPAIGN[self.level] if self.mode == "campaign"
              and self.level < len(CAMPAIGN) else None)
        big = lv.get("arena", 1.0) if lv else 1.0
        ARENA = pygame.Rect(VIEW.left, VIEW.top,
                            int(VIEW.w * big), int(VIEW.h * big))
        left = (ARENA.left + ARENA.w * 0.20, ARENA.centery)
        right = (ARENA.left + ARENA.w * 0.80, ARENA.centery)
        if self.mode == "campaign":
            if self.level > self.cleared:
                return
            party = lv.get("party", 1)
            mine = MAX_HP * (1.0 + hp_bonus(self.cleared))
            self.fighters = []
            for k in range(party):
                w = WEAPONS[self.camp_party[k] if party > 1 else self.camp_pick]
                spread = (k - (party - 1) * 0.5) * (ARENA.h * 0.16)
                self.fighters.append(Fighter(
                    "YOU" if party == 1 else w.NAME, RED, RED_D,
                    (left[0], left[1] + spread), w,
                    player=self.human and k == 0, max_hp=mine, team=0))
            self.fighters.append(
                Fighter(lv["name"], lv["colour"], lv["dark"], right,
                        lv["weapon"], shape=lv["sides"],
                        max_hp=MAX_HP * lv["hp"], dmg_mult=lv["dmg"],
                        speed_mult=lv["spd"], team=1))
        else:
            self.fighters = [
                Fighter("RED", RED, RED_D, left, WEAPONS[self.pick[0]],
                        player=self.human),
                Fighter("BLUE", BLUE, BLUE_D, right, WEAPONS[self.pick[1]],
                        team=1),
            ]
        self.projectiles.clear()
        self.minions.clear()
        self.particles.clear()
        self.floaters.clear()
        self.orbs.clear()
        self.state = "fight"
        self.paused = False
        self.winner = None
        self.clock_t = 0.0
        self.banner_t = 0.0
        self.shake = 0.0
        self.slowmo = 0.0
        self.hitstop = 0.0
        self.orb_timer = 7.0
        self.cam = Vector2()
        self.camera(1.0)

    def knockout(self, loser, winner):
        if self.state != "fight":
            return
        self.spark(loser.pos, loser.colour, 40, speed=430)
        if any(f.hp > 0 for f in self.team_of(loser.team)):
            SFX.play("ko", 0.5)        # a team-mate went down, not the side
            self.shake = max(self.shake, 14.0)
            return
        self.state = "ko"
        self.winner = winner
        self.banner_t = 0.0
        self.slowmo = 1.5
        self.shake = 26.0
        self.flash_t = 0.3
        if self.mode == "campaign":
            self.record_level(winner)
        else:
            self.score[0 if winner.team == 0 else 1] += 1
        self.spark(loser.pos, loser.colour, 60, speed=520)
        self.spark(loser.pos, (255, 255, 255), 24, speed=300)
        SFX.play("ko", 1.0)

    def record_level(self, winner):
        """A campaign win only counts the first time, and it is saved at once."""
        self.camp_win = winner.team == 0
        self.unlock_text = ""
        if not self.camp_win or self.level != self.cleared:
            return
        kind, val = CAMPAIGN[self.level]["reward"]
        self.cleared = min(len(CAMPAIGN), self.cleared + 1)
        save_progress(self.cleared)
        if kind == "weapon":
            self.unlock_text = "UNLOCKED:  " + val
        elif kind == "hp":
            self.unlock_text = "REWARD:  +%d%% MAX HP" % round(val * 100.0)
        elif kind == "crown":
            self.unlock_text = "REWARD:  THE CROWN"
        else:
            self.unlock_text = "REWARD:  THE BELT"

    def spawn_orb(self):
        for _ in range(24):
            p = Vector2(random.uniform(ARENA.left + 70, ARENA.right - 70),
                        random.uniform(ARENA.top + 70, ARENA.bottom - 70))
            if all((p - f.pos).length() > 150 for f in self.fighters):
                self.orbs.append(Orb(p))
                return

    def collide(self):
        for i in range(len(self.fighters)):
            for j in range(i + 1, len(self.fighters)):
                self.collide_pair(self.fighters[i], self.fighters[j])

    def collide_pair(self, a, b):
        d = b.pos - a.pos
        dist = d.length()
        touch = a.r + b.r
        if dist < 1e-6 or dist >= touch:
            return
        n = d / dist
        ma, mb = a.weapon.MASS, b.weapon.MASS
        push = touch - dist
        a.pos -= n * push * (mb / (ma + mb))    # the lighter one gives way
        b.pos += n * push * (ma / (ma + mb))
        rel = (b.vel - a.vel).dot(n)
        if rel < 0:
            j = -2.04 * rel / (1.0 / ma + 1.0 / mb)
            a.vel -= n * (j / ma)
            b.vel += n * (j / mb)
            if -rel > 260:
                self.spark((a.pos + b.pos) * 0.5, (255, 255, 255), 6, speed=220)
                self.shake = max(self.shake, 5.0)

    def camera(self, dt):
        """Centre the view on your side, and never past the walls."""
        if ARENA.w <= VIEW.w and ARENA.h <= VIEW.h:
            self.cam = Vector2(VIEW.centerx - ARENA.centerx,
                               VIEW.centery - ARENA.centery)
            return
        mine = [f for f in self.fighters if f.team == 0 and f.hp > 0]
        if not mine:
            mine = self.fighters or []
        if not mine:
            return
        focus = Vector2()
        for f in mine:
            focus += f.pos
        focus /= len(mine)
        want = Vector2(VIEW.centerx - focus.x, VIEW.centery - focus.y)
        want.x = clamp(want.x, VIEW.right - ARENA.right, VIEW.left - ARENA.left)
        want.y = clamp(want.y, VIEW.bottom - ARENA.bottom, VIEW.top - ARENA.top)
        self.cam += (want - self.cam) * min(1.0, 6.0 * dt)

    def update(self, dt):
        if self.hitstop > 0.0:
            self.hitstop -= dt
            dt *= 0.12
        if self.slowmo > 0.0:
            self.slowmo -= dt
            dt *= 0.35
        self.shake = max(0.0, self.shake - dt * 44.0)
        self.flash_t = max(0.0, self.flash_t - dt)

        if self.state == "fight":
            self.clock_t += dt
        elif self.state == "ko":
            self.banner_t += dt

        # Whoever moves second aims at fresher information, so the order
        # alternates - otherwise blue quietly wins every mirror match.
        self.order ^= 1
        for f in (self.fighters[::-1] if self.order else self.fighters):
            f.update(dt, self)
        self.collide()

        for p in self.projectiles:
            p.update(dt, self)
        self.projectiles = [p for p in self.projectiles if not p.dead]
        self.minions = [m for m in self.minions if m.update(dt, self)]
        self.particles = [p for p in self.particles if p.update(dt)]
        self.floaters = [f for f in self.floaters if f.update(dt)]

        if self.orbs_on and self.state == "fight":
            self.orb_timer -= dt
            if self.orb_timer <= 0.0:
                self.orb_timer = random.uniform(8.0, 12.0)
                if len(self.orbs) < 2:
                    self.spawn_orb()
        self.orbs = [o for o in self.orbs if o.update(dt, self)]
        self.camera(dt)

    # -- input -------------------------------------------------------------
    def party_size(self):
        if self.mode != "campaign" or self.level >= len(CAMPAIGN):
            return 1
        return CAMPAIGN[self.level].get("party", 1)

    def unlocked_idx(self):
        names = unlocked_weapons(self.cleared)
        return [i for i, w in enumerate(WEAPONS) if w.NAME in names]

    def menu_layout(self):
        """Every clickable thing on the versus menu: (rect, kind, value)."""
        items = [(pygame.Rect(W - 216, 22, 180, 40), "camp", None)]
        cw, ch, gap = 188, 42, 4
        for side in (0, 1):
            for i in range(len(WEAPONS)):
                col, row = divmod(i, TIERS)      # bases left, upgrades right
                x = (56 + col * (cw + 6) if side == 0
                     else W - 56 - cw - (1 - col) * (cw + 6))
                items.append((pygame.Rect(x, 130 + row * (ch + gap), cw, ch),
                              "pick", (side, i)))
        bx = W // 2 - 152
        items.append((pygame.Rect(bx, 512, 304, 36), "human", None))
        items.append((pygame.Rect(bx, 552, 304, 36), "orbs", None))
        items.append((pygame.Rect(bx, 594, 304, 50), "start", None))
        return items

    def camp_layout(self):
        """Every clickable thing on the campaign screen."""
        items = [(pygame.Rect(W - 216, 22, 180, 40), "back", None),
                 (pygame.Rect(W - 216, 66, 180, 28), "human", None)]
        top, h, gap = 100, 26, 3
        for i in range(len(CAMPAIGN)):
            items.append((pygame.Rect(56, top + i * (h + gap), W - 112, h),
                          "level", i))
        party = self.party_size()
        if party > 1:
            sw = 116
            sx = (W - (party * sw + (party - 1) * 8)) // 2
            for k in range(party):
                items.append((pygame.Rect(sx + k * (sw + 8), 588, sw, 24),
                              "slot", k))
        bw, bh, bgap = 84, 42, 8
        span = TIERS * bw + (TIERS - 1) * bgap
        x0 = (W - span) // 2
        for i in range(len(WEAPONS)):
            col, row = divmod(i, TIERS)
            items.append((pygame.Rect(x0 + row * (bw + bgap),
                                      616 + col * (bh + 4), bw, bh),
                          "ball", i))
        items.append((pygame.Rect(W // 2 - 152, 710, 304, 46), "start", None))
        return items

    def open_campaign(self):
        self.mode = "campaign"
        self.state = "campaign"
        self.level = min(self.cleared, len(CAMPAIGN) - 1)
        picks = self.unlocked_idx()
        if self.camp_pick not in picks:
            self.camp_pick = picks[0]
        self.camp_party = [i if i in picks else picks[0]
                           for i in self.camp_party]
        SFX.play("click")

    def open_versus(self):
        self.mode = "versus"
        self.state = "menu"
        SFX.play("click")

    def set_pick(self, side, i):
        if WEAPONS[i].NAME in unlocked_weapons(self.cleared):
            self.pick[side] = i
            SFX.play("click")

    def after_ko(self):
        """What SPACE does once someone is down."""
        if self.mode == "campaign" and self.camp_win:
            self.level = min(len(CAMPAIGN) - 1, self.level + 1)
            self.state = "campaign"
        else:
            self.start_fight()

    def handle(self, ev):
        """False means quit."""
        if ev.type == pygame.KEYDOWN:
            return self.handle_key(ev.key)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.handle_click(ev.pos)
        return True

    def handle_key(self, k):
        if k == pygame.K_ESCAPE:
            if self.state == "menu":
                return False
            if self.state == "campaign":
                self.open_versus()
            elif self.mode == "campaign":
                self.state = "campaign"
                self.paused = False
            else:
                self.state = "menu"
                self.paused = False
            return True
        if k == pygame.K_m:
            SFX.muted = not SFX.muted
        elif k == pygame.K_f:
            self.speed = 1 if self.speed >= 3 else self.speed + 1
        elif k == pygame.K_p and self.state in ("fight", "ko"):
            self.paused = not self.paused
        elif k == pygame.K_TAB and self.state in ("menu", "campaign"):
            self.human = not self.human
            SFX.play("click")
        elif self.state == "menu":
            self.menu_key(k)
        elif self.state == "campaign":
            self.campaign_key(k)
        else:
            self.fight_key(k)
        return True

    BLUE_KEYS = (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r,
                 pygame.K_t, pygame.K_y, pygame.K_u)

    def menu_key(self, k):
        if pygame.K_1 <= k <= pygame.K_7:
            self.set_pick(0, k - pygame.K_1)
        elif k in self.BLUE_KEYS:
            self.set_pick(1, self.BLUE_KEYS.index(k))
        elif k == pygame.K_o:
            self.orbs_on = not self.orbs_on
            SFX.play("click")
        elif k == pygame.K_c:
            self.open_campaign()
        elif k in (pygame.K_SPACE, pygame.K_RETURN):
            self.start_fight()

    def campaign_key(self, k):
        picks = self.unlocked_idx()
        if k in (pygame.K_DOWN, pygame.K_s):
            self.level = min(self.cleared, len(CAMPAIGN) - 1, self.level + 1)
            SFX.play("click")
        elif k in (pygame.K_UP, pygame.K_w):
            self.level = max(0, self.level - 1)
            SFX.play("click")
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            step = 1 if k in (pygame.K_RIGHT, pygame.K_d) else -1
            at = picks.index(self.camp_pick) if self.camp_pick in picks else 0
            self.camp_pick = picks[(at + step) % len(picks)]
            SFX.play("click")
        elif pygame.K_1 <= k <= pygame.K_9 and k - pygame.K_1 <= self.cleared:
            self.level = k - pygame.K_1
            SFX.play("click")
        elif k == pygame.K_c:
            self.open_versus()
        elif k in (pygame.K_SPACE, pygame.K_RETURN):
            self.start_fight()

    def fight_key(self, k):
        if k == pygame.K_r:
            self.start_fight()
        elif k == pygame.K_SPACE:
            if self.state == "ko":
                self.after_ko()
            elif self.human and self.fighters and self.fighters[0].dash_cd <= 0:
                me = self.fighters[0]
                me.dash(me.aim)

    def handle_click(self, pos):
        if self.state == "menu":
            for rect, kind, val in self.menu_layout():
                if not rect.collidepoint(pos):
                    continue
                if kind == "pick":
                    self.set_pick(val[0], val[1])
                elif kind == "camp":
                    self.open_campaign()
                elif kind == "human":
                    self.human = not self.human
                    SFX.play("click")
                elif kind == "orbs":
                    self.orbs_on = not self.orbs_on
                    SFX.play("click")
                elif kind == "start":
                    self.start_fight()
                break
        elif self.state == "campaign":
            for rect, kind, val in self.camp_layout():
                if not rect.collidepoint(pos):
                    continue
                if kind == "level" and val <= self.cleared:
                    self.level = val
                    SFX.play("click")
                elif kind == "ball" and val in self.unlocked_idx():
                    if self.party_size() > 1:
                        self.camp_party[self.slot] = val
                        self.slot = (self.slot + 1) % self.party_size()
                    else:
                        self.camp_pick = val
                    SFX.play("click")
                elif kind == "slot":
                    self.slot = val
                    SFX.play("click")
                elif kind == "human":
                    self.human = not self.human
                    SFX.play("click")
                elif kind == "back":
                    self.open_versus()
                elif kind == "start":
                    self.start_fight()
                break
        elif self.state == "ko":
            self.after_ko()

    # -- drawing -----------------------------------------------------------
    def draw(self, s):
        s.fill(BG)
        if self.state == "menu":
            self.draw_menu(s)
        elif self.state == "campaign":
            self.draw_campaign(s)
        else:
            off = [self.cam.x, self.cam.y]
            if self.shake > 0.2:
                off[0] += random.uniform(-self.shake, self.shake) * 0.5
                off[1] += random.uniform(-self.shake, self.shake) * 0.5
            off = tuple(off)
            self.draw_arena(s, off)
            self.draw_hud(s)
            if self.state == "ko":
                self.draw_banner(s)
            if self.paused:
                self.draw_paused(s)
        if self.flash_t > 0:
            v = int(190 * (self.flash_t / 0.3))
            f = pygame.Surface((W, H), pygame.SRCALPHA)
            f.fill((255, 255, 255, clamp(v, 0, 255)))
            s.blit(f, (0, 0))

    def draw_arena(self, s, off):
        inner = ARENA.move(off)
        clip = s.get_clip()
        s.set_clip(VIEW)
        s.blit(city_floor(ARENA.w, ARENA.h), inner.topleft)

        for o in self.orbs:
            o.draw(s, off)
        for m in self.minions:
            m.draw(s, off)
        for p in self.projectiles:
            p.draw(s, off)
        for f in self.fighters:
            f.draw(s, off, self)
        for p in self.particles:
            p.draw(s, off)
        for f in self.floaters:
            f.draw(s, off)

        pygame.draw.rect(s, WALL, inner, 3)
        L = 34
        for cx, cy, dx, dy in ((inner.left, inner.top, 1, 1),
                               (inner.right - 1, inner.top, -1, 1),
                               (inner.left, inner.bottom - 1, 1, -1),
                               (inner.right - 1, inner.bottom - 1, -1, -1)):
            pygame.draw.line(s, INK, (cx, cy), (cx + dx * L, cy), 3)
            pygame.draw.line(s, INK, (cx, cy), (cx, cy + dy * L), 3)
        s.set_clip(clip)
        self.draw_minimap(s)

        tags = []
        if self.speed > 1:
            tags.append("%dx" % self.speed)
        if SFX.muted:
            tags.append("MUTED")
        if tags:
            text(s, "  ".join(tags), 17, (VIEW.right - 20, VIEW.top + 26),
                 DIM, right=True)
        if self.human and self.fighters:
            me = self.fighters[0]
            ready = me.dash_cd <= 0
            text(s, "DASH " + ("READY" if ready else "%.1f" % me.dash_cd), 17,
                 (VIEW.left + 20, VIEW.top + 18), GOLD if ready else DIM)

    def draw_minimap(self, s):
        """Only worth drawing when the ground is bigger than the window."""
        if ARENA.w <= VIEW.w and ARENA.h <= VIEW.h:
            return
        mw = 168
        mh = max(40, int(mw * ARENA.h / ARENA.w))
        box = pygame.Rect(0, 0, mw, mh)
        box.bottomright = (VIEW.right - 14, VIEW.bottom - 14)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((10, 11, 16, 190))
        s.blit(panel, box.topleft)
        pygame.draw.rect(s, (70, 76, 94), box, 1)

        def spot(p):
            return (box.left + int((p.x - ARENA.left) / ARENA.w * mw),
                    box.top + int((p.y - ARENA.top) / ARENA.h * mh))

        seen = pygame.Rect(0, 0, int(VIEW.w / ARENA.w * mw),
                           int(VIEW.h / ARENA.h * mh))
        seen.topleft = spot(Vector2(VIEW.left - self.cam.x, VIEW.top - self.cam.y))
        pygame.draw.rect(s, (86, 94, 116), seen, 1)
        for m in self.minions:
            pygame.draw.circle(s, mix(m.owner.colour, BG, 0.4), spot(m.pos), 1)
        for f in self.fighters:
            if f.hp <= 0:
                continue
            pygame.draw.circle(s, f.colour, spot(f.pos),
                               4 if f.r > 30 else 3)

    @staticmethod
    def stat_line(f):
        parts = ["%d HP" % int(f.hp), "%d HITS" % f.hits]
        if f.weapon.shots and getattr(f.weapon, "SPEED", 0):
            parts.append("%d%% ACC" % round(100.0 * f.hits / f.weapon.shots))
        elif isinstance(f.weapon, Summoner):
            parts.append("%d SUMMONED" % f.weapon.shots)
        return "   ".join(parts)

    def draw_hud(self, s):
        pygame.draw.rect(s, PANEL, (0, 0, W, HUD_H - 6))
        pygame.draw.line(s, (44, 48, 62), (0, HUD_H - 6), (W, HUD_H - 6), 2)
        ours, theirs = self.team_of(0), self.team_of(1)
        if not ours or not theirs:
            return
        a_hp = sum(f.hp for f in ours)
        b_hp = sum(f.hp for f in theirs)
        fa = a_hp / max(1e-6, a_hp + b_hp)
        pa = int(round(fa * 100))
        lead, rival = ours[0], theirs[0]

        text(s, lead.name if len(ours) == 1 else "YOUR TEAM", 30, (26, 6),
             lead.colour)
        text(s, "  ".join(f.weapon.NAME for f in ours), 17, (27, 44), DIM)
        text(s, rival.name, 30, (W - 26, 23), rival.colour, right=True)
        text(s, rival.weapon.NAME, 17, (W - 27, 53), DIM, right=True)

        text(s, "VS", 24, (W // 2, 20), INK, center=True)
        mid = ("LEVEL %d / %d" % (self.level + 1, len(CAMPAIGN))
               if self.mode == "campaign" else
               "%d - %d" % (self.score[0], self.score[1]))
        text(s, mid, 19, (W // 2, 46), DIM, center=True)

        # One bar, split where the two sides meet - the split is the whole
        # story of the fight, so the marker sits on it.
        bar = pygame.Rect(250, 62, W - 500, 26)
        pygame.draw.rect(s, (11, 12, 18), bar.inflate(6, 6))
        split = int(bar.w * fa)
        pygame.draw.rect(s, lead.dark, (bar.x, bar.y, split, bar.h))
        pygame.draw.rect(s, lead.colour, (bar.x, bar.y, split, bar.h // 2))
        pygame.draw.rect(s, rival.dark, (bar.x + split, bar.y,
                                         bar.w - split, bar.h))
        pygame.draw.rect(s, rival.colour, (bar.x + split, bar.y,
                                           bar.w - split, bar.h // 2))
        pygame.draw.rect(s, (62, 68, 86), bar, 2)
        mx = bar.x + split
        pygame.draw.line(s, INK, (mx, bar.top - 3), (mx, bar.bottom + 3), 2)
        pygame.draw.polygon(s, INK, [(mx - 6, bar.top - 3), (mx + 6, bar.top - 3),
                                     (mx, bar.top + 6)])
        pygame.draw.polygon(s, INK, [(mx - 6, bar.bottom + 3),
                                     (mx + 6, bar.bottom + 3),
                                     (mx, bar.bottom - 6)])

        # with a party, each ball gets a pip of its own under the bar
        if len(ours) > 1:
            px = bar.left
            for f in ours:
                w = (bar.w * 0.3) / len(ours)
                frac = clamp(f.hp / f.max_hp, 0.0, 1.0)
                pygame.draw.rect(s, (14, 15, 22), (px, bar.bottom + 8, w - 4, 6))
                pygame.draw.rect(s, f.colour if f.hp > 0 else (60, 64, 78),
                                 (px, bar.bottom + 8, (w - 4) * frac, 6))
                px += w

        text(s, "%d%%" % pa, 32, (bar.left - 16, bar.centery), lead.colour,
             right=True)
        text(s, "%d%%" % (100 - pa), 32, (bar.right + 16, bar.centery),
             rival.colour, left=True)

        if len(ours) == 1:
            text(s, self.stat_line(lead), 15, (26, 96), DIM)
        else:
            up = sum(1 for f in ours if f.hp > 0)
            text(s, "%d / %d UP     %d HP" % (up, len(ours), int(a_hp)), 15,
                 (26, 96), DIM)
        text(s, self.stat_line(rival), 15, (W - 26, 104), DIM, right=True)
        text(s, "%d:%04.1f" % (int(self.clock_t // 60), self.clock_t % 60), 17,
             (W // 2, 104), DIM, center=True)

    def draw_banner(self, s):
        win = self.winner
        t = min(1.0, self.banner_t / 0.35)
        y = VIEW.centery - 26
        if self.mode == "campaign":
            done = self.camp_win and self.cleared >= len(CAMPAIGN)
            title = ("CAMPAIGN COMPLETE" if done else
                     "LEVEL CLEARED" if self.camp_win else "DEFEATED")
            size = int(lerp(92, 52, t))
            rule = (self.team_of(0)[0].colour if self.camp_win
                    else win.colour)
        else:
            title = "%s WINS" % win.name
            size = int(lerp(120, 66, t))
            rule = win.colour
        band = pygame.Surface((VIEW.w, 196), pygame.SRCALPHA)
        band.fill((8, 9, 14, 208))
        s.blit(band, (VIEW.left, y - 64))
        pygame.draw.line(s, rule, (VIEW.left, y - 64), (VIEW.right, y - 64), 2)
        pygame.draw.line(s, rule, (VIEW.left, y + 132), (VIEW.right, y + 132), 2)
        text(s, title, size, (W // 2, y), rule, center=True)
        if self.banner_t <= 0.5:
            return
        if self.mode == "campaign":
            line = self.unlock_text or ("%d hits  -  %d damage"
                                        % (win.hits, int(win.dealt)))
            hint = ("SPACE  next level        R  again        ESC  ladder"
                    if self.camp_win else
                    "SPACE / R  try again        ESC  back to the ladder")
            text(s, line, 22, (W // 2, y + 56),
                 GOLD if self.unlock_text else INK, center=True)
        else:
            text(s, "%d hits  -  %d damage  -  %.0f DPS"
                 % (win.hits, int(win.dealt), win.dealt / max(1.0, self.clock_t)),
                 22, (W // 2, y + 56), INK, center=True)
            hint = "SPACE / click  rematch        ESC  menu"
        text(s, hint, 20, (W // 2, y + 96), DIM, center=True)

    def draw_paused(self, s):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((0, 0, 0, 150))
        s.blit(v, (0, 0))
        text(s, "PAUSED", 72, (W // 2, VIEW.centery - 20), INK, center=True)
        text(s, "P  resume        R  rematch        ESC  menu", 20,
             (W // 2, VIEW.centery + 40), DIM, center=True)

    # -- the menu ----------------------------------------------------------
    def draw_menu(self, s):
        text(s, "BALL BRAWL", 42, (W // 2, 26), INK, center=True)
        text(s, "two balls, one arena, pick your weapons", 15,
             (W // 2, 68), DIM, center=True)
        text(s, "RED", 22, (56, 96), RED)
        text(s, "keys 1-7 pick the left column", 12, (112, 103), DIM)
        r = text(s, "BLUE", 22, (W - 56, 107), BLUE, right=True)
        text(s, "keys Q-U", 12, (r.left - 10, 109), DIM, right=True)

        for rect, kind, val in self.menu_layout():
            if kind == "pick":
                side, i = val
                self.draw_card(s, rect, WEAPONS[i], side, self.pick[side] == i)
            elif kind == "camp":
                self.draw_button(s, rect, "CAMPAIGN >", GOLD, "C")
            elif kind == "human":
                self.draw_button(s, rect, "RED IS:  %s" % ("PLAYER" if self.human
                                                           else "CPU"),
                                 GOLD if self.human else DIM, "TAB")
            elif kind == "orbs":
                self.draw_button(s, rect, "HEALTH ORBS:  %s" % ("ON" if self.orbs_on
                                                                else "OFF"),
                                 GREEN if self.orbs_on else DIM, "O")
            elif kind == "start":
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
                pygame.draw.rect(s, mix((28, 32, 44), (60, 90, 70), pulse), rect)
                pygame.draw.rect(s, mix(GREEN, INK, pulse * 0.5), rect, 2)
                text(s, "FIGHT   (SPACE)", 26, rect.center, INK, center=True)

        # the two chosen weapons explain themselves under their own side
        for side, base in ((0, RED), (1, BLUE)):
            w = WEAPONS[self.pick[side]]
            x = 56 if side == 0 else W - 56
            for k, line in enumerate(w.BLURB):
                text(s, line, 13, (x, 452 + k * 16), DIM, right=side == 1)
            px = x if side == 0 else x - 300
            for label, n in zip(("DMG", "RATE", "REACH"), w.PIPS):
                text(s, label, 11, (px, 486), DIM)
                for k in range(5):
                    c = base if k < n else (48, 52, 66)
                    pygame.draw.rect(s, c, (px + 40 + k * 8, 488, 5, 8))
                px += 100

        if self.cleared:
            text(s, "%d / %d CAMPAIGN LEVELS CLEARED"
                 % (self.cleared, len(CAMPAIGN)), 13, (W // 2, 656), GREEN,
                 center=True)
        if self.human:
            text(s, "WASD move      mouse aim      SPACE dash", 15,
                 (W // 2, 676), DIM, center=True)
        if self.score[0] or self.score[1]:
            text(s, "SESSION   RED %d  -  %d BLUE" % (self.score[0], self.score[1]),
                 15, (W // 2, 696), DIM, center=True)

    def draw_card(self, s, rect, wcls, side, selected):
        locked = wcls.NAME not in unlocked_weapons(self.cleared)
        base = (72, 78, 96) if locked else (RED if side == 0 else BLUE)
        live = selected and not locked
        pygame.draw.rect(s, mix(PANEL, base, 0.22 if live else 0.05), rect)
        pygame.draw.rect(s, base if live else (52, 57, 72), rect, 2 if live else 1)
        pygame.draw.circle(s, mix(PANEL, base, 0.8),
                           (rect.left + 20, rect.centery), 9)
        pygame.draw.circle(s, mix(base, (0, 0, 0), 0.4),
                           (rect.left + 20, rect.centery), 9, 1)
        text(s, wcls.NAME, 16, (rect.left + 38, rect.centery),
             INK if live else DIM, left=True)
        if locked:
            text(s, "L%d" % unlock_level(wcls.NAME), 12,
                 (rect.right - 8, rect.centery), DIM, right=True)

    # -- the campaign ------------------------------------------------------
    def draw_campaign(self, s):
        text(s, "CAMPAIGN", 34, (56, 18), INK)
        text(s, "beat a block, keep what it was holding", 14, (58, 58), DIM)
        text(s, "%d / %d CLEARED" % (self.cleared, len(CAMPAIGN)), 18,
             (W - 240, 36), GREEN if self.cleared else DIM, right=True)
        if self.cleared:
            text(s, "+%d%% MAX HP" % round(hp_bonus(self.cleared) * 100), 13,
                 (W - 240, 58), GREEN, right=True)

        for rect, kind, val in self.camp_layout():
            if kind == "back":
                self.draw_button(s, rect, "< VERSUS", DIM, "C")
            elif kind == "human":
                self.draw_button(s, rect, "PLAY" if self.human else "WATCH",
                                 GOLD if self.human else DIM, "TAB")
            elif kind == "level":
                self.draw_level(s, rect, val)
            elif kind == "ball":
                self.draw_ball(s, rect, val)
            elif kind == "slot":
                live = val == self.slot
                w = WEAPONS[self.camp_party[val]]
                pygame.draw.rect(s, mix(PANEL, RED, 0.22 if live else 0.06), rect)
                pygame.draw.rect(s, RED if live else (52, 57, 72), rect,
                                 2 if live else 1)
                text(s, "%d.  %s" % (val + 1, w.NAME), 13, rect.center,
                     INK if live else DIM, center=True)
            elif kind == "start":
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
                pygame.draw.rect(s, mix((28, 32, 44), (60, 90, 70), pulse), rect)
                pygame.draw.rect(s, mix(GREEN, INK, pulse * 0.5), rect, 2)
                text(s, "FIGHT   (SPACE)", 24, rect.center, INK, center=True)

        # what the highlighted level actually is
        lv = CAMPAIGN[self.level]
        text(s, lv["brief"], 14, (56, 546), INK if self.level <= self.cleared
             else DIM)
        text(s, "%s    HP %d%%    SPD %d%%    DMG %d%%    REWARD  %s"
             % (lv["weapon"].NAME, round(lv["hp"] * 100), round(lv["spd"] * 100),
                round(lv["dmg"] * 100), reward_label(lv)),
             12, (56, 564), mix(DIM, lv["colour"], 0.45))
        if self.party_size() > 1:
            text(s, "BRING THREE - click a slot, then a ball", 13,
                 (W - 56, 564), GOLD, right=True)
        else:
            text(s, "YOUR BALL:  %s" % WEAPONS[self.camp_pick].NAME, 13,
                 (W - 56, 578), DIM, right=True)

    def draw_level(self, s, rect, i):
        lv = CAMPAIGN[i]
        locked = i > self.cleared
        base = (70, 76, 94) if locked else lv["colour"]
        sel = i == self.level and not locked
        pygame.draw.rect(s, mix(PANEL, base, 0.20 if sel else 0.04), rect)
        pygame.draw.rect(s, base if sel else (48, 53, 68), rect, 2 if sel else 1)

        spin = pygame.time.get_ticks() * 0.0006 + i
        pygame.draw.polygon(s, mix(base, (0, 0, 0), 0.4),
                            shape_points(rect.left + 22, rect.centery, 9,
                                         lv["sides"], spin))
        text(s, "%2d.  %s" % (i + 1, lv["name"]), 16, (rect.left + 42,
             rect.centery), DIM if locked else INK, left=True)
        text(s, lv["weapon"].NAME, 12, (rect.left + 260, rect.centery),
             mix(DIM, base, 0.4), left=True)
        text(s, reward_label(lv), 12, (rect.left + 400, rect.centery),
             DIM if locked else GOLD, left=True)
        if i < self.cleared:
            text(s, "CLEARED", 13, (rect.right - 12, rect.centery), GREEN,
                 right=True)
        elif locked:
            text(s, "LOCKED", 13, (rect.right - 12, rect.centery), DIM,
                 right=True)
        else:
            text(s, "NEXT UP", 13, (rect.right - 12, rect.centery), GOLD,
                 right=True)

    def draw_ball(self, s, rect, i):
        wcls = WEAPONS[i]
        locked = wcls.NAME not in unlocked_weapons(self.cleared)
        sel = i == self.camp_pick and not locked
        base = (70, 76, 94) if locked else RED
        pygame.draw.rect(s, mix(PANEL, base, 0.22 if sel else 0.05), rect)
        pygame.draw.rect(s, base if sel else (52, 57, 72), rect, 2 if sel else 1)
        self.draw_icon(s, (rect.centerx - 6, rect.top + 15), wcls, base, 0.6)
        label = "LVL %d" % unlock_level(wcls.NAME) if locked else wcls.NAME
        text(s, label, 10, (rect.centerx, rect.bottom - 8),
             INK if sel else DIM, center=True)

    def draw_icon(self, s, c, wcls, colour, scale=1.0):
        """A weapon's badge. Upgrades share their base's shape, so the
        dispatch is by family, not by exact class, and everything is drawn
        off `scale` so the same badge fits a card or a small button."""
        cx, cy = c

        def at(dist, ang):
            return (int(cx + math.cos(ang) * dist * scale),
                    int(cy + math.sin(ang) * dist * scale))

        def px(v):
            return max(1, int(round(v * scale)))

        pygame.draw.circle(s, mix(PANEL, colour, 0.8), (cx, cy), px(15))
        pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), (cx, cy), px(15),
                           px(2))
        if issubclass(wcls, Summoner):
            n = 3 if wcls is Summoner else 4
            for i in range(n):
                q = at(24, i * TAU / n + 0.5)
                pygame.draw.circle(s, INK, q, px(5))
                pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), q, px(5), 1)
        elif issubclass(wcls, Fists):
            for i in range(wcls.BLADES):
                q = at(20, i * TAU / wcls.BLADES + 0.4)
                pygame.draw.line(s, mix(colour, (0, 0, 0), 0.3), (cx, cy), q,
                                 px(4))
                pygame.draw.circle(s, INK, q, px(6))
                pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), q, px(6), 1)
        elif issubclass(wcls, Hammer):
            for i in range(wcls.BLADES):
                a = i * TAU / wcls.BLADES
                pygame.draw.line(s, (112, 82, 50), at(10, a), at(26, a), px(5))
                head = pygame.Rect(0, 0, px(13), px(22))
                head.center = at(30, a)
                pygame.draw.rect(s, (150, 156, 172), head)
                pygame.draw.rect(s, INK, head, 1)
        elif issubclass(wcls, Melee):
            reach = 31 if wcls.REACH > 55 else 26
            for i in range(wcls.BLADES):
                a = i * TAU / wcls.BLADES + 0.4
                pygame.draw.line(s, INK, at(16, a), at(reach, a), px(3))
        elif issubclass(wcls, Gun):
            pygame.draw.line(s, (160, 168, 186), at(10, 0), at(34, 0), px(6))
            pygame.draw.line(s, (100, 107, 126),
                             (cx + px(12), cy + px(2)),
                             (cx + px(20), cy + px(12)), px(6))
            if wcls is not Gun:
                pygame.draw.line(s, (160, 168, 186),
                                 (cx + px(10), cy - px(8)),
                                 (cx + px(30), cy - px(8)), px(4))
        else:
            arc = pygame.Rect(0, 0, px(34), px(44))
            arc.center = (cx + px(21), cy)
            pygame.draw.arc(s, (150, 106, 60), arc, -1.2, 1.2, px(4))
            for i in range(getattr(wcls, "ARROWS", 1)):
                off = ((i - (wcls.ARROWS - 1) / 2) * 9 * scale
                       if wcls.ARROWS > 1 else 0)
                pygame.draw.line(s, INK, (cx - px(4), cy + off),
                                 (cx + px(30), cy + off), px(3))

    def draw_button(self, s, rect, label, colour, key):
        pygame.draw.rect(s, PANEL, rect)
        pygame.draw.rect(s, mix((52, 57, 72), colour, 0.5), rect, 2)
        text(s, label, 20, (rect.left + 16, rect.centery), INK, left=True)
        text(s, key, 15, (rect.right - 12, rect.centery), DIM, right=True)


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Ball Brawl")
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    game = Game()

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1.0 / 30.0)
        game.keys = pygame.key.get_pressed()
        game.mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif not game.handle(ev):
                running = False
        if not game.paused:
            for _ in range(game.speed if game.state == "fight" else 1):
                game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
