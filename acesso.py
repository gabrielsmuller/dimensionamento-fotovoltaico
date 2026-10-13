import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import sys, os
import requests
import json
import datetime
from cryptography.fernet import Fernet
from atualizacoes import verificar_atualizacoes
from dotenv import load_dotenv

organizacao = None

# Ajustar o caminho se executado como um executável PyInstaller
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

icon_path = "dimicon.ico"
icon_full_path = os.path.join(application_path, icon_path)

# Credenciais do Supabase: arquivo .env na mesma pasta do executável (ou do código)
_pasta_env = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_pasta_env, ".env"))

def salvar_organizacao(nome):
    global organizacao
    organizacao = nome

def obter_organizacao():
    global organizacao
    return organizacao

# Gera uma chave. Isso deve ser feito uma vez e salvo de forma segura.
def generate_key():
    return Fernet.generate_key()

# Salva a chave em um arquivo seguro
def save_key(key, file_path):
    with open(file_path, "wb") as key_file:
        key_file.write(key)

# Carrega a chave de um arquivo
def load_key(file_path):
    with open(file_path, "rb") as key_file:
        return key_file.read()

# Criptografa uma mensagem
def encrypt_message(message, key):
    return Fernet(key).encrypt(message.encode())

# Descriptografa uma mensagem
def decrypt_message(encrypted_message, key):
    return Fernet(key).decrypt(encrypted_message).decode()

# Caminho para armazenar a chave e os dados do usuário
diretorio_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
arquivo_key = os.path.join(diretorio_documentos, 'key.key')
arquivo_config = os.path.join(diretorio_documentos, 'config_login.json')

# Gera e salva a chave, se não existir
if not os.path.exists(arquivo_key):
    key = generate_key()
    save_key(key, arquivo_key)
else:
    key = load_key(arquivo_key)

def salvar_configuracoes(username, password, manter_conectado):
    with open(arquivo_config, 'w') as arquivo:
        encrypted_password = encrypt_message(password, key)
        json.dump({'ultimo_login': username, 'password': encrypted_password.decode(), 'manter_conectado': manter_conectado}, arquivo)

def atualizar_manter_conectado(username, manter_conectado):
    diretorio_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
    arquivo_config = os.path.join(diretorio_documentos, 'config_login.json')

    # Carrega as configurações atuais para não sobrescrever outros dados
    try:
        with open(arquivo_config, 'r') as arquivo:
            config = json.load(arquivo)
    except FileNotFoundError:
        config = {}

    # Atualiza apenas o campo 'manter_conectado'
    config['ultimo_login'] = username  # Manter o username atual para preenchimento automático
    config['manter_conectado'] = manter_conectado

    # Salva as configurações atualizadas
    with open(arquivo_config, 'w') as arquivo:
        json.dump(config, arquivo)

def carregar_configuracoes():
    try:
        with open(arquivo_config, 'r') as arquivo:
            config = json.load(arquivo)
            config['password'] = decrypt_message(config['password'].encode(), key) if 'password' in config else ''
            return config
    except FileNotFoundError:
        return {'ultimo_login': '', 'password': '', 'manter_conectado': False}

