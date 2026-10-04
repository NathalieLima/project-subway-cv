"""Receptor simples para testar os comandos sem abrir o jogo.

Execute este arquivo em outro terminal. Ele imprime LEFT/RIGHT/UP/DOWN/F5 ao
receber os eventos globais gerados pelo controlador.
"""
from pynput import keyboard


def on_press(key):
    mapping = {
        keyboard.Key.left: "LEFT",
        keyboard.Key.right: "RIGHT",
        keyboard.Key.up: "UP",
        keyboard.Key.down: "DOWN",
        keyboard.Key.f5: "F5 / REINICIAR",
    }
    if key in mapping:
        print(f"Recebido: {mapping[key]}")
    elif key == keyboard.Key.esc:
        print("Encerrando receptor.")
        return False
    return None


if __name__ == "__main__":
    print("Aguardando setas e F5 globais. Pressione ESC para sair.")
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
