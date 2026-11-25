# meta dev: @QpjdQ
# meta name: Pomidorka

import asyncio
import io
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT_BOLD = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSans/full/ttf/NotoSans-Bold.ttf"
FONT_REGULAR = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSans/full/ttf/NotoSans-Regular.ttf"

# Ключи должны совпадать во всех темах, иначе загрузчик отклонит баннер.
themes = {
    "dark": {
        "background_color": "#0F0A14",
        "main_color": "#FFFFFF",
        "desc_color": "#E7A8D9",
        "accent_color": "#FF4FC8",
        "cover_placeholder_color": "#2A1838",
        "progress_track_color": "#5A2F6E",
    },
    "light": {
        "background_color": "#F7EEF9",
        "main_color": "#1A0E1F",
        "desc_color": "#7A4A8A",
        "accent_color": "#D6249A",
        "cover_placeholder_color": "#E8D5EE",
        "progress_track_color": "#E0C6E8",
    },
}

options = {
    "show_cover": True,
    "show_footer": True,
}

W, H = 1000, 340
S = 2  # сглаживание: рисуем в 2 раза больше и уменьшаем
COVER_X, COVER_Y, COVER_SIZE = 24, 64, 252
TEXT_X = COVER_X + COVER_SIZE + 28
RIGHT = W - 24

HEADS = {
    0: "Играет в {name}",
    1: "Стримит {name}",
    2: "Слушает {name}",
    3: "Смотрит {name}",
}
# Какую активность показывать первой, если их несколько
ORDER = [2, 0, 1, 3]


def pick_activity(data):
    activities = data.get("activities") or []
    for kind in ORDER:
        for activity in activities:
            if activity.get("type") == kind:
                return activity
    return None


def image_url(activity):
    assets = activity.get("assets") or {}
    image = assets.get("large_image", "")
    app_id = activity.get("application_id")
    if image.startswith(("http://", "https://")):
        return image
    if image.startswith("mp:"):
        return "https://media.discordapp.net/" + image[3:]
    if image.startswith("spotify:"):
        return "https://i.scdn.co/image/" + image[8:]
    if image.startswith("youtube:"):
        return f"https://i.ytimg.com/vi/{image[8:]}/hqdefault.jpg"
    if image and ":" not in image and app_id:
        return f"https://cdn.discordapp.com/app-assets/{app_id}/{image}.png"
    return None


def format_time(seconds):
    seconds = int(max(0, seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


def load_font(raw, size):
    if raw:
        return ImageFont.truetype(io.BytesIO(raw), size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def fit_text(text, font, max_width):
    if font.getlength(text) <= max_width:
        return text
    while text and font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text + "…"


def draw_banner(colors, enabled, activity, bold_raw, regular_raw, cover_raw):
    img = Image.new("RGBA", (W * S, H * S), colors["background_color"])
    draw = ImageDraw.Draw(img)

    head_font = load_font(bold_raw, 34 * S)
    title_font = load_font(bold_raw, 44 * S)
    desc_font = load_font(regular_raw, 30 * S)
    small_font = load_font(regular_raw, 26 * S)

    max_text_width = (RIGHT - TEXT_X) * S

    # Обложка с закруглёнными углами
    cover_px = COVER_SIZE * S
    mask = Image.new("L", (cover_px, cover_px), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cover_px - 1, cover_px - 1), radius=22 * S, fill=255)
    cover = Image.new("RGBA", (cover_px, cover_px), colors["cover_placeholder_color"])
    if enabled.get("show_cover", True) and cover_raw:
        try:
            picture = Image.open(io.BytesIO(cover_raw)).convert("RGBA")
            cover = ImageOps.fit(picture, (cover_px, cover_px), Image.Resampling.LANCZOS)
        except OSError:
            pass
    img.paste(cover, (COVER_X * S, COVER_Y * S), mask)

    # Заголовок над карточкой
    name = activity.get("name", "")
    head = HEADS.get(activity.get("type"), "{name}").format(name=name)
    draw.text((COVER_X * S, 22 * S), fit_text(head, head_font, (RIGHT - COVER_X) * S),
              font=head_font, fill=colors["main_color"])

    # Название и подпись
    title = activity.get("details") or name
    subtitle = activity.get("state") or ""
    draw.text((TEXT_X * S, 108 * S), fit_text(title, title_font, max_text_width),
              font=title_font, fill=colors["main_color"])
    if subtitle:
        draw.text((TEXT_X * S, 150 * S), fit_text(subtitle, desc_font, max_text_width),
                  font=desc_font, fill=colors["desc_color"])

    # Нижняя строка: прогресс или прошедшее время
    if enabled.get("show_footer", True):
        timestamps = activity.get("timestamps") or {}
        start, end = timestamps.get("start"), timestamps.get("end")
        if start:
            elapsed = max(0, time.time() - start / 1000)
            bar_left, bar_right = TEXT_X * S, RIGHT * S
            bar_top, bar_bottom = 230 * S, 238 * S
            if end:
                duration = (end - start) / 1000
                position = min(elapsed, duration)
                fraction = position / duration if duration else 0
                draw.rounded_rectangle((bar_left, bar_top, bar_right, bar_bottom),
                                       radius=4 * S, fill=colors["progress_track_color"])
                filled = bar_left + (bar_right - bar_left) * fraction
                draw.rounded_rectangle((bar_left, bar_top, max(filled, bar_left + 8 * S), bar_bottom),
                                       radius=4 * S, fill=colors["main_color"])
                draw.text((bar_left, 252 * S), format_time(position),
                          font=small_font, fill=colors["desc_color"])
                draw.text((bar_right, 252 * S), format_time(duration),
                          font=small_font, fill=colors["desc_color"], anchor="ra")
            else:
                draw.text((TEXT_X * S, 252 * S), "Прошло: " + format_time(elapsed),
                          font=small_font, fill=colors["accent_color"])

    out = img.resize((W, H), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    out.save(buffer, format="PNG")
    buffer.seek(0)
    buffer.name = "banner.png"
    return buffer


async def render(settings, data, font_bytes):
    activity = pick_activity(data)
    if activity is None:
        return None

    bold_raw = font_bytes or await settings["dl_font"](FONT_BOLD)
    regular_raw = font_bytes or await settings["dl_font"](FONT_REGULAR)

    cover_url = image_url(activity)
    cover_raw = await settings["dl_bytes"](cover_url) if cover_url else None

    return await asyncio.to_thread(
        draw_banner,
        settings["colors"],
        settings["options"],
        activity,
        bold_raw,
        regular_raw,
        cover_raw,
    )
