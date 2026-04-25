#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "public" / "maps"
CACHE_DIR = ROOT / ".cache" / "maptiler-tiles"
MAPTILER_KEY_PATH = ROOT / "tools" / "maptiler_key.txt"
LOGICAL_WIDTH = 800
LOGICAL_HEIGHT = 500
PIXEL_RATIO = 2
WIDTH = LOGICAL_WIDTH * PIXEL_RATIO
HEIGHT = LOGICAL_HEIGHT * PIXEL_RATIO
TILE_SIZE = 512
STYLE = "openstreetmap"
LANGUAGE = "ru"
FALLBACK_LANGUAGE = "en"
TILE_DELAY_SECONDS = 0.15
USER_AGENT = (
    "FamilyTripHelper/1.0 (+https://familytrip.stasich7.ru; "
    "contact: map-generation@familytrip.stasich7.ru)"
)


@dataclass(frozen=True)
class Point:
    label: str
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteMap:
    key: str
    filename: str
    zoom: float
    points: tuple[Point, ...]
    center: tuple[float, float] | None = None


def latlon_to_world_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    scale = TILE_SIZE * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale
    y = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * scale
    return x, y


def center_for(route_map: RouteMap) -> tuple[float, float]:
    if route_map.center is not None:
        return route_map.center
    return (
        sum(point.lat for point in route_map.points) / len(route_map.points),
        sum(point.lon for point in route_map.points) / len(route_map.points),
    )


def project(point: Point, center_px: tuple[float, float], tile_zoom: int, zoom: float) -> tuple[float, float]:
    scale = 2 ** (tile_zoom - zoom)
    px, py = latlon_to_world_px(point.lat, point.lon, tile_zoom)
    cx, cy = center_px
    return LOGICAL_WIDTH / 2 + (px - cx) / scale, LOGICAL_HEIGHT / 2 + (py - cy) / scale


def tile_bounds(center_px: tuple[float, float], tile_zoom: int, zoom: float) -> tuple[int, int, int, int]:
    scale = 2 ** (tile_zoom - zoom)
    cx, cy = center_px
    min_world_x = cx - LOGICAL_WIDTH * scale / 2
    max_world_x = cx + LOGICAL_WIDTH * scale / 2
    min_world_y = cy - LOGICAL_HEIGHT * scale / 2
    max_world_y = cy + LOGICAL_HEIGHT * scale / 2
    return (
        math.floor(min_world_x / TILE_SIZE) - 1,
        math.ceil(max_world_x / TILE_SIZE) + 1,
        math.floor(min_world_y / TILE_SIZE) - 1,
        math.ceil(max_world_y / TILE_SIZE) + 1,
    )


def read_maptiler_key() -> str:
    return MAPTILER_KEY_PATH.read_text(encoding="utf-8").strip()


def maptiler_zoom(route_map: RouteMap) -> float:
    # MapTiler Static uses a 512px tile pyramid. This keeps user-facing zoom
    # equivalent to the familiar 256px OSM/Google zoom scale.
    return route_map.zoom - 1


def tile_path(tile_zoom: int, tile_x: int, tile_y: int, language: str) -> Path:
    return CACHE_DIR / STYLE / language / str(tile_zoom) / str(tile_x) / f"{tile_y}.png"


def tile_url(tile_zoom: int, tile_x: int, tile_y: int, language: str) -> str:
    key = read_maptiler_key()
    return f"https://api.maptiler.com/maps/{STYLE}/{tile_zoom}/{tile_x}/{tile_y}.png?key={key}&language={language}"


