# Coleta de dados

Prioridade: endpoint oficial, download oficial, HTTP reproduzível, formulário e somente então navegador automatizado. Não se contorna CAPTCHA, autenticação ou restrições.

O bruto é salvo antes do tratamento e nunca sobrescrito silenciosamente. Registrar URL, método, parâmetros e filtros em JSON válido, horário, HTTP, status, contagem e SHA-256. Conteúdo vazio ou página de erro em HTTP 200 deve falhar.

Endpoints de SINISA e SINAN permanecem `TODO` até inspeção oficial. Mudanças de nomenclatura, metodologia, unidade e código original do SINISA devem ser preservadas.

## População RIPSA/SES-RJ

O formulário `pop_populacao_ripsa2024.def` foi validado por GET. A consulta usa POST em `webtabx.exe` e o coletor seleciona opções pelos rótulos presentes no formulário, evitando manter expressões internas presumidas. Cada ano é exportado pelo link CSV produzido pelo próprio TabNet.

Os brutos anuais são preservados separadamente. A série processada contém 92 municípios por ano e registra a codificação detectada. O código de seis dígitos do TabNet é reconciliado com a dimensão IBGE de sete dígitos já validada.

## Dimensão territorial

A dimensão municipal usa a rota oficial `estados/33/municipios` da API de Localidades do IBGE. A API informa que seus identificadores de divisões político-administrativas são os oficialmente designados pelo IBGE.

As nove regiões de saúde e seus municípios foram transcritos do documento oficial da Superintendência de Atenção Primária à Saúde da SES-RJ, páginas 41–42. A lista publicada repete “Itaperuna” no trecho da região Noroeste e usa “Cachoeira de Macacu”; a dimensão remove a duplicação e concilia o segundo nome com “Cachoeiras de Macacu”, denominação retornada pelo IBGE. Essas decisões são explícitas e testadas.
