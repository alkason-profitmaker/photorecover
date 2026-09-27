"""
Local Web-Based Recovery Workstation and Preview Server
Serves the modern responsive UI, manages asynchronous scans, and provides thumbnail APIs.
"""

import os
import sys
import json
import shutil
import string
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, List

from .recovery import SDCardRecovery, RecoveredItem
from .enhancer import ImageEnhancer
from .upscaler import AIUpscaler


class ScanSessionManager:
    """Manages background recovery scans and in-memory caches."""

    def __init__(self):
        self.lock = threading.Lock()
        self.active_recovery: Optional[SDCardRecovery] = None
        self.scan_thread: Optional[threading.Thread] = None

        self.is_scanning = False
        self.is_complete = False
        self.error_msg: Optional[str] = None

        self.progress_data: Dict[str, Any] = {
            "progress": 0.0,
            "bytes_scanned": 0,
            "total_bytes": 0,
            "speed_mb": 0.0,
            "stats": {}
        }
        self.recovered_items: List[RecoveredItem] = []
        self.item_by_hash: Dict[str, RecoveredItem] = {}
        # Permanent safe storage directory (Windows Pictures / PhotoRecover)
        self.base_output_dir = Path.home() / "Pictures" / "PhotoRecover"
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.current_output_dir = self.base_output_dir

    def start_scan(self, config: Dict[str, Any]):
        with self.lock:
            if self.is_scanning:
                return

            self.is_scanning = True
            self.is_complete = False
            self.error_msg = None
            self.recovered_items.clear()
            self.item_by_hash.clear()
            self.progress_data = {"progress": 0.0, "bytes_scanned": 0, "total_bytes": 0, "speed_mb": 0.0, "stats": {}}

            source_path = config.get("source_path", "")
            scan_fs = config.get("scan_filesystem", True)
            attempt_repair = config.get("attempt_repair", True)
            include_raw = config.get("include_raw", True)
            include_video = config.get("include_video", True)
            dedupe = config.get("deduplicate", True)

            custom_dest = config.get("destination", "").strip()
            if custom_dest:
                self.current_output_dir = Path(custom_dest)
            else:
                from datetime import datetime
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.current_output_dir = self.base_output_dir / f"Session_{timestamp_str}"
            self.current_output_dir.mkdir(parents=True, exist_ok=True)

            self.active_recovery = SDCardRecovery(
                validate_images=True,
                deduplicate=dedupe,
                attempt_repair=attempt_repair,
                include_raw=include_raw,
                include_video=include_video,
                verbose=False
            )

        def run_worker():
            try:
                def on_progress(p_info):
                    tot = p_info.get("total_bytes", 0)
                    cur = p_info.get("bytes_scanned", 0)
                    pct = (cur / tot * 100) if tot > 0 else 0
                    with self.lock:
                        self.progress_data = {
                            "progress": pct,
                            "bytes_scanned": cur,
                            "total_bytes": tot,
                            "speed_mb": p_info.get("speed_mb", 0.0),
                            "stats": p_info.get("stats", {})
                        }

                items = self.active_recovery.recover(
                    source_path=source_path,
                    output_dir=str(self.current_output_dir),
                    scan_filesystem=scan_fs,
                    progress_callback=on_progress
                )

                with self.lock:
                    self.recovered_items = items
                    for it in items:
                        self.item_by_hash[it.hash] = it
                    self.is_complete = True
                    self.is_scanning = False
                    self.progress_data["progress"] = 100.0

            except Exception as e:
                with self.lock:
                    self.is_scanning = False
                    self.error_msg = str(e)

        self.scan_thread = threading.Thread(target=run_worker, daemon=True)
        self.scan_thread.start()

    def control_scan(self, action: str):
        with self.lock:
            if not self.active_recovery:
                return
            if action == "pause":
                self.active_recovery.pause()
            elif action == "resume":
                self.active_recovery.resume()
            elif action == "cancel":
                self.active_recovery.cancel()


session_manager = ScanSessionManager()


