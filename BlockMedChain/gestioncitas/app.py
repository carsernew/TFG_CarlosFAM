from flask import Flask, jsonify, request
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CITAS_JSON_DIR = os.path.join(BASE_DIR, 'citas_json')
LABORATORIO_DATA_DIR = os.path.join(BASE_DIR, 'laboratorio_json')
HISTORIAL_DB_FILE = os.path.join(BASE_DIR, 'historial_db.json')
CONSULTAS_JSON_DIR = os.path.join(BASE_DIR, 'consultas_json')
os.makedirs(CONSULTAS_JSON_DIR, exist_ok=True)
os.makedirs(CITAS_JSON_DIR, exist_ok=True)
os.makedirs(LABORATORIO_DATA_DIR, exist_ok=True)

HISTORIAL_DB_FILE = "historial_db.json"

def inicializar_historial_db():
    if not os.path.exists(HISTORIAL_DB_FILE):
        # Usar diccionario en lugar de lista para búsquedas más rápidas
        historial_db = {
            "0xf8f4d31644538bb7a952c5dd14374024e3f87f71": "QmeEdvhVJ2uDe828ow5Rx2qgVM6N21ro94ze23f7hbnnps"
        }
        with open(HISTORIAL_DB_FILE, 'w') as f:
            json.dump(historial_db, f, indent=2)

# Inicializar al arrancar el servicio
inicializar_historial_db()

@app.route('/api/historial/cid/<wallet_address>', methods=['GET'])
def obtener_cid_historial(wallet_address):
    try:
        with open(HISTORIAL_DB_FILE, 'r') as f:
            historial_db = json.load(f)
        
        # Ahora sí puedes usar .get() directamente
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
    notificar_historial_a_frontend(wallet_address, cid)
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
        tx_hash = data.get('tx_hash', '')
        
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
            "hora": hora,
            "tx_hash": tx_hash
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
            "CID": cid,
            "tx_hash": tx_hash
        }

        nombre_archivo_resumen = f"Cita_{wallet_address[:8]}_{fecha}_{hora}.json"
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

