# -*- coding: utf-8 -*-
"""
BOT DE WHATSAPP PARA BARBERÍA - VERSIÓN MEJORADA
=================================================
Características:
- Detección robusta de mensajes no leídos
- Historial de conversación por cliente
- Maneja múltiples conversaciones simultáneas
- Base de datos SQLite integrada
- Rotación de modelos Gemini
"""

import time
import datetime
import json
import os
from playwright.sync_api import sync_playwright
import google.generativeai as genai

# Importar base de datos
from database import db

# ==================== CONFIGURACIÓN ====================
# Modelos de Gemini (TODOS los disponibles gratuitamente)
MODELOS_GEMINI = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-flash-001',
    'gemini-1.5-flash-002',
    'gemini-1.5-pro',
    'gemini-1.5-pro-latest',
    'gemini-1.0-pro',
    'gemini-1.0-pro-latest',
    'gemini-1.0-pro-001',
    'gemini-pro',
]

# Respuestas inteligentes predefinidas (fallback cuando IA no disponible)
RESPUESTAS_FALLBACK = {
    'saludo': [
        'hola', 'buenas', 'buen dia', 'buenos dias', 'buenas tardes', 'buenas noches', 'hey', 'hi'
    ],
    'precio': [
        'precio', 'cuanto', 'cuesta', 'cobran', 'vale', 'costo'
    ],
    'horario': [
        'horario', 'hora', 'abren', 'cierran', 'atienden', 'abierto', 'disponible'
    ],
    'cita': [
        'cita', 'turno', 'reservar', 'agendar', 'disponibilidad', 'hueco', 'espacio'
    ],
    'ubicacion': [
        'donde', 'direccion', 'ubicacion', 'llegar', 'queda', 'estan'
    ]
}

def generar_respuesta_fallback(mensaje, nombre_cliente):
    """Genera respuesta inteligente sin usar IA"""
    mensaje_lower = mensaje.lower()
    
    # Detectar tipo de consulta
    for tipo, palabras in RESPUESTAS_FALLBACK.items():
        for palabra in palabras:
            if palabra in mensaje_lower:
                if tipo == 'saludo':
                    return f"Hola {nombre_cliente}! Bienvenido a la barberia. En que te puedo ayudar? Cortes, precios, o agendar cita?"
                elif tipo == 'precio':
                    instrucciones = db.get_config('instrucciones', 'Corte $10')
                    return f"Nuestros precios: {instrucciones}. Te gustaria agendar una cita?"
                elif tipo == 'horario':
                    hora_inicio = db.get_config('hora_inicio', '9')
                    hora_fin = db.get_config('hora_fin', '20')
                    return f"Atendemos de {hora_inicio}:00 a {hora_fin}:00. Quieres que te agende para hoy?"
                elif tipo == 'cita':
                    dia, fecha, hora = obtener_fecha_hora()
                    disponibles = db.obtener_horarios_disponibles(fecha)
                    if disponibles:
                        return f"Para hoy tenemos disponible: {', '.join(disponibles[:5])}. Cual te sirve?"
                    else:
                        return "Hoy estamos llenos. Te puedo agendar para manana?"
                elif tipo == 'ubicacion':
                    return "Estamos en la direccion registrada. Puedes buscarnos en Google Maps o llamar para indicaciones."
    
    # Respuesta generica
    return "Hola! Soy el asistente de la barberia. Te puedo ayudar con: precios, horarios disponibles, o agendar una cita. Que necesitas?"

# Mensajes ya procesados en esta sesión (para no duplicar)
MENSAJES_PROCESADOS = set()

# Control de rate limit
ULTIMO_REQUEST_IA = 0
MIN_DELAY_ENTRE_REQUESTS = 2  # segundos entre requests a la IA

def obtener_fecha_hora():
    """Retorna dia de semana, fecha y hora actual"""
    dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    ahora = datetime.datetime.now()
    return dias[ahora.weekday()], ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M")

def construir_historial_texto(cliente_nombre):
    """Construye el historial de conversación como texto"""
    mensajes = db.obtener_historial(cliente_nombre, limite=10)
    
    if not mensajes:
        return "Sin historial previo."
    
    lineas = []
    for msg in mensajes:
        autor = "Bot" if msg['es_bot'] else cliente_nombre
        lineas.append(f"{autor}: {msg['contenido']}")
    
    return "\n".join(lineas)

