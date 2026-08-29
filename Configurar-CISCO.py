import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# ==========================================
# FUNÇÕES DE AUTOMAÇÃO DE REDE
# ==========================================

def executar_automacao():
    # 1. Coleta os dados da interface gráfica
    ip = entry_ip.get()
    usuario = entry_usuario.get()
    senha = entry_senha.get()
    protocolo = var_protocolo.get()
    novo_hostname = entry_hostname.get()
    vlan_id = entry_vlan_id.get()
    vlan_name = entry_vlan_name.get().replace(" ", "_")

    # ==========================================
    # VALIDAÇÃO FLEXÍVEL DE CAMPOS
    # ==========================================
    # Apenas IP e Senha são estritamente obrigatórios para conectar
    if not ip or not senha:
        messagebox.showerror("Erro", "Os campos 'IP do Switch' e 'Senha' são obrigatórios para conectar!")
        return
        
    # Pelo menos uma ação deve ser solicitada (mudar nome ou configurar VLAN)
    if not novo_hostname and not (vlan_id and vlan_name):
        messagebox.showerror("Erro", "Preencha o 'Novo Hostname' ou os dados da 'VLAN' (ID e Nome) para executar alguma configuração!")
        return
        
    # Se preencheu só metade dos dados da VLAN
    if (vlan_id and not vlan_name) or (not vlan_id and vlan_name):
        messagebox.showerror("Erro", "Para configurar a VLAN, é necessário preencher tanto o ID quanto o Nome!")
        return

    if protocolo == "SSH":
        tipo_dispositivo = 'cisco_ios'
    else:
        tipo_dispositivo = 'cisco_ios_telnet'

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
        # ETAPA A: VERIFICAÇÃO PRÉVIA DA VLAN
        # ==========================================
        if vlan_id: # Só faz essa checagem se o usuário pediu para configurar VLAN
            saida_vlan = conexao.send_command(f"show vlan id {vlan_id}")
            
            if "not found" not in saida_vlan.lower() and "invalid" not in saida_vlan.lower():
                # messagebox.askyesno cria uma janela com os botões "Sim" e "Não"
                resposta = messagebox.askyesno(
                    "VLAN Já Existe", 
                    f"A VLAN {vlan_id} já está criada neste switch!\n\nDeseja continuar e sobrescrever o nome dela?"
                )
                if not resposta: # Se o usuário clicar em "Não"
                    conexao.disconnect()
                    return

        # ==========================================
        # ETAPA B: BACKUP DA CONFIGURAÇÃO
        # ==========================================
        agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prompt_atual = conexao.find_prompt().replace('#', '').replace('>', '')
        nome_arquivo = f"backup_{prompt_atual}_{agora}.txt"
        
        running_config = conexao.send_command("show running-config")
        
        with open(nome_arquivo, "w") as arquivo_backup:
            arquivo_backup.write(running_config)
            
        print(f"Backup salvo com sucesso: {nome_arquivo}")

        # ==========================================
        # ETAPA C: APLICAÇÃO DAS CONFIGURAÇÕES
        # ==========================================
        comandos_configuracao = []
        
        if novo_hostname:
            comandos_configuracao.append(f"hostname {novo_hostname}")
            
        if vlan_id:
            comandos_configuracao.append(f"vlan {vlan_id}")
            comandos_configuracao.append(f"name {vlan_name}")
            comandos_configuracao.append("exit")
        
        resultado_config = conexao.send_config_set(comandos_configuracao)
        
        print("\n--- MENSAGEM DO SWITCH AO APLICAR A CONFIGURAÇÃO ---")
        print(resultado_config)
        print("----------------------------------------------------\n")

        # ==========================================
        # ETAPA D: VALIDAÇÃO DAS CONFIGURAÇÕES
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
        # ETAPA E: FEEDBACK AO USUÁRIO
        # ==========================================
        if divergencia:
            texto_alerta = "\n".join(mensagens_alerta)
            messagebox.showwarning("Alerta de Configuração", 
                                   f"Configuração aplicada, porém foi encontrada uma divergência:\n\n{texto_alerta}")
        else:
            messagebox.showinfo("Sucesso", 
                                f"Sucesso!\nBackup gerado: {nome_arquivo}\nConfigurações aplicadas e validadas com sucesso!")

    except NetmikoAuthenticationException:
        messagebox.showerror("Erro de Autenticação", "Usuário ou senha incorretos (ou falha no Enable).")
    except NetmikoTimeoutException:
        messagebox.showerror("Erro de Conexão", f"O switch no IP {ip} está inacessível via {protocolo} (Timeout).")
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {str(e)}")


# ==========================================
# CONSTRUÇÃO DA INTERFACE GRÁFICA (TKINTER)
# ==========================================

janela = tk.Tk()
janela.title("Configurador de Switch Cisco")
janela.geometry("400x350") 
janela.eval('tk::PlaceWindow . center')

tk.Label(janela, text="IP do Switch:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
entry_ip = tk.Entry(janela)
entry_ip.grid(row=0, column=1, padx=10, pady=5)

tk.Label(janela, text="Usuário (Opcional):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
entry_usuario = tk.Entry(janela)
entry_usuario.grid(row=1, column=1, padx=10, pady=5)

tk.Label(janela, text="Senha (VTY/Enable):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
entry_senha = tk.Entry(janela, show="*")
entry_senha.grid(row=2, column=1, padx=10, pady=5)

tk.Label(janela, text="Protocolo:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
var_protocolo = tk.StringVar(value="SSH") 
frame_protocolo = tk.Frame(janela)
frame_protocolo.grid(row=3, column=1, padx=10, pady=5, sticky="w")
tk.Radiobutton(frame_protocolo, text="SSH", variable=var_protocolo, value="SSH").pack(side="left")
tk.Radiobutton(frame_protocolo, text="Telnet", variable=var_protocolo, value="Telnet").pack(side="left")

# Atualizei os textos da interface para deixar claro que são opcionais
tk.Label(janela, text="Novo Hostname (Opcional):").grid(row=4, column=0, padx=10, pady=5, sticky="e")
entry_hostname = tk.Entry(janela)
entry_hostname.grid(row=4, column=1, padx=10, pady=5)

tk.Label(janela, text="ID da VLAN (Opcional):").grid(row=5, column=0, padx=10, pady=5, sticky="e")
entry_vlan_id = tk.Entry(janela)
entry_vlan_id.grid(row=5, column=1, padx=10, pady=5)

tk.Label(janela, text="Nome da VLAN (Opcional):").grid(row=6, column=0, padx=10, pady=5, sticky="e")
entry_vlan_name = tk.Entry(janela)
entry_vlan_name.grid(row=6, column=1, padx=10, pady=5)

btn_executar = tk.Button(janela, text="Fazer Backup e Configurar", command=executar_automacao, bg="lightblue")
btn_executar.grid(row=7, column=0, columnspan=2, pady=20)

janela.mainloop()