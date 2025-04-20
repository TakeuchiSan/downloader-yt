from flask import Flask, jsonify, request, send_file, render_template_string
from yt_dlp import YoutubeDL
import os, logging, random

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>YouTube MP3/MP4 Downloader</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
    .container { max-width: 900px; margin: auto; background: #fff; padding: 30px; border-radius: 12px;
                 box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    h1 { text-align: center; margin-bottom: 20px; color: #333; }
    input[type="text"] { width: 100%; box-sizing: border-box; padding: 15px; font-size: 16px;
                           border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px; }
    button { padding: 12px 20px; font-size: 14px; margin: 10px 5px 15px 0; border: none; border-radius: 8px;
             background-color: #007bff; color: white; cursor: pointer; }
    button:hover { background-color: #0056b3; }
    .search-status { font-style: italic; color: #555; font-size: 16px;
                     animation: pulse 1.2s infinite; margin-top: 10px; }
    @keyframes pulse { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }
    .suggestions { border: 1px solid #ccc; padding: 15px; border-radius: 8px;
                   background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 25px;
                   max-height: 300px; overflow-y: auto; }
    .suggestions div { padding: 8px; cursor: pointer; }
    .suggestions div:hover { background: #f1f1f1; }

    .video-suggestions, .search-results { margin-top: 30px; }
    .video-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 15px;
      margin-top: 15px;
    }
    .suggestion-card {
      border: 1px solid #eee;
      border-radius: 8px;
      overflow: hidden;
      transition: transform 0.2s;
    }
    .suggestion-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .suggestion-thumbnail {
      width: 100%;
      height: 140px;
      object-fit: cover;
    }
    .suggestion-details {
      padding: 12px;
    }
    .suggestion-title {
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 5px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .suggestion-author {
      font-size: 12px;
      color: #666;
      margin-bottom: 8px;
    }
    .suggestion-buttons {
      display: flex;
      gap: 8px;
    }
    .suggestion-buttons button {
      flex: 1;
      padding: 5px;
      font-size: 12px;
    }
    .contact-section {
      margin-top: 40px;
      padding: 25px;
      background: #f8f9fa;
      border-radius: 10px;
    }
    .contact-title {
      font-size: 18px;
      margin-bottom: 15px;
      color: #333;
      font-weight: 600;
      text-align: center;
    }
    .contact-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
    }
    .contact-card {
      padding: 15px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .contact-icon {
      font-size: 24px;
      margin-bottom: 10px;
      color: #007bff;
      text-align: center;
    }
    .contact-label, .contact-value {
      text-align: center;
    }
    .contact-label {
      font-size: 14px;
      color: #666;
      margin-bottom: 5px;
    }
    .contact-value {
      font-size: 16px;
      font-weight: 500;
      color: #333;
    }
    .contact-link {
      color: inherit;
      text-decoration: none;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>YouTube Downloader</h1>
    <input type="text" id="query" placeholder="Masukkan judul atau link YouTube..." oninput="suggest()" />
    <button onclick="search()">Cari</button>

    <div id="suggestions" class="suggestions" style="display:none;"></div>
    <div class="search-results" id="results"></div>

    <div class="video-suggestions">
      <div class="video-grid" id="random-video-container"></div>
    </div>

    <div class="contact-section">
      <div class="contact-title">Kontak Kami</div>
      <div class="contact-grid">
        <div class="contact-card">
          <div class="contact-icon"><i class="fab fa-whatsapp"></i></div>
          <div class="contact-label">WhatsApp</div>
          <div class="contact-value">
            <a href="https://wa.me/6283139749414" class="contact-link" target="_blank">+62-831-3974-9414</a>
          </div>
        </div>
        <div class="contact-card">
          <div class="contact-icon"><i class="fas fa-envelope"></i></div>
          <div class="contact-label">Email</div>
          <div class="contact-value">
            <a href="mailto:suppytdownloder@gmail.com" class="contact-link">suppytdownloder@gmail.com</a>
          </div>
        </div>
        <div class="contact-card">
          <div class="contact-icon"><i class="fab fa-instagram"></i></div>
          <div class="contact-label">Instagram</div>
          <div class="contact-value">
            <a href="https://instagram.com/kalll_kall" class="contact-link" target="_blank">@kalll_kall</a>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
  let suggestTimeout;
  function suggest() {
    clearTimeout(suggestTimeout);
    const q = document.getElementById('query').value;
    const sugDiv = document.getElementById('suggestions');
    if (q.length < 3) { sugDiv.style.display = 'none'; return; }
    suggestTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (res.ok) {
          sugDiv.innerHTML = data.map(item => `<div onclick="pickSuggest('${item.replace(/'/g, "\\'")}')">${item}</div>`).join('');
          sugDiv.style.display = 'block';
        }
      } catch (e) { console.error(e); }
    }, 300);
  }

  function pickSuggest(val) {
    document.getElementById('query').value = val;
    document.getElementById('suggestions').style.display = 'none';
    search();
  }

  async function search() {
    document.getElementById('suggestions').style.display = 'none';
    const q = document.getElementById('query').value;
    const resDiv = document.getElementById('results');
    resDiv.innerHTML = '<p class="search-status">Mencari...</p>';
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (!res.ok) return resDiv.innerHTML = `<p>Error: ${data.error}</p>`;
      resDiv.innerHTML = '<div class="video-grid" id="search-results-grid"></div>';
      const grid = document.getElementById('search-results-grid');
      data.forEach(video => {
        const card = document.createElement('div');
        card.className = 'suggestion-card';
        card.innerHTML = `
          <img class="suggestion-thumbnail" src="${video.thumbnail}" />
          <div class="suggestion-details">
            <div class="suggestion-title">${video.title}</div>
            <div class="suggestion-author">${video.author}</div>
            <div class="suggestion-buttons">
              <button onclick="download('${video.url}','mp3')">MP3</button>
              <button onclick="download('${video.url}','mp4')">MP4</button>
            </div>
          </div>`;
        grid.appendChild(card);
      });
    } catch (e) { resDiv.innerHTML = `<p>Error: ${e.message}</p>`; }
  }

  function download(url, fmt) {
    const a = document.createElement('a');
    a.href = `/api/download?url=${encodeURIComponent(url)}&format=${fmt}`;
    a.click();
  }

  async function loadRandomSuggestions() {
    const container = document.getElementById('random-video-container');
    try {
      const res = await fetch('/api/random_suggestions');
      const data = await res.json();
      if (!res.ok) return;
      container.innerHTML = '';
      data.forEach(video => {
        const card = document.createElement('div');
        card.className = 'suggestion-card';
        card.innerHTML = `
          <img class="suggestion-thumbnail" src="${video.thumbnail}" />
          <div class="suggestion-details">
            <div class="suggestion-title">${video.title}</div>
            <div class="suggestion-author">${video.author}</div>
            <div class="suggestion-buttons">
              <button onclick="download('${video.url}','mp3')">MP3</button>
              <button onclick="download('${video.url}','mp4')">MP4</button>
            </div>
          </div>`;
        container.appendChild(card);
      });
    } catch (e) {
      console.error('Error loading suggestions:', e);
    }
  }

  window.onload = loadRandomSuggestions;
</script>
</body>
</html>
'''

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/suggest')
def suggest():
    q = request.args.get('q')
    if not q: return jsonify({'error': "Parameter 'q' diperlukan"}), 400
    try:
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'default_search': 'ytsearch5:'}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(q, download=False)
            titles = [e.get('title','') for e in info.get('entries',[]) if e]
        return jsonify(titles)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/random_suggestions')
def random_suggestions():
    try:
        query = 'music'
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'default_search': 'ytsearch50:'}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries',[]) or []
            results = [
                {'id': v.get('id'), 'title': v.get('title','Tanpa judul'),
                 'url': v.get('url'), 'thumbnail': v.get('thumbnails',[{}])[-1].get('url'),
                 'author': v.get('uploader','Unknown')} for v in entries if v
            ]
        random.shuffle(results)
        return jsonify(results[:12])
    except Exception as e:
        app.logger.error(f"Error random: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search():
    q = request.args.get('q')
    if not q: return jsonify({'error': "Parameter 'q' diperlukan"}), 400
    try:
        app.logger.info(f"Mencari video: {q}")
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'default_search': 'ytsearch100:'}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(q, download=False)
            entries = info.get('entries',[]) or []
            results = [
                {'id': v.get('id'), 'title': v.get('title','Tanpa judul'),
                 'url': v.get('url'), 'thumbnail': v.get('thumbnails',[{}])[-1].get('url'),
                 'author': v.get('uploader','Unknown')} for v in entries if v
            ]
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download')
def download_file():
    url = request.args.get('url')
    fmt = request.args.get('format','mp4')
    if not url: return jsonify({'error': "Parameter 'url' diperlukan"}), 400
    
    # Cek apakah URL valid (YouTube)
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'error': "URL tidak valid (harus dari YouTube)"}), 400
    
    try:
        app.logger.info(f"Downloading: {url} as {fmt}")
        ydl_opts = {
            'format': 'bestaudio/best' if fmt == 'mp3' else 'best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'quiet': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if fmt == 'mp3' else []
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt == 'mp3':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)
