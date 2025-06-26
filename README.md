# 📘 GUÍA BÁSICA DE BLOCKMEDCHAIN

Esta guía te ayudará a poner en marcha la aplicación **BlockMedChain** y comenzar a realizar pruebas de forma local y segura.

---

## 1. 🔐 Cartera MetaMask (Red de Ethereum de prueba: Sepolia)

### 🔽 Descarga de MetaMask

1. Ve al sitio oficial: [https://metamask.io](https://metamask.io)
2. Descarga e instala la extensión desde la tienda oficial del navegador.
3. Al abrirla:
   - Crea una nueva wallet o importa una existente.
   - **Guarda bien tu frase secreta de recuperación (12 palabras).**
   - Copia y guarda tu dirección pública (será necesaria para las pruebas).

### ⚙️ Configuración de la red Sepolia

1. Abre MetaMask.
2. Haz clic en el selector de red (arriba donde dice “Ethereum Mainnet”).
3. Clic en “Mostrar/ocultar redes de prueba”.
4. Activa la opción para mostrar redes de prueba.
5. Selecciona **Sepolia Test Network**.

---

## 2. 🗂 Tener IPFS instalado y funcionando

### 🛠 Instalación

```bash
tar -xvzf go-ipfs_vX.X.X.tar.gz
cd go-ipfs
sudo bash install.sh
```

### Despliegue 

```bash
ipfs init
ipfs daemon
```
## 3. 📦 Instalación de paquetes necesarios

Instala los siguientes paquetes para que la aplicación funcione correctamente:

### Python

```bash
pip install flask
pip install PyJWT
pip install web3
```

### Node.js

```bash
npm install web3
npm install ethers
```

## 4. 🔏 Configuración de autenticación

Para acceder a la aplicación:

  - Dirígete a la carpeta autentificacion/wallets.
  - Pega debajo de la última cartera tu dirección pública de MetaMask (en la red Sepolia).
  - Colócala en las secciones donde desees realizar pruebas.

## ✅ Listo

Una vez completados estos pasos, podrás utilizar la aplicación BlockMedChain con total libertad para realizar pruebas y desarrollo.
