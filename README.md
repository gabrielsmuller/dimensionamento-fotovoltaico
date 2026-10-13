# PV Optimizer

Algoritmo para o dimensionamento automático de sistemas fotovoltaicos **autônomos (*off-grid*)** e **híbridos**, com interface gráfica, voltado à elaboração rápida de propostas técnicas com equipamentos eletricamente compatíveis.

## Visão geral

Dimensionar sistemas fotovoltaicos com baterias exige obter os dados de irradiação do local, estimar o consumo, dimensionar o gerador e o banco de baterias e verificar a compatibilidade entre módulos, inversores e baterias. Este projeto automatiza essas etapas para:

* **Reduzir o tempo** de elaboração das propostas;
* **Simplificar o processo** para profissionais com diferentes níveis de conhecimento técnico;
* **Garantir a compatibilidade** elétrica entre os equipamentos sugeridos;
* **Reduzir custos**, indicando a combinação de equipamentos de menor custo.

## Funcionalidades

* **Irradiação automática:** obtém a irradiação global horizontal do Atlas Brasileiro de Energia Solar (INPE) a partir do endereço da instalação.
* **Transposição para o plano dos módulos:** modelo de Perez (biblioteca pvlib), conforme a inclinação e a orientação informadas.
* **Perdas do sistema:** temperatura, perdas ôhmicas, inversor, *mismatch*, sujeira, degradação inicial (LID) e ângulo de incidência (IAM).
* **Dimensionamento:** quantidade de módulos, baterias (com profundidade de descarga e eficiência) e inversores.
* **Compatibilidade:** limites de potência, de módulos por inversor e de baterias por banco de cada equipamento cadastrado.
* **Fator de demanda (opcional):** método COBEI aplicado à potência das cargas.
* **Topologias:** sistemas *off-grid* e híbridos.

## Como funciona

1. **Entrada:** localização, tabela de cargas, consumo mensal (sistemas híbridos) e dados da instalação.
2. **Processamento:** cálculo da irradiação, das perdas e das quantidades de cada equipamento.
3. **Saída:** proposta com os modelos e as quantidades de módulos, inversores e baterias, ordenada por custo.

## Tecnologias

* **Linguagem:** Python (interface em Tkinter)
* **Cálculo solar:** pvlib, pandas, NumPy
* **Banco de dados:** Supabase (autenticação e catálogo de cargas)

## Executando

```bash
pip install -r requirements.txt
python main.py
```

As credenciais do Supabase devem ser informadas em um arquivo `.env`. Os casos de teste podem ser executados sem a interface gráfica:

```bash
python testes/casos.py
```

## Contexto acadêmico

Projeto desenvolvido como Trabalho de Conclusão de Curso de Engenharia de Computação na **Universidade Tecnológica Federal do Paraná (UTFPR), campus Toledo**.

**Autor:** Gabriel Siqueira Müller
**Orientador:** Prof. Dr. Marcos Roberto Bombacini
