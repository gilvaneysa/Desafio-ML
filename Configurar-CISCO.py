import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# ==========================================
# FUNÇÕES DE AUTOMAÇÃO DE REDE
# ==========================================

def fazer_backup():
    ip = entry_ip.get()
    usuario = entry_usuario.get()
    senha = entry_senha.get()
    protocolo = var_protocolo.get()

    if not ip or not senha:
        messagebox.showerror("Erro", "Os campos 'IP do Switch' e 'Senha' são obrigatórios para conectar e fazer backup!")
        return

    tipo_dispositivo = 'cisco_ios' if protocolo == "SSH" else 'cisco_ios_telnet'

    switch_device = {
        'device_type': tipo_dispositivo,
        'host': ip,
        'username': usuario,
        'password': senha,
        'secret': senha,
        'global_delay_factor': 2
    }

    try:
        conexao = ConnectHandler(**switch_device)
        conexao.enable()
        
        agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prompt_atual = conexao.find_prompt().replace('#', '').replace('>', '')
        nome_arquivo = f"backup_{prompt_atual}_{agora}.txt"
        
        running_config = conexao.send_command("show running-config")
        tabela_vlans = conexao.send_command("show vlan")
        
        conteudo_backup = f"!!! RUNNING CONFIGURATION !!!\n\n{running_config}\n\n\n!!! TABELA DE VLANS !!!\n\n{tabela_vlans}"
        
        with open(nome_arquivo, "w") as arquivo_backup:
            arquivo_backup.write(conteudo_backup)
            
        conexao.disconnect()
        messagebox.showinfo("Sucesso", f"Backup realizado com sucesso!\nSalvo no arquivo: {nome_arquivo}")

    except NetmikoAuthenticationException:
        messagebox.showerror("Erro de Autenticação", "Usuário ou senha incorretos.")
    except NetmikoTimeoutException:
        messagebox.showerror("Erro de Conexão", f"O switch no IP {ip} está inacessível via {protocolo} (Timeout).")
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")


