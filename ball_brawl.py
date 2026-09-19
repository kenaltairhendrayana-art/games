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

CONTROLS
  Menu
    1 / 2 / 3       weapon for the red fighter
    8 / 9 / 0       weapon for the blue fighter
    TAB             red fighter: CPU or PLAYER
    O               health orbs on / off
    click           all of the above, with the mouse
    SPACE           fight
  Fight  (only when red is the PLAYER)
    WASD / arrows   thrust
    mouse           aim the gun and the bow
    SPACE           dash
  Any time
    P               pause
    F               speed  1x / 2x / 3x
    M               mute
    R               rematch
    ESC             back to the menu
"""

import math
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

# Physics. Fighters are always under thrust, so drag and the speed clamp are
# what actually decide how fast the fight looks, not the acceleration.
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
        self.size = 34 if crit else 23

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
                f.vel += unit(self.vel) * self.knock
                world.spark(f.pos - unit(self.vel) * f.r, self.owner.colour,
                            10 if crit else 6, speed=220)
                self.hit.add(f)
                if self.pierce <= 0:
                    self.dead = True
                    return
                self.pierce -= 1
                self.vel *= 0.8

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
# A weapon owns three things: the range its carrier wants to hold (PREF),
# what it does each frame, and how it draws. The whole AI hangs off PREF -
# that one number is what makes a sword ball charge and a bow ball run.
# ---------------------------------------------------------------------------
class Weapon:
    NAME = "?"
    PREF = 200.0              # range the carrier tries to hold
    RADIUS = 26.0             # the heavy weapon makes a bigger target
    SPEED_MULT = 1.0          # the light weapon is the fast one
    DASH_MULT = 1.0           # multiplies the dash cooldown
    BLURB = ("", "")
    PIPS = (0, 0, 0)          # damage / rate / reach, out of 5, for the menu

    def __init__(self, owner):
        self.owner = owner
        self.shots = 0

    def update(self, dt, world):
        pass

    def draw(self, s, off, world):
        pass


class Sword(Weapon):
    NAME = "SWORD"
    PREF = 0.0
    RADIUS = 23.0
    SPEED_MULT = 1.22         # carries the least weight, so it runs you down
    DASH_MULT = 0.62
    BLURB = ("orbiting blades that cut on",
             "contact - and swat bullets down")
    PIPS = (4, 4, 1)

    BLADES = 3
    REACH = 60.0
    SPIN = 4.7
    KNOCK = 40.0              # shoving the target away also ends the combo
    LUNGE = 55.0              # so the cut pulls the swordsman in instead
    DMG = (26.0, 37.0)
    HIT_CD = 0.32
    CRIT = 0.12

    def __init__(self, owner):
        super().__init__(owner)
        self.angle = random.uniform(0, TAU)
        self.cool = [0.0] * self.BLADES
        self.parry_cd = 0.0
        self.flash = 0.0

    def segments(self):
        o = self.owner
        for i in range(self.BLADES):
            a = self.angle + i * TAU / self.BLADES
            d = Vector2(math.cos(a), math.sin(a))
            yield o.pos + d * (o.r + 4), o.pos + d * (o.r + self.REACH)

    def update(self, dt, world):
        o = self.owner
        self.angle = (self.angle + self.SPIN * dt) % TAU
        self.parry_cd = max(0.0, self.parry_cd - dt)
        self.flash = max(0.0, self.flash - dt * 5.0)
        foe = world.foe(o)
        for i, (a, b) in enumerate(self.segments()):
            self.cool[i] = max(0.0, self.cool[i] - dt)
            if foe and foe.hp > 0 and self.cool[i] <= 0:
                if seg_dist(foe.pos, a, b) <= foe.r + 4:
                    crit = random.random() < self.CRIT
                    dmg = random.uniform(*self.DMG) * (1.8 if crit else 1.0)
                    foe.take_damage(dmg, o, world, crit=crit)
                    push = unit(foe.pos - o.pos)
                    foe.vel += push * self.KNOCK
                    o.vel += push * self.LUNGE
                    self.cool[i] = self.HIT_CD
                    self.flash = 1.0
                    world.spark(foe.pos - push * foe.r, o.colour, 8, speed=240)
                    SFX.play("cut", 0.7)
            if self.parry_cd <= 0:
                for p in world.projectiles:
                    if p.owner is o or p.dead:
                        continue
                    if segs_close(p.prev, p.pos, a, b, 11.0):
                        p.dead = True
                        self.parry_cd = 0.11
                        world.spark(p.pos, (255, 255, 255), 9, speed=260)
                        world.shake = max(world.shake, 3.0)
                        SFX.play("parry", 0.45)
                        break

    def draw(self, s, off, world):
        o = self.owner
        ov = Vector2(off)
        for a, b in self.segments():
            a, b = a + ov, b + ov
            d = unit(b - a)
            side = Vector2(-d.y, d.x)
            body = [a + side * 4, b + side * 1.3, b - side * 1.3, a - side * 4]
            edge = mix(o.colour, (255, 255, 255), 0.55 + 0.45 * self.flash)
            pygame.draw.polygon(s, edge, body)
            pygame.draw.polygon(s, (255, 255, 255), body, 1)
            pygame.draw.line(s, (206, 211, 224), a + side * 7, a - side * 7, 3)
            pygame.draw.line(s, (72, 56, 44), a - d * 7, a, 5)
            if self.flash > 0.05:
                blit_glow(s, b, 26, o.colour, int(90 * self.flash))


class Gun(Weapon):
    NAME = "GUN"
    PREF = 330.0
    RADIUS = 26.0
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
    SPREAD = 0.05
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
            crit_chance=self.CRIT, bounces=1, knock=45.0, size=4.0, life=2.4))
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
        base = o.pos + Vector2(off) + d * (o.r + 2 - 5 * self.kick)
        barrel = base + d * 26
        pygame.draw.line(s, (46, 50, 62), base - side * 4, barrel - side * 4, 9)
        pygame.draw.line(s, (150, 158, 176), base, barrel, 6)
        pygame.draw.line(s, (92, 99, 118), base - d * 4 + side * 2,
                         base + d * 6 + side * 12, 7)
        pygame.draw.circle(s, (34, 37, 47), (int(barrel.x), int(barrel.y)), 3)
        if self.kick > 0.25:
            blit_glow(s, barrel + d * 6, int(18 * self.kick),
                      (255, 220, 150), int(150 * self.kick))


class Bow(Weapon):
    NAME = "BOW"
    PREF = 380.0
    RADIUS = 28.0
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
            size=5.0, life=2.2))
        o.vel -= d * 90.0
        self.shots += 1
        world.spark(nock, mix(o.colour, (255, 255, 255), 0.5), 5, speed=180)
        SFX.play("arrow", 0.5)

    def draw(self, s, off, world):
        o = self.owner
        d = o.aim
        side = Vector2(-d.y, d.x)
        c = o.pos + Vector2(off) + d * (o.r + 8)
        pull = 16.0 * self.charge
        tip1, tip2 = c + side * 24 - d * 6, c - side * 24 - d * 6
        # limbs
        pygame.draw.lines(s, (122, 84, 46), False,
                          [tip1, c + side * 14 + d * 9, c + d * 12,
                           c - side * 14 + d * 9, tip2], 5)
        # string, pulled back by the draw
        knock_pt = c - d * pull
        pygame.draw.lines(s, (215, 220, 232), False, [tip1, knock_pt, tip2], 2)
        if self.charge > 0.08:
            shaft = knock_pt + d * (10 + 26 * self.charge)
            pygame.draw.line(s, mix(o.colour, (255, 255, 255), 0.4),
                             knock_pt, shaft, 3)
            pygame.draw.polygon(s, (255, 255, 255),
                                [shaft + d * 6, shaft - d * 3 + side * 4,
                                 shaft - d * 3 - side * 4])
        if self.charge > 0.86:
            blit_glow(s, c + d * 20, 22, o.colour, int(120 * (self.charge - 0.86) / 0.14))


WEAPONS = (Sword, Gun, Bow)


# ---------------------------------------------------------------------------
# THE BALLS
# ---------------------------------------------------------------------------
class Fighter:
    def __init__(self, name, colour, dark, pos, weapon_cls, player=False):
        self.name = name
        self.colour = colour
        self.dark = dark
        self.pos = Vector2(pos)
        self.vel = unit(Vector2(random.uniform(-1, 1), random.uniform(-1, 1))) * 260
        self.r = weapon_cls.RADIUS
        self.hp = MAX_HP
        self.weapon = weapon_cls(self)
        self.player = player
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
        self.hp = min(MAX_HP, self.hp + amount)

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
        cap = MAX_SPEED * self.weapon.SPEED_MULT * (1.9 if self.dash_t > 0 else 1.0)
        if sp > cap:
            self.vel.scale_to_length(cap)
        elif sp < MIN_SPEED and self.hp > 0:
            self.vel = unit(self.vel, (random.uniform(-1, 1),
                                       random.uniform(-1, 1))) * MIN_SPEED
        self.pos += self.vel * dt
        self.bounce_walls(world)

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
    def draw(self, s, off, world):
        ov = Vector2(off)
        p = self.pos + ov
        # trail
        for i, t in enumerate(self.trail):
            f = (i + 1) / len(self.trail)
            rad = max(1, int(self.r * 0.7 * f))
            col = mix(BG, self.colour, 0.30 * f)
            pygame.draw.circle(s, col, (int(t[0] + ov.x), int(t[1] + ov.y)), rad)

        if self.hp <= 0:
            husk = mix(self.dark, (44, 46, 56), 0.65)
            pygame.draw.circle(s, husk, (int(p.x), int(p.y)), int(self.r))
            pygame.draw.circle(s, mix(husk, (0, 0, 0), 0.45),
                               (int(p.x), int(p.y)), int(self.r), 2)
            for sgn in (-1, 1):
                e = p + Vector2(self.r * 0.34 * sgn, -self.r * 0.10)
                k = self.r * 0.16
                pygame.draw.line(s, (215, 218, 228), (e.x - k, e.y - k),
                                 (e.x + k, e.y + k), 2)
                pygame.draw.line(s, (215, 218, 228), (e.x - k, e.y + k),
                                 (e.x + k, e.y - k), 2)
            return

        blit_glow(s, p, int(self.r * 1.9), self.colour, 62)
        body = mix(self.dark, self.colour, 0.85)
        if self.flash > 0:
            body = mix(body, (255, 255, 255), 0.75 * self.flash)
        pygame.draw.circle(s, body, (int(p.x), int(p.y)), int(self.r))
        # a little shading so it reads as a ball, not a disc
        pygame.draw.circle(s, mix(body, (255, 255, 255), 0.35),
                           (int(p.x - self.r * 0.3), int(p.y - self.r * 0.33)),
                           int(self.r * 0.42))
        pygame.draw.circle(s, mix(self.dark, (0, 0, 0), 0.35),
                           (int(p.x), int(p.y)), int(self.r), 2)

        # eyes, looking at whoever it is fighting
        foe = world.foe(self)
        look = unit((foe.pos - self.pos) if foe else self.aim, self.aim)
        for sgn in (-1, 1):
            side = Vector2(-look.y, look.x) * (self.r * 0.34 * sgn)
            e = p + look * self.r * 0.30 + side
            pygame.draw.circle(s, (250, 250, 255), (int(e.x), int(e.y)),
                               max(2, int(self.r * 0.20)))
            q = e + look * self.r * 0.09
            pygame.draw.circle(s, (18, 18, 24), (int(q.x), int(q.y)),
                               max(1, int(self.r * 0.10)))

        # health ring
        frac = clamp(self.hp / MAX_HP, 0.0, 1.0)
        rr = pygame.Rect(0, 0, self.r * 2 + 14, self.r * 2 + 14)
        rr.center = (int(p.x), int(p.y))
        pygame.draw.arc(s, mix(BG, self.dark, 0.8), rr, 0, TAU, 3)
        if frac > 0.01:
            pygame.draw.arc(s, self.colour, rr,
                            TAU * 0.25, TAU * 0.25 + TAU * frac, 3)
        if self.dash_t > 0:
            blit_glow(s, p, int(self.r * 3.2), (255, 255, 255), 70)

        self.weapon.draw(s, off, world)


# ---------------------------------------------------------------------------
# PICKUPS
# ---------------------------------------------------------------------------
class Orb:
    HEAL = 90.0

    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.life = 11.0
        self.r = 14.0
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
# THE GAME
#
# One object holds the whole world and the three screens it can be showing.
# update() never touches a font or the display, so the fight can be run
# headless - which is how the matchups were balanced.
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.state = "menu"          # menu | fight | ko
        self.paused = False
        self.speed = 1
        self.orbs_on = True
        self.human = False
        self.pick = [0, 1]           # weapon index for red, blue
        self.score = [0, 0]
        self.fighters = []
        self.projectiles = []
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
        self.fighters = [
            Fighter("RED", RED, RED_D,
                    (ARENA.left + ARENA.w * 0.20, ARENA.centery),
                    WEAPONS[self.pick[0]], player=self.human),
            Fighter("BLUE", BLUE, BLUE_D,
                    (ARENA.left + ARENA.w * 0.80, ARENA.centery),
                    WEAPONS[self.pick[1]]),
        ]
        self.projectiles.clear()
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
        self.score[0 if winner is self.fighters[0] else 1] += 1
        self.spark(loser.pos, loser.colour, 60, speed=520)
        self.spark(loser.pos, (255, 255, 255), 24, speed=300)
        SFX.play("ko", 1.0)

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
        push = (touch - dist) * 0.5
        a.pos -= n * push
        b.pos += n * push
        rel = (b.vel - a.vel).dot(n)
        if rel < 0:                       # equal masses, so they swap along n
            a.vel += n * rel * 1.04
            b.vel -= n * rel * 1.04
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
    def menu_layout(self):
        """Every clickable thing on the menu: (rect, kind, value)."""
        items = []
        cw, ch, gap = 396, 98, 10
        top = 230
        for side in (0, 1):
            x = 56 if side == 0 else W - 56 - cw
            for i in range(len(WEAPONS)):
                items.append((pygame.Rect(x, top + i * (ch + gap), cw, ch),
                              "pick", (side, i)))
        bx = W // 2 - 152
        items.append((pygame.Rect(bx, 566, 304, 40), "human", None))
        items.append((pygame.Rect(bx, 612, 304, 40), "orbs", None))
        items.append((pygame.Rect(bx, 664, 304, 52), "start", None))
        return items

    def handle(self, ev):
        """False means quit."""
        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if k == pygame.K_ESCAPE:
                if self.state == "menu":
                    return False
                self.state = "menu"
                self.paused = False
            elif k == pygame.K_m:
                SFX.muted = not SFX.muted
            elif k == pygame.K_f:
                self.speed = 1 if self.speed >= 3 else self.speed + 1
            elif k == pygame.K_p and self.state != "menu":
                self.paused = not self.paused
            elif self.state == "menu":
                if k in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.pick[0] = k - pygame.K_1
                    SFX.play("click")
                elif k in (pygame.K_8, pygame.K_9, pygame.K_0):
                    self.pick[1] = {pygame.K_8: 0, pygame.K_9: 1, pygame.K_0: 2}[k]
                    SFX.play("click")
                elif k == pygame.K_TAB:
                    self.human = not self.human
                    SFX.play("click")
                elif k == pygame.K_o:
                    self.orbs_on = not self.orbs_on
                    SFX.play("click")
                elif k in (pygame.K_SPACE, pygame.K_RETURN):
                    self.start_fight()
            else:
                if k == pygame.K_r:
                    self.start_fight()
                elif k == pygame.K_SPACE:
                    if self.state == "ko":
                        self.start_fight()
                    elif self.human and self.fighters and self.fighters[0].dash_cd <= 0:
                        me = self.fighters[0]
                        me.dash(me.aim)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.state == "menu":
                for rect, kind, val in self.menu_layout():
                    if not rect.collidepoint(ev.pos):
                        continue
                    SFX.play("click")
                    if kind == "pick":
                        self.pick[val[0]] = val[1]
                    elif kind == "human":
                        self.human = not self.human
                    elif kind == "orbs":
                        self.orbs_on = not self.orbs_on
                    elif kind == "start":
                        self.start_fight()
                    break
            elif self.state == "ko":
                self.start_fight()
        return True

    # -- drawing -----------------------------------------------------------
    def draw(self, s):
        s.fill(BG)
        if self.state == "menu":
            self.draw_menu(s)
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
        pygame.draw.rect(s, (17, 18, 26), inner)
        step = 52
        for x in range(inner.left + step, inner.right, step):
            pygame.draw.line(s, GRID, (x, inner.top + 1), (x, inner.bottom - 1))
        for y in range(inner.top + step, inner.bottom, step):
            pygame.draw.line(s, GRID, (inner.left + 1, y), (inner.right - 1, y))
        pygame.draw.circle(s, GRID, inner.center, 90, 1)
        pygame.draw.circle(s, GRID, inner.center, 4)

        clip = s.get_clip()
        s.set_clip(ARENA)
        for o in self.orbs:
            o.draw(s, off)
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
        if f.weapon.shots:
            parts.append("%d%% ACC" % round(100.0 * f.hits / f.weapon.shots))
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

        text(s, a.name, 30, (26, 6), RED)
        text(s, a.weapon.NAME, 17, (27, 44), DIM)
        text(s, b.name, 30, (W - 26, 23), BLUE, right=True)
        text(s, b.weapon.NAME, 17, (W - 27, 53), DIM, right=True)

        text(s, "VS", 24, (W // 2, 20), INK, center=True)
        text(s, "%d - %d" % (self.score[0], self.score[1]), 19,
             (W // 2, 46), DIM, center=True)

        # One bar, split where the two health pools meet - the split is the
        # whole story of the fight, so the marker sits on it.
        bar = pygame.Rect(250, 62, W - 500, 26)
        pygame.draw.rect(s, (11, 12, 18), bar.inflate(6, 6))
        split = int(bar.w * fa)
        pygame.draw.rect(s, RED_D, (bar.x, bar.y, split, bar.h))
        pygame.draw.rect(s, RED, (bar.x, bar.y, split, bar.h // 2))
        pygame.draw.rect(s, BLUE_D, (bar.x + split, bar.y, bar.w - split, bar.h))
        pygame.draw.rect(s, BLUE, (bar.x + split, bar.y, bar.w - split, bar.h // 2))
        pygame.draw.rect(s, (62, 68, 86), bar, 2)
        mx = bar.x + split
        pygame.draw.line(s, INK, (mx, bar.top - 3), (mx, bar.bottom + 3), 2)
        pygame.draw.polygon(s, INK, [(mx - 6, bar.top - 3), (mx + 6, bar.top - 3),
                                     (mx, bar.top + 6)])
        pygame.draw.polygon(s, INK, [(mx - 6, bar.bottom + 3),
                                     (mx + 6, bar.bottom + 3),
                                     (mx, bar.bottom - 6)])

        text(s, "%d%%" % pa, 32, (bar.left - 16, bar.centery), RED, right=True)
        text(s, "%d%%" % (100 - pa), 32, (bar.right + 16, bar.centery), BLUE,
             left=True)

        text(s, self.stat_line(a), 15, (26, 96), DIM)
        text(s, self.stat_line(b), 15, (W - 26, 104), DIM, right=True)
        text(s, "%d:%04.1f" % (int(self.clock_t // 60), self.clock_t % 60), 17,
             (W // 2, 104), DIM, center=True)

    def draw_banner(self, s):
        win = self.winner
        t = min(1.0, self.banner_t / 0.35)
        size = int(lerp(120, 66, t))
        y = ARENA.centery - 26
        band = pygame.Surface((ARENA.w, 196), pygame.SRCALPHA)
        band.fill((8, 9, 14, 208))
        s.blit(band, (ARENA.left, y - 64))
        pygame.draw.line(s, win.colour, (ARENA.left, y - 64), (ARENA.right, y - 64), 2)
        pygame.draw.line(s, win.colour, (ARENA.left, y + 132), (ARENA.right, y + 132), 2)
        text(s, "%s WINS" % win.name, size, (W // 2, y), win.colour, center=True)
        if self.banner_t > 0.5:
            text(s, "%d hits  -  %d damage  -  %.0f DPS"
                 % (win.hits, int(win.dealt), win.dealt / max(1.0, self.clock_t)),
                 22, (W // 2, y + 56), INK, center=True)
            text(s, "SPACE / click  rematch        ESC  menu", 20,
                 (W // 2, y + 96), DIM, center=True)

    def draw_paused(self, s):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((0, 0, 0, 150))
        s.blit(v, (0, 0))
        text(s, "PAUSED", 72, (W // 2, ARENA.centery - 20), INK, center=True)
        text(s, "P  resume        R  rematch        ESC  menu", 20,
             (W // 2, ARENA.centery + 40), DIM, center=True)

    # -- the menu ----------------------------------------------------------
    def draw_menu(self, s):
        text(s, "BALL BRAWL", 66, (W // 2, 58), INK, center=True)
        text(s, "two balls, one arena, pick your weapons", 20,
             (W // 2, 108), DIM, center=True)

        if self.score[0] or self.score[1]:
            text(s, "SESSION   RED %d  -  %d BLUE" % (self.score[0], self.score[1]),
                 18, (W // 2, 140), DIM, center=True)
        text(s, "RED", 32, (56, 182), RED)
        text(s, "keys 1 2 3", 16, (150, 192), DIM)
        r = text(s, "BLUE", 32, (W - 56, 198), BLUE, right=True)
        text(s, "keys 8 9 0", 16, (r.left - 14, 200), DIM, right=True)

        for rect, kind, val in self.menu_layout():
            if kind == "pick":
                side, i = val
                self.draw_card(s, rect, WEAPONS[i], side, self.pick[side] == i)
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
                text(s, "FIGHT   (SPACE)", 28, rect.center, INK, center=True)

        if self.human:
            text(s, "WASD move      mouse aim      SPACE dash", 17,
                 (W // 2, 738), DIM, center=True)

    def draw_card(self, s, rect, wcls, side, selected):
        base = RED if side == 0 else BLUE
        bg = mix(PANEL, base, 0.22 if selected else 0.06)
        pygame.draw.rect(s, bg, rect)
        pygame.draw.rect(s, base if selected else (52, 57, 72), rect,
                         3 if selected else 1)
        icon = (rect.left + 46, rect.centery)
        self.draw_icon(s, icon, wcls, base)
        text(s, wcls.NAME, 25, (rect.left + 88, rect.top + 8),
             INK if selected else DIM)
        for k, line in enumerate(wcls.BLURB):
            text(s, line, 13, (rect.left + 88, rect.top + 38 + k * 16), DIM)
        # stat pips
        px = rect.left + 88
        for label, n in zip(("DMG", "RATE", "REACH"), wcls.PIPS):
            text(s, label, 12, (px, rect.bottom - 22), DIM)
            for k in range(5):
                c = base if k < n else (48, 52, 66)
                pygame.draw.rect(s, c, (px + 44 + k * 9, rect.bottom - 19, 6, 8))
            px += 98

    def draw_icon(self, s, c, wcls, colour):
        cx, cy = c
        pygame.draw.circle(s, mix(PANEL, colour, 0.8), (cx, cy), 15)
        pygame.draw.circle(s, mix(colour, (0, 0, 0), 0.4), (cx, cy), 15, 2)
        if wcls is Sword:
            for k in range(3):
                a = k * TAU / 3 + 0.4
                d = Vector2(math.cos(a), math.sin(a))
                pygame.draw.line(s, INK, (cx + d.x * 16, cy + d.y * 16),
                                 (cx + d.x * 31, cy + d.y * 31), 3)
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
        text(s, label, 21, (rect.centerx - 10, rect.centery), INK, center=True)
        text(s, key, 15, (rect.right - 10, rect.centery), DIM, right=True)


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