class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()
        self.iconbitmap(icon_full_path)
        self.title("Acessar")
        self.geometry("440x335")
        self.center_window(440, 335)
        self.resizable(False, False)

        # Frame para o login
        login_frame = ttk.Frame(self)
        login_frame.pack(pady=10)

        config = carregar_configuracoes()
        ultimo_login = config.get('ultimo_login', '')
        ultimo_password = config.get('password', '')
        manter_conectado = config.get('manter_conectado', False)

        # Rótulo e campo de entrada para o login
        self.user_label = ttk.Label(login_frame, text="Login (e-mail): ")
        self.user_label.pack(side='left', padx=(20, 10), pady=(25, 10))

        self.user_entry = ttk.Entry(login_frame, width=30)
        self.user_entry.delete(0, 'end')
        self.user_entry.insert(0, ultimo_login)
        self.user_entry.pack(side='left', padx=(0, 40), pady=(25, 10))

        # Frame para a senha
        password_frame = ttk.Frame(self)
        password_frame.pack()

        # Rótulo e campo de entrada para a senha
        self.password_label = ttk.Label(password_frame, text="Senha: ")
        self.password_label.pack(side='left', padx=(78, 10), pady=10)

        self.password_entry = ttk.Entry(password_frame, show="*", width=30)
        self.password_entry.delete(0, 'end')
        self.password_entry.insert(0, ultimo_password)
        self.password_entry.pack(side='left', padx=(0, 40), pady=10)

        # Checkbox para lembrar login
        self.remember_var = tk.BooleanVar()
        self.remember_check = ttk.Checkbutton(self, text="Manter conectado", variable=self.remember_var)
        self.remember_check.pack(pady=(15, 5))
        self.remember_var.set(manter_conectado)

        # Label "Esqueci minha senha"
        self.forgot_password_label = tk.Label(self, text="Esqueci minha senha", fg="blue", cursor="hand2")
        self.forgot_password_label.pack(pady=(5, 0))
        self.forgot_password_label.bind("<Button-1>", self.forgot_password)

        # Frame para os botões
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=15)

        # Botões de entrar e solicitar acesso dentro do frame
        self.request_access_button = ttk.Button(button_frame, text="Entrar", command=self.login, style="Accent.TButton")
        self.request_access_button.pack(side='right', padx=(10, 10), pady=10)

        self.login_button = ttk.Button(button_frame, text="Cadastrar-se", command=self.request_access)
        self.login_button.pack(side='right', padx=(10, 10), pady=10)

        if manter_conectado:
            self.login(automatico=True)
        else:
            self.deiconify()

    def forgot_password(self, event):
        forgot_window = tk.Toplevel(self)
        forgot_window.iconbitmap(icon_full_path)
        forgot_window.title("Esqueci a Senha")
        forgot_window.geometry("400x250")
        window_width = 400
        window_height = 200
        screen_width = forgot_window.winfo_screenwidth()
        screen_height = forgot_window.winfo_screenheight()
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))
        forgot_window.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        forgot_window.resizable(False, False)

        commercial_label = ttk.Label(forgot_window, text=" Para redefinir sua senha, entre em contato com nossa equipe de T.I e informe seu login.", wraplength=350)
        commercial_label.pack(pady=10, padx=10)

        # Contato da equipe de T.I
        ti_frame = ttk.Frame(forgot_window)
        ti_frame.pack(pady=10)

        ti_label = ttk.Label(ti_frame, text="Telefone (Whatsapp): 45 99927-9001")
        ti_label.pack(pady=5)

        ti_button = ttk.Button(ti_frame, text="Entrar em contato", command=lambda: open_whatsapp("45999279001"),
                               style="Accent.TButton")
        ti_button.pack(pady=(10, 5))

        def open_whatsapp(phone_number):
            import webbrowser
            url = f"https://wa.me/{phone_number}"
            webbrowser.open(url)

    def login(self, automatico=False):
        username = self.user_entry.get()
        password = self.password_entry.get() if not automatico else carregar_configuracoes().get('password')
        remember = self.remember_var.get()

        load_dotenv()

        api_key = os.getenv("SUPABASE_API_KEY")
        auth_key = os.getenv("SUPABASE_AUTH_KEY")

        url = "https://ktdmbdjzmisdtjhdlvnl.supabase.co/rest/v1/Acessos"
        headers = {
            "apikey": api_key,
            "Authorization": auth_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        # Primeiro, verifique se o usuário está ativo
        query_url = f"{url}?login=eq.{username}"
        response = requests.get(query_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if not data:
                if not automatico:
                    messagebox.showerror("Login", "Usuário ou senha inválidos.")
                return

            if data[0]['ativo'] is False:
                if not automatico:
                    messagebox.showerror("Login",
                                         "Seu usuário não foi aprovado ainda ou está desativado, entre em contato conosco para mais detalhes.")
                return

            # Se o usuário estiver ativo, verifique a senha
            query_url = f"{url}?login=eq.{username}&senha=eq.{password}"
            response = requests.get(query_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data:
                    if data[0]['resetar_senha']:
                        self.abrir_popup_resetar_senha(username)
                    else:
                        if not automatico:
                            salvar_configuracoes(username, password, remember)  # Salva as configurações
                        self.master.organizacao = data[0]['organizacao']  # Atualizar a organização após o login
                        self.master.lbl_organizacao.config(text=self.master.organizacao)

                        salvar_organizacao(self.master.organizacao)

                        self.destroy()  # Fecha a janela de login
                        self.master.deiconify()  # Mostra a janela principal
                        verificar_atualizacoes(self)
                else:
                    if not automatico:
                        messagebox.showerror("Login", "Usuário ou senha inválidos.")
                    if automatico:
                        self.deiconify()
            else:
                if not automatico:
                    messagebox.showerror("Erro", "Ocorreu um erro ao tentar realizar o login.")
        else:
            if not automatico:
                messagebox.showerror("Erro", "Ocorreu um erro ao tentar verificar o usuário.")

    def abrir_popup_resetar_senha(self, username):
        popup = tk.Toplevel(self)
        popup.title("Redefinir Senha")
        popup.geometry("400x300")
        popup.iconbitmap(icon_full_path)
        popup.resizable(False, False)

        window_width = 400
        window_height = 300
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))
        popup.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        ttk.Label(popup, text="Para continuar, redefina sua senha:").pack(pady=(10, 5))

        ttk.Label(popup, text="Nova Senha:").pack(pady=5)
        nova_senha_entry = ttk.Entry(popup, show='*')
        nova_senha_entry.pack(pady=5)

        ttk.Label(popup, text="Confirmar Nova Senha:").pack(pady=5)
        confirmar_senha_entry = ttk.Entry(popup, show='*')
        confirmar_senha_entry.pack(pady=5)

        def redefinir_senha():
            nova_senha = nova_senha_entry.get()
            confirmar_senha = confirmar_senha_entry.get()
            if nova_senha == confirmar_senha:
                atualizar_senha(username, nova_senha)
                popup.destroy()
                messagebox.showinfo("Sucesso", "Senha redefinida com sucesso. Por favor, faça login novamente.")
                self.deiconify()
            else:
                messagebox.showerror("Erro", "As senhas não coincidem. Tente novamente.")

        ttk.Button(popup, text="Redefinir Senha", command=redefinir_senha, style="Accent.TButton").pack(pady=20)

        def atualizar_senha(username, nova_senha):
            load_dotenv()
            api_key = os.getenv("SUPABASE_API_KEY")
            auth_key = os.getenv("SUPABASE_AUTH_KEY")
            url = "https://ktdmbdjzmisdtjhdlvnl.supabase.co/rest/v1/Acessos"
            headers = {
                "apikey": api_key,
                "Authorization": auth_key,
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }

            data = {
                "senha": nova_senha,
                "resetar_senha": False
            }

            response = requests.patch(f"{url}?login=eq.{username}", headers=headers, json=data)
            if response.status_code != 200:
                messagebox.showerror("Erro", "Ocorreu um erro ao tentar atualizar a senha. Tente novamente.")

    def request_access(self):
        SolicitationDialog(self.master)

    def center_window(self, width, height):
        # Centraliza a janela
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def salvar_ultimo_login(self, username):
        diretorio_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
        arquivo_config = os.path.join(diretorio_documentos, 'config_login.json')

        with open(arquivo_config, 'w') as arquivo:
            json.dump({'ultimo_login': username}, arquivo)

    def carregar_ultimo_login(self):
        diretorio_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
        arquivo_config = os.path.join(diretorio_documentos, 'config_login.json')

        try:
            with open(arquivo_config, 'r') as arquivo:
                config = json.load(arquivo)
                return config.get('ultimo_login', '')  # Retorna uma string vazia se não encontrar o login
        except FileNotFoundError:
            return ''

class SolicitationDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.iconbitmap(icon_full_path)
        self.title("Solicitar Acesso")
        self.resizable(False, False)
        self.geometry("480x335")
        self.center_window(480, 335)
        self.resizable(False, False)

        # Frame para a solicitação
        solicitation_frame = ttk.Frame(self)
        solicitation_frame.pack(pady=10)

        # Rótulo e campo de entrada para o Nome da Empresa
        self.company_label = ttk.Label(solicitation_frame, text="Nome da Empresa:")
        self.company_label.pack(side='left', padx=(40, 10), pady=(25, 10))

        self.company_entry = ttk.Entry(solicitation_frame, width=30)
        self.company_entry.pack(side='left', padx=(4, 50), pady=(25, 10))

        # Frame para o E-mail
        email_frame = ttk.Frame(self)
        email_frame.pack()

        # Rótulo e campo de entrada para o E-mail
        self.email_label = ttk.Label(email_frame, text="E-mail:                   ")
        self.email_label.pack(side='left', padx=(40, 10), pady=10)

        self.email_entry = ttk.Entry(email_frame, width=30)
        self.email_entry.pack(side='left', padx=(2, 50), pady=10)

        # Frame para o Telefone
        phone_frame = ttk.Frame(self)
        phone_frame.pack()

        # Rótulo e campo de entrada para o Telefone
        self.phone_label = ttk.Label(phone_frame, text="Telefone:                ")
        self.phone_label.pack(side='left', padx=(40, 10), pady=(20, 10))

        self.phone_entry = ttk.Entry(phone_frame, width=30)
        self.phone_entry.pack(side='left', padx=(0, 50), pady=(20, 10))

        # Frame para os botões
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=15)

        # Botões de enviar e entrar em contato
        self.send_button = ttk.Button(button_frame, text="Enviar Solicitação", command=self.send_request, style="Accent.TButton")
        self.send_button.pack(side='right', padx=(10, 10), pady=(15, 10))

        self.contact_button = ttk.Button(button_frame, text="Entrar em contato", command=self.contact)
        self.contact_button.pack(side='right', padx=(10, 10), pady=(15, 10))

    def center_window(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f'{width}x{height}+{x}+{y}')

    def send_request(self):
        company = self.company_entry.get()
        email = self.email_entry.get()
        phone = self.phone_entry.get()

        if not company or not email or not phone:
            messagebox.showerror("Erro", "Por favor, preencha todos os campos obrigatórios.")
            return

        if not phone.isdigit():
            messagebox.showerror("Erro", "Por favor, insira o número de telefone somente numérico.")
            return

        import re
        email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.match(email_regex, email):
            messagebox.showerror("Erro", "Por favor, insira um endereço de email válido.")
            return

        url = "https://ktdmbdjzmisdtjhdlvnl.supabase.co/rest/v1/Acessos"
        load_dotenv()
        api_key = os.getenv("SUPABASE_API_KEY")
        auth_key = os.getenv("SUPABASE_AUTH_KEY")
        headers = {
            "apikey": api_key,
            "Authorization": auth_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        data = {
            "organizacao": company,
            "login": email,
            "telefone": phone,
            "data_criacao": datetime.date.today().isoformat()
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            messagebox.showinfo("Solicitação Enviada", "Sua solicitação foi enviada com sucesso.")
            self.destroy()
        else:
            messagebox.showerror("Erro", "Ocorreu um erro ao enviar sua solicitação.")

    def contact(self):
        contact_window = tk.Toplevel(self)
        contact_window.iconbitmap(icon_full_path)
        contact_window.title("Entrar em Contato")
        contact_window.geometry("400x250")
        self.center_new_window(contact_window, 400, 250)
        contact_window.resizable(False, False)


        # Contato da equipe de T.I
        ti_frame = ttk.Frame(contact_window)
        ti_frame.pack(pady=(20, 10))

        ti_label = ttk.Label(ti_frame, text="Equipe de T.I: 45 9117-1687")
        ti_label.pack(pady=5)

        ti_button = ttk.Button(ti_frame, text="Entrar em contato", command=lambda: self.open_whatsapp("4591171687"), style="Accent.TButton")
        ti_button.pack(pady=5)

    def open_whatsapp(self, phone_number):
        import webbrowser
        url = f"https://wa.me/{phone_number}"
        webbrowser.open(url)

    def center_new_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f'{width}x{height}+{x}+{y}')
