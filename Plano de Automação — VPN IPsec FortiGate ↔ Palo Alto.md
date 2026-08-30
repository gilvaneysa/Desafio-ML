# Plano de Automação — VPN IPsec FortiGate ↔ Palo Alto

## 1. Objetivo

Este documento define um plano técnico para automatizar a implantação de uma VPN IPsec site-to-site entre um **FortiGate** e um **Palo Alto Networks**, contemplando desde a coleta e validação dos parâmetros até a configuração, ativação, validação operacional e rollback.

O objetivo da automação é reduzir intervenção manual, padronizar configurações, minimizar erros de parametrização e produzir evidências suficientes para auditoria e troubleshooting.

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

# 5. Variáveis da automação

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

Tunnel IP:
  VPN-FGT-PA-001: "169.255.1.1/30"
  VPN-PA-FGT-001: "169.255.1.2/30"

```

A chave pré-compartilhada (**PSK**) deverá ser armazenada separadamente, preferencialmente em um **secret manager**, e nunca diretamente no repositório Git. Em caso de um script interativo 
o usuário poderia preencher os parametros obrigatório inclusive a chave PSK.

---

# 6. Fase 1 — Validação de entrada

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

Essa validação seria para verificar se foi preeenhido alguma paramentroãs não aceito pelos dispositivos, como :
-Formato de endereçamento invalido.
-Nome no tunel VPN com espaço ou maior que 15 caracteres para Fortigate e 63 para Paloalto.
-Formato de nome da inteface que é diferente em ambos os equipamentos.
-Formato da escrita de algoritmo de criptografia e autenticação exemplo, no Fortigate aes256-sha256 seria equivalente a aes-256-cbc do Paloalto.

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

# 7. Fase 2 — Validação dos equipamentos

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
- VDOM, quando utilizado. (Se houver VDOM os paramentros  de configuração devem incluir a informações da VDOM)

Exemplo conceitual:

```text
GET /api/v2/monitor/system/status - consultar o status geral e as informações de saúde do sistema do Fortigate.
GET /api/?type=op&cmd=<show><system><info></info></system></show>&key=< SUA_API_KEY> consultar o status geral e as informações de saúde do sistema do Palo alto.
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

É importante consultar as rotas existe nos equipamentos para evitar possível conflito de roteamento, essa verificação é extremamente importante. 

---

# 8. Fase 3 — Verificação de conflitos

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

Essa lógica evita que uma execução repetida gere objetos duplicados. Essa checagem se adaqua bastantes para a criação dos objetos que serão utilizados nas politicas de firewall. 

---

# 9. Fase 4 — Backup / Snapshot

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

# 10. Fase 5 — Configuração do FortiGate

## 10.1 Phase 1 / IKE

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

No caso de um script único, alguma variáveis podem ser utilizadas em ambas os equipamentos como a parte de IKE, Autenticação e criptografia. Paramentros que tem o mesmo valor mais formatos diferentes precisam ter variáveis diferente. 

---

# 11. Fase 6 — Configuração da Phase 2

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

# 12. Fase 7 — Objetos de endereço

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

# 13. Fase 8 — Roteamento

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

# 14. Fase 9 — Security Policy

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

# 15. Fase 10 — Configuração do Palo Alto

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

# 16. Fase 11 — Commit / Aplicação da configuração

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

Esta fase deverá ser tratada com cuidado porque os dois fabricantes possuem modelos diferentes de aplicação de configuração. De acordo com a arvore acima o script de automação pode gerar os arquivos de configuração ou aplicar a configuração via API 
Uma forma de prevenção e controle seria utilizamos no Fortigate o Workpace mode. O Workspace Mode do FortiOS permite realizar um conjunto de alterações dentro de uma transação e só torná-las efetivas quando a transação é submetida. 
Antes do commit, as alterações podem ser modificadas ou descartadas. Além disso, objetos envolvidos ficam bloqueados para evitar alterações concorrentes. o timeout padrão é de 5 minutos sem atividade. Se não houver atividade durante esse período, 
a transação expira e todas as alterações pendentes são descartadas. Isso é importante caso haja alguma perda de conectividade com o equipamento em caso de configuração equivocada. 
No palo alto poderiamos utilizar o Validade, que não faz a mesma coisa da workspace mode do Fortigate, mas ajuda a verificar a configuração antes do commit. O Validate consegue verificar coisas como:
sintaxe;
referências entre objetos;
parâmetros obrigatórios;
consistência da configuração;
erros que fariam o commit falhar.

O que é o DRY-RUN
Dry-run é um modo de execução em que a automação executa todas as validações e calcula o que faria, mas não realiza nenhuma alteração nos equipamentos. Função da automação para gerar os Scripts, caso a API não seja utilizada. 

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

# 17. Fase 12 — Validação da Phase 1

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

# 18. Fase 13 — Validação da Phase 2

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

# 19. Fase 14 — Teste de conectividade

Realizar testes de ponta a ponta. Podemos relizar um Ping de uma interface LAN do equipamento(O Ip da interface do Local Selector para o Remote Selector)

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

# 20. Fase 15 — Validação dos contadores

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



---

# 21. Fase 17 — Evidências

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

# 23. Tratamento de erros

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

# 24. Estratégia de Rollback

O rollback deverá ser definido antes da implantação. Desfazer as configurações ou restaurar backup em casos mais graves. 

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

# 25. Idempotência

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

# 26. Estrutura recomendada da automação

Uma estrutura possível utilizando Python:

```text

vpn-automation/
│
├── README.md
│
├── inventory/
│   └── production.yml # Ele define quais equipamentos existem, como a automação deve acessá-los e em qual ambiente eles estão. IP,api_port, DNS
│
├── variables/
│   └── vpn-001.yml    # Esse arquivo define os parâmetros da VPN.Como:name,IKE, local_networks, autenticação e criptogtafia
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

Etapas de execução no Fortigate 

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
		
Etapa  de execução no Palo Alto 

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

# 27. Fluxo completo

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

# 28. Critérios de sucesso

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

# 29. Considerações de segurança da automação

As credenciais utilizadas pela automação não deverão ser armazenadas diretamente no código.

Não utilizar:

```python
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

# 30. Tecnologias recomendadas

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