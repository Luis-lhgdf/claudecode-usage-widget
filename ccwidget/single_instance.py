"""Garante uma copia so do widget, e traz a existente para frente.

Clicar duas vezes no atalho abriria duas janelas iguais, uma por cima da outra.
Aqui a primeira copia reserva uma porta local; as seguintes nao conseguem
reserva-la, avisam quem ja esta rodando e saem.

A porta funciona melhor que um arquivo de trava para isto: ela e liberada pelo
sistema se o processo morrer de qualquer jeito -- inclusive um encerramento
forcado --, sem deixar trava velha para trás, e ainda serve de canal para pedir
que a janela apareca.
"""

from __future__ import annotations

import socket
import threading

HOST = "127.0.0.1"
PORT = 49731          # porta alta e fixa, fora das faixas de uso comum
HELLO = b"CCWIDGET-SHOW\n"
ACK = b"CCWIDGET-OK\n"
TIMEOUT = 1.5


def claim() -> socket.socket | None:
    """Tenta ser a copia unica.

    Devolve o socket reservado, ou None se outra copia ja o tem.
    """
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Sem SO_REUSEADDR de proposito: o bind precisa falhar quando ja existe
        # alguem escutando, que e justamente o sinal que procuramos.
        servidor.bind((HOST, PORT))
        servidor.listen(2)
        return servidor
    except OSError:
        servidor.close()
        return None


def wake_existing() -> bool:
    """Pede para a copia em execucao aparecer.

    Devolve True se ela respondeu. False significa que a porta esta ocupada por
    outro programa qualquer -- nesse caso o widget deve abrir normalmente, em
    vez de se recusar a iniciar por causa de um vizinho.
    """
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as cliente:
            cliente.sendall(HELLO)
            return cliente.recv(len(ACK)) == ACK
    except OSError:
        return False


def serve(servidor: socket.socket, ao_chamar) -> threading.Thread:
    """Escuta pedidos das outras copias numa thread.

    `ao_chamar` roda na thread do listener, entao deve apenas sinalizar; quem
    mexe na janela e a thread da interface. Tkinter nao e seguro para uso
    concorrente.
    """

    def laco() -> None:
        while True:
            try:
                conexao, _ = servidor.accept()
            except OSError:
                return  # socket fechado: o widget esta encerrando
            with conexao:
                try:
                    if conexao.recv(len(HELLO)) == HELLO:
                        conexao.sendall(ACK)
                        ao_chamar()
                except OSError:
                    pass

    thread = threading.Thread(target=laco, daemon=True)
    thread.start()
    return thread
