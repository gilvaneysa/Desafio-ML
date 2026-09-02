import requests
import urllib3

# Desativa alertas de certificado SSL autoassinado (comum em redes locais)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def testar_ping_fortigate(host_fgt, api_token, origem_ip, destino_ip):
    """
    Dispara um comando de ping via método POST na API do FortiGate.
    """
    url = f"https://{host_fgt}/api/v2/monitor/router/ping/run"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "address": destino_ip,
        "source": origem_ip,
        "count": 5
    }
    
    print(f"\n[FortiGate] Executando comando de ping via POST de {origem_ip} para {destino_ip}...")
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=15)
        response.raise_for_status()
        dados = response.json()
        
        # Analisa o retorno da API do FortiOS
        resultado = dados.get("results", {})
        packets_received = resultado.get("packets_received", 0)
        
        if packets_received > 0:
            print(f"[SUCESSO] FortiGate alcançou o destino! Pacotes recebidos: {packets_received}/5")
            return True
        else:
            print(f"[FALHA] FortiGate não obteve resposta do destino {destino_ip}.")
            return False
    except Exception as e:
        print(f"[ERRO] Falha ao comunicar com a API do FortiGate: {e}")
        return False


def testar_ping_paloalto(host_pa, api_key, destino_ip):
    """
    Dispara um comando de ping operacional via XML API do Palo Alto.
    """
    url = f"https://{host_pa}/api/"
    cmd = f"<ping><host>{destino_ip}</host></ping>"
    params = {
        "type": "op",
        "cmd": cmd,
        "key": api_key
    }
    
    print(f"\n[Palo Alto] Disparando ping para {destino_ip}...")
    try:
        response = requests.post(url, data=params, verify=False, timeout=15)
        response.raise_for_status()
        
        # Verifica se o XML de resposta indica sucesso (procurando por 'success' ou estatísticas de pacotes)
        if "success" in response.text.lower() and "loss = 0%" in response.text:
            print(f"[SUCESSO] Palo Alto alcançou o destino com 0% de perda!")
            print(response.text)
            return True
        else:
            print(f"[FALHA / ALERTA] O teste de ping do Palo Alto retornou perdas ou falhas.")
            print(response.text)
            return False
    except Exception as e:
        print(f"[ERRO] Falha ao comunicar com a API do Palo Alto: {e}")
        return False


if __name__ == "__main__":
    # Exemplo de configuração (substitua pelos dados reais ou carregue do seu arquivo YAML)
    FGT_IP = "10.10.100.10"
    FGT_TOKEN = "SEU_TOKEN_FORTIGATE"
    ORIGEM_FGT = "10.10.10.1"      # IP da interface interna ou do local selector
    DESTINO_REMOTO = "10.20.20.10" # IP do host na ponta oposta
    
    PA_IP = "10.10.100.20"
    PA_KEY = "SUA_API_KEY_PALOALTO"

    # Executa o teste através do FortiGate
    testar_ping_fortigate(FGT_IP, FGT_TOKEN, ORIGEM_FGT, DESTINO_REMOTO)
    
    # Executa o teste através do Palo Alto
    testar_ping_paloalto(PA_IP, PA_KEY, "10.10.10.1")