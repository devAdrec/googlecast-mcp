#!/usr/bin/env python3
"""Reverse check: prove the eval harness can actually go red -- in both directions.

A suite that has never failed has proved nothing. This script seeds one known
fault at a time into a *copy* of the product, runs the offline eval against the
copy, and asserts the items that were expected to go red really did.

Both directions, because one alone is not enough:

  faults   -- each carries a list of item ids written BEFORE the run. An item on
              that list that stays green is a FAKE TEST: it never touched the
              behaviour it claims to guard.
  controls -- harmless edits (a comment, a docstring) that must leave the suite
              GREEN. A control that goes red means the suite fires at noise, and
              that is just as broken as one that never fires.

Reverting is structural, not a matter of remembering: every case runs against a
fresh copy under a temp directory, with PYTHONPATH pointed at it, and
PYTHONDONTWRITEBYTECODE set so no stale .pyc can survive a case. The product
tree is opened read-only and is never written to. The final step re-runs the
eval against the untouched product and requires GREEN -- that, not `git status`,
is what proves nothing leaked.

Coverage is reported at the end: any registered item that no fault expects to
turn red is printed as CHUA PHU. A comment claiming coverage is worth nothing.

Run:
    python reverse-check.py            # every case
    python reverse-check.py --only tts # cases whose id contains "tts"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parents[2]
EVAL = HERE / "eval-googlecast-mcp.py"
COPY_PATHS = ["src", "scripts", "pyproject.toml"]


def case(case_id: str, path: str, find: str, replace: str, red: list[str],
         note: str = "", count: int = 1, also: list[tuple] | None = None) -> dict:
    """One seeded case. `also` carries extra (find, replace, count) edits for a
    fault that only shows up when several places change together."""
    edits = [(find, replace, count)] + [
        (f, r, c if len(e) > 2 else 1)
        for e in (also or [])
        for f, r, c in [(e[0], e[1], e[2] if len(e) > 2 else 1)]
    ]
    return {"id": case_id, "path": path, "edits": edits, "red": set(red), "note": note}


# --------------------------------------------------------------------------
# Seeded faults. `red` is written before the run and is the expectation.
# --------------------------------------------------------------------------
FAULTS: list[dict] = [
    # -- speaker_store ------------------------------------------------------
    case("store.video-counts-as-speaker",
         "src/googlecast_mcp/speaker_store.py",
         'SPEAKER_CAST_TYPES = ("audio", "group")',
         'SPEAKER_CAST_TYPES = ("audio", "group", "cast")',
         ["store.is_speaker", "store.speakers_filter"],
         "a Nest Hub would be offered as a speaker"),
    case("store.save-replaces-instead-of-merging",
         "src/googlecast_mcp/speaker_store.py",
         "for device in self.load() + devices:",
         "for device in devices:",
         ["store.merge_keeps_missed", "store.merge_updates_fields"],
         "one lossy mDNS scan would erase every device it missed"),
    case("store.crashes-on-truncated-file",
         "src/googlecast_mcp/speaker_store.py",
         "except (OSError, json.JSONDecodeError):",
         "except OSError:",
         ["store.corrupt_json"]),
    case("store.ignores-path-override",
         "src/googlecast_mcp/speaker_store.py",
         'override = os.environ.get("GOOGLECAST_MCP_STORE")',
         "override = None",
         ["store.path_env"]),

    # -- cast_manager -------------------------------------------------------
    case("cast.wrong-mime-fallback",
         "src/googlecast_mcp/cast_manager.py",
         '    return "video/mp4"',
         '    return "audio/mpeg"',
         ["cast.guess_content_type"]),
    case("cast.query-string-defeats-mime",
         "src/googlecast_mcp/cast_manager.py",
         'lowered = url.lower().split("?", 1)[0]',
         "lowered = url.lower()",
         ["cast.guess_content_type"]),
    case("cast.volume-not-clamped",
         "src/googlecast_mcp/cast_manager.py",
         "clamped = max(0.0, min(1.0, level))",
         "clamped = level",
         ["cast.volume_clamped"],
         "the item must call set_volume, not re-implement min/max beside it"),
    case("cast.error-hides-known-devices",
         "src/googlecast_mcp/cast_manager.py",
         'f"Device {target!r} did not respond. Known devices: {known}."',
         'f"Device did not respond."',
         ["cast.resolve_error_lists_known"]),
    case("cast.name-lookup-case-sensitive",
         "src/googlecast_mcp/cast_manager.py",
         "            lowered = target.strip().lower()\n            for cast in self._devices.values():",
         "            lowered = target\n            for cast in self._devices.values():",
         ["cast.resolve_locally"]),
    case("cast.status-drops-content-id",
         "src/googlecast_mcp/cast_manager.py",
         '                "content_id": getattr(media, "content_id", None),\n',
         "",
         ["cast.status_shape"],
         "content_id is the durable trace the hardware layer relies on"),
    case("cast.play-does-not-wait-for-receiver",
         "src/googlecast_mcp/cast_manager.py",
         "mc.block_until_active(timeout=10)",
         "pass",
         ["cast.play_media_guesses_mime"]),
    case("cast.ignores-explicit-mime",
         "src/googlecast_mcp/cast_manager.py",
         "content_type or _guess_content_type(url),",
         "_guess_content_type(url),",
         ["cast.play_media_explicit_mime"]),
    case("cast.seek-ignores-position",
         "src/googlecast_mcp/cast_manager.py",
         "self._connected(target).media_controller.seek(position_seconds)",
         "self._connected(target).media_controller.seek(0)",
         ["cast.controls_reach_device"]),

    # -- media_server -------------------------------------------------------
    case("media.binds-advertised-host",
         "src/googlecast_mcp/media_server.py",
         'ThreadingHTTPServer(("0.0.0.0", self._requested_port), handler)',
         "ThreadingHTTPServer((self._host, self._requested_port), handler)",
         ["media.binds_wildcard_advertises_lan"],
         "the bind address and the advertised address are two different things"),
    case("media.url-not-escaped",
         "src/googlecast_mcp/media_server.py",
         'f"http://{self._host}:{self.port}/{quote(relative.as_posix())}"',
         'f"http://{self._host}:{self.port}/{relative.as_posix()}"',
         ["media.quotes_filenames"]),
    case("media.serves-wrong-directory",
         "src/googlecast_mcp/media_server.py",
         "handler = partial(_QuietHandler, directory=str(self._directory))",
         "handler = partial(_QuietHandler, directory=str(self._directory.parent))",
         ["media.serves_bytes"],
         "the speaker would get a 404 while the cast still reports success"),
    case("media.port-repinnable-while-running",
         "src/googlecast_mcp/media_server.py",
         'raise RuntimeError("cannot change port while the media server is running")',
         "pass",
         ["media.port_pin_before_start"]),
    # Removing server_close() alone is invisible: HTTPServer sets
    # SO_REUSEADDR, and dropping the reference lets refcounting close the
    # socket anyway. The behaviour the item really guards is the early return.
    case("media.stop-not-idempotent",
         "src/googlecast_mcp/media_server.py",
         "        with self._lock:\n            if self._httpd is None:\n                return\n"
         "            self._httpd.shutdown()",
         "        with self._lock:\n            self._httpd.shutdown()",
         ["media.stop_is_idempotent"],
         "a second stop() during shutdown would raise"),

    # -- tts ----------------------------------------------------------------
    case("tts.voice-choice-ignored",
         "src/googlecast_mcp/tts.py",
         "return VOICES.get(voice.strip().lower(), voice)",
         "return DEFAULT_VOICE",
         ["tts.resolve_voice", "tts.distinct_voice_distinct_file", "say.reports_resolved_voice"]),
    case("tts.ignores-cache-override",
         "src/googlecast_mcp/tts.py",
         'override = os.environ.get("GOOGLECAST_MCP_CACHE")',
         "override = None",
         ["tts.cache_dir_env"]),
    case("tts.accepts-empty-text",
         "src/googlecast_mcp/tts.py",
         '    if not text or not text.strip():\n        raise ValueError("text must not be empty")',
         "    if False:\n        raise ValueError(\"text must not be empty\")",
         ["tts.empty_text_rejected"]),
    # Both cache reads have to go. Disabling only the fast path leaves the
    # locked double-check to catch it, so that alone is a performance
    # regression the suite cannot see -- recorded in eval/README.md.
    case("tts.cache-never-hits",
         "src/googlecast_mcp/tts.py",
         "    if path.exists() and path.stat().st_size > 0:\n        return path",
         "    if False:\n        return path",
         ["tts.cache_hit_skips_service"],
         "every announcement would be re-rendered over the network",
         also=[("        if path.exists() and path.stat().st_size > 0:\n            return path",
                "        if False:\n            return path", 1)]),
    case("tts.no-retry",
         "src/googlecast_mcp/tts.py",
         "for attempt in range(3):",
         "for attempt in range(1):",
         ["tts.retries_then_succeeds", "tts.no_zero_byte_residue"]),
    case("tts.keeps-zero-byte-file",
         "src/googlecast_mcp/tts.py",
         "path.unlink(missing_ok=True)",
         "pass",
         # not tts.retries_then_succeeds: the third attempt overwrites the
         # stub file, so that item cannot see the missing cleanup.
         ["tts.no_zero_byte_residue", "tts.empty_render_is_failure"],
         "a 0-byte mp3 poisons the cache: the speaker plays silence forever",
         count=2),
    case("tts.renders-overlap-again",
         "src/googlecast_mcp/tts.py",
         "    async with _synthesis_lock:",
         "    if True:",
         ["tts.renders_are_serialised"],
         "the regression the lock was added for: retrying alone left 4/6 in 101s"),

    # -- server: selection --------------------------------------------------
    case("server.no-target-plays-everywhere",
         "src/googlecast_mcp/server.py",
         '    return [], {\n        "status": "needs_speaker_selection",',
         '    return names, None\n    return [], {\n        "status": "needs_speaker_selection",',
         # not server.no_speakers_found: the empty-network branch returns at
         # server.py:84-89, before the selection prompt this fault replaces.
         ["server.no_target_asks", "say.without_target_plays_nothing"],
         "requirement 3 inverted: silence becomes consent to a physical side effect"),
    case("server.all-includes-groups",
         "src/googlecast_mcp/server.py",
         'if s["cast_type"] != "group"',
         "if s",
         ["server.all_excludes_groups", "say.all_casts_once_per_speaker"],
         "the double-stream bug: the API still answers 'playing' on all four"),
    case("server.comma-list-not-split",
         "src/googlecast_mcp/server.py",
         'return [part.strip() for part in cleaned.split(",") if part.strip()], None',
         "return [cleaned], None",
         ["server.comma_list"]),
    case("server.name-lowercased",
         "src/googlecast_mcp/server.py",
         'return [part.strip() for part in cleaned.split(",") if part.strip()], None',
         'return [part.strip().lower() for part in cleaned.split(",") if part.strip()], None',
         ["server.comma_list", "server.group_by_name_still_reachable"]),
    case("server.empty-network-still-asks",
         "src/googlecast_mcp/server.py",
         "    if not names:",
         "    if False:",
         ["server.no_speakers_found"]),

    # -- server: say --------------------------------------------------------
    case("say.casts-as-video",
         "src/googlecast_mcp/server.py",
         '_manager.play_media, name, url, "audio/mpeg", text[:60]',
         '_manager.play_media, name, url, "video/mp4", text[:60]',
         ["say.casts_audio_mpeg"]),
    case("say.drops-title",
         "src/googlecast_mcp/server.py",
         '_manager.play_media, name, url, "audio/mpeg", text[:60]',
         '_manager.play_media, name, url, "audio/mpeg", None',
         ["say.casts_audio_mpeg"]),
    case("say.always-reports-ok",
         "src/googlecast_mcp/server.py",
         '"status": "ok" if played else "failed",',
         '"status": "ok",',
         ["say.every_speaker_failing_is_a_failure"],
         "the most dangerous shape of lie: green while nothing happened"),
    case("say.one-dead-speaker-sinks-all",
         "src/googlecast_mcp/server.py",
         "        try:\n"
         "            await asyncio.to_thread(\n"
         '                _manager.play_media, name, url, "audio/mpeg", text[:60]\n'
         "            )\n"
         '            return {"speaker": name, "status": "playing"}\n'
         "        except Exception as exc:  # one unreachable speaker must not fail the rest\n"
         '            return {"speaker": name, "status": "error", "error": str(exc)}',
         "        await asyncio.to_thread(\n"
         '            _manager.play_media, name, url, "audio/mpeg", text[:60]\n'
         "        )\n"
         '        return {"speaker": name, "status": "playing"}',
         ["say.one_bad_speaker_does_not_sink_the_rest",
          "say.every_speaker_failing_is_a_failure"]),

    # -- tool surface -------------------------------------------------------
    case("server.tool-missing",
         "src/googlecast_mcp/server.py",
         "@mcp.tool()\nasync def quit_app(",
         "async def quit_app(",
         ["server.tool_surface"],
         "an explicit name SET catches this; len() == len() would not"),
    case("server.target-becomes-required",
         "src/googlecast_mcp/server.py",
         "    target: str | None = None,\n    voice: str = \"female\",",
         "    target: str,\n    voice: str = \"female\",",
         ["server.say_schema", "say.without_target_plays_nothing"]),

    # -- __main__ -----------------------------------------------------------
    case("entry.wildcard-bind-treated-as-address",
         "src/googlecast_mcp/__main__.py",
         'if bind_host not in ("0.0.0.0", "::"):',
         "if True:",
         ["entry.trusts_lan_and_proxy_domain"]),
    case("entry.no-https-origins",
         "src/googlecast_mcp/__main__.py",
         'for scheme in ("http", "https")',
         'for scheme in ("http",)',
         ["entry.trusts_lan_and_proxy_domain"],
         "the TLS reverse proxy in front would be rejected"),
    case("entry.host-needs-explicit-port",
         "src/googlecast_mcp/__main__.py",
         'allowed_hosts=[p for h in unique for p in (h, f"{h}:*")],',
         'allowed_hosts=[f"{h}:*" for h in unique],',
         ["entry.trusts_lan_and_proxy_domain"],
         "a proxy on 443 sends a bare Host -> 421 Misdirected Request"),
    case("entry.browser-origin-dropped",
         "src/googlecast_mcp/__main__.py",
         "allowed_origins.extend(origins or [])",
         "pass",
         ["entry.browser_origin_passthrough"]),
    case("entry.session-header-not-exposed",
         "src/googlecast_mcp/__main__.py",
         'expose_headers=["Mcp-Session-Id", "mcp-session-id"],',
         "expose_headers=[],",
         ["entry.cors_exposes_session_header"],
         "the browser client fails with a bare 'Failed to fetch'"),
    case("entry.preflight-not-allowed",
         "src/googlecast_mcp/__main__.py",
         'allow_methods=["GET", "POST", "DELETE", "OPTIONS"],',
         'allow_methods=["GET", "POST", "DELETE"],',
         ["entry.cors_exposes_session_header"]),

    # -- shipped artefacts --------------------------------------------------
    case("ship.sdk-pin-removed",
         "pyproject.toml",
         '"mcp[cli]>=1.13,<2"',
         '"mcp[cli]"',
         ["ship.mcp_pin"],
         "opens the door to the unrelated 'mcp' 2.0.0 and its httpx2 dependency"),
    case("ship.install-does-not-replace-process",
         "scripts/service.sh",
         'sudo systemctl restart "$SERVICE_NAME"',
         'sudo systemctl start "$SERVICE_NAME"',
         ["ship.service_restarts"],
         "the three-day ghost process",
         count=2),
    case("ship.proxy-buffers",
         "scripts/nginx-googlecast-mcp.conf",
         "proxy_buffering off",
         "proxy_buffering on",
         ["ship.nginx_no_buffering"],
         "the client hangs and reports nothing at all"),
]

# --------------------------------------------------------------------------
# Controls: harmless edits that must leave the suite GREEN.
# A red here means the suite fires at noise -- as broken as never firing.
# --------------------------------------------------------------------------
CONTROLS: list[dict] = [
    case("control.comment-added",
         "src/googlecast_mcp/cast_manager.py",
         "class DeviceNotFoundError(Exception):",
         "# A harmless comment. Nothing about behaviour changes here.\nclass DeviceNotFoundError(Exception):",
         []),
    case("control.docstring-reworded",
         "src/googlecast_mcp/tts.py",
         '"""Vietnamese text-to-speech via edge-tts.',
         '"""Vietnamese text to speech, using edge-tts.',
         []),
    case("control.blank-line-in-entrypoint",
         "src/googlecast_mcp/__main__.py",
         "def main() -> None:",
         "\ndef main() -> None:",
         []),
    case("control.whitespace-in-service-script",
         "scripts/service.sh",
         "cmd_status() {",
         "cmd_status()  {",
         []),
]


