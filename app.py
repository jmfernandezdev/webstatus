from flask import Flask, render_template
import requests
import time
from datetime import datetime
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os

app = Flask(__name__)

class WebsiteMonitor:
    def __init__(self, urls):
        self.urls = urls
        self.status_history = {}
        self.metrics = {}  # Almacena métricas de tiempo
        self.screenshots = {}  # Almacena rutas de capturas
        
    def capture_screenshot(self, url):
        """Captura screenshot usando Selenium"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            driver = webdriver.Chrome(options=chrome_options)
            
            driver.get(url)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f'static/screenshots/{url.split("//")[1].replace("/","_")}_{timestamp}.png'
            
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            driver.save_screenshot(screenshot_path)
            driver.quit()
            
            return screenshot_path
        except Exception as e:
            print(f"Error capturando screenshot: {str(e)}")
            return None

    def check_website(self, url):
        """Verifica el estado y mide el tiempo"""
        start_time = time.time()
        try:
            response = requests.get(url, timeout=10, verify=True)
            status_code = response.status_code
            elapsed = (time.time() - start_time) * 1000  # Milisegundos
            
            self.metrics[url] = elapsed
            
            if status_code >= 500:
                screenshot = self.capture_screenshot(url)
                self.screenshots[url] = screenshot
                return False, f"Error {status_code}", elapsed
            elif status_code >= 400:
                screenshot = self.capture_screenshot(url)
                self.screenshots[url] = screenshot
                return False, f"Error {status_code}", elapsed
            return True, f"OK - Status {status_code}", elapsed
            
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.metrics[url] = elapsed
            screenshot = self.capture_screenshot(url)
            self.screenshots[url] = screenshot
            return False, f"Error: {str(e)}", elapsed

    def monitor(self):
        """Monitoreo continuo"""
        while True:
            for url in self.urls:
                is_available, message, elapsed = self.check_website(url)
                
                previous_status = self.status_history.get(url, True)
                if is_available != previous_status:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if not is_available:
                        print(f"[{timestamp}] PROBLEMA en {url}: {message}")
                    else:
                        print(f"[{timestamp}] {url} restaurado: {message}")
                    self.status_history[url] = is_available
                
            time.sleep(300)  # 5 minutos

    def get_status(self):
        """Devuelve estado actual para el dashboard"""
        return {
            'urls': self.urls,
            'status': self.status_history,
            'metrics': self.metrics,
            'screenshots': self.screenshots
        }

# Plantilla HTML (guardar como templates/dashboard.html)
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Website Monitor</title>
    <meta charset="UTF-8">
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .status-ok { color: green; }
        .status-error { color: red; }
        .screenshot { max-width: 200px; }
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>Website Monitoring Dashboard</h1>
    <table>
        <tr>
            <th>URL</th>
            <th>Estado</th>
            <th>Tiempo (ms)</th>
            <th>Captura</th>
        </tr>
        {% for url in status['urls'] %}
        <tr>
            <td>{{ url }}</td>
            <td class="{{ 'status-ok' if status['status'].get(url, True) else 'status-error' }}">
                {{ 'OK' if status['status'].get(url, True) else 'ERROR' }}
            </td>
            <td>{{ status['metrics'].get(url, 0)|round(2) }}</td>
            <td>
                {% if status['screenshots'].get(url) %}
                <img src="{{ url_for('static', filename=status['screenshots'][url].split('static/')[1]) }}" 
                     class="screenshot">
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    <p>Última actualización: {{ now }}</p>
</body>
</html>
"""

# Rutas Flask
@app.route('/')
def dashboard():
    status = monitor.get_status()
    return render_template('dashboard.html', 
                         status=status,
                         now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# Iniciar el sistema
if __name__ == "__main__":
    websites = [
        "https://vantag.es",
        "https://turnerja.com",
        "https://legalzone.es"
    ]
    
    monitor = WebsiteMonitor(websites)
    
    # Iniciar monitoreo en thread separado
    monitor_thread = threading.Thread(target=monitor.monitor, daemon=True)
    monitor_thread.start()
    
    # Crear carpeta para capturas si no existe
    os.makedirs('static/screenshots', exist_ok=True)
    
    # Iniciar Flask
    app.run(debug=True, host='0.0.0.0', port=5000)
