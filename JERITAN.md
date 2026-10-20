# JERITAN

A browser game, and the only thing in this repository that is not Python.

You are the duty detective at Fourth District. Two calls have come in from
14 Lindenweg in one week, and the second is the kind the shift sergeant
hands upward: screaming from under a neighbour's floor, and a tenant who
"is not herself and does not look right". You have a torch, a notebook and
no warrant.

Five rooms, forty-five exhibits, eight questions she answers a little too
well, and a cellar that opens either with the key taped under the cutlery
drawer or on five solid exhibits and the nerve to take a door off its
frame. Two women with one face at the foot of the stairs. Six endings.

The game is in Indonesian. Sound is generated in code, as everything else
in this repository is: a room drone, a heartbeat that follows how close
she is standing, and the monitor on the hall shelf that is paired with
something below the floor. Headphones help.

## Playing it

One file, no server:

```
jeritan.html
```

Open it in a browser. That is the whole game — no build step, no assets,
nothing fetched except two fonts from Google Fonts, and it plays without
those too.

## Deploying it

`jeritan.html` is written for the Claude Artifact runtime, which wraps a
page in its own `<!doctype html>`, `<head>` and `<body>` at publish time.
Static hosting does not, so there is a build step whose whole job is that
wrapper:

```
bash build_site.sh
```

It writes `site/`:

| | |
|---|---|
| `index.html` | the game, inside a real document, with link-preview meta and a favicon |
| `404.html` | for anything else anybody asks this host for |
| `robots.txt`, `sitemap.xml` | the usual two |
| `og.png` | the card WhatsApp and Twitter show when the link is pasted |

The source is never edited by the build, so there is only ever one copy of
the game in this repository. `site/` is build output and is ignored, like
`build/` and `dist/`.

### Netlify

`netlify.toml` already says `bash build_site.sh` and `publish = "site"`.
There is nothing to install: no npm, no dependencies, and the build image
has bash.

**From git** — point Netlify at this repository and take the defaults it
reads from `netlify.toml`. Every push redeploys.

**Without git** — run the build and drag the `site/` folder onto
app.netlify.com, or:

```
npx netlify-cli deploy --prod --dir=site
```

Set the real address once it exists, so that link previews and the sitemap
stop pointing at the placeholder:

```
SITE_URL = "https://your-name.netlify.app"
```

in `netlify.toml` under `[build.environment]`. `build_site.sh` reads the
same variable, so a local build matches what Netlify publishes.

## Regenerating the preview card

`og.png` is a 1200×630 screenshot of a small HTML card, and it is the one
`.png` in this repository that is a real asset rather than a working
screenshot — hence its exception in `.gitignore`. Remake it with any
headless browser if the title or the numbers on it ever change.
