from eficiencias import eficiencias, estado_para_regiao
import os
from dotenv import load_dotenv
import requests

status = "ok"

class Dimensionamento:
    def __init__(self, inversor, qtdinversor, qtdplacas, baterias, autotrafo, tabela_geracao):
        self.inversor = inversor
        self.qtdinversor = qtdinversor
        self.qtdplacas = qtdplacas
        self.baterias = baterias
        self.autotrafo = autotrafo
        self.tabela_geracao = tabela_geracao

class Inversor:
    def __init__(self, nome, potencia, tipo, tipo_rede, marca, max_placas, baterias):
        self.nome = nome
        self.potencia = potencia
        self.tipo = tipo
        self.marca = marca
        self.tipo_rede = tipo_rede
        self.max_placas = max_placas
        self.baterias = baterias

    @classmethod
    def renac_off_5k(cls):
        nome = "Renac Offgrid 5kW"
        potencia = 5000
        tipo = "Offgrid"
        marca = "Renac"
        tipo_rede = "Bifásico"
        max_placas = {"550W": 8, "555W": 8, "570W": 8, "580W": 8, "585W": 8, "610W": 8}
        baterias = {"Lítio LV Turbo L1 - 5300Wh": 2, "Chumbo Moura - 2640Wh": 4}
        return cls(nome, potencia, tipo, tipo_rede, marca, max_placas, baterias)

    @classmethod
    def renac_6k(cls):
        nome = "Renac Híbrido 6kW"
        potencia = 6000
        tipo = "Híbrido"
        marca = "Renac"
        tipo_rede = "Bifásico"
        max_placas = {"550W": 16, "555W": 16, "570W": 15, "580W": 15, "585W": 0, "610W": 0}
        baterias = {"Lítio Turbo H1 - 3740Wh": 8}
        return cls(nome, potencia, tipo, tipo_rede, marca, max_placas, baterias)

    @classmethod
    def aux_6k(cls):
        nome = "Auxsol Híbrido 6kW"
        potencia = 6000
        tipo = "Híbrido"
        marca = "Auxsol"
        tipo_rede = "Bifásico"
        max_placas = {"550W": 16, "555W": 16, "570W": 15, "580W": 15, "585W": 15, "610W": 14}
        baterias = {"Lítio ABL-T-H1 - 5300Wh": 4}
        return cls(nome, potencia, tipo, tipo_rede, marca, max_placas, baterias)

    #@classmethod
    #def renac_10k(cls):
    #    nome = "Renac Híbrido 10kW"
    #    potencia = 10000
    #    tipo = "Híbrido"
    #    marca = "Renac"
    #    tipo_rede = "Trifásico"
    #    max_placas = {"550W": 25, "555W": 25, "580W": 25} # Atualizar
    #    baterias = {"Lítio Turbo H1 - 3740Wh": 25, "Lítio Turbo H1 - 9500Wh": 6}
    #    return cls(nome, potencia, tipo, tipo_rede, marca, max_placas, baterias)


modelos_baterias = {
    "Lítio Turbo H1 - 3740Wh": 3740,
    "Lítio Turbo H1 - 9500Wh": 9500,
    "Lítio ABL-T-H1 - 5300Wh": 5300,
    #"Lítio ABL-H - 6650Wh": 6650,
    "Lítio LV Turbo L1 - 5300Wh": 5300,
    "Chumbo Moura - 2640Wh": 2640
}

# Custos fictícios e arredondados: servem apenas como "pesos" para a escolha da
# configuração de menor custo (ver TCC, Seção 3.4.2). Não são preços de mercado.
custo_item = {
    "Lítio Turbo H1 - 3740Wh": 6100,
    "Lítio Turbo H1 - 9500Wh": 9800,
    "Lítio ABL-T-H1 - 5300Wh": 8400,
    #"Lítio ABL-H - 6650Wh": 15000, # Ficticio
    "Lítio LV Turbo L1 - 5300Wh": 8900,
    "Chumbo Moura - 2640Wh": 2600,
    "Renac Offgrid 5kW": 2400,
    "Renac Híbrido 6kW": 4800,
    "Auxsol Híbrido 6kW": 4400,
    "Renac Híbrido 10kW": 8400
    #"Autotrafo": 2000 # Ficticio
}

