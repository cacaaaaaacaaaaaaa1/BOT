from flask import Flask, request, jsonify
import requests
import json
import base64
import os
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ==========================================================
# ⚙️ CONFIGURACIÓN (Rellena esto con tus datos de Meta)
# ==========================================================
TOKEN_META = "EAA1YD3XNCIwBQPWlGW2qWNrNwQMdUsVtyGQQ213yZALhN6PjL21spEY7CbMO9NzHLi7U0tQ2em4b6sXHR4YfSntRjZBKPHsZAkbCwCeE56PGEqMoOVhw0lqU9AeIuybCZByKujzjxwELQcYlYeireYJxnqY5mJrlQkkg4HrTXDPgptGYG3MsRDzwXhGF8DZCvPdUBSSKAv2KNR9JWWTvASDh7pYEFV4JDqw6P7C626EYZCg8lTpsiztEqrwBCVtNqOTltDJlUwl4M1vIBbOLGnu3JF"
PHONE_ID = "839576705914181"
VERIFY_TOKEN = "cobaep_secreto"  # Úsalo al configurar el Webhook en Meta

# ==========================================================
# 🧠 MEMORIA TEMPORAL
# ==========================================================
# Guardamos aquí: { "numero_telefono": { "matricula": "11/2024..." } }
sesiones = {} 

# ==========================================================
# 📨 FUNCIONES DE ENVÍO A WHATSAPP
# ==========================================================

