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
    1 .. 8          weapon for the red fighter
    Q .. I          weapon for the blue fighter
    TAB             red fighter: CPU or PLAYER
    O               health orbs on / off
    C               open the campaign
    SPACE           fight
  Campaign
    up / down       choose a level (or 1 .. 8)
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
ARENA = pygame.Rect(20, HUD_H, W - 40, H - HUD_H - 20)

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

_city_floor = None


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


def city_floor(w, h):
    """The arena floor. Built on first use, then reused every frame."""
    global _city_floor
    if _city_floor is not None and _city_floor.get_size() == (w, h):
        return _city_floor
    rng = random.Random(20260920)
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

    _city_floor = s
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
            if f is self.owner or f in self.hit or f.hp <= 0:
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
            if m.owner is self.owner or m.hp <= 0:
                continue
            if seg_dist(m.pos, self.prev, self.pos) <= m.R + self.size:
                m.hurt(self.dmg, world)
                if self.pierce <= 0:
                    self.dead = True
                    return
                self.pierce -= 1

    def draw(self, s, off):
        p = self.pos + Vector2(off)
        d = unit(self.vel)
        c = self.owner.colour
        if self.kind == "arrow":
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
        foe = world.foe(o)
        for i, (a, b) in enumerate(self.segments()):
            self.cool[i] = max(0.0, self.cool[i] - dt)
            if foe and foe.hp > 0 and self.cool[i] <= 0:
                if seg_dist(foe.pos, a, b) <= foe.r + 7:
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
                if m.owner is not o and m.hp > 0:
                    if seg_dist(m.pos, a, b) <= m.R + 4:
                        m.hurt(random.uniform(*self.DMG), world)
                        self.flash = max(self.flash, 0.6)
            if self.parry_cd <= 0:
                for pr in world.projectiles:
                    if pr.owner is o or pr.dead:
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
        d = o.aim.rotate_rad(random.uniform(-0.02, 0.02))
        nock = o.pos + d * (o.r + 14)
        world.projectiles.append(Projectile(
            o, nock, d * self.SPEED, random.uniform(*self.DMG), "arrow",
            crit_chance=self.CRIT, bounces=0, pierce=1, knock=220.0,
            size=7.0, life=2.2))
        o.vel -= d * 90.0
        self.shots += 1
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
        a = random.uniform(0, TAU)
        d = Vector2(math.cos(a), math.sin(a))
        world.minions.append(Minion(o, o.pos + d * (o.r + 12)))
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


WEAPONS = (Sword, Dagger, Flurry, Gun, Bow, Hammer, Fists, Summoner)
STARTERS = ("SWORD",)


# ---------------------------------------------------------------------------
# THE BALLS
# ---------------------------------------------------------------------------
class Fighter:
    def __init__(self, name, colour, dark, pos, weapon_cls, player=False,
                 shape=0, max_hp=MAX_HP, dmg_mult=1.0, speed_mult=1.0):
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

    def __init__(self, owner, pos):
        self.owner = owner
        self.pos = Vector2(pos)
        self.vel = unit(Vector2(random.uniform(-1, 1),
                                random.uniform(-1, 1))) * self.SPEED
        self.hp = self.HP
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
                foe.take_damage(random.uniform(*self.BURST), self.owner, world)
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

        if self.pos.x < ARENA.left + self.R:
            self.pos.x, self.vel.x = ARENA.left + self.R, abs(self.vel.x)
        elif self.pos.x > ARENA.right - self.R:
            self.pos.x, self.vel.x = ARENA.right - self.R, -abs(self.vel.x)
        if self.pos.y < ARENA.top + self.R:
            self.pos.y, self.vel.y = ARENA.top + self.R, abs(self.vel.y)
        elif self.pos.y > ARENA.bottom - self.R:
            self.pos.y, self.vel.y = ARENA.bottom - self.R, -abs(self.vel.y)

        if foe and foe.hp > 0 and self.cool <= 0:
            if (foe.pos - self.pos).length() <= foe.r + self.R:
                foe.take_damage(random.uniform(*self.DMG), self.owner, world)
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
        blit_glow(s, p, self.R * 2.2, self.owner.colour, 45)
        pygame.draw.circle(s, col, (int(p.x), int(p.y)), int(self.R))
        pygame.draw.circle(s, mix(self.owner.dark, (0, 0, 0), 0.3),
                           (int(p.x), int(p.y)), int(self.R), 1)


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
    return 0.05 * cleared


