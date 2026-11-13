# RoadVizor — ETL Gold

## 1. Visão geral

A camada Gold é responsável por transformar os dados tratados na camada Silver em informações consolidadas, organizadas e preparadas para utilização no dashboard do RoadVizor.

Seu principal objetivo é facilitar a visualização e a análise do desempenho dos servidores, permitindo acompanhar métricas de CPU, memória RAM e tráfego de rede em diferentes períodos.

A ETL Gold utiliza Python, Pandas e Boto3 para realizar o processamento dos dados e a comunicação com o Amazon S3.

## 2. Arquitetura da ETL

O processamento segue o fluxo abaixo:

**Silver → Processamento Gold → Dashboard**

- **Silver:** fornece os dados previamente tratados e armazenados no Amazon S3.
- **Gold:** realiza as agregações, calcula médias, valores máximos e indicadores de desempenho.
- **Dashboard:** consome os arquivos gerados pela Gold para apresentar os resultados visualmente.

A ETL Gold acessa diretamente os arquivos existentes na Silver, sem executar novamente o processamento da camada anterior.

## 3. Tecnologias utilizadas

| Tecnologia | Finalidade                                        |
| ---------- | ------------------------------------------------- |
| Python     | Linguagem utilizada no desenvolvimento da ETL     |
| Pandas     | Manipulação, tratamento e agregação dos dados     |
| Boto3      | Comunicação com os serviços da AWS                |
| Amazon S3  | Armazenamento dos dados das camadas Silver e Gold |

## 4. Estrutura de armazenamento

A ETL utiliza dois buckets do Amazon S3:

**Bucket de origem — Silver**

`datalake-silver-roadvizor-sptech`

Prefixo de leitura:

`trusted/`

**Bucket de destino — Gold**

`datalake-gold-roadvizor-sptech`

Prefixo de gravação:

`gold/`

Os arquivos processados são armazenados no bucket Gold, separados por finalidade analítica.

## 5. Funcionamento da ETL

O processamento é dividido em três etapas principais: Extract, Transform e Load.

### 5.1. Extract — Extração

Nesta etapa, o script estabelece conexão com o Amazon S3 e identifica os arquivos CSV disponíveis no prefixo `trusted/` da camada Silver.

Os arquivos encontrados são lidos utilizando Pandas e reunidos em um único DataFrame.

O DataFrame permite manipular e analisar os registros de diferentes servidores em uma estrutura tabular.

### 5.2. Transform — Transformação

Nesta etapa, os dados são preparados para gerar informações analíticas.

**Padronização das colunas**

# Diferenças negativas não são consideradas.

Os nomes das colunas são normalizados para manter um padrão único durante o processamento.

Também são tratados nomes alternativos de métricas, como `cpu_pct` e `cpu_percent`, que podem representar a mesma informação.

**Tratamento dos dados**

São realizadas as seguintes operações:

- Conversão dos timestamps para o formato de data e hora.
- Conversão das métricas para valores numéricos.
- Remoção de registros sem informações essenciais.
- Remoção de capturas duplicadas.
- Ordenação dos registros por servidor e horário.

**Cálculo do tráfego de rede**

Os contadores de rede representam valores acumulados desde a inicialização do sistema.

Por isso, a ETL calcula a diferença entre capturas consecutivas para identificar o volume de dados recebidos e enviados entre os registros.

Valores negativos, que podem indicar reinicialização do servidor, são desconsiderados.

### 5.3. Agregação das métricas

Após o tratamento, os registros são agrupados por servidor e período de tempo.

A agregação transforma várias capturas individuais em indicadores resumidos.

**CPU — Intervalos de 10 minutos**

Calcula:

- Média de utilização da CPU.
- Maior percentual de utilização.
- Quantidade de capturas realizadas.

**RAM — Intervalos de 10 minutos**

Calcula:

- Média de utilização da memória RAM.
- Maior percentual de utilização.
- Quantidade de capturas realizadas.

**Rede — Intervalos de 10 minutos**

Calcula:

- Volume de dados recebidos em MB.
- Volume de dados enviados em MB.
- Quantidade de capturas realizadas.

**Consolidação por hora**

Agrupa as capturas de cada servidor em intervalos de uma hora, calculando as médias e os valores máximos de CPU e RAM, além do tráfego de rede acumulado.

**KPIs — Intervalos de 8 horas**

Consolida os indicadores de cada servidor em três períodos:

| Período          | Intervalo       |
| ---------------- | --------------- |
| Primeiro período | 00:00 até 08:00 |
| Segundo período  | 08:00 até 16:00 |
| Terceiro período | 16:00 até 00:00 |

São calculados os valores médios e máximos de CPU e RAM, o tráfego de rede e a quantidade de capturas.

As médias dos KPIs são calculadas diretamente a partir das capturas originais, evitando distorções causadas por médias de intervalos com quantidades diferentes de registros.

### 5.4. Load — Carregamento

Na última etapa, os DataFrames gerados são convertidos novamente para CSV e enviados ao bucket Gold do Amazon S3.

Os arquivos são armazenados no prefixo `gold/`, ficando disponíveis para consumo pelo dashboard.

## 6. Arquivos gerados

A ETL produz cinco arquivos CSV:

| Arquivo            | Descrição                                                             |
| ------------------ | --------------------------------------------------------------------- |
| `gold_cpu.csv`     | Indicadores de utilização da CPU em intervalos de 10 minutos.         |
| `gold_ram.csv`     | Indicadores de utilização da memória RAM em intervalos de 10 minutos. |
| `gold_rede.csv`    | Volume de dados recebidos e enviados em intervalos de 10 minutos.     |
| `gold_hora.csv`    | Consolidação das métricas por hora.                                   |
| `gold_kpis_8h.csv` | Indicadores consolidados em períodos de 8 horas.                      |

## 7. Como executar

### Pré-requisitos

Antes de executar a ETL, é necessário possuir:

- Python instalado.
- Acesso ao Amazon S3.
- Credenciais AWS válidas e configuradas.
- Permissões para listar e ler objetos do bucket Silver.
- Permissões para gravar objetos no bucket Gold.
- Buckets de origem e destino existentes.

### Instalação das dependências

Instale as bibliotecas necessárias:

```bash
pip install boto3 pandas
```

### Configuração da AWS

Configure as credenciais da AWS por meio do AWS CLI ou de outro método compatível com o Boto3.

O script utiliza a região `us-east-1`.

### Execução

No terminal, acesse o diretório do projeto e execute:

```bash
python a.py
```

Ao finalizar o processamento, o terminal apresenta a quantidade de registros gerados em cada arquivo.

## 8. Resultado esperado

Após a execução bem-sucedida, os arquivos estarão disponíveis no bucket Gold:

```text
datalake-gold-roadvizor-sptech/
└── gold/
    ├── gold_cpu.csv
    ├── gold_ram.csv
    ├── gold_rede.csv
    ├── gold_hora.csv
    └── gold_kpis_8h.csv
```

## 9. Integração com o dashboard RoadVizor

Os arquivos produzidos pela camada Gold servem como fonte de dados para a visualização das métricas de infraestrutura.

A organização temporal permite oferecer diferentes níveis de detalhamento:

- **Visão geral:** KPIs consolidados a cada 8 horas.
- **Análise horária:** médias e máximas das métricas por hora.
- **Análise detalhada:** consulta dos registros em intervalos de 10 minutos.

Dessa forma, o dashboard pode apresentar indicadores gerais e permitir que o usuário aprofunde a análise de um servidor em períodos específicos.

## 10. Considerações finais

A camada Gold finaliza o processo de preparação dos dados do RoadVizor, transformando registros de infraestrutura em informações consolidadas e adequadas para análise.

Sua estrutura facilita o acompanhamento do desempenho dos servidores, a identificação de variações nas métricas e a disponibilização de informações para apoiar a tomada de decisões.

**Projeto acadêmico RoadVizor — Eduarda**