def enviar_mensaje(telefono, texto):
    """Envía un mensaje de texto simple."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(url, headers=headers, json=data)

def enviar_lista_semestres(telefono):
    """Envía un menú desplegable con los 6 semestres."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "📅 Selección de Semestre"
            },
            "body": {
                "text": "Matrícula recibida correctamente. Por favor, selecciona el semestre a consultar:"
            },
            "footer": {
                "text": "Sistema de Boletas"
            },
            "action": {
                "button": "Ver Semestres",
                "sections": [
                    {
                        "title": "Elige una opción",
                        "rows": [
                            {"id": "1", "title": "1er Semestre", "description": "Grado 1"},
                            {"id": "2", "title": "2do Semestre", "description": "Grado 2"},
                            {"id": "3", "title": "3er Semestre", "description": "Grado 3"},
                            {"id": "4", "title": "4to Semestre", "description": "Grado 4"},
                            {"id": "5", "title": "5to Semestre", "description": "Grado 5"},
                            {"id": "6", "title": "6to Semestre", "description": "Grado 6"}
                        ]
                    }
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def enviar_pdf(telefono, url_publica_pdf):
    """Envía el archivo PDF al usuario."""
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "document",
        "document": {
            "link": url_publica_pdf,
            "caption": "✅ Aquí tienes tu boleta.",
            "filename": "Boleta_Calificaciones.pdf"
        }
    }
    requests.post(url, headers=headers, json=data)

# ==========================================================
# 🕵️ LÓGICA DE LA ESCUELA (SOAP)
# ==========================================================

def descargar_boleta_soap(matricula, semestre):
    """Conecta con el servidor de la escuela y baja el PDF."""
    url = "http://www.cobaep.edu.mx/alumnos/ConsultaBoletaAndroid.asmx"
    
    # XML Exacto que espera el servidor
    payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <v:Envelope xmlns:i="http://www.w3.org/2001/XMLSchema-instance" 
                xmlns:d="http://www.w3.org/2001/XMLSchema" 
                xmlns:c="http://schemas.xmlsoap.org/soap/encoding/" 
                xmlns:v="http://schemas.xmlsoap.org/soap/envelope/">
        <v:Header />
        <v:Body>
            <GetEnrollmentStudent xmlns="http://www.cobaep.edu.mx/alumnos/" id="o0" c:root="1">
                <matricula i:type="d:string">{matricula}</matricula>
                <grado i:type="d:int">{semestre}</grado>
            </GetEnrollmentStudent>
        </v:Body>
    </v:Envelope>"""
    
    headers = {
        'User-Agent': 'ksoap2-android/2.6.0+;version=3.6.4',
        'SOAPAction': 'http://www.cobaep.edu.mx/alumnos/GetEnrollmentStudent',
        'Content-Type': 'text/xml;charset=utf-8'
    }
    
    try:
        print(f"📡 Solicitando boleta: Matrícula {matricula}, Grado {semestre}...")
        response = requests.post(url, headers=headers, data=payload)
        
        # Análisis robusto del XML para encontrar el Base64
        root = ET.fromstring(response.text)
        b64_string = ""
        
        # Buscamos el texto más largo en la respuesta (el PDF)
        for element in root.iter():
            if element.text and len(element.text) > 1000:
                b64_string = element.text
                break
        
        if b64_string:
            pdf_bytes = base64.b64decode(b64_string)
            # Nombre seguro para el archivo
            nombre_limpio = matricula.replace('/', '_')
            filename = f"static/boleta_{nombre_limpio}_sem{semestre}.pdf"
            
            with open(filename, "wb") as f:
                f.write(pdf_bytes)
            print("✅ PDF descargado y guardado correctamente.")
            return filename
        else:
            print("⚠️ El servidor respondió, pero no envió PDF (Posible error de matrícula).")
            return None

    except Exception as e:
        print(f"❌ Error en la conexión SOAP: {e}")
        return None

# ==========================================================
# 🌐 EL WEBHOOK (Puerta de entrada)
# ==========================================================

@app.route('/webhook', methods=['GET'])
def verificar_token():
    """Verificación inicial de Meta."""
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return "Error de autenticación", 403

@app.route('/webhook', methods=['POST'])
def recibir_mensaje():
    """Procesamiento de mensajes entrantes."""
    try:
        data = request.json
        # Verificamos si es un mensaje válido
        if 'entry' in data and len(data['entry']) > 0:
            changes = data['entry'][0]['changes'][0]
            if 'value' in changes and 'messages' in changes['value']:
                msg = changes['value']['messages'][0]
                tel = msg['from']
                tipo = msg['type']
                
                # --- CASO 1: TEXTO (Usuario envía matrícula) ---
                if tipo == 'text':
                    texto = msg['text']['body'].strip()
                    # Guardamos matrícula en memoria
                    sesiones[tel] = {"matricula": texto}
                    # Enviamos menú
                    enviar_lista_semestres(tel)
                
                # --- CASO 2: INTERACTIVO (Usuario elige semestre de la lista) ---
                elif tipo == 'interactive':
                    respuesta = msg['interactive']
                    semestre_id = ""
                    
                    # Detectar si viene de lista o botón (por seguridad)
                    if 'list_reply' in respuesta:
                        semestre_id = respuesta['list_reply']['id']
                    elif 'button_reply' in respuesta:
                        semestre_id = respuesta['button_reply']['id']
                    
                    # Procesar la selección
                    if semestre_id and tel in sesiones:
                        matricula = sesiones[tel]['matricula']
                        
                        enviar_mensaje(tel, f"🔍 Buscando boleta... (Matrícula: {matricula}, Semestre: {semestre_id})")
                        
                        # Ejecutar descarga
                        ruta_pdf = descargar_boleta_soap(matricula, semestre_id)
                        
                        if ruta_pdf:
                            # Construir URL pública (usando la dirección de Ngrok)
                            url_pdf_publica = request.host_url + ruta_pdf
                            # Enviar
                            enviar_pdf(tel, url_pdf_publica)
                            # Limpiar sesión
                            del sesiones[tel]
                        else:
                            enviar_mensaje(tel, "⚠️ No se encontró la boleta. Verifica que la matrícula y el semestre sean correctos.")
                    else:
                        enviar_mensaje(tel, "⚠️ Sesión expirada. Por favor, escribe tu matrícula nuevamente.")

    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Asegurar que existe la carpeta para guardar PDFs
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # Iniciar servidor
    app.run(port=5000, debug=True)