from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os

app = Flask(__name__, static_folder="static")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_video_info(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info.get('formats', []):
                if f.get('height') and f.get('ext') == 'mp4':
                    formats.append({
                        'format_id': f.get('format_id'),
                        'height': f.get('height'),
                        'ext': f.get('ext'),
                        'filesize': f.get('filesize'),
                        'format_note': f.get('format_note', '')
                    })
            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': sorted(formats, key=lambda x: x['height'], reverse=True)
            }
        except Exception as e:
            return {'error': str(e)}

def download_video(url, format_id):
    ydl_opts = {
        "format": format_id,
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info).replace(".webm", ".mp4").replace(".mkv", ".mp4")
    
    return file_path

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/get-formats", methods=["POST"])
def get_formats():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    info = get_video_info(url)
    if "error" in info:
        return jsonify({"error": info["error"]}), 400
    
    return jsonify(info)

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format_id")
    
    if not url or not format_id:
        return "Error: Missing URL or format", 400
    
    try:
        file_path = download_video(url, format_id)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Error: {e}", 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
