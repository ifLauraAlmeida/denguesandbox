# Auditoria preliminar de release

Data: 2026-07-29

## Resultado automatizado

- Ambiente resolvido e fixado em `uv.lock`: 76 pacotes.
- Testes: 69 aprovados.
- Cobertura total medida: 50%.
- Lint: aprovado.
- Arquivos candidatos à versão acima de 5 MiB: nenhum.
- Possíveis segredos de alta confiança: nenhum.
- Licenças declaradas pelas dependências diretas: inventariadas, sem campo vazio.
- Repositório Git: menos de 1 MiB de objetos soltos e nenhum lixo reportado.

O comando reproduzível é:

```powershell
python -m dengue_rj.cli audit-release
```

A saída detalhada é escrita em `outputs/reports/auditoria_release.json`.

## Integridade dos artefatos

O comando `refresh-file-control` inventariou 107 artefatos locais:

- 76 arquivos brutos;
- 31 arquivos processados;
- 107 hashes SHA-256 verificados;
- 92 conteúdos distintos por hash;
- 26 linhas pertencentes a grupos com conteúdo duplicado.

As duplicatas refletem coletas históricas preservadas. Nenhum arquivo foi
apagado ou escolhido silenciosamente. O inventário é recriado em ordem
determinística e não inclui banco, saídas analíticas nem arquivos `.gitkeep`.

Em ambiente limpo, os dados devem ser coletados e processados antes de executar:

```powershell
python -m dengue_rj.cli refresh-file-control
python -m dengue_rj.cli audit-release
```

O gate termina com erro se faltar um arquivo registrado, se um hash divergir
ou se o controle estiver vazio.

## Risco de licença

O PyMuPDF, usado atualmente para extrair tabelas do PDF de correspondência
SNIS–SINISA–ACERTAR, declara licenciamento duplo AGPL 3.0 ou comercial. A
compatibilidade com a distribuição pretendida deve ser revisada; como
alternativa, a extração pode ser migrada para biblioteca permissiva após
validar que as tabelas resultantes permanecem idênticas.

Em ensaio com `pdfplumber` 0.11.10, as 74 linhas foram encontradas, mas 53
células divergiram e duas expressões SINISA desapareceram (`ES005` e `FN030`).
A migração foi rejeitada para não degradar a rastreabilidade.

## Escopo e limitações

A busca por segredos reduz falsos positivos usando padrões de atribuição e
chaves privadas; ela não substitui ferramenta especializada nem revisão
humana. O inventário de licenças usa metadados dos pacotes instalados e requer
revisão jurídica antes de distribuição formal.
