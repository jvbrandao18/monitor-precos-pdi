# Monitor de preços em Python

Projeto de automação para o **PDI 2025/2026 — Habilidade digital**. Substitui a consulta manual de páginas de produtos por uma rotina que coleta preços, guarda o histórico, identifica ofertas e gera relatórios.

## O que o projeto faz

- Consulta páginas por HTTP ou controla um navegador Chromium com Playwright (**RPA**).
- Extrai um preço por seletor CSS configurável, sem alterar o código para cadastrar produtos.
- Registra cada consulta em SQLite, incluindo horário, moeda, preço-alvo e falhas.
- Sinaliza `ALERTA` quando o preço é menor ou igual ao alvo; o aviso aparece no terminal e nos relatórios.
- Exporta o histórico para CSV e um relatório HTML que abre no navegador.
- Executa diariamente pelo GitHub Actions, às **09h de Brasília (12h UTC)**, ou sob demanda.

Não envia e-mail nem mensagens. Não realiza compras. O agendamento consulta inicialmente uma loja pública de treino, com preços em libras (`GBP`).

## Executar em cinco minutos

Requisito: Python 3.11 ou superior.

```bash
git clone https://github.com/jvbrandao18/monitor-precos-pdi.git
cd monitor-precos-pdi
python -m venv .venv
```

Ative o ambiente:

```bash
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instale e rode a demonstração:

```bash
python -m pip install -e .
python -m monitor_precos demo
```

A demonstração sobe uma pequena loja HTTP local, consulta um produto por **R$ 199,90**, altera o preço para **R$ 129,90** e consulta novamente. O alvo é **R$ 150,00**. A segunda consulta deve gerar `ALERTA`.

Abra `output/relatorio.html` no navegador ou `output/historico.csv` em uma planilha. O banco fica em `data/precos.sqlite3`. A demonstração usa dados fictícios e não precisa de uma loja externa. As URLs locais da demonstração só funcionam enquanto o comando está executando.

## Demonstração de RPA com navegador

```bash
python -m pip install -e '.[browser]'
python -m playwright install chromium
python -m monitor_precos demo --browser --db data/demo-rpa.sqlite3 --output output/demo-rpa
```

No Linux, se faltarem bibliotecas do sistema, use `python -m playwright install --with-deps chromium`. O robô abre o Chromium em modo headless, navega até o produto, espera o elemento de preço e lê seu conteúdo. A mesma lógica de armazenamento e alerta é usada nos dois modos.

## Monitorar produtos

```bash
python -m monitor_precos run
# Para páginas que carregam o preço com JavaScript:
python -m monitor_precos run --browser
# Regerar relatórios sem consultar lojas:
python -m monitor_precos report
```

Edite `products.json` para cadastrar seus produtos. Exemplo de estrutura para uma loja que você tenha escolhido:

```json
[
  {
    "id": "meu-produto",
    "name": "Meu produto",
    "url": "https://sua-loja.example/produto",
    "selector": ".preco",
    "currency": "BRL",
    "decimal_separator": ",",
    "target_price": "150.00"
  }
]
```

Essa URL ilustra o formato; substitua pela página real. O seletor deve encontrar **exatamente um preço**. `target_price` sempre usa ponto decimal e não leva símbolo de moeda. `decimal_separator` descreve o preço exibido na página. Moedas não são convertidas.

Parâmetros disponíveis:

```bash
python -m monitor_precos run --config products.json --db data/precos.sqlite3 --output output
python -m monitor_precos --help
```

Saída `0`: consultas concluídas, inclusive quando há alertas. Saída `1`: alguma coleta falhou, mas as demais continuam e os relatórios são gerados. Saída `2`: configuração ou execução inválida.

## Automação no GitHub

Em **Actions → Monitorar preços → Run workflow**, execute uma coleta manual. O mesmo fluxo roda diariamente; o GitHub pode atrasar execuções agendadas. Após cada execução, baixe o artefato `monitor-precos-N`: ele contém banco e relatórios.

O histórico é restaurado por cache entre execuções. O cache pode expirar ou ser removido pelo GitHub; os artefatos também têm retenção limitada. Para histórico permanente, execute localmente com backup do SQLite ou armazene os artefatos fora do GitHub. Repositórios públicos sem atividade podem ter o agendamento desativado pelo GitHub após 60 dias.

O workflow **Testes e demonstração RPA** valida o projeto em cada push e executa uma demonstração com Chromium. Seu artefato `evidencia-demonstracao-rpa` serve como evidência reproduzível.

## Validação e arquitetura

```bash
python -m unittest discover -s tests -v
```

Os testes verificam conversão de preços brasileiros e internacionais, queda de preço com coleta HTTP local, persistência, falha isolada de uma loja, preço exatamente no alvo, configuração duplicada e escape nos relatórios.

```text
products.json → HTTP ou Chromium/Playwright → preço em centavos
                                            ↓
                                      SQLite + regra de alvo
                                            ↓
                                    terminal + CSV + HTML
```

- `monitor_precos/core.py`: coleta, validação, banco e relatórios.
- `monitor_precos/cli.py`: comandos e loja temporária da demonstração.
- `tests/`: testes automatizados.
- `.github/workflows/`: testes, RPA e monitoramento diário.
- [Registro e roteiro do PDI](docs/PDI.md).
- [Relatório de demonstração incluído](examples/relatorio-demo.html).

## Limites

Cada loja tem seu HTML; mudanças podem exigir ajuste do seletor. Consulte páginas cujo acesso automatizado seja permitido e use uma frequência moderada. Sites com login, CAPTCHA ou bloqueio de robôs não são contornados. Frete, cupons, parcelamento e disponibilidade não entram no cálculo. Uma falha de coleta fica registrada como `ERRO`, sem fabricar preço. A coleta usa limites de tempo e, no modo HTTP, novas tentativas em falhas transitórias.

Datas do histórico são registradas em UTC. A demonstração comprova o funcionamento com valores controlados; preços externos podem mudar ou ficar indisponíveis.
