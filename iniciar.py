# -*- coding: utf-8 -*-
"""
SCRIPT DE INICIO PARA BOT DE BARBERÍA
======================================
Ejecuta: python iniciar.py

Opciones:
- python iniciar.py bot     -> Solo el bot de WhatsApp
- python iniciar.py panel   -> Solo el panel admin
- python iniciar.py todo    -> Ambos (en diferentes terminales)
"""

import subprocess
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════╗
║           🏠 SISTEMA DE BOT PARA BARBERÍA                  ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║   Opciones:                                                ║
║                                                            ║
║   python iniciar.py bot    -> Iniciar bot de WhatsApp      ║
║   python iniciar.py panel  -> Iniciar panel admin web      ║
║   python iniciar.py todo   -> Iniciar ambos                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        return
    
    opcion = sys.argv[1].lower()
    
    if opcion == 'bot':
        print("\n🤖 Iniciando Bot de WhatsApp...\n")
        os.system('python bot_whatsapp_playwright.py')
        
    elif opcion == 'panel':
        print("\n🌐 Iniciando Panel Admin...\n")
        print("Abre http://localhost:5000 en tu navegador\n")
        os.system('python api_server.py')
        
    elif opcion == 'todo':
        print("\n🚀 Iniciando todo el sistema...\n")
        print("NOTA: Necesitas abrir 2 terminales:")
        print("  Terminal 1: python iniciar.py bot")
        print("  Terminal 2: python iniciar.py panel")
        print("\nO ejecuta cada uno en una terminal diferente.")
        
    else:
        print(f"Opción no reconocida: {opcion}")
        print("Usa: bot, panel, o todo")


if __name__ == "__main__":
    main()