def generar_respuesta_ia(mensaje_cliente, cliente_nombre):
    """Genera respuesta usando Gemini con rotación de modelos"""
    global ULTIMO_REQUEST_IA
    
    api_key = db.get_config('api_key')
    if not api_key:
        print("    [IA] Sin API key, usando fallback...")
        return generar_respuesta_fallback(mensaje_cliente, cliente_nombre)
    
    # Control de rate limit
    tiempo_desde_ultimo = time.time() - ULTIMO_REQUEST_IA
    if tiempo_desde_ultimo < MIN_DELAY_ENTRE_REQUESTS:
        esperar = MIN_DELAY_ENTRE_REQUESTS - tiempo_desde_ultimo
        time.sleep(esperar)
    
    nombre_negocio = db.get_config('nombre_negocio', 'Barberia')
    instrucciones = db.get_config('instrucciones', 'Horario: 9am-8pm. Corte $10.')
    
    dia_semana, fecha_hoy, hora_actual = obtener_fecha_hora()
    horarios_disponibles = db.obtener_horarios_disponibles(fecha_hoy)
    historial = construir_historial_texto(cliente_nombre)
    
    prompt = f"""Eres el asistente virtual de {nombre_negocio}.

=== INFORMACION ACTUAL ===
- Hoy: {dia_semana}, {fecha_hoy}
- Hora: {hora_actual}
- Horarios HOY disponibles: {', '.join(horarios_disponibles) if horarios_disponibles else 'COMPLETO'}

=== INFORMACION DEL NEGOCIO ===
{instrucciones}

=== REGLAS ESTRICTAS ===
1. SOLO respondes sobre la barberia (precios, horarios, citas, servicios)
2. Los PRECIOS son FIJOS - NO se negocian bajo ninguna circunstancia
3. Los TURNOS ya agendados NO se modifican por chat (deben llamar)
4. Si preguntan algo fuera del tema, amablemente redirige al tema de barberia
5. Responde CORTO (maximo 2-3 lineas), natural, estilo WhatsApp
6. Se amable pero profesional, no uses emojis excesivos

=== SISTEMA DE CITAS ===
Si el cliente CONFIRMA una fecha y hora, incluye AL FINAL de tu mensaje:
[AGENDAR: YYYY-MM-DD HH:MM]

Ejemplo: "Perfecto, te anoto! [AGENDAR: 2025-12-12 15:00]"

=== HISTORIAL DE CONVERSACION ===
{historial}

=== MENSAJE ACTUAL DEL CLIENTE ===
{cliente_nombre}: {mensaje_cliente}

Tu respuesta (recuerda: corta y directa):"""

    # Intentar con cada modelo de Gemini
    for modelo in MODELOS_GEMINI:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(modelo)
            response = model.generate_content(prompt)
            ULTIMO_REQUEST_IA = time.time()
            print(f"    [IA] Modelo usado: {modelo}")
            return response.text
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                print(f"    [IA] {modelo}: Rate limit, esperando...")
                time.sleep(2)  # Esperar un poco más si hay rate limit
            else:
                print(f"    [IA] {modelo}: {error_str[:40]}")
            continue
    
    # Si todos fallaron, usar respuesta inteligente de fallback
    print("    [IA] Todos los modelos fallaron, usando fallback inteligente...")
    return generar_respuesta_fallback(mensaje_cliente, cliente_nombre)

def procesar_comando_agenda(respuesta_ia, cliente_nombre):
    """Detecta y procesa comandos de agenda en la respuesta"""
    if "[AGENDAR:" not in respuesta_ia:
        return respuesta_ia, False
    
    try:
        contenido = respuesta_ia.split("[AGENDAR:")[1].split("]")[0].strip()
        fecha, hora = contenido.split(" ")
        
        exito, mensaje = db.agendar_cita(fecha, hora, cliente_nombre, "WhatsApp")
        
        if exito:
            # Marcar conversación como exitosa
            db.marcar_cita_confirmada(cliente_nombre)
            respuesta_limpia = respuesta_ia.split("[AGENDAR:")[0].strip()
            return f"{respuesta_limpia} ✅ Cita confirmada para {fecha} a las {hora}!", True
        else:
            return "⚠️ Ese horario ya no está disponible. ¿Te parece otra hora?", False
    except Exception as e:
        print(f"    [ERROR AGENDA] {e}")
        return respuesta_ia.split("[AGENDAR:")[0].strip(), False

def imprimir_banner():
    """Imprime el banner inicial"""
    print("\n" + "="*60)
    print("  🏠 BOT DE WHATSAPP - " + db.get_config('nombre_negocio', 'Barbería'))
    print("  📊 Base de datos: SQLite")
    print("  🤖 IA: Gemini (con rotación)")
    print("="*60)

