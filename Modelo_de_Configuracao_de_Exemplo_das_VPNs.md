# Modelo de Configuração de Exemplo das VPNs

# Guia de Configuração e Resultados: VPN IPsec FortiGate ↔ Palo Alto

Este documento consolida o passo a passo ordenado das configurações necessárias (Fase 1, Fase 2, Endereçamento do Túnel, Rotas Estáticas e Políticas de Segurança) em ambos os equipamentos, juntamente com o resultado esperado da implementação.

---

## 1. Parâmetros de Referência (Variáveis)

* **FortiGate (Endpoint A):**
  * IP Público WAN: `200.10.10.10`
  * Rede Local (LAN): `10.10.10.0/24`
  * IP do Túnel: `169.255.1.1/30`
* **Palo Alto (Endpoint B):**
  * IP Público WAN: `200.20.20.20`
  * Rede Local (LAN): `10.20.20.0/24`
  * IP do Túnel: `169.255.1.2/30`
* **Parâmetros IPsec/IKE:**
  * IKE Version: `IKEv2`
  * Criptografia / Autenticação: `AES256 / SHA256`
  * Grupo DH / PFS: `Group 14`
  * PSK (Chave Compartilhada): `SuaChaveSecretaCompartilhada123`

---

## 2. Configuração no FortiGate

### Passo 2.1: Fase 1 (IKE) e Fase 2 (IPsec)
```text
config vpn ipsec phase1-interface
    edit "VPN-FGT-PA-001"
        set interface "wan1"
        set peertype any
        set net-device enable
        set proposal aes256-sha256
        set remote-gw 200.20.20.20
        set psksecret SuaChaveSecretaCompartilhada123
        set ike-version 2
        set dhgrp 14
    next
end

config vpn ipsec phase2-interface
    edit "VPN-FGT-PA-001"
        set phase1name "VPN-FGT-PA-001"
        set proposal aes256-sha256
        set dhgrp 14
        set src-addr-type subnet
        set dst-addr-type subnet
        set src-subnet 10.10.10.0 255.255.255.0
        set dst-subnet 10.20.20.0 255.255.255.0
    next
end
```

### Passo 2.2: Endereçamento do Túnel (Interface)
```text
config system interface
    edit "VPN-FGT-PA-001"
        set ip 169.255.1.1 255.255.255.252
        set remote-ip 169.255.1.2 255.255.255.252
    next
end
```

### Passo 2.3: Rota Estática
```text
config router static
    edit 0
        set dst 10.20.20.0 255.255.255.0
        set device "VPN-FGT-PA-001"
    next
end
```

### Passo 2.4: Políticas de Segurança
```text
config firewall address
    edit "ADDR-LAN-FGT"
        set subnet 10.10.10.0 255.255.255.0
    next
    edit "ADDR-LAN-PA"
        set subnet 10.20.20.0 255.255.255.0
    next
end

config firewall policy
    edit 0
        set name "OUT-VPN-FGT-PA"
        set srcintf "internal"
        set dstintf "VPN-FGT-PA-001"
        set srcaddr "ADDR-LAN-FGT"
        set dstaddr "ADDR-LAN-PA"
        set action accept
        set schedule "always"
        set service "ALL"
        set nat disable
    next
    edit 0
        set name "IN-VPN-FGT-PA"
        set srcintf "VPN-FGT-PA-001"
        set dstintf "internal"
        set srcaddr "ADDR-LAN-PA"
        set dstaddr "ADDR-LAN-FGT"
        set action accept
        set schedule "always"
        set service "ALL"
        set nat disable
    next
end
```

---

## 3. Configuração no Palo Alto

### Passo 3.1: Perfis de Criptografia e IKE Gateway
```xml
<!-- Exemplo conceitual da estrutura XML/CLI no PAN-OS -->
<!-- IKE Crypto Profile -->
<entry name="IKE-Crypto-FGT">
  <encryption><member>aes-256-cbc</member></encryption>
  <hash><member>sha256</member></hash>
  <dh-group><group14>group14</group14></dh-group>
</entry>

<!-- IKE Gateway -->
<entry name="IKE-GW-FGT">
  <version>ikev2</version>
  <interface>ethernet1/1</interface>
  <peer-address><ip>200.10.10.10</ip></peer-address>
  <authentication>
    <pre-shared-key><key>SuaChaveSecretaCompartilhada123</key></pre-shared-key>
  </authentication>
</entry>
```

### Passo 3.2: IPsec Crypto Profile e Túnel
```xml
<!-- IPsec Crypto Profile -->
<entry name="IPsec-Crypto-FGT">
  <esp>
    <encryption><member>aes-256-cbc</member></encryption>
    <authentication><member>sha256</member></authentication>
  </esp>
  <dh-group>group14</dh-group>
</entry>

<!-- IPsec Tunnel Interface -->
<entry name="IPsec-Tunnel-FGT">
  <tunnel-interface>tunnel.1</tunnel-interface>
  <ike-gateway>
    <entry name="IKE-GW-FGT"/>
  </ike-gateway>
  <ipsec-crypto-profile>IPsec-Crypto-FGT</ipsec-crypto-profile>
</entry>
```

### Passo 3.3: Endereçamento do Túnel
```xml
<entry name="tunnel.1">
  <ip><member>169.255.1.2/30</member></ip>
  <comment>Tunel IPsec com FortiGate</comment>
</entry>
```

### Passo 3.4: Rota Estática
```xml
<entry name="Route-To-FGT-LAN">
  <destination>10.10.10.0/24</destination>
  <interface>tunnel.1</interface>
  <virtual-router>default</virtual-router>
</entry>
```

### Passo 3.5: Políticas de Segurança
```xml
<entry name="Allow-LAN-to-FGT">
  <from><member>trust</member></from>
  <to><member>untrust</member></to>
  <source><member>10.20.20.0/24</member></source>
  <destination><member>10.10.10.0/24</member></destination>
  <service><member>any</member></service>
  <action>allow</action>
</entry>
```

---

## 4. Resultado Esperado da Execução (Validação)

Após aplicar as configurações e executar o *commit* em ambos os firewalls, os comandos de verificação operacional devem retornar os seguintes estados:

### 4.1 Validação da Phase 1 (IKE SA)
* **No FortiGate:** `get vpn ike gateway name VPN-FGT-PA-001`
* **No Palo Alto:** `show vlan-ha` ou `show ike-sa gateway IKE-GW-FGT`
* **Resultado Esperado:** 
  ```text
  Status: IKE SA UP (Negotiated successfully, IKEv2 active)
  ```

### 4.2 Validação da Phase 2 (IPsec SA)
* **No FortiGate:** `get vpn ipsec tunnel summary`
* **Resultado Esperado:**
  ```text
  name=VPN-FGT-PA-001 gateway=200.20.20.20 ... SA status=up
  IPsec SA:
    Local gateway: 200.10.10.10
    Remote gateway: 200.20.20.20
    Selectors: 10.10.10.0/24 <-> 10.20.20.0/24
    Encapsulated packets > 0
    Decapsulated packets > 0
  ```

### 4.3 Teste de Conectividade (Ping de Ponta a Ponta)
* **Comando executado a partir de um host ou interface do FortiGate:**
  ```text
  exec ping-options source 10.10.10.10
  ping 10.20.20.10
  ```
* **Resultado Esperado:**
  ```text
  Reply from 10.20.20.10: bytes=32 time=5ms TTL=64
  Success rate is 100 percent (5/5)
  ```
