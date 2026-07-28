# Conventional Commits

Formato: `tipo(escopo): descrição imperativa`, seguido opcionalmente por corpo e rodapé.

Tipos usuais: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci` e `perf`. Escopos devem nomear uma responsabilidade, como `collector`, `sir`, `metadata` ou `sinan`.

Mudança incompatível usa `!` (`feat(cli)!:`) e rodapé `BREAKING CHANGE:`. O corpo explica motivo e impacto; não repete apenas o título.

Válidos: `feat(sir): implement Euler solver`, `fix(sinan): handle empty TabNet response`, `test(sir): add population conservation test`.

Inválidos: `updates`, `fix stuff`, `feat: added things.` (vagos, tempo verbal inadequado ou pontuação desnecessária).
