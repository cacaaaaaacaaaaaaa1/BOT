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

def enviar_mensaje(telefono, texto):
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN_META}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": telefono, "type": "text", "text": {"body": texto}}
    
    print(f"📤 Intentando enviar a: {telefono}...") # LOG 1
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        # --- AQUÍ ESTÁ LA CLAVE DEL DIAGNÓSTICO ---
        print(f"📡 Estatus de Meta: {response.status_code}") # LOG 2
        print(f"📝 Respuesta completa: {response.text}")    # LOG 3 (Este nos dirá el error)
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

@app.route('/webhook', methods=['GET'])
def verificar_token():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return "Error de autenticación", 403

@app.route('/webhook', methods=['POST'])
def recibir_mensaje():
    try:
        data = request.json
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            telefono = msg['from']
            tipo = msg['type']
            
            print(f"📩 Mensaje recibido de {telefono} (Tipo: {tipo})")

            # Respondemos algo simple para probar la salida
            enviar_mensaje(telefono, "Probando conexión... 1, 2, 3.")
            
    except Exception as e:
        print(f"❌ Error procesando entrada: {e}")
        
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