def reward_label(lv):
    kind, val = lv["reward"]
    return val if kind == "weapon" else "THE BELT"


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
        self.keys = None
        self.mouse = (W // 2, H // 2)

    # -- world -------------------------------------------------------------
    def foe(self, f):
        for o in self.fighters:
            if o is not f:
                return o
        return None

    def spark(self, pos, colour, n, speed=200.0):
        for _ in range(n):
            a = random.uniform(0, TAU)
            v = Vector2(math.cos(a), math.sin(a)) * random.uniform(0.25, 1.0) * speed
            self.particles.append(Particle(pos, v, random.uniform(0.18, 0.48),
                                           colour, random.uniform(2.0, 4.5)))

    def start_fight(self):
        left = (ARENA.left + ARENA.w * 0.20, ARENA.centery)
        right = (ARENA.left + ARENA.w * 0.80, ARENA.centery)
        if self.mode == "campaign":
            if self.level > self.cleared:
                return
            lv = CAMPAIGN[self.level]
            self.fighters = [
                Fighter("YOU", RED, RED_D, left, WEAPONS[self.camp_pick],
                        player=self.human,
                        max_hp=MAX_HP * (1.0 + hp_bonus(self.cleared))),
                Fighter(lv["name"], lv["colour"], lv["dark"], right,
                        lv["weapon"], shape=lv["sides"],
                        max_hp=MAX_HP * lv["hp"], dmg_mult=lv["dmg"],
                        speed_mult=lv["spd"]),
            ]
        else:
            self.fighters = [
                Fighter("RED", RED, RED_D, left, WEAPONS[self.pick[0]],
                        player=self.human),
                Fighter("BLUE", BLUE, BLUE_D, right, WEAPONS[self.pick[1]]),
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

    def knockout(self, loser, winner):
        if self.state != "fight":
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
            self.score[0 if winner is self.fighters[0] else 1] += 1
        self.spark(loser.pos, loser.colour, 60, speed=520)
        self.spark(loser.pos, (255, 255, 255), 24, speed=300)
        SFX.play("ko", 1.0)

    def record_level(self, winner):
        """A campaign win only counts the first time, and it is saved at once."""
        self.camp_win = winner is self.fighters[0]
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
        if len(self.fighters) < 2:
            return
        a, b = self.fighters
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

    # -- input -------------------------------------------------------------
    def unlocked_idx(self):
        names = unlocked_weapons(self.cleared)
        return [i for i, w in enumerate(WEAPONS) if w.NAME in names]

    def menu_layout(self):
        """Every clickable thing on the versus menu: (rect, kind, value)."""
        items = [(pygame.Rect(W - 216, 22, 180, 40), "camp", None)]
        cw, ch, gap = 396, 46, 4
        top = 132
        for side in (0, 1):
            x = 56 if side == 0 else W - 56 - cw
            for i in range(len(WEAPONS)):
                items.append((pygame.Rect(x, top + i * (ch + gap), cw, ch),
                              "pick", (side, i)))
        bx = W // 2 - 152
        items.append((pygame.Rect(bx, 572, 304, 34), "human", None))
        items.append((pygame.Rect(bx, 612, 304, 34), "orbs", None))
        items.append((pygame.Rect(bx, 654, 304, 48), "start", None))
        return items

    def camp_layout(self):
        """Every clickable thing on the campaign screen."""
        items = [(pygame.Rect(W - 216, 22, 180, 40), "back", None)]
        top, h, gap = 84, 56, 4
        for i in range(len(CAMPAIGN)):
            items.append((pygame.Rect(56, top + i * (h + gap), W - 112, h),
                          "level", i))
        bw, bh, bgap = 80, 50, 8
        span = len(WEAPONS) * bw + (len(WEAPONS) - 1) * bgap
        x0 = (W - span) // 2
        for i in range(len(WEAPONS)):
            items.append((pygame.Rect(x0 + i * (bw + bgap), 582, bw, bh),
                          "ball", i))
        items.append((pygame.Rect(W // 2 - 152, 642, 304, 34), "human", None))
        items.append((pygame.Rect(W // 2 - 152, 684, 304, 48), "start", None))
        return items

    def open_campaign(self):
        self.mode = "campaign"
        self.state = "campaign"
        self.level = min(self.cleared, len(CAMPAIGN) - 1)
        picks = self.unlocked_idx()
        if self.camp_pick not in picks:
            self.camp_pick = picks[0]
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
                 pygame.K_t, pygame.K_y, pygame.K_u, pygame.K_i)

    def menu_key(self, k):
        if pygame.K_1 <= k <= pygame.K_8:
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
        elif pygame.K_1 <= k <= pygame.K_8 and k - pygame.K_1 <= self.cleared:
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
                    self.camp_pick = val
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
            off = (0, 0)
            if self.shake > 0.2:
                off = (random.uniform(-self.shake, self.shake) * 0.5,
                       random.uniform(-self.shake, self.shake) * 0.5)
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
        s.blit(city_floor(ARENA.w, ARENA.h), inner.topleft)

        clip = s.get_clip()
        s.set_clip(ARENA)
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
        s.set_clip(clip)

        pygame.draw.rect(s, WALL, inner, 3)
        L = 34
        for cx, cy, dx, dy in ((inner.left, inner.top, 1, 1),
                               (inner.right - 1, inner.top, -1, 1),
                               (inner.left, inner.bottom - 1, 1, -1),
                               (inner.right - 1, inner.bottom - 1, -1, -1)):
            pygame.draw.line(s, INK, (cx, cy), (cx + dx * L, cy), 3)
            pygame.draw.line(s, INK, (cx, cy), (cx, cy + dy * L), 3)

        tags = []
        if self.speed > 1:
            tags.append("%dx" % self.speed)
        if SFX.muted:
            tags.append("MUTED")
        if tags:
            text(s, "  ".join(tags), 17, (ARENA.right - 20, ARENA.top + 26),
                 DIM, right=True)
        if self.human and self.fighters:
            me = self.fighters[0]
            ready = me.dash_cd <= 0
            text(s, "DASH " + ("READY" if ready else "%.1f" % me.dash_cd), 17,
                 (ARENA.left + 20, ARENA.top + 18), GOLD if ready else DIM)

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
        if len(self.fighters) < 2:
            return
        a, b = self.fighters
        total = max(1e-6, a.hp + b.hp)
        fa = a.hp / total
        pa = int(round(fa * 100))

        text(s, a.name, 30, (26, 6), a.colour)
        text(s, a.weapon.NAME, 17, (27, 44), DIM)
        text(s, b.name, 30, (W - 26, 23), b.colour, right=True)
        text(s, b.weapon.NAME, 17, (W - 27, 53), DIM, right=True)

        text(s, "VS", 24, (W // 2, 20), INK, center=True)
        mid = ("LEVEL %d / %d" % (self.level + 1, len(CAMPAIGN))
               if self.mode == "campaign" else
               "%d - %d" % (self.score[0], self.score[1]))
        text(s, mid, 19, (W // 2, 46), DIM, center=True)

        # One bar, split where the two health pools meet - the split is the
        # whole story of the fight, so the marker sits on it.
        bar = pygame.Rect(250, 62, W - 500, 26)
        pygame.draw.rect(s, (11, 12, 18), bar.inflate(6, 6))
        split = int(bar.w * fa)
        pygame.draw.rect(s, a.dark, (bar.x, bar.y, split, bar.h))
        pygame.draw.rect(s, a.colour, (bar.x, bar.y, split, bar.h // 2))
        pygame.draw.rect(s, b.dark, (bar.x + split, bar.y, bar.w - split, bar.h))
        pygame.draw.rect(s, b.colour,
                         (bar.x + split, bar.y, bar.w - split, bar.h // 2))
        pygame.draw.rect(s, (62, 68, 86), bar, 2)
        mx = bar.x + split
        pygame.draw.line(s, INK, (mx, bar.top - 3), (mx, bar.bottom + 3), 2)
        pygame.draw.polygon(s, INK, [(mx - 6, bar.top - 3), (mx + 6, bar.top - 3),
                                     (mx, bar.top + 6)])
        pygame.draw.polygon(s, INK, [(mx - 6, bar.bottom + 3),
                                     (mx + 6, bar.bottom + 3),
                                     (mx, bar.bottom - 6)])

        text(s, "%d%%" % pa, 32, (bar.left - 16, bar.centery), a.colour,
             right=True)
        text(s, "%d%%" % (100 - pa), 32, (bar.right + 16, bar.centery), b.colour,
             left=True)

        text(s, self.stat_line(a), 15, (26, 96), DIM)
        text(s, self.stat_line(b), 15, (W - 26, 104), DIM, right=True)
        text(s, "%d:%04.1f" % (int(self.clock_t // 60), self.clock_t % 60), 17,
             (W // 2, 104), DIM, center=True)

    def draw_banner(self, s):
        win = self.winner
        t = min(1.0, self.banner_t / 0.35)
        y = ARENA.centery - 26
        if self.mode == "campaign":
            done = self.camp_win and self.cleared >= len(CAMPAIGN)
            title = ("CAMPAIGN COMPLETE" if done else
                     "LEVEL CLEARED" if self.camp_win else "DEFEATED")
            size = int(lerp(92, 52, t))
            rule = self.fighters[0].colour if self.camp_win else win.colour
        else:
            title = "%s WINS" % win.name
            size = int(lerp(120, 66, t))
            rule = win.colour
        band = pygame.Surface((ARENA.w, 196), pygame.SRCALPHA)
        band.fill((8, 9, 14, 208))
        s.blit(band, (ARENA.left, y - 64))
        pygame.draw.line(s, rule, (ARENA.left, y - 64), (ARENA.right, y - 64), 2)
        pygame.draw.line(s, rule, (ARENA.left, y + 132), (ARENA.right, y + 132), 2)
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
        text(s, "PAUSED", 72, (W // 2, ARENA.centery - 20), INK, center=True)
        text(s, "P  resume        R  rematch        ESC  menu", 20,
             (W // 2, ARENA.centery + 40), DIM, center=True)

    # -- the menu ----------------------------------------------------------
    def draw_menu(self, s):
        text(s, "BALL BRAWL", 50, (W // 2, 34), INK, center=True)
        text(s, "two balls, one arena, pick your weapons", 17,
             (W // 2, 80), DIM, center=True)

        text(s, "RED", 26, (56, 100), RED)
        text(s, "keys 1-8", 14, (124, 108), DIM)
        r = text(s, "BLUE", 26, (W - 56, 113), BLUE, right=True)
        text(s, "keys Q-I", 14, (r.left - 12, 115), DIM, right=True)

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
                text(s, "FIGHT   (SPACE)", 27, rect.center, INK, center=True)

        # the chosen weapon says what it does, under its own column
        for k, line in enumerate(WEAPONS[self.pick[0]].BLURB):
            text(s, line, 13, (56, 538 + k * 16), DIM)
        for k, line in enumerate(WEAPONS[self.pick[1]].BLURB):
            text(s, line, 13, (W - 56, 546 + k * 16), DIM, right=True)

        if self.cleared:
            text(s, "%d / %d CAMPAIGN LEVELS CLEARED"
                 % (self.cleared, len(CAMPAIGN)), 14, (W // 2, 720), GREEN,
                 center=True)
        if self.human:
            text(s, "WASD move      mouse aim      SPACE dash", 16,
                 (W // 2, 738), DIM, center=True)
        if self.score[0] or self.score[1]:
            text(s, "SESSION   RED %d  -  %d BLUE" % (self.score[0], self.score[1]),
                 16, (W // 2, 754), DIM, center=True)

    def draw_card(self, s, rect, wcls, side, selected):
        locked = wcls.NAME not in unlocked_weapons(self.cleared)
        base = (72, 78, 96) if locked else (RED if side == 0 else BLUE)
        live = selected and not locked
        pygame.draw.rect(s, mix(PANEL, base, 0.22 if live else 0.05), rect)
        pygame.draw.rect(s, base if live else (52, 57, 72), rect, 3 if live else 1)
        self.draw_icon(s, (rect.left + 38, rect.centery), wcls, base)
        text(s, wcls.NAME, 19, (rect.left + 80, rect.top + 1),
             INK if live else DIM)
        if locked:
            text(s, "locked - clear level %d" % unlock_level(wcls.NAME),
                 12, (rect.left + 80, rect.top + 24), DIM)
            return
        px = rect.left + 80
        for label, n in zip(("DMG", "RATE", "REACH"), wcls.PIPS):
            text(s, label, 10, (px, rect.bottom - 15), DIM)
            for k in range(5):
                c = base if k < n else (48, 52, 66)
                pygame.draw.rect(s, c, (px + 36 + k * 8, rect.bottom - 14, 5, 7))
            px += 88

    # -- the campaign ------------------------------------------------------
    def draw_campaign(self, s):
        text(s, "CAMPAIGN", 38, (56, 20), INK)
        text(s, "beat a shape, keep what it was holding", 15, (58, 64), DIM)
        text(s, "%d / %d CLEARED" % (self.cleared, len(CAMPAIGN)), 19,
             (W - 240, 42), GREEN if self.cleared else DIM, right=True)
        if self.cleared:
            text(s, "+%d%% MAX HP" % round(hp_bonus(self.cleared) * 100), 15,
                 (W - 240, 66), GREEN, right=True)
        text(s, "YOUR BALL", 14, (W // 2, 568), DIM, center=True)

        for rect, kind, val in self.camp_layout():
            if kind == "back":
                self.draw_button(s, rect, "< VERSUS", DIM, "C")
            elif kind == "level":
                self.draw_level(s, rect, val)
            elif kind == "ball":
                self.draw_ball(s, rect, val)
            elif kind == "human":
                self.draw_button(s, rect, "YOU ARE:  %s"
                                 % ("PLAYING" if self.human else "WATCHING"),
                                 GOLD if self.human else DIM, "TAB")
            elif kind == "start":
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
                pygame.draw.rect(s, mix((28, 32, 44), (60, 90, 70), pulse), rect)
                pygame.draw.rect(s, mix(GREEN, INK, pulse * 0.5), rect, 2)
                text(s, "FIGHT   (SPACE)", 26, rect.center, INK, center=True)

    def draw_level(self, s, rect, i):
        lv = CAMPAIGN[i]
        locked = i > self.cleared
        base = (70, 76, 94) if locked else lv["colour"]
        sel = i == self.level and not locked
        pygame.draw.rect(s, mix(PANEL, base, 0.20 if sel else 0.05), rect)
        pygame.draw.rect(s, base if sel else (52, 57, 72), rect, 3 if sel else 1)

        # the shape itself, turning slowly
        spin = pygame.time.get_ticks() * 0.0006 + i
        pts = shape_points(rect.left + 44, rect.centery, 18,
                           lv["sides"], spin)
        pygame.draw.polygon(s, mix(base, (0, 0, 0), 0.45), pts)
        pygame.draw.polygon(s, base, pts, 2)

        text(s, "%d.  %s" % (i + 1, lv["name"]), 19,
             (rect.left + 88, rect.top + 2), DIM if locked else INK)
        text(s, lv["brief"], 12, (rect.left + 88, rect.top + 23), DIM)
        text(s, "%s    HP %d%%    SPD %d%%    DMG %d%%"
             % (lv["weapon"].NAME, round(lv["hp"] * 100), round(lv["spd"] * 100),
                round(lv["dmg"] * 100)),
             11, (rect.left + 88, rect.top + 40), mix(DIM, base, 0.45))

        text(s, "REWARD  " + reward_label(lv), 14,
             (rect.right - 18, rect.top + 15), DIM if locked else GOLD, right=True)
        if i < self.cleared:
            text(s, "CLEARED", 14, (rect.right - 18, rect.top + 40), GREEN,
                 right=True)
        elif locked:
            text(s, "LOCKED", 14, (rect.right - 18, rect.top + 40), DIM,
                 right=True)
        else:
            text(s, "NEXT UP", 14, (rect.right - 18, rect.top + 40), GOLD,
                 right=True)

    def draw_ball(self, s, rect, i):
        wcls = WEAPONS[i]
        locked = wcls.NAME not in unlocked_weapons(self.cleared)
        sel = i == self.camp_pick and not locked
        base = (70, 76, 94) if locked else RED
        pygame.draw.rect(s, mix(PANEL, base, 0.22 if sel else 0.05), rect)
        pygame.draw.rect(s, base if sel else (52, 57, 72), rect, 3 if sel else 1)
        self.draw_icon(s, (rect.centerx - 12, rect.top + 19), wcls, base)
        label = "LVL %d" % unlock_level(wcls.NAME) if locked else wcls.NAME
        text(s, label, 11, (rect.centerx, rect.bottom - 8),
             INK if sel else DIM, center=True)

    def draw_icon(self, s, c, wcls, colour):
        cx, cy = c
        pygame.draw.circle(s, mix(PANEL, colour, 0.8), (cx, cy), 15)
        pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), (cx, cy), 15, 2)
        if wcls is Summoner:
            for n in range(3):
                a = n * TAU / 3 + 0.5
                q = (int(cx + math.cos(a) * 24), int(cy + math.sin(a) * 24))
                pygame.draw.circle(s, INK, q, 5)
                pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), q, 5, 1)
        elif wcls is Fists:
            for n in (-1, 1):
                q = (cx + 17, cy + n * 11)
                pygame.draw.line(s, mix(colour, (0, 0, 0), 0.3), (cx + 6, cy), q, 5)
                pygame.draw.circle(s, INK, q, 6)
                pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), q, 6, 1)
        elif wcls is Sword or wcls is Dagger or wcls is Flurry:
            n = wcls.BLADES
            reach = 31 if wcls is Sword else 26
            for k in range(n):
                a = k * TAU / n + 0.4
                d = Vector2(math.cos(a), math.sin(a))
                pygame.draw.line(s, INK, (cx + d.x * 16, cy + d.y * 16),
                                 (cx + d.x * reach, cy + d.y * reach), 3)
        elif wcls is Hammer:
            pygame.draw.line(s, (112, 82, 50), (cx + 12, cy), (cx + 28, cy), 5)
            pygame.draw.rect(s, (150, 156, 172), (cx + 25, cy - 11, 13, 22))
            pygame.draw.rect(s, INK, (cx + 25, cy - 11, 13, 22), 1)
        elif wcls is Gun:
            pygame.draw.line(s, (160, 168, 186), (cx + 10, cy), (cx + 34, cy), 6)
            pygame.draw.line(s, (100, 107, 126), (cx + 12, cy + 2),
                             (cx + 20, cy + 12), 6)
        else:
            pygame.draw.arc(s, (150, 106, 60),
                            pygame.Rect(cx + 4, cy - 22, 34, 44),
                            -1.2, 1.2, 4)
            pygame.draw.line(s, INK, (cx + 12, cy - 18), (cx + 12, cy + 18), 1)
            pygame.draw.line(s, INK, (cx - 4, cy), (cx + 30, cy), 3)

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
