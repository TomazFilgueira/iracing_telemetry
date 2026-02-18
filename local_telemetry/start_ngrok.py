import os
import subprocess
import sys
from config import NGROK_AUTH_TOKEN

def start_remote_access():
    if NGROK_AUTH_TOKEN == "COLE_SEU_TOKEN_AQUI":
        print("❌ ERRO: O NGROK_AUTH_TOKEN não foi configurado no arquivo config.py.")
        print("Por favor, peça ao usuário para inserir o token no arquivo de configuração.")
        return

    try:
        print("🌐 Configurando autenticação do Ngrok...")
        # Configura o token no sistema (roda silenciosamente)
        subprocess.run(["ngrok", "config", "add-authtoken", NGROK_AUTH_TOKEN], check=True, capture_output=True)
        
        print("🚀 Iniciando túnel HTTP na porta 8501 (Streamlit)...")
        print("🔗 O link público aparecerá abaixo em 'Forwarding'.")
        
        # Inicia o túnel e mantém a janela aberta
        os.system("ngrok http 8501")
        
    except FileNotFoundError:
        print("❌ ERRO: O executável 'ngrok' não foi encontrado.")
        print("Certifique-se de que o ngrok.exe está na pasta do projeto ou no PATH do Windows.")
    except Exception as e:
        print(f"⚠️ Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    start_remote_access()