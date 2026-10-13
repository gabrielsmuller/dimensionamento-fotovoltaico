import tkinter as tk
#import customtkinter as ctk
from tkinter import ttk
import sys, os
from obterhsp import obter_hsp
import requests
import re
import json
from PIL import Image, ImageTk
from tkintermapview import TkinterMapView
from geopy.geocoders import Nominatim
from exportar import exportar
from atualizacoes import verificar_atualizacoes
from resultados import resultados, preparar_irradiacao
from acesso import LoginDialog, carregar_configuracoes, atualizar_manter_conectado, obter_organizacao
from popups import CustomInfoPopup, EditItemWindow, YesNoPopup, AddManualItemWindow, AddItemWindow, ConsumoPopup, BigCustomInfoPopup
#import sv_ttk
import ctypes
from dotenv import load_dotenv
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except AttributeError:
    pass

restart = None

# Ajustar o caminho se executado como um executável PyInstaller
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

icon_path = "dimicon.ico"
icon_full_path = os.path.join(application_path, icon_path)

class Dimensionamento:
    def __init__(self, inversor, qtdinversor, qtdplacas, baterias, autotrafo):
        self.search_in_progress = False
        self.inversor = inversor
        self.qtdinversor = qtdinversor
        self.qtdplacas = qtdplacas
        self.baterias = baterias
        self.autotrafo = autotrafo

def restart_app(self, tipo=None):

    def on_yes():
        global restart
        if not tipo:
            self.destroy()
            app = DimensionamentoApp()
            app.mainloop()
        else:
            restart = tipo
            self.destroy()
            app = DimensionamentoApp()
            app.mainloop()

    def on_no():
        return

    popup = YesNoPopup(self, "Confirmar", "Você realmente quer começar um novo dimensionamento?",
                       on_yes_callback=on_yes, on_no_callback=on_no)
    popup.grab_set()

estados = {
    "Acre",
    "Alagoas",
    "Amapá",
    "Amazonas",
    "Bahia",
    "Ceará",
    "Distrito Federal",
    "Espírito Santo",
    "Goiás",
    "Maranhão",
    "Mato Grosso",
    "Mato Grosso do Sul",
    "Minas Gerais",
    "Pará",
    "Paraíba",
    "Paraná",
    "Pernambuco",
    "Piauí",
    "Rio de Janeiro",
    "Rio Grande do Norte",
    "Rio Grande do Sul",
    "Rondônia",
    "Roraima",
    "Santa Catarina",
    "São Paulo",
    "Sergipe",
    "Tocantins"
}

def convert_coordinates_to_address(latitude, longitude):
    # Inicialize o objeto Nominatim
    geolocator = Nominatim(user_agent="convert_coordinates_to_address")

    try:
        # Usa o serviço reverse do Nominatim para converter as coordenadas em endereço
        location = geolocator.reverse((latitude, longitude), exactly_one=True)

        # Extrai a cidade, estado e país do resultado
        address = location.raw['address']
        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', '')

        # Formata o endereço como desejado
        if city:
            formatted_address = f"{city}, {state}, {country}"
            estado = state
        elif state:
            formatted_address = f"{state}, {country}"
            estado = state
        else:
            formatted_address = None
            estado = None

        return formatted_address, estado

    except Exception as e:
        print("Erro ao converter coordenadas para endereço:", e)
        return None

def salvar_tema_preferido(tema):
    diretorio_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
    arquivo_config = os.path.join(diretorio_documentos, 'config_tema.json')

    with open(arquivo_config, 'w') as arquivo:
        json.dump({'tema': tema}, arquivo)

def carregar_tema_preferido():
    diretorio_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
    arquivo_config = os.path.join(diretorio_documentos, 'config_tema.json')

    try:
        with open(arquivo_config, 'r') as arquivo:
            config = json.load(arquivo)
            return config.get('tema', 'light')
    except FileNotFoundError:
        return 'light'

class DimensionamentoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.user_accepted_terms = self.check_terms_accepted()
        self.withdraw()
        self.tema_preferido = carregar_tema_preferido()
        self.search_in_progress = False
        self.title(f"Simulação de Sistemas Híbridos e Off-Grids")
        self.geometry("1100x600")
        self.center_window(1100, 600)
        self.iconbitmap(icon_full_path)
        self.search_in_progress = False
        self.resizable(False, False)

        global versao
        global restart

        if obter_organizacao() is None:
            self.organizacao = ""
        else:
            self.organizacao = obter_organizacao()

        if getattr(sys, 'frozen', False):
            tcl_path = sys._MEIPASS
        else:
            tcl_path = os.path.dirname(os.path.abspath(__file__))

        tcl_full_path = os.path.join(tcl_path, "azure.tcl")
        tcl_folder = tcl_full_path
        self.tk.call('source', tcl_folder)
        self.tk.call("set_theme", self.tema_preferido)

        self.tabControl = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab1, text='Início')
        self.tabControl.pack(expand=1, fill="both")

        # Carrega inicialmente a logo para o tema 'dark'
        self.logo_path = self.get_logo_path(self.tema_preferido)
        self.logo_image = Image.open(self.logo_path)
        self.tk_logo_image = ImageTk.PhotoImage(self.logo_image)
        self.logo_label = ttk.Label(self.tab1, image=self.tk_logo_image)
        self.logo_label.pack(pady=(40, 50))

        self.system_choice = tk.StringVar(value="")
        self.network_type = tk.StringVar(value="")
        self.selected_pannel = tk.StringVar()
        self.selected_pannel.set("Selecionar")
        self.selected_inclination = tk.StringVar()
        self.selected_inclination.set("Selecionar")
        self.temperature_var = tk.StringVar(value="-0.3")
        self.security_factor_var = tk.StringVar(value="0")
        self.selected_orientation = tk.StringVar()
        self.selected_orientation.set("Selecionar")
        self.modo_calculo = tk.StringVar()
        self.modo_calculo.set("Somar consumo + cargas")

        self.inicio()

        if restart:
            restart = None
            self.lbl_organizacao.config(text=obter_organizacao())
            self.deiconify()
        else:
            self.show_login()

    def check_terms_accepted(self):
        terms_file_path = os.path.join(os.path.expanduser("~"), "Documents", "terms_accepted.txt")
        return os.path.exists(terms_file_path)

    def mark_terms_as_accepted(self):
        terms_file_path = os.path.join(os.path.expanduser("~"), "Documents", "terms_accepted.txt")
        with open(terms_file_path, "w") as f:
            f.write("accepted")

    def show_login(self):
        login_window = LoginDialog(self)
        login_window.update_idletasks() # Força a janela a atualizar seu estado
        if login_window.winfo_exists():
            #login_window.grab_set()  # Impede interações com outras janelas
            login_window.protocol("WM_DELETE_WINDOW", self.on_login_close)  # Gerencia o evento de fechar a janela de login

    def logout(self):
        # Desabilita 'Manter Conectado' e salva o estado
        ultimo_login = carregar_configuracoes().get('ultimo_login', '')
        atualizar_manter_conectado(ultimo_login, False)

        # Esconde a janela principal
        self.withdraw()

        # Verifica se a janela de login já existe e está aberta; se não, mostra novamente
        if hasattr(self, 'login_window') and self.login_window.winfo_exists():
            self.login_window.deiconify()  # Mostra a tela de login se já estiver aberta
        else:
            self.show_login()  # Caso contrário, abre uma nova tela de login

    def on_login_close(self):
        self.destroy()  # Fecha a aplicação se a janela de login for fechada

    def center_window(self, width, height):
        self.update_idletasks()  # Garante que todas as métricas da janela estejam atualizadas

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calcula a posição central normalmente
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f'{width}x{height}+{x}+{y}')

    def inicio(self):
        global restart

        button_width = 30

        ttk.Button(self.tab1, text="Dimensionamento Híbrido", command=lambda: self.open_dimensionamentos("Híbrido"),
                   width=button_width,
                   style="Accent.TButton").pack(pady=(5, 15))
        ttk.Button(self.tab1, text="Dimensionamento Off-Grid", command=lambda: self.open_dimensionamentos("Offgrid"),
                   width=button_width,
                   style="Accent.TButton").pack(pady=15)
        ttk.Button(self.tab1, text="Recomendações e Boas Práticas", command=lambda: self.open_recomendacoes(),
                   width=button_width).pack(pady=15)

        # Adiciona o botão para alternar o tema
        self.theme_var = tk.IntVar(value=("dark" == self.tema_preferido))  # Atualiza com base no tema preferido

        # Frame para conter elementos centralizados na parte inferior
        bottom_frame = ttk.Frame(self.tab1)
        bottom_frame.pack(side='bottom', fill='x', pady=(0, 25))

        # Label de Organização
        global organizacao
        organizacao = self.organizacao
        self.lbl_organizacao = ttk.Label(bottom_frame, text=self.organizacao)
        self.lbl_organizacao.pack(side='top', pady=(0, 15))

        # Botões "Alternar Tema" e "Sair"
        buttons_frame = ttk.Frame(bottom_frame)
        buttons_frame.pack(side='top', pady=(5, 15))

        self.btn_tema = ttk.Button(buttons_frame, text="   Alternar Tema   ", command=self.toggle_theme)
        self.btn_tema.pack(side='left', padx=10)

        self.btn_sair = ttk.Button(buttons_frame, text="Sair", command=self.logout)
        self.btn_sair.pack(side='left', padx=10)

        if restart:
            self.open_dimensionamentos(restart)

    def get_logo_path(self, theme):
        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))

        if theme == 'dark':
            logo_filename = 'utflogodark.png'
        else:
            logo_filename = 'utflogo.png'

        return os.path.join(application_path, logo_filename)

    def apply_custom_styles(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=24)

    def toggle_theme(self):
        new_theme = "light" if self.theme_var.get() else "dark"
        self.tk.call("set_theme", new_theme)
        self.theme_var.set(1 if new_theme == "dark" else 0)

        # Reaplicar as configurações personalizadas de estilo
        self.apply_custom_styles()

        # Carregar e exibir a nova logo com base no tema
        new_logo_path = self.get_logo_path(new_theme)
        new_logo_image = Image.open(new_logo_path)
        self.tk_logo_image = ImageTk.PhotoImage(new_logo_image)
        self.logo_label.config(image=self.tk_logo_image)

        # Salvar a preferência de tema do usuário
        salvar_tema_preferido(new_theme)

    def open_recomendacoes(self):
        popup = BigCustomInfoPopup(self, "Guia de Boas Práticas para Dimensionamento",
        ("Este é um guia com alguns pontos importantes a considerar ao dimensionar sistemas utilizando este software.\n\n"
         "1. A parte mais crucial ao dimensionar um sistema híbrido ou off-grid não é o cálculo em si, mas o preenchimento correto das informações. Certifique-se de preencher todos os dados de maneira adequada ao sistema a ser dimensionado, sem diminuir as cargas para enquadrar em sistemas menores.\n\n"
         "2. Evite utilizar bombas no dimensionamento. Bombas possuem uma corrente de partida elevada e, para utilizá-las, é recomendado apenas um motor de até 1.5cv apenas no inversor Renac off-grid 5kW.")
        )
        popup.grab_set()

    def open_dimensionamentos(self, tipo):
        self.system_choice = tipo
        if hasattr(self, 'tab2'):
            restart_app(self, tipo)
        else:
            self.show_tab(1)

    def detalhes_sistema(self, add_widget):

        if add_widget == 1:
            upper_frame = ttk.Frame(self.tab2)
            upper_frame.pack(padx=10, pady=(10, 0), side="top", fill="both", expand=True)

            main_frame = ttk.Frame(upper_frame)
            main_frame.pack(padx=0, pady=(0, 0), side="right", fill="both", expand=True)

            network_frame = ttk.LabelFrame(main_frame, text="Tipo de Rede", padding=(10, 10))
            network_frame.pack(padx=10, pady=(3, 10), side="top", fill="both", expand=True)

            options = [
                #"Monofásico 127V (Fase + Neutro/Terra)",
                "Monofásico 220V (Fase + Neutro + Terra)",
                "Bifásico 220V (Fase + Fase + Neutro/Terra)",
                #"Trifásico 220V (Fase + Fase + Fase + Neutro + Terra)",
                "Trifásico 380V (Fase + Fase + Fase + Neutro + Terra)"
            ]

            pannels = ["550W", "555W", "570W", "580W", "585W", "610W"]

            orientations = ["Norte", "Noroeste", "Oeste", "Sudoeste", "Sul", "Sudeste", "Leste", "Nordeste"]

            inclinations = ["0°", "5°", "10°", "15°", "20°", "25°", "30°", "35°"]

            for idx, option in enumerate(options):
                ttk.Radiobutton(network_frame, text=option, variable=self.network_type, value=option).grid(row=idx, column=0, padx=10, pady=(40, 0), sticky='w')

            ttk.Button(network_frame, text="?", width=1, command=lambda: self.ajuda("tipo_rede")).grid(row=0, column=1, padx=(10, 0), pady=(40, 0), sticky='n')

            right_frame = ttk.LabelFrame(upper_frame, text="Dados da Usina")
            right_frame.pack(side="left", padx=(10, 10), pady=(0, 10))

            def caixa(texto, linha, coluna):
                """Caixa da grade de dados da usina com uma linha centralizada para o campo e o botão de ajuda."""
                frame = ttk.LabelFrame(right_frame, text=texto, padding=(10, 10))
                padx = (20, 10) if coluna == 0 else (10, 20)
                pady = (15, 10) if linha == 0 else ((10, 20) if linha == 2 else 10)
                frame.grid(row=linha, column=coluna, padx=padx, pady=pady, sticky="nsew")
                conteudo = ttk.Frame(frame)
                conteudo.pack(expand=True, pady=30)
                return conteudo

            system_box = caixa("Tipo do Sistema", 0, 0)
            ttk.Label(system_box, text=str(self.system_choice)).pack()

            pannel_box = caixa("Potência dos Painéis", 0, 1)
            ttk.OptionMenu(pannel_box, self.selected_pannel, self.selected_pannel.get(), *pannels).pack(side="left")
            ttk.Button(pannel_box, text="?", width=1, command=lambda: self.ajuda("potencia_painel")).pack(side="left", padx=(5, 0))

            orientation_box = caixa("Orientação dos Painéis", 1, 0)
            ttk.OptionMenu(orientation_box, self.selected_orientation, self.selected_orientation.get(), *orientations).pack(side="left")
            ttk.Button(orientation_box, text="?", width=1, command=lambda: self.ajuda("orientacao")).pack(side="left", padx=(5, 0))

            inclination_box = caixa("Inclinação dos Painéis", 1, 1)
            ttk.OptionMenu(inclination_box, self.selected_inclination, self.selected_inclination.get(), *inclinations).pack(side="left")
            ttk.Button(inclination_box, text="?", width=1, command=lambda: self.ajuda("inclinacao")).pack(side="left", padx=(5, 0))

            security_box = caixa("Fator de Segurança (%)", 2, 0)
            ttk.Entry(security_box, textvariable=self.security_factor_var, width=8).pack(side="left")
            ttk.Button(security_box, text="?", width=1, command=lambda: self.ajuda("fator_seguranca")).pack(side="left", padx=(5, 0))
            self.security_factor_var.trace_add('write', self.validate_security_factor)

            temperature_box = caixa("Coef. de Temperatura (%/°C)", 2, 1)
            ttk.Entry(temperature_box, textvariable=self.temperature_var, width=8).pack(side="left")
            ttk.Button(temperature_box, text="?", width=1, command=lambda: self.ajuda("coef_temperatura")).pack(side="left", padx=(5, 0))
            self.temperature_var.trace_add('write', self.validate_temperature_coefficient)

            button_frame = ttk.Frame(main_frame, padding=(20, 10))
            button_frame.pack(padx=20, pady=(30, 30), side="bottom", fill="both", expand=True)

            next_button = ttk.Button(button_frame, style="Accent.TButton", text="Próximo", command=lambda: self.show_tab(2))
            next_button.pack(padx=40, pady=60)

    TEXTOS_AJUDA = {
        "tipo_rede": ("Tipo de Rede",
                      "Tipo de ligação da unidade consumidora, informado na conta de energia. "
                      "Os inversores cadastrados operam em 220 V e atendem redes monofásicas 220 V, "
                      "bifásicas 220 V e trifásicas 380 V (220 V entre fase e neutro)."),
        "potencia_painel": ("Potência dos Painéis",
                            "Potência nominal (W) do módulo fotovoltaico que será utilizado, conforme o "
                            "datasheet ou o estoque disponível. Ela define quantos módulos podem ser "
                            "ligados em série em cada inversor."),
        "orientacao": ("Orientação dos Painéis",
                       "Direção para a qual os módulos estarão voltados. No Brasil (hemisfério Sul), "
                       "a orientação Norte é a que gera mais energia ao longo do ano; orientações "
                       "Leste e Oeste geram menos, e Sul é a menos favorável."),
        "inclinacao": ("Inclinação dos Painéis",
                       "Ângulo entre os módulos e o plano horizontal. Normalmente segue a inclinação "
                       "do telhado. Em estruturas de solo, um valor próximo da latitude do local "
                       "favorece a geração ao longo do ano."),
        "coef_temperatura": ("Coeficiente de Temperatura",
                             "Coeficiente de temperatura de potência do módulo, informado no datasheet "
                             "(em %/°C). O valor recomendado é -0.3%/°C. Caso seja utilizado um valor "
                             "diferente, consulte um engenheiro projetista para validar."),
        "fator_seguranca": ("Fator de Segurança",
                            "Margem adicional opcional, em %, aplicada sobre a eficiência do sistema. "
                            "As perdas por temperatura, cabeamento, inversor, sujeira, degradação e "
                            "ângulo de incidência já são consideradas no cálculo, por isso o valor "
                            "padrão é 0%. Use um valor maior apenas para dar folga extra ao gerador."),
    }

    def ajuda(self, chave):
        titulo, texto = self.TEXTOS_AJUDA[chave]
        popup = CustomInfoPopup(self, titulo, texto)
        popup.grab_set()

    def validate_security_factor(self, *args):
        valor = self.security_factor_var.get()
        if valor == "":
            return
        try:
            if not 0 <= float(valor) <= 99:
                self.security_factor_var.set("0")
        except ValueError:
            self.security_factor_var.set("0")

    def fator_seguranca(self):
        """Fator de segurança digitado pelo usuário, em fração (campo vazio = 0)."""
        try:
            return float(self.security_factor_var.get() or 0) / 100
        except ValueError:
            return 0.0

    def validate_temperature_coefficient(self, *args):
        try:
            temperature_coefficient = float(self.temperature_var.get())
            if temperature_coefficient > 0.00 or temperature_coefficient < -0.99:
                self.temperature_var.set("-0.99")
        except ValueError:
            self.temperature_var.set("-0.99")

    def show_tab(self, index):
        add_widget = 0

        if index >= 2:
            if not self.network_type.get():
                CustomInfoPopup(self, "Informações Faltantes", "Por favor, selecione o tipo de rede.")
                return

            if self.selected_orientation.get() == "Selecionar" or self.selected_inclination.get() == "Selecionar" or self.selected_pannel.get() == "Selecionar":
                CustomInfoPopup(self, "Informações Faltantes", "Por favor, preencha todos os dados da usina.")
                return

        if index == 1:
            if hasattr(self, 'tab2'):
                self.tabControl.select(self.tab2)
            else:
                self.tab2 = ttk.Frame(self.tabControl)
                self.tabControl.add(self.tab2, text='Detalhes do Sistema')
                add_widget = 1

            self.detalhes_sistema(add_widget)

        if index == 2:
            if hasattr(self, 'tab3'):
                self.tabControl.select(self.tab3)
            else:
                self.tab3 = ttk.Frame(self.tabControl)
                self.tabControl.add(self.tab3, text='Localização')
                add_widget = 1

            self.localizacao(add_widget)

        if index == 3:
            if hasattr(self, 'tab4'):
                self.tabControl.select(self.tab4)
            else:
                self.tab4 = ttk.Frame(self.tabControl)
                self.tabControl.add(self.tab4, text='Dados de Consumo')
                add_widget = 1

            self.detalhes_consumo(add_widget)

        if index == 4 and not hasattr(self, 'tab4'):
            self.tab4 = ttk.Frame(self.tabControl)
            self.tabControl.add(self.tab4, text='Dados de Consumo')
            self.tabControl.tab(self.tab4, state='disabled')
            add_widget = 1
            self.detalhes_consumo(add_widget)

        if index == 4:
            if hasattr(self, 'tab5'):
                self.tabControl.select(self.tab5)
            else:
                self.tab5 = ttk.Frame(self.tabControl)
                self.tabControl.add(self.tab5, text='Tabela de Cargas')
                add_widget = 1

            self.tabela_de_cargas(add_widget)

        if index == 5:

            autonomia_max = 0
            consumo_max = 0
            potencia_max = 0
            potencia_total = 0
            consumo_total = 0

            for child in self.tree.get_children():
                item_values = self.tree.item(child, 'values')

                try:
                    autonomia = float(item_values[3])
                    potencia = float(item_values[2]) * float(item_values[1])
                    consumo = float(item_values[4])

                    autonomia_max = max(autonomia_max, autonomia)
                    # Maior equipamento individual: valores por unidade
                    consumo_max = max(consumo_max, consumo / float(item_values[1]))
                    potencia_max = max(potencia_max, potencia / float(item_values[1]))
                    potencia_total += potencia
                    consumo_total += consumo

                except ValueError:
                    continue

            consumo_total = round(consumo_total * 1, 1)

            if autonomia_max == 0 or potencia_total == 0 or consumo_total == 0:
                CustomInfoPopup(self, "Informações Faltantes", "Por favor, adicione pelo menos um item na tabela de cargas.")
                return

            self.endereco_selecionado, self.estado = self.obter_endereco()

            if self.coordenadas_selecionadas is None:
                CustomInfoPopup(self, "Seleção", "Por favor, selecione uma localização adicionando um marcador.")
                return

            if self.estado not in estados:
                CustomInfoPopup(self, "Localização inválida", "O local da instalação é inválido. Por favor, selecione um local dentro do Brasil.")
                return

            if not self.user_accepted_terms:
                self.show_terms_popup()
                return

            tabela = []
            for item in self.tree.get_children():
                item_data = self.tree.item(item, "values")
                tabela.append(item_data)

            tabela_consumo = self.obter_consumo_mensal()

            status = self.resultados_finais(self.system_choice, self.network_type.get(), autonomia_max, consumo_max, potencia_max, potencia_total, consumo_total, self.selected_pannel.get(), tabela, self.coordenadas_selecionadas, self.endereco_selecionado, self.selected_orientation.get(), self.selected_inclination.get(), tabela_consumo, self.temperature_var.get(), self.estado, self.modo_calculo.get())

            if status != "ok":
                CustomInfoPopup(self, "Erro", status)
                return

        self.tabControl.select(index)

    def show_terms_popup(self):
        popup = tk.Toplevel()
        popup.title("Aviso")
        popup.iconbitmap(icon_full_path)
        popup.resizable(False, False)

        # Configurações de tamanho e posição da janela
        window_width = 500
        window_height = 300
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))
        popup.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        # Label para mostrar a mensagem
        label = ttk.Label(popup, text="Este aplicativo é de caráter informativo. A Vertys Solar Group não se responsabiliza pelas instalações elétricas. Cabe ao responsável técnico do projeto validar e aplicar as informações descritas de acordo com cada projeto, bem como avaliar a viabilidade de cada instalação.", wraplength=430)
        label.pack(padx=20, pady=20)

        self.accept_terms_var = tk.IntVar()

        checkbox = ttk.Checkbutton(popup, text="Estou ciente", variable=self.accept_terms_var)
        checkbox.pack(pady=5)

        def on_accept():
            if self.accept_terms_var.get() == 1:
                self.mark_terms_as_accepted()
                self.user_accepted_terms = True
                popup.destroy()
                self.show_tab(5)

        accept_button = ttk.Button(popup, text="Continuar", command=on_accept, style="Accent.TButton")
        accept_button.pack(pady=10)

        popup.transient(self.master)
        popup.grab_set()

    def obter_endereco(self):
        latitude, longitude = self.coordenadas_selecionadas[0], self.coordenadas_selecionadas[1]
        try:
            endereco_obj, estado = convert_coordinates_to_address(latitude, longitude)
            return endereco_obj, estado
        except TypeError:
            return None, None

    def obter_consumo_mensal(self):
        consumo_mensal = []

        for item in self.tree_consumo.get_children():
            item_values = self.tree_consumo.item(item, 'values')

            consumo = float(item_values[1])
            consumo_mensal.append(consumo)

        return consumo_mensal

    def localizacao(self, add_widget):

        if add_widget == 1:

            left_frame = ttk.Frame(self.tab3)
            left_frame.pack(side="left", fill="both", expand=True)

            search_frame = ttk.LabelFrame(left_frame, text="Pesquisar Cidade/Estado", padding=(20, 10))
            search_frame.pack(fill="x", padx=20, pady=10)

            search_entry = ttk.Entry(search_frame)
            search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=(10, 15))
            search_button = ttk.Button(search_frame, text="Buscar", style="Accent.TButton", command=lambda: self.buscar_local(search_entry))
            search_button.pack(side="left", pady=(10, 15))

            search_entry.bind('<Return>', lambda event: self.buscar_local(search_entry))

            # LabelFrame para o mapa
            map_frame = ttk.LabelFrame(left_frame, text="Selecione o Local da Instalação", padding=(10, 10))
            map_frame.pack(fill="both", expand=True, padx=20, pady=10)

            self.map_view = TkinterMapView(map_frame, width=400, height=400, corner_radius=10)
            self.map_view.set_tile_server("https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga")
            self.map_view.pack(fill="both", expand=True)
            self.map_view.set_position(-23.550520, -46.633308)
            self.map_view.set_zoom(10)

            self.map_view.add_right_click_menu_command(label="Selecionar Local",
                                                    command=self.adicionar_marcador_rclick,
                                                    pass_coords=True)

            # Configuração da parte direita
            actions_frame = ttk.LabelFrame(self.tab3, padding=(10, 10))
            actions_frame.pack(side="right", fill="y", padx=(5, 20), pady=10)

            add_marker_button = ttk.Button(actions_frame, text="Selecionar Local", style="Accent.TButton",
                                           command=self.adicionar_marcador)
            add_marker_button.pack(fill="x", padx=20, pady=10)

            remove_marker_button = ttk.Button(actions_frame, text="Remover Seleção", command=self.remover_marcador)
            remove_marker_button.pack(fill="x", padx=20, pady=10)

            next_button = ttk.Button(actions_frame, text="Próximo", command=self.obter_coordenadas_marcador,
                                     style="Accent.TButton")
            next_button.pack(side="bottom", fill="x", padx=20, pady=20)

    def adicionar_marcador_rclick(self, coords):

        latitude, longitude = coords[0], coords[1]

        self.coordenadas_selecionadas = (latitude, longitude)

        if hasattr(self, 'marcador_atual'):
            self.map_view.delete(self.marcador_atual)

        texto_marcador = "Localização Selecionada"
        self.marcador_atual = self.map_view.set_marker(coords[0], coords[1], text=texto_marcador)

    def adicionar_marcador(self):
        try:
            current_position = self.map_view.get_position()
            latitude, longitude = current_position[0], current_position[1]

            self.coordenadas_selecionadas = (latitude, longitude)

            if hasattr(self, 'marcador_atual'):
                self.map_view.delete(self.marcador_atual)

            texto_marcador = "Localização Selecionada"
            self.marcador_atual = self.map_view.set_marker(latitude, longitude, text=texto_marcador)

        except AttributeError:
            print("Método get_position ou convert_coordinates_to_address não disponível.")

    def remover_marcador(self):
        if hasattr(self, 'marcador_atual'):
            self.endereco_selecionado = None
            self.coordenadas_selecionadas = None
            self.marcador_atual.delete()
            del self.marcador_atual

    def obter_coordenadas_marcador(self):
        if hasattr(self, 'coordenadas_selecionadas') and self.coordenadas_selecionadas is not None:
            if self.system_choice == "Offgrid":
                self.show_tab(4)
            else:
                self.show_tab(3)
        else:
            CustomInfoPopup(self, "Seleção", "Por favor, selecione uma localização adicionando um marcador.")

    def buscar_local(self, search_entry):
        if not self.search_in_progress:
            self.search_in_progress = True
            endereco = search_entry.get()
            endereco += ', Brasil'
            url = f'https://nominatim.openstreetmap.org/search?q={endereco}&format=jsonv2&addressdetails=1&limit=1&email=yourATreal.email'
            headers = {'User-Agent': 'Dimensionamentos Vertys/1.0 (ti@vertysgroup.com)'}

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # This will raise an HTTPError for bad responses
                resultado_pesquisa = response.json()

                if not resultado_pesquisa:
                    print("Cidade/Estado não encontrado.")
                else:
                    location = resultado_pesquisa[0]
                    latitude = float(location['lat'])
                    longitude = float(location['lon'])
                    current_position = latitude, longitude  # Centraliza o mapa
                    latitude, longitude = current_position[0], current_position[1]
                    self.map_view.set_position(latitude, longitude)

                    self.coordenadas_selecionadas = (latitude, longitude)

                    if hasattr(self, 'marcador_atual'):
                        self.map_view.delete(self.marcador_atual)

                    texto_marcador = "Localização Selecionada"
                    self.marcador_atual = self.map_view.set_marker(latitude, longitude, text=texto_marcador)

            except requests.exceptions.RequestException as e:
                print(f"Erro ao buscar localização: {e}")
            finally:
                self.search_in_progress = False

    def detalhes_consumo(self, add_widget):
        if add_widget == 1:
            # Criando um frame para dividir a tela em esquerda e direita
            frame = ttk.Frame(self.tab4)
            frame.pack(expand=True, fill='both')

            # Parte esquerda: Labelframe de Atenção
            left_frame = ttk.Frame(frame)
            left_frame.pack(side='right', fill='both', pady=0, padx=(20, 10), expand=True)

            attention_frame = ttk.Labelframe(left_frame, text='Observação', padding=20)
            attention_frame.pack_propagate(False)
            attention_frame.config(width=200, height=120)
            attention_frame.pack(fill='both', pady=(20, 10), padx=20, expand=True)
            attention_label = ttk.Label(attention_frame, wraplength=300, text='Caso queira dimensionar somente a parte Off-Grid de um sistema Híbrido, não preencha a tabela de consumo.')
            attention_label.pack(fill='x', expand=True)

            observation_frame = ttk.Labelframe(left_frame, text='Modo de Cálculo', padding=20)
            observation_frame.pack_propagate(False)
            observation_frame.config(width=200, height=120)
            observation_frame.pack(fill='both', pady=10, padx=20, expand=True)

            modos = ["Somar consumo + cargas", "Considerar maior"]

            modo_calculo_menu = ttk.OptionMenu(observation_frame, self.modo_calculo, self.modo_calculo.get(), *modos)
            modo_calculo_menu.pack(side="left", pady=30, padx=(31, 0))

            doubt_calculo = ttk.Button(observation_frame, text="?", command=self.doubt_calculo, width=2)
            doubt_calculo.pack(side="left", pady=30, padx=(2, 10))

            ttk.Button(left_frame, text="Próximo", command=lambda: self.show_tab(4),
                       style="Accent.TButton").pack(padx=20, pady=(60, 80))

            # Parte direita: Treeview para os meses e consumo
            right_frame = ttk.Labelframe(frame, text='Tabela de Consumo', padding=(20, 0))
            right_frame.pack(side='left', fill='both', pady=20, padx=(35, 0), expand=True)

            # Contêiner da TreeView com dimensões fixas
            tree_container = ttk.Frame(right_frame, height=325, width=340)
            tree_container.pack_propagate(False)
            tree_container.pack(expand=True, pady=(0, 0), side='top')

            # TreeView dentro do contêiner
            columns = ('Mês', 'Consumo')
            style = ttk.Style()
            style.configure("Treeview", rowheight=24)

            self.tree_consumo = ttk.Treeview(tree_container, columns=columns, show='headings', style="Treeview")
            self.tree_consumo.heading('Mês', text='Mês')
            self.tree_consumo.heading('Consumo', text='Consumo (KWh)')
            self.tree_consumo.column("Mês", width=100)
            self.tree_consumo.column("Consumo", width=100, anchor="center")
            self.tree_consumo.bind("<Double-1>", self.on_double_click)

            # Adicionando dados à Treeview
            meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                     'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            for mes in meses:
                self.tree_consumo.insert('', tk.END, values=(mes, 0))

            self.tree_consumo.pack(fill='both', expand=True)

            # Botões abaixo da Treeview
            button_frame = ttk.Frame(right_frame)
            button_frame.pack(side='bottom', pady=(5, 20))
            edit_button = ttk.Button(button_frame, text="Editar Selecionados", command=self.editar_selecionado,
                                     style="Accent.TButton")
            edit_all_button = ttk.Button(button_frame, text="Selecionar Tudo", command=self.selecionar_tudo)

            edit_button.pack(side='left', padx=(10, 7), pady=5)
            edit_all_button.pack(side='left', padx=(7, 10), pady=5)

            info_frame = ttk.Frame(right_frame)
            info_frame.pack(side='bottom', pady=(0, 10))

            center_frame = ttk.Frame(info_frame)
            center_frame.pack(anchor="center")

            self.label_consumo_medio = ttk.Label(center_frame, text="Média: 0 KWh")
            self.label_consumo_medio.pack(side="top", padx=10)

    def doubt_calculo(self):
        popup = BigCustomInfoPopup(self, "Modo de Cálculo",
                                "O modo de cálculo determina a quantidade necessária de painéis, considerando diferentes critérios:\n\n"
                                "1. Somar consumo + cargas: Neste modo, a quantidade de módulos é calculada para atender tanto às necessidades de carga das baterias quanto ao consumo mensal registrado na tabela de consumo. Isso resulta em uma quantidade maior de módulos, garantindo que ambas as demandas sejam satisfeitas, possivelmente proporcionando um excedente de energia.\n\n"
                                "2. Considerar maior: A quantidade de módulos é determinada pelo maior valor entre o consumo diário e a necessidade de carga das baterias. Este método resulta em uma quantidade menor de módulos, priorizando a maior demanda. No entanto, pode ser insuficiente para suprir completamente o consumo nos dias em que também é necessário recarregar as baterias.\n\n")
        popup.grab_set()

    def on_double_click(self, event):
        region = self.tree_consumo.identify("region", event.x, event.y)
        column = self.tree_consumo.identify_column(event.x)
        item = self.tree_consumo.identify_row(event.y)

        if region != "cell" or self.tree_consumo.heading(column)['text'] != 'Consumo (KWh)':
            return

        x, y, width, height = self.tree_consumo.bbox(item, column)

        value = self.tree_consumo.item(item, 'values')[1]
        entry = tk.Entry(self.tree_consumo, width=10)
        entry.place(x=x, y=y, width=width, height=height, anchor='nw')
        entry.insert(0, value)
        entry.focus_set()

        def validate_and_save(event=None):
            # Valida e salva o valor se for um float válido
            try:
                float_value = float(entry.get())
                if float_value == 0.0:
                    float_value = 0
                self.tree_consumo.item(item, values=(self.tree_consumo.item(item, 'values')[0], float_value))
                self.atualizar_media_consumo()
            except ValueError:
                # Se o valor não for um float válido, não faz nada ou mostra um erro
                # Aqui você pode optar por mostrar uma mensagem de erro ao usuário
                print("Erro: Valor inserido não é um número válido.")
            finally:
                entry.destroy()  # Remove o Entry independente do resultado

        entry.bind('<Return>', validate_and_save)
        entry.bind('<FocusOut>', validate_and_save)

    def atualizar_media_consumo(self):
        # Essa função deve calcular e atualizar a média de consumo
        soma_consumo = 0
        total_itens = len(self.tree_consumo.get_children())
        for item in self.tree_consumo.get_children():
            consumo_atual = self.tree_consumo.item(item, 'values')[1]
            soma_consumo += float(consumo_atual)

        if total_itens > 0:
            media_consumo = soma_consumo / total_itens
            self.label_consumo_medio.config(text=f"Média: {media_consumo:.2f} KWh")

    def editar_selecionado(self):
        selected_item = self.tree_consumo.selection()

        if selected_item:
            def atualizar_itens_selecionados(valor):
                for item in self.tree_consumo.selection():
                    self.tree_consumo.item(item, values=(self.tree_consumo.item(item, 'values')[0], valor))

                soma_consumo = 0
                total_itens = len(self.tree_consumo.get_children())
                for item in self.tree_consumo.get_children():
                    consumo_atual = self.tree_consumo.item(item, 'values')[1]
                    soma_consumo += float(consumo_atual)

                if total_itens > 0:
                    media_consumo = soma_consumo / total_itens
                    self.label_consumo_medio.config(text=f"Média: {media_consumo:.2f} KWh")

            popup = ConsumoPopup(self.tab4, atualizar_itens_selecionados)
            popup.grab_set()
        else:
            CustomInfoPopup(self, "Seleção", "Por favor, selecione um mês para editar o consumo.")
            return

    def selecionar_tudo(self):
        itens = self.tree_consumo.get_children()
        self.tree_consumo.selection_set(itens)

    def tabela_de_cargas(self, add_widget):

        if add_widget == 1:
            # Configuração da Treeview
            self.tree_frame = ttk.Frame(self.tab5)
            self.tree_frame.pack(padx=20, pady=(20, 5), fill="both", expand=True)

            self.tree_scroll = ttk.Scrollbar(self.tree_frame)
            self.tree_scroll.pack(side="right", fill="y")

            self.tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set,
                                     columns=("Equipamento", "Quantidade", "Potência", "Autonomia", "Consumo"), show="headings")
            self.tree.column("Equipamento", anchor="center")
            self.tree.column("Quantidade", width=70, anchor="center")
            self.tree.column("Potência", width=100, anchor="center")
            self.tree.column("Autonomia", width=100, anchor="center")
            self.tree.column("Consumo", width=100, anchor="center")
            self.tree.heading("Equipamento", text="Equipamento")
            self.tree.heading("Quantidade", text="Quantidade")
            self.tree.heading("Potência", text="Potência (W)")
            self.tree.heading("Autonomia", text="Autonomia (h)")
            self.tree.heading("Consumo", text="Consumo (Wh)")
            self.tree.pack(side="left", fill="both", expand=True)

            self.tree_scroll.config(command=self.tree.yview)

            # Frame para informações adicionais
            self.info_frame = ttk.Frame(self.tab5)
            self.info_frame.pack(fill="x", padx=20, pady=(25, 0))

            self.center_frame = ttk.Frame(self.info_frame)
            self.center_frame.pack(anchor="center")

            self.label_autonomia_max = ttk.Label(self.center_frame, text="Autonomia Máxima: 0 h")
            self.label_autonomia_max.pack(side="left", padx=10)
            self.label_potencia_total = ttk.Label(self.center_frame, text="Soma das Potências: 0 W")
            self.label_potencia_total.pack(side="left", padx=10)
            self.label_consumo_total = ttk.Label(self.center_frame, text="Consumo Total: 0 Wh")
            self.label_consumo_total.pack(side="left", padx=10)

            self.button_frame = ttk.LabelFrame(self.tab5, text="")
            self.button_frame.pack(fill="x", expand=True, padx=20)

            self.tree.bind("<Double-1>", self.on_item_double_click)

            ttk.Button(self.button_frame, text="Adicionar", style="Accent.TButton", command=lambda: self.add_item()).pack(side="left", padx=(30, 15), pady=(20, 35))
            ttk.Button(self.button_frame, text="Adicionar Manualmente", style="Accent.TButton", command=lambda: self.add_manual_item()).pack(side="left", padx=15, pady=(20, 35))
            ttk.Button(self.button_frame, text="Editar", style="Accent.TButton", command=self.edit_selected_item).pack(side="left", padx=15,pady=(20, 35))
            ttk.Button(self.button_frame, text="Remover", command=self.remove_selected_item).pack(side="left", padx=15, pady=(20, 35))
            #ttk.Button(self.button_frame, text="Editar Catálogo", command=lambda: self.open_catalog()).pack(side="left", padx=10, pady=20)
            ttk.Button(self.button_frame, text="Ver Resultados", command=lambda: self.show_tab(5), style="Accent.TButton").pack(side="right", padx=30, pady=(20, 35))

    def on_item_double_click(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            self.edit_selected_item()
        else:
            self.add_item()

    def on_item_updated(self):
        self.atualizar_info_labels(self.tree)

    def atualizar_info_labels(self, tree):
        autonomia_max = 0
        consumo_max = 0
        potencia_max = 0
        potencia_total = 0
        consumo_total = 0

        for child in tree.get_children():
            item_values = tree.item(child, 'values')

            try:
                autonomia = float(item_values[3])
                potencia = float(item_values[2]) * float(item_values[1])
                consumo = float(item_values[4])

                # Atualizar os valores máximos e totais
                autonomia_max = max(autonomia_max, autonomia)
                # Maior equipamento individual: valores por unidade
                consumo_max = max(consumo_max, consumo / float(item_values[1]))
                potencia_max = max(potencia_max, potencia / float(item_values[1]))
                potencia_total += potencia
                consumo_total += consumo
            except ValueError:
                # Caso algum valor não possa ser convertido para inteiro, continue para o próximo item
                continue

        consumo_total = round(consumo_total * 1, 1)

        # Atualizar os textos dos labels
        self.label_autonomia_max.config(text=f"Autonomia Máxima: {autonomia_max} h")
        self.label_potencia_total.config(text=f"Soma das Potências: {potencia_total} W")
        self.label_consumo_total.config(text=f"Consumo Total: {consumo_total} Wh")

    def edit_selected_item(self):
        selected_item = self.tree.selection()

        if selected_item:
            item_id = selected_item[0]
            item_data = self.tree.item(item_id, 'values')
            EditItemWindow(self, item_id, *item_data, on_close=self.on_item_updated)
        else:
            CustomInfoPopup(self, "Seleção", "Por favor, selecione um equipamento para editar.")
            return

    def update_item_in_load_table(self, original_item, updated_data):
        self.tree.item(original_item, values=updated_data)
        self.atualizar_info_labels(self.tree)

    def remove_selected_item(self):
        selected_item = self.tree.selection()

        if selected_item:
            def on_yes():
                self.tree.delete(selected_item[0])
                self.atualizar_info_labels(self.tree)

            popup = YesNoPopup(self.master,
                               "Confirmar",
                               "Deseja remover o item selecionado?",
                               on_yes_callback=on_yes)
            popup.grab_set()
        else:
            CustomInfoPopup(self, "Seleção", "Por favor, selecione um equipamento para remover.")
            return

    def add_manual_item(self):
        AddManualItemWindow(self, on_close=self.on_item_updated)

    def add_to_load_table_manual(self, equipment, quantity, potencia, consumo, autonomia):

        self.tree.insert('', 'end', values=(equipment, quantity, potencia, autonomia, consumo))
        self.atualizar_info_labels(self.tree)

    def add_item(self):
        AddItemWindow(self, on_close=self.on_item_updated)

    def add_to_load_table(self, equipment, quantity):
        load_dotenv()
        api_key = os.getenv("SUPABASE_API_KEY")
        auth_key = os.getenv("SUPABASE_AUTH_KEY")
        url = "https://ktdmbdjzmisdtjhdlvnl.supabase.co/rest/v1/Catalogo de Cargas"
        headers = {
            "apikey": api_key,
            "Authorization": auth_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        # Prepara a URL para a consulta com filtragem por 'equipamento'
        query_url = f"{url}?equipamento=eq.{equipment}"

        # Realiza a consulta HTTP GET ao Supabase
        response = requests.get(query_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0]
                potencia = result['potencia']
                autonomia = result['autonomia']
                consumo = float(result['consumo']) * float(quantity)

                # Insere os dados na árvore de visualização
                self.tree.insert('', 'end', values=(equipment, quantity, potencia, autonomia, consumo))

                # Atualiza as informações no display
                self.atualizar_info_labels(self.tree)
            else:
                print("Equipamento não encontrado.")
        else:
            print(f"Erro ao acessar dados: {response.text}")

    def resultados_finais(self, tipo_sistema, tipo_rede, autonomia, consumo_max, potencia_max, potencia, consumo, painel, tabela, coordenadas, endereco, orientacao, inclinacao, tabela_consumo, temperatura, estado, modo_calculo):

        coordenadas_arredondadas = (round(coordenadas[0], 2), round(coordenadas[1], 2))

        # irradiação no plano dos módulos (Perez) e eficiência global do sistema
        hsp, eficiencia = preparar_irradiacao(coordenadas, obter_hsp(coordenadas), estado, orientacao, inclinacao, temperatura)
        fator_seguranca = self.fator_seguranca()
        eficiencia *= (1 - fator_seguranca)  # margem opcional do usuário (padrão 0%)

        # Calculando os dimensionamentos
        dimensionamento1, dimensionamento2, status = resultados(tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, painel, hsp, tabela_consumo, modo_calculo, tabela)

        if dimensionamento1 is None and dimensionamento2 is None:
            return status
        else:
            if hasattr(self, 'tab6'):
                self.tabControl.select(self.tab6)
            else:
                self.tab6 = ttk.Frame(self.tabControl)
                self.tabControl.add(self.tab6, text='Resultados')

        eficiencia = round(eficiencia, 4)

        # Remover conteúdo antigo de tab3 se existir
        for widget in self.tab6.winfo_children():
            widget.destroy()

        # Pack 1 - Informações Básicas
        pack1 = ttk.LabelFrame(self.tab6, text="Informações do Sistema")
        pack1.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=20)
        ttk.Label(pack1, text=f"Tipo do sistema: {tipo_sistema}").pack(anchor="w", padx=10, pady=(15, 5))
        tipo_rede_curto = re.sub(r"\s*\([^)]*\)", "", tipo_rede)
        ttk.Label(pack1, text=f"Tipo da rede: {tipo_rede_curto}").pack(anchor="w", padx=10, pady=5)
        ttk.Label(pack1, text=f"Potência dos painéis: {painel}").pack(anchor="w", padx=10, pady=5)
        #ttk.Label(pack1, text=f"Eficiência do sistema: {eficiencia}").pack(anchor="w", padx=10, pady=5)
        ttk.Label(pack1, text=f"Coordenadas: {coordenadas_arredondadas}").pack(anchor="w", padx=10, pady=5)
        ttk.Label(pack1, text=f"Autonomia máxima: {round(autonomia, 2)}h").pack(anchor="w", padx=10, pady=5)
        ttk.Label(pack1, text=f"Soma das potências: {int(potencia)}W").pack(anchor="w", padx=10, pady=5)
        ttk.Label(pack1, text=f"Consumo total: {int(consumo)}Wh").pack(anchor="w", padx=10, pady=5)
        ttk.Button(pack1, text="Atualizar Resultados", command=lambda: self.show_tab(5), style="Accent.TButton").pack(
            anchor="center", side="bottom", padx=20, pady=20)
        ttk.Button(pack1, text="Novo Dimensionamento", command=lambda: restart_app(self)).pack(
            anchor="center", side="bottom", padx=20, pady=0)

        # Pack 2 - Primeiro Dimensionamento
        if dimensionamento2 is not None:
            pack2 = ttk.LabelFrame(self.tab6, text="Dimensionamento Sugerido 1")
        else:
            pack2 = ttk.LabelFrame(self.tab6, text="Dimensionamento Sugerido")
        pack2.pack(side="left", fill="both", expand=True, padx=10, pady=20)
        ttk.Label(pack2, text=f"Inversor recomendado: {dimensionamento1.inversor}").pack(anchor="w", padx=10, pady=(15, 5))
        ttk.Label(pack2, text=f"Quantidade de inversores: {dimensionamento1.qtdinversor}").pack(anchor="w", padx=10, pady=5)
        ttk.Label(pack2, text=f"Quantidade de painéis: {dimensionamento1.qtdplacas}").pack(anchor="w", padx=10, pady=5)
        if dimensionamento1.autotrafo:
            ttk.Label(pack2, text=f"Necessário autotrafo: {dimensionamento1.autotrafo}").pack(anchor="w",padx=10, pady=5)
        num_baterias = len(dimensionamento1.baterias)

        if num_baterias == 1:
            bateria = list(dimensionamento1.baterias.keys())[0]
            ttk.Label(pack2, text=f"Modelo da Bateria: {bateria}").pack(anchor="w", padx=10, pady=5)
            ttk.Label(pack2, text=f"Quantidade de baterias: {dimensionamento1.baterias[bateria]}").pack(anchor="w", padx=10, pady=5)
        else:
            ttk.Label(pack2, text=f"Baterias Recomendadas:").pack(anchor="w", padx=10, pady=5)
            for i, bateria in enumerate(dimensionamento1.baterias):
                ttk.Label(pack2, text=f"Opção {i + 1}:").pack(anchor="w", padx=10, pady=5)
                ttk.Label(pack2, text=f"  Modelo da bateria: {bateria}").pack(anchor="w", padx=10, pady=5)
                ttk.Label(pack2, text=f"  Quantidade de baterias: {dimensionamento1.baterias[bateria]}").pack(anchor="w", padx=10, pady=5)
        if dimensionamento1.tabela_geracao is not None:
            media_geracao = round(sum(dimensionamento1.tabela_geracao) / len(dimensionamento1.tabela_geracao), 1)
            #ttk.Label(pack2, text=f"Geração mensal estimada: {media_geracao}kWh").pack(anchor="w", padx=10, pady=5)
        ttk.Button(pack2, text="Exportar", command=lambda: exportar(self, tipo_sistema, tipo_rede, eficiencia, autonomia, potencia, consumo, painel, dimensionamento1, tabela, endereco, coordenadas_arredondadas, orientacao, inclinacao, temperatura, fator_seguranca, tabela_consumo, hsp, modo_calculo, self.organizacao), style="Accent.TButton").pack(
            anchor="center", side="bottom", padx=20, pady=20)

        if dimensionamento2 is not None:
            # Pack 3 - Segundo Dimensionamento
            pack3 = ttk.LabelFrame(self.tab6, text="Dimensionamento Sugerido 2")
            pack3.pack(side="left", fill="both", expand=True, padx=(10, 20), pady=20)
            ttk.Label(pack3, text=f"Inversor recomendado: {dimensionamento2.inversor}").pack(anchor="w", padx=10, pady=(15, 5))
            ttk.Label(pack3, text=f"Quantidade de inversores: {dimensionamento2.qtdinversor}").pack(anchor="w", padx=10, pady=5)
            ttk.Label(pack3, text=f"Quantidade de painéis: {dimensionamento2.qtdplacas}").pack(anchor="w", padx=10, pady=5)
            if dimensionamento2.autotrafo:
                ttk.Label(pack3, text=f"Necessário autotrafo: {dimensionamento2.autotrafo}").pack(anchor="w",padx=10, pady=5)
            num_baterias = len(dimensionamento2.baterias)
            if num_baterias == 1:
                bateria = list(dimensionamento2.baterias.keys())[0]
                ttk.Label(pack3, text=f"Modelo da Bateria: {bateria}").pack(anchor="w", padx=10, pady=5)
                ttk.Label(pack3, text=f"Quantidade de baterias: {dimensionamento2.baterias[bateria]}").pack(anchor="w", padx=10, pady=5)
            else:
                ttk.Label(pack3, text=f"Baterias Recomendadas:").pack(anchor="w", padx=10, pady=5)
                for i, bateria in enumerate(dimensionamento2.baterias):
                    ttk.Label(pack3, text=f"Opção {i + 1}:").pack(anchor="w", padx=10, pady=5)
                    ttk.Label(pack3, text=f"  Modelo da bateria: {bateria}").pack(anchor="w", padx=10, pady=5)
                    ttk.Label(pack3, text=f"  Quantidade de baterias: {dimensionamento2.baterias[bateria]}").pack(
                        anchor="w", padx=10, pady=5)

            #if dimensionamento2.tabela_geracao is not None:
                #media_geracao = round(sum(dimensionamento2.tabela_geracao) / len(dimensionamento2.tabela_geracao), 1)
                #ttk.Label(pack3, text=f"Geração mensal estimada: {media_geracao}kWh").pack(anchor="w", padx=10, pady=5)
            ttk.Button(pack3, text="Exportar", command=lambda: exportar(self, tipo_sistema, tipo_rede, eficiencia, autonomia, potencia, consumo, painel, dimensionamento2, tabela, endereco, coordenadas_arredondadas, orientacao, inclinacao, temperatura, fator_seguranca, tabela_consumo, hsp, modo_calculo, self.organizacao), style="Accent.TButton").pack(
                anchor="center", side="bottom", padx=20, pady=20)

        return "ok"

if __name__ == "__main__":
    app = DimensionamentoApp()
    app.mainloop()
