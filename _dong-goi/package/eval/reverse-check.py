#!/usr/bin/env python3
"""Kiểm ngược bộ eval: eval chưa từng ĐỎ là eval chưa chứng minh được gì.

    uv run python _dong-goi/package/eval/reverse-check.py

Cách làm, theo đúng thứ tự — thứ tự chính là điểm mấu chốt:

  1. KHAI TRƯỚC kỳ vọng. Mỗi lỗi gieo vào đi kèm danh sách mục kiểm LẼ RA PHẢI
     ĐỎ, viết ra trước khi chạy. Nhìn kết quả rồi mới "kỳ vọng" là tự lừa mình.
  2. Gieo lỗi, chạy lại eval offline.
  3. So kỳ vọng với thực tế:
       - lẽ-ra-đỏ-mà-XANH  → TEST GIẢ. Phải sửa bài kiểm, hoặc ghi CHƯA PHỦ.
                             Chú thích suông không phải một lựa chọn.
       - đỏ-đúng-kỳ-vọng   → mục kiểm đó có thật.
  4. Khôi phục nguyên trạng, XOÁ __pycache__, rồi CHẠY LẠI EVAL và đòi thấy
     XANH. Đây mới là bằng chứng hoàn nguyên.

     `git status` sạch KHÔNG phải bằng chứng: một lỗi gieo vào dài đúng bằng
     bản gốc để lại .pyc cũ, git thấy sạch mà eval vẫn đỏ — đã dính đúng bẫy
     này một lần.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src" / "googlecast_mcp"
EVAL = Path(__file__).with_name("eval-googlecast-mcp.py")

# --------------------------------------------------------------------------
# 1. KỲ VỌNG — viết TRƯỚC khi chạy bất cứ thứ gì
# --------------------------------------------------------------------------
# (tên lỗi, file, chuỗi cũ, chuỗi mới, các mục kiểm LẼ RA PHẢI ĐỎ)

FAULTS: list[tuple[str, Path, str, str, list[str]]] = [
    (
        "hoàn nguyên bản vá 'all': gửi tới cả nhóm lẫn thành viên",
        SRC / "server.py",
        'return [s["friendly_name"] for s in speakers if s["cast_type"] != "group"], None',
        'return [s["friendly_name"] for s in speakers], None',
        ["đúng tập loa mong đợi", "không có nhóm trong danh sách",
         "mỗi host vật lý nhận đúng một luồng"],
    ),
    (
        "coi thiết bị hình ảnh cũng là loa",
        SRC / "speaker_store.py",
        'SPEAKER_CAST_TYPES = ("audio", "group")',
        'SPEAKER_CAST_TYPES = ("audio", "group", "cast")',
        ["cast KHÔNG phải loa", "SPEAKER_CAST_TYPES",
         "trả đúng tập loa để hỏi lại", "đúng tập loa mong đợi"],
    ),
    (
        "ĐỔI TÊN một tool (số lượng KHÔNG đổi — bẫy so-kích-thước)",
        SRC / "server.py",
        "async def quit_app(target: str) -> str:",
        "async def quit_application(target: str) -> str:",
        ["bộ tool đúng bằng tập kỳ vọng"],
    ),
    (
        "allowlist bỏ dạng host TRẦN, chỉ giữ 'host:*'",
        SRC / "__main__.py",
        'allowed_hosts=[p for h in unique for p in (h, f"{h}:*")],',
        'allowed_hosts=[f"{h}:*" for h in unique],',
        ["có 127.0.0.1", "domain dạng TRẦN"],
    ),
    (
        "allowlist bỏ scheme https (proxy TLS phía trước sẽ bị 421)",
        SRC / "__main__.py",
        'for scheme in ("http", "https")',
        'for scheme in ("http",)',
        ["origin https trần", "origin https kèm cổng"],
    ),
    (
        "thiếu chọn loa thì cứ phát ra tất cả (tác dụng phụ vật lý ngoài ý muốn)",
        SRC / "server.py",
        '''    if not names:
        return [], {
            "status": "no_speakers_found",''',
        '''    if names:
        return names, None
    if not names:
        return [], {
            "status": "no_speakers_found",''',
        ["KHÔNG cast tới thiết bị nào", "KHÔNG gọi TTS",
         "chuỗi chọn loa toàn khoảng trắng"],
    ),
    (
        "media server quảng bá 0.0.0.0 (loa không bao giờ tải được)",
        SRC / "media_server.py",
        "self._host = host or lan_ip()",
        'self._host = "0.0.0.0"',
        ["URL quảng bá là địa chỉ LAN, KHÔNG phải 0.0.0.0"],
    ),
    (
        "bỏ chốt chặn text rỗng (gửi chuỗi rỗng lên edge-tts)",
        SRC / "tts.py",
        '''    if not text or not text.strip():
        raise ValueError("text must not be empty")''',
        '''    if not text or not text.strip():
        return Path(tempfile.gettempdir()) / "rong.mp3"''',
        ["'' → ValueError", "'   ' → ValueError"],
    ),
    (
        "SpeakerStore ghi đè thay vì gộp (mất loa đang ngủ)",
        SRC / "speaker_store.py",
        "for device in self.load() + devices:",
        "for device in devices:",
        ["lần lưu sau GỘP, không ghi đè", "speakers() lọc đúng tập"],
    ),
    (
        "bỏ kẹp âm lượng (gửi thẳng 5.0 xuống thiết bị)",
        SRC / "cast_manager.py",
        "clamped = max(0.0, min(1.0, level))",
        "clamped = level",
        ["set_volume(5.0) trả về 1.0", "giá trị thật gửi xuống thiết bị là 1.0",
         "set_volume(-3.0) trả về 0.0"],
    ),
    (
        "đoán sai MIME cho mp3 (loa nhận audio như video)",
        SRC / "cast_manager.py",
        '".mp3": "audio/mpeg",',
        '".mp3": "video/mp4",',
        # KHÔNG kỳ vọng "content_type gửi cho loa": say() truyền thẳng hằng
        # "audio/mpeg", không đi qua bảng MIME. Kỳ vọng ban đầu ở đây SAI (bài
        # kiểm vẫn thật) — đã sửa kỳ vọng, không nới bài kiểm.
        ["a.mp3 → audio/mpeg", "a.MP3 → audio/mpeg", "a.mp3?token=1 → audio/mpeg"],
    ),
    (
        "một loa hỏng làm đổ cả lượt (bỏ cô lập lỗi)",
        SRC / "server.py",
        '''        except Exception as exc:  # one unreachable speaker must not fail the rest
            return {"speaker": name, "status": "error", "error": str(exc)}''',
        '        except Exception:\n            return {"speaker": name, "status": "playing"}',
        ["loa hỏng báo lỗi riêng", "không loa nào phát được → failed"],
    ),
]

# Lỗi ĐỐI CHỨNG: thay đổi vô hại, eval PHẢI vẫn xanh. Nếu nó cũng làm đỏ thì
# bộ kiểm đang bám vào thứ không phải hành vi.
CONTROL = (
    "đối chứng: sửa một dòng chú thích (eval phải VẪN XANH)",
    SRC / "tts.py",
    "# Vietnamese neural voices offered by edge-tts.",
    "# Vietnamese neural voices offered by edge-tts. (dòng chú thích đã sửa)",
)

# CHƯA PHỦ — nói thẳng, không giấu:
NOT_COVERED = [
    "Tầng --hardware: không gieo lỗi tự động được vì cần loa thật và sẽ phát ra "
    "tiếng. Luật mốc chờ ở đó ĐÃ được kiểm ngược MỘT LẦN BẰNG TAY: bản trước "
    "đọc player_state ngay khi play_media trả về và ĐỎ thật (`Kitchen speaker "
    "reports IDLE`) dù loa vẫn tốt; thay bằng wait_until thì xanh.",
    "Đường _connect_saved (kết nối thẳng theo địa chỉ đã lưu khi mDNS sót "
    "thiết bị) chỉ được phủ ở nhánh 'không tìm thấy'. Nhánh kết nối THÀNH CÔNG "
    "cần một thiết bị Cast thật → CHƯA PHỦ ở tầng offline.",
    "nginx / TLS / CORS ở tầng proxy: eval chỉ kiểm allowlist mà tiến trình "
    "sinh ra, không dựng nginx. CHƯA PHỦ.",
]


# --------------------------------------------------------------------------
# 2-4. Chạy
# --------------------------------------------------------------------------


def clear_bytecode() -> None:
    """Xoá bytecode. Bỏ bước này là mời đúng cái bẫy .pyc quay lại."""
    for d in REPO.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)


def run_eval() -> tuple[bool, set[str]]:
    """Chạy eval tầng offline. Trả (xanh?, tập nhãn mục kiểm bị ĐỎ)."""
    clear_bytecode()
    proc = subprocess.run(
        [sys.executable, str(EVAL)], cwd=REPO, capture_output=True, text=True
    )
    red = set(re.findall(r"^  FAIL (.+?)(?: — |$)", proc.stdout, flags=re.M))
    if proc.returncode not in (0, 1):
        red.add(f"<eval sập: {proc.stderr.strip().splitlines()[-1:]}>")
    return proc.returncode == 0, red


def main() -> int:
    originals = {p: p.read_bytes() for _, p, _, _, _ in FAULTS}
    originals[CONTROL[1]] = CONTROL[1].read_bytes()

    print("Bước 0 — nguyên trạng phải XANH trước đã")
    green, red = run_eval()
    if not green:
        print(f"  DỪNG: eval đã đỏ từ đầu: {sorted(red)}")
        return 2
    print("  ok   eval xanh ở nguyên trạng\n")

    fake_tests: list[str] = []
    report: list[tuple[str, list[str], list[str]]] = []

    try:
        for name, path, old, new, expected in FAULTS:
            print(f"Lỗi gieo vào — {name}")
            text = path.read_text(encoding="utf-8")
            if old not in text:
                print("  DỪNG: không tìm thấy chuỗi cần thay — eval lệch pha với mã nguồn.")
                return 2
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            try:
                green, red = run_eval()
            finally:
                path.write_bytes(originals[path])

            if green:
                # Toàn bộ eval vẫn xanh sau một lỗi thật → mọi kỳ vọng đều giả.
                print("  TEST GIẢ: eval VẪN XANH dù mã nguồn đã hỏng.")
                fake_tests.extend(f"{name} :: {e}" for e in expected)
                report.append((name, [], expected))
                continue

            hit = [e for e in expected if any(e in r for r in red)]
            miss = [e for e in expected if e not in hit]
            for e in hit:
                print(f"  ok   đỏ đúng kỳ vọng: {e}")
            for e in miss:
                print(f"  TEST GIẢ: lẽ ra đỏ mà XANH: {e}")
            print(f"       (tổng cộng {len(red)} mục đỏ)")
            fake_tests.extend(f"{name} :: {e}" for e in miss)
            report.append((name, hit, miss))
            print()

        name, path, old, new = CONTROL
        print(f"Đối chứng — {name}")
        text = path.read_text(encoding="utf-8")
        assert old in text, "không tìm thấy dòng chú thích đối chứng"
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        try:
            green, red = run_eval()
        finally:
            path.write_bytes(originals[path])
        if green:
            print("  ok   eval vẫn xanh với thay đổi vô hại\n")
        else:
            print(f"  CẢNH BÁO: đối chứng làm eval đỏ: {sorted(red)}\n")
            fake_tests.append("đối chứng vô hại lại làm eval đỏ")
    finally:
        for path, blob in originals.items():
            path.write_bytes(blob)

    # Bước cuối: hoàn nguyên = CHẠY LẠI EVAL THẤY XANH, không phải nhìn git.
    print("Xác minh hoàn nguyên — xoá bytecode rồi CHẠY LẠI EVAL")
    green, red = run_eval()
    print(f"  {'ok   eval xanh trở lại' if green else 'HỎNG: eval vẫn đỏ: ' + str(sorted(red))}")
    print("  (đây là bằng chứng hoàn nguyên; `git status` sạch thì KHÔNG phải)")

    print("\n" + "=" * 62)
    print(f"Đã gieo {len(FAULTS)} lỗi + 1 đối chứng.")
    print("CHƯA PHỦ:")
    for n in NOT_COVERED:
        print(f"  - {n}")
    if fake_tests:
        print("\nTEST GIẢ CẦN SỬA:")
        for f in fake_tests:
            print(f"  - {f}")
        return 1
    print("\nKhông có mục lẽ-ra-đỏ-mà-xanh. Hoàn nguyên: " + ("XANH" if green else "ĐỎ"))
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
