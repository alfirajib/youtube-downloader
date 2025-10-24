from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import os
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

# Base yt-dlp options untuk bypass bot detection
# Base yt-dlp options untuk bypass bot detection
def get_base_ydl_opts():
    return {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'best',
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    }
    

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
        
        ydl_opts = get_base_ydl_opts()
        
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
        format_type = data.get('format', 'mp4')
        
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
        
        # Konfigurasi yt-dlp dengan anti-bot measures
        ydl_opts = get_base_ydl_opts()
        ydl_opts.update({
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{download_id}.%(ext)s'),
            'progress_hooks': [progress_hook],
        })
        
        if format_type == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            file_ext = 'mp3'
        else:  # mp4
            # Gunakan format yang lebih sederhana untuk menghindari 403
            ydl_opts['format'] = 'best[height<=720]/best'
            file_ext = 'mp4'
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