# --------------------------------------------------------------------------
def make_copy(dest: Path) -> None:
    for rel in COPY_PATHS:
        source = PRODUCT / rel
        target = dest / rel
        if source.is_dir():
            shutil.copytree(source, target,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def apply_fault(root: Path, spec: dict) -> None:
    path = root / spec["path"]
    text = path.read_text(encoding="utf-8")
    for find, replace, count in spec["edits"]:
        found = text.count(find)
        if found != count:
            raise RuntimeError(
                f"{spec['id']}: pattern occurs {found}x in {spec['path']}, "
                f"expected {count}x -- the product moved and this case is stale"
            )
        text = text.replace(find, replace)
    path.write_text(text, encoding="utf-8")


def run_eval(root: Path) -> tuple[set[str], set[str], dict]:
    """Run the offline eval against `root`. Returns (red_ids, all_ids, raw)."""
    report = root / "report.json"
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GOOGLECAST_MCP_EVAL_ROOT": str(root),
        "GOOGLECAST_MCP_EVAL_JSON": str(report),
    })
    env.pop("GOOGLECAST_MCP_CACHE", None)
    env.pop("GOOGLECAST_MCP_STORE", None)
    proc = subprocess.run([sys.executable, str(EVAL)], env=env,
                          capture_output=True, text=True, timeout=900)
    if not report.exists():
        raise RuntimeError(
            "the eval produced no report at all:\n"
            + (proc.stdout or "")[-3000:] + (proc.stderr or "")[-2000:]
        )
    raw = json.loads(report.read_text(encoding="utf-8"))
    if raw["ran"] < raw["total"]:
        raise RuntimeError(
            f"the eval stopped half-way: ran {raw['ran']}/{raw['total']}. "
            "A partial run cannot grade a seeded fault."
        )
    red = {r["id"] for r in raw["results"] if r["outcome"] != "PASS"}
    every = {r["id"] for r in raw["results"]}
    return red, every, raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="run cases whose id contains this")
    args = parser.parse_args()

    cases = [c for c in FAULTS + CONTROLS if args.only in c["id"]]
    if not cases:
        print(f"--only {args.only!r} khop 0 case; khong co gi de chung minh.", file=sys.stderr)
        return 2
    workdir = Path(tempfile.mkdtemp(prefix="googlecast-reverse-"))
    verdicts: list[tuple[str, str, str]] = []
    registered: set[str] = set()

    print(f"reverse-check: {len(cases)} case ({len(FAULTS)} loi gieo + {len(CONTROLS)} doi chung)")
    print(f"ban sao lam viec: {workdir}")
    print(f"cay san pham chi doc: {PRODUCT}\n")

    try:
        for spec in cases:
            is_control = spec in CONTROLS
            root = workdir / spec["id"].replace("/", "_")
            root.mkdir(parents=True)
            label = "DOI CHUNG" if is_control else "loi gieo "
            try:
                make_copy(root)
                apply_fault(root, spec)
                red, every, raw = run_eval(root)
                registered |= every
            except Exception as exc:
                verdicts.append((spec["id"], "LOI", str(exc).splitlines()[0]))
                print(f"  LOI  {label} {spec['id']}\n        {str(exc).splitlines()[0]}")
                continue

            if is_control:
                if red:
                    verdicts.append((spec["id"], "DO BUA",
                                     f"a harmless edit turned {sorted(red)} red"))
                    print(f" DOBUA {label} {spec['id']} -> {sorted(red)}")
                else:
                    verdicts.append((spec["id"], "dat", "stayed green, as it must"))
                    print(f"  ok   {label} {spec['id']} -> xanh (dung ky vong)")
                continue

            missed = spec["red"] - red
            if missed:
                verdicts.append((spec["id"], "TEST GIA",
                                 f"expected red but stayed green: {sorted(missed)}"))
                print(f" TGIA  {label} {spec['id']}\n        van XANH: {sorted(missed)}")
            else:
                extra = sorted(red - spec["red"])
                suffix = f"  (+{extra})" if extra else ""
                verdicts.append((spec["id"], "dat", f"caught by {sorted(spec['red'])}"))
                print(f"  ok   {label} {spec['id']} -> do dung cho{suffix}")

        # Reverting is proved by running, not by looking at git.
        print("\n-- hoan nguyen: chay lai eval tren cay san pham nguyen ven --")
        pristine = workdir / "_pristine"
        pristine.mkdir()
        make_copy(pristine)
        red, every, raw = run_eval(pristine)
        registered |= every
        if red:
            verdicts.append(("hoan-nguyen", "LOI", f"the untouched tree is not green: {sorted(red)}"))
            print(f"  LOI  cay nguyen ven van DO: {sorted(red)}")
        else:
            print(f"  ok   cay nguyen ven XANH ({raw['ran']}/{raw['total']})")

        # Coverage: an item no fault can redden is a structural suspect.
        covered = set().union(*(c["red"] for c in FAULTS)) if FAULTS else set()
        uncovered = sorted(registered - covered)
        stale = sorted(covered - registered)

        print("\n" + "=" * 72)
        bad = [v for v in verdicts if v[1] != "dat"]
        for cid, verdict, detail in bad:
            print(f"[{verdict}] {cid}\n    {detail}")
        print(f"case dat: {len(verdicts) - len(bad)}/{len(verdicts)}")
        print(f"do phu nguoc (lop offline): {len(registered) - len(uncovered)}/{len(registered)} muc")
        if uncovered:
            print("CHUA PHU (khong loi gieo nao lam do duoc -- nghi pham cau truc):")
            for item in uncovered:
                print(f"  - {item}")
        if stale:
            print(f"KY VONG LAC: id khong co trong so dang ky: {stale}")
        print("Lop --online / --hardware khong nam trong kiem nguoc nay: CHUA PHU,")
        print("chung can dich vu that / loa that, xem eval/README.md.")
        print("=" * 72)
        ok = not bad and not uncovered and not stale
        print("KET QUA KIEM NGUOC: " + ("DAT" if ok else "CHUA DAT"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
