# Plano de Automação — VPN IPsec FortiGate ↔ Palo Alto

## 1. Objetivo

Este documento define um plano técnico para automatizar a implantação de uma VPN IPsec site-to-site entre um **FortiGate** e um **Palo Alto Networks**, contemplando desde a coleta e validação dos parâmetros até a configuração, ativação, validação operacional e rollback.

O objetivo da automação é reduzir a intervenção manual, padronizar configurações, minimizar erros de parametrização e produzir evidências suficientes para auditoria e troubleshooting.

A automação não deverá gerar configurações duplicadas nem alterar parâmetros que não façam parte do escopo da VPN.

---

# 2. Escopo

## 2.1 Equipamentos

| Função | Fabricante | Equipamento |
|---|---|---|
| Endpoint A | Fortinet | FortiGate |
| Endpoint B | Palo Alto | Palo Alto Networks Firewall |

## 2.2 Escopo funcional

A automação deverá contemplar:

1. Validação dos pré-requisitos.
2. Coleta dos parâmetros da VPN.
3. Validação das variáveis de entrada.
4. Configuração do FortiGate.
5. Configuração do Palo Alto.
6. Configuração das redes locais/remotas.
7. Configuração das políticas de segurança.
8. Ativação da VPN.
9. Validação do túnel IPsec.
10. Testes de conectividade.
11. Coleta de evidências.
12. Rollback em caso de falha.

---

# 3. Arquitetura de referência

Exemplo de arquitetura:

```text
                 INTERNET
                    |
          +---------+---------+
          |                   |
     Public IP A         Public IP B
          |                   |
   +------+-------+    +------+-------+
   |   FortiGate  |====| Palo Alto    |
   |              | IPsec|            |
   +------+-------+    +------+-------+
          |                   |
      LAN A                 LAN B
  10.10.10.0/24         10.20.20.0/24
```

O túnel deverá estabelecer uma associação IPsec entre os dois firewalls.

Exemplo:

```text
FortiGate:
Public IP: 200.10.10.10
LAN:       10.10.10.0/24

Palo Alto:
Public IP: 200.20.20.20
LAN:       10.20.20.0/24
```

Fluxo esperado:

```text
10.10.10.0/24
      |
  FortiGate
      |
   IPsec VPN
      |
  Palo Alto
      |
10.20.20.0/24
```

---

# 4. Pré-requisitos

Antes de iniciar qualquer alteração, a automação deverá validar os seguintes requisitos.

## 4.1 Conectividade administrativa

O servidor de automação deverá possuir conectividade administrativa com os dois equipamentos.

Exemplo:

```text
Automation Server
       |
       +---- HTTPS/API ----> FortiGate
       |
       +---- HTTPS/API ----> Palo Alto
```

O acesso deverá ser realizado por APIs oficiais.

### FortiGate

Preferencialmente utilizar:

```text
FortiOS REST API
```

### Palo Alto

Preferencialmente utilizar:

```text
PAN-OS XML API
```
---

# 5. Arquitetura de comunicação

```text
                         Python Automation
                                |
                     HTTPS / TLS 1.2+
                                |
               +----------------+----------------+
               |                                 |
               v                                 v
        FortiGate API                       Palo Alto API
               |                                 |
        REST API                         REST API / XML API
               |                                 |
               v                                 v
        FortiOS CMDB                       PAN-OS
```

O servidor onde o Python será executado deve ter conectividade somente com as interfaces de gerenciamento dos firewalls, preferencialmente através de uma rede de gerenciamento dedicada.

## FortiGate — API utilizada

**FortiOS REST API**

```text
https://<FORTIGATE>/api/v2/
```

**Exemplo:**

```text
https://10.10.100.10/api/v2/cmdb/firewall/address
```

A documentação oficial demonstra a utilização do endpoint `api/v2/cmdb/firewall/address` e autenticação através de `Authorization: Bearer <API-TOKEN>`.
O acesso deve ser feito por HTTPS.

**Referência:** https://docs.fortinet.com/document/fortigate/latest/administration-guide/940602/using-apis

### Preparação do FortiGate

Essa etapa é apenas no FortiGate.

A automação deve possuir uma identidade própria. O FortiGate deverá possuir um REST API Admin com token específico para a automação.

Isso permite:

