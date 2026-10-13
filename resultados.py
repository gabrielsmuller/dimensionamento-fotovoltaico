from eficiencias import eficiencias, estado_para_regiao
import math
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

# Profundidade de descarga (DoD) admitida e eficiência de carga/descarga de cada
# modelo. A energia utilizável de uma bateria é capacidade × DoD × eficiência
# (Khatib; Ibrahim; Mohamed, 2016).
#   - Renac Turbo L1 e H1: 90% de DoD informado no datasheet do fabricante.
#   - Auxsol ABL-T (5,3 kWh): ~85% (4,5 kWh utilizáveis no datasheet do ABL-T05H-H02).
#   - Chumbo-ácido Moura: 50%, valor usual de projeto para preservar a vida útil.
#   - Eficiência: 95% para lítio (LiFePO4) e 85% para chumbo-ácido (valores típicos).
parametros_baterias = {
    "Lítio Turbo H1 - 3740Wh": {"dod": 0.90, "eficiencia": 0.95},
    "Lítio Turbo H1 - 9500Wh": {"dod": 0.90, "eficiencia": 0.95},
    "Lítio ABL-T-H1 - 5300Wh": {"dod": 0.85, "eficiencia": 0.95},
    "Lítio LV Turbo L1 - 5300Wh": {"dod": 0.90, "eficiencia": 0.95},
    "Chumbo Moura - 2640Wh": {"dod": 0.50, "eficiencia": 0.85},
}


def energia_util_bateria(modelo):
    """Energia que uma bateria do modelo pode entregar por ciclo, em Wh."""
    p = parametros_baterias[modelo]
    return modelos_baterias[modelo] * p["dod"] * p["eficiencia"]

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

def teto(num):
    """Arredonda para o inteiro imediatamente superior (função teto).

    A tolerância evita que erros de ponto flutuante (ex.: 4,0000000001)
    acrescentem um equipamento a mais."""
    return math.ceil(num - 1e-9)

def obter_eficiencia(orientacao, inclinacao, estado):

    # Usando o mapeamento de estado para região para determinar a região
    regiao = estado_para_regiao.get(estado, "Região não encontrada")

    # Verificar se a região foi encontrada
    if regiao == "Região não encontrada":
        return "Estado não encontrado ou região não mapeada"

    # Encontrar a eficiência com base na orientação e inclinação
    eficiencia = eficiencias[regiao].get((orientacao, inclinacao), "Eficiência não encontrada")

    return eficiencia


# Perdas estáticas agrupadas no fator global de segurança (TCC, Seção 3.5.3.2),
# com base nas recomendações do PVWatts (NREL)
PERDAS_ESTATICAS = {
    "ohmicas": 0.015,
    "inversor_e_mismatch": 0.05,
    "sujeira_e_opticas": 0.01,
}


# True: transpõe a irradiação para o plano dos módulos pelo modelo de Perez (pvlib).
# False: usa a tabela de fatores por região, orientação e inclinação (eficiencias.py),
# método da versão anterior, mantido para comparação.
USAR_PEREZ = True


def calcular_eficiencia(estado, orientacao, inclinacao, temperatura, incluir_orientacao=True):
    temperatura_local = 50 #°C

    eficiencia_temperatura = 1 - ((temperatura_local-25)*abs(float(temperatura))/100) # temperatura
    eficiencia = eficiencia_temperatura

    if incluir_orientacao:
        eficiencia *= float(obter_eficiencia(orientacao, inclinacao, estado)) # orientacao e inclinacao

    for perda in PERDAS_ESTATICAS.values():
        eficiencia *= (1 - perda)

    return eficiencia


def preparar_irradiacao(coordenadas, ghi_mensal, estado, orientacao, inclinacao, temperatura):
    """Irradiação mensal usada no dimensionamento e eficiência global do sistema.

    Com USAR_PEREZ, a irradiação já está no plano dos módulos e a eficiência não
    inclui o fator de orientação/inclinação. Retorna (hsp_mensal_Wh, eficiencia)."""
    if USAR_PEREZ:
        from transposicao import irradiacao_plano_inclinado
        latitude, longitude = coordenadas
        hsp = irradiacao_plano_inclinado(latitude, longitude, ghi_mensal, inclinacao, orientacao)
        return hsp, calcular_eficiencia(estado, orientacao, inclinacao, temperatura, incluir_orientacao=False)
    return list(ghi_mensal), calcular_eficiencia(estado, orientacao, inclinacao, temperatura)


# Fator de demanda pelo método COBEI (TCC, Seção 2.8). Desligado por padrão:
# altere para True para testar o dimensionamento com o fator aplicado.
APLICAR_COBEI = False
# O fator de demanda representa a não simultaneidade das cargas, por isso reduz
# a POTÊNCIA demandada (que dimensiona os inversores). O consumo diário já leva
# em conta as horas de uso de cada equipamento; reduzi-lo também descontaria a
# simultaneidade duas vezes. Mantido como opção apenas para testes.
COBEI_AJUSTA_ENERGIA = False

