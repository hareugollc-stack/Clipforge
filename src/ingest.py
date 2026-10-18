"""
URL ingestion for ClipForge — download a video from a pasted link,
then hand it to the normal clip pipeline.

Uses yt-dlp. YouTube sometimes throws a bot check at datacenter IPs;
download_url() surfaces a clear error in that case instead of hanging.
"""
import os
import subprocess
import sys
import uuid

MAX_BYTES = 150 * 1024 * 1024  # 150 MB cap per download


def download_url(url, out_dir, max_bytes=MAX_BYTES):
    """Download video from url into out_dir. Returns local file path."""
    os.makedirs(out_dir, exist_ok=True)
    tag = uuid.uuid4().hex[:8]
    tmpl = os.path.join(out_dir, f"ingest-{tag}.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--no-check-certificate",  # sandbox egress proxy does TLS interception
        "--extractor-args", "youtube:player_client=android",  # dodges bot check
        "-f", "bv*[height<=720]+ba/b[height<=720]/b",
        "-f", "bv*[height<=720]+ba/b[height<=720]/b",
        "--max-filesize", str(max_bytes),
        "--no-warnings",
        "-o", tmpl,
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        err = (r.stderr or "")[-500:]
        if "bot" in err.lower() or "sign in" in err.lower():
            raise RuntimeError(
                "YouTube blocked the download with a bot check. "
                "Try again in a few minutes, or upload the video file directly.")
        raise RuntimeError("Download failed: " + err)
    # find the downloaded file
    for f in os.listdir(out_dir):
        if f.startswith(f"ingest-{tag}."):
            return os.path.join(out_dir, f)
    raise RuntimeError("Download finished but no file found.")


if __name__ == "__main__":
    import sys
    print(download_url(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "."))
