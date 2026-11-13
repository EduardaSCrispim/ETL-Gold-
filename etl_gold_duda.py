import boto3
import pandas as pd
from io import StringIO



REGIAO_AWS = "us-east-1"
BUCKET_SILVER = "datalake-silver-roadvizor-sptech"
BUCKET_GOLD = "datalake-gold-Duda-sptech"
PREFIXO_SILVER = "trusted/"
PREFIXO_GOLD = "gold/"
SEPARADOR = ";"


s3 = boto3.client(
    "s3",
    region_name=REGIAO_AWS
)




def ler_silver():

    print("\nIniciando leitura da camada Silver...")

    arquivos = []

    paginador = s3.get_paginator("list_objects_v2")

    paginas = paginador.paginate(
        Bucket=BUCKET_SILVER,
        Prefix=PREFIXO_SILVER
    )

  
    for pagina in paginas:

        for objeto in pagina.get("Contents", []):

            caminho = objeto["Key"]

            if caminho.lower().endswith(".csv"):

                print(f"Lendo arquivo: {caminho}")

            
                resposta = s3.get_object(
                    Bucket=BUCKET_SILVER,
                    Key=caminho
                )

                conteudo = resposta["Body"].read().decode("utf-8-sig")

                df_arquivo = pd.read_csv(
                    StringIO(conteudo),
                    sep=SEPARADOR
                )

                arquivos.append(df_arquivo)

   
    if not arquivos:
        raise Exception("Nenhum arquivo CSV encontrado na Silver.")

    df = pd.concat(
        arquivos,
        ignore_index=True
    )

    print(f"Total de capturas encontradas: {len(df)}")

    return df



def padronizar_colunas(df):

    print("\nPadronizando as colunas...")

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

   
    aliases = {

        "mac_address": "mac",

        
        "cpu_pct": "cpu",
        "cpu_percent": "cpu",
        "cpu_percentual": "cpu",

        
        "ram_pct": "ram",
        "ram_percent": "ram",
        "ram_percentual": "ram",

    
        "rede_recebida": "rede_recebida_mb",
        "rede_enviada": "rede_enviada_mb"
    }

   
    for nome_antigo, nome_novo in aliases.items():

        if nome_antigo in df.columns and nome_novo not in df.columns:

            df = df.rename(
                columns={nome_antigo: nome_novo}
            )

  
    identificadores = [
        "mac",
        "cod_maquina",
        "hostname"
    ]

    coluna_id = None

    for coluna in identificadores:

        if coluna in df.columns:
            coluna_id = coluna
            break

    if coluna_id is None:

        raise Exception(
            "Não foi encontrada uma coluna para identificar o servidor."
        )

   
    df["id_servidor"] = df[coluna_id].astype(str)

 
    colunas_obrigatorias = [
        "timestamp",
        "id_servidor",
        "cpu",
        "ram",
        "rede_recebida_mb",
        "rede_enviada_mb"
    ]


    for coluna in colunas_obrigatorias:

        if coluna not in df.columns:

            raise Exception(
                f"Coluna obrigatória não encontrada: {coluna}"
            )

    return df




def tratar_dados(df):

    print("\nTratando os dados...")

   
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )


    colunas_numericas = [
        "cpu",
        "ram",
        "rede_recebida_mb",
        "rede_enviada_mb"
    ]

    for coluna in colunas_numericas:

        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce"
        )

 
    df = df.dropna(
        subset=[
            "timestamp",
            "id_servidor",
            "cpu",
            "ram"
        ]
    )

  
    df = df.drop_duplicates(
        subset=[
            "id_servidor",
            "timestamp"
        ]
    )

   
    df = df.sort_values(
        by=[
            "id_servidor",
            "timestamp"
        ]
    )

  
    df["rede_recebida_mb_delta"] = (
        df.groupby("id_servidor")["rede_recebida_mb"].diff()
    )

    df["rede_enviada_mb_delta"] = (
        df.groupby("id_servidor")["rede_enviada_mb"].diff()
    )

    # Se o contador diminuir, pode ter ocorrido reinicialização.
 
    df.loc[
        df["rede_recebida_mb_delta"] < 0,
        "rede_recebida_mb_delta"
    ] = pd.NA

    df.loc[
        df["rede_enviada_mb_delta"] < 0,
        "rede_enviada_mb_delta"
    ] = pd.NA

    print(f"Capturas válidas: {len(df)}")

    return df

# CPU A CADA 10 MINUTOS

def gerar_cpu(df):

    print("\nCalculando métricas de CPU...")


    df["intervalo_10min"] = (
        df["timestamp"].dt.floor("10min")
    )

    gold = df.groupby(
        [
            "id_servidor",
            "intervalo_10min"
        ]
    ).agg(
        cpu_media=("cpu", "mean"),
        cpu_maxima=("cpu", "max"),
        quantidade_capturas=("cpu", "count")
    ).reset_index()

    return gold



