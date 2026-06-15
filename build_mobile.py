# -*- coding: utf-8 -*-
"""
打包腳本：把 index.html + data/*.js 內聯成「單一檔」手機版 (JP_mobile.html)。
- 只「讀取」現有檔案，不修改任何既有檔。
- 輸出是一個全新的自包含 HTML：無外部載入，手機直接點開即可，離線可用。
- 附帶 PWA manifest / 圖示 / meta，讓「加入主畫面」更像 App（自動安裝橫幅需 https 才會觸發）。

用法：在 JP 資料夾執行  python build_mobile.py
之後若有更新內容，重新跑一次即可重新產生。
"""
import os, re, json
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "index.html")
OUT  = os.path.join(HERE, "JP_mobile.html")

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

html = read(SRC)

# ---- 1) 把每個 <script src="data/xxx.js"></script> 換成內聯內容 ----
inlined = {"count": 0, "bytes": 0}
def inline_script(m):
    rel = m.group(1)                       # 例如 data/day01.js
    path = os.path.join(HERE, rel.replace("/", os.sep))
    if not os.path.exists(path):
        return m.group(0)                  # 找不到就原樣保留
    code = read(path)
    inlined["count"] += 1
    inlined["bytes"] += len(code.encode("utf-8"))
    # 避免極少數情況下 JS 內含 </script> 字串提前結束標籤
    code = code.replace("</script>", "<\\/script>")
    return "<script>\n/* === inlined: %s === */\n%s\n</script>" % (rel, code)

html = re.sub(r'<script src="(data/[^"]+\.js)"></script>', inline_script, html)

# ---- 2) PWA 圖示（SVG，內嵌為 data URI）----
icon_svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#3b6ef5"/><stop offset="1" stop-color="#7c4df0"/>'
    '</linearGradient></defs>'
    '<rect width="512" height="512" rx="110" fill="url(#g)"/>'
    '<text x="256" y="352" font-size="300" text-anchor="middle" fill="#fff" '
    'font-family="Segoe UI,Meiryo,sans-serif" font-weight="bold">あ</text>'
    '</svg>'
)
icon_uri = "data:image/svg+xml," + quote(icon_svg, safe="")

manifest = {
    "name": "日語 N5→N3 完全特訓",
    "short_name": "日語特訓",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f4f6fb",
    "theme_color": "#3b6ef5",
    "icons": [{"src": icon_uri, "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
}
manifest_uri = "data:application/manifest+json," + quote(json.dumps(manifest, ensure_ascii=False), safe="")

head_inject = (
    '\n<meta name="apple-mobile-web-app-capable" content="yes">'
    '\n<meta name="mobile-web-app-capable" content="yes">'
    '\n<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
    '\n<meta name="apple-mobile-web-app-title" content="日語特訓">'
    '\n<meta name="theme-color" content="#3b6ef5">'
    '\n<link rel="apple-touch-icon" href="%s">'
    '\n<link rel="icon" href="%s">'
    '\n<link rel="manifest" href="%s">'
    "\n</head>"
) % (icon_uri, icon_uri, manifest_uri)

html = html.replace("</head>", head_inject, 1)

# ---- 3) 安裝提示 / beforeinstallprompt（只加在手機版輸出檔）----
install_js = r"""
<script>
(function(){
  // (A) 線上(https)時：捕捉自動安裝事件，顯示「安裝到主畫面」浮鈕
  var deferred=null;
  window.addEventListener('beforeinstallprompt', function(e){
    e.preventDefault(); deferred=e;
    if(document.getElementById('pwaInstallBtn')) return;
    var b=document.createElement('button');
    b.id='pwaInstallBtn'; b.textContent='📲 安裝到主畫面';
    b.style.cssText='position:fixed;right:14px;bottom:14px;z-index:10050;border:none;border-radius:999px;padding:12px 18px;font-size:15px;font-weight:700;color:#fff;background:linear-gradient(90deg,#3b6ef5,#7c4df0);box-shadow:0 8px 24px rgba(60,40,120,.35);cursor:pointer;font-family:inherit';
    b.onclick=async function(){ if(deferred){ deferred.prompt(); await deferred.userChoice; deferred=null; b.remove(); } };
    document.body.appendChild(b);
  });
  // (B) 本機/離線開啟時：第一次給一條「加入主畫面」教學（可關，記住不再顯示）
  function isStandalone(){
    return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone===true;
  }
  window.addEventListener('load', function(){
    setTimeout(function(){
      if(isStandalone()) return;
      try{ if(localStorage.getItem('pwaTipDismissed')==='1') return; }catch(e){}
      var ua=navigator.userAgent||'';
      var ios=/iPhone|iPad|iPod/i.test(ua);
      var tip=document.createElement('div');
      tip.style.cssText='position:fixed;left:10px;right:10px;bottom:10px;z-index:10050;background:#22283a;color:#fff;border-radius:14px;padding:13px 15px;font-size:13.5px;line-height:1.7;box-shadow:0 10px 40px rgba(0,0,0,.35);font-family:inherit';
      tip.innerHTML='📲 想像 App 一樣使用？'
        + (ios
            ? '點下方 Safari 的「分享」↑ →「加入主畫面」。'
            : 'Chrome 右上角「⋮」→「加到主畫面」。')
        + ' <span id="pwaTipX" style="color:#ffd56b;text-decoration:underline;cursor:pointer;white-space:nowrap;margin-left:6px">知道了</span>';
      document.body.appendChild(tip);
      document.getElementById('pwaTipX').onclick=function(){ try{localStorage.setItem('pwaTipDismissed','1');}catch(e){} tip.remove(); };
    }, 1200);
  });
})();
</script>
</body>"""
html = html.replace("</body>", install_js, 1)

# ---- 4) 標題小註記，方便辨識這是手機版 ----
html = html.replace("<title>", "<!-- 自動產生的單一檔手機版，請勿手動編輯；改內容請改 data/ 後重跑 build_mobile.py -->\n<title>", 1)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("OK -> %s" % OUT)
print("inlined data files : %d" % inlined["count"])
print("inlined data size  : %.1f KB" % (inlined["bytes"]/1024))
print("output file size   : %.1f KB" % (len(html.encode("utf-8"))/1024))