- Auditoria.
- Revogação independente.
- Controle de permissões.
- Identificação das alterações.
- Rotação de credenciais.

```text
Python
   |
   | Bearer Token
   v
FortiGate
   |
   +--- API Admin
```

O token não deve ficar no Git; o ideal seria ficar no Secret Manager.
O FortiGate deve aceitar a administração/API apenas a partir do IP do servidor de automação.

### Exemplo FortiGate — GET

```python
import requests

url = "https://10.10.100.10/api/v2/cmdb/firewall/address"

headers = {
    "Authorization": "Bearer API_TOKEN",
    "Accept": "application/json"
}

response = requests.get(
    url,
    headers=headers,
    timeout=10,
    verify=True
)

response.raise_for_status()
data = response.json()
print(data)
```

A biblioteca Python utilizada é a `requests`.

O endpoint e payload exatos precisam ser validados contra a versão específica do FortiOS utilizada, porque o schema CMDB pode variar entre releases.
A automação deve ser desenvolvida e testada contra a versão de FortiOS efetivamente utilizada em produção.

## Palo Alto — estratégia de API

O PAN-OS disponibiliza REST API e XML API.
A REST API é adequada para operações CRUD de objetos e políticas, mas a própria Palo Alto documenta que ela cobre apenas um subconjunto das funções e que o XML API ainda é necessário para determinadas operações, incluindo completar configurações e commits.

Portanto:

```text
Palo Alto
    |
    +---- REST API
    |       |
    |       +-- CRUD
    |       +-- Objects
    |       +-- Policies
    |
    +---- XML API
            |
            +-- Configuration
            +-- Operational commands
            +-- Commit
            +-- funções não cobertas pelo REST
```

A API utiliza uma API Key.
A documentação atual permite enviar a chave no header:

```text
X-PAN-KEY: <API_KEY>
```

**Referência:** https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-panorama-api/about-the-pan-os-xml-api/structure-of-a-pan-os-xml-api-request/api-authentication-and-security

### Preparação do Palo Alto

A automação deve possuir uma identidade própria. Criaria um administrador exclusivo. A conta deve ter apenas as permissões necessárias. A documentação do PAN-OS destaca que as APIs podem utilizar roles administrativos granulares, permitindo restringir o acesso a determinadas funcionalidades.

O gerenciamento deve ser acessível apenas pelo servidor de automação.

### Palo Alto — REST API

O padrão de endpoint REST é:

```text
https://<IP>/restapi/<PAN-OS-version>/<resource>
```

**Exemplo:**

```python
url = (
    "https://10.10.100.20/"
    "restapi/v11.1/..."
)

headers = {
    "X-PAN-KEY": api_key,
    "Accept": "application/json"
}
```

### Palo Alto — XML API — exemplo

```python
url = "https://10.10.100.20/api/"

params = {
    "type": "config",
    "action": "show",
    "key": api_key,
    "xpath": "/config/..."
}

response = requests.post(
    url,
    params=params,
    timeout=10,
    verify=True
)
```

Mesma biblioteca Python utilizada no FortiGate.

---

# 6. Variáveis da automação

A automação não deverá possuir valores de produção diretamente no código.

Todos os parâmetros deverão ser tratados como variáveis.

Exemplo de arquivo:

```yaml
vpn:
  name: "VPN-FGT-PA-001"

  ike:
    version: "ikev2"
    encryption: "aes256"
    authentication: "sha256"
    dh_group: "14"
    lifetime: 28800

  ipsec:
    encryption: "aes256"
    authentication: "sha256"
    pfs: "group14"
    lifetime: 3600

fortigate:
  management_ip: "192.168.100.10"
  wan_interface: "wan1"
  public_ip: "200.10.10.10"
  local_network: "10.10.10.0/24"

paloalto:
  management_ip: "192.168.100.20"
  wan_interface: "ethernet1/1"
  public_ip: "200.20.20.20"
  local_network: "10.20.20.0/24"

traffic:
  local_network: "10.10.10.0/24"
  remote_network: "10.20.20.0/24"

tunnel_ip:
  VPN-FGT-PA-001: "169.255.1.1/30"
  VPN-PA-FGT-001: "169.255.1.2/30"

```

