#!/usr/bin/env python3
"""Static server for Squall Cove.

Threaded, with HTTP/1.1 keep-alive, so the browser can pull the Three.js bundle and
the model files in parallel instead of tripping over connection resets.

Usage:  python serve.py [port] [--open|--chrome]
Picks the next free port if the requested one is busy.
"""
import http.server
import socketserver
import sys
import os
import webbrowser
import subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))
_args = sys.argv[1:]
OPEN = '--open' in _args
CHROME = '--chrome' in _args
_ports = [a for a in _args if a.isdigit()]
PORT = int(_ports[0]) if _ports else 8771


def open_high_perf_chrome(url):
    """A dedicated Chrome window pinned to the discrete GPU (it needs its own profile to take the flag)."""
    paths = [
        os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
    ]
    chrome = next((p for p in paths if os.path.exists(p)), None)
    if not chrome:
        webbrowser.open(url)
        return
    profile = os.path.join(os.path.expandvars(r'%LocalAppData%'), 'SquallCove', 'chrome-profile')
    try:
        subprocess.Popen([
            chrome, '--app=' + url, '--user-data-dir=' + profile,
            '--force-high-performance-gpu', '--ignore-gpu-blocklist',
            '--disable-features=CalculateNativeWinOcclusion',
            '--window-size=1560,960',
        ])
        print('   Opened a dedicated Chrome window on the high-performance GPU.')
    except Exception as e:
        print('   Could not launch dedicated Chrome (%s), using the default browser.' % e)
        webbrowser.open(url)


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.js': 'text/javascript',
        '.mjs': 'text/javascript',
    }

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('  %s\n' % (fmt % args))


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128


def main():
    port = PORT
    httpd = None
    for _ in range(25):
        try:
            httpd = ThreadingServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            port += 1
    if httpd is None:
        print('Could not find a free port near', PORT)
        return
    url = 'http://localhost:%d/index.html' % port
    print('Squall Cove serving at %s' % url)
    if CHROME:
        open_high_perf_chrome(url)
    elif OPEN:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
