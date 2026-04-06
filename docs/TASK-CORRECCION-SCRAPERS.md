# Corrección de Scrapers — Usar Librerías Reales

## El problema
Los scrapers se construyeron como código custom en vez de usar las librerías
que el plan especificó. Esto viola Regla 1 y Regla 2 del CLAUDE.md.

## Instrucciones por plataforma

### Twitter — NO TOCAR (ya está bien)
Usa twscrape + httpx fallback. Verificar que funciona con @Alejandro_Pinha.

### Instagram — REESCRIBIR usando Instaloader directo
```python
import instaloader
L = instaloader.Instaloader()
profile = instaloader.Profile.from_username(L.context, "alejandro.pinha")
# profile.followers, profile.followees, profile.mediacount
for post in profile.get_posts():
    # post.caption, post.likes, post.comments, post.date_utc
    # post.is_video, post.video_view_count, post.typename
    break  # limitar a últimos 100
```
NO escribir wrappers custom. Llamar Instaloader directo.
Probar con: @alejandro.pinha y @rafasolanoperez

### Facebook — FALLBACK CHAIN con dos librerías
```python
# Intento 1: facebook-scraper (kevinzg)
try:
    from facebook_scraper import get_posts, get_profile
    posts = list(get_posts(page_name, pages=3))
except Exception:
    pass

# Intento 2: facebook_page_scraper (fallback)
try:
    from facebook_page_scraper import Facebook_scraper
    scraper = Facebook_scraper(page_name, 20)
    posts_dict = scraper.scrap_to_json()
except Exception:
    pass
```
Instalar AMBAS: pip install facebook-scraper facebook-page-scraper
Si ninguna funciona, loguear error limpio. Facebook es inestable por diseño.
Probar con: página de Facebook "Alejandro Piña Medina"

### TikTok — REESCRIBIR usando TikTok-Api con Playwright
```python
from TikTokApi import TikTokApi
# Requiere: pip install TikTokApi playwright
# Setup: python -m playwright install chromium

async with TikTokApi() as api:
    await api.create_sessions(num_sessions=1, sleep_after=3)
    user = api.user(username=handle)
    user_data = await user.info()
    async for video in user.videos(count=30):
        # video.stats, video.desc, video.createTime
        pass
```
REQUIERE Playwright. Si no está instalado, reportar como blocker.
NO hacer workaround con httpx.

### YouTube — USAR scrapetube (sin API key)
```python
import scrapetube
videos = scrapetube.get_channel(channel_url=f"https://youtube.com/@{handle}")
for video in videos:
    # video['videoId'], video['title'], video['viewCountText']
    break  # limitar
```
Si el dirigente NO tiene canal, retornar lista vacía. NO inventar datos.

## Qué NO hacer
- NO escribir wrappers httpx custom que parsean HTML
- NO inventar datos si el scraper falla
- NO reportar "funcional" sin probar contra un perfil real
- NO hacer commit de los 5 scrapers juntos — uno por uno

## Entregable
Al terminar, reportar esta tabla:

| Plataforma | Librería | Perfil probado | Posts | Status |
|---|---|---|---|---|
| Twitter | twscrape + httpx | @Alejandro_Pinha | N | ✅/❌ |
| Instagram | instaloader | @alejandro.pinha | N | ✅/❌ |
| Facebook | kevinzg + page_scraper | Piña Medina | N | ✅/❌ |
| TikTok | TikTok-Api 7.3 | (buscar si tiene) | N | ✅/❌/🚫 |
| YouTube | scrapetube | (buscar si tiene) | N | ✅/❌/🚫 |
