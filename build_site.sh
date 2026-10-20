#!/usr/bin/env bash
#
# Builds site/ for Netlify out of one source file: jeritan.html.
#
# jeritan.html is written for the Artifact skeleton, which supplies its own
# <!doctype>, <html>, <head> and <body> at publish time. Plain static hosting
# does not, so this script wraps it: a complete document, link-preview meta,
# a favicon, and the few small files a site is expected to serve. The source
# is never edited, so there is only ever one copy of the game in this repo.
#
#   bash build_site.sh   ->  site/{index,404}.html, robots.txt, sitemap.xml, og.png
#
set -euo pipefail
cd "$(dirname "$0")"

SRC="jeritan.html"
OUT="site"
TITLE="Jeritan"
DESC="Permainan penyidikan: satu flat, satu malam, dan dua perempuan dengan satu wajah. Geledah ruangannya, desak keterangannya hanya di tempat ada barang bukti, lalu tentukan siapa yang naik ke mobil."
URL="${SITE_URL:-https://jeritan.netlify.app}"
FONTS="https://fonts.googleapis.com/css2?family=Special+Elite&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
ICON="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E%3Crect%20width='32'%20height='32'%20rx='6'%20fill='%230c1117'/%3E%3Cpath%20d='M16%205.5a6.2%206.2%200%200%201%203.2%2011.5L21.4%2026.5h-10.8L12.8%2017A6.2%206.2%200%200%201%2016%205.5z'%20fill='%23d8933a'/%3E%3C/svg%3E"

[ -f "$SRC" ] || { echo "build_site.sh: cannot find "; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT"

# --- the page itself ---------------------------------------------------------
# Five lines at the top of the source are either Artifact-only or rewritten in
# the <head> below, so they are dropped on the way through.
{
  cat <<HEAD
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>$TITLE</title>
<meta name="description" content="$DESC">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#08090b">
<meta property="og:type" content="website">
<meta property="og:site_name" content="$TITLE">
<meta property="og:title" content="$TITLE">
<meta property="og:description" content="$DESC">
<meta property="og:url" content="$URL/">
<meta property="og:image" content="$URL/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="id_ID">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="$TITLE">
<meta name="twitter:description" content="$DESC">
<meta name="twitter:image" content="$URL/og.png">
<link rel="canonical" href="$URL/">
<link rel="icon" href="$ICON">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="$FONTS">
</head>
<body>
HEAD
  sed -e '/claude:viewport-fit-sides/d' \
      -e '/<meta charset=/d' \
      -e '/<meta name="viewport"/d' \
      -e '/<title>/d' \
      -e '/fonts\.googleapis\.com/d' \
      "$SRC"
  printf '</body>\n</html>\n'
} > "$OUT/index.html"

# --- 404 ---------------------------------------------------------------------
cat > "$OUT/404.html" <<HTML
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tidak ada di berkas ini</title>
<meta name="robots" content="noindex">
<meta name="color-scheme" content="dark">
<link rel="icon" href="$ICON">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="$FONTS">
<style>
  html,body{height:100%}
  body{margin:0;display:grid;place-items:center;background:#08090b;color:#dbe1e6;
       font:16px/1.6 "IBM Plex Sans","Segoe UI",system-ui,sans-serif;
       padding:0 max(16px,env(safe-area-inset-left,0px))}
  main{max-width:46ch;text-align:left}
  .no{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;
      letter-spacing:.2em;color:#d8933a}
  h1{font-family:"Special Elite","Courier New",monospace;font-size:clamp(28px,7vw,42px);
     line-height:1.05;margin:10px 0 14px}
  p{color:#9aa5ae;margin:0 0 20px}
  a{display:inline-block;border:1px solid #2e3942;padding:9px 14px;color:#dbe1e6;
    text-decoration:none;font-family:"Special Elite","Courier New",monospace;letter-spacing:.05em}
  a:hover{border-color:#d8933a;color:#d8933a}
</style>
</head>
<body>
<main>
  <div class="no">PERKARA 7731-K &nbsp;·&nbsp; 404</div>
  <h1>Halaman ini tidak ada di dalam berkas</h1>
  <p>Yang Anda cari tidak pernah masuk ke map perkara ini. Yang ada cuma satu flat, satu malam, dan satu pintu yang digembok dari sisi yang salah.</p>
  <a href="/">Kembali ke Lindenweg 14</a>
</main>
</body>
</html>
HTML

# --- robots ------------------------------------------------------------------
cat > "$OUT/robots.txt" <<ROBOTS
User-agent: *
Allow: /

Sitemap: $URL/sitemap.xml
ROBOTS

cat > "$OUT/sitemap.xml" <<SITEMAP
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>$URL/</loc><changefreq>monthly</changefreq></url>
</urlset>
SITEMAP

# --- link preview card -------------------------------------------------------
if [ -f og.png ]; then
  cp og.png "$OUT/og.png"
else
  echo "build_site.sh: no og.png, link previews will have no image"
fi

bytes=$(wc -c < "$OUT/index.html" | tr -d ' ')
echo "build_site.sh: $OUT/index.html ready ($bytes bytes), plus 404, robots, sitemap."
