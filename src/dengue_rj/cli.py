"""Interface de linha de comando do sandbox."""

from pathlib import Path

import click
import pandas as pd
import yaml

from dengue_rj.analysis.exploratory import build_exploratory_analysis
from dengue_rj.analysis.liraa_temporal import build_liraa_temporal_analysis
from dengue_rj.analysis.regression import build_exploratory_regressions
from dengue_rj.analysis.spatial import build_spatial_analysis
from dengue_rj.collectors.liraa_collector import collect_liraa
from dengue_rj.collectors.ripsa_collector import collect_population
from dengue_rj.collectors.sanitation_glossary_collector import (
    collect_sanitation_glossaries,
)
from dengue_rj.collectors.sinan_collector import collect_sinan
from dengue_rj.collectors.sinisa_collector import collect_sinisa
from dengue_rj.collectors.sinisa_crosswalk_collector import (
    collect_sinisa_crosswalk,
)
from dengue_rj.collectors.snis_historical_collector import collect_snis_historical
from dengue_rj.collectors.snis_solid_waste_collector import collect_solid_waste
from dengue_rj.collectors.snis_stormwater_collector import collect_stormwater
from dengue_rj.collectors.spatial_collector import collect_spatial_mesh
from dengue_rj.collectors.territory_collector import collect_territory
from dengue_rj.database.builder import (
    build_database,
    build_dengue_indicators,
    build_dengue_time_series,
    load_demography,
    load_dengue,
    load_liraa,
    load_sanitation,
)
from dengue_rj.metadata.writer import initialize_metadata
from dengue_rj.models.sir import SIRParameters, solve_sir
from dengue_rj.processors.liraa import process_liraa
from dengue_rj.processors.sanitation_harmonization import (
    build_priority_harmonization,
)
from dengue_rj.processors.sanitation_indicators import (
    build_sanitation_indicator_inventory,
)
from dengue_rj.processors.sinan_dengue import process_sinan_residence
from dengue_rj.processors.sinisa_crosswalk import build_sinisa_crosswalk
from dengue_rj.processors.sinisa_municipal import process_sinisa_municipal
from dengue_rj.processors.spatial import process_spatial_mesh
from dengue_rj.visualization.dot_animation import generate_dot_gif


@click.group()
def main() -> None:
    """Opera o pipeline reprodutível da dengue no RJ."""


@main.command("init-metadata")
def init_metadata_command() -> None:
    created = initialize_metadata()
    click.echo(f"Metadados prontos; {len(created)} arquivo(s) criado(s).")


@main.command("build-database")
def build_database_command() -> None:
    click.echo(f"Banco criado: {build_database()}")


@main.command("load-demography")
def load_demography_command() -> None:
    """Valida e carrega população RIPSA no DuckDB."""
    path = load_demography()
    click.echo(f"Demografia carregada e reconciliada: {path}")


@main.command("load-sanitation")
def load_sanitation_command() -> None:
    """Valida e carrega SNIS/SINISA no DuckDB."""
    path = load_sanitation()
    click.echo(f"Saneamento carregado e reconciliado: {path}")


@main.command("load-dengue")
def load_dengue_command() -> None:
    """Valida e carrega casos SINAN/Dengue no DuckDB."""
    path = load_dengue()
    click.echo(f"Dengue carregada por residência: {path}")


@main.command("load-liraa")
def load_liraa_command() -> None:
    """Valida e carrega LIRAa/LIA no DuckDB."""
    path = load_liraa()
    click.echo(f"LIRAa carregado e reconciliado: {path}")


@main.command("calculate-dengue-indicators")
def calculate_dengue_indicators_command() -> None:
    """Calcula casos e incidência municipal pelo início dos sintomas."""
    path = build_dengue_indicators()
    click.echo(f"Indicadores municipais de dengue calculados: {path}")