modelos_paineis = {
    "550W": 550,
    "555W": 555,
    "570W": 570,
    "580W": 580,
    "585W": 585,
    "610W": 610
}

def round033(num):
    parte_decimal = num - int(num)
    if parte_decimal > 0.33333:
        return int(num) + 1
    else:
        return int(num)

def obter_eficiencia(orientacao, inclinacao, estado):

    # Usando o mapeamento de estado para região para determinar a região
    regiao = estado_para_regiao.get(estado, "Região não encontrada")

    # Verificar se a região foi encontrada
    if regiao == "Região não encontrada":
        return "Estado não encontrado ou região não mapeada"

    # Encontrar a eficiência com base na orientação e inclinação
    eficiencia = eficiencias[regiao].get((orientacao, inclinacao), "Eficiência não encontrada")

    return eficiencia


def calcular_eficiencia(fator_seguranca, estado, orientacao, inclinacao, temperatura):
    temperatura_local = 50 #°C

    #print(estado)

    eficiencia_inclinacao_orientacao = obter_eficiencia(orientacao, inclinacao, estado) # orientacao e inclinacao
    eficiencia_fator_seguranca = (1-fator_seguranca) # fator de segurança
    eficiencia_temperatura = 1 - ((temperatura_local-25)*abs(float(temperatura))/100) # temperatura

    eficiencia = float(eficiencia_inclinacao_orientacao) * eficiencia_fator_seguranca * eficiencia_temperatura

    eficiencia = eficiencia * (1-0.015) * (1-0.05) * (1-0.01) #???

    #print(eficiencia, eficiencia_inclinacao_orientacao, eficiencia_fator_seguranca, eficiencia_temperatura)

    return eficiencia


