from flask import Flask, jsonify, request
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CITAS_JSON_DIR = os.path.join(BASE_DIR, 'citas_json')
HISTORIAL_DB_FILE = os.path.join(BASE_DIR, 'historial_db.json')
os.makedirs(CITAS_JSON_DIR, exist_ok=True)

# Inicializar base de datos de historiales si no existe
def inicializar_historial_db():
    if not os.path.exists(HISTORIAL_DB_FILE):
        historial_db = {
            "0x1234567890abcdef": "QmeEdvhVJ2uDe828ow5Rx2qgVM6N21ro94ze23f7hbnnps"
        }
        with open(HISTORIAL_DB_FILE, 'w') as f:
            json.dump(historial_db, f, indent=2)

# Inicializar al arrancar el servicio
inicializar_historial_db()

# API para obtener el CID del historial según la cartera
@app.route('/api/historial/cid/<wallet_address>', methods=['GET'])
def obtener_cid_historial(wallet_address):
    try:
        with open(HISTORIAL_DB_FILE, 'r') as f:
            historial_db = json.load(f)
        
        cid = historial_db.get(wallet_address)
        
        if cid:
            return jsonify({"cid": cid, "wallet": wallet_address}), 200
        else:
            return jsonify({"error": "No se encontró historial para esta cartera"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Error obteniendo CID: {str(e)}"}), 500

# API para agregar o actualizar CID de historial para una cartera
@app.route('/api/historial/cid', methods=['POST'])
def actualizar_cid_historial():
    try:
        data = request.get_json()
        
        if not data or 'wallet_address' not in data or 'cid' not in data:
            return jsonify({"error": "Se requiere wallet_address y cid"}), 400
        
        wallet_address = data['wallet_address']
        cid = data['cid']
    
        with open(HISTORIAL_DB_FILE, 'r') as f:
            historial_db = json.load(f)
        
        historial_db[wallet_address] = cid
    
        with open(HISTORIAL_DB_FILE, 'w') as f:
            json.dump(historial_db, f, indent=2)
        
        return jsonify({"message": "CID actualizado exitosamente", "wallet": wallet_address, "cid": cid}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error actualizando CID: {str(e)}"}), 500

# API para listar todos los historiales (administración)
@app.route('/api/historial/all', methods=['GET'])
def listar_historiales():
    try:
        with open(HISTORIAL_DB_FILE, 'r') as f:
            historial_db = json.load(f)
        
        return jsonify({"historiales": historial_db}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error listando historiales: {str(e)}"}), 500

# API para obtener citas de un wallet específico
@app.route('/api/citas/wallet/<wallet_address>', methods=['GET'])
def obtener_citas_wallet(wallet_address):
    citas = []

    def buscar_wallet_recursiva(obj, wallet):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    if buscar_wallet_recursiva(value, wallet):
                        return True
                elif isinstance(value, str) and wallet.lower() in value.lower():
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if buscar_wallet_recursiva(item, wallet):
                    return True
        return False

    try:
        for filename in os.listdir(CITAS_JSON_DIR):
            if filename.endswith('.json'):
                ruta_resumen = os.path.join(CITAS_JSON_DIR, filename)
                try:
                    with open(ruta_resumen, 'r') as f:
                        resumen = json.load(f)
                    cid = resumen.get('CID')
                    if not cid:
                        continue

                    archivo_tmp = os.path.join(BASE_DIR, f"temp_cita_ipfs_{filename}")
                    if not descargar_json_de_ipfs(cid, archivo_tmp):
                        print(f"No se pudo descargar JSON para CID {cid}")
                        continue
                
                    with open(archivo_tmp, 'r') as f:
                        data = json.load(f)
                    os.remove(archivo_tmp)

                    if buscar_wallet_recursiva(data, wallet_address):
                        fecha = data.get('fecha', 'Desconocida')
                        hora = data.get('hora', 'Desconocida')
                        citas.append((filename, fecha, hora))

                except Exception as e:
                    print(f"Error procesando {filename}: {e}")

        return jsonify({"citas": citas}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo citas: {str(e)}"}), 500

# API para crear una nueva cita
@app.route('/api/citas', methods=['POST'])
def crear_cita():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
            
        wallet_address = data.get('wallet_address')
        nombre = data.get('nombre')
        fecha = data.get('fecha')
        hora = data.get('hora')
        
        if not all([wallet_address, nombre, fecha, hora]):
            return jsonify({"error": "Faltan campos requeridos"}), 400

        
        citas_existentes = []
        for filename in os.listdir(CITAS_JSON_DIR):
            if filename.endswith('.json'):
                ruta = os.path.join(CITAS_JSON_DIR, filename)
                try:
                    with open(ruta, 'r') as f:
                        resumen = json.load(f)
                    cid = resumen.get('CID')
                    if cid:
                        # Descargar y verificar el contenido completo
                        archivo_tmp = os.path.join(BASE_DIR, f"temp_check_{filename}")
                        if descargar_json_de_ipfs(cid, archivo_tmp):
                            with open(archivo_tmp, 'r') as f:
                                cita_data = json.load(f)
                            os.remove(archivo_tmp)
                            citas_existentes.append(cita_data)
                except Exception as e:
                    print(f"Error verificando {filename}: {e}")

       
        for cita in citas_existentes:
            if cita.get('fecha') == fecha and cita.get('hora') == hora:
                return jsonify({
                    "error": "La fecha y hora seleccionada ya está ocupada. Por favor elige otro horario."
                }), 409

       
        cita_completa = {
            "nombre": nombre,
            "fecha": fecha,
            "hora": hora
        }

        
        ruta_temp = os.path.join(CITAS_JSON_DIR, "temp_cita.json")
        with open(ruta_temp, 'w') as f:
            json.dump(cita_completa, f, indent=2)

        
        cid = subir_json_a_ipfs(ruta_temp)
        os.remove(ruta_temp)

        if not cid:
            return jsonify({"error": "Error al subir la cita a IPFS"}), 500

        resumen_cita = {
            "wallet": wallet_address,
            "CID": cid
        }

        nombre_archivo_resumen = f"Resumen_{wallet_address[:8]}_{fecha}_{hora}.json"
        ruta_resumen = os.path.join(CITAS_JSON_DIR, nombre_archivo_resumen)

        with open(ruta_resumen, 'w') as f:
            json.dump(resumen_cita, f, indent=2)

        return jsonify({
            "message": "Cita creada exitosamente",
            "archivo": nombre_archivo_resumen,
            "cid": cid
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Error creando cita: {str(e)}"}), 500

# API para eliminar una cita
@app.route('/api/citas/<archivo>', methods=['DELETE'])
def eliminar_cita(archivo):
    try:
        ruta = os.path.join(CITAS_JSON_DIR, archivo)
        
        if os.path.exists(ruta):
            os.remove(ruta)
            return jsonify({"message": "Cita eliminada exitosamente"}), 200
        else:
            return jsonify({"error": "Archivo de cita no encontrado"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Error eliminando cita: {str(e)}"}), 500



@app.route('/api/citas', methods=['GET'])
def listar_todas_citas():
    try:
        citas = []
        
        for filename in os.listdir(CITAS_JSON_DIR):
            if filename.endswith('.json'):
                ruta = os.path.join(CITAS_JSON_DIR, filename)
                try:
                    with open(ruta, 'r') as f:
                        resumen = json.load(f)
                    
                    cid = resumen.get('CID')
                    wallet = resumen.get('wallet')
                    
                    if cid:
                        # Obtener datos completos desde IPFS
                        archivo_tmp = os.path.join(BASE_DIR, f"temp_list_{filename}")
                        if descargar_json_de_ipfs(cid, archivo_tmp):
                            with open(archivo_tmp, 'r') as f:
                                cita_data = json.load(f)
                            os.remove(archivo_tmp)
                            
                            citas.append({
                                "archivo": filename,
                                "wallet": wallet,
                                "cid": cid,
                                "datos": cita_data
                            })
                            
                except Exception as e:
                    print(f"Error procesando {filename}: {e}")
        
        return jsonify({"citas": citas}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error listando citas: {str(e)}"}), 500


def descargar_json_de_ipfs(cid, nombre_archivo_salida):
    try:
        url = f'http://127.0.0.1:5001/api/v0/cat?arg={cid}'
        response = requests.post(url)
        if response.status_code == 200:
            with open(nombre_archivo_salida, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"Error IPFS: {response.content}")
            return False
    except Exception as e:
        print(f"Error IPFS: {e}")
        return False

def subir_json_a_ipfs(ruta_json):
    try:
        with open(ruta_json, 'rb') as f:
            files = {'file': f}
            response = requests.post('http://127.0.0.1:5001/api/v0/add', files=files)
            
            if response.status_code == 200:
                res = response.json()
                cid = res['Hash'] 
                print(f"Archivo '{ruta_json}' subido a IPFS. CID: {cid}")
                return cid
            else:
                print(f"Error subiendo archivo a IPFS: {response.content}")
                return None
    except Exception as e:
        print(f"Error subiendo archivo a IPFS: {e}")
        return None

# Endpoint de salud del servicio
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "citas-data-service"}), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5005)