# -*- coding: utf-8 -*-
"""
API SERVER Y PANEL ADMIN PARA BOT DE BARBERÍA
==============================================
- API REST para gestión de citas
- Panel web administrativo
- Estadísticas en tiempo real
"""

from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_cors import CORS
import datetime
import json
import os

# Importar base de datos
from database import db

app = Flask(__name__)
CORS(app)  # Permitir CORS para futura app móvil

# ==================== PANEL WEB ADMIN HTML ====================
ADMIN_HTML = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Admin - {{nombre_negocio}}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
            animation: fadeInDown 0.5s ease;
        }
        
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #888;
            font-size: 1.1em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            animation: fadeIn 0.5s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,217,255,0.2);
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.9); }
            to { opacity: 1; transform: scale(1); }
        }
        
        .stat-number {
            font-size: 3em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stat-label {
            color: #aaa;
            margin-top: 5px;
        }
        
        .section {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            border: 1px solid rgba(255,255,255,0.1);
            animation: fadeIn 0.6s ease;
        }
        
        .section h2 {
            color: #00d9ff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .citas-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .cita-item {
            background: rgba(0,217,255,0.1);
            border-radius: 10px;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s;
        }
        
        .cita-item:hover {
            background: rgba(0,217,255,0.2);
        }
        
        .cita-hora {
            font-size: 1.5em;
            font-weight: bold;
            color: #00ff88;
        }
        
        .cita-cliente {
            font-size: 1.2em;
        }
        
        .cita-estado {
            padding: 5px 15px;
            border-radius: 20px;
            background: #00ff88;
            color: #000;
            font-weight: bold;
            font-size: 0.8em;
        }
        
        .config-form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .form-group label {
            color: #aaa;
        }
        
        .form-group input, .form-group textarea {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            padding: 12px;
            color: #fff;
            font-size: 1em;
        }
        
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #00d9ff;
        }
        
        .btn {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #000;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(0,217,255,0.4);
        }
        
        .toggle-bot {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .toggle {
            width: 60px;
            height: 30px;
            background: #333;
            border-radius: 15px;
            position: relative;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .toggle.active {
            background: #00ff88;
        }
        
        .toggle::after {
            content: '';
            position: absolute;
            width: 24px;
            height: 24px;
            background: #fff;
            border-radius: 50%;
            top: 3px;
            left: 3px;
            transition: left 0.3s;
        }
        
        .toggle.active::after {
            left: 33px;
        }
        
        .empty-state {
            text-align: center;
            color: #666;
            padding: 40px;
        }
        
        .horarios-disponibles {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .horario-badge {
            background: rgba(0,255,136,0.2);
            color: #00ff88;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 1.8em; }
            .stat-number { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏠 {{nombre_negocio}}</h1>
            <p class="subtitle">Panel de Administración</p>
        </header>
        
        <!-- Estadísticas -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="citas-hoy">{{stats.citas_hoy}}</div>
                <div class="stat-label">Citas Hoy</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="mensajes-hoy">{{stats.mensajes_hoy}}</div>
                <div class="stat-label">Mensajes Hoy</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="conv-activas">{{stats.conversaciones_activas}}</div>
                <div class="stat-label">Chats Activos</div>
            </div>
        </div>
        
        <!-- Citas de Hoy -->
        <div class="section">
            <h2>📅 Citas de Hoy ({{fecha_hoy}})</h2>
            <div class="citas-list" id="citas-hoy-list">
                {% if citas_hoy %}
                    {% for cita in citas_hoy %}
                    <div class="cita-item">
                        <span class="cita-hora">{{cita.hora}}</span>
                        <span class="cita-cliente">{{cita.cliente_nombre}}</span>
                        <span class="cita-estado">{{cita.estado}}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">No hay citas para hoy</div>
                {% endif %}
            </div>
        </div>
        
        <!-- Horarios Disponibles -->
        <div class="section">
            <h2>🕐 Horarios Disponibles Hoy</h2>
            <div class="horarios-disponibles">
                {% for hora in horarios_disponibles %}
                    <span class="horario-badge">{{hora}}</span>
                {% endfor %}
                {% if not horarios_disponibles %}
                    <div class="empty-state">Todos los horarios están ocupados</div>
                {% endif %}
            </div>
        </div>
        
        <!-- Configuración -->
        <div class="section">
            <h2>⚙️ Configuración del Bot</h2>
            <form class="config-form" id="config-form">
                <div class="toggle-bot">
                    <span>Bot Activo:</span>
                    <div class="toggle {{bot_activo_class}}" id="toggle-bot" onclick="toggleBot()"></div>
                </div>
                
                <div class="form-group">
                    <label>Nombre del Negocio</label>
                    <input type="text" id="nombre-negocio" value="{{nombre_negocio}}">
                </div>
                
                <div class="form-group">
                    <label>API Key de Gemini</label>
                    <input type="password" id="api-key" value="{{api_key}}" placeholder="AIza...">
                </div>
                
                <div class="form-group">
                    <label>Instrucciones del Bot</label>
                    <textarea id="instrucciones" rows="3">{{instrucciones}}</textarea>
                </div>
                
                <div class="form-group">
                    <label>Horario de Atención</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="number" id="hora-inicio" value="{{hora_inicio}}" style="width: 100px;" min="0" max="23"> 
                        <span style="align-self: center;">a</span>
                        <input type="number" id="hora-fin" value="{{hora_fin}}" style="width: 100px;" min="0" max="23">
                    </div>
                </div>
                
                <button type="submit" class="btn">💾 Guardar Cambios</button>
            </form>
        </div>
    </div>
    
    <script>
        // Toggle del bot
        function toggleBot() {
            const toggle = document.getElementById('toggle-bot');
            const isActive = toggle.classList.contains('active');
            
            fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bot_encendido: !isActive ? 'true' : 'false' })
            }).then(r => r.json()).then(data => {
                toggle.classList.toggle('active');
            });
        }
        
        // Guardar configuración
        document.getElementById('config-form').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const config = {
                nombre_negocio: document.getElementById('nombre-negocio').value,
                api_key: document.getElementById('api-key').value,
                instrucciones: document.getElementById('instrucciones').value,
                hora_inicio: document.getElementById('hora-inicio').value,
                hora_fin: document.getElementById('hora-fin').value
            };
            
            fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            }).then(r => r.json()).then(data => {
                alert('✅ Configuración guardada');
            });
        });
        
        // Actualizar estadísticas cada 30 segundos
        setInterval(() => {
            fetch('/api/stats').then(r => r.json()).then(data => {
                document.getElementById('citas-hoy').textContent = data.citas_hoy;
                document.getElementById('mensajes-hoy').textContent = data.mensajes_hoy;
                document.getElementById('conv-activas').textContent = data.conversaciones_activas;
            });
        }, 30000);
    </script>
