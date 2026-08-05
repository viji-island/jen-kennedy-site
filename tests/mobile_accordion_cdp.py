#!/usr/bin/env python3
"""Deterministic CDP regression for the mobile accordion scroll-feedback bug.

Runs Chromium at 390x844 with touch emulation, taps several accordion rows while
another row is open, and records scrollY plus the tapped row's viewport top for
760 ms per tap. It loads the normal animated page (with only a cache-busting
query), rather than the ?flat debug mode. It also guards accordion state, desktop
glide, reduced motion, touch scrolling, the six-slide hero, and His & Hers
media/trailer markup.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = Path(os.environ.get("ACCORDION_ARTIFACT_DIR", "/tmp/jen-kennedy-site-artifacts"))
SCREENSHOT = ARTIFACT_DIR / "mobile-accordion-after.png"
# Three CSS pixels allows compositor/layout rounding at DPR 3, while remaining
# much smaller than the 20px mobile row padding and catching a visible jump.
TOP_STABILITY_TOLERANCE_PX = 3


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class CDP:
    def __init__(self, ws_url: str):
        parsed = urllib.parse.urlparse(ws_url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        self.sock.settimeout(15)
        self._buffer = b""
        key = base64.b64encode(os.urandom(16)).decode()
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {parsed.hostname}:{parsed.port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        try:
            self.sock.sendall(request.encode())
            response = self.recv_until(b"\r\n\r\n").decode(errors="replace")
            if " 101 " not in response:
                raise RuntimeError(f"CDP websocket handshake failed: {response}")
        except Exception:
            self.sock.close()
            raise
        self.next_id = 1

    def recv_exact(self, length: int) -> bytes:
        """Return exactly *length* bytes, preserving data read past HTTP headers."""
        while len(self._buffer) < length:
            chunk = self.sock.recv(max(4096, length - len(self._buffer)))
            if not chunk:
                raise RuntimeError("CDP websocket closed while receiving data")
            self._buffer += chunk
        data, self._buffer = self._buffer[:length], self._buffer[length:]
        return data

    def recv_until(self, delimiter: bytes) -> bytes:
        """Read through *delimiter* without assuming a TCP recv returns a full header."""
        while delimiter not in self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("CDP websocket closed while receiving HTTP headers")
            self._buffer += chunk
        end = self._buffer.index(delimiter) + len(delimiter)
        data, self._buffer = self._buffer[:end], self._buffer[end:]
        return data

    def _send_frame(self, opcode: int, payload: bytes):
        mask = os.urandom(4)
        header = bytes([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header += bytes([0x80 | length])
        elif length <= 0xFFFF:
            header += bytes([0x80 | 126]) + struct.pack("!H", length)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", length)
        masked_payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + mask + masked_payload)

    def _recv(self):
        while True:
            first, second = self.recv_exact(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self.recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self.recv_exact(8))[0]
            masked = second & 0x80
            mask = self.recv_exact(4) if masked else b""
            data = self.recv_exact(length)
            if masked:
                data = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
            if opcode == 8:
                raise RuntimeError("CDP websocket closed")
            if opcode == 9:
                self._send_frame(0xA, data)
                continue
            if opcode == 10:
                continue
            if opcode != 1:
                raise RuntimeError(f"unexpected CDP websocket opcode: {opcode}")
            return json.loads(data.decode())

    def call(self, method: str, params: dict | None = None):
        message_id = self.next_id
        self.next_id += 1
        payload = json.dumps({"id": message_id, "method": method, "params": params or {}}).encode()
        self._send_frame(1, payload)
        while True:
            response = self._recv()
            if response.get("id") == message_id:
                if "error" in response:
                    raise RuntimeError(f"CDP {method} failed: {response['error']}")
                return response.get("result", {})

    def eval(self, expression: str):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        value = result["result"]
        if "exceptionDetails" in result:
            raise RuntimeError(f"page eval failed: {result['exceptionDetails']}")
        return value.get("value")

    def close(self):
        self.sock.close()


def wait_for_debugger(profile_path: str, chrome: subprocess.Popen):
    deadline = time.time() + 15
    active_port_file = Path(profile_path) / "DevToolsActivePort"
    while time.time() < deadline:
        try:
            lines = active_port_file.read_text().splitlines()
            debug_port = int(lines[0])
            url = f"http://127.0.0.1:{debug_port}/json/list"
            with urlopen(url, timeout=1) as response:
                pages = json.load(response)
            page = next((item for item in pages if item.get("type") == "page"), None)
            if page:
                return page["webSocketDebuggerUrl"]
        except Exception:
            if chrome.poll() is not None:
                raise RuntimeError(f"Chromium exited before remote debugging started (exit {chrome.returncode})")
            time.sleep(0.1)
    raise RuntimeError("Chromium remote debugging endpoint did not start")


def js(value):
    return json.dumps(value, ensure_ascii=False)


def wait_for_page(cdp: CDP):
    deadline = time.time() + 10
    while time.time() < deadline:
        if cdp.eval("Boolean(document.getElementById('h-total'))"):
            return
        time.sleep(0.05)
    raise RuntimeError(f"index.html did not load; page URL was {cdp.eval('location.href')}")


def click_row(cdp: CDP, element_id: str):
    # This invokes the button's production click listener after touch emulation has
    # selected coarse-pointer CSS. Positioning a row can be clamped while a large
    # preceding panel is still loading, so coordinate taps are not deterministic.
    cdp.eval("document.querySelector(" + js("#" + element_id + " .row") + ").click()")


def mouse_click(cdp: CDP, element_id: str):
    box = cdp.eval(
        "(() => { const r = document.querySelector(" + js("#" + element_id + " .row") + ").getBoundingClientRect();"
        "return {x:r.left + r.width / 2, y:r.top + r.height / 2}; })()"
    )
    cdp.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": box["x"], "y": box["y"], "button": "left", "clickCount": 1})
    cdp.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": box["x"], "y": box["y"], "button": "left", "clickCount": 1})


def position_row(cdp: CDP, element_id: str, top: int = 300):
    cdp.eval(
        "(() => { const el = document.getElementById(" + js(element_id) + "), html = document.documentElement, previous = html.style.scrollBehavior;"
        f"html.style.scrollBehavior = 'auto'; window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - {top}); html.style.scrollBehavior = previous; }})()"
    )
    time.sleep(0.08)


def begin_trace(cdp: CDP, element_id: str, duration_ms: int = 760):
    cdp.eval(
        "window.__accordionTrace = []; window.__accordionScrollBy = []; window.__accordionProgrammaticScroll = []; "
        "window.__accordionTracePromise = new Promise(resolve => {"
        "const wrap = document.getElementById(" + js(element_id) + ");"
        "window.__accordionTraceBefore = {scrollY:Math.round(scrollY*100)/100,top:Math.round(wrap.getBoundingClientRect().top*100)/100};"
        "const started = performance.now();"
        "const frame = now => { window.__accordionTrace.push({t:Math.round(now-started),scrollY:Math.round(scrollY*100)/100,top:Math.round(wrap.getBoundingClientRect().top*100)/100});"
        f"if (now-started < {duration_ms}) requestAnimationFrame(frame); else resolve(window.__accordionTrace); }}; requestAnimationFrame(frame); }});"
    )


def finish_trace(cdp: CDP):
    cdp.eval("window.__accordionTracePromise")
    return cdp.eval("({trace:window.__accordionTrace,before:window.__accordionTraceBefore,scrollByCalls:window.__accordionScrollBy,programmaticCalls:window.__accordionProgrammaticScroll,scrollBehaviorAfter:{computed:getComputedStyle(document.documentElement).scrollBehavior,inline:document.documentElement.style.scrollBehavior}})")


def open_and_trace(cdp: CDP, element_id: str):
    position_row(cdp, element_id)
    begin_trace(cdp, element_id)
    click_row(cdp, element_id)
    return finish_trace(cdp)


def trace_summary(trace_result: dict):
    trace = trace_result["trace"]
    tops = [sample["top"] for sample in trace]
    scrolls = [sample["scrollY"] for sample in trace]
    before = trace_result["before"]
    return {
        "frames": len(trace),
        "durationMs": trace[-1]["t"] if trace else 0,
        "scrollByCalls": len(trace_result["scrollByCalls"]),
        "programmaticScrollCalls": len(trace_result["programmaticCalls"]),
        "correctionBehaviors": [call["behavior"] for call in trace_result["scrollByCalls"]],
        "correctionInlineBehaviors": [call["inlineBehavior"] for call in trace_result["scrollByCalls"]],
        "scrollBehaviorAfter": trace_result["scrollBehaviorAfter"],
        "scrollYBeforeClick": before["scrollY"],
        "scrollYStart": scrolls[0] if scrolls else None,
        "scrollYEnd": scrolls[-1] if scrolls else None,
        "scrollYRange": round(max(scrolls) - min(scrolls), 2) if scrolls else 0,
        "targetTopBeforeClick": before["top"],
        "targetTopStart": tops[0] if tops else None,
        "targetTopEnd": tops[-1] if tops else None,
        "targetTopRange": round(max(tops) - min(tops), 2) if tops else 0,
        "targetTopMaxDeviation": round(max(abs(top - before["top"]) for top in tops), 2) if tops else 0,
    }


def duration_seconds(value: str):
    """Normalize Chromium's computed transition-duration serialization."""
    first = value.split(",", 1)[0].strip()
    if first.endswith("ms"):
        return float(first[:-2]) / 1000
    if first.endswith("s"):
        return float(first[:-1])
    raise ValueError(f"unexpected transition duration: {value!r}")


