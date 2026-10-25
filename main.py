import os
import re
import sys
import ffmpeg
from yt_dlp import YoutubeDL

COOKIES_FILE = "cookies.txt"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()

if SCRIPT_DIR not in os.environ["PATH"]:
    os.environ["PATH"] = SCRIPT_DIR + os.pathsep + os.environ["PATH"]

cookies_path = os.path.join(SCRIPT_DIR, COOKIES_FILE)


def sanitize_filename(filename):
    """Очищает строку от символов, запрещенных в именах файлов Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def get_video_info_and_formats(url):
    """Получает название видео и список доступных разрешений."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": False,
        "ffmpeg_location": SCRIPT_DIR,
        "remote_components": ["ejs:github"],
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": [
                "player_client=tvhtml5,android",
                "player_js_variant=tv"
            ]
        }
    }

    if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
        ydl_opts["cookiefile"] = cookies_path
        print(f"🍪 Используются локальные куки: {cookies_path}")
    else:
        print("⚠️ Работа в гостевом режиме (без куков)...")

    print("🔍 Синхронизация с EJS-дешифратором и прохождение JS-челленджа...")
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"❌ Критическая ошибка yt-dlp при разборе: {e}")
            return None, None, None

        # Получаем и очищаем оригинальное название видео
        video_title = sanitize_filename(info.get("title", "video"))

        formats = info.get("formats", [])
        unique_resolutions = {}
        for f in formats:
            height = f.get("height")
            if height:
                format_note = f.get("format_note") or f.get("resolution") or f"{height}p"
                unique_resolutions[height] = format_note
                
        return sorted(unique_resolutions.keys(), reverse=True), unique_resolutions, video_title


def download_and_split(url):
    """Скачивает видеопотоки и разделяет их с помощью FFmpeg, используя оригинальное имя."""
    resolutions, res_dict, video_title = get_video_info_and_formats(url)
    if not resolutions:
        print("❌ Не удалось найти доступные форматы видео.")
        return

    print(f"\n🎥 Найдено видео: {video_title}")
    print("Доступные варианты качества:")
    for idx, res in enumerate(resolutions, 1):
        print(f"[{idx}] {res}p ({res_dict[res]})")
    
    while True:
        try:
            choice = int(input(f"\nВыберите номер качества (1-{len(resolutions)}): "))
            if 1 <= choice <= len(resolutions):
                selected_height = resolutions[choice - 1]
                break
            print("Неверный выбор. Попробуйте еще раз.")
        except ValueError:
            print("Пожалуйста, введите число.")

    output_dir = os.path.join(SCRIPT_DIR, "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Имя для временного полного файла
    temp_video_path = os.path.join(output_dir, "temp_full_video.mp4")

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "format_sort": [f"res:{selected_height}", "vcodec:h264", "acodec:aac"],
        "outtmpl": temp_video_path,
        "quiet": False,
        "merge_output_format": "mp4",
        "ffmpeg_location": SCRIPT_DIR,
        "remote_components": ["ejs:github"],
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": [
                "player_client=tvhtml5,android",
                "player_js_variant=tv"
            ]
        }
    }

    if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
        ydl_opts["cookiefile"] = cookies_path

    print(f"\n📥 Скачивание видео в качестве {selected_height}p...")
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"❌ Ошибка во время скачивания потоков: {e}")
        return

    # Формируем красивые финальные имена по вашей маске
    video_only_path = os.path.join(output_dir, f"{video_title} [{selected_height}p].mp4")
    audio_only_path = os.path.join(output_dir, f"{video_title} [Audio].mp3")

    print("\n✂️ Разделение медиафайла на видео и аудиодорожку...")
    try:
        # Извлекаем видео без звука
        ffmpeg.input(temp_video_path).output(video_only_path, vcodec="copy", an=None).run(overwrite_output=True, quiet=True)
        print(f"🎬 Видео без звука успешно сохранено: {video_only_path}")

        # Срезаем аудиодорожку в MP3
        ffmpeg.input(temp_video_path).output(audio_only_path, acodec="libmp3lame", q=2).run(overwrite_output=True, quiet=True)
        print(f"🎵 Итоговая аудиодорожка сохранена: {audio_only_path}")
    except ffmpeg.Error as e:
        print("❌ Ошибка обработки FFmpeg:", e.stderr.decode() if (e.stderr and hasattr(e.stderr, 'decode')) else e)
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            print("🧹 Очистка временных файлов завершена.")


if __name__ == "__main__":
    video_url = input("Введите ссылку на видео: ")
    download_and_split(video_url)
