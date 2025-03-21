from flask import Flask, render_template, request, send_file
import yt_dlp
import os

app = Flask(__name__, static_folder="static")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def download_video(url):
    ydl_opts = {
        "format": "best",
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
        "allow_unplayable_formats": True,  # Allow all formats
        "merge_output_format": "mp4",  # Convert to MP4 if needed
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info).replace(".webm", ".mp4").replace(".mkv", ".mp4")
    
    return file_path

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        if url:
            try:
                file_path = download_video(url)
                return send_file(file_path, as_attachment=True)
            except Exception as e:
                return f"Error: {e}"
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
