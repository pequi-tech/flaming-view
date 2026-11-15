# flaming-view


## Desenvolvimento local

Com Python 3, Node.js e npm instalados, suba o backend e o front end juntos:

```bash
./start.sh
```

O script prepara as dependências na primeira execução, confere os checksums da release e inicia a API em
`http://localhost:8000` e o front end em `http://localhost:5180`. Pressione `Ctrl+C` para encerrar ambos.
Defina `FIRMS_MAP_KEY` no ambiente antes de executar para habilitar dados em tempo real. As portas podem ser
alteradas com `BACKEND_PORT` e `FRONTEND_PORT`.

Se `serving/release/CURRENT` não existir, gere os dados antes de iniciar: `make -C infra && make -C serving publish`.
`infra` e `serving` são etapas de processamento/publicação de dados, não serviços que ficam rodando.

Veja também os READMEs do [front end](front-end/README.md), [backend](back-end/README.md),
[pipeline de dados](infra/README.md) e [publicação da release](serving/README.md).