A chave pré-compartilhada (**PSK**) deverá ser armazenada separadamente, preferencialmente em um **secret manager**, e nunca diretamente no repositório Git. Em caso de um script interativo, o usuário poderia preencher os parâmetros obrigatórios, inclusive a chave PSK.

---

# 7. Fase 1 — Validação de entrada

## Objetivo

Garantir que os dados fornecidos para a criação da VPN sejam válidos antes de qualquer alteração nos equipamentos.

Essa fase é crítica porque uma configuração IPsec pode ser tecnicamente aceita pelo firewall e ainda assim não estabelecer o túnel devido a uma inconsistência entre os dois dispositivos.

## Validações

A automação deverá validar:

- IP público do FortiGate.
- IP público do Palo Alto.
- Interface WAN.
- Redes locais.
- Redes remotas.
- IKE version.
- Algoritmos de criptografia.
- Algoritmos de autenticação.
- DH Group.
- PFS.
- Lifetimes.
- Nome da VPN.

Essa validação serve para verificar se foram preeenhido alguma parâmetros não aceito pelos dispositivos, como :
- Formato de endereçamento inválido.
-Nome no túnel VPN com espaço ou com tamanho maior que 15 caracteres para FortiGate e 63 para Palo Alto.
-Formato de nome da inteface que é diferente em ambos os equipamentos.
- Formato da escrita dos algoritmos de criptografia e autenticação. Exemplo: no FortiGate, `aes256-sha256` seria equivalente a `aes-256-cbc` do Palo Alto.

## Validação de redes


Exemplo:

```text
FortiGate local:
10.10.10.0/24

Palo Alto local:
10.20.20.0/24
```

A automação deverá garantir que:

```text
FortiGate local   == Palo Alto remote
FortiGate remote  == Palo Alto local
```

Ou seja:

```text
FGT local  = 10.10.10.0/24
FGT remote = 10.20.20.0/24

PA local   = 10.20.20.0/24
PA remote  = 10.10.10.0/24
```

---

# 8. Fase 2 — Validação dos equipamentos

Nesta fase a automação deverá consultar os equipamentos antes de realizar alterações.

## FortiGate

Coletar:

- Hostname.
- Serial number.
- FortiOS version.
- Interface WAN.
- IP da interface WAN.
- Rotas existentes.
- VPNs existentes.
- Objetos de firewall relacionados.
- VDOM, quando utilizado. (Se houver VDOM os parâmetros  de configuração devem incluir a informações da VDOM)

Exemplo conceitual:

```text
GET /api/v2/monitor/system/status - consultar o status geral e as informações de saúde do sistema do FortiGate.
GET /api/?type=op&cmd=<show><system><info></info></system></show>&key=< SUA_API_KEY> consultar o status geral e as informações de saúde do sistema do Palo Alto.
```

e consultas aos objetos de configuração necessários.

## Palo Alto

Coletar:

- Hostname.
- Serial number.
- PAN-OS version.
- Interfaces.
- Virtual Router.
- Security Zones.
- IPsec Tunnels existentes.
- IKE Gateways existentes.
- Security Policies.
- Routes.

É importante consultar as rotas existentes nos equipamentos para evitar possível conflito de roteamento. Essa verificação é extremamente importante.

---

# 9. Fase 3 — Verificação de conflitos

Antes de criar a VPN, verificar se já existem objetos com os mesmos nomes ou parâmetros.

Exemplo:

```text
VPN-FGT-PA-001
IKE-FGT-PA-001
IPSEC-FGT-PA-001
ADDR-LAN-FGT-001
ADDR-LAN-PA-001
```

A automação deverá classificar cada objeto como:

```text
EXISTE E ESTÁ CORRETO
EXISTE E ESTÁ INCORRETO
NÃO EXISTE
```

### Regra de idempotência

Se o objeto já existir e estiver correto:

```text
Não alterar.
```

Se existir e estiver incorreto:

```text
Abortar ou corrigir somente se explicitamente autorizado.
```

Se não existir:

```text
Criar.
```

Essa lógica evita que uma execução repetida gere objetos duplicados. Essa checagem se adaqua bastantes para a criação dos objetos que serão utilizados nas políticas de firewall.

---

# 10. Fase 4 — Backup / Snapshot

Antes de qualquer alteração, realizar backup da configuração.

## FortiGate

Coletar a configuração atual.

Exemplo conceitual:

```text
show full-configuration
```

O backup deverá ser armazenado com:

```text
hostname
serial
timestamp
change-id
```

Exemplo:

```text
FGT01_123456789_2026-08-30_103000.cfg
```

## Palo Alto

Realizar exportação da configuração candidata ou running configuration, conforme o método de automação adotado.

O backup deverá ser associado ao identificador da mudança.

Exemplo:

```text
CHANGE-ID: VPN-20260830-001
```

---

# 11. Fase 5 — Configuração do FortiGate

## 11.1 Phase 1 / IKE

Criar o túnel IPsec utilizando os parâmetros definidos.

Exemplo conceitual:

```text
VPN:
VPN-FGT-PA-001

Remote Gateway:
200.20.20.20

IKE:
IKEv2

Encryption:
AES-256

Authentication:
SHA-256

DH:
Group 14

Lifetime:
28800 seconds
```

No FortiGate, a configuração deverá ser criada utilizando a API ou mecanismo de automação escolhido.

### Comentário

No caso de um script único, algumas variáveis podem ser utilizadas em ambas os equipamentos como IKE, autenticação e criptografia. Parâmetros que tem o mesmo valor mas formatos diferentes precisam ter variáveis diferentes.

---

# 12. Fase 6 — Configuração da Phase 2

Configurar os parâmetros IPsec.

Exemplo:

```text
Encryption:
AES-256

Authentication:
SHA-256

PFS:
Group 14

Lifetime:
3600 seconds
```

Traffic selectors:

```text
Local:
10.10.10.0/24

Remote:
10.20.20.0/24
```

O conceito é:

```text
FGT:
Local  = 10.10.10.0/24
Remote = 10.20.20.0/24

PA:
Local  = 10.20.20.0/24
Remote = 10.10.10.0/24
```

Os selectors precisam ser compatíveis nos dois lados.

---

# 13. Fase 7 — Objetos de endereço

Criar os objetos necessários.

Exemplo no FortiGate:

```text
ADDR-LAN-FGT
    10.10.10.0/24

ADDR-LAN-PA
    10.20.20.0/24
```

No Palo Alto:

```text
ADDR-LAN-PA
    10.20.20.0/24

ADDR-LAN-FGT
    10.10.10.0/24
```

### Boa prática

Os nomes deverão seguir um padrão previamente definido.

Exemplo:

```text
VPN_<SITE_A>_<SITE_B>
ADDR_<SITE>_<NETWORK>
IKE_<SITE_A>_<SITE_B>
IPSEC_<SITE_A>_<SITE_B>
```

Isso facilita troubleshooting e manutenção.

---

# 14. Fase 8 — Roteamento

A automação deverá configurar a rota necessária para encaminhar o tráfego para o túnel.

Exemplo conceitual no FortiGate:

```text
10.20.20.0/24
        ↓
VPN-FGT-PA-001
```

No Palo Alto:

```text
10.10.10.0/24
        ↓
IPsec-Tunnel-FGT-PA
```

## Importante

A estratégia de roteamento deverá ser definida antes da automação.

Possibilidades:

1. Rotas estáticas.
2. BGP sobre VPN.
3. OSPF sobre VPN.
4. Rotas dinâmicas específicas do ambiente.

Para uma VPN site-to-site simples, **rotas estáticas são a opção mais simples e previsível**.

---

# 15. Fase 9 — Security Policy

A automação deverá criar as políticas de segurança necessárias.

## FortiGate

Exemplo lógico:

```text
LAN
 ↓
VPN-FGT-PA-001
```

Policy:

```text
Source Interface:
LAN

Source:
10.10.10.0/24

Destination Interface:
VPN-FGT-PA-001

Destination:
10.20.20.0/24

Action:
ACCEPT
```

No sentido inverso:

```text
VPN-FGT-PA-001
        ↓
LAN
```

### NAT

Para comunicação site-to-site normalmente:

```text
NAT = disabled
```

A automação deverá validar explicitamente esse parâmetro.

---

# 16. Fase 10 — Configuração do Palo Alto

No Palo Alto deverão ser configurados os componentes necessários:

```text
IKE Crypto Profile
        ↓
IKE Gateway
        ↓
IPsec Crypto Profile
        ↓
IPsec Tunnel
        ↓
Virtual Router
        ↓
Security Policy
```

