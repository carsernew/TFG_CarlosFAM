import requests
import json
import os

db_archivo = "ipfs_rutas.json"
if not os.path.exists(db_archivo):
    with open(db_archivo, 'w') as f:
        json.dump([], f)


def subir_json_a_ipfs(ruta_json):
    try:
        with open(ruta_json, 'rb') as f:
            files = {'file': f}
            response = requests.post('http://127.0.0.1:5001/api/v0/add', files=files)
            
            if response.status_code == 200:
                res = response.json()
                cid = res['Hash'] 
                print(f"Archivo '{ruta_json}' subido a IPFS. CID: {cid}")
                
                with open(db_archivo, 'r+') as f:
                    archivos_subidos = json.load(f)
                    archivos_subidos.append({"archivo": ruta_json, "cid": cid})
                    f.seek(0)
                    json.dump(archivos_subidos, f, indent=4)
                return cid

            else:
                print(f"Error subiendo archivo a IPFS: {response.content}")
                return None

    except Exception as e:
        print(f"Error subiendo archivo a IPFS: {e}")
        return None


def descargar_json_de_ipfs(cid, nombre_archivo_salida):
    try:
        url = f'http://127.0.0.1:5001/api/v0/cat?arg={cid}'
        response = requests.post(url)
        if response.status_code == 200:
            with open(nombre_archivo_salida, 'wb') as f:
                f.write(response.content)
            print(f"Archivo descargado desde IPFS y guardado como: {nombre_archivo_salida}")
        else:
            print(f"Error descargando archivo de IPFS: {response.content}")
    except Exception as e:
        print(f"Error descargando archivo de IPFS: {e}")

def ver_archivos_subidos():
    try:
        with open(db_archivo, 'r') as f:
            archivos_subidos = json.load(f)
            if archivos_subidos:
                print("\nArchivos subidos a IPFS:")
                for archivo in archivos_subidos:
                    print(f"Archivo: {archivo['archivo']} | CID: {archivo['cid']}")
            else:
                print("No hay archivos subidos a IPFS.")
    except Exception as e:
        print(f"Error leyendo la base de datos: {e}")

# Menú interactivo
def menu():
    while True:
        print("\n--- Menú IPFS ---")
        print("1. Subir archivo JSON a IPFS")
        print("2. Descargar archivo JSON desde IPFS")
        print("3. Ver archivos subidos")
        print("4. Salir")

        opcion = input("Elige una opción: ")

        if opcion == '1':
            ruta_json = input("Introduce la ruta del archivo JSON que quieres subir: ")
            if os.path.exists(ruta_json):
                subir_json_a_ipfs(ruta_json)
            else:
                print(f"El archivo {ruta_json} no existe.")
        
        elif opcion == '2':
            cid = input("Introduce el CID del archivo que deseas descargar: ")
            nombre_archivo_salida = input("Introduce el nombre con el que deseas guardar el archivo descargado: ")
            descargar_json_de_ipfs(cid, nombre_archivo_salida)
        
        elif opcion == '3':
            ver_archivos_subidos()

        elif opcion == '4':
            print("Saliendo...")
            break
        
        else:
            print("Opción no válida, por favor elige nuevamente.")

if __name__ == "__main__":
    menu()
