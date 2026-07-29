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

## Pendência bloqueadora

`data/metadata/controle_arquivos.csv` contém apenas o cabeçalho. Portanto,
nenhum hash central foi verificado por essa tabela. Isso não significa
divergência dos arquivos já acompanhados por metadados específicos dos
coletores, mas impede marcar a auditoria central de hashes como concluída.

Antes de uma release, o pipeline deve popular o controle central com caminho,
origem, versão e SHA-256 dos artefatos brutos e processados relevantes.

O comando de auditoria termina com erro enquanto essa condição não for
cumprida, mesmo que as demais verificações passem.

## Risco de licença

O PyMuPDF, usado atualmente para extrair tabelas do PDF de correspondência
SNIS–SINISA–ACERTAR, declara licenciamento duplo AGPL 3.0 ou comercial. A
compatibilidade com a distribuição pretendida deve ser revisada; como
alternativa, a extração pode ser migrada para biblioteca permissiva após
validar que as tabelas resultantes permanecem idênticas.

## Escopo e limitações

A busca por segredos reduz falsos positivos usando padrões de atribuição e
chaves privadas; ela não substitui ferramenta especializada nem revisão
humana. O inventário de licenças usa metadados dos pacotes instalados e requer
revisão jurídica antes de distribuição formal.