def executar_automacao():
    ip = entry_ip.get()
    usuario = entry_usuario.get()
    senha = entry_senha.get()
    protocolo = var_protocolo.get()
    novo_hostname = entry_hostname.get()
    vlan_id = entry_vlan_id.get()
    vlan_name = entry_vlan_name.get().replace(" ", "_")

    if not ip or not senha:
        messagebox.showerror("Erro", "Os campos 'IP do Switch' e 'Senha' são obrigatórios para conectar!")
        return
        
    if not novo_hostname and not (vlan_id and vlan_name):
        messagebox.showerror("Erro", "Preencha o 'Novo Hostname' ou os dados da 'VLAN' (ID e Nome) para executar alguma configuração!")
        return
        
    if (vlan_id and not vlan_name) or (not vlan_id and vlan_name):
        messagebox.showerror("Erro", "Para configurar a VLAN, é necessário preencher tanto o ID quanto o Nome!")
        return

    tipo_dispositivo = 'cisco_ios' if protocolo == "SSH" else 'cisco_ios_telnet'

    switch_device = {
        'device_type': tipo_dispositivo,
        'host': ip,
        'username': usuario,
        'password': senha,
        'secret': senha,
        'global_delay_factor': 2
    }

    try:
        conexao = ConnectHandler(**switch_device)
        conexao.enable()

        # ==========================================
        # ETAPA A: VERIFICAÇÃO PRÉVIA DA VLAN (ID e Nome)
        # ==========================================
        if vlan_id and vlan_name: 
            # 1. Verifica se o ID da VLAN já existe
            saida_vlan_id = conexao.send_command(f"show vlan id {vlan_id}")
            if "not found" not in saida_vlan_id.lower() and "invalid" not in saida_vlan_id.lower():
                resposta_id = messagebox.askyesno(
                    "VLAN Já Existe", 
                    f"A VLAN {vlan_id} já está criada neste switch!\n\nDeseja continuar e sobrescrever o nome dela?"
                )
                if not resposta_id: 
                    conexao.disconnect()
                    return

            # 2. Verifica se o Nome da VLAN já está em uso em OUTRO ID
            saida_vlan_brief = conexao.send_command("show vlan brief")
            nome_duplicado = False
            
            # Analisa linha por linha a tabela de VLANs do switch
            for linha in saida_vlan_brief.splitlines():
                partes = linha.split()
                if len(partes) >= 2:
                    id_encontrado = partes[0]
                    nome_encontrado = partes[1]
                    # Se o nome bater, mas o ID for diferente, significa que é de outra VLAN
                    if nome_encontrado == vlan_name and id_encontrado != str(vlan_id):
                        if id_encontrado.isdigit(): # Validação para pular cabeçalhos da tabela
                            nome_duplicado = True
                            break
            
            if nome_duplicado:
                resposta_nome = messagebox.askyesno(
                    "Nome Duplicado", 
                    f"Atenção: O nome '{vlan_name}' já está sendo usado por outra VLAN neste switch!\n\nDeseja continuar e criar a VLAN {vlan_id} com este nome duplicado?"
                )
                if not resposta_nome:
                    conexao.disconnect()
                    return

        # ==========================================
        # ETAPA B: APLICAÇÃO DAS CONFIGURAÇÕES
        # ==========================================
        comandos_configuracao = []
        
        if novo_hostname:
            comandos_configuracao.append(f"hostname {novo_hostname}")
            
        if vlan_id:
            comandos_configuracao.append(f"vlan {vlan_id}")
            comandos_configuracao.append(f"name {vlan_name}")
            comandos_configuracao.append("exit")
        
        resultado_config = conexao.send_config_set(comandos_configuracao)

        # ==========================================
        # ETAPA C: VALIDAÇÃO DAS CONFIGURAÇÕES
        # ==========================================
        divergencia = False
        mensagens_alerta = []

        if novo_hostname:
            check_hostname = conexao.send_command("show running-config | include hostname")
            if novo_hostname not in check_hostname:
                divergencia = True
                mensagens_alerta.append(f"Divergência: Hostname não alterado. Encontrado: {check_hostname}")

        if vlan_id:
            check_vlan_nova = conexao.send_command(f"show vlan id {vlan_id}")
            if vlan_name not in check_vlan_nova:
                divergencia = True
                mensagens_alerta.append(f"Divergência: Nome da VLAN {vlan_id} não bate com '{vlan_name}'.")

        conexao.disconnect()

        # ==========================================
        # ETAPA D: FEEDBACK AO USUÁRIO
        # ==========================================
        if divergencia:
            texto_alerta = "\n".join(mensagens_alerta)
            messagebox.showwarning("Alerta de Configuração", 
                                   f"Configuração aplicada, porém foi encontrada uma divergência:\n\n{texto_alerta}")
        else:
            messagebox.showinfo("Sucesso", "Configurações aplicadas e validadas com sucesso!")

    except NetmikoAuthenticationException:
        messagebox.showerror("Erro de Autenticação", "Usuário ou senha incorretos (ou falha no Enable).")
    except NetmikoTimeoutException:
        messagebox.showerror("Erro de Conexão", f"O switch no IP {ip} está inacessível via {protocolo} (Timeout).")
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")


