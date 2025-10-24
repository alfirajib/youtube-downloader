from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import yt_dlp
import os
import uuid
import shutil
from threading import Thread
import time

app = Flask(__name__, static_folder='static', template_folder='static')
CORS(app)

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Dictionary untuk tracking download status
download_status = {}

def cleanup_old_files():
    """Hapus file yang lebih dari 1 jam"""
    while True:
        try:
            for filename in os.listdir(DOWNLOAD_FOLDER):
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    if time.time() - os.path.getmtime(filepath) > 3600:  # 1 jam
                        os.remove(filepath)
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(600)  # Jalankan setiap 10 menit

# Mulai cleanup thread
cleanup_thread = Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_video_info():
    """Ambil informasi video dari URL"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL tidak boleh kosong'}), 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return jsonify({
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown')
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download_video():
    """Download video atau audio"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        format_type = data.get('format', 'mp4')  # mp4 atau mp3
        
        if not url:
            return jsonify({'error': 'URL tidak boleh kosong'}), 400
        
        # Generate unique ID untuk download ini
        download_id = str(uuid.uuid4())
        download_status[download_id] = {'status': 'processing', 'progress': 0}
        
        # Progress hook
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent = d.get('_percent_str', '0%').strip().replace('%', '')
                    download_status[download_id]['progress'] = float(percent)
                except:
                    pass
            elif d['status'] == 'finished':
                download_status[download_id]['status'] = 'completed'
                download_status[download_id]['progress'] = 100
        
        # Konfigurasi yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{download_id}.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
        
        if format_type == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            file_ext = 'mp3'
        else:  # mp4
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
            file_ext = 'mp4'
        
        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = f"{download_id}.{file_ext}"
            
        download_status[download_id]['status'] = 'completed'
        download_status[download_id]['filename'] = filename
        
        return jsonify({
            'download_id': download_id,
            'filename': filename,
            'title': info.get('title', 'Unknown')
        })
    
    except Exception as e:
        if download_id in download_status:
            download_status[download_id]['status'] = 'error'
            download_status[download_id]['error'] = str(e)
        return jsonify({'error': str(e)}), 400

@app.route('/api/progress/<download_id>')
def get_progress(download_id):
    """Cek progress download"""
    if download_id in download_status:
        return jsonify(download_status[download_id])
    return jsonify({'error': 'Download ID tidak ditemukan'}), 404

@app.route('/api/file/<filename>')
def download_file(filename):
    """Serve file untuk didownload"""
    try:
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        return jsonify({'error': 'File tidak ditemukan'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)