# Fatores de demanda por categoria (método COBEI). IL e TUG: um fator por faixa
# de 1 kW de potência instalada (0-1 kW, 1-2 kW, ..., acima de 10 kW). Demais
# categorias: um fator por número de aparelhos (1, 2, 3, 4 ou mais).
FATORES_DEMANDA = {
    "IL": [0.88, 0.75, 0.66, 0.59, 0.52, 0.45, 0.40, 0.35, 0.31, 0.27, 0.24],
    "TUG": [0.88, 0.75, 0.66, 0.59, 0.52, 0.45, 0.40, 0.35, 0.31, 0.27, 0.24],
    "TUE": [1.00],
    "CH": [0.68, 0.56, 0.48, 0.43],
    "TE": [0.72, 0.62, 0.57, 0.54],
    "LL": [0.71, 0.64, 0.60, 0.57],
    "AAP": [0.60, 0.48, 0.40, 0.37],
    "AAA": [1.00, 1.00, 1.00, 0.80],
    "MO": [0.56, 0.47, 0.39, 0.35],
    "MSR": [1.00, 1.00, 1.00, 1.00],
    "AC": [1.00, 1.00, 1.00, 1.00],
    "HM": [0.60, 0.48, 0.40, 0.37],
}


def obter_categoria(tabela):
    """Acrescenta a categoria COBEI de cada equipamento (consulta ao Supabase).

    Equipamentos não encontrados, ou sem acesso ao banco, recebem 'outros'
    (fator de demanda 1, ou seja, sem redução)."""
    load_dotenv()
    api_key = os.getenv("SUPABASE_API_KEY")
    auth_key = os.getenv("SUPABASE_AUTH_KEY")
    url = "https://ktdmbdjzmisdtjhdlvnl.supabase.co/rest/v1/Catalogo de Cargas"
    headers = {
        "apikey": api_key or "",
        "Authorization": auth_key or "",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    nova_tabela = []

    for item in tabela:
        equipamento, quantidade, potencia, autonomia, consumo = item[:5]
        categoria = 'outros'
        if api_key:
            try:
                response = requests.get(f"{url}?equipamento=eq.{equipamento}", headers=headers, timeout=10)
                if response.status_code == 200 and response.json():
                    categoria = response.json()[0].get('categoria') or 'outros'
            except requests.RequestException:
                pass
        nova_tabela.append((equipamento, quantidade, potencia, autonomia, consumo, categoria))

    return nova_tabela


def fator_demanda_por_categoria(tabela):
    """Fator de demanda de cada categoria presente na tabela.

    IL/TUG: escolhido pela potência instalada total da categoria (faixas de 1 kW).
    Demais: escolhido pelo número total de aparelhos da categoria."""
    potencia_kw = {}
    quantidade = {}
    for equipamento, qtd, potencia, autonomia, consumo, categoria in tabela:
        potencia_kw[categoria] = potencia_kw.get(categoria, 0) + int(qtd) * float(potencia) / 1000
        quantidade[categoria] = quantidade.get(categoria, 0) + int(qtd)

    fatores = {}
    for categoria in potencia_kw:
        lista = FATORES_DEMANDA.get(categoria)
        if lista is None:
            fatores[categoria] = 1.0
        elif categoria in ("IL", "TUG"):
            indice = max(0, teto(potencia_kw[categoria]) - 1)
            fatores[categoria] = lista[min(indice, len(lista) - 1)]
        else:
            fatores[categoria] = lista[min(quantidade[categoria], len(lista)) - 1]
    return fatores


def aplicar_fator_demanda(tabela):
    fatores = fator_demanda_por_categoria(tabela)
    nova_tabela = []
    for equipamento, quantidade, potencia, autonomia, consumo, categoria in tabela:
        fd = fatores[categoria]
        consumo_ajustado = float(consumo) * fd if COBEI_AJUSTA_ENERGIA else float(consumo)
        nova_tabela.append((equipamento, int(quantidade), float(potencia) * fd, float(autonomia),
                            consumo_ajustado, categoria))
    return nova_tabela


def metodo_cobei(tabela):
    """Retorna a tabela de cargas com o fator de demanda COBEI aplicado."""
    return aplicar_fator_demanda(obter_categoria(tabela))


def resultados(tipo_sistema, tipo_rede, eficiencia, autonomia, consumo_max, potencia_max, potencia, consumo, modelo_painel, hsp, tabela_consumo, modo_calculo, tabela_cargas):
    global status
    status = "ok"
    custos_e_dimensionamentos = {}

    if APLICAR_COBEI and tabela_cargas:
        tabela_fd = metodo_cobei(tabela_cargas)
        # potência demandada simultaneamente (dimensiona os inversores)
        potencia = sum(int(i[1]) * float(i[2]) for i in tabela_fd)
        if COBEI_AJUSTA_ENERGIA:
            consumo = sum(float(i[4]) for i in tabela_fd)

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
    qtd_paineis_offgrid = teto(qtd_paineis_offgrid)

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
            qtd_paineis_ongrid = teto(qtd_paineis_ongrid)


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
        qtd_baterias = max(1, teto(consumo / energia_util_bateria(modelo)))
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
