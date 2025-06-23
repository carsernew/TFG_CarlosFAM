from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import os
import json
from datetime import datetime, timedelta
import jwt

app = Flask(__name__)
app.secret_key = 'clave_secreta_medico_muy_segura'
JWT_SECRET = 'jwt_secret_compartido_entre_microservicios'
SESSION_TIMEOUT = timedelta(minutes=5)

DATA_SERVICE_URL = 'http://localhost:5005'
DATA_AUTH_URL='http://localhost:5000'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIRR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.route('/')
def menumedicos():
    return render_template('menu_doctores.html')

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

@app.route('/citas')
def ver_todas_las_citas():
    """Ver todas las citas programadas"""
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/citas'))

    # Obtener filtros opcionales
    fecha_filtro = request.args.get('fecha', '')
    estado_filtro = request.args.get('estado', 'todas')

    try:
        # Llamar al microservicio de datos para obtener todas las citas
        params = {}
        if fecha_filtro:
            params['fecha'] = fecha_filtro
        if estado_filtro != 'todas':
            params['estado'] = estado_filtro

        response = requests.get(f'{DATA_SERVICE_URL}/api/citas/todas', params=params)
        
        if response.status_code == 200:
            citas = response.json().get('citas', [])
            
            # Procesar las citas para mostrar información adicional
            for cita in citas:
                # Formatear la fecha y hora para mejor visualización
                try:
                    fecha_obj = datetime.strptime(f"{cita['fecha']} {cita['hora']}", "%Y-%m-%d %H:%M")
                    cita['fecha_formateada'] = fecha_obj.strftime("%d/%m/%Y")
                    cita['hora_formateada'] = fecha_obj.strftime("%H:%M")
                    cita['dia_semana'] = fecha_obj.strftime("%A")
                except:
                    cita['fecha_formateada'] = cita.get('fecha', 'N/A')
                    cita['hora_formateada'] = cita.get('hora', 'N/A')
                    cita['dia_semana'] = 'N/A'
                
                # Formatear dirección de wallet para mostrar solo los primeros y últimos caracteres
                wallet = cita.get('wallet_address', '')
                if len(wallet) > 10:
                    cita['wallet_corta'] = wallet[:6] + '...' + wallet[-4:]
                else:
                    cita['wallet_corta'] = wallet
                    
        else:
            citas = []
            print(f"Error obteniendo citas: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        citas = []

    return render_template('ver_citas_medico.html', 
                         citas=citas, 
                         fecha_filtro=fecha_filtro,
                         estado_filtro=estado_filtro)

@app.route('/historial/<wallet_address>')
def ver_historial_paciente(wallet_address):
    """Ver historial médico de un paciente específico"""
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next=f'/historial/{wallet_address}'))

    try:
        # Obtener el CID del historial desde el microservicio de datos
        response = requests.get(f'{DATA_SERVICE_URL}/api/historial/cid/{wallet_address}')
        
        if response.status_code == 200:
            result = response.json()
            cid = result.get('cid')
            
            if cid:
                # Descargar el JSON directamente desde IPFS
                archivo_tmp = os.path.join(BASE_DIR, f"historial_tmp_{wallet_address}.json")
                
                if descargar_json_de_ipfs(cid, archivo_tmp):
                    try:
                        with open(archivo_tmp, 'r', encoding='utf-8') as f:
                            datos = json.load(f)
                        
                        # Agregar información adicional
                        datos['wallet_address'] = wallet_address
                        datos['wallet_corta'] = wallet_address[:6] + '...' + wallet_address[-4:] if len(wallet_address) > 10 else wallet_address
                        
                    except Exception as e:
                        datos = {
                            "error": "No se pudo leer el historial médico", 
                            "detalle": str(e),
                            "wallet_address": wallet_address
                        }
                    finally:
                        if os.path.exists(archivo_tmp):
                            os.remove(archivo_tmp)
                else:
                    datos = {
                        "error": "No se pudo descargar el historial desde IPFS",
                        "wallet_address": wallet_address
                    }
            else:
                datos = {
                    "error": "CID no encontrado para este paciente",
                    "wallet_address": wallet_address
                }
                
        elif response.status_code == 404:
            datos = {
                "error": "No se encontró historial médico para este paciente",
                "wallet_address": wallet_address
            }
        else:
            datos = {
                "error": "Error obteniendo información del historial",
                "wallet_address": wallet_address
            }
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        datos = {
            "error": "Error de conexión con el servicio de datos",
            "wallet_address": wallet_address
        }

    return render_template("historial_paciente.html", historial=datos)

