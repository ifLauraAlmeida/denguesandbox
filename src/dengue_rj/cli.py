"""Interface de linha de comando do sandbox."""

from pathlib import Path

import click
import pandas as pd
import yaml

from dengue_rj.collectors.ripsa_collector import collect_population
from dengue_rj.collectors.sanitation_glossary_collector import (
    collect_sanitation_glossaries,
)
from dengue_rj.collectors.sinisa_collector import collect_sinisa
from dengue_rj.collectors.sinisa_crosswalk_collector import (
    collect_sinisa_crosswalk,
)
from dengue_rj.collectors.snis_historical_collector import collect_snis_historical
from dengue_rj.collectors.snis_solid_waste_collector import collect_solid_waste
from dengue_rj.collectors.snis_stormwater_collector import collect_stormwater
from dengue_rj.collectors.territory_collector import collect_territory
from dengue_rj.database.builder import build_database, load_demography, load_sanitation
from dengue_rj.metadata.writer import initialize_metadata
from dengue_rj.models.sir import SIRParameters, solve_sir
from dengue_rj.processors.sanitation_harmonization import (
    build_priority_harmonization,
)
from dengue_rj.processors.sanitation_indicators import (
    build_sanitation_indicator_inventory,
)
from dengue_rj.processors.sinisa_crosswalk import build_sinisa_crosswalk
from dengue_rj.processors.sinisa_municipal import process_sinisa_municipal
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