## Exemplo lógico

```text
IKE Crypto:
AES256
SHA256
DH14

IKE Gateway:
Peer = 200.10.10.10

IPsec Crypto:
AES256
SHA256
PFS14

IPsec Tunnel:
IPSEC-FGT-PA-001
```

A interface/túnel deverá ser associada à zona e ao Virtual Router conforme a arquitetura do Palo Alto.

---

# 17. Fase 11 — Commit / Aplicação da configuração

                    Python Automation
                           |
              +------------+------------+
              |                         |
          DRY-RUN                    APPLY
              |                         |
       Gera configuração        Valida + Aplica
              |                         |
              v                         v
            Scripts              APIs dos Firewalls
              |                  /              \
              |                 /                \
              v                v                  v
          .txt/.xml       FortiGate            Palo Alto
                              |                    |
                         Workspace Mode      Candidate Config
                              |                    |
                           Commit              Validate
                                                   |
                                                 Commit

Esta fase deverá ser tratada com cuidado porque os dois fabricantes possuem modelos diferentes de aplicação de configuração. De acordo com a arvore acima o script de automação pode gerar os arquivos de configuração ou aplicar a configuração via API.
Uma forma de prevenção e controle seria utilizarmos no FortiGate o Workspace mode. O Workspace Mode do FortiOS permite realizar um conjunto de alterações dentro de uma transação e só torná-las efetivas quando a transação é submetida.
Antes do commit, as alterações podem ser modificadas ou descartadas. Além disso, objetos envolvidos ficam bloqueados para evitar alterações concorrentes. o timeout padrão é de 5 minutos sem atividade. Se não houver atividade durante esse período,
a transação expira e todas as alterações pendentes são descartadas. Isso é importante caso haja alguma perda de conectividade com o equipamento em caso de configuração equivocada.
No palo alto poderiamos utilizar o Validate, que não faz a mesma coisa da workspace mode do FortiGate, mas ajuda a verificar a configuração antes do commit. O Validate consegue verificar coisas como:
sintaxe;
referências entre objetos;
parâmetros obrigatórios;
consistência da configuração;
erros que fariam o commit falhar.

O que é o DRY-RUN
Dry-run é um modo de execução em que a automação executa todas as validações e calcula o que faria, mas não realiza nenhuma alteração nos equipamentos. Função da automação para gerar os Scripts, caso a API não seja utilizada.

DRY-RUN - fases
```text
  [PASS] Parameters
  [PASS] Compatibility
  [PASS] Routing
  [PASS] Preflight

Changes:

FortiGate
  CREATE phase1-interface VPN-FGT-PA-001
  CREATE phase2-interface VPN-FGT-PA-001
  CREATE route 10.20.20.0/24
  CREATE policy 100

Palo Alto
  CREATE IKE Gateway
  CREATE IPsec Tunnel
  CREATE Route
  CREATE Security Policy

NO CHANGES APPLIED
```

## FortiGate

Aplicar a configuração através da API.

Após a alteração: Validar a configuração

```text
Configuração aplicada
        ↓
Validação
```

## Palo Alto

No Palo Alto existe separação entre:

```text
Candidate Configuration
        ↓
Commit
        ↓
Running Configuration
```

A automação deverá:

1. Criar/alterar configuração.
2. Validar a configuração candidata.
3. Executar commit.
4. Aguardar conclusão.
5. Validar o resultado do commit.

Não considerar a operação concluída somente porque a API aceitou a alteração.

---

# 18. Fase 12 — Validação da Phase 1

Após a aplicação, verificar a negociação IKE.

O resultado esperado:

```text
IKE SA = UP
```

Conceitualmente:

```text
FortiGate
    |
    | IKE
    |
Palo Alto

Status:
UP
```

A automação deverá registrar:

- Estado.
- Peer.
- IKE version.
- Proposal negociada.
- DH group.

---

# 19. Fase 13 — Validação da Phase 2

Depois da Phase 1, verificar a SA IPsec.

Resultado esperado:

```text
IPsec SA = UP
```

Validar:

```text
Local selector:
10.10.10.0/24

Remote selector:
10.20.20.0/24
```

Também verificar:

```text
Encapsulated packets > 0
Decapsulated packets > 0
```

