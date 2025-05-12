// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CitaIPFS {
    event CitaRegistrada(address indexed paciente, string cid);
    event CitaEliminada(address indexed paciente, string cid);

    struct Cita {
        address paciente;
        string cid;
        uint256 timestamp;
        bool activa;
    }

    Cita[] public citas;

    function guardarCita(string memory cid) public returns (uint256) {
        citas.push(Cita(msg.sender, cid, block.timestamp, true));
        emit CitaRegistrada(msg.sender, cid);
        return citas.length - 1;
    }

    function borrarCita(string memory cid) public returns (bool) {
        for (uint256 i = 0; i < citas.length; i++) {
            if (
                keccak256(bytes(citas[i].cid)) == keccak256(bytes(cid)) &&
                citas[i].paciente == msg.sender &&
                citas[i].activa
            ) {
                citas[i].activa = false;
                emit CitaEliminada(msg.sender, cid);
                return true;
            }
        }
        return false;
    }

    function totalCitas() public view returns (uint256 total) {
        for (uint256 i = 0; i < citas.length; i++) {
            if (citas[i].activa) {
                total++;
            }
        }
    }
}




