# -*- coding: utf-8 -*-
"""Casos de teste do algoritmo de dimensionamento (sem interface gráfica).

Reproduz o caminho do botão "Calcular" do main.py para um conjunto fixo de
cenários e imprime o resultado de cada um. Serve para conferir o efeito de cada
alteração no código e como base para as simulações de validação no PVsyst.

Uso:  python testes/casos.py            (resumo legível)
      python testes/casos.py --json     (saída em JSON, para comparar versões)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obterhsp import obter_hsp  # noqa: E402
from resultados import preparar_irradiacao, resultados  # noqa: E402

LOCAIS = {
    "Toledo-PR": ((-24.7246, -53.7412), "Paraná", "25°"),
    "Petrolina-PE": ((-9.3891, -40.5030), "Pernambuco", "10°"),
    "Manaus-AM": ((-3.1190, -60.0217), "Amazonas", "5°"),
}

# (equipamento, quantidade, potência [W], autonomia [h/dia], consumo [Wh/dia])
def _item(nome, qtd, pot, horas):
    return (nome, qtd, pot, horas, qtd * pot * horas)

CARGA_PEQUENA = [
    _item("Lâmpada LED", 6, 10, 5),
    _item("Geladeira", 1, 120, 10),
    _item("Televisão", 1, 100, 4),
    _item("Notebook", 1, 60, 4),
]
CARGA_MEDIA = CARGA_PEQUENA + [
    _item("Freezer", 1, 150, 12),
    _item("Bomba d'água", 1, 750, 1),
    _item("Micro-ondas", 1, 1200, 0.3),
    _item("Máquina de lavar", 1, 500, 1),
    _item("Ventilador", 2, 100, 6),
]

CASOS = [
    # nome, sistema, local, carga, consumo mensal [kWh] (híbrido)
    ("OFF-1 Toledo carga pequena", "Offgrid", "Toledo-PR", CARGA_PEQUENA, []),
    ("OFF-2 Toledo carga média", "Offgrid", "Toledo-PR", CARGA_MEDIA, []),
    ("OFF-3 Petrolina carga pequena", "Offgrid", "Petrolina-PE", CARGA_PEQUENA, []),
    ("OFF-4 Petrolina carga média", "Offgrid", "Petrolina-PE", CARGA_MEDIA, []),
    ("OFF-5 Manaus carga pequena", "Offgrid", "Manaus-AM", CARGA_PEQUENA, []),
    ("OFF-6 Manaus carga média", "Offgrid", "Manaus-AM", CARGA_MEDIA, []),
    ("HIB-1 Toledo 500 kWh/mês", "Híbrido", "Toledo-PR", CARGA_PEQUENA, [500] * 12),
]

PAINEL = "550W"
ORIENTACAO = "Norte"
COEF_TEMPERATURA = "-0.3"   # %/°C, valor padrão da interface
REDE = "Monofásico 220V (Fase + Neutro + Terra)"
MODO_HIBRIDO = "Somar consumo + cargas"


def totais_da_tabela(tabela):
    """Mesmas grandezas que o main.py calcula a partir da tabela de cargas."""
    autonomia_max = max(float(i[3]) for i in tabela)
    potencia_total = sum(float(i[2]) * float(i[1]) for i in tabela)
    consumo_total = round(sum(float(i[4]) for i in tabela), 1)
    # maior equipamento individual (potência e consumo por unidade)
    potencia_max = max(float(i[2]) for i in tabela)
    consumo_max = max(float(i[4]) / float(i[1]) for i in tabela)
    return autonomia_max, consumo_max, potencia_max, potencia_total, consumo_total


def rodar_caso(nome, sistema, local, tabela, consumo_mensal):
    coords, estado, inclinacao = LOCAIS[local]
    hsp, eficiencia = preparar_irradiacao(coords, obter_hsp(coords), estado, ORIENTACAO, inclinacao, COEF_TEMPERATURA)
    aut, cmax, pmax, ptot, ctot = totais_da_tabela(tabela)
    d1, d2, status = resultados(sistema, REDE, eficiencia, aut, cmax, pmax, ptot, ctot, PAINEL,
                                hsp, consumo_mensal, MODO_HIBRIDO, tabela)
    opcoes = []
    for d in (d1, d2):
        if d is not None:
            opcoes.append({"inversor": d.inversor, "qtd_inversores": d.qtdinversor,
                           "qtd_modulos": d.qtdplacas, "baterias": d.baterias})
    return {"caso": nome, "local": local, "inclinacao": inclinacao,
            "consumo_Wh_dia": ctot, "hsp_min": round(min(hsp) / 1000, 3),
            "eficiencia": round(float(eficiencia), 4), "status": status, "opcoes": opcoes}


# Categorias COBEI dos equipamentos de teste (no aplicativo elas vêm do Supabase)
CATEGORIAS_TESTE = {
    "Lâmpada LED": "IL", "Televisão": "TUG", "Notebook": "TUG", "Ventilador": "TUG",
    "Geladeira": "TUE", "Freezer": "TUE", "Bomba d'água": "TUE",
    "Micro-ondas": "MO", "Máquina de lavar": "TUE",
}


def _categorias_de_teste(tabela):
    return [tuple(i[:5]) + (CATEGORIAS_TESTE.get(i[0], "outros"),) for i in tabela]


if __name__ == "__main__":
    import contextlib
    import io
    if "--tabela" in sys.argv:  # usa a tabela de orientação/inclinação em vez de Perez
        import resultados as _r
        _r.USAR_PEREZ = False
    if "--cobei" in sys.argv:  # roda com o fator de demanda COBEI ligado
        import resultados as _r
        _r.APLICAR_COBEI = True
        _r.obter_categoria = _categorias_de_teste
    saida = []
    for caso in CASOS:
        with contextlib.redirect_stdout(io.StringIO()):  # silencia os print() internos
            saida.append(rodar_caso(*caso))
    if "--json" in sys.argv:
        print(json.dumps(saida, ensure_ascii=False, indent=1))
    else:
        for r in saida:
            print(f"\n{r['caso']}  ({r['consumo_Wh_dia']:.0f} Wh/dia, HSP mín {r['hsp_min']}, "
                  f"eficiência {r['eficiencia']})")
            if r["status"] != "ok":
                print("   STATUS:", r["status"])
            for i, o in enumerate(r["opcoes"], 1):
                print(f"   opção {i}: {o['qtd_inversores']}× {o['inversor']} | {o['qtd_modulos']} módulos | {o['baterias']}")
