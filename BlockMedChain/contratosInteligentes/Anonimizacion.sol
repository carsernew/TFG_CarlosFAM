// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Message {
    string public mensaje;

    constructor() {
        mensaje = "Anonimizar";
    }

    function setMensaje(string memory _nuevoMensaje) public {
        mensaje = _nuevoMensaje;
    }

    function getMensaje() public view returns (string memory) {
        return mensaje;
    }
}