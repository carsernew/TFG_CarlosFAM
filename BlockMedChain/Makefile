.PHONY: all autentificador pacientes_service doctores_service laboratorios_service gestioncitas ipfs run stop clean

# Configuraciones generales
PYTHON=python3

all: run

run: ipfs autentificador pacientes_service doctores_service laboratorios_service gestioncitas

autentificador:
	cd autentificador && $(PYTHON) app.py &

pacientes_service:
	cd pacientes_service && $(PYTHON) app.py &

gestioncitas:
	cd gestioncitas && $(PYTHON) app.py &

doctores_service:
	cd doctores_service && $(PYTHON) app.py &

laboratorios_service:
	cd laboratorios_service && $(PYTHON) app.py &
ipfs:
	@echo "Iniciando nodo IPFS..."
	@ipfs daemon > ipfs.log 2>&1 &

stop:
	@echo "Deteniendo microservicios y nodo IPFS..."
	@pkill -f "autentificador/app.py" || true
	@pkill -f "pacientes_service/app.py" || true
	@pkill -f "gestioncitas/app.py" || true
	@pkill -f "doctores_service/app.py" || true
	@pkill -f "laboratorios_service/app.py" || true
	@pkill -f "ipfs daemon" || true

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
