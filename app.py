from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
from moviepy.editor import VideoFileClip, AudioFileClip
import tempfile
import logging
from functools import lru_cache
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")

# Constants
DOWNLOAD_FOLDER = "downloads"
MAX_CACHE_SIZE = 100
CACHE_TTL = 3600  # 1 hour in seconds

# Create download folder if it doesn't exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_cache_key(url):
    """Generate a cache key for the URL"""
    return hashlib.md5(url.encode()).hexdigest()

@lru_cache(maxsize=MAX_CACHE_SIZE)
def get_video_info(url):
    """Get video information with caching"""
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
                    format_info['has_audio'] = f.get('acodec') != 'none'
                    format_info['is_original'] = f.get('height') == original_height
                    formats.append(format_info)
                
                # Audio formats
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    format_info['abr'] = f.get('abr', 0)
                    audio_formats.append(format_info)
            
            # Sort formats
            formats.sort(key=lambda x: (-x['is_original'], -x['height']))
            audio_formats.sort(key=lambda x: x['abr'] if x['abr'] is not None else 0, reverse=True)
            
            return {
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats,
                'audio_formats': audio_formats
            }
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return {'error': str(e)}

def download_video(url, format_id, merge_audio=False):
    """Download video with error handling and cleanup"""
    temp_dir = tempfile.mkdtemp()
    try:
        ydl_opts = {
            "format": format_id,
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
        }

        if merge_audio:
            # Download video without audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(video_info).replace(".webm", ".mp4").replace(".mkv", ".mp4")
            
            # Download best audio
            audio_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio[ext=m4a]",
                "outtmpl": os.path.join(temp_dir, "%(title)s_audio.%(ext)s"),
            }
            
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                audio_info = ydl.extract_info(url, download=True)
                audio_path = ydl.prepare_filename(audio_info)
            
            # Merge video and audio
            try:
                video = VideoFileClip(video_path)
                audio = AudioFileClip(audio_path)
                
                final_video = video.set_audio(audio)
                output_path = video_path.replace(".mp4", "_merged.mp4")
                
                final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
                
                video.close()
                audio.close()
                
                # Clean up temporary files
                os.remove(video_path)
                os.remove(audio_path)
                
                return output_path
                
            except Exception as e:
                logger.error(f"Error merging video and audio: {str(e)}")
                raise
        else:
            # Regular video download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info).replace(".webm", ".mp4").replace(".mkv", ".mp4")
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        raise
    finally:
        # Clean up temporary directory
        for file in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, file))
            except Exception as e:
                logger.error(f"Error cleaning up file: {str(e)}")
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            logger.error(f"Error removing temp directory: {str(e)}")

def download_mp3(url, quality='best'):
    """Download audio and convert to MP3 with specified quality"""
    temp_dir = tempfile.mkdtemp()
    output_path = None
    try:
        quality_formats = {
            'best': 'bestaudio[ext=m4a]/bestaudio[ext=m4a]',
            'good': 'bestaudio[ext=m4a][abr<=192]/bestaudio[ext=m4a][abr<=192]',
            'normal': 'bestaudio[ext=m4a][abr<=128]/bestaudio[ext=m4a][abr<=128]'
        }
        
        ydl_opts = {
            "format": quality_formats.get(quality, 'bestaudio[ext=m4a]/bestaudio[ext=m4a]'),
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(info)
            
            output_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(audio_path))[0] + '.mp3')
            
            try:
                audio = AudioFileClip(audio_path)
                bitrates = {'best': 320, 'good': 192, 'normal': 128}
                
                audio.write_audiofile(
                    output_path,
                    bitrate=f"{bitrates.get(quality, 320)}k",
                    codec='libmp3lame'
                )
                
                audio.close()
                os.remove(audio_path)
                
                if not os.path.exists(output_path):
                    raise Exception("MP3 file was not created successfully")
                
                return output_path
                
            except Exception as e:
                raise Exception(f"Audio conversion failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error downloading MP3: {str(e)}")
        raise
    finally:
        if output_path and not os.path.exists(output_path):
            try:
                for file in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, file))
                    except Exception as e:
                        logger.error(f"Error cleaning up file: {str(e)}")
                os.rmdir(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory: {str(e)}")

@app.route("/")
def index():
    return render_template("Index.html")

@app.route("/youtube-to-mp3")
def youtube_to_mp3():
    return render_template("youtube_to_mp3.html")

@app.route("/youtube-to-video")
def youtube_to_video():
    return render_template("youtube_to_video.html")

@app.route("/get-formats", methods=["POST"])
def get_formats():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        info = get_video_info(url)
        if "error" in info:
            return jsonify({"error": info["error"]}), 400
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting formats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format_id")
    merge_audio = request.form.get("merge_audio") == "true"
    format_type = request.form.get("format")
    quality = request.form.get("quality")
    
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    
    try:
        if format_type == "mp3":
            if not quality:
                return jsonify({"error": "Missing quality parameter"}), 400
            try:
                file_path = download_mp3(url, quality)
            except Exception as e:
                if "Audio conversion failed" in str(e):
                    return jsonify({
                        "error": "Failed to convert audio. Please try a different quality option.",
                        "requires_ffmpeg": False
                    }), 400
                raise
        else:
            if not format_id:
                return jsonify({"error": "Missing format ID"}), 400
            file_path = download_video(url, format_id, merge_audio)
        
        if not os.path.exists(file_path):
            raise Exception("Downloaded file not found")
            
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
        
        # Clean up the file after sending
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                temp_dir = os.path.dirname(file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up file: {str(e)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in download: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
