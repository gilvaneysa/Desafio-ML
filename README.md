# Configurador de Switch Cisco e Automação de Rede

Ferramenta desenvolvida em Python com interface gráfica (Tkinter) para gerenciar, realizar backup completo e aplicar configurações (como Hostname e VLANs) em switches Cisco através de SSH ou Telnet.

## Pré-requisitos

Certifique-se de possuir o **Python 3** instalado em sua máquina antes de prosseguir com os passos abaixo.

---

## Guia de Instalação e Execução

### No Linux (Ubuntu)

1. Atualize os pacotes do sistema pelo terminal:
   ```bash
   sudo apt update
   ```

2. Instale o suporte à interface gráfica (Tkinter) e o gerenciador de ambientes virtuais:
   ```bash
   sudo apt install python3-tk
   sudo apt install python3.14-venv
   ```

3. Instale a biblioteca de automação de rede (`netmiko`):
   ```bash
   python3 -m pip install netmiko
   ```
   *Caso receba um erro informando sobre ambiente gerenciado externamente, utilize a flag de sistema:*
   ```bash
   python3 -m pip install netmiko --break-system-packages
   ```
   *Ou se preferir realizar a instalação padrão via pip:*
   ```bash
   pip install netmiko
   ```

4. Navegue até a pasta do projeto e execute o script:
   ```bash
   python3 Script.py
   ```

---

### No Windows

1. Baixe e instale a versão mais recente do [Python 3](https://www.python.org/). **Atenção:** Marque a caixa *"Add Python to PATH"* na primeira tela do instalador.

   ---
   ## OBSERVAÇÃO 
   Caso vc tenha esquecido de marcar a caixa: "Add Python to PATH" Não precisa necessariamente reinstalar.
   No Windows:
   Configurações → Sistema → Sobre → Configurações avançadas do sistema → Variáveis de Ambiente
   Em Variáveis de usuário, edite Path e adicione os diretórios do Python, normalmente semelhantes a:
   
   C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\
   C:\Users\SEU_USUARIO\AppData\Local\Programs\Python\Python313\Scripts\
   C:\Program Files\Python313
   
   

3. Abra o Prompt de Comando (CMD) ou PowerShell e instale o pacote de dependência:
   ```bash
   python -m pip install netmiko
   ```

4. Acesse o diretório onde o arquivo do programa está salvo e execute-o:
   ```bash
   python Script.py
   ```

---
## OBSERVAÇÃO 
 A máquina que executará o script deverá ter conectividade com o switch que deseja configurar.

## Funcionalidades da Ferramenta

* **Suporte a Múltiplos Protocolos:** Conecte-se via SSH (`cisco_ios`) ou Telnet (`cisco_ios_telnet`).
* **Validação de Entradas:** O script valida se o ID da VLAN está no intervalo permitido (1 a 4094) e se o nome do Hostname não contém caracteres inválidos ou espaços.
* **Backup Automático:** Gera um arquivo de texto contendo a configuração completa (`running-config`) e a tabela de VLANs do equipamento.
* **Checagem de Duplicidade:** Alerta caso a VLAN ou o nome escolhido já existam no switch, permitindo que você decida se deseja prosseguir.

## Outros Arquivos 

Este repositório também contém os seguintes arquivos complementares:

Backup do Switch (.txt): arquivo de configuração de um switch de laboratório, gerado pelo script de automação. 
O backup tem como objetivo demonstrar as configurações aplicadas e o resultado obtido por meio da execução do script.
Plano de Automação — VPN IPsec FortiGate ↔ Palo Alto (.md): documento em formato Markdown que apresenta o plano de execução para a automação
da criação de túneis VPN IPsec entre FortiGate e Palo Alto, incluindo as principais etapas, configurações e considerações para a implementação.
Arquivos de configuração de VPN: exemplos das configurações necessárias para o estabelecimento de uma VPN IPsec entre FortiGate e Palo Alto, servindo como referência para a automação.
Script de teste de conectividade via API: script utilizado para validar a comunicação com os equipamentos por meio de API após 
o estabelecimento do túnel VPN, permitindo verificar se a conectividade e a integração com os dispositivos estão funcionando conforme esperado.