#  RAM A CADA 10 MINUTOS


def gerar_ram(df):

    print("\nCalculando métricas de RAM...")

    df["intervalo_10min"] = (
        df["timestamp"].dt.floor("10min")
    )

    gold = df.groupby(
        [
            "id_servidor",
            "intervalo_10min"
        ]
    ).agg(
        ram_media=("ram", "mean"),
        ram_maxima=("ram", "max"),
        quantidade_capturas=("ram", "count")
    ).reset_index()

    return gold



# REDE A CADA 10 MINUTOS


def gerar_rede(df):

    print("\nCalculando métricas de rede...")

    df["intervalo_10min"] = (
        df["timestamp"].dt.floor("10min")
    )


    gold = df.groupby(
        [
            "id_servidor",
            "intervalo_10min"
        ]
    ).agg(
        rede_recebida_mb=(
            "rede_recebida_mb_delta",
            "sum"
        ),

        rede_enviada_mb=(
            "rede_enviada_mb_delta",
            "sum"
        ),

        quantidade_capturas=(
            "timestamp",
            "count"
        )
    ).reset_index()

    return gold



# CALCULO POR HORA

def gerar_horario(df):

    print("\nCalculando médias por hora...")

    df["intervalo_hora"] = (
        df["timestamp"].dt.floor("h")
    )

    gold = df.groupby(
        [
            "id_servidor",
            "intervalo_hora"
        ]
    ).agg(
        cpu_media=("cpu", "mean"),
        cpu_maxima=("cpu", "max"),

        ram_media=("ram", "mean"),
        ram_maxima=("ram", "max"),

        rede_recebida_mb=(
            "rede_recebida_mb_delta",
            "sum"
        ),

        rede_enviada_mb=(
            "rede_enviada_mb_delta",
            "sum"
        ),

        quantidade_capturas=("timestamp", "count")

    ).reset_index()

    return gold


# PAR AS KPIs


def gerar_kpis_8h(df):

    print("\nCalculando KPIs de 8 horas...")

    df["periodo_8h"] = (
        df["timestamp"].dt.floor("8h")
    )

    # Calcula os indicadores de cada servidor, no caso a média
    gold = df.groupby(
        [
            "id_servidor",
            "periodo_8h"
        ]
    ).agg(
        cpu_media=("cpu", "mean"),
        cpu_maxima=("cpu", "max"),

        ram_media=("ram", "mean"),
        ram_maxima=("ram", "max"),

        rede_recebida_mb=(
            "rede_recebida_mb_delta",
            "sum"
        ),

        rede_enviada_mb=(
            "rede_enviada_mb_delta",
            "sum"
        ),

        quantidade_capturas=("timestamp", "count")

    ).reset_index()

    return gold


# ENVIA DOS ARQUIVOS PARA A GOLD


def enviar_gold(df, nome_arquivo):

    # Converte o DataFrame para CSV
    arquivo_csv = df.to_csv(
        index=False,
        sep=SEPARADOR
    )

    # Define o caminho do arquivo dentro do bucket
    caminho = PREFIXO_GOLD + nome_arquivo

    # Envia o arquivo para o S3
    s3.put_object(
        Bucket=BUCKET_GOLD,
        Key=caminho,
        Body=arquivo_csv.encode("utf-8"),
        ContentType="text/csv"
    )

    print(f"Arquivo enviado para: {caminho}")


# EXECUÇÃO DA ETL GOLD

def main():

    try:

        print("\n======================================")
        print("       ETL GOLD - ROADVIZOR")
        print("======================================")

       
        df = ler_silver()
        df = padronizar_colunas(df)
        df = tratar_dados(df)

        # Resume os dados a cada 10 minutos pra tela do grafico
        gold_cpu = gerar_cpu(df)
        gold_ram = gerar_ram(df)
        gold_rede = gerar_rede(df)
        gold_hora = gerar_horario(df)
        gold_kpis = gerar_kpis_8h(df)

        
        enviar_gold(
            "gold_cpu.csv"
        )

        enviar_gold(
            "gold_ram.csv"
        )

        enviar_gold(
            "gold_rede.csv"
        )

        enviar_gold(
            "gold_hora.csv"
        )

        enviar_gold(
            "gold_kpis_8h.csv"
        )

        print("\n======================================")
        print("       ETL GOLD FINALIZADA!")
        print("======================================")

        # Quantos registros foram produzidos hihi
        print("\nRegistros gerados:")

        print(f"CPU: {len(gold_cpu)}")

        print(f"RAM: {len(gold_ram)}")

        print(f"Rede: {len(gold_rede)}")

        print(f"Por hora: {len(gold_hora)}")

        print(f"KPIs de 8 horas: {len(gold_kpis)}")

    except Exception as erro:

        print("\nERRO DURANTE A ETL GOLD:")
        print(erro)


if __name__ == "__main__":
    main()


