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
TOKEN_META = "EAA1YD3XNCIwBQOivmy0sh6DSLV7TEklnNTwbx18IsOJ413USWL0ZByPH6WjtKs54U7OO4CkWmXV17QPqYHnsxTheD7DSrbnUTvdTsgiNRBDKsm5OPJSIbNJsZAurAsBZBqgZCwY0DUuSEH86GtzHyLLfVjcXneKZCzUvyGsO0gRX0xMbjXHdRhFiwaQjQJpGYaWmQaH0FgQxSzD4R2C75Tm4f5X0ZCDxVvSweFe5zFRzxZAzEmqPCoOJa6lM4B69liBZCQMX7muafAxyWcCJz0NxRl4aeQZDZD"
PHONE_ID = "839576705914181"
VERIFY_TOKEN = "cobaep_secreto"  # Úsalo al configurar el Webhook en Meta

# ==========================================================
# 🧠 MEMORIA TEMPORAL
# ==========================================================
sesiones = {} 

# ==========================================================
# 📨 FUNCIONES WHATSAPP
# ==========================================================

def enviar_mensaje(telefono, texto):
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}}
    requests.post(url, headers=headers, json=data)

def enviar_bienvenida(telefono):
    """Envía las instrucciones iniciales y créditos."""
    mensaje = (
        "¡Bienvenido al buscador de boletas COBAEP! 🎓\n\n"
        "Para empezar, necesito saber tu matrícula para buscar tu boleta.\n\n"
        "👉 *Escribe tu matrícula ahora*\n"
        "(¡IMPORTANTE! No pongas espacios, escríbela tal cual, ej: 11/2024...)\n\n"
        "---------------------------------\n"
        "🤖 Bot creado por: *Ricardo Melendes Silva*"
    )
    enviar_mensaje(telefono, mensaje)

def enviar_lista_semestres(telefono):
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "📅 Selección de Semestre"},
            "body": {"text": "Matrícula recibida ✅\nSelecciona el semestre a consultar:"},
            "footer": {"text": "Sistema Escolar - By Ricardo Melendes"},
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
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "document",
        "document": {
            "link": url_publica_pdf,
            "caption": "✅ Aquí tienes tu boleta.\n\n- Bot creado por: Ricardo Melendes Silva",
            "filename": "Boleta_Calificaciones.pdf"
        }
    }
    requests.post(url, headers=headers, json=data)

# ==========================================================
# 🕵️ LÓGICA SOAP (Descarga de Boleta)
# ==========================================================

def descargar_boleta_soap(matricula, semestre):
    url = "http://www.cobaep.edu.mx/alumnos/ConsultaBoletaAndroid.asmx"
    payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <v:Envelope xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns:d="http://www.w3.org/2001/XMLSchema" xmlns:c="http://schemas.xmlsoap.org/soap/encoding/" xmlns:v="http://schemas.xmlsoap.org/soap/envelope/">
        <v:Header /><v:Body><GetEnrollmentStudent xmlns="http://www.cobaep.edu.mx/alumnos/" id="o0" c:root="1">
            <matricula i:type="d:string">{matricula}</matricula><grado i:type="d:int">{semestre}</grado>
        </GetEnrollmentStudent></v:Body></v:Envelope>"""
    
    headers = {'User-Agent': 'ksoap2-android/2.6.0+;version=3.6.4', 'SOAPAction': 'http://www.cobaep.edu.mx/alumnos/GetEnrollmentStudent', 'Content-Type': 'text/xml;charset=utf-8'}
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        root = ET.fromstring(response.text)
        b64_string = ""
        for element in root.iter():
            if element.text and len(element.text) > 1000:
                b64_string = element.text
                break
        
        if b64_string:
            pdf_bytes = base64.b64decode(b64_string)
            nombre_limpio = matricula.replace('/', '_')
            filename = f"static/boleta_{nombre_limpio}_sem{semestre}.pdf"
            with open(filename, "wb") as f:
                f.write(pdf_bytes)
            return filename
    except Exception as e:
        print(f"Error SOAP: {e}")
    return None

# ==========================================================
# 🌐 WEBHOOK
# ==========================================================

@app.route('/webhook', methods=['GET'])
def verificar_token():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return "Error", 403

@app.route('/webhook', methods=['POST'])
def recibir_mensaje():
    try:
        data = request.json
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            tel = msg['from']
            tipo = msg['type']
            
            # 1. SI ES TEXTO
            if tipo == 'text':
                texto = msg['text']['body'].strip()
                
                # --- EL PORTERO INTELIGENTE ---
                # Si el texto tiene una diagonal "/" y es largo, ASUMIMOS QUE ES MATRÍCULA
                if "/" in texto and len(texto) > 6:
                    sesiones[tel] = {"matricula": texto}
                    enviar_lista_semestres(tel)
                else:
                    # Si no parece matrícula (ej: "Hola", "bot", "gracias"), mandamos bienvenida
                    enviar_bienvenida(tel)
            
            # 2. SI ES SELECCIÓN DE BOTÓN/LISTA
            elif tipo == 'interactive':
                respuesta = msg['interactive']
                semestre_id = ""
                
                if 'list_reply' in respuesta:
                    semestre_id = respuesta['list_reply']['id']
                elif 'button_reply' in respuesta:
                    semestre_id = respuesta['button_reply']['id']
                
                if semestre_id and tel in sesiones:
                    matricula = sesiones[tel]['matricula']
                    enviar_mensaje(tel, f"⏳ Descargando boleta (Matrícula: {matricula}, Semestre: {semestre_id})...")
                    
                    ruta_pdf = descargar_boleta_soap(matricula, semestre_id)
                    
                    if ruta_pdf:
                        url_pdf_publica = f"{request.scheme}://{request.host}/{ruta_pdf}"
                        enviar_pdf(tel, url_pdf_publica)
                        del sesiones[tel]
                    else:
                        enviar_mensaje(tel, "❌ No se encontró boleta con esos datos. Verifica tu matrícula.")
                else:
                    enviar_bienvenida(tel) # Si falló la sesión, mandamos bienvenida de nuevo

    except Exception:
        pass 
        
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host='0.0.0.0', port=10000)
