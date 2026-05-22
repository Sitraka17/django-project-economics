"""
Téléchargeur de photos GreenGo - La Maison Rouge Beaurieux
Prérequis : pip install playwright && playwright install chromium
"""

import asyncio
import os
import re
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.greengo.voyage/hote/la-maison-rouge-beaurieux-02"
OUTPUT_DIR = Path("maison_rouge_photos")


async def get_all_image_urls(page) -> list[str]:
    """Récupère toutes les URLs d'images depuis la page et le __NEXT_DATA__."""
    urls = set()

    # 1. Depuis __NEXT_DATA__ (source la plus fiable — contient toutes les images)
    next_data = await page.evaluate("""() => {
        const el = document.getElementById('__NEXT_DATA__');
        return el ? el.textContent : null;
    }""")

    if next_data:
        import json
        data = json.loads(next_data)
        # Cherche récursivement toutes les clés contenant des URLs d'images
        text = json.dumps(data)
        found = re.findall(
            r'(greengobackend-production-media/pictures/accommmodation/[^"\'\\]+\.(?:jpeg|jpg|png|webp))',
            text
        )
        for path in found:
            urls.add(f"https://media.greengo.voyage/{path}")

    # 2. Depuis les balises <img> du DOM (fallback)
    img_urls = await page.evaluate("""() => {
        return [...document.querySelectorAll('img')]
            .map(img => img.src || img.dataset.src || '')
            .filter(src => src.includes('greengobackend') || src.includes('media.greengo'));
    }""")

    for src in img_urls:
        # Normalise vers URL directe (sans proxy de redimensionnement)
        match = re.search(r'plain/(s3://greengobackend-production-media/(.+))', src)
        if match:
            urls.add(f"https://media.greengo.voyage/{match.group(2)}")
        elif src.startswith("https://media.greengo.voyage/"):
            urls.add(src)

    return sorted(urls)


async def scroll_and_open_gallery(page):
    """Fait défiler la page et tente d'ouvrir la galerie complète."""
    print("⏳ Chargement de la page...")
    await page.goto(URL, wait_until="networkidle", timeout=30000)

    # Cherche et clique sur le bouton "Voir toutes les photos"
    for selector in [
        "button:has-text('photos')",
        "button:has-text('Voir')",
        "[data-testid='photo-gallery']",
        ".photo-gallery__see-all",
    ]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(2000)
                print(f"✅ Galerie ouverte via : {selector}")
                break
        except Exception:
            continue

    # Scroll pour forcer le lazy-loading
    for _ in range(5):
        await page.keyboard.press("End")
        await page.wait_for_timeout(800)

    await page.wait_for_timeout(1500)


def download_image(url: str, dest: Path, index: int) -> bool:
    """Télécharge une image et la sauvegarde localement."""
    ext = url.rsplit(".", 1)[-1].split("?")[0]
    filename = dest / f"photo_{index:02d}.{ext}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.greengo.voyage/",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            filename.write_bytes(resp.read())
        print(f"  ✅ {filename.name}")
        return True
    except Exception as e:
        print(f"  ❌ Erreur photo_{index:02d} : {e}")
        return False


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            locale="fr-FR",
        )
        page = await context.new_page()

        await scroll_and_open_gallery(page)
        image_urls = await get_all_image_urls(page)
        await browser.close()

    if not image_urls:
        print("❌ Aucune image trouvée. Vérifiez l'URL ou essayez headless=False.")
        return

    print(f"\n📷 {len(image_urls)} images trouvées :\n")
    for i, url in enumerate(image_urls, 1):
        print(f"  {i:2d}. {url}")

    # Sauvegarde la liste d'URLs
    urls_file = OUTPUT_DIR / "urls.txt"
    urls_file.write_text("\n".join(image_urls))
    print(f"\n💾 Liste sauvegardée dans : {urls_file}")

    # Téléchargement
    print(f"\n⬇️  Téléchargement vers ./{OUTPUT_DIR}/\n")
    ok = sum(download_image(url, OUTPUT_DIR, i) for i, url in enumerate(image_urls, 1))
    print(f"\n✅ {ok}/{len(image_urls)} images téléchargées dans ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())