Apenas verificar que o túnel aparece como `UP` não é suficiente.

Um túnel pode estar operacional na negociação IKE/IPsec e ainda assim não transportar tráfego corretamente devido a:

- Roteamento.
- Security Policy.
- NAT.
- Selector.
- ACL.
- Assimetria de rota.
- Firewall do host.

---

# 20. Fase 14 — Teste de conectividade

Realizar testes de ponta a ponta. Podemos realizar um Ping de uma interface LAN do equipamento (o IP da interface do Local Selector para o Remote Selector)

Exemplo:

```text
Host A
10.10.10.10

       ↓

FortiGate

       ↓

IPsec

       ↓

Palo Alto

       ↓

Host B
10.20.20.10
```

Teste:

```text
ping 10.20.20.10
```

Também deverá ser validado o retorno:

```text
Host B → Host A
```

---

# 21. Fase 15 — Validação dos contadores

A automação deverá coletar os contadores antes e depois do teste.

Exemplo:

```text
Antes:
TX = 1000
RX = 1200

Teste:
10 ICMP packets

Depois:
TX = 1010
RX = 1210
```

A alteração dos contadores fornece evidência de que o tráfego realmente passou pelo túnel.

---
# 22. Desafios e riscos da automação

A automação deverá considerar os principais desafios e riscos específicos de uma implantação de VPN IPsec entre fabricantes diferentes.

| Desafio / risco | Impacto | Tratamento previsto |
|---|---|---|
| Diferenças entre FortiOS e PAN-OS | Parâmetros equivalentes podem possuir nomes, formatos ou modelos de configuração diferentes. | Validar e converter os parâmetros antes da aplicação. |
| Incompatibilidade IKE/IPsec | O túnel pode não estabelecer ou negociar uma proposta diferente da esperada. | Executar compatibility check e validar a proposta efetivamente negociada. |
| Traffic Selectors | IKE/IPsec pode estar `UP` sem que o tráfego passe corretamente. | Validar selectors nos dois lados e testar tráfego. |
| Conflito de rotas | O tráfego pode seguir outra rota em vez do túnel. | Consultar rotas antes da alteração e validar após a implantação. |
| NAT e Security Policy | O túnel pode estar `UP`, mas o tráfego pode ser bloqueado ou sofrer NAT indevido. | Validar políticas, NAT e fluxo nos dois sentidos. |
| VDOM / VSYS / Virtual Router | A configuração pode ser aplicada no contexto lógico incorreto. | Coletar e validar o contexto antes da configuração. |
| Falha parcial entre os fabricantes | Um equipamento pode aplicar a alteração enquanto o outro falha. | Controlar o estado da execução e executar rollback conforme a etapa alcançada. |
| Falha de API ou Commit | A API pode aceitar a requisição sem que a configuração esteja efetivamente aplicada. | Validar o resultado da operação e realizar verificações pós-commit. |
| Execução repetida | Pode gerar objetos ou configurações duplicadas. | Utilizar idempotência e comparação do estado atual com o desejado. |
| Exposição de credenciais/PSK | Comprometimento das credenciais utilizadas pela automação. | Utilizar Secret Manager, privilégio mínimo, HTTPS e logs sem secrets. |

O principal risco operacional é a ausência de uma transação única entre os dois fabricantes. O FortiGate e o Palo Alto possuem mecanismos próprios para controle da configuração, mas não existe uma transação distribuída que faça o commit dos dois equipamentos de forma atômica. Portanto, a automação deverá controlar explicitamente o estado da execução e estar preparada para falhas parciais.

Além disso, `IKE SA = UP` e `IPsec SA = UP` não deverão ser considerados, isoladamente, como indicação de sucesso. A validação deverá continuar até confirmar roteamento, políticas, tráfego e incremento dos contadores TX/RX.

---


---

# 23. Fase 16 — Evidências

A automação deverá produzir um relatório final.

Exemplo:

```text
==================================================
VPN DEPLOYMENT REPORT
==================================================

Change ID:
VPN-20260830-001

VPN:
VPN-FGT-PA-001

FortiGate:
FGT01

Palo Alto:
PA01

IKE:
UP

IPsec:
UP

Local Network:
10.10.10.0/24

Remote Network:
10.20.20.0/24

Encryption:
AES256

Authentication:
SHA256

DH:
14

PFS:
14

Connectivity:
PASS

Traffic:
PASS

Configuration:
PASS

Overall Result:
SUCCESS
==================================================
```