def obter_categoria(tabela):
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

    nova_tabela = []

    for item in tabela:
        equipamento, quantidade, potencia, autonomia, consumo = item

        # Prepara a URL para a consulta com filtragem por 'equipamento'
        query_url = f"{url}?equipamento=eq.{equipamento}"

        # Realiza a consulta HTTP GET ao Supabase
        response = requests.get(query_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data:
                categoria = data[0].get('categoria', 'outros')
            else:
                categoria = 'outros'
        else:
            categoria = 'outros'

        # Adiciona o item com a categoria na nova tabela
        nova_tabela.append((equipamento, quantidade, potencia, autonomia, consumo, categoria))

    return nova_tabela


def aplicar_fator_demanda(tabela):
    # A tabela CO-BEI fornecida, associando cada tipo de equipamento ao fator de demanda por número de aparelhos
    fatores_demanda = {
        "IL": [0.88, 0.75, 0.66, 0.59, 0.52, 0.45, 0.40, 0.35, 0.31, 0.27, 0.24],  # Potência em kW
        "TUG": [0.88, 0.75, 0.66, 0.59, 0.52, 0.45, 0.40, 0.35, 0.31, 0.27, 0.24],  # Potência em kW
        "TUE": [1.00],
        "CH": [0.68, 0.56, 0.48, 0.43],
        "TE": [0.72, 0.62, 0.57, 0.54],
        "LL": [0.71, 0.64, 0.60, 0.57],
        "AAP": [0.60, 0.48, 0.40, 0.37],
        "AAA": [1.00, 1.00, 1.00, 0.80],
        "MO": [0.56, 0.47, 0.39, 0.35],
        "MSR": [1.00, 1.00, 1.00, 1.00],
        "AC": [1.00, 1.00, 1.00, 1.00],
        "HM": [0.60, 0.48, 0.40, 0.37]
    }

    nova_tabela = []

    for item in tabela:
        equipamento, quantidade, potencia, autonomia, consumo, categoria = item
        quantidade = int(quantidade)
        potencia = float(potencia)
        autonomia = float(autonomia)
        consumo = float(consumo)

        # Ajusta a potência e consumo usando o fator de demanda
        if categoria in fatores_demanda:
            if categoria == "IL" or categoria == "TUG":
                # Encontrar o índice do fator de demanda baseado na potência
                if potencia / 1000 <= 10:
                    fd_index = int(potencia / 1000)  # Índice baseado na potência em kW
                else:
                    fd_index = 10  # Índice para potências acima de 10 kW
                fator_demanda = fatores_demanda[categoria][fd_index] / 100  # Fator de demanda em %
            else:
                fd_index = min(quantidade, 4) - 1  # Índice no fator de demanda (0 a 3)
                fator_demanda = fatores_demanda[categoria][fd_index]
        else:
            fator_demanda = 1.0  # Sem ajuste

        potencia_ajustada = potencia * fator_demanda
        consumo_ajustado = consumo * fator_demanda

        nova_tabela.append((equipamento, quantidade, potencia_ajustada, autonomia, consumo_ajustado, categoria))

    return nova_tabela


def metodo_cobei(tabela):
    print("Tabela Original:")
    print(tabela)

    tabela = obter_categoria(tabela)

    print("Tabela com Categoria:")
    print(tabela)

    tabela = aplicar_fator_demanda(tabela)

    print("Tabela com Fator de Demanda Aplicado:")
    print(tabela)


def resultados(tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, hsp, tabela_consumo, modo_calculo, tabela_cargas):
    global status
    status = "ok"
    custos_e_dimensionamentos = {}

    #metodo_cobei(tabela_cargas) # SOMENTE PARA TESTE // A PRINCÍPIO NÃO SERÁ IMPLEMENTADO

    if tipo_sistema == "Offgrid":
        inversor_renacoff5k = Inversor.renac_off_5k()
        custo, dimensionamento_renacoff5k = resultados_por_inversor(hsp, tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, inversor_renacoff5k, tabela_consumo, modo_calculo)
        if dimensionamento_renacoff5k is not None:
            custos_e_dimensionamentos[custo] = dimensionamento_renacoff5k
        else:
            return None, None, status

    inversor_aux6k = Inversor.aux_6k()
    custo, dimensionamento_aux6k = resultados_por_inversor(hsp, tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, inversor_aux6k, tabela_consumo, modo_calculo)
    if dimensionamento_aux6k is not None:
        custos_e_dimensionamentos[custo] = dimensionamento_aux6k

    inversor_renac6k = Inversor.renac_6k()
    custo, dimensionamento_renac6k = resultados_por_inversor(hsp, tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, inversor_renac6k, tabela_consumo, modo_calculo)
    if dimensionamento_renac6k is not None:
        custos_e_dimensionamentos[custo] = dimensionamento_renac6k

    #if tipo_rede == "Trifásico 380V (Fase + Fase + Fase + Neutro + Terra)" or tipo_rede == "Trifásico 220V (Fase + Fase + Fase + Neutro + Terra)":
    #    inversor_renac10k = Inversor.renac_10k()
    #    custo, dimensionamento_renac10k = resultados_por_inversor(hsp, tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, inversor_renac10k, tabela_consumo, modo_calculo)
    #    custos_e_dimensionamentos[custo] = dimensionamento_renac10k

    # Ordenar os inversores pelo custo
    custos_ordenados = sorted(custos_e_dimensionamentos.items())

    # Selecionar os dimensionamentos
    dimensionamentos_selecionados = []
    offgrid_incluido = False
    for custo, dimensionamento in custos_ordenados:
        if dimensionamento.inversor == 'Renac Offgrid 5kW':
            dimensionamentos_selecionados.append(dimensionamento)
            offgrid_incluido = True
            break

    # Adicionar o inversor mais barato geral se não incluiu offgrid ainda ou precisa de outro inversor
    if len(dimensionamentos_selecionados) < 2:
        for custo, dimensionamento in custos_ordenados:
            if dimensionamento not in dimensionamentos_selecionados:
                dimensionamentos_selecionados.append(dimensionamento)
            if len(dimensionamentos_selecionados) == 2:
                break

    if len(dimensionamentos_selecionados) == 2:
        return dimensionamentos_selecionados[0], dimensionamentos_selecionados[1], status
    elif len(dimensionamentos_selecionados) == 1:
        return dimensionamentos_selecionados[0], None, status
    else:
        return None, None, status


def resultados_por_inversor(hsp, tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, inversor, tabela_consumo, modo_calculo):
    global status

    # Inversor
    #print(f"\n============================================\nInversor: {inversor.nome}\n")

    dias_no_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    #if inversor.nome == "Renac Híbrido 10kW" and tipo_rede == "Trifásico 220V (Fase + Fase + Fase + Neutro + Terra)":
    #    custo_autotrafo = custo_item["Autotrafo"]
    #else:
    custo_autotrafo = 0

    hsp_minimo = min(hsp)/1000

    # Quantidade de painéis
    potencia_painel = modelos_paineis[modelo_painel]
    qtd_paineis_offgrid = consumo / (potencia_painel * hsp_minimo * eficiencia)
    #print(consumo, potencia_painel, hsp_minimo, eficiencia)
    qtd_paineis_offgrid = round033(qtd_paineis_offgrid)

    # Determina se o inversor suporta o equipamento de maior potência inserido
    if inversor.nome == "Renac Offgrid 5kW":
        potencia_max_inversor = inversor.potencia * 6
        max_placas_inversor = inversor.max_placas[modelo_painel] * 6
    else:
        potencia_max_inversor = inversor.potencia
        max_placas_inversor = inversor.max_placas[modelo_painel]

    if potencia_max > potencia_max_inversor:
        status = "A potência de um dos equipamentos está acima da potência nominal dos inversores. Por favor, considere reduzir a potência do equipamento. (" + str(potencia_max) + "W)"
        return None, None

    qtd_paineis_max = consumo_max / (potencia_painel * hsp_minimo * eficiencia)
    if qtd_paineis_max > max_placas_inversor:
        status = "O consumo de um dos equipamentos está acima do suportado pelos inversores. Por favor, considere reduzir a potência ou a autonomia do equipamento. (" + str(consumo_max) + "Wh)"
        return None, None

    if tipo_sistema == "Offgrid":
        qtd_paineis = qtd_paineis_offgrid
        tabela_geracao = None

        if inversor.nome == "Renac Offgrid 5kW":
            minimo_paineis = 4
            if qtd_paineis < minimo_paineis:
                qtd_paineis = minimo_paineis
        else:
            minimo_paineis = 5
            if qtd_paineis < minimo_paineis:
                qtd_paineis = minimo_paineis

    else:
        hsp_medio = (sum(hsp)/len(hsp))/1000
        consumo_medio = (sum(tabela_consumo)/len(tabela_consumo))*1000
        diasnomes_medio = (sum(dias_no_mes)/len(dias_no_mes))

        minimo_paineis = 5

        if qtd_paineis_offgrid < minimo_paineis:
            qtd_paineis_offgrid = minimo_paineis

        if consumo_medio == 0:
            tabela_geracao = None
            qtd_paineis = qtd_paineis_offgrid
        else:
            # Quantidade de painéis ongrid
            qtd_paineis_ongrid = consumo_medio / (potencia_painel * hsp_medio * eficiencia * diasnomes_medio)
            qtd_paineis_ongrid = int(qtd_paineis_ongrid) + 1


            if modo_calculo == "Somar consumo + cargas":
                qtd_paineis = qtd_paineis_ongrid + qtd_paineis_offgrid
            else:
                qtd_paineis = max(qtd_paineis_ongrid, qtd_paineis_offgrid)

            if qtd_paineis < minimo_paineis:
                qtd_paineis = minimo_paineis

            # Gráfico de geração
            tabela_geracao = []

            for mes in range(12):
                geracao = (hsp[mes]/1000 * eficiencia * potencia_painel * dias_no_mes[mes] * qtd_paineis)/1000
                tabela_geracao.append(geracao)

    # Quantidade de baterias e inversores necessários
    qtd_baterias = 0
    inversores_por_baterias = {}
    baterias_por_modelo = {}
    for modelo in inversor.baterias:
        wh_bateria = modelos_baterias[modelo]
        qtd_baterias = consumo / wh_bateria
        qtd_baterias = round033(qtd_baterias)
        if qtd_baterias == 0:
            qtd_baterias = 1
        if modelo == "Chumbo Moura - 2640Wh":
            qtd_baterias = ((qtd_baterias + 3) // 4) * 4
        qtd_inversores_bateria = (qtd_baterias + inversor.baterias[modelo] - 1) // inversor.baterias[modelo]
        inversores_por_baterias[modelo] = qtd_inversores_bateria
        baterias_por_modelo[modelo] = qtd_baterias

    # Quantidade de inversores baseada na capacidade máxima de módulos
    max_paineis = inversor.max_placas[modelo_painel]
    qtd_inversores_modulos = (qtd_paineis + max_paineis - 1) // max_paineis

    # Quantidade de inversores baseada na potência dos equipamentos
    potencia_inversor = inversor.potencia
    qtd_inversores_potencia = (potencia_inversor + potencia - 1) // potencia_inversor
    qtd_inversores_potencia = int(qtd_inversores_potencia)
    # Quantidade final de inversores
    min_inversores = min(inversores_por_baterias.values())
    qtd_inversores = max(qtd_inversores_modulos, min_inversores)
    qtd_inversores_final = max(qtd_inversores_modulos, min_inversores, qtd_inversores_potencia)
    qtd_inversores_a_mais = qtd_inversores_final - qtd_inversores
    print(qtd_inversores, qtd_inversores_final, qtd_inversores_a_mais)
    # Reverifica as baterias
    if qtd_inversores_a_mais != 0:
        for modelo in inversor.baterias:
            if modelo == "Chumbo Moura - 2640Wh":
                baterias_por_modelo[modelo] += 4
            if baterias_por_modelo[modelo] < qtd_inversores_final:
                baterias_por_modelo[modelo] = qtd_inversores_final

    # Reverifica a quantidade de módulos
    paineis_por_inversor = qtd_paineis / qtd_inversores_final
    if paineis_por_inversor < minimo_paineis:
        qtd_paineis = minimo_paineis * qtd_inversores_final

        if tabela_geracao is not None:

            tabela_geracao = []

            for mes in range(12):
                geracao = (hsp[mes] / 1000 * eficiencia * potencia_painel * dias_no_mes[mes] * qtd_paineis) / 1000
                tabela_geracao.append(geracao)

    #print(f"Potência total: {potencia}, Potência máxima do inversor: {inversor.potencia}")
    #print("Quantidade de Inversores (por baterias):", min_inversores)
    #print("Quantidade de Inversores (por módulos):", qtd_inversores_modulos)
    #print("Quantidade de Inversores (por potência):", qtd_inversores_potencia)
    #print("\nResultados:")
    #print(f"Quantidade Final de inversores: {qtd_inversores_final}")
    #print("Quantidade de Painéis:", qtd_paineis)
    modelos_escolhidos = [modelo for modelo, qtd in inversores_por_baterias.items() if qtd == min_inversores]

    custo_baterias = {}
    for modelo in modelos_escolhidos:
        custo_baterias[modelo] = custo_item[modelo] * baterias_por_modelo[modelo]

    # Atualiza o dicionário baterias_por_modelo para conter apenas os modelos escolhidos
    baterias_por_modelo = {modelo: baterias_por_modelo[modelo] for modelo in modelos_escolhidos}

    custo_inversor = custo_item[inversor.nome]*qtd_inversores_final
    custo_baterias = min(custo_baterias.values())

    custo_total = custo_inversor + custo_baterias + custo_autotrafo
    #print(custo_total)

    if custo_autotrafo == 0:
        dimensionamento = Dimensionamento(inversor.nome, qtd_inversores_final, qtd_paineis, baterias_por_modelo, None, tabela_geracao)
    else:
        dimensionamento = Dimensionamento(inversor.nome, qtd_inversores_final, qtd_paineis, baterias_por_modelo, "Autotrafo", tabela_geracao)

    return custo_total, dimensionamento
