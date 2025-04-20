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
    .video { display: flex; align-items: center; gap: 15px; margin-bottom: 15px; border-bottom: 1px solid #eee; 
             padding-bottom: 15px; }
    .thumbnail { width: 120px; height: 80px; border-radius: 6px; object-fit: cover; }
    .info { flex: 1; display: flex; flex-direction: column; justify-content: center; }
    .info strong { font-size: 16px; color: #333; }
    .info em { font-size: 12px; color: #555; margin-bottom: 6px; }
    .buttons { display: flex; gap: 10px; margin-top: 10px; }
    .buttons button { font-size: 14px; padding: 6px 12px; border-radius: 6px; }
    .search-status { font-style: italic; color: #555; font-size: 16px;
                     animation: pulse 1.2s infinite; margin-top: 10px; }
    @keyframes pulse { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }
    .suggestions { border: 1px solid #ccc; padding: 15px; border-radius: 8px;
                   background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 25px;
                   max-height: 300px; overflow-y: auto; }
    .suggestions div { padding: 8px; cursor: pointer; }
    .suggestions div:hover { background: #f1f1f1; }
    .random-suggestions { 
      border: 1px solid #ccc; 
      padding: 15px; 
      border-radius: 8px;
      background: #fff; 
      box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
      margin-top: 25px;
      max-height: none;
      overflow-y: auto; 
    }
    #random-suggestions h2 { text-align: center; color: #333; margin-bottom: 15px; font-size: 24px; }
    .suggestion-video { 
      display: flex; 
      align-items: center; 
      gap: 12px; 
      margin-bottom: 12px; 
      padding: 10px; 
      border-bottom: 1px solid #eee; 
    }
    .suggestion-video:hover { background: #f9f9f9; }
    .suggestion-thumbnail { width: 120px; height: 80px; border-radius: 6px; object-fit: cover; }
    #load-more-btn { display: block; margin: 15px auto; padding: 10px 20px; font-size: 16px;
                     background: #28a745; color: white; border: none; border-radius: 6px; cursor: pointer; }
    #load-more-btn:hover { background: #218838; }
  </style>
</head>
<body>
  <div class="container">
    <h1>YouTube Downloader</h1>
    <input type="text" id="query" placeholder="Masukkan judul atau link YouTube..." oninput="suggest()" />
    <button onclick="search()">Cari</button>

    <div id="suggestions" class="suggestions" style="display:none;"></div>
    <div id="results"></div>

    <div class="random-suggestions" id="random-suggestions" style="display: none;">
      <h2>Video Saran</h2>
      <div id="random-video-container"></div>
      <button id="load-more-btn" onclick="showAllSuggestions()" style="display:none;">Tampilkan Semua</button>
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
      document.getElementById('random-suggestions').style.display = 'none'; // Hide suggestions during search
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (!res.ok) return resDiv.innerHTML = `<p>Error: ${data.error}</p>`;
        resDiv.innerHTML = '';
        data.forEach(v => {
          const dv = document.createElement('div'); dv.className = 'video';
          dv.innerHTML = `
            <img class="thumbnail" src="${v.thumbnail}" />
            <div class="info"> 
              <strong>${v.title}</strong>
              <em>${v.author}</em>
              <div class="buttons">
                <button onclick="download('${v.url}','mp3')">MP3</button>
                <button onclick="download('${v.url}','mp4')">MP4</button>
              </div>
            </div>`;
          resDiv.appendChild(dv);
        });
      } catch (e) { resDiv.innerHTML = `<p>Error: ${e.message}</p>`; }
    }
    function download(url, fmt) {
      const a = document.createElement('a');
      a.href = `/api/download?url=${encodeURIComponent(url)}&format=${fmt}`;
      a.click();
    }

    let randomVideos = [];
    async function loadRandomSuggestions() {
      const rndDiv = document.getElementById('random-video-container');
      try {
        const res = await fetch('/api/random_suggestions');
        const data = await res.json();
        if (!res.ok) { rndDiv.innerHTML = '<p>Gagal memuat saran.</p>'; return; }
        randomVideos = data;
        renderRandom(randomVideos.length);
        document.getElementById('load-more-btn').style.display = 'none';
      } catch {
        rndDiv.innerHTML = '<p>Error loading suggestions.</p>';
      }
    }
    function renderRandom(count) {
      const rndDiv = document.getElementById('random-video-container');
      rndDiv.innerHTML = '';
      randomVideos.slice(0, count).forEach(v => {
        const dv = document.createElement('div'); dv.className = 'suggestion-video';
        dv.innerHTML = `
          <img class="suggestion-thumbnail" src="${v.thumbnail}" />
          <div class="suggestion-info"> 
            <strong>${v.title}</strong>
            <em>${v.author}</em>
            <div class="buttons">
              <button onclick="download('${v.url}','mp3')">MP3</button>
              <button onclick="download('${v.url}','mp4')">MP4</button>
            </div>
          </div>`;
        rndDiv.appendChild(dv);
      });
    }
    function showAllSuggestions() {
      renderRandom(randomVideos.length);
      document.getElementById('load-more-btn').style.display = 'none';
    }

    window.onload = () => {
      loadRandomSuggestions();
      document.getElementById('random-suggestions').style.display = 'block'; // Show on homepage
    };
  </script>
</body>
</html>
'''

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/suggest')
def suggest():
    q = request.args.get('q')
    if not q: return jsonify({ 'error': "Parameter 'q' diperlukan" }), 400
    try:
        ydl_opts = { 'quiet': True, 'extract_flat': 'in_playlist', 'default_search': 'ytsearch5:' }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(q, download=False)
            titles = [e.get('title','') for e in info.get('entries',[]) if e]
        return jsonify(titles)
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500

@app.route('/api/random_suggestions')
def random_suggestions():
    try:
        query = 'music'
        ydl_opts = { 'quiet': True, 'extract_flat': 'in_playlist', 'default_search': 'ytsearch10:' }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries',[]) or []
            results = [
                {'id': v.get('id'), 'title': v.get('title','Tanpa judul'),
                 'url': v.get('url'), 'thumbnail': v.get('thumbnails',[{}])[-1].get('url'),
                 'author': v.get('uploader','Unknown')} for v in entries if v
            ]
        random.shuffle(results)
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error random: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search():
    q = request.args.get('q')
    if not q: return jsonify({ 'error': "Parameter 'q' diperlukan" }), 400
    try:
        app.logger.info(f"Mencari video: {q}")
        ydl_opts = { 'quiet': True, 'extract_flat': 'in_playlist', 'default_search': 'ytsearch10:' }
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
        return jsonify({ 'error': str(e) }), 500

@app.route('/api/download')
def download_file():
    url = request.args.get('url')
    fmt = request.args.get('format','mp4')
    if not url: return jsonify({ 'error': "Parameter 'url' diperlukan" }), 400
    try:
        app.logger.info(f"Downloading: {url} as {fmt}")
        ydl_opts = {
            'format': 'bestaudio/best' if fmt=='mp3' else 'best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'quiet': True,
            'postprocessors': [{ 'key':'FFmpegExtractAudio','preferredcodec':'mp3' }] if fmt=='mp3' else []
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt=='mp3': filename = filename.rsplit('.',1)[0] + '.mp3'
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)