@main.command("build-dengue-time-series")
def build_dengue_time_series_command() -> None:
    """Gera séries mensais, semanais e cobertura do SINAN."""
    result = build_dengue_time_series()
    click.echo(
        f"Séries de dengue criadas: mensal={result.monthly_file}; "
        f"semanal={result.weekly_file}; cobertura={result.coverage_file}"
    )


@main.command("build-exploratory-analysis")
def build_exploratory_analysis_command() -> None:
    """Produz análise descritiva de dengue e saneamento."""
    result = build_exploratory_analysis()
    click.echo(f"Análise exploratória criada: {result.report}")


@main.command("build-liraa-analysis")
def build_liraa_analysis_command() -> None:
    """Cruza LIRAa com incidência mensal contemporânea e futura."""
    result = build_liraa_temporal_analysis()
    click.echo(f"Análise LIRAa–dengue criada: {result.report_file}")


@main.command("build-exploratory-regressions")
def build_exploratory_regressions_command() -> None:
    """Ajusta regressões exploratórias LIRAa–dengue."""
    result = build_exploratory_regressions()
    click.echo(f"Regressões exploratórias criadas: {result.report_file}")


@main.command("build-spatial-analysis")
def build_spatial_analysis_command() -> None:
    """Calcula Moran global e local da incidência municipal."""
    result = build_spatial_analysis()
    click.echo(f"Análise espacial criada: {result.report_file}")


@main.command()
@click.option("--source", type=click.Choice(["all", "ripsa", "sinisa", "sinan_dengue"]), required=True)
def collect(source: str) -> None:
    with Path("config/sources.yaml").open(encoding="utf-8") as stream:
        sources = yaml.safe_load(stream)
    selected = sources if source == "all" else {source: sources[source]}
    pending = [name for name, config in selected.items() if not config.get("base_url")]
    if pending:
        raise click.ClickException(
            f"Coleta recusada: URL oficial ainda não validada para {', '.join(pending)}."
        )
    raise click.ClickException("Coletores concretos dependem da inspeção oficial dos endpoints.")


@main.command("collect-territory")
def collect_territory_command() -> None:
    """Coleta e valida a dimensão oficial dos municípios do RJ."""
    result = collect_territory()
    click.echo(
        f"Dimensão territorial validada: {result.records} municípios; "
        f"raw={result.raw_file}; processed={result.processed_file}"
    )


@main.command("collect-demography")
def collect_demography_command() -> None:
    """Coleta população RIPSA/SES-RJ para 2020–2024."""
    result = collect_population()
    click.echo(
        f"Demografia validada: {result.records} registros; "
        f"raw={len(result.raw_files)} arquivos; processed={result.processed_file}"
    )


@main.command("collect-liraa")
def collect_liraa_command() -> None:
    """Coleta planilhas LIRAa oficiais de 2020–2024."""
    result = collect_liraa()
    click.echo(f"LIRAa coletado: {len(result.files)} arquivos anuais")


@main.command("collect-spatial-mesh")
def collect_spatial_mesh_command() -> None:
    """Coleta a Malha Municipal 2024 do IBGE para o RJ."""
    result = collect_spatial_mesh()
    click.echo(f"Malha municipal coletada: {result.raw_file}")


@main.command("process-spatial-mesh")
def process_spatial_mesh_command() -> None:
    """Valida a malha e cria vizinhança rainha."""
    result = process_spatial_mesh()
    click.echo(
        f"Malha processada: {result.municipalities} municípios; "
        f"{result.directed_edges} arestas dirigidas"
    )


@main.command("process-liraa")
def process_liraa_command() -> None:
    """Consolida os levantamentos municipais LIRAa/LIA."""
    result = process_liraa()
    click.echo(
        f"LIRAa processado: {result.records} registros; "
        f"{result.surveys} levantamentos; cobertura={result.coverage_file}"
    )


