from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
from moviepy.editor import VideoFileClip, AudioFileClip
import tempfile
import threading
import time

app = Flask(__name__, static_folder="static")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Global dictionary to store download progress
download_progress = {}

def progress_hook(d):
    if d['status'] == 'downloading':
        video_id = d.get('info_dict', {}).get('id', 'unknown')
        total_bytes = d.get('total_bytes')
        downloaded_bytes = d.get('downloaded_bytes', 0)
        
        if total_bytes:
            progress = (downloaded_bytes / total_bytes) * 100
            download_progress[video_id] = {
                'progress': round(progress, 2),
                'speed': d.get('speed', 0),
                'status': 'downloading'
            }
    elif d['status'] == 'finished':
        video_id = d.get('info_dict', {}).get('id', 'unknown')
        download_progress[video_id] = {
            'progress': 100,
            'status': 'finished'
        }

def get_video_info(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "progress_hooks": [progress_hook],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id', 'unknown')
            download_progress[video_id] = {'progress': 0, 'status': 'starting'}
            
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
                'audio_formats': audio_formats,
                'video_id': video_id
            }
        except Exception as e:
            return {'error': str(e)}

def download_video(url, format_id, merge_audio=False):
    ydl_opts = {
        "format": format_id,
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "progress_hooks": [progress_hook],
    }

    if merge_audio:
        # Download video without audio
        video_format = format_id
        ydl_opts["format"] = video_format
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(video_info).replace(".webm", ".mp4").replace(".mkv", ".mp4")
        
        # Download best audio
        audio_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=m4a]",
            "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s_audio.%(ext)s",
            "progress_hooks": [progress_hook],
        }
        
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            audio_info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(audio_info)
        
        # Merge video and audio using moviepy
        try:
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            
            # Set the audio of the video clip
            final_video = video.set_audio(audio)
            
            # Generate output path
            output_path = video_path.replace(".mp4", "_merged.mp4")
            
            # Write the result to a file
            final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
            
            # Close the clips to free up resources
            video.close()
            audio.close()
            
            # Clean up temporary files
            os.remove(video_path)
            os.remove(audio_path)
            
            return output_path
            
        except Exception as e:
            # Clean up in case of error
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if os.path.exists(output_path):
                os.remove(output_path)
            raise Exception(f"Error merging video and audio: {str(e)}")
    else:
        # Regular video download without merging
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

@app.route("/progress/<video_id>")
def get_progress(video_id):
    progress = download_progress.get(video_id, {'progress': 0, 'status': 'unknown'})
    return jsonify(progress)

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format_id")
    merge_audio = request.form.get("merge_audio") == "true"
    
    if not url or not format_id:
        return jsonify({"error": "Missing URL or format"}), 400
    
    try:
        file_path = download_video(url, format_id, merge_audio)
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
        
        # Add cleanup after sending the file
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Also clean up any potential merged files
                merged_path = file_path.replace(".mp4", "_merged.mp4")
                if os.path.exists(merged_path):
                    os.remove(merged_path)
            except Exception as e:
                print(f"Error cleaning up file: {str(e)}")
        
        return response
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