def fetch_tile(tile_zoom: int, tile_x: int, tile_y: int, language: str) -> Image.Image:
    path = tile_path(tile_zoom, tile_x, tile_y, language)
    if path.exists() and path.stat().st_size > 0:
        return Image.open(path).convert("RGB")

    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        tile_url(tile_zoom, tile_x, tile_y, language),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/png,image/*;q=0.8,*/*;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            path.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        if language != FALLBACK_LANGUAGE:
            return fetch_tile(tile_zoom, tile_x, tile_y, FALLBACK_LANGUAGE)
        raise RuntimeError(f"MapTiler tile request failed with HTTP {exc.code}: z={tile_zoom} x={tile_x} y={tile_y}") from exc

    time.sleep(TILE_DELAY_SECONDS)
    return Image.open(path).convert("RGB")


def draw_base_map(route_map: RouteMap) -> tuple[Image.Image, list[tuple[float, float]]]:
    tile_zoom = math.ceil(maptiler_zoom(route_map))
    center = center_for(route_map)
    center_px = latlon_to_world_px(center[0], center[1], tile_zoom)
    scale = 2 ** (tile_zoom - maptiler_zoom(route_map))
    min_tile_x, max_tile_x, min_tile_y, max_tile_y = tile_bounds(center_px, tile_zoom, maptiler_zoom(route_map))
    max_tile_index = 2**tile_zoom
    image = Image.new("RGB", (LOGICAL_WIDTH, LOGICAL_HEIGHT), "#e7efe1")

    for raw_tile_x in range(min_tile_x, max_tile_x + 1):
        tile_x = raw_tile_x % max_tile_index
        for tile_y in range(min_tile_y, max_tile_y + 1):
            if tile_y < 0 or tile_y >= max_tile_index:
                continue
            tile = fetch_tile(tile_zoom, tile_x, tile_y, LANGUAGE)
            size = max(1, round(TILE_SIZE / scale))
            if size != TILE_SIZE:
                tile = tile.resize((size, size), Image.Resampling.LANCZOS)
            left = round(LOGICAL_WIDTH / 2 + (raw_tile_x * TILE_SIZE - center_px[0]) / scale)
            top = round(LOGICAL_HEIGHT / 2 + (tile_y * TILE_SIZE - center_px[1]) / scale)
            image.paste(tile, (left, top))

    projected = [project(point, center_px, tile_zoom, maptiler_zoom(route_map)) for point in route_map.points]
    return image, projected


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_overlay(image: Image.Image, projected: list[tuple[float, float]], route_map: RouteMap) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    line = [(round(x), round(y)) for x, y in projected]
    if len(line) > 1:
        draw.line(line, fill=(255, 255, 255, 230), width=11, joint="curve")
        draw.line(line, fill=(217, 79, 50, 235), width=6, joint="curve")

    font = load_font(19, bold=True)
    for index, (x, y) in enumerate(projected, start=1):
        cx = round(x)
        cy = round(y)
        radius = 15
        draw.ellipse(
            (cx - radius - 5, cy - radius - 5, cx + radius + 5, cy + radius + 5),
            fill=(255, 255, 255, 248),
        )
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(217, 79, 50, 255),
            outline=(110, 42, 31, 100),
            width=2,
        )
        text = str(index)
        bbox = draw.textbbox((0, 0), text, font=font)
        draw.text(
            (cx - (bbox[2] - bbox[0]) / 2, cy - (bbox[3] - bbox[1]) / 2 - 2),
            text,
            font=font,
            fill=(255, 255, 255, 255),
        )

    draw.rounded_rectangle(
        (11, 11, LOGICAL_WIDTH - 11, LOGICAL_HEIGHT - 11),
        radius=17,
        outline=(40, 48, 52, 75),
        width=2,
    )


def render_map(route_map: RouteMap) -> Path:
    image, projected = draw_base_map(route_map)
    draw_overlay(image, projected, route_map)
    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / route_map.filename
    image.save(output, "PNG", optimize=True)
    return output


