
# 🧪 Benchmark de Ferramentas de Ofuscação de Código Python

Este projeto foi desenvolvido como parte do trabalho final do curso de **Engenharia de Computação e Informação da UFRJ**. Ele tem como objetivo avaliar diferentes ferramentas de ofuscação de código Python com base em métricas como desempenho, uso de memória, tempo de inicialização e tamanho final do código.

---

## 📌 Visão Geral do Processo

```mermaid
flowchart TD
    classDef header fill:#303F9F,color:white,stroke-width:0px,font-weight:bold,font-size:18px
    classDef mainFlow fill:#3F51B5,color:white,stroke-width:0px,font-weight:bold
    classDef toolBox fill:#00BCD4,color:white,stroke-width:0px
    classDef processBox fill:#FF9800,color:white,stroke-width:0px
    classDef metricBox fill:#4CAF50,color:white,stroke-width:0px
    classDef outputBox fill:#9C27B0,color:white,stroke-width:0px

    TITLE["PYTHON CODE OBFUSCATION<br>BENCHMARK"]:::header
    INPUT["PYTHON<br>SOURCE CODE"]:::mainFlow
    TOOLS["OBFUSCATION<br>TOOLS"]:::mainFlow
    BENCHMARK["BENCHMARK<br>PROCESS"]:::mainFlow
    METRICS["EVALUATED<br>METRICS"]:::mainFlow
    RESULTS["COMPARATIVE<br>ANALYSIS"]:::mainFlow

    TITLE --> INPUT --> TOOLS --> BENCHMARK --> METRICS --> RESULTS

    TOOLS --- ToolsGroup
    subgraph ToolsGroup [" "]
        direction TB
        T1["PyArmor<br><i>Advanced commercial<br>protection</i>"]:::toolBox
        T2["PyMinifier<br><i>Basic minification<br>and obfuscation</i>"]:::toolBox
        T3["Cython<br><i>Compilation to<br>C code</i>"]:::toolBox
        T4["PyInstaller<br><i>Executable<br>packaging</i>"]:::toolBox
        T5["PyObfuscate<br><i>Identifier<br>obfuscation</i>"]:::toolBox
        T1 --- T2 --- T3 --- T4 --- T5
    end

    BENCHMARK --- ProcessGroup
    subgraph ProcessGroup [" "]
        direction TB
        B1["1. Preparation<br><i>Tool installation and<br>dependency detection</i>"]:::processBox
        B2["2. Application<br><i>Obfuscation execution<br>on original code</i>"]:::processBox
        B3["3. Execution<br><i>Tests with multiple<br>controlled iterations</i>"]:::processBox
        B4["4. Monitoring<br><i>Continuous measurement of<br>resources and performance</i>"]:::processBox
        B1 --- B2 --- B3 --- B4
    end

    METRICS --- MetricsGroup
    subgraph MetricsGroup [" "]
        direction TB
        M1["⏱️ Execution<br>Time<br><i>(seconds)</i>"]:::metricBox
        M2["💾 Memory<br>Usage<br><i>(MB)</i>"]:::metricBox
        M3["📏 Code<br>Size<br><i>(KB)</i>"]:::metricBox
        M4["⚡ Startup<br>Time<br><i>(ms)</i>"]:::metricBox
        M1 --- M2 --- M3 --- M4
    end

    RESULTS --- ResultsGroup
    subgraph ResultsGroup [" "]
        direction TB
        R1["📊 Comparative<br>Graphs"]:::outputBox
        R2["📈 Statistical<br>Analysis"]:::outputBox
        R3["🌐 Interactive<br>HTML Dashboard"]:::outputBox
        R1 --- R2 --- R3
    end

    class ToolsGroup,ProcessGroup,MetricsGroup,ResultsGroup invisible
    classDef invisible fill:none,stroke:none
```

---

## 🚀 Como Executar

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/benchmark-python-obfuscation.git
cd benchmark-python-obfuscation
```

### 2. Instale as dependências

Crie um ambiente virtual e instale os requisitos:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Algumas ferramentas de ofuscação precisam ser instaladas separadamente (ex: `pip install pyarmor pyminifier cython pyinstaller`)

### 3. Execute o benchmark

```bash
python benchmark.py --test-files exemplo1.py exemplo2.py -i 10 -o resultados/
```

---

## ⚙️ Argumentos da Linha de Comando

| Flag | Descrição |
|------|-----------|
| `--test-files`, `-t` | Lista de arquivos `.py` a serem testados |
| `--iterations`, `-i` | Número de execuções por ferramenta (default: 3) |
| `--output-dir`, `-o` | Caminho do diretório de saída |
| `--disable-tools` | Ferramentas a serem desabilitadas |

---

## 🛠️ Ferramentas Suportadas

- **Original**: Código sem alterações
- **PyArmor**: Ofuscação avançada de bytecode
- **Pyminifier**: Minificação e renomeação simples
- **Cython**: Compilação para C
- **PyInstaller**: Empacotamento em executável
- **PyObfuscate**: Renomeação de identificadores

---

## 📂 Estrutura de Saída

O diretório de saída conterá:

- `summary.json`: Métricas agregadas
- `results.csv`: Tabela de dados
- `report.html`: Dashboard interativo
- `chart_*.png`: Gráficos separados por métrica
- `plot.png`: Gráfico comparativo geral
- `system_info.csv`: Dados sobre o sistema

---

## 📈 Métricas Coletadas

- ⏱️ **execution_time** — tempo de execução
- ⚡ **startup_time** — tempo de inicialização
- 💾 **memory_usage** — pico de memória
- 📏 **code_size** — tamanho final do código

---

## 🤝 Contribuindo

Sinta-se à vontade para abrir issues ou enviar PRs com melhorias, novas ferramentas ou correções. Basta seguir o padrão do dicionário `TOOLS` para adicionar novas estratégias.

---

## 🧠 Licença

Distribuído sob licença MIT.

---

## 🌎 English Version?

[Click here to see the English README](README_EN.md) — coming soon!