@app.route('/paciente/<wallet_address>')
def detalle_paciente(wallet_address):
    try:
        # Obtener las citas del paciente
        response_citas = requests.get(f'{DATA_SERVICE_URL}/api/citas/wallet/{wallet_address}')
        
        if response_citas.status_code == 200:
            citas = response_citas.json().get('citas', [])
            
            # Procesar las citas
            for cita in citas:
                try:
                    fecha_obj = datetime.strptime(f"{cita['fecha']} {cita['hora']}", "%Y-%m-%d %H:%M")
                    cita['fecha_formateada'] = fecha_obj.strftime("%d/%m/%Y")
                    cita['hora_formateada'] = fecha_obj.strftime("%H:%M")
                    cita['dia_semana'] = fecha_obj.strftime("%A")
                except:
                    cita['fecha_formateada'] = cita.get('fecha', 'N/A')
                    cita['hora_formateada'] = cita.get('hora', 'N/A')
                    cita['dia_semana'] = 'N/A'
        else:
            citas = []

        # Información del paciente
        paciente_info = {
            'wallet_address': wallet_address,
            'wallet_corta': wallet_address[:6] + '...' + wallet_address[-4:] if len(wallet_address) > 10 else wallet_address,
            'total_citas': len(citas),
            'citas': citas
        }

    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        paciente_info = {
            'wallet_address': wallet_address,
            'wallet_corta': wallet_address[:6] + '...' + wallet_address[-4:] if len(wallet_address) > 10 else wallet_address,
            'error': 'Error de conexión con el servicio de datos'
        }

    return render_template('detalle_paciente.html', paciente=paciente_info)

@app.route('/estadisticas')
def estadisticas():
    """Ver estadísticas generales"""
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/estadisticas'))

    try:
        # Obtener estadísticas del microservicio
        response = requests.get(f'{DATA_SERVICE_URL}/api/estadisticas')
        
        if response.status_code == 200:
            stats = response.json()
        else:
            stats = {
                'error': 'No se pudieron obtener las estadísticas'
            }
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        stats = {
            'error': 'Error de conexión con el servicio de datos'
        }

    return render_template('estadisticas.html', estadisticas=stats)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('http://localhost:5000/')

# Función auxiliar para descargar desde IPFS
def descargar_json_de_ipfs(cid, nombre_archivo_salida):
    """Descarga un archivo JSON desde IPFS dado su CID"""
    try:
        url = f'http://127.0.0.1:5001/api/v0/cat?arg={cid}'
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            with open(nombre_archivo_salida, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"Error IPFS: {response.status_code} - {response.content}")
            return False
            
    except requests.exceptions.Timeout:
        print("Timeout conectando con IPFS")
        return False
    except Exception as e:
        print(f"Error IPFS: {e}")
        return False

# Context processor para pasar información común a todas las plantillas
@app.context_processor
def inject_user():
    return {
        'usuario_actual': session.get('wallet_address', ''),
        'rol_actual': session.get('rol', ''),
        'sesion_activa': 'wallet_address' in session
    }


@app.route('/ver_citas', methods=['GET'])
def ver_citas():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/ver_citas'))
    
    # Ruta correcta basada en la estructura real
    ruta_wallets = os.path.join(BASE_DIRR, 'autentificador', 'wallets', 'wallets_pacientes.txt')
    lista_wallets = []
    try:
        with open(ruta_wallets, 'r', encoding='utf-8') as f:
            lista_wallets = [linea.strip() for linea in f if linea.strip()]
        print("Wallets cargadas:", lista_wallets) # <- DEBUG
    except Exception as e:
        print(f"Error leyendo archivo de wallets: {e}")
        lista_wallets = []
    
    wallet_seleccionada = request.args.get('wallet')
    
    if wallet_seleccionada:
        session['wallet_seleccionada'] = wallet_seleccionada
        
    
    citas = []
    if wallet_seleccionada:
        try:
            response = requests.get(f'{DATA_SERVICE_URL}/api/citas/wallet/{wallet_seleccionada}')
            if response.status_code == 200:
                citas = response.json().get('citas', [])
            else:
                print(f"Error obteniendo citas: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error conectando con servicio de datos: {e}")
    
    return render_template('ver_citas.html',
                         citas=citas,
                         wallets=lista_wallets,
                         wallet_seleccionada=wallet_seleccionada)


@app.route('/ver_historial')
def ver_historial():
    if 'wallet_address' not in session:
        return redirect(url_for('auth', next='/ver_historial'))
    
    wallet_address = session.get('wallet_seleccionada', session['wallet_address'])
    wallet_address= wallet_address.lower()
    print(f"Usando wallet para historial: {wallet_address}") 
    
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
            datos = {"error": "No se encontró historial médico para esta cartera"}
        else:
            datos = {"error": "Error obteniendo información del historial"}
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con servicio de datos: {e}")
        datos = {"error": "Error de conexión con el servicio de datos"}
    
    return render_template("ver_historial.html", 
                         historial=datos, 
                         wallet_actual=wallet_address)




if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5006)