def main():
    """Función principal del bot"""
    imprimir_banner()
    
    with sync_playwright() as playwright:
        print("\n[1/4] Abriendo Microsoft Edge...")
        
        browser = playwright.chromium.launch_persistent_context(
            user_data_dir="whatsapp_session",
            channel="msedge",
            headless=False,
            args=["--start-maximized"]
        )
        
        page = browser.pages[0]
        print("[2/4] Navegando a WhatsApp Web...")
        page.goto("https://web.whatsapp.com")
        
        print("[3/4] Esperando carga (escanea QR si es necesario)...")
        
        # Esperar que cargue WhatsApp con múltiples selectores
        whatsapp_cargado = False
        selectores_espera = [
            '#pane-side',
            'div[aria-label="Lista de chats"]',
            'div[data-testid="chat-list"]',
        ]
        
        for selector in selectores_espera:
            try:
                page.wait_for_selector(selector, timeout=30000)
                whatsapp_cargado = True
                print(f"[4/4] ✅ WhatsApp conectado!")
                break
            except:
                continue
        
        if not whatsapp_cargado:
            print("[!] Esperando QR... (tienes 2 minutos)")
            try:
                page.wait_for_selector('#pane-side', timeout=120000)
                print("[4/4] ✅ WhatsApp conectado!")
            except:
                print("[ERROR] No se pudo conectar a WhatsApp")
                return
        
        print("\n" + "="*60)
        print("  🟢 BOT ACTIVO - Escuchando mensajes...")
        print("  Presiona Ctrl+C para detener")
        print("="*60 + "\n")
        
        ciclo = 0
        while True:
            try:
                # Verificar si el bot está encendido
                if db.get_config('bot_encendido', 'true').lower() != 'true':
                    if ciclo % 30 == 0:
                        print("[PAUSA] Bot desactivado en configuración")
                    time.sleep(2)
                    ciclo += 1
                    continue
                
                ciclo += 1
                if ciclo % 20 == 0:
                    print(f"[♥] Bot activo - {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                # ========== DETECTAR MENSAJES NO LEÍDOS ==========
                chat_encontrado = None
                
                # MÉTODO 1: Buscar spans con números (badge de notificación)
                try:
                    chats = page.query_selector_all('#pane-side > div > div > div > div')
                    
                    for chat_elem in chats[:15]:  # Revisar primeros 15 chats
                        try:
                            # Buscar si tiene un badge con número
                            spans = chat_elem.query_selector_all('span')
                            for span in spans:
                                texto = span.text_content()
                                if texto and texto.strip().isdigit():
                                    num = int(texto.strip())
                                    if 0 < num < 100:
                                        chat_encontrado = chat_elem
                                        print(f"\n[🔔] Chat con {num} mensaje(s) no leído(s)")
                                        break
                            if chat_encontrado:
                                break
                        except:
                            continue
                except Exception as e:
                    pass
                
                # MÉTODO 2: Buscar por aria-label
                if not chat_encontrado:
                    try:
                        badges = page.query_selector_all('span[aria-label*="no leído"], span[aria-label*="unread"]')
                        if badges:
                            # Subir al elemento del chat
                            badge = badges[0]
                            parent = badge
                            for _ in range(10):  # Subir hasta 10 niveles
                                parent = parent.evaluate_handle('el => el.parentElement')
                                if parent:
                                    role = parent.get_attribute('role') if hasattr(parent, 'get_attribute') else None
                                    if role == 'listitem' or role == 'row':
                                        chat_encontrado = parent
                                        print("\n[🔔] Chat no leído encontrado (método 2)")
                                        break
                    except:
                        pass
                
                # Si encontramos un chat con mensajes nuevos
                if chat_encontrado:
                    try:
                        # Hacer click en el chat
                        chat_encontrado.click()
                        time.sleep(1.5)
                        
                        # Obtener nombre del contacto
                        nombre_cliente = "Cliente"
                        try:
                            header = page.query_selector('header span[dir="auto"]')
                            if header:
                                nombre_cliente = header.text_content() or "Cliente"
                        except:
                            pass
                        
                        # Verificar si es contacto ignorado
                        ignorados = db.get_config('contactos_ignorados', '[]')
                        try:
                            lista_ignorados = json.loads(ignorados)
                            if nombre_cliente in lista_ignorados:
                                print(f"[IGNORADO] {nombre_cliente}")
                                time.sleep(1)
                                continue
                        except:
                            pass
                        
                        print(f"[CHAT] {nombre_cliente}")
                        
                        # ========== LEER MENSAJES ==========
                        time.sleep(1)  # Esperar que cargue el chat
                        
                        # Buscar todos los mensajes con diferentes selectores
                        mensajes_elem = page.query_selector_all('span.selectable-text')
                        
                        print(f"[DEBUG] Mensajes encontrados: {len(mensajes_elem) if mensajes_elem else 0}")
                        
                        if mensajes_elem and len(mensajes_elem) > 0:
                            # Tomar último mensaje
                            ultimo_elem = mensajes_elem[-1]
                            ultimo_mensaje = ultimo_elem.text_content()
                            
                            print(f"[DEBUG] Ultimo mensaje: '{ultimo_mensaje[:50]}...'")
                            
                            # NUEVA LOGICA: Verificar si es mensaje NUESTRO
                            # Buscamos en el contenedor padre del mensaje si tiene checkmarks
                            es_mio = False
                            
                            try:
                                # Metodo 1: Buscar checkmarks en la pagina (mensajes enviados tienen checks)
                                all_rows = page.query_selector_all('div[role="row"]')
                                if all_rows and len(all_rows) > 0:
                                    ultimo_row = all_rows[-1]
                                    # Los mensajes enviados tienen iconos de check
                                    check1 = ultimo_row.query_selector('span[data-icon="msg-check"]')
                                    check2 = ultimo_row.query_selector('span[data-icon="msg-dblcheck"]')
                                    check3 = ultimo_row.query_selector('span[data-icon="msg-dblcheck-ack"]')
                                    
                                    if check1 or check2 or check3:
                                        es_mio = True
                                        print("[DEBUG] Ultimo mensaje es NUESTRO (tiene checkmarks)")
                            except Exception as e:
                                print(f"[DEBUG] Error verificando checkmarks: {e}")
                            
                            # ID unico para no procesar dos veces  
                            msg_id = f"{nombre_cliente}:{ultimo_mensaje[:60]}"
                            
                            print(f"[DEBUG] Es mio: {es_mio}, Ya procesado: {msg_id in MENSAJES_PROCESADOS}")
                            
                            if not es_mio and msg_id not in MENSAJES_PROCESADOS:
                                print(f"\n{'='*50}")
                                print(f"NUEVO MENSAJE de {nombre_cliente}:")
                                print(f"  '{ultimo_mensaje}'")
                                print(f"{'='*50}")
                                
                                # Guardar mensaje del cliente en DB
                                try:
                                    db.agregar_mensaje(nombre_cliente, ultimo_mensaje, es_bot=False)
                                except Exception as e:
                                    print(f"[DEBUG] Error guardando en DB: {e}")
                                
                                # Generar respuesta
                                print("[BOT] Generando respuesta con IA...")
                                respuesta = generar_respuesta_ia(ultimo_mensaje, nombre_cliente)
                                print(f"[BOT] Respuesta generada: {respuesta[:80]}...")
                                
                                # Procesar comandos de agenda
                                respuesta, cita_agendada = procesar_comando_agenda(respuesta, nombre_cliente)
                                
                                # Guardar respuesta del bot en DB
                                try:
                                    db.agregar_mensaje(nombre_cliente, respuesta, es_bot=True)
                                except:
                                    pass
                                
                                # ========== ENVIAR RESPUESTA ==========
                                print("[BOT] Buscando caja de texto...")
                                
                                # Intentar varios selectores para la caja de texto
                                caja = None
                                selectores_caja = [
                                    'footer div[contenteditable="true"]',
                                    'div[contenteditable="true"][data-tab="10"]',
                                    'div[title="Escribe un mensaje"]',
                                    'div[contenteditable="true"][role="textbox"]'
                                ]
                                
                                for sel in selectores_caja:
                                    try:
                                        caja = page.query_selector(sel)
                                        if caja:
                                            print(f"[DEBUG] Caja encontrada con selector: {sel}")
                                            break
                                    except:
                                        continue
                                
                                if caja:
                                    try:
                                        caja.click()
                                        time.sleep(0.3)
                                        
                                        # Escribir mensaje caracter por caracter
                                        page.keyboard.type(respuesta, delay=15)
                                        time.sleep(0.3)
                                        page.keyboard.press("Enter")
                                        
                                        print(f"[OK] ENVIADO: {respuesta[:60]}...")
                                        MENSAJES_PROCESADOS.add(msg_id)
                                        
                                        if cita_agendada:
                                            print("[OK] CITA AGENDADA!")
                                    except Exception as e:
                                        print(f"[ERROR] Al enviar mensaje: {e}")
                                else:
                                    print("[ERROR] No encontre la caja de texto para escribir")
                            
                            elif es_mio:
                                print("[INFO] Ultimo mensaje es nuestro, esperando respuesta del cliente...")
                            else:
                                print("[INFO] Mensaje ya procesado anteriormente")
                        else:
                            print("[DEBUG] No se encontraron mensajes en el chat")
                        
                        print("")  # Linea vacia
                        
                    except Exception as e:
                        print(f"[ERROR] Procesando chat: {e}")
                
                time.sleep(2)  # Esperar antes del siguiente ciclo
                
            except KeyboardInterrupt:
                print("\n\n[!] Bot detenido por el usuario")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(3)
        
        browser.close()


if __name__ == "__main__":
    main()