---

# 24. Tratamento de erros

A automação deverá possuir tratamento específico para falhas.

## Exemplo

```text
Validação
   |
   +-- FAIL → Abort
   |
   +-- PASS
          |
       Backup
          |
       Configuração
          |
       Validação
          |
      +---+---+
      |       |
    PASS     FAIL
      |       |
   Commit   Rollback
      |
   Teste
      |
   SUCCESS
```

Nenhuma etapa posterior deverá ser executada quando uma etapa crítica falhar.

---

# 25. Estratégia de Rollback

O rollback deverá ser definido antes da implantação, para desfazer as configurações ou restaurar o backup em casos mais graves.

## Cenário 1 — Falha antes da aplicação

Nenhuma alteração deverá ser realizada.

```text
Abort
```

## Cenário 2 — Falha após configuração

Remover somente os objetos criados pela automação.

Exemplo:

```text
VPN
IKE Gateway
IPsec Tunnel
Routes
Policies
Address Objects
```

## Cenário 3 — Falha após commit

Restaurar a configuração anterior utilizando o mecanismo de rollback suportado pelo equipamento.

A automação deverá registrar:

```text
Rollback iniciado
Rollback concluído
Rollback validado
```

---

# 26. Idempotência

A automação deverá ser projetada para ser executada múltiplas vezes.

Exemplo:

### Primeira execução

```text
VPN não existe
       ↓
Criar VPN
       ↓
Configurar
       ↓
Validar
```

### Segunda execução

```text
VPN existe
       ↓
Parâmetros conferidos
       ↓
Configuração correta
       ↓
Nenhuma alteração necessária
```

Isso é fundamental para evitar configurações duplicadas.

---

# 27. Estrutura recomendada da automação

Uma estrutura possível utilizando Python:

```text

vpn-automation/
│
├── README.md
│
├── inventory/
│   └── production.yml # Ele define quais equipamentos existentes, como a automação deve acessá-los e em qual ambiente eles estão. IP, api_port, DNS
│
├── variables/
│   └── vpn-001.yml    # Esse arquivo define os parâmetros da VPN.Como: name, IKE, local_networks, autenticação e criptografia
│
│
├── secrets/
│   └── vault-reference.yml   # Armazena somente referências para o Secret Manager
│
├── src/
│   ├── main.py
│   ├── fortigate.py
│   ├── paloalto.py
│   └── secret_manager.py
│
├── tests/
│   └── test_vpn.py
│
├── reports/
│
└── logs/

Etapas de execução no FortiGate

class FortiGate:

    def connect(self):
        pass

    def get_routes(self):
        pass

    def get_interfaces(self):
        pass

    def get_vpn(self):
        pass

    def backup(self):
        pass

    def start_workspace(self):
        pass

    def create_phase1(self, config):
        pass

    def create_phase2(self, config):
        pass
		
  	def enderecar_Tunel(self, config):
        pass
		
    def create_route(self, config):
        pass

    def create_policy(self, config):
        pass

    def validate(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass

    def verify_tunnel(self):
        pass

Etapas de execução no Palo Alto

class PaloAlto:

    def connect(self):
        pass

    def get_routes(self):
        pass

    def get_interfaces(self):
        pass

    def get_vpn(self):
        pass

    def backup(self):
        pass

    def create_ike_gateway(self, config):
        pass

    def create_ipsec_tunnel(self, config):
        pass
		
	def enderecar_Tunel(self, config):
        pass

    def create_route(self, config):
        pass

    def create_policy(self, config):
        pass

    def validate(self):
        pass

    def commit(self):
        pass

    def verify_tunnel(self):
        pass

    def rollback(self):
        pass


```

---

# 28. Fluxo completo

O fluxo recomendado é:

