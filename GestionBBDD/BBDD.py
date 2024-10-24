import sqlite3
import json
import os

# Función para crear la base de datos y la tabla de pacientes
def crear_base_datos():
    conn = sqlite3.connect('pacientes.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        fecha_nacimiento DATE,
        sexo TEXT,
        direccion TEXT,
        telefono TEXT,
        correo TEXT
    )
    ''')
    
    cursor.execute('''
    INSERT INTO pacientes (nombre, apellido, fecha_nacimiento, sexo, direccion, telefono, correo)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Carlos', 'Martínez', '1990-01-15', 'M', 'Calle Falsa 123', '555-1234', 'carlos.martinez@email.com'))

    conn.commit()
    conn.close()
    print("Base de datos creada correctamente o ya existente.")

# Función para exportar la base de datos a un archivo JSON
def exportar_bd_a_json():
    conn = sqlite3.connect('pacientes.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM pacientes')
    pacientes = cursor.fetchall()

    column_names = [description[0] for description in cursor.description]

    pacientes_json = []
    for paciente in pacientes:
        paciente_dict = dict(zip(column_names, paciente))
        pacientes_json.append(paciente_dict)

    with open('pacientes.json', 'w') as json_file:
        json.dump(pacientes_json, json_file, indent=4)

    conn.close()
    print("Datos exportados a 'pacientes.json' correctamente.")

# Función para importar datos de un archivo JSON a la base de datos
def importar_json_a_bd():
    if not os.path.exists('pacientes.json'):
        print("El archivo 'pacientes.json' no existe.")
        return

    with open('pacientes.json', 'r') as json_file:
        pacientes_json = json.load(json_file)

    conn = sqlite3.connect('pacientes.db')
    cursor = conn.cursor()

    for paciente in pacientes_json:
        cursor.execute('''
        INSERT INTO pacientes (nombre, apellido, fecha_nacimiento, sexo, direccion, telefono, correo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (paciente['nombre'], paciente['apellido'], paciente['fecha_nacimiento'], 
              paciente['sexo'], paciente['direccion'], paciente['telefono'], paciente['correo']))

    conn.commit()
    conn.close()
    print("Datos importados desde 'pacientes.json' correctamente.")

# Función para leer y mostrar todos los registros de la base de datos
def leer_base_datos():
    conn = sqlite3.connect('pacientes.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM pacientes')
    pacientes = cursor.fetchall()

    print("\n--- Lista de Pacientes ---")
    for paciente in pacientes:
        print(f"ID: {paciente[0]}, Nombre: {paciente[1]}, Apellido: {paciente[2]}, "
              f"Fecha de Nacimiento: {paciente[3]}, Sexo: {paciente[4]}, "
              f"Dirección: {paciente[5]}, Teléfono: {paciente[6]}, Correo: {paciente[7]}")

    conn.close()

# Función para mostrar un menú de opciones
def menu():
    while True:
        print("\n--- Menú ---")
        print("1. Exportar base de datos a JSON")
        print("2. Importar datos desde JSON a base de datos")
        print("3. Leer y mostrar todos los registros de la base de datos")
        print("4. Salir")

        opcion = input("Elige una opción (1, 2, 3 o 4): ")

        if opcion == '1':
            exportar_bd_a_json()
        elif opcion == '2':
            importar_json_a_bd()
        elif opcion == '3':
            leer_base_datos()
        elif opcion == '4':
            print("Saliendo del programa.")
            break
        else:
            print("Opción no válida. Intenta de nuevo.")

# Crear la base de datos al inicio
crear_base_datos()

# Ejecutar el menú interactivo
menu()