@main.command("collect-sinan-pilot")
def collect_sinan_pilot_command() -> None:
    """Coleta o arquivo bruto piloto SINAN/Dengue de 2020."""
    result = collect_sinan()
    click.echo(f"SINAN piloto coletado: {result.files[0]}")


@main.command("collect-sinan")
def collect_sinan_command() -> None:
    """Coleta os arquivos brutos SINAN/Dengue de 2020–2024."""
    result = collect_sinan(tuple(range(2020, 2025)))
    click.echo(f"SINAN coletado: {len(result.files)} anos; 2020–2024")


@main.command("process-sinan-pilot")
def process_sinan_pilot_command() -> None:
    """Processa somente residentes do RJ no piloto SINAN 2020."""
    result = process_sinan_residence(
        Path("data/raw/dengue/sinan/DENGBR20.csv.zip"),
        2020,
    )
    click.echo(
        f"SINAN piloto processado por residência: {result.records} registros; "
        f"{result.municipalities} municípios; {result.output_file}"
    )


@main.command("process-sinan")
def process_sinan_command() -> None:
    """Processa 2020–2024 exclusivamente por município de residência."""
    records = 0
    for year in range(2020, 2025):
        result = process_sinan_residence(
            Path(f"data/raw/dengue/sinan/DENGBR{year % 100:02d}.csv.zip"),
            year,
        )
        records += result.records
    click.echo(f"SINAN processado por residência: {records} registros; 2020–2024")


@main.command("collect-sinisa")
def collect_sinisa_command() -> None:
    """Coleta os cinco módulos oficiais do SINISA, referência 2023."""
    result = collect_sinisa()
    click.echo(
        f"SINISA coletado: referência 2023; {len(result.package_files)} módulos; "
        f"raw={result.catalog_file.parent}"
    )


@main.command("collect-sinisa-crosswalk")
def collect_sinisa_crosswalk_command() -> None:
    """Coleta o PDF oficial de transição SNIS-SINISA-ACERTAR."""
    result = collect_sinisa_crosswalk()
    click.echo(f"De-para SINISA-SNIS coletado: {result.raw_file}")


@main.command("collect-sanitation-glossaries")
def collect_sanitation_glossaries_command() -> None:
    """Coleta glossários SNIS/SINISA de indicadores de água e esgoto."""
    result = collect_sanitation_glossaries()
    click.echo(f"Glossários coletados: {len(result.raw_files)} PDFs")


@main.command("collect-snis-historical")
def collect_snis_historical_command() -> None:
    """Coleta indicadores municipais SNIS de 2020–2022."""
    result = collect_snis_historical()
    click.echo(
        f"SNIS histórico coletado: {result.source_records} registros de origem; "
        f"{result.processed_records} indicadores; processed={result.processed_file}"
    )


@main.command("collect-solid-waste")
def collect_solid_waste_command() -> None:
    """Coleta planilhas anuais SNIS de resíduos sólidos."""
    result = collect_solid_waste()
    click.echo(
        f"Resíduos sólidos coletados: {len(result.raw_files)} pacotes anuais; "
        f"{result.records} indicadores do RJ; processed={result.processed_file}"
    )


@main.command("collect-stormwater")
def collect_stormwater_command() -> None:
    """Coleta planilhas anuais SNIS de águas pluviais."""
    result = collect_stormwater()
    click.echo(
        f"Águas pluviais coletadas: {len(result.raw_files)} pacotes anuais; "
        f"{result.records} indicadores do RJ; processed={result.processed_file}"
    )


@main.command("build-sanitation-indicator-inventory")
def build_sanitation_indicator_inventory_command() -> None:
    """Inventaria códigos e metadados originais SNIS/SINISA."""
    output = build_sanitation_indicator_inventory()
    records = len(pd.read_csv(output))
    click.echo(f"Inventário de saneamento criado: {records} indicadores; {output}")


