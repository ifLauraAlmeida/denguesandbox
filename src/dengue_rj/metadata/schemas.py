"""Schemas CSV de rastreabilidade."""

COLLECTION_COLUMNS = [
    "id_coleta", "fonte", "sistema", "descricao_base", "url_origem", "endpoint",
    "metodo_http", "arquivo_bruto", "formato_arquivo", "data_referencia_inicial",
    "data_referencia_final", "data_atualizacao_fonte", "data_hora_coleta",
    "parametros_requisicao", "filtros_selecionados", "opcoes_selecionadas",
    "codigo_http", "status_coleta", "quantidade_registros", "hash_sha256",
    "versao_coletor", "observacoes",
]
CALCULATION_COLUMNS = [
    "id_calculo", "nome_indicador", "descricao", "formula", "numerador", "denominador",
    "variaveis_entrada", "fonte_variaveis", "unidade", "escala", "nivel_temporal",
    "nivel_geografico", "tratamento_valores_ausentes", "tratamento_divisao_zero",
    "hipoteses", "limitacoes", "referencia_metodologica", "arquivo_codigo",
    "funcao_codigo", "versao_calculo", "arquivo_saida", "data_execucao", "observacoes",
]
VARIABLE_COLUMNS = [
    "fonte", "nome_original", "nome_padronizado", "descricao", "tipo_original",
    "tipo_processado", "unidade", "dominio", "valores_validos", "valor_ausente_original",
    "transformacao_aplicada", "arquivo_origem", "observacoes",
]
FILE_CONTROL_COLUMNS = [
    "arquivo", "camada", "fonte", "data_criacao", "data_modificacao",
    "quantidade_linhas", "quantidade_colunas", "hash_sha256", "arquivo_origem",
    "status_validacao", "versao_pipeline",
]
