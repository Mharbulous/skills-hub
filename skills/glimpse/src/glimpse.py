"""Glimpse - on-demand window screenshot CLI for Claude Code."""

import sys
import os
import json
import re
import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import win32gui
    import win32ui
    import win32con
    import win32process
    import ctypes
    from ctypes import wintypes
    from PIL import Image
except ImportError:
    print("Missing dependencies. Run: pip install pywin32 Pillow", file=sys.stderr)
    sys.exit(2)

VERSION = "0.2.0"
GLIMPSE_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Glimpse"
SCREENSHOT_DIR = GLIMPSE_DIR / "screenshots"
STATUS_FILE = GLIMPSE_DIR / "status.json"
MAX_SCREENSHOTS = 50
NOISE_PROCESSES = {"TextInputHost.exe", "ApplicationFrameHost.exe", "explorer.exe", "Microsoft.CmdPal.UI.exe"}


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]


def enumerate_windows():
    results = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.psapi.GetModuleFileNameExW(handle, None, buf, 260)
            ctypes.windll.kernel32.CloseHandle(handle)
            process = os.path.basename(buf.value)
        except Exception:
            process = "unknown"
        results.append({"handle": hwnd, "title": title, "process": process})
        return True

    win32gui.EnumWindows(callback, None)
    return results


def capture_window(hwnd, output_path):
    # DWM extended frame bounds exclude invisible resize borders; fall back if unavailable.
    try:
        rect = wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)

    # PW_RENDERFULLCONTENT (=2) for hardware-accelerated content; BitBlt fallback if PrintWindow fails.
    if not ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2):
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

    info = bitmap.GetInfo()
    img = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bitmap.GetBitmapBits(True), "raw", "BGRX", 0, 1)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")

    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)
    win32gui.DeleteObject(bitmap.GetHandle())


def cleanup_screenshots():
    if not SCREENSHOT_DIR.exists():
        return 0
    files = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda f: f.stat().st_mtime)
    excess = files[:-MAX_SCREENSHOTS] if len(files) > MAX_SCREENSHOTS else []
    for f in excess:
        f.unlink()
    return len(excess)


def read_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text())
    return {"screenshot_dir": str(SCREENSHOT_DIR), "screenshot_count": 0, "last_capture": None, "version": VERSION}


def write_status(last_capture=None):
    count = len(list(SCREENSHOT_DIR.glob("*.png"))) if SCREENSHOT_DIR.exists() else 0
    status = {
        "screenshot_dir": str(SCREENSHOT_DIR),
        "screenshot_count": count,
        "last_capture": last_capture or read_status().get("last_capture"),
        "version": VERSION,
    }
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def cmd_windows(args):
    visible = [{"title": w["title"], "process": w["process"]}
               for w in enumerate_windows() if w["process"] not in NOISE_PROCESSES]
    print(json.dumps(visible))


CHROMIUM_BROWSERS = [
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
]


def is_url(text):
    return text.startswith("http://") or text.startswith("https://") or text.startswith("localhost")


def find_browser():
    for path in CHROMIUM_BROWSERS:
        if os.path.exists(path):
            return path
    return None


def find_window_by_pid(pid, timeout=6):
    """Poll EnumWindows until a visible window owned by pid appears, or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for w in enumerate_windows():
            _, wpid = win32process.GetWindowThreadProcessId(w["handle"])
            if wpid == pid and win32gui.IsWindowVisible(w["handle"]) and win32gui.GetWindowText(w["handle"]):
                return w
        time.sleep(0.3)
    return None


def cmd_capture_url(url, args):
    # Fast path: reuse an existing --app window whose title contains a URL fragment.
    # Chrome/Edge --app windows show the page title (not the URL), so we match on
    # the hostname extracted from the URL as a heuristic.
    hostname = re.sub(r"https?://", "", url).split("/")[0].split(":")[0]
    windows = enumerate_windows()
    browser_processes = {"msedge.exe", "chrome.exe", "brave.exe"}
    match = next(
        (w for w in windows
         if w["process"].lower() in browser_processes and hostname in w["title"].lower()),
        None,
    )

    if not match:
        # Slow path: launch a new --app window and find it by PID.
        browser = find_browser()
        if not browser:
            print("No Chromium-based browser found. Install Edge or Chrome.", file=sys.stderr)
            sys.exit(1)
        proc = subprocess.Popen([browser, f"--app={url}"])
        match = find_window_by_pid(proc.pid)
        if not match:
            print(f"Launched browser (PID {proc.pid}) but no window appeared within 6s.", file=sys.stderr)
            sys.exit(1)

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slugify(match['title'] or hostname)}.png"
    output_path = SCREENSHOT_DIR / filename
    capture_window(match["handle"], output_path)
    return output_path, match["title"]


def cmd_capture(args):
    if not args.title:
        print("Usage: glimpse capture <title|url>", file=sys.stderr)
        sys.exit(1)
    query = " ".join(args.title)

    if is_url(query):
        output_path, title = cmd_capture_url(query, args)
    else:
        query_lower = query.lower()
        windows = enumerate_windows()
        match = next((w for w in windows if query_lower in w["title"].lower()), None)
        if not match:
            available = [w["title"] for w in windows if w["process"] not in NOISE_PROCESSES]
            print(f'No window matching "{query}". Available: {", ".join(available)}', file=sys.stderr)
            sys.exit(1)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{slugify(match['title'])}.png"
        output_path = SCREENSHOT_DIR / filename
        capture_window(match["handle"], output_path)

    if args.downscale:
        img = Image.open(str(output_path))
        if img.width > args.downscale:
            ratio = args.downscale / img.width
            img.resize((args.downscale, int(img.height * ratio)), Image.LANCZOS).save(str(output_path), "PNG")

    print(f"Captured: {output_path}")
    cleanup_screenshots()
    write_status(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


def cmd_status(args):
    s = read_status()
    print(f"Screenshot dir: {s['screenshot_dir']}")
    print(f"Screenshots:    {s['screenshot_count']}")
    print(f"Last capture:   {s['last_capture'] or 'never'}")
    print(f"Version:        {s['version']}")


def cmd_clean(args):
    deleted = cleanup_screenshots()
    write_status()
    if deleted:
        print(f"Deleted {deleted} old screenshot(s).")
    else:
        print(f"Nothing to clean (at or below {MAX_SCREENSHOTS} screenshots).")


def main():
    parser = argparse.ArgumentParser(prog="glimpse", description="On-demand window screenshot CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("windows", help="List visible windows as JSON").set_defaults(func=cmd_windows)

    cap = sub.add_parser("capture", help="Capture a window screenshot")
    cap.add_argument("title", nargs="*", help="Window title substring to match")
    cap.add_argument("--downscale", type=int, metavar="MAX_WIDTH", help="Resize image so width does not exceed MAX_WIDTH")
    cap.set_defaults(func=cmd_capture)

    sub.add_parser("status", help="Show screenshot count, folder path, last capture").set_defaults(func=cmd_status)
    sub.add_parser("clean", help="Delete oldest screenshots beyond limit").set_defaults(func=cmd_clean)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
