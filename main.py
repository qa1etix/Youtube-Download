import os
import sys
import ffmpeg
from yt_dlp import YoutubeDL

# Полный путь к файлу куков (должен лежать рядом со скриптом)
COOKIES_FILE = "cookies.txt"

# 🔥 Магия путей: определяем точную папку, где лежит ЭТОТ запущенный скрипт
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()

# Добавляем папку скрипта в PATH, чтобы библиотека ffmpeg-python нашла ffmpeg.exe и ffprobe.exe
if SCRIPT_DIR not in os.environ["PATH"]:
    os.environ["PATH"] = SCRIPT_DIR + os.pathsep + os.environ["PATH"]

# Путь к кукам внутри папки скрипта
cookies_path = os.path.join(SCRIPT_DIR, COOKIES_FILE)


def get_available_formats(url):
    """Безопасно получает список доступных разрешений видео."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": SCRIPT_DIR,  # 👈 Принудительно заставляем искать ffmpeg.exe в папке скрипта
        "extractor_args": {
            "youtube": ["player_js_variant=tv", "formats=missing_pot"]
        }
    }

    if os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = cookies_path
        print(f"🍪 Используются локальные куки: {cookies_path}")
    else:
        print(f"⚠️ Файл {COOKIES_FILE} не найден в {SCRIPT_DIR}. Работа без куков...")

    print("🔍 Получение списка доступных разрешений...")
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"❌ Ошибка yt-dlp при анализе: {e}")
            return None, None

        formats = info.get("formats", [])
        unique_resolutions = {}
        for f in formats:
            height = f.get("height")
            if height:
                format_note = f.get("format_note") or f.get("resolution") or f"{height}p"
                unique_resolutions[height] = format_note
                
        if not unique_resolutions:
            return None, None

        return sorted(unique_resolutions.keys(), reverse=True), unique_resolutions


def download_and_split(url):
    """Скачивает видео в выбранном качестве и разделяет его."""
    resolutions, res_dict = get_available_formats(url)
    if not resolutions:
        print("❌ Не удалось разобрать форматы видео.")
        return

    print("\nДоступные варианты качества:")
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

    # Создаем папку output внутри папки скрипта
    output_dir = os.path.join(SCRIPT_DIR, "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    temp_video_path = os.path.join(output_dir, "temp_full_video.mp4")

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "format_sort": [f"res:{selected_height}", "vcodec:h264", "acodec:aac"],
        "outtmpl": temp_video_path,
        "quiet": False,
        "merge_output_format": "mp4",
        "ffmpeg_location": SCRIPT_DIR,  # 👈 Снова жестко указываем путь к ffmpeg.exe для загрузки
        "extractor_args": {
            "youtube": ["player_js_variant=tv", "formats=missing_pot"]
        }
    }

    if os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = cookies_path

    print(f"\n📥 Скачивание видео (целевое разрешение: {selected_height}p)...")
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"❌ Ошибка при скачивании: {e}")
        return

    video_only_path = os.path.join(output_dir, f"video_{selected_height}p.mp4")
    audio_only_path = os.path.join(output_dir, "audio_only.mp3")

    print("\n✂️ Разделение на видео и аудио...")
    try:
        # Извлекаем только видео (без звука) без перекодирования
        ffmpeg.input(temp_video_path).output(video_only_path, vcodec="copy", an=None).run(overwrite_output=True, quiet=True)
        print(f"🎬 Видео без звука сохранено: {video_only_path}")

        # Извлекаем только аудио и конвертируем в mp3
        ffmpeg.input(temp_video_path).output(audio_only_path, acodec="libmp3lame", q=2).run(overwrite_output=True, quiet=True)
        print(f"🎵 Аудиодорожка сохранена: {audio_only_path}")
    except ffmpeg.Error as e:
        print("❌ Ошибка при обработке FFmpeg:", e.stderr.decode() if (e.stderr and hasattr(e.stderr, 'decode')) else e)
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
            print("🧹 Временные файлы очищены.")


if __name__ == "__main__":
    print(f"🤖 Скрипт запущен. Ищу ffmpeg.exe в папке: {SCRIPT_DIR}")
    
    # Быстрая проверка наличия файла перед стартом
    if not os.path.exists(os.path.join(SCRIPT_DIR, "ffmpeg.exe")):
        print(f"⛔ Внимание! Файл ffmpeg.exe НЕ НАЙДЕН в папке {SCRIPT_DIR}.")
        print("Убедитесь, что перекинули ffmpeg.exe именно туда, где лежит этот .py файл!")
    
    video_url = input("\nВведите ссылку на видео: ")
    download_and_split(video_url)
