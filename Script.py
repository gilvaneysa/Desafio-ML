import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# ==========================================
# FUNÇÕES DE AUTOMAÇÃO DE REDE
# ==========================================

def executar_automacao():
    # 1. Coleta os dados informados pelo usuário na interface gráfica
    ip = entry_ip.get()
    usuario = entry_usuario.get()
    senha = entry_senha.get()
    novo_hostname = entry_hostname.get()
    vlan_id = entry_vlan_id.get()
    vlan_name = entry_vlan_name.get()

    # Validação simples para ver se os campos não estão vazios
    if not all([ip, usuario, senha, novo_hostname, vlan_id, vlan_name]):
        messagebox.showerror("Erro", "Por favor, preencha todos os campos!")
        return

    # Dicionário de configuração para o Netmiko (Cisco IOS)
    switch_device = {
        'device_type': 'cisco_ios',
        'host': ip,
        'username': usuario,
        'password': senha,
    }

    try:
        # 2. Conecta ao switch
        conexao = ConnectHandler(**switch_device)
        
        # Entra no modo de privilégio (enable) se necessário
        conexao.enable()

        # ==========================================
        # ETAPA A: BACKUP DA CONFIGURAÇÃO
        # ==========================================
        # Pega a data e hora atual para o nome do arquivo
        agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Captura o hostname atual para compor o nome do arquivo
        prompt_atual = conexao.find_prompt().replace('#', '').replace('>', '')
        nome_arquivo = f"backup_{prompt_atual}_{agora}.txt"
        
        # Pega as configurações rodando atualmente (running-config)
        running_config = conexao.send_command("show running-config")
        
        # Salva em um arquivo texto local
        with open(nome_arquivo, "w") as arquivo_backup:
            arquivo_backup.write(running_config)
            
        print(f"Backup salvo com sucesso: {nome_arquivo}")

        # ==========================================
        # ETAPA B: APLICAÇÃO DAS CONFIGURAÇÕES
        # ==========================================
        # Lista de comandos que serão enviados ao switch
        comandos_configuracao = [
            f"hostname {novo_hostname}",
            f"vlan {vlan_id}",
            f"name {vlan_name}",
            "exit" # Sai da configuração da VLAN
        ]
        # Aplica a lista de comandos no modo de configuração global
        conexao.send_config_set(comandos_configuracao)

        # ==========================================
        # ETAPA C: VALIDAÇÃO DAS CONFIGURAÇÕES
        # ==========================================
        divergencia = False
        mensagens_alerta = []

        # Valida o Hostname
        check_hostname = conexao.send_command("show running-config | include hostname")
        if novo_hostname not in check_hostname:
            divergencia = True
            mensagens_alerta.append(f"Divergência: Hostname não alterado. Encontrado: {check_hostname}")

        # Valida a VLAN (o comando 'show vlan id' mostra detalhes específicos da VLAN)
        check_vlan = conexao.send_command(f"show vlan id {vlan_id}")
        if vlan_name not in check_vlan:
            divergencia = True
            mensagens_alerta.append(f"Divergência: Nome da VLAN {vlan_id} não bate com '{vlan_name}'.")

        # Fecha a conexão com o switch
        conexao.disconnect()

        # ==========================================
        # ETAPA D: FEEDBACK AO USUÁRIO (FRONTEND)
        # ==========================================
        if divergencia:
            # Junta todos os alertas em um único texto e exibe como "Aviso"
            texto_alerta = "\n".join(mensagens_alerta)
            messagebox.showwarning("Alerta de Configuração", 
                                   f"Configuração aplicada, porém foi encontrada uma configuração não padrão/divergente:\n\n{texto_alerta}")
        else:
            # Mensagem de sucesso absoluto
            messagebox.showinfo("Sucesso", 
                                f"Sucesso!\nBackup gerado: {nome_arquivo}\nConfigurações aplicadas e validadas com sucesso!")

    # Tratamento de erros comuns (falha de login, IP inalcançável, etc)
    except NetmikoAuthenticationException:
        messagebox.showerror("Erro de Autenticação", "Usuário ou senha incorretos.")
    except NetmikoTimeoutException:
        messagebox.showerror("Erro de Conexão", f"O switch no IP {ip} está inacessível (Timeout).")
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")


# ==========================================
# CONSTRUÇÃO DA INTERFACE GRÁFICA (TKINTER)
# ==========================================

# Cria a janela principal
janela = tk.Tk()
janela.title("Configurador de Switch Cisco")
janela.geometry("350x300") # Largura x Altura
janela.eval('tk::PlaceWindow . center') # Tenta centralizar a janela

# Organizando tudo em um grid simples para ficar alinhado
tk.Label(janela, text="IP do Switch:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
entry_ip = tk.Entry(janela)
entry_ip.grid(row=0, column=1, padx=10, pady=5)

tk.Label(janela, text="Usuário SSH:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
entry_usuario = tk.Entry(janela)
entry_usuario.grid(row=1, column=1, padx=10, pady=5)

tk.Label(janela, text="Senha SSH:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
entry_senha = tk.Entry(janela, show="*") # show="*" esconde a senha
entry_senha.grid(row=2, column=1, padx=10, pady=5)

tk.Label(janela, text="Novo Hostname:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
entry_hostname = tk.Entry(janela)
entry_hostname.grid(row=3, column=1, padx=10, pady=5)

tk.Label(janela, text="ID da VLAN:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
entry_vlan_id = tk.Entry(janela)
entry_vlan_id.grid(row=4, column=1, padx=10, pady=5)

tk.Label(janela, text="Nome da VLAN:").grid(row=5, column=0, padx=10, pady=5, sticky="e")
entry_vlan_name = tk.Entry(janela)
entry_vlan_name.grid(row=5, column=1, padx=10, pady=5)

# Botão para iniciar o processo. Ele chama a função 'executar_automacao'
btn_executar = tk.Button(janela, text="Fazer Backup e Configurar", command=executar_automacao, bg="lightblue")
btn_executar.grid(row=6, column=0, columnspan=2, pady=20)

# Inicia o loop da interface gráfica, mantendo a janela aberta
janela.mainloop()