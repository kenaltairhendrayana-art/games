# OPERATION: IRON LINE

A military tower-defence game. Hold the corridor.

Enemy armour advances along the supply road while air units push straight
for your Forward HQ. Emplace weapons, refit them, and do not let the line
break.

Seven chapters, forty tours, and a two-hundred-wave endgame in a city
that spends its soldiers twice.

## Running it

**From a release build** — one file, no installer:

```
IronLine.exe
```

**From source** — one dependency:

```
pip install pygame-ce
python iron_line.py
```

## Controls

| | |
|---|---|
| `1`..`8` | select an emplacement to build (6 loadout + 2 special slots) |
| Left click | place / select an emplacement |
| Right click | cancel placement / deselect |
| `E` | refit the selected emplacement |
| `X` | sell it |
| `T` | cycle its targeting priority |
| `SPACE` | deploy the next wave early (pays a readiness bonus) |
| `F` | cycle game speed (1x / 2x / 3x) |
| `P` | pause |
| `M` | music on / off |
| `ESC` | cancel, then open the pause menu |
| `F11` | fullscreen |

## Where your save goes

Never next to the game. The profile is written to the operating system's
own data directory:

| | |
|---|---|
| Windows | `%APPDATA%\IronLine\iron_line_profile.json` |
| macOS | `~/Library/Application Support/IronLine/` |
| Linux | `~/.local/share/iron-line/` |

A profile left beside the script by an older build is copied forward the
first time you run a newer one. The old file is left where it is.

## Building a release

```
python build.py
```

Produces `dist/IronLine.exe`. That single file is the whole
distribution — there is nothing to ship beside it.

If a build will not start, `python build.py --console` makes the same
thing with a console window behind it, so you can see the traceback a
windowed build swallows.

## No assets

There are none. Every graphic in this game is drawn in code — every
unit, every map, every cutscene — and all eighteen pieces of music are
generated at runtime from a five-note motif, with no audio files
anywhere. The game is one Python file.

That is not a boast, it is a licensing fact: there is nothing in the
build that belongs to anybody else.