MAPS = [
    RouteMap(
        "2026-08-05",
        "2026-08-05-tbilisi-first-evening.png",
        15,
        (
            Point("Площадь Свободы", 41.6934, 44.8015),
            Point("улица Коте Абхази", 41.6910, 44.8065),
            Point("Мост Мира", 41.6930, 44.8085),
            Point("парк Рике", 41.6938, 44.8110),
            Point("мини-зоопарк у Самебы", 41.6975, 44.8166),
        ),
    ),
    RouteMap(
        "2026-08-06",
        "2026-08-06-tbilisi-old-town.png",
        15,
        (
            Point("Абанотубани", 41.6879, 44.8110),
            Point("Инжировое ущелье", 41.6868, 44.8098),
            Point("крепость Нарикала", 41.6883, 44.8085),
            Point("канатная дорога к Нарикале", 41.6924, 44.8109),
            Point("храм Метехи", 41.6905, 44.8119),
        ),
    ),
    RouteMap(
        "2026-08-07",
        "2026-08-07-tbilisi-rustaveli-mtatsminda.png",
        15,
        (
            Point("Площадь Свободы", 41.6934, 44.8015),
            Point("проспект Руставели", 41.6969, 44.7991),
            Point("Тбилисский театр оперы и балета", 41.7003, 44.7953),
            Point("нижняя станция фуникулера", 41.6953, 44.7913),
            Point("парк Мтацминда", 41.6950, 44.7854),
        ),
    ),
    RouteMap(
        "2026-08-08",
        "2026-08-08-mtskheta-jvari.png",
        11,
        (
            Point("Тбилиси", 41.7151, 44.8271),
            Point("Мцхета", 41.8451, 44.7190),
            Point("Светицховели", 41.8429, 44.7212),
            Point("монастырь Джвари", 41.8386, 44.7337),
        ),
    ),
    RouteMap(
        "2026-08-09",
        "2026-08-09-tbilisi-markets-sololaki.png",
        10,
        (
            Point("Дезертирский рынок", 41.7215, 44.7950),
            Point("Сухой мост", 41.7018, 44.8003),
            Point("парк 9 апреля", 41.6971, 44.7988),
            Point("Площадь Свободы", 41.6934, 44.8015),
            Point("Сололаки", 41.6902, 44.7985),
        ),
    ),
    RouteMap(
        "2026-08-10",
        "2026-08-10-kakheti-sighnaghi.png",
        8.5,
        (
            Point("Тбилиси", 41.7151, 44.8271),
            Point("монастырь Бодбе", 41.6064, 45.9344),
            Point("Сигнахи", 41.6186, 45.9216),
            Point("Алазанская долина", 41.7450, 45.9800),
        ),
    ),
    RouteMap(
        "2026-08-11",
        "2026-08-11-tbilisi-left-bank.png",
        15,
        (
            Point("парк Муштаиди", 41.7216, 44.7894),
            Point("район Чугурети", 41.7100, 44.7964),
            Point("проспект Агмашенебели", 41.7085, 44.8006),
            Point("Сухой мост", 41.7018, 44.8003),
        ),
    ),
    RouteMap(
        "2026-08-12",
        "2026-08-12-kazbegi-road.png",
        9,
        (
            Point("Тбилиси", 41.7151, 44.8271),
            Point("Жинвальское водохранилище", 42.1279, 44.7725),
            Point("крепость Ананури", 42.1639, 44.7032),
            Point("Гудаури", 42.4770, 44.4760),
            Point("Степанцминда", 42.6575, 44.6414),
            Point("гора Казбек", 42.6960, 44.5180),
        ),
    ),
    RouteMap(
        "2026-08-13",
        "2026-08-13-batumi-first-evening.png",
        15,
        (
            Point("Старый Батумский бульвар", 41.6522, 41.6361),
            Point("скульптура Али и Нино", 41.6558, 41.6408),
            Point("Батумский морской порт", 41.6535, 41.6423),
            Point("Площадь Европы", 41.6507, 41.6366),
            Point("Laguna", 41.6486, 41.6295),
        ),
    ),
    RouteMap(
        "2026-08-14",
        "2026-08-14-batumi-old-town.png",
        15,
        (
            Point("Batumi Piazza", 41.6498, 41.6410),
            Point("Площадь Европы", 41.6507, 41.6366),
            Point("Астрономические часы Батуми", 41.6506, 41.6375),
            Point("улица Мемеда Абашидзе", 41.6490, 41.6379),
            Point("Старый Батумский бульвар", 41.6517, 41.6338),
        ),
    ),
    RouteMap(
        "2026-08-15",
        "2026-08-15-batumi-argo-port.png",
        14,
        (
            Point("нижняя станция канатной дороги Арго", 41.6477, 41.6466),
            Point("верхняя станция канатной дороги Арго", 41.6575, 41.6815),
            Point("Батумский морской порт", 41.6535, 41.6423),
            Point("Парк чудес", 41.6556, 41.6382),
            Point("колесо обозрения", 41.6560, 41.6369),
        ),
    ),
    RouteMap(
        "2026-08-16",
        "2026-08-16-batumi-botanical-garden.png",
        12,
        (
            Point("центр Батуми", 41.6507, 41.6366),
            Point("Батумский ботанический сад", 41.6944, 41.7073),
            Point("Зеленый мыс", 41.6913, 41.7045),
        ),
    ),
    RouteMap(
        "2026-08-17",
        "2026-08-17-batumi-family-day.png",
        15,
        (
            Point("парк 6 мая", 41.6478, 41.6267),
            Point("Площадь Европы", 41.6507, 41.6366),
            Point("Batumi Piazza", 41.6498, 41.6410),
            Point("Парк чудес", 41.6556, 41.6382),
            Point("колесо обозрения", 41.6560, 41.6369),
        ),
    ),
    RouteMap(
        "2026-08-18",
        "2026-08-18-adjara-makhuntseti.png",
        11,
        (
            Point("Батуми", 41.6507, 41.6366),
            Point("Махунцети", 41.5749, 41.8584),
            Point("водопад Махунцети", 41.5740, 41.8599),
            Point("арочный мост царицы Тамары", 41.5715, 41.8618),
        ),
    ),
    RouteMap(
        "2026-08-19",
        "2026-08-19-batumi-market-old-town.png",
        15,
        (
            Point("Батумский рынок", 41.6440, 41.6475),
            Point("Batumi Piazza", 41.6498, 41.6410),
            Point("Площадь Европы", 41.6507, 41.6366),
            Point("Астрономические часы Батуми", 41.6506, 41.6375),
            Point("Старый Батумский бульвар", 41.6517, 41.6338),
        ),
    ),
    RouteMap(
        "2026-08-20",
        "2026-08-20-batumi-final-day.png",
        14,
        (
            Point("пляж у Батумского бульвара", 41.6505, 41.6288),
            Point("Площадь Европы", 41.6507, 41.6366),
            Point("Batumi Piazza", 41.6498, 41.6410),
            Point("озеро Ардагани и танцующие фонтаны", 41.6375, 41.6115),
        ),
    ),
    RouteMap(
        "2026-08-21",
        "2026-08-21-batumi-airport.png",
        12.5,
        (
            Point("проживание в центре Батуми", 41.6507, 41.6366),
            Point("аэропорт Батуми", 41.6103, 41.5997),
        ),
    ),
]


MAPS_BY_KEY = {route_map.key: route_map for route_map in MAPS}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one route map PNG from real OSM tiles.")
    parser.add_argument("key", choices=sorted(MAPS_BY_KEY), help="Map key, for example 2026-08-05.")
    args = parser.parse_args()

    route_map = MAPS_BY_KEY[args.key]
    output = render_map(route_map)
    print(output.relative_to(ROOT))
    print("Точки на карте: " + "; ".join(f"{index} — {point.label}" for index, point in enumerate(route_map.points, start=1)))


if __name__ == "__main__":
    main()