def salvar_configuracao():
    ip = entry_ip.get()
    usuario = entry_usuario.get()
    senha = entry_senha.get()
    protocolo = var_protocolo.get()

    if not ip or not senha:
        messagebox.showerror("Erro", "Os campos 'IP do Switch' e 'Senha' são obrigatórios para conectar e salvar!")
        return

    tipo_dispositivo = 'cisco_ios' if protocolo == "SSH" else 'cisco_ios_telnet'

    switch_device = {
        'device_type': tipo_dispositivo,
        'host': ip,
        'username': usuario,
        'password': senha,
        'secret': senha,
        'global_delay_factor': 2
    }

    try:
        conexao = ConnectHandler(**switch_device)
        conexao.enable()
        conexao.save_config()
        conexao.disconnect()
        messagebox.showinfo("Sucesso", "As configurações foram salvas com sucesso na memória do switch (startup-config)!")
    except NetmikoAuthenticationException:
        messagebox.showerror("Erro de Autenticação", "Usuário ou senha incorretos.")
    except NetmikoTimeoutException:
        messagebox.showerror("Erro de Conexão", f"O switch no IP {ip} está inacessível via {protocolo} (Timeout).")
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")


# ==========================================
# CONSTRUÇÃO DA INTERFACE GRÁFICA (TKINTER)
# ==========================================

janela = tk.Tk()
janela.title("Configurador de Switch Cisco")
janela.geometry("450x500") 
janela.eval('tk::PlaceWindow . center')

texto_explicativo = "Ferramenta de automação para Switches Cisco.\nPreencha os dados abaixo para alterar Hostname e/ou criar VLANs."
tk.Label(janela, text=texto_explicativo, justify="center", fg="#333333", font=("Arial", 9, "italic")).grid(row=0, column=0, columnspan=2, pady=10)

tk.Label(janela, text="IP do Switch:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
entry_ip = tk.Entry(janela, width=25)
entry_ip.grid(row=1, column=1, padx=10, pady=5, sticky="w")

tk.Label(janela, text="Usuário (Opcional):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
entry_usuario = tk.Entry(janela, width=25)
entry_usuario.grid(row=2, column=1, padx=10, pady=5, sticky="w")

tk.Label(janela, text="Senha (VTY/Enable):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
entry_senha = tk.Entry(janela, show="*", width=25)
entry_senha.grid(row=3, column=1, padx=10, pady=5, sticky="w")

tk.Label(janela, text="Protocolo:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
var_protocolo = tk.StringVar(value="SSH") 
frame_protocolo = tk.Frame(janela)
frame_protocolo.grid(row=4, column=1, padx=10, pady=5, sticky="w")
tk.Radiobutton(frame_protocolo, text="SSH", variable=var_protocolo, value="SSH").pack(side="left")
tk.Radiobutton(frame_protocolo, text="Telnet", variable=var_protocolo, value="Telnet").pack(side="left")

tk.Label(janela, text="Novo Hostname (Opcional):").grid(row=5, column=0, padx=10, pady=5, sticky="e")
entry_hostname = tk.Entry(janela, width=25)
entry_hostname.grid(row=5, column=1, padx=10, pady=5, sticky="w")

tk.Label(janela, text="ID da VLAN (Opcional):").grid(row=6, column=0, padx=10, pady=5, sticky="e")
entry_vlan_id = tk.Entry(janela, width=25)
entry_vlan_id.grid(row=6, column=1, padx=10, pady=5, sticky="w")

tk.Label(janela, text="Nome da VLAN (Opcional):").grid(row=7, column=0, padx=10, pady=5, sticky="e")
entry_vlan_name = tk.Entry(janela, width=25)
entry_vlan_name.grid(row=7, column=1, padx=10, pady=5, sticky="w")

# ==========================================
# BOTÕES INDEPENDENTES
# ==========================================

btn_backup = tk.Button(janela, text="Fazer Backup Completo", command=fazer_backup, bg="lightyellow", width=25)
btn_backup.grid(row=8, column=0, columnspan=2, pady=(15, 5))

btn_executar = tk.Button(janela, text="Aplicar Configurações", command=executar_automacao, bg="lightblue", width=25)
btn_executar.grid(row=9, column=0, columnspan=2, pady=5)

btn_salvar = tk.Button(janela, text="Salvar no Switch (Write Memory)", command=salvar_configuracao, bg="lightgreen", width=25)
btn_salvar.grid(row=10, column=0, columnspan=2, pady=5)

janela.mainloop()