@main.command("build-sinisa-crosswalk")
def build_sinisa_crosswalk_command() -> None:
    """Extrai a regra oficial de transição para formato tabular."""
    output = build_sinisa_crosswalk()
    records = len(pd.read_csv(output))
    click.echo(f"De-para tabular criado: {records} informações; {output}")


@main.command("build-sanitation-harmonization")
def build_sanitation_harmonization_command() -> None:
    """Materializa a comparação dos indicadores prioritários."""
    output = build_priority_harmonization()
    build_sanitation_indicator_inventory()
    records = len(pd.read_csv(output))
    click.echo(f"Harmonização prioritária criada: {records} indicadores; {output}")


@main.command("process-sinisa-municipal")
def process_sinisa_municipal_command() -> None:
    """Processa os quatro componentes municipais SINISA 2023."""
    result = process_sinisa_municipal()
    click.echo(
        f"SINISA municipal processado: {result.records} registros; "
        f"{len(result.component_files)} componentes; cobertura={result.coverage_file}"
    )


@main.command()
@click.option("--source", type=str, required=True)
def process(source: str) -> None:
    raise click.ClickException(
        f"Não há bruto validado para processar ({source}); execute coleta oficial primeiro."
    )


@main.command("calculate-indicators")
def calculate_indicators() -> None:
    raise click.ClickException("Não há fatos validados no banco; indicadores não foram fabricados.")


@main.command()
@click.option("--municipality-code", required=True)
@click.option("--population", type=click.FloatRange(min=1), required=True)
@click.option("--infected", type=click.FloatRange(min=0), required=True)
@click.option("--removed", type=click.FloatRange(min=0), default=0.0, show_default=True)
@click.option("--beta", type=click.FloatRange(min=0), required=True)
@click.option("--gamma", type=click.FloatRange(min=0, min_open=True), required=True)
@click.option("--days", type=click.IntRange(min=1), default=180, show_default=True)
def simulate(
    municipality_code: str,
    population: float,
    infected: float,
    removed: float,
    beta: float,
    gamma: float,
    days: int,
) -> None:
    params = SIRParameters(population, infected, removed, beta, gamma)
    result = solve_sir(params, days)
    table = pd.DataFrame(
        {
            "codigo_ibge_municipio": municipality_code,
            "municipio": "CENARIO_SINTETICO",
            "data": pd.NaT,
            "tempo": result.time,
            "cenario": "hipotetico",
            "susceptible": result.susceptible,
            "infected": result.infected,
            "removed": result.removed,
            "new_infections": result.new_infections,
            "new_removals": result.new_removals,
            "beta": beta,
            "gamma": gamma,
            "basic_reproduction_number": params.basic_reproduction_number,
            "effective_reproduction_number": result.effective_reproduction_number,
            "population": population,
            "model_version": "0.1.0",
        }
    )
    output = Path(f"outputs/tables/{municipality_code}_simulacao_sintetica_sir.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False)
    click.echo(f"Simulação hipotética salva: {output}")


@main.command("generate-gif")
@click.option("--input", "input_path", type=click.Path(path_type=Path, exists=True), required=True)
@click.option("--output", type=click.Path(path_type=Path), default=Path("outputs/gifs/sir_demo.gif"))
def generate_gif(input_path: Path, output: Path) -> None:
    table = pd.read_csv(input_path)
    generate_dot_gif(table, output, str(table["municipio"].iloc[0]))
    click.echo(f"GIF salvo: {output}")


@main.command()
def validate() -> None:
    SIRParameters(1000, 1, 0, 0.2, 0.1).validate()
    initialize_metadata()
    click.echo("Validações estruturais concluídas.")


@main.command("fit-sir")
@click.option("--municipality-code", required=True)
def fit_sir(municipality_code: str) -> None:
    raise click.ClickException(
        f"Calibração de {municipality_code} requer série oficial processada; nada foi estimado."
    )


if __name__ == "__main__":
    main()