def remove_profile(profile_path: Path, attempts: int = 6):
    """Remove Chromium's profile after its remaining writers have exited."""
    for attempt in range(attempts):
        try:
            shutil.rmtree(profile_path)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 * (2 ** attempt))


def main():
    server = None
    profile_path = None
    chrome = None
    cdp = None
    report = {"screenshot": str(SCREENSHOT)}
    try:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: QuietHandler(*args, directory=str(ROOT), **kwargs))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_port
        # Snap Chromium can only create DevToolsActivePort under the user's home directory.
        profile_path = Path(tempfile.mkdtemp(prefix="jen-accordion-cdp-", dir=Path.home()))
        chrome = subprocess.Popen(
            ["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--remote-allow-origins=*",
             "--remote-debugging-port=0", f"--user-data-dir={profile_path}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cdp = CDP(wait_for_debugger(str(profile_path), chrome))
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 3, "mobile": True})
        cdp.call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
        cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": """
          (() => {
            const originalScrollBy = window.scrollBy.bind(window);
            const originalScrollTo = window.scrollTo.bind(window);
            const originalScrollIntoView = Element.prototype.scrollIntoView;
            window.__accordionScrollBy = [];
            window.__accordionProgrammaticScroll = [];
            window.scrollBy = (...args) => {
              const target = window.__accordionTraceTarget;
              const html = document.documentElement;
              const call = {kind:'scrollBy', t:performance.now(), args, behavior:getComputedStyle(html).scrollBehavior, inlineBehavior:html.style.scrollBehavior, before:{scrollY, top:target ? target.getBoundingClientRect().top : null}};
              window.__accordionScrollBy.push(call); window.__accordionProgrammaticScroll.push(call);
              const result = originalScrollBy(...args);
              call.after = {scrollY, top:target ? target.getBoundingClientRect().top : null};
              return result;
            };
            window.scrollTo = (...args) => { window.__accordionProgrammaticScroll.push({kind:'scrollTo', t: performance.now(), args}); return originalScrollTo(...args); };
            Element.prototype.scrollIntoView = function(...args) { window.__accordionProgrammaticScroll.push({kind:'scrollIntoView', t: performance.now(), args}); return originalScrollIntoView.apply(this, args); };
          })();
        """})
        cdp.call("Page.navigate", {"url": f"http://127.0.0.1:{port}/index.html?accordion-cdp=mobile-{time.time_ns()}"})
        wait_for_page(cdp)
        cdp.eval("document.fonts.ready")
        report["mobileCoarsePointer"] = cdp.eval("matchMedia('(pointer:coarse)').matches && matchMedia('(hover:none)').matches")
        report["hero"] = cdp.eval("({slides:document.querySelectorAll('.hero .hslide').length,total:document.getElementById('h-total').textContent})")
        report["hisAndHers"] = cdp.eval("(() => { const w=document.getElementById('his-and-hers'); return {figures:w.querySelectorAll('.his-hers-media figure').length,trailer:w.querySelector('.trailer-link').dataset.yt}; })()")

        # Exercise the three rows that exhibited delayed correction in the iPhone recording.
        report["mobileTraces"] = {}
        for row_id in ("i-dont-understand-you", "lessons-in-chemistry", "the-girl-from-plainville"):
            report["mobileTraces"][row_id] = trace_summary(open_and_trace(cdp, row_id))
        report["accordionState"] = cdp.eval("(() => { const wraps=[...document.querySelectorAll('.row-wrap')]; return {open:wraps.filter(w=>w.classList.contains('open')).map(w=>w.id),aria:wraps.map(w=>[w.id,w.querySelector('.row').getAttribute('aria-expanded')]),inert:wraps.map(w=>[w.id,w.querySelector('.exp').hasAttribute('inert')]),hash:location.hash}; })()")

        # Capture the open mobile row before the touch-drag probe moves the viewport near the footer.
        screenshot = cdp.call("Page.captureScreenshot", {"format": "png"})["data"]
        SCREENSHOT.write_bytes(base64.b64decode(screenshot))

        # Real touch drag must scroll; the accordion's passive touchstart may observe it but cannot block it.
        cdp.eval("window.scrollTo(0, document.body.scrollHeight - innerHeight - 300)")
        before_drag = cdp.eval("scrollY")
        touch = {"x": 350, "y": 700, "radiusX": 1, "radiusY": 1, "force": 1, "id": 1}
        cdp.call("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [touch]})
        for y in (620, 520, 420):
            touch["y"] = y
            cdp.call("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [touch]})
        cdp.call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        time.sleep(0.2)
        report["touchDragDelta"] = round(cdp.eval("scrollY") - before_drag, 2)

        # Desktop remains intentionally gliding.
        cdp.call("Emulation.setTouchEmulationEnabled", {"enabled": False})
        cdp.call("Emulation.clearDeviceMetricsOverride")
        cdp.call("Page.navigate", {"url": f"http://127.0.0.1:{port}/index.html?accordion-cdp=desktop-{time.time_ns()}"})
        wait_for_page(cdp)
        position_row(cdp, "the-god-of-the-woods")
        cdp.eval("window.__accordionScrollBy = []; window.__accordionTraceTarget = document.getElementById('the-god-of-the-woods')")
        mouse_click(cdp, "the-god-of-the-woods")
        time.sleep(0.78)
        report["desktop"] = cdp.eval("""(() => {
          const calls = window.__accordionScrollBy;
          const scrolls = calls.flatMap(c => [c.before.scrollY, c.after.scrollY]);
          const tops = calls.flatMap(c => [c.before.top, c.after.top]).filter(Number.isFinite);
          return {
            coarsePointer:matchMedia('(pointer:coarse)').matches,
            transition:getComputedStyle(document.querySelector('#the-god-of-the-woods .exp')).transitionDuration,
            scrollByCalls:calls.length,
            scrollYRange:Math.max(...scrolls) - Math.min(...scrolls),
            targetTopRange:Math.max(...tops) - Math.min(...tops),
          };
        })()""")

        # Reduced motion removes transitions and should not re-enable mobile scrolling.
        cdp.call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 3, "mobile": True})
        cdp.call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 1})
        cdp.call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
        cdp.call("Page.navigate", {"url": f"http://127.0.0.1:{port}/index.html?accordion-cdp=reduced-{time.time_ns()}"})
        wait_for_page(cdp)
        position_row(cdp, "the-god-of-the-woods")
        cdp.eval("window.__accordionScrollBy = []")
        click_row(cdp, "the-god-of-the-woods")
        time.sleep(0.15)
        report["reducedMotion"] = cdp.eval("(() => { const w=document.getElementById('the-god-of-the-woods'); return {matches:matchMedia('(prefers-reduced-motion: reduce)').matches,transition:getComputedStyle(w.querySelector('.exp')).transitionDuration,scrollByCalls:window.__accordionScrollBy.length,aria:w.querySelector('.row').getAttribute('aria-expanded')}; })()")

        print(json.dumps(report, indent=2, sort_keys=True))
        assert report["mobileCoarsePointer"], "390x844 harness did not activate coarse-pointer touch media"
        assert report["hero"] == {"slides": 6, "total": "06"}, "six-slide hero regression"
        assert report["hisAndHers"] == {"figures": 3, "trailer": "8_szlvBLll0"}, "His & Hers media/trailer regression"
        assert all(trace["durationMs"] >= 700 for trace in report["mobileTraces"].values()), "mobile trace shorter than 700ms"
        assert all(trace["programmaticScrollCalls"] <= 1 for trace in report["mobileTraces"].values()), "mobile tap started multi-frame programmatic scroll feedback"
        assert all(all(behavior != "smooth" for behavior in trace["correctionBehaviors"]) for trace in report["mobileTraces"].values()), "coarse accordion correction ran under global smooth scrolling"
        assert all(trace["scrollBehaviorAfter"] == {"computed": "smooth", "inline": ""} for trace in report["mobileTraces"].values()), "coarse correction did not restore the global smooth-scroll style"
        assert all(trace["scrollYRange"] == 0 for trace in report["mobileTraces"].values()), "mobile correction continued scrolling after its single synchronous call"
        assert all(trace["targetTopMaxDeviation"] <= TOP_STABILITY_TOLERANCE_PX for trace in report["mobileTraces"].values()), f"mobile tapped-row top moved by more than {TOP_STABILITY_TOLERANCE_PX}px after its synchronous correction"
        state = report["accordionState"]
        assert state["open"] == ["the-girl-from-plainville"] and state["hash"] == "#the-girl-from-plainville", "one-open-row/hash regression"
        assert all((expanded == "true") == (row_id == "the-girl-from-plainville") for row_id, expanded in state["aria"]), "aria-expanded regression"
        assert all((not inert) == (row_id == "the-girl-from-plainville") for row_id, inert in state["inert"]), "inert regression"
        assert report["touchDragDelta"] > 50, "vertical touch gesture did not scroll"
        desktop = report["desktop"]
        assert not desktop["coarsePointer"], "desktop harness unexpectedly activated coarse-pointer media"
        assert abs(duration_seconds(desktop["transition"]) - 0.56) < 0.001, "desktop accordion transition duration regression"
        assert desktop["scrollByCalls"] >= 5, "desktop glide did not issue enough scrollBy calls"
        assert desktop["scrollYRange"] > 3 and desktop["targetTopRange"] > 3, "desktop glide did not produce measurable row/scroll motion"
        assert report["reducedMotion"] == {"matches": True, "transition": "0s", "scrollByCalls": 0, "aria": "true"}, "reduced-motion regression"
    finally:
        if cdp:
            try:
                cdp.call("Browser.close")
            except (OSError, RuntimeError, socket.timeout):
                pass
            try:
                cdp.close()
            except OSError:
                pass
        if chrome:
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.terminate()
                try:
                    chrome.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    chrome.kill()
                    chrome.wait()
        if server:
            server.shutdown()
            server.server_close()
        if profile_path:
            remove_profile(profile_path)


if __name__ == "__main__":
    main()