```text
                 START
                   |
                   v
          Carregar variáveis
                   |
                   v
        Validar parâmetros
                   |
              +----+----+
              |         |
            FAIL       PASS
              |         |
            ABORT    Validar FGT
                        |
                        v
                  Validar PALO ALTO
                        |
                        v
                 Verificar conflito
                        |
                        v
                     Backup
                        |
                        v
               Configurar FortiGate
                        |
                        v
                Configurar Palo Alto
                        |
                        v
                 Commit / Apply
                        |
                        v
                  IKE Validation
                        |
                        v
                 IPsec Validation
                        |
                        v
                 Routing Validation
                        |
                        v
                 Policy Validation
                        |
                        v
                Connectivity Test
                        |
                        v
                Counter Validation
                        |
                  +-----+-----+
                  |           |
                FAIL         PASS
                  |           |
               Rollback     Report
                  |           |
                  +-----+-----+
                        |
                       END
```

---

# 29. Critérios de sucesso

A automação somente deverá retornar **SUCCESS** quando todos os critérios forem atendidos:

```text
[PASS] Parâmetros válidos
[PASS] FortiGate acessível
[PASS] Palo Alto acessível
[PASS] Backup realizado
[PASS] Configuração aplicada
[PASS] IKE SA UP
[PASS] IPsec SA UP
[PASS] Rotas presentes
[PASS] Security Policies presentes
[PASS] Tráfego permitido
[PASS] Pacotes TX/RX incrementando
[PASS] Teste de conectividade
[PASS] Evidências coletadas
```


---

# 30. Considerações de segurança da automação

As credenciais utilizadas pela automação não deverão ser armazenadas diretamente no código.

Não utilizar:

```Python
username = "admin"
password = "MinhaSenha123"
```

Preferir:

```text
Secret Manager
        ↓
Automation
        ↓
API
```

Também deverão ser aplicados:

- Contas administrativas dedicadas.
- Privilégio mínimo.
- API access restrito por IP.
- HTTPS.
- Rotação de credenciais.
- Auditoria.
- Logs sem exposição de PSK.
- Controle de acesso ao repositório.
- Controle de acesso aos arquivos de configuração.

---

# 31. Tecnologias recomendadas

Para uma implementação corporativa, a seguinte arquitetura é recomendada:

```text
Git
 |
 | versionamento
 v
CI/CD
 |
 v
Python
 |
 +------------------+
 |                  |
 v                  v
FortiGate API    Palo Alto API
 |                  |
 +--------+---------+
          |
          v
      Validation
          |
          v
       Report
```



---

# 32. Recomendações finais

A implementação não deverá ser baseada simplesmente em:

```text
Enviar configuração → verificar se subiu
```

O processo correto deve ser:

```text
Validate
   ↓
Backup
   ↓
Plan
   ↓
Configure
   ↓
Commit
   ↓
Verify
   ↓
Test
   ↓
Evidence
```

A maior atenção deverá ser dada à **compatibilidade dos parâmetros IKE/IPsec, selectors, roteamento, NAT e políticas de segurança**, pois uma VPN pode apresentar `IKE UP` e `IPsec UP` e ainda assim não transportar corretamente o tráfego de produção.

O desenho recomendado é manter a automação **orientada por dados**, com parâmetros da VPN separados da lógica de execução. Dessa forma, a mesma automação poderá ser reutilizada para múltiplas VPNs FortiGate ↔ Palo Alto apenas alterando o arquivo de variáveis.

---

# 33. Checklist de implementação

## Pré-implementação

- [ ] IPs públicos validados
- [ ] Interfaces WAN validadas
- [ ] Redes locais/remotas validadas
- [ ] IKE definido
- [ ] IPsec definido
- [ ] PSK disponível no secret manager
- [ ] Roteamento definido
- [ ] Security Policy definida
- [ ] Acesso API validado
- [ ] Backup realizado

## Implementação

- [ ] Objetos criados
- [ ] IKE configurado
- [ ] IPsec configurado
- [ ] Routes configuradas
- [ ] Security Policies configuradas
- [ ] Configuração aplicada
- [ ] Commit realizado

## Pós-implementação

- [ ] IKE SA UP
- [ ] IPsec SA UP
- [ ] Routes validadas
- [ ] Policies validadas
- [ ] Ping realizado
- [ ] Teste de aplicação realizado
- [ ] TX/RX validados
- [ ] Logs coletados
- [ ] Evidências armazenadas
- [ ] Relatório gerado

## Rollback

- [ ] Backup disponível
- [ ] Procedimento de rollback testado
- [ ] Objetos criados identificados
- [ ] Rollback documentado
- [ ] Validação pós-rollback definida
