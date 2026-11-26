def download_task(video_url, job_id):
    """Runs yt-dlp in a background thread and saves an mp4 into DOWNLOAD_DIR."""
    try:
        output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
        
        cmd = [
            "python", "-m", "yt_dlp",
            "--extractor-args", "youtube:player_client=tv,mweb",
            "--extractor-args", "youtubepot-bgutilhttp:base_url=https://bgutil-pot-latest-1crq.onrender.com",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            video_url,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            jobs[job_id] = {"status": "error", "error": result.stderr[-500:] or "yt-dlp failed"}
            return

        # Find the produced file (yt-dlp may produce .mp4 or .mkv etc.)
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(job_id + "."):
                jobs[job_id] = {"status": "done", "file": f}
                return

        jobs[job_id] = {"status": "error", "error": "Output file not found"}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}