class WebUIRequestHandler(BaseHTTPRequestHandler):
    """Handles REST API and static HTML requests."""

    def log_message(self, format, *args):
        # Suppress noisy HTTP request console logging
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._serve_index()
        elif path == "/api/drives":
            self._handle_get_drives()
        elif path == "/api/scan/status":
            self._handle_get_status()
        elif path.startswith("/api/thumbnail/"):
            img_hash = path.split("/")[-1]
            self._handle_get_thumbnail(img_hash, parsed.query)
        elif path.startswith("/api/image/"):
            img_hash = path.split("/")[-1]
            self._handle_get_image(img_hash, parsed.query)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length) if length > 0 else b'{}'

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        if path == "/api/scan/start":
            session_manager.start_scan(data)
            self._send_json({"status": "started"})
        elif path == "/api/scan/control":
            action = data.get("action", "")
            session_manager.control_scan(action)
            self._send_json({"status": "acknowledged"})
        elif path == "/api/recover/export":
            self._handle_export(data)
        elif path == "/api/open-folder":
            self._handle_open_folder()
        elif path.startswith("/api/enhance/preview/"):
            img_hash = path.split("/")[-1]
            self._handle_enhance_preview(img_hash)
        elif path.startswith("/api/enhance/save/"):
            img_hash = path.split("/")[-1]
            self._handle_enhance_save(img_hash)
        elif path == "/api/enhance/batch":
            self._handle_enhance_batch(data)
        else:
            self.send_error(404, "Not Found")

    def _serve_index(self):
        index_file = Path(__file__).parent / "web" / "index.html"
        if not index_file.exists():
            self.send_error(404, "Web UI index.html missing")
            return

        content = index_file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_get_drives(self):
        drives = []
        if sys.platform == "win32":
            # Detect Windows logical drives
            for letter in string.ascii_uppercase:
                drive_path = f"{letter}:\\"
                if os.path.exists(drive_path):
                    try:
                        total, used, free = shutil.disk_usage(drive_path)
                        total_gb = round(total / (1024 ** 3), 1)
                        free_gb = round(free / (1024 ** 3), 1)
                        desc = f"{letter}: ({free_gb} GB free / {total_gb} GB)"
                    except Exception:
                        desc = f"{letter}: (Removable Drive)"
                    drives.append({"name": desc, "path": drive_path, "size": f"{total_gb} GB" if 'total_gb' in locals() else ""})
        else:
            # Unix mount points
            for m in ("/media", "/mnt", "/Volumes"):
                p = Path(m)
                if p.exists():
                    for sub in p.iterdir():
                        drives.append({"name": str(sub), "path": str(sub), "size": ""})

        self._send_json({"drives": drives})

    def _handle_get_status(self):
        with session_manager.lock:
            items_payload = [
                {
                    "hash": it.hash,
                    "filename": it.filename,
                    "media_type": it.media_type,
                    "extension": it.extension,
                    "size": it.size,
                    "is_repaired": it.is_repaired,
                    "width": it.width,
                    "height": it.height,
                    "exif_camera": it.exif_camera,
                    "exif_date": it.exif_date
                }
                for it in session_manager.recovered_items
            ]

            resp = {
                "is_scanning": session_manager.is_scanning,
                "is_complete": session_manager.is_complete,
                "error": session_manager.error_msg,
                "progress": session_manager.progress_data.get("progress", 0.0),
                "bytes_scanned": session_manager.progress_data.get("bytes_scanned", 0),
                "total_bytes": session_manager.progress_data.get("total_bytes", 0),
                "speed_mb": session_manager.progress_data.get("speed_mb", 0.0),
                "stats": session_manager.progress_data.get("stats", {}),
                "output_dir": str(session_manager.current_output_dir),
                "items": items_payload
            }
        self._send_json(resp)

    def _handle_get_thumbnail(self, img_hash: str, query: str = ""):
        if "enhanced=true" in query:
            preview_file = session_manager.current_output_dir / "previews" / f"{img_hash}_enhanced.jpg"
            if preview_file.exists():
                data = preview_file.read_bytes()
                self._send_image_bytes(data, "image/jpeg")
                return

        item = session_manager.item_by_hash.get(img_hash)
        if not item:
            self.send_error(404, "Thumbnail not found")
            return

        if item.thumbnail_bytes:
            data = item.thumbnail_bytes
            content_type = "image/jpeg"
        elif Path(item.path).exists():
            data = Path(item.path).read_bytes()
            content_type = "image/jpeg" if item.extension in ('jpg', 'jpeg') else f"image/{item.extension}"
        else:
            self.send_error(404, "Image missing")
            return

        self._send_image_bytes(data, content_type)

    def _handle_get_image(self, img_hash: str, query: str = ""):
        """Serves full resolution photo (original or studio-enhanced)."""
        if "enhanced=true" in query:
            preview_file = session_manager.current_output_dir / "previews" / f"{img_hash}_enhanced.jpg"
            if preview_file.exists():
                data = preview_file.read_bytes()
                self._send_image_bytes(data, "image/jpeg")
                return

        item = session_manager.item_by_hash.get(img_hash)
        if not item or not Path(item.path).exists():
            self.send_error(404, "Photo not found")
            return

        data = Path(item.path).read_bytes()
        content_type = "image/jpeg" if item.extension in ('jpg', 'jpeg') else f"image/{item.extension}"
        self._send_image_bytes(data, content_type)

    def _send_image_bytes(self, data: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _handle_export(self, data: Dict[str, Any]):
        hashes = data.get("hashes", [])
        destination = Path(data.get("destination", "C:\\Recovered_Photos"))
        destination.mkdir(parents=True, exist_ok=True)

        copied = 0
        with session_manager.lock:
            for h in hashes:
                item = session_manager.item_by_hash.get(h)
                if item and Path(item.path).exists():
                    dest_file = destination / item.filename
                    shutil.copy2(item.path, dest_file)
                    copied += 1

        self._send_json({"status": "success", "count": copied, "destination": str(destination)})

    def _handle_open_folder(self):
        folder = str(session_manager.current_output_dir)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
            self._send_json({"status": "ok", "path": folder})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)})

    def _handle_enhance_preview(self, img_hash: str):
        item = session_manager.item_by_hash.get(img_hash)
        if not item or not Path(item.path).exists():
            self.send_error(404, "Image not found")
            return

        try:
            enhancer = ImageEnhancer()
            img = enhancer.load_image(item.path)
            # Apply our master world-class studio restoration pipeline!
            enhanced = enhancer.studio_photo_restore(
                img,
                enhance_portrait=True,
                auto_exposure=True,
                denoise=True,
                super_resolve_scale=1.5
            )

            out_dir = session_manager.current_output_dir / "previews"
            out_dir.mkdir(parents=True, exist_ok=True)
            preview_path = out_dir / f"{img_hash}_enhanced.jpg"
            enhancer.save_image(enhanced, preview_path, quality=95)

            t_val = int(time.time() * 1000)
            self._send_json({
                "status": "ok",
                "enhanced_url": f"/api/image/{img_hash}?enhanced=true&t={t_val}"
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)})

    def _handle_enhance_save(self, img_hash: str):
        item = session_manager.item_by_hash.get(img_hash)
        if not item:
            self.send_error(404, "Image not found")
            return

        preview_file = session_manager.current_output_dir / "previews" / f"{img_hash}_enhanced.jpg"
        if not preview_file.exists():
            self._send_json({"status": "error", "message": "Enhanced preview not yet generated"})
            return

        try:
            stem = Path(item.filename).stem
            studio_filename = f"{stem}_studio.jpg"
            studio_path = session_manager.current_output_dir / studio_filename

            # Never overwrite! If exists, append counter
            count = 1
            while studio_path.exists():
                studio_path = session_manager.current_output_dir / f"{stem}_studio_{count}.jpg"
                studio_filename = studio_path.name
                count += 1

            shutil.copy2(preview_file, studio_path)

            # Flush to disk for permanent non-deletion guarantee
            with open(studio_path, "ab") as f:
                f.flush()
                os.fsync(f.fileno())

            self._send_json({
                "status": "ok",
                "filename": studio_filename,
                "path": str(studio_path)
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)})

    def _handle_enhance_batch(self, data: Dict[str, Any]):
        hashes = data.get("hashes", [])
        if not hashes:
            with session_manager.lock:
                hashes = [it.hash for it in session_manager.recovered_items if it.media_type == "photo"]

        def run_batch():
            enhancer = ImageEnhancer()
            for h in hashes:
                it = session_manager.item_by_hash.get(h)
                if not it or not Path(it.path).exists():
                    continue
                try:
                    stem = Path(it.filename).stem
                    out_name = f"{stem}_studio.jpg"
                    dest = session_manager.current_output_dir / out_name
                    if not dest.exists():
                        img = enhancer.load_image(it.path)
                        enhanced = enhancer.studio_photo_restore(img)
                        enhancer.save_image(enhanced, dest, quality=95)
                        with open(dest, "ab") as f:
                            f.flush()
                            os.fsync(f.fileno())
                except Exception:
                    pass

        threading.Thread(target=run_batch, daemon=True).start()
        self._send_json({"status": "ok", "message": f"Studio enhancement started for {len(hashes)} photos."})


def start_server(port: int = 8765, open_browser: bool = True):
    """Starts the PhotoRecover interactive Web GUI workstation."""
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, WebUIRequestHandler)

    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 60)
    print("  PHOTORECOVER 2.0 - WORKSTATION & PREVIEW UI")
    print(f"  Live local web interface: {url}")
    print("=" * 60 + "\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down PhotoRecover Workstation...")
        httpd.server_close()
