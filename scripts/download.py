import sys
import os
import re
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime

async def resolve_short_url(url):
    if "pin.it" in url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    return str(r.url)
        except:
            pass
    return url

async def get_media_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status != 200:
                    return None, False
                html = await r.text()

                pws = re.search(r'<script[^>]*id="__PWS_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
                if pws:
                    data = json.loads(pws.group(1))
                    pins = data.get("props", {}).get("initialReduxState", {}).get("pins", {})

                    for pid, pin in pins.items():
                        story = pin.get("story_pin_data")
                        if story:
                            for page in story.get("pages", []):
                                for block in page.get("blocks", []):
                                    video = block.get("video")
                                    if video:
                                        vlist = video.get("video_list", {})
                                        for q in ["V_720P", "V_EXP7", "V_480P", "V_360P"]:
                                            if q in vlist:
                                                vurl = vlist[q].get("url", "")
                                                if vurl and ".mp4" in vurl:
                                                    return vurl, True

                        videos = pin.get("videos")
                        if videos:
                            vlist = videos.get("video_list", {})
                            for q in ["V_720P", "V_EXP7", "V_480P", "V_360P"]:
                                if q in vlist:
                                    vurl = vlist[q].get("url", "")
                                    if vurl and ".mp4" in vurl:
                                        return vurl, True

                        images = pin.get("images", {})
                        for k in ["orig", "736x", "474x"]:
                            if k in images and images[k].get("url"):
                                return images[k]["url"], False

                vm = re.search(r'"url"\s*:\s*"(https://v[^"]*\.pinimg\.com/videos/[^"]+\.mp4[^"]*)"', html)
                if vm:
                    return vm.group(1).replace("\\u002F", "/"), True

                im = re.search(r'"url"\s*:\s*"(https://i\.pinimg\.com/originals/[^"]+)"', html)
                if im:
                    return im.group(1).replace("\\u002F", "/"), False

    except Exception as e:
        print(f"❌ خطا: {e}", flush=True)
    return None, False

async def download_file(url, is_video, output_dir):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.pinterest.com/"}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as r:
                if r.status == 200:
                    content = await r.read()
                    ext = ".mp4" if is_video else ".jpg"
                    fname = f"media{ext}"
                    fpath = Path(output_dir) / fname
                    fpath.write_bytes(content)
                    return str(fpath)
    except Exception as e:
        print(f"❌ خطای دانلود: {e}", flush=True)
    return None

def update_main_readme(base_dir, url, resolved, media_url, is_video, file_path, success, folder_name):
    readme_path = base_dir / "README.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    persian_msg = """
> ⚠️ اگر نتوانستید بصورت مستقیم از گیتهاب دانلود کنید بخاطر محدودیت های اینترنت است برای حل این موضوع شما میتوانید کل ریپازیتوری را از صفحه ی اصلی فورک بصورت زیپ دانلود کنید در این صورت مشکل حل شده و فایل ها درون فایل زیپ خواهد بود 📦

"""

    # Read existing content or create header
    if readme_path.exists():
        content = readme_path.read_text()
    else:
        content = f"# 📌 دانلودهای پینترست\n\n{persian_msg}| 📅 تاریخ | 🔗 منبع | 📁 پوشه | 📂 نوع | ✅ وضعیت |\n|------|--------|--------|------|--------|\n"

    # Add new entry
    media_type = "🎬 ویدیو" if is_video else "🖼️ تصویر"
    status = "✅ موفق" if success else "❌ ناموفق"
    folder_link = f"[{folder_name}](./{folder_name}/)"
    new_line = f"| {timestamp} | [{url}]({url}) | {folder_link} | {media_type} | {status} |\n"
    content += new_line

    readme_path.write_text(content)

async def main(url):
    base_dir = Path("downloads")
    base_dir.mkdir(exist_ok=True)

    folder_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / folder_name
    output_dir.mkdir(exist_ok=True)

    resolved = await resolve_short_url(url)

    media_url, is_video = await get_media_url(resolved)
    file_path = None
    if media_url:
        file_path = await download_file(media_url, is_video, str(output_dir))

    success = file_path is not None

    # Update main README
    update_main_readme(base_dir, url, resolved, media_url, is_video, file_path, success, folder_name)

    # Print Summary
    print("", flush=True)
    print("=" * 50, flush=True)
    print("📊 خلاصه دانلود", flush=True)
    print("=" * 50, flush=True)
    print(f"🔗 لینک ورودی: {url}", flush=True)
    if resolved != url:
        print(f"🔄 لینک نهایی: {resolved}", flush=True)
    if success:
        print(f"✅ وضعیت: موفق", flush=True)
        print(f"📂 نوع: {'🎬 ویدیو' if is_video else '🖼️ تصویر'}", flush=True)
        print(f"📁 ذخیره شد در: {file_path}", flush=True)
        print(f"🌐 لینک مدیا: {media_url}", flush=True)
    else:
        print(f"❌ وضعیت: ناموفق - مدیایی یافت نشد", flush=True)
    print("=" * 50, flush=True)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if url:
        asyncio.run(main(url))
    else:
        print("📌 استفاده: python download.py <لینک_پینترست>", flush=True)
