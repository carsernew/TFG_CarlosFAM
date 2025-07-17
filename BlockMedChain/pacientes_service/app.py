from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import os
import copy
import json
from datetime import datetime, timedelta
import jwt

app = Flask(__name__)
app.secret_key = 'clave_secreta_muy_segura'
JWT_SECRET = 'jwt_secret_compartido_entre_microservicios'
SESSION_TIMEOUT = timedelta(minutes=5)

# URL del microservicio de datos
DATA_SERVICE_URL = 'http://localhost:5005'
DATA_AUTH_URL='http://localhost:5000'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def menu_pacientes():
    return render_template('menu_pacientes.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('http://localhost:5000/')

@app.route('/ver_citas', methods=['GET'])
def ver_citas():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/ver_citas'))

    direccion_wallet = session['wallet_address']
    
    try:
        # Llamar al microservicio de datos para obtener las citas
        response = requests.get(f'{DATA_SERVICE_URL}/api/citas/wallet/{direccion_wallet}')
        
        if response.status_code == 200:
            citas = response.json().get('citas', [])
        else:
            citas = []
            print(f"Error obteniendo citas: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        citas = []

    return render_template('ver_citas.html', citas=citas)

@app.route('/auth')
def auth():
    token = request.args.get('token')
    next_url = request.args.get('next', '/')

    if not token:
        return "No se proporcionó token de autenticación", 400

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        session['wallet_address'] = payload['wallet_address']
        session['rol'] = payload['rol']
        session['session_expira'] = datetime.utcnow() + SESSION_TIMEOUT
        return redirect(next_url)
    except jwt.ExpiredSignatureError:
        return "Token de autenticación expirado", 401
    except jwt.InvalidTokenError:
        return "Token de autenticación inválido", 401

@app.route('/agendar_cita', methods=['GET', 'POST'])
def agendar_cita():
    wallet_address = session.get('wallet_address', '')
    wallet_number = wallet_address[:42]

    if request.method == 'GET':
        return render_template('agendar_cita.html', nombre=wallet_number, error=None)

    nombre = request.form['nombre']
    fecha = request.form['fecha']
    hora = request.form['hora']
    tx_hash = request.form.get('tx_hash')


    # Validaciones básicas del lado del cliente
    try:
        dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="Fecha u hora inválida.")

    if dt.weekday() > 4:
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="Solo se pueden agendar citas de lunes a viernes.")
    if dt.hour < 8 or dt.hour >= 15:
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="La hora debe estar entre las 08:00 y las 14:00.")

    # Datos de la cita
    cita_data = {
        "wallet_address": wallet_address,
        "nombre": nombre,
        "fecha": fecha,
        "hora": hora,
        "tx_hash": tx_hash
    }

    try:
        # Llamar al microservicio de datos para crear la cita
        response = requests.post(f'{DATA_SERVICE_URL}/api/citas', json=cita_data)
        
        if response.status_code == 201:
            result = response.json()
            return render_template("confirmacion_cita.html", archivo=result.get('archivo'))
        elif response.status_code == 409:
            error_msg = response.json().get('error', 'Horario no disponible')
            return render_template('agendar_cita.html', nombre=wallet_number, error=error_msg)
        else:
            error_msg = response.json().get('error', 'Error al crear la cita')
            return render_template('agendar_cita.html', nombre=wallet_number, error=error_msg)
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        return render_template('agendar_cita.html', nombre=wallet_number,
                               error="Error de conexión. Inténtalo más tarde.")

@app.route('/ver_historial')
def ver_historial():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/ver_historial'))
    
    wallet_address = session['wallet_address']
    
    try:
        # Obtener el CID del historial desde el microservicio de datos
        response = requests.get(f'{DATA_SERVICE_URL}/api/historial/cid/{wallet_address}')
        
        if response.status_code == 200:
            result = response.json()
            cid = result.get('cid')
            
            if cid:
                # Descargar el JSON directamente desde IPFS en el frontend
                archivo_tmp = os.path.join(BASE_DIR, f"historial_tmp_{wallet_address}.json")
                
                if descargar_json_de_ipfs(cid, archivo_tmp):
                    try:
                        with open(archivo_tmp, 'r') as f:
                            datos = json.load(f)
                    except Exception as e:
                        datos = {"error": "No se pudo leer el JSON", "detalle": str(e)}
                    finally:
                        if os.path.exists(archivo_tmp):
                            os.remove(archivo_tmp)
                else:
                    datos = {"error": "No se pudo descargar desde IPFS"}
            else:
                datos = {"error": "CID no encontrado"}
                
        elif response.status_code == 404:
            datos = {"error": "No se encontró historial médico para su cartera"}
        else:
            datos = {"error": "Error obteniendo información del historial"}
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        datos = {"error": "Error de conexión con el servicio de datos"}

    return render_template("ver_historial.html", historial=datos)

