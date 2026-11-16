# Evidências — PDI 2025/2026

## Vínculo com a ação

| Campo | Entrega |
| --- | --- |
| Item a desenvolver | Habilidade digital |
| Ação | Projeto de Programação |
| Objetivo | Um projeto concluído em Python que utilize RPA e automatize um processo |
| Processo automatizado | Consultar páginas de produtos, registrar preços e comparar com um valor-alvo |
| Entrega | Código, testes, demonstração com navegador, histórico e relatórios |

## Como comprovar

1. Acesse o repositório e consulte o README.
2. Abra **Actions → Testes e demonstração RPA** e confira uma execução concluída.
3. Baixe o artefato `evidencia-demonstracao-rpa` e abra o relatório HTML.
4. Confirme a primeira observação a R$ 199,90 e a segunda a R$ 129,90, com alerta para o alvo de R$ 150,00. Esses preços são fictícios, da demonstração local.
5. Em **Actions → Monitorar preços**, execute a consulta da loja de treino e baixe seu relatório.

Alternativa local: siga o README e execute `python -m monitor_precos demo --browser`. O modo RPA requer a instalação opcional do Playwright e do Chromium.

## Texto sugerido para acompanhamento

> Projeto de monitoramento de preços em Python concluído e publicado no GitHub. A solução automatiza a consulta de páginas de produtos por HTTP ou RPA com Playwright/Chromium, registra o histórico em SQLite, identifica preços abaixo do valor-alvo e gera relatórios HTML e CSV. Inclui testes automatizados, demonstração reproduzível de queda de preço e rotina de execução diária no GitHub Actions. Evidência: https://github.com/jvbrandao18/monitor-precos-pdi

## Roteiro para apresentação

- **Problema:** consultas manuais repetidas para verificar se um produto atingiu o preço desejado.
- **Entrada:** lista de produtos, URLs, seletores CSS e preços-alvo em JSON.
- **RPA:** Chromium navega até as páginas e lê o elemento de preço.
- **Regra:** preço coletado menor ou igual ao alvo gera `ALERTA`.
- **Resultado:** histórico auditável e relatórios gerados sem preencher planilhas manualmente.
- **Conhecimentos aplicados:** Python, extração de HTML, automação de navegador, persistência SQL, tratamento de erros, testes, Git e execução agendada.

O código e os testes são evidências da entrega técnica. Para a apresentação, execute a demonstração e revise o funcionamento para explicar suas etapas e limitações.