@app.route('/api/consultas', methods=['POST'])
def crear_consulta():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se proporcionaron datos"}), 400
            
        # Extraer datos del formulario
        cita_id = data.get('cita_id')
        wallet_paciente = data.get('wallet_paciente')
        wallet_medico = data.get('wallet_medico')
        fecha_cita = data.get('fecha_cita')
        hora_cita = data.get('hora_cita')
        motivo_consulta = data.get('motivo_consulta')
        diagnostico = data.get('diagnostico')
        medicacion = data.get('medicacion')
        observaciones = data.get('observaciones')
        tx_hash = data.get('tx_hash', '')
        fecha_consulta = data.get('fecha_consulta')
        
        
        # Validar campos requeridos
        if not all([wallet_paciente, wallet_medico, fecha_cita, hora_cita]):
            return jsonify({"error": "Faltan campos requeridos"}), 400

        # Crear objeto completo de la consulta
        consulta_completa = {
            "cita_id": cita_id,
            "wallet_paciente": wallet_paciente,
            "wallet_medico": wallet_medico,
            "fecha_cita": fecha_cita,
            "hora_cita": hora_cita,
            "motivo_consulta": motivo_consulta,
            "diagnostico": diagnostico,
            "medicacion": medicacion,
            "observaciones": observaciones,
            "tx_hash": tx_hash,
            "fecha_consulta": fecha_consulta,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Guardar temporalmente en archivo local
        ruta_temp = os.path.join(CONSULTAS_JSON_DIR, "temp_consulta.json")
        with open(ruta_temp, 'w', encoding='utf-8') as f:
            json.dump(consulta_completa, f, indent=2, ensure_ascii=False)

        # Subir archivo a IPFS y obtener CID
        cid = subir_json_a_ipfs(ruta_temp)
        os.remove(ruta_temp)  # Eliminar archivo temporal

        if not cid:
            return jsonify({"error": "Error al subir la consulta a IPFS"}), 500

        # Crear resumen de la consulta con CID
        resumen_consulta = {
            "wallet_paciente": wallet_paciente,
            "wallet_medico": wallet_medico,
            "fecha_cita": fecha_cita,
            "hora_cita": hora_cita,
            "CID": cid,
            "fecha_consulta": fecha_consulta,
            "tx_hash": tx_hash,
            "cita_id": cita_id
        }

        # Generar nombre único para el archivo resumen
        # Formato: Consulta_{wallet_medico_primeros8}_{fecha}_{hora}.json
        nombre_archivo_resumen = f"Consulta_{wallet_medico[:8]}_{fecha_cita}_{hora_cita.replace(':', '')}.json"
        ruta_resumen = os.path.join(CONSULTAS_JSON_DIR, nombre_archivo_resumen)

        # Guardar resumen localmente
        with open(ruta_resumen, 'w', encoding='utf-8') as f:
            json.dump(resumen_consulta, f, indent=2, ensure_ascii=False)

        return jsonify({
            "message": "Consulta creada exitosamente",
            "archivo": nombre_archivo_resumen,
            "cid": cid,
            "tx_hash": tx_hash,
            "wallet_paciente": wallet_paciente,
            "wallet_medico": wallet_medico
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Error creando consulta: {str(e)}"}), 500

# API para obtener consultas de un médico específico
@app.route('/api/consultas/medico/<wallet_medico>', methods=['GET'])
def obtener_consultas_medico(wallet_medico):
    try:
        consultas = []
        
        for filename in os.listdir(CONSULTAS_JSON_DIR):
            if filename.endswith('.json'):
                ruta_resumen = os.path.join(CONSULTAS_JSON_DIR, filename)
                try:
                    with open(ruta_resumen, 'r', encoding='utf-8') as f:
                        resumen = json.load(f)
                    
                    # Verificar si la consulta pertenece al médico
                    if resumen.get('wallet_medico') == wallet_medico:
                        cid = resumen.get('CID')
                        if cid:
                            # Descargar datos completos desde IPFS
                            archivo_tmp = os.path.join(BASE_DIR, f"temp_consulta_{filename}")
                            if descargar_json_de_ipfs(cid, archivo_tmp):
                                with open(archivo_tmp, 'r', encoding='utf-8') as f:
                                    consulta_data = json.load(f)
                                os.remove(archivo_tmp)
                                
                                consultas.append({
                                    "archivo": filename,
                                    "resumen": resumen,
                                    "datos": consulta_data
                                })
                                
                except Exception as e:
                    print(f"Error procesando {filename}: {e}")
        
        return jsonify({"consultas": consultas}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo consultas: {str(e)}"}), 500

# API para obtener consultas de un paciente específico
@app.route('/api/consultas/paciente/<wallet_paciente>', methods=['GET'])
def obtener_consultas_paciente(wallet_paciente):
    try:
        consultas = []
        
        for filename in os.listdir(CONSULTAS_JSON_DIR):
            if filename.endswith('.json'):
                ruta_resumen = os.path.join(CONSULTAS_JSON_DIR, filename)
                try:
                    with open(ruta_resumen, 'r', encoding='utf-8') as f:
                        resumen = json.load(f)
                    
                    # Verificar si la consulta pertenece al paciente
                    if resumen.get('wallet_paciente') == wallet_paciente:
                        cid = resumen.get('CID')
                        if cid:
                            # Descargar datos completos desde IPFS
                            archivo_tmp = os.path.join(BASE_DIR, f"temp_consulta_{filename}")
                            if descargar_json_de_ipfs(cid, archivo_tmp):
                                with open(archivo_tmp, 'r', encoding='utf-8') as f:
                                    consulta_data = json.load(f)
                                os.remove(archivo_tmp)
                                
                                consultas.append({
                                    "archivo": filename,
                                    "resumen": resumen,
                                    "datos": consulta_data
                                })
                                
                except Exception as e:
                    print(f"Error procesando {filename}: {e}")
        
        return jsonify({"consultas": consultas}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo consultas: {str(e)}"}), 500

# API para obtener todas las consultas (administración)
@app.route('/api/consultas', methods=['GET'])
def listar_todas_consultas():
    try:
        consultas = []
        
        for filename in os.listdir(CONSULTAS_JSON_DIR):
            if filename.endswith('.json'):
                ruta_resumen = os.path.join(CONSULTAS_JSON_DIR, filename)
                try:
                    with open(ruta_resumen, 'r', encoding='utf-8') as f:
                        resumen = json.load(f)
                    
                    cid = resumen.get('CID')
                    if cid:
                        # Descargar datos completos desde IPFS
                        archivo_tmp = os.path.join(BASE_DIR, f"temp_consulta_{filename}")
                        if descargar_json_de_ipfs(cid, archivo_tmp):
                            with open(archivo_tmp, 'r', encoding='utf-8') as f:
                                consulta_data = json.load(f)
                            os.remove(archivo_tmp)
                            
                            consultas.append({
                                "archivo": filename,
                                "resumen": resumen,
                                "datos": consulta_data
                            })
                            
                except Exception as e:
                    print(f"Error procesando {filename}: {e}")
        
        return jsonify({"consultas": consultas}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error listando consultas: {str(e)}"}), 500

# API para eliminar una consulta
@app.route('/api/consultas/<archivo>', methods=['DELETE'])
def eliminar_consulta(archivo):
    try:
        ruta = os.path.join(CONSULTAS_JSON_DIR, archivo)
        
        if os.path.exists(ruta):
            os.remove(ruta)
            return jsonify({"message": "Consulta eliminada exitosamente"}), 200
        else:
            return jsonify({"error": "Archivo de consulta no encontrado"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Error eliminando consulta: {str(e)}"}), 500

@app.route('/api/historial/anonimizado', methods=['POST'])
def guardar_historial_anonimizado():
    """
    Guarda el CID de un historial médico anonimizado
    """
    try:
        data = request.get_json()
        
        if not data or 'wallet_address' not in data or 'cid_anonimizado' not in data:
            return jsonify({"error": "Se requiere wallet_address y cid_anonimizado"}), 400
            
        wallet_address = data['wallet_address']
        cid_anonimizado = data['cid_anonimizado']
        cid_original = data.get('cid_original', '')
        secciones_incluidas = data.get('secciones_incluidas', [])
        fecha_anonimizacion = data.get('fecha_anonimizacion', datetime.utcnow().isoformat())
        
        # Crear objeto con la información del historial anonimizado
        historial_anonimizado = {
            "wallet_address": wallet_address,
            "cid_anonimizado": cid_anonimizado,
            "cid_original": cid_original,
            "secciones_incluidas": secciones_incluidas,
            "fecha_anonimizacion": fecha_anonimizacion,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Guardar en archivo JSON local
        nombre_archivo = f"historial_anonimizado_{wallet_address[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        ruta_archivo = os.path.join(BASE_DIR, 'historiales_anonimizados', nombre_archivo)
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(historial_anonimizado, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "message": "Historial anonimizado guardado exitosamente",
            "archivo": nombre_archivo,
            "cid_anonimizado": cid_anonimizado,
            "wallet_address": wallet_address,
            "secciones_incluidas": secciones_incluidas
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Error guardando historial anonimizado: {str(e)}"}), 500

@app.route('/api/historial/anonimizado/wallet/<wallet_address>', methods=['GET'])
def obtener_historiales_anonimizados(wallet_address):
    """
    Obtiene todos los historiales anonimizados de un wallet específico
    """
    try:
        historiales_dir = os.path.join(BASE_DIR, 'historiales_anonimizados')
        historiales = []
        
        if os.path.exists(historiales_dir):
            for filename in os.listdir(historiales_dir):
                if filename.endswith('.json') and wallet_address[:8] in filename:
                    ruta_archivo = os.path.join(historiales_dir, filename)
                    try:
                        with open(ruta_archivo, 'r', encoding='utf-8') as f:
                            historial_data = json.load(f)
                        
                        if historial_data.get('wallet_address') == wallet_address:
                            historiales.append({
                                "archivo": filename,
                                "datos": historial_data
                            })
                    except Exception as e:
                        print(f"Error procesando {filename}: {e}")
        
        return jsonify({"historiales_anonimizados": historiales}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo historiales anonimizados: {str(e)}"}), 500

@app.route('/api/historial/anonimizado/all', methods=['GET'])
def obtener_todos_historiales_anonimizados():
    """
    Obtiene todos los historiales anonimizados disponibles
    """
    try:
        historiales_dir = os.path.join(BASE_DIR, 'historiales_anonimizados')
        historiales = []
        
        # Crear directorio si no existe
        os.makedirs(historiales_dir, exist_ok=True)
        
        if os.path.exists(historiales_dir):
            for filename in os.listdir(historiales_dir):
                if filename.endswith('.json'):
                    ruta_archivo = os.path.join(historiales_dir, filename)
                    try:
                        with open(ruta_archivo, 'r', encoding='utf-8') as f:
                            historial_data = json.load(f)
                        
                        historiales.append({
                            "archivo": filename,
                            "cid_anonimizado": historial_data.get('cid_anonimizado'),
                            "fecha_anonimizacion": historial_data.get('fecha_anonimizacion'),
                            "secciones_incluidas": historial_data.get('secciones_incluidas', []),
                            "wallet_original": historial_data.get('wallet_address', 'N/A')[:8] + '...' if historial_data.get('wallet_address') else 'N/A'
                        })
                    except Exception as e:
                        print(f"Error procesando {filename}: {e}")
        
        return jsonify({"historiales_anonimizados": historiales}), 200
        
    except Exception as e:
        return jsonify({"error": f"Error obteniendo historiales anónimos: {str(e)}"}), 500

# Endpoint de salud del servicio
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "citas-data-service"}), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5005)