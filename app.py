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
            audio_formats = []
            
            # Get original video height
            original_height = info.get('height', 0)
            
            for f in info.get('formats', []):
                format_info = {
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'filesize': f.get('filesize'),
                    'format_note': f.get('format_note', '')
                }
                
                # Video formats
                if f.get('height') and f.get('ext') == 'mp4':
                    format_info['height'] = f.get('height')
                    # Check if video has audio
                    format_info['has_audio'] = f.get('acodec') != 'none'
                    # Mark if it's original quality
                    format_info['is_original'] = f.get('height') == original_height
                    formats.append(format_info)
                
                # Audio formats
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    format_info['abr'] = f.get('abr', 0)  # Default to 0 if None
                    audio_formats.append(format_info)
            
            # Sort video formats by original quality first, then height
            formats.sort(key=lambda x: (-x['is_original'], -x['height']))
            
            # Sort audio formats by bitrate (descending), handling None values
            audio_formats.sort(key=lambda x: x['abr'] if x['abr'] is not None else 0, reverse=True)
            
            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats,
                'audio_formats': audio_formats
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

def get_direct_url(url, format_id):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "format": format_id,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'url': info.get('url'),
                'title': info.get('title'),
                'ext': info.get('ext')
            }
        except Exception as e:
            return {'error': str(e)}

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
        return jsonify({"error": "Missing URL or format"}), 400
    
    try:
        file_path = download_video(url, format_id)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/download-file/<filename>")
def download_file(filename):
    try:
        return send_file(
            os.path.join(DOWNLOAD_FOLDER, filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
