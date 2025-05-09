.PHONY: all autentificador pacientes_service ipfs run stop clean

# Configuraciones generales
PYTHON=python3

all: run

run: ipfs autentificador pacientes_service

autentificador:
	cd autentificador && $(PYTHON) app.py &

pacientes_service:
	cd pacientes_service && $(PYTHON) app.py &

ipfs:
	@echo "Iniciando nodo IPFS..."
	@ipfs daemon > ipfs.log 2>&1 &

stop:
	@echo "Deteniendo microservicios y nodo IPFS..."
	@pkill -f "autentificador/app.py" || true
	@pkill -f "pacientes_service/app.py" || true
	@pkill -f "ipfs daemon" || true

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