@app.route('/salir_historial')
def salir_historial():
    return redirect(url_for('menu_pacientes'))

@app.route('/anular', methods=['POST'])
def anular_cita():
    archivo = request.form.get('cita_id')

    if not archivo:
        return "Falta el identificador de la cita.", 400

    try:
        # Llamar al microservicio de datos para eliminar la cita
        response = requests.delete(f'{DATA_SERVICE_URL}/api/citas/{archivo}')
        
        if response.status_code == 200:
            return redirect(url_for('ver_citas'))
        elif response.status_code == 404:
            return "Cita no encontrada.", 404
        else:
            error_msg = response.json().get('error', 'Error al eliminar la cita')
            return f"No se pudo eliminar la cita: {error_msg}", 500
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        return "Error de conexión. Inténtalo más tarde.", 500

# Función auxiliar para descargar desde IPFS
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

@app.route('/anonimizar', methods=['GET', 'POST'])
def anonimizar():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/anonimizar'))
    
    wallet_address = session['wallet_address']
    print(f"DEBUG: Procesando anonimizar para wallet: {wallet_address}")
    
    if request.method == 'GET':
        print("DEBUG: GET request para anonimizar")
        try:
            # Obtener el CID del historial desde el microservicio de datos
            url_historial = f'{DATA_SERVICE_URL}/api/historial/cid/{wallet_address}'
            print(f"DEBUG: Llamando a URL: {url_historial}")
            response = requests.get(url_historial)
            print(f"DEBUG: Respuesta del servicio: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                cid = result.get('cid')
                print(f"DEBUG: CID obtenido: {cid}")
                
                if cid:
                    # Descargar el JSON directamente desde IPFS
                    archivo_tmp = os.path.join(BASE_DIR, f"historial_anonimizar_{wallet_address}.json")
                    print(f"DEBUG: Descargando a archivo temporal: {archivo_tmp}")
                    
                    if descargar_json_de_ipfs(cid, archivo_tmp):
                        try:
                            with open(archivo_tmp, 'r') as f:
                                datos = json.load(f)
                            print(f"DEBUG: Datos cargados, tipo: {type(datos)}")
                            
                            # Obtener las secciones disponibles
                            secciones = list(datos.keys()) if isinstance(datos, dict) else []
                            print(f"DEBUG: Secciones encontradas: {secciones}")
                            
                            return render_template("anonimizar.html", 
                                                 secciones=secciones, 
                                                 datos=datos,
                                                 cid_original=cid,
                                                 debug_info=f"Wallet: {wallet_address}, CID: {cid}, Secciones: {len(secciones)}")
                        except Exception as e:
                            print(f"DEBUG: Error leyendo JSON: {e}")
                            return render_template("anonimizar.html", 
                                                 error=f"No se pudo leer el JSON del historial: {str(e)}")
                        finally:
                            if os.path.exists(archivo_tmp):
                                os.remove(archivo_tmp)
                    else:
                        print("DEBUG: Error descargando desde IPFS")
                        return render_template("anonimizar.html", 
                                             error="No se pudo descargar desde IPFS")
                else:
                    print("DEBUG: CID vacío o None")
                    return render_template("anonimizar.html", 
                                         error="CID no encontrado")
                    
            elif response.status_code == 404:
                print("DEBUG: Historial no encontrado (404)")
                return render_template("anonimizar.html", 
                                     error="No se encontró historial médico para su cartera")
            else:
                print(f"DEBUG: Error del servicio: {response.status_code} - {response.text}")
                return render_template("anonimizar.html", 
                                     error=f"Error obteniendo información del historial (Status: {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Conectando con servicio de datos: {e}")
            return render_template("anonimizar.html", 
                                 error=f"Error de conexión con el servicio de datos: {str(e)}")
        except Exception as e:
            print(f"ERROR: Error general en GET: {e}")
            return render_template("anonimizar.html", 
                                 error=f"Error inesperado: {str(e)}")
    
    elif request.method == 'POST':
        try:
            # Obtener el CID original y las secciones seleccionadas
            cid_original = request.form.get('cid_original')
            secciones_habilitadas = request.form.getlist('secciones')
            
            if not cid_original:
                return render_template("anonimizar.html", 
                                    error="CID original no encontrado")
            
            # Descargar el historial original
            archivo_tmp = os.path.join(BASE_DIR, f"historial_original_{wallet_address}.json")
            
            if descargar_json_de_ipfs(cid_original, archivo_tmp):
                try:
                    with open(archivo_tmp, 'r') as f:
                        datos_originales = json.load(f)
                    
                    # Crear nueva versión con solo las secciones habilitadas
                    datos_anonimizados = {}
                    if isinstance(datos_originales, dict):
                        for seccion in secciones_habilitadas:
                            if seccion in datos_originales:
                                datos_anonimizados[seccion] = datos_originales[seccion]
                    
                    # Guardar el archivo anonimizado temporalmente
                    archivo_anonimizado = os.path.join(BASE_DIR, f"historial_anonimizado_{wallet_address}.json")
                    with open(archivo_anonimizado, 'w') as f:
                        json.dump(datos_anonimizados, f, indent=2, ensure_ascii=False)
                    
                    # Subir a IPFS
                    nuevo_cid = subir_json_a_ipfs(archivo_anonimizado)
                    
                    if nuevo_cid:
                        # NUEVA FUNCIONALIDAD: Guardar en microservicio 5005
                        data_para_microservicio = {
                            "wallet_address": wallet_address,
                            "cid_anonimizado": nuevo_cid,
                            "cid_original": cid_original,
                            "secciones_incluidas": secciones_habilitadas,
                            "fecha_anonimizacion": datetime.utcnow().isoformat()
                        }
                        
                        try:
                            # Llamar al microservicio 5005 para guardar el CID anonimizado
                            response = requests.post(
                                f'{DATA_SERVICE_URL}/api/historial/anonimizado',
                                json=data_para_microservicio
                            )
                            
                            if response.status_code == 201:
                                print(f"CID anonimizado guardado exitosamente en microservicio: {nuevo_cid}")
                                # Obtener información adicional de la respuesta
                                resultado_guardado = response.json()
                                archivo_guardado = resultado_guardado.get('archivo', '')
                            else:
                                print(f"Error guardando en microservicio: {response.status_code} - {response.text}")
                                archivo_guardado = "Error al guardar en microservicio"
                                
                        except requests.exceptions.RequestException as e:
                            print(f"Error conectando con microservicio 5005: {e}")
                            archivo_guardado = "Error de conexión con microservicio"
                        
                        return render_template("anonimizar.html", 
                                            success=True,
                                            nuevo_cid=nuevo_cid,
                                            secciones_incluidas=secciones_habilitadas,
                                            archivo_guardado=archivo_guardado)
                    else:
                        return render_template("anonimizar.html", 
                                            error="Error al subir el historial anonimizado a IPFS")
                        
                except Exception as e:
                    print(f"Error procesando historial: {e}")
                    return render_template("anonimizar.html", 
                                        error="Error al procesar el historial")
                finally:
                    # Limpiar archivos temporales
                    for archivo in [archivo_tmp, archivo_anonimizado]:
                        if 'archivo_anonimizado' in locals() and os.path.exists(archivo):
                            os.remove(archivo)
            else:
                return render_template("anonimizar.html", 
                                    error="No se pudo descargar el historial original")
                
        except Exception as e:
            print(f"Error en proceso de anonimización: {e}")
            return render_template("anonimizar.html", 
                                error="Error en el proceso de anonimización")


def subir_json_a_ipfs(archivo_json):
    try:
        url = 'http://127.0.0.1:5001/api/v0/add'
        with open(archivo_json, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('Hash')
        else:
            print(f"Error subiendo a IPFS: {response.content}")
            return None
    except Exception as e:
        print(f"Error subiendo a IPFS: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5004)