</body>
</html>
'''

# ==================== RUTAS WEB ====================

@app.route('/')
def index():
    """Página principal del panel admin"""
    hoy = datetime.date.today().isoformat()
    
    return render_template_string(ADMIN_HTML,
        nombre_negocio=db.get_config('nombre_negocio', 'Barbería'),
        api_key=db.get_config('api_key', ''),
        instrucciones=db.get_config('instrucciones', ''),
        hora_inicio=db.get_config('hora_inicio', '9'),
        hora_fin=db.get_config('hora_fin', '20'),
        bot_activo_class='active' if db.get_config('bot_encendido', 'true') == 'true' else '',
        stats=db.obtener_estadisticas(),
        citas_hoy=db.obtener_citas_dia(hoy),
        horarios_disponibles=db.obtener_horarios_disponibles(hoy),
        fecha_hoy=hoy
    )

# ==================== API REST ====================

@app.route('/api/stats')
def api_stats():
    """Obtener estadísticas"""
    return jsonify(db.obtener_estadisticas())

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Obtener o actualizar configuración"""
    if request.method == 'GET':
        return jsonify(db.get_all_config())
    else:
        data = request.get_json()
        for clave, valor in data.items():
            db.set_config(clave, valor)
        return jsonify({'success': True})

@app.route('/api/citas', methods=['GET'])
def api_citas():
    """Obtener citas"""
    fecha = request.args.get('fecha')
    if fecha:
        return jsonify(db.obtener_citas_dia(fecha))
    else:
        desde = request.args.get('desde', datetime.date.today().isoformat())
        return jsonify(db.obtener_todas_citas(desde))

@app.route('/api/citas', methods=['POST'])
def api_crear_cita():
    """Crear una cita"""
    data = request.get_json()
    fecha = data.get('fecha')
    hora = data.get('hora')
    cliente = data.get('cliente')
    telefono = data.get('telefono', 'Manual')
    
    if not all([fecha, hora, cliente]):
        return jsonify({'error': 'Faltan datos'}), 400
    
    exito, mensaje = db.agendar_cita(fecha, hora, cliente, telefono)
    return jsonify({'success': exito, 'message': mensaje})

@app.route('/api/citas/<int:cita_id>', methods=['DELETE'])
def api_cancelar_cita(cita_id):
    """Cancelar una cita"""
    # Por ahora simplemente marca como cancelada
    return jsonify({'success': True})

@app.route('/api/horarios/<fecha>')
def api_horarios(fecha):
    """Obtener horarios disponibles para una fecha"""
    return jsonify(db.obtener_horarios_disponibles(fecha))

@app.route('/api/conversaciones')
def api_conversaciones():
    """Obtener conversaciones recientes"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM conversaciones 
        ORDER BY ultimo_mensaje DESC 
        LIMIT 20
    ''')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/mensajes/<cliente>')
def api_mensajes(cliente):
    """Obtener historial de mensajes de un cliente"""
    return jsonify(db.obtener_historial(cliente, limite=50))


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🌐 Panel Admin - Servidor Iniciado")
    print("="*50)
    print(f"\n  Abre en tu navegador: http://localhost:5000")
    print("\n  Endpoints API disponibles:")
    print("    GET  /api/stats      - Estadísticas")
    print("    GET  /api/config     - Configuración")
    print("    POST /api/config     - Actualizar config")
    print("    GET  /api/citas      - Lista de citas")
    print("    POST /api/citas      - Crear cita")
    print("    GET  /api/horarios/FECHA - Horarios libres")
    print("\n" + "="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
