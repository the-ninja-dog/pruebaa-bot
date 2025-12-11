# -*- coding: utf-8 -*-
"""
BASE DE DATOS SQLITE PARA BOT DE BARBERÍA
==========================================
Maneja: clientes, citas, conversaciones, configuración
"""

import sqlite3
import datetime
import json
import os

DATABASE_FILE = "barberia.db"

class Database:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.init_database()
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        return conn
    
    def init_database(self):
        """Crea las tablas si no existen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabla de configuración
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')
        
        # Tabla de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de citas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS citas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                cliente_nombre TEXT,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                servicio TEXT DEFAULT 'Corte',
                estado TEXT DEFAULT 'Confirmado',
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        ''')
        
        # Tabla de conversaciones (historial por chat)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_nombre TEXT NOT NULL,
                estado TEXT DEFAULT 'activa',
                ultimo_mensaje DATETIME DEFAULT CURRENT_TIMESTAMP,
                cita_confirmada INTEGER DEFAULT 0
            )
        ''')
        
        # Tabla de mensajes (historial de cada conversación)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversacion_id INTEGER,
                cliente_nombre TEXT,
                es_bot INTEGER DEFAULT 0,
                contenido TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id)
            )
        ''')
        
        # Insertar configuración por defecto si no existe
        cursor.execute('''
            INSERT OR IGNORE INTO configuracion (clave, valor) VALUES
            ('nombre_negocio', 'Barbería Z'),
            ('api_key', ''),
            ('bot_encendido', 'true'),
            ('instrucciones', 'Horario: 9am-8pm. Corte $10. Barba $5. Corte+Barba $12.'),
            ('contactos_ignorados', '[]'),
            ('hora_inicio', '9'),
            ('hora_fin', '20')
        ''')
        
        conn.commit()
        conn.close()
        print(f"[DB] Base de datos inicializada: {self.db_file}")
    
    # ==================== CONFIGURACIÓN ====================
    
    def get_config(self, clave, default=None):
        """Obtiene un valor de configuración"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,))
        row = cursor.fetchone()
        conn.close()
        return row['valor'] if row else default
    
    def set_config(self, clave, valor):
        """Establece un valor de configuración"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)
        ''', (clave, valor))
        conn.commit()
        conn.close()
    
    def get_all_config(self):
        """Obtiene toda la configuración como diccionario"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT clave, valor FROM configuracion')
        rows = cursor.fetchall()
        conn.close()
        return {row['clave']: row['valor'] for row in rows}
    
    # ==================== CITAS ====================
    
    def obtener_citas_dia(self, fecha):
        """Obtiene todas las citas de un día"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM citas WHERE fecha = ? AND estado = 'Confirmado'
            ORDER BY hora
        ''', (fecha,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def obtener_horarios_disponibles(self, fecha):
        """Obtiene horarios libres para una fecha"""
        hora_inicio = int(self.get_config('hora_inicio', 9))
        hora_fin = int(self.get_config('hora_fin', 20))
        
        citas = self.obtener_citas_dia(fecha)
        horas_ocupadas = [c['hora'] for c in citas]
        
        disponibles = []
        for h in range(hora_inicio, hora_fin + 1):
            hora_str = f"{h:02d}:00"
            if hora_str not in horas_ocupadas:
                disponibles.append(hora_str)
        
        return disponibles
    
    def agendar_cita(self, fecha, hora, cliente_nombre, telefono="WhatsApp"):
        """
        Agenda una cita.
        - Si el cliente ya tiene cita ese día, la reprograma
        - Si el horario está ocupado por otro, retorna error
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verificar si el horario está ocupado por otro cliente
        cursor.execute('''
            SELECT * FROM citas 
            WHERE fecha = ? AND hora = ? AND estado = 'Confirmado'
        ''', (fecha, hora))
        cita_existente = cursor.fetchone()
        
        if cita_existente:
            if cita_existente['cliente_nombre'].lower() != cliente_nombre.lower():
                conn.close()
                return False, "Horario ocupado por otro cliente"
        
        # Buscar si el cliente ya tiene cita ese día
        cursor.execute('''
            SELECT * FROM citas 
            WHERE fecha = ? AND LOWER(cliente_nombre) = LOWER(?) AND estado = 'Confirmado'
        ''', (fecha, cliente_nombre))
        cita_cliente = cursor.fetchone()
        
        if cita_cliente:
            # Reprogramar
            old_hora = cita_cliente['hora']
            cursor.execute('''
                UPDATE citas SET hora = ? WHERE id = ?
            ''', (hora, cita_cliente['id']))
            conn.commit()
            conn.close()
            return True, f"Reprogramado de {old_hora} a {hora}"
        else:
            # Nueva cita
            cursor.execute('''
                INSERT INTO citas (cliente_nombre, fecha, hora, estado)
                VALUES (?, ?, ?, 'Confirmado')
            ''', (cliente_nombre, fecha, hora))
            conn.commit()
            conn.close()
            return True, "Cita agendada"
    
    def cancelar_cita(self, fecha, cliente_nombre):
        """Cancela una cita"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE citas SET estado = 'Cancelado'
            WHERE fecha = ? AND LOWER(cliente_nombre) = LOWER(?) AND estado = 'Confirmado'
        ''', (fecha, cliente_nombre))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def obtener_todas_citas(self, desde_fecha=None):
        """Obtiene todas las citas futuras"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if desde_fecha:
            cursor.execute('''
                SELECT * FROM citas WHERE fecha >= ? ORDER BY fecha, hora
            ''', (desde_fecha,))
        else:
            cursor.execute('SELECT * FROM citas ORDER BY fecha DESC, hora')
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ==================== CONVERSACIONES ====================
    
    def obtener_conversacion(self, cliente_nombre):
        """Obtiene o crea una conversación para un cliente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conversaciones WHERE cliente_nombre = ? AND estado = 'activa'
        ''', (cliente_nombre,))
        conv = cursor.fetchone()
        
        if not conv:
            cursor.execute('''
                INSERT INTO conversaciones (cliente_nombre, estado)
                VALUES (?, 'activa')
            ''', (cliente_nombre,))
            conn.commit()
            conv_id = cursor.lastrowid
        else:
            conv_id = conv['id']
        
        conn.close()
        return conv_id
    
    def agregar_mensaje(self, cliente_nombre, contenido, es_bot=False):
        """Agrega un mensaje al historial"""
        conv_id = self.obtener_conversacion(cliente_nombre)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO mensajes (conversacion_id, cliente_nombre, contenido, es_bot)
            VALUES (?, ?, ?, ?)
        ''', (conv_id, cliente_nombre, contenido, 1 if es_bot else 0))
        
        # Actualizar timestamp de última actividad
        cursor.execute('''
            UPDATE conversaciones SET ultimo_mensaje = CURRENT_TIMESTAMP WHERE id = ?
        ''', (conv_id,))
        
        conn.commit()
        conn.close()
    
    def obtener_historial(self, cliente_nombre, limite=10):
        """Obtiene el historial de mensajes de un cliente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM mensajes 
            WHERE cliente_nombre = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cliente_nombre, limite))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Invertir para tener orden cronológico
        mensajes = [dict(row) for row in rows]
        mensajes.reverse()
        return mensajes
    
    def marcar_cita_confirmada(self, cliente_nombre):
        """Marca que la conversación terminó con cita confirmada"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE conversaciones 
            SET cita_confirmada = 1, estado = 'cerrada'
            WHERE cliente_nombre = ? AND estado = 'activa'
        ''', (cliente_nombre,))
        conn.commit()
        conn.close()
    
    def conversacion_tiene_cita(self, cliente_nombre):
        """Verifica si el cliente ya confirmó cita en esta conversación"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT cita_confirmada FROM conversaciones 
            WHERE cliente_nombre = ? AND estado = 'activa'
        ''', (cliente_nombre,))
        row = cursor.fetchone()
        conn.close()
        return row and row['cita_confirmada'] == 1
    
    # ==================== ESTADÍSTICAS ====================
    
    def obtener_estadisticas(self):
        """Obtiene estadísticas del bot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hoy = datetime.date.today().isoformat()
        
        # Citas de hoy
        cursor.execute('''
            SELECT COUNT(*) as total FROM citas 
            WHERE fecha = ? AND estado = 'Confirmado'
        ''', (hoy,))
        citas_hoy = cursor.fetchone()['total']
        
        # Total mensajes hoy
        cursor.execute('''
            SELECT COUNT(*) as total FROM mensajes 
            WHERE DATE(timestamp) = ?
        ''', (hoy,))
        mensajes_hoy = cursor.fetchone()['total']
        
        # Conversaciones activas
        cursor.execute('''
            SELECT COUNT(*) as total FROM conversaciones WHERE estado = 'activa'
        ''')
        conv_activas = cursor.fetchone()['total']
        
        conn.close()
        
        return {
            'citas_hoy': citas_hoy,
            'mensajes_hoy': mensajes_hoy,
            'conversaciones_activas': conv_activas
        }


# Instancia global
db = Database()


# Para retrocompatibilidad con agenda_helper
def inicializar_agenda():
    """Compatibilidad con código anterior"""
    pass  # La DB se inicializa sola

def obtener_horarios_disponibles(fecha):
    """Compatibilidad con código anterior"""
    return db.obtener_horarios_disponibles(fecha)

def agendar_cita(fecha, hora, cliente, telefono):
    """Compatibilidad con código anterior"""
    return db.agendar_cita(fecha, hora, cliente, telefono)

def cancelar_cita(fecha, cliente):
    """Compatibilidad con código anterior"""
    return db.cancelar_cita(fecha, cliente)


if __name__ == "__main__":
    # Test de la base de datos
    print("=== Test de Base de Datos ===")
    
    # Config
    print(f"Nombre negocio: {db.get_config('nombre_negocio')}")
    
    # Horarios disponibles hoy
    hoy = datetime.date.today().isoformat()
    print(f"Horarios disponibles hoy: {db.obtener_horarios_disponibles(hoy)}")
    
    # Estadísticas
    print(f"Estadísticas: {db.obtener_estadisticas()}")
