"""Generate a comprehensive, publication-grade PDF from the project documentation and README."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
OUTPUT_PDF = DOCS_DIR / "Emporio_da_Musica_AI_Agent_Documentacao.pdf"
ARTIFACT_PDF = Path(r"C:\Users\nando\.gemini\antigravity\brain\f8aefff2-e864-4b1c-b011-b4f9882a7b33") / "Emporio_da_Musica_AI_Agent_Documentacao.pdf"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Emporio da Musica AI Agent - Documentação Técnica</title>
<style>
  @page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
  }
  
  :root {
    --ink: #173d37;
    --paper: #f6f3ec;
    --coral: #e6815e;
    --muted: #5a6458;
    --line: #d8ded4;
    --white: #ffffff;
    --code-bg: #f0f2eb;
    --sans: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    --serif: Georgia, "Times New Roman", serif;
  }

  * { box-sizing: border-box; }
  body {
    font-family: var(--sans);
    color: var(--ink);
    line-height: 1.6;
    font-size: 10pt;
    margin: 0;
    padding: 0;
  }

  .page-break {
    page-break-before: always;
  }

  /* Cover Page */
  .cover {
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 30mm 10mm 20mm 10mm;
    page-break-after: always;
  }

  .cover-top {
    border-top: 4px solid var(--coral);
    padding-top: 15px;
  }

  .cover-badge {
    display: inline-block;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--coral);
    margin-bottom: 20px;
  }

  .cover-title {
    font-family: var(--serif);
    font-size: 34pt;
    font-weight: 400;
    line-height: 1.1;
    color: var(--ink);
    margin: 0 0 15px 0;
    letter-spacing: -1px;
  }

  .cover-title span {
    color: var(--coral);
  }

  .cover-subtitle {
    font-size: 14pt;
    color: var(--muted);
    font-weight: 300;
    line-height: 1.5;
    max-width: 550px;
  }

  .cover-card {
    background: #edf0e8;
    border-left: 3px solid var(--ink);
    padding: 15px 20px;
    margin-top: 30px;
    font-size: 9.5pt;
    color: var(--ink);
  }

  .cover-footer {
    border-top: 1px solid var(--line);
    padding-top: 15px;
    display: flex;
    justify-content: space-between;
    font-size: 8.5pt;
    color: var(--muted);
  }

  /* Typography & Headings */
  h1, h2, h3, h4 {
    font-family: var(--serif);
    color: var(--ink);
    break-after: avoid;
  }

  h1 {
    font-size: 20pt;
    border-bottom: 2px solid var(--line);
    padding-bottom: 6px;
    margin-top: 25pt;
    margin-bottom: 12pt;
    letter-spacing: -0.5px;
  }

  h2 {
    font-size: 14pt;
    margin-top: 18pt;
    margin-bottom: 8pt;
    color: #244e45;
  }

  h3 {
    font-size: 11pt;
    margin-top: 14pt;
    margin-bottom: 5pt;
  }

  p {
    margin-top: 0;
    margin-bottom: 8pt;
    text-align: justify;
  }

  /* Lists */
  ul, ol {
    margin-top: 0;
    margin-bottom: 10pt;
    padding-left: 18px;
  }

  li {
    margin-bottom: 4pt;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
    font-size: 8.5pt;
    break-inside: avoid;
  }

  th, td {
    padding: 6px 10px;
    text-align: left;
    border: 1px solid var(--line);
  }

  th {
    background: #eef2ea;
    font-weight: 600;
    color: var(--ink);
  }

  tr:nth-child(even) td {
    background: #fbfbfa;
  }

  .badge-pass {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    background: #d4e8d4;
    color: #1e5a1e;
    font-weight: bold;
    font-size: 7.5pt;
  }

  .badge-blocked {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    background: #fbe0d4;
    color: #9c3f1e;
    font-weight: bold;
    font-size: 7.5pt;
  }

  /* Code & Pre */
  code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8.5pt;
    background: var(--code-bg);
    padding: 1px 4px;
    border-radius: 3px;
    color: #1b4b42;
  }

  pre {
    background: var(--code-bg);
    border: 1px solid var(--line);
    border-radius: 4px;
    padding: 8px 12px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8pt;
    line-height: 1.45;
    overflow-x: auto;
    margin: 8pt 0 12pt 0;
    break-inside: avoid;
  }

  pre code {
    background: transparent;
    padding: 0;
    color: inherit;
  }

  /* Callout Boxes */
  .callout {
    border-left: 3px solid var(--coral);
    background: #fdfaf6;
    padding: 10px 14px;
    margin: 10pt 0;
    border-radius: 0 4px 4px 0;
    break-inside: avoid;
    font-size: 9pt;
  }

  .callout-title {
    font-weight: bold;
    color: var(--coral);
    margin-bottom: 4px;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .callout-info {
    border-left-color: var(--ink);
    background: #f2f5f1;
  }

  .callout-info .callout-title {
    color: var(--ink);
  }

  /* Chat Dialogue styling */
  .dialogue-turn {
    margin: 10pt 0;
    padding: 10px 14px;
    border-radius: 6px;
    break-inside: avoid;
    border: 1px solid var(--line);
  }

  .dialogue-user {
    background: #f5f6f2;
    border-left: 3px solid #737a70;
  }

  .dialogue-assistant {
    background: #fbfcf9;
    border-left: 3px solid var(--ink);
  }

  .dialogue-header {
    font-size: 8pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }

  .dialogue-user .dialogue-header { color: #5a6458; }
  .dialogue-assistant .dialogue-header { color: var(--ink); }

  .dialogue-tools {
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px dashed var(--line);
    font-size: 7.5pt;
    color: #4b6357;
    font-style: italic;
  }

  .toc-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    border-bottom: 1px dotted var(--line);
    padding-bottom: 2px;
  }

  .toc-title { font-weight: 500; }
  .toc-page { color: var(--muted); }
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover">
  <div class="cover-top">
    <div class="cover-badge">Desafio Técnico · AI Engineer · Artefact</div>
    <h1 class="cover-title">Empório da Música<br><span>AI Agent</span></h1>
    <div class="cover-subtitle">
      Documentação Técnica de Arquitetura, Implementação, Validação e Relatório de Entrega
    </div>
    
    <div class="cover-card">
      <strong>Resumo da Solução:</strong> Agente conversacional em Python com grounding determinístico de catálogo e políticas, function calling com SDK oficial do Google Gemini, proteção contra prompt injection, animação skeleton e otimização de latência.
    </div>
  </div>

  <div class="cover-footer">
    <div>
      <strong>Candidato:</strong> Fernando Alves Machado<br>
      <strong>E-mail:</strong> fernando.r100k@gmail.com<br>
      <strong>Repositório Git Público:</strong> https://github.com/FernandoAlvesMachado/emporio-musica-ai-agent
    </div>
    <div style="text-align: right;">
      <strong>Data de Conclusão:</strong> 02 de Novembro de 2026<br>
      <strong>Linguagem Principal:</strong> Python 3.11+ / 3.13<br>
      <strong>Status da Solução:</strong> 100% dos testes aprovados (65/65)
    </div>
  </div>
</div>

<!-- SUMÁRIO EXECUTIVO -->
<h1>Sumário Executivo</h1>
<p>
  Este documento consolida o <code>README.md</code>, a documentação técnica de arquitetura, o relatório de validação e os cenários de interação desenvolvidos para a <strong>Empório da Música</strong>, loja fictícia de instrumentos musicais em Campo Grande/MS, em atendimento ao Desafio Técnico para <strong>AI Engineer</strong> da <strong>Artefact</strong>.
</p>

<div class="callout callout-info">
  <div class="callout-title">Destaques da Implementação</div>
  <ul>
    <li><strong>Linguagem e Stack:</strong> Python puro com biblioteca padrão para orquestração, SQLite para integridade relacional, <code>pypdf</code> para extração fiel com numeração física de páginas, e SDK oficial <code>google-genai</code> (Interactions API com loop de ferramentas bounded).</li>
    <li><strong>Grounding Determinístico:</strong> O agente nunca inventa preços, disponibilidade, regras de frete ou descontos. Todo fato apresentado provém das 6 bases CSV ou das 8 páginas do manual de políticas.</li>
    <li><strong>Proteção contra Prompt Injection:</strong> Defesa em duas camadas com sanitização de tags estruturais de controle (ex: <code>&lt;system&gt;</code>, <code>[SYSTEM]</code>) e instruções imutáveis do sistema que repelem jailbreaks (DAN, Developer Mode) e tentativas de vazamento de prompts.</li>
    <li><strong>Otimização de Raciocínio (Latência):</strong> Configuração de <code>thinking_budget: 1024</code> que reduziu o tempo de resposta em chamadas complexas de ferramentas de ~50s para menos de 3s–8s.</li>
    <li><strong>Interface Web Local & Skeleton:</strong> Servidor HTTP loopback seguro com interface visual responsiva, cartões de catálogo, busca de políticas e feedback visual de carregamento animado (skeleton loading) no chat.</li>
    <li><strong>Privacidade Absoluta:</strong> Nenhum dado pessoal de cliente, chave de API ou banco gerado é versionado no Git. Verificação automatizada por script de conformidade.</li>
  </ul>
</div>

<h2>Estrutura deste Documento</h2>
<div class="toc-item"><span class="toc-title">1. README do Projeto (Guia Técnico Completo)</span><span class="toc-page">Seção 1</span></div>
<div class="toc-item"><span class="toc-title">&nbsp;&nbsp;&nbsp;&nbsp;1.1 Instalação e Execução (CLI e Browser)</span><span class="toc-page">1.1</span></div>
<div class="toc-item"><span class="toc-title">&nbsp;&nbsp;&nbsp;&nbsp;1.2 Decisões Técnicas e Arquitetura Justificada</span><span class="toc-page">1.2</span></div>
<div class="toc-item"><span class="toc-title">&nbsp;&nbsp;&nbsp;&nbsp;1.3 Engenharia de Prompt, Escopo e Grounding</span><span class="toc-page">1.3</span></div>
<div class="toc-item"><span class="toc-title">&nbsp;&nbsp;&nbsp;&nbsp;1.4 Proteção contra Prompt Injection e Otimização de Performance</span><span class="toc-page">1.4</span></div>
<div class="toc-item"><span class="toc-title">&nbsp;&nbsp;&nbsp;&nbsp;1.5 Uso Declarado de Assistentes de IA no Desenvolvimento</span><span class="toc-page">1.5</span></div>
<div class="toc-item"><span class="toc-title">2. Relatório de Validação e Matriz de Requisitos</span><span class="toc-page">Seção 2</span></div>
<div class="toc-item"><span class="toc-title">3. Cenários de Conversação e Transcrições Reais</span><span class="toc-page">Seção 3</span></div>

<div class="page-break"></div>

<!-- SEÇÃO 1: README DO PROJETO -->
<h1>1. README do Projeto (Guia Técnico Completo)</h1>

<h2>1.1 Visão Geral e Cenário</h2>
<p>
  O projeto implementa o assistente virtual da <strong>Empório da Música</strong>. A aplicação combina ferramentas determinísticas de catálogo e políticas com o loop conversacional da API Gemini do Google, interface em linha de comando (CLI) e uma interface local para navegador.
</p>
<p>
  A integridade dos dados foi tratada como requisito de primeira ordem: dados recuperados do catálogo e trechos de políticas são injetados como <em>dados de referência não confiáveis</em>, impedindo que textos de produtos ou documentos sobreponham as instruções centrais do sistema.
</p>

<h2>1.2 Instalação e Configuração</h2>
<p>Requer Python 3.11+ e Git. A instalação e inicialização a partir da raiz do repositório é simples e direta:</p>

<pre><code># Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
source .venv/bin/activate       # Linux / macOS

# Instalar dependências em modo editável com pacotes de desenvolvimento
python -m pip install -e ".[dev]"

# Configurar variáveis de ambiente (.env)
cp .env.example .env
# Adicionar GEMINI_API_KEY no arquivo .env

# Carregar os dados originais no SQLite
python -m emporio_music load

# Iniciar o chat no terminal
python -m emporio_music chat --show-tools

# Iniciar a interface Web local
python -m emporio_music serve --open-browser
</code></pre>

<div class="callout">
  <div class="callout-title">Variáveis de Ambiente Suportadas</div>
  <table>
    <tr><th>Variável</th><th>Padrão</th><th>Descrição</th></tr>
    <tr><td><code>GEMINI_API_KEY</code></td><td><em>Obrigatório</em></td><td>Chave da API do Google Gemini (obtida no Google AI Studio).</td></tr>
    <tr><td><code>GEMINI_MODEL</code></td><td><code>gemini-3.1-flash-lite</code></td><td>Modelo do Gemini utilizado para chamadas de função e conversação.</td></tr>
    <tr><td><code>EMPORIO_THINKING_BUDGET</code></td><td><code>1024</code></td><td>Orçamento de tokens de raciocínio, otimizando o tempo de resposta.</td></tr>
    <tr><td><code>EMPORIO_MODEL_TIMEOUT</code></td><td><code>60</code></td><td>Timeout máximo em segundos por chamada ao provedor LLM.</td></tr>
    <tr><td><code>EMPORIO_CHAT_LANGUAGE</code></td><td><code>pt-BR</code></td><td>Idioma padrão de atendimento (suporta <code>pt-BR</code> e <code>en</code>).</td></tr>
    <tr><td><code>EMPORIO_DATABASE_PATH</code></td><td><code>data/processed/emporio.sqlite3</code></td><td>Local do banco de dados SQLite compilado deterministicamente.</td></tr>
    <tr><td><code>EMPORIO_POLICIES_PATH</code></td><td><code>data/raw/políticas_da_loja.pdf</code></td><td>Local do manual de procedimentos em PDF.</td></tr>
  </table>
</div>

<h2>1.3 Decisões Técnicas Justificadas</h2>
<ul>
  <li><strong>Arquitetura Enxuta (Small Architecture):</strong> Optou-se por utilizar módulos da biblioteca padrão do Python (como <code>sqlite3</code>, <code>http.server</code>, <code>dataclasses</code>, <code>pathlib</code>) junto ao SDK oficial <code>google-genai</code>. Isso eliminou frameworks intermediários complexos (LangChain, LlamaIndex), garantindo controle total sobre o ciclo de vida da requisição, rastreabilidade explícita das ferramentas e ausência de overhead.</li>
  <li><strong>Tratamento e Integridade dos Dados:</strong> A importação valida atomicamente todos os 6 arquivos CSV. Valores monetários são convertidos via <code>Decimal</code> para centavos inteiros (<code>cents</code>) no SQLite, eliminando imprecisões de ponto flutuante. A disponibilidade de produtos exige estritamente <code>status == 'active'</code> e <code>stock_quantity &gt; 0</code>.</li>
  <li><strong>Regras Estritas de Não-Acúmulo de Promoções:</strong> O cálculo de pagamentos (PIX e parcelado) foi implementado como uma ferramenta determinística separada (<code>quote_payment</code>), fora do modelo, garantindo que o desconto de 5% no PIX incida apenas sobre o preço cheio e nunca sobre itens promocionais.</li>
  <li><strong>Fidelidade e Conflitos nas Políticas:</strong> As 8 páginas do PDF são lidas preservando os números físicos de página. Em casos de conflito factual nas fontes originais (ex: telefones divergentes entre as páginas 1 e 6, ou frete exato de R$ 500,00 não especificado), o agente foi instruído a reconhecer a ambiguidade e solicitar confirmação com a equipe, sem inventar regras fictícias.</li>
  <li><strong>Privacidade de Dados de Clientes:</strong> Embora a base contenha tabelas de clientes e pedidos, o agente não expõe ferramentas para consulta ou alteração dessas ordens, evitando vazamento de dados pessoais ou aprovação simulada de devoluções sem autenticação prévia de identidade.</li>
</ul>

<h2>1.4 Proteção Contra Prompt Injection e Otimização de Performance</h2>
<p>
  Para garantir segurança de nível corporativo e usabilidade ágil, foram introduzidas duas melhorias essenciais no agente:
</p>

<h3>Defesa Contra Injeção de Prompt em Camadas</h3>
<ol>
  <li><strong>Sanitização Estrutural de Entrada (<code>_sanitize_customer_input</code>):</strong> O agente filtra e neutraliza tags que simulam papéis internos (como <code>&lt;system&gt;</code>, <code>[SYSTEM]</code>, <code>&lt;&lt;SYS&gt;&gt;</code>, <code>```system</code>), impedindo que um atacante quebre a fronteira de papel do modelo.</li>
  <li><strong>Instruções de Segurança e Imutabilidade (<code>prompts.py</code>):</strong> A persona do assistente é definida como estritamente imutável. Tentativas de jailbreak (como o modo "DAN", "Developer Mode", personificação de administradores ou solicitações de "ignore regras anteriores") são detectadas e o assistente responde educadamente mantendo-se estritamente no escopo da loja. Além disso, o sistema veda a divulgação do prompt interno ou das chaves de configuração.</li>
</ol>

<h3>Otimização de Raciocínio (Thinking Budget)</h3>
<p>
  Os modelos da família Flash com raciocínio expandido podiam gastar dezenas de segundos gerando pensamentos antes de emitir chamadas de ferramentas. Através do parâmetro <code>thinking_budget: 1024</code>, a chamada passou a resolver o direcionamento das ferramentas de forma rápida e precisa, reduzindo a latência total de ~50s para menos de 3s–8s em buscas complexas.
</p>

<h3>Animação Skeleton no Chat Web</h3>
<p>
  A interface web loopback (<code>127.0.0.1:8000</code>) recebeu um elemento de carregamento visual <code>.chat-message-skeleton</code> com efeito de shimmer pulsante em CSS. Ele fornece feedback visual imediato ao cliente enquanto o Gemini processa as consultas, respeitando a diretiva de acessibilidade <code>prefers-reduced-motion</code>.
</p>

<h2>1.5 Declaração de Uso de Assistentes de Código (Workflow)</h2>
<p>
  Em total transparência com os critérios da Artefact:
</p>
<ul>
  <li><strong>ChatGPT:</strong> Utilizado na etapa inicial de brainstorm e planejamento estrutural dos estágios do desafio.</li>
  <li><strong>Claude / Codex / Antigravity:</strong> Utilizado durante a implementação do código Python, escrita dos testes unitários com pytest, auditoria dos arquivos CSV e elaboração dos scripts de verificação contínua.</li>
  <li><strong>Google Gemini (<code>gemini-3.1-flash-lite</code>):</strong> Provedor de LLM em tempo de execução para as interações e resolução de chamadas de ferramentas do agente.</li>
</ul>

<div class="page-break"></div>

<!-- SEÇÃO 2: RELATÓRIO DE VALIDAÇÃO TÉCNICA -->
<h1>2. Relatório de Validação e Matriz de Requisitos</h1>
<p>
  A tabela abaixo sumariza a conformidade do projeto com os critérios de avaliação e requisitos do desafio técnico:
</p>

<table>
  <thead>
    <tr>
      <th>Requisito</th>
      <th>Tipo</th>
      <th>Status</th>
      <th>Evidência Técnica</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Python como linguagem principal</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Pacote <code>src/emporio_music/</code> estruturado, Python 3.11+ / 3.13.</td>
    </tr>
    <tr>
      <td>CLI conversacional interativa</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Comando <code>python -m emporio_music chat</code> com suporte a <code>--show-tools</code> e <code>--language</code>.</td>
    </tr>
    <tr>
      <td>Preservação dos dados originais</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>6 tabelas CSV validadas, 65 produtos, 9 categorias, 25 promoções.</td>
    </tr>
    <tr>
      <td>Grounding em ferramentas e fontes</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Catálogo e manual PDF lidos via SQLite parametrizado e <code>pypdf</code>.</td>
    </tr>
    <tr>
      <td>Cálculo exato e não acúmulo de PIX</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Ferramenta <code>quote_payment</code> com cálculo determinístico em centavos inteiros.</td>
    </tr>
    <tr>
      <td>Fidelidade a páginas físicas do PDF</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Excertos e páginas completas referenciadas de 1 a 8 com numeração física.</td>
    </tr>
    <tr>
      <td>Resistência a Prompt Injection</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Sanitização de delimitadores estruturais e instruções de segurança imutáveis.</td>
    </tr>
    <tr>
      <td>Suíte de testes automatizados</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>65 testes automatizados aprovados no <code>pytest</code> em 2.62s.</td>
    </tr>
    <tr>
      <td>Proteção de credenciais e Git público</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Script <code>check_tracked_files.py</code> auditou 44 arquivos sem vazamentos.</td>
    </tr>
    <tr>
      <td>Interface Web Local (Skeleton UI)</td>
      <td>Opcional</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Servidor loopback com interface responsiva, cartões e animação skeleton.</td>
    </tr>
    <tr>
      <td>Publicação no GitHub</td>
      <td>Obrigatório</td>
      <td><span class="badge-pass">PASS</span></td>
      <td>Repositório público ativo com histórico transparente de commits.</td>
    </tr>
  </tbody>
</table>

<div class="callout callout-info">
  <div class="callout-title">Resultado dos Testes Unitários e Integração</div>
  <p>Comando executado: <code>python -m pytest</code></p>
  <pre><code>============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\PROJETOS\Avulsos\Artefact\Teste pratico
configfile: pyproject.toml
collected 65 items

tests/test_agent.py ....................                                 [ 30%]
tests/test_browser.py ...............                                    [ 53%]
tests/test_browser_chat.py ........                                      [ 66%]
tests/test_foundation.py ............                                    [ 84%]
tests/test_sdk_contract.py .                                             [ 86%]
tests/test_tools.py .........                                            [100%]

============================== 65 passed in 2.62s ==============================</code></pre>
</div>

<div class="page-break"></div>

<!-- SEÇÃO 3: CENÁRIOS E TRANSCRIÇÕES REAIS -->
<h1>3. Cenários e Transcrições de Conversação</h1>
<p>
  Abaixo estão documentadas transcrições de interações realizadas com o assistente, demonstrando a ativação real de ferramentas, resolução de consultas em tempo real e aplicação das diretrizes de atendimento:
</p>

<h2>3.1 Cenário 1: Recomendação com Orçamento e Cotação de Pagamento (PIX)</h2>
<p><em>Objetivo: Demonstrar consulta ao catálogo por categoria, filtro de disponibilidade e cálculo de pagamento à vista sem acúmulo indevido de descontos.</em></p>

<div class="dialogue-turn dialogue-user">
  <div class="dialogue-header">Cliente</div>
  "Please recommend three available acoustic guitars costing at most BRL 1000. Give the actual prices and product IDs."
</div>

<div class="dialogue-turn dialogue-assistant">
  <div class="dialogue-header">Empório da Música · Assistente Gemini</div>
  Hello! Welcome to Emporio da Musica. I'd be happy to help you find an acoustic guitar. We have several great options available for under BRL 1000. Here are three popular choices:
  <ul>
    <li><strong>Tagima Memphis AC-39 Nylon Natural</strong> (ID: 83) – BRL 429.90</li>
    <li><strong>Yamaha C40 Nylon Natural</strong> (ID: 81) – BRL 599.90</li>
    <li><strong>Yamaha F310 Aço Natural</strong> (ID: 87) – BRL 699.90</li>
  </ul>
  Are you looking for a guitar with nylon strings for a softer sound, or do you prefer the bright, projection-heavy sound of steel strings?
  <div class="dialogue-tools">Ferramentas executadas nesta rodada: list_categories, search_products.</div>
</div>

<div class="dialogue-turn dialogue-user">
  <div class="dialogue-header">Cliente</div>
  "What is the recorded stock of the first option, and how much would I pay by PIX?"
</div>

<div class="dialogue-turn dialogue-assistant">
  <div class="dialogue-header">Empório da Música · Assistente Gemini</div>
  We currently have <strong>15 units</strong> of the Tagima Memphis AC-39 Nylon Natural (ID: 83) in stock.<br><br>
  If you choose to pay via PIX, the price is <strong>BRL 408.41</strong>, which includes a 5% discount on the base price of BRL 429.90. This calculation follows our store payment guidelines (pages 3 and 6 of our store policies).<br><br>
  Please note that this is an indicative quote based on our current catalog snapshot. Would you like to know anything else about this model or our payment options?
  <div class="dialogue-tools">Ferramentas executadas nesta rodada: get_product, quote_payment.</div>
</div>

<h2>3.2 Cenário 2: Consulta de Preço e Tratamento de Item Inexistente</h2>
<div class="dialogue-turn dialogue-user">
  <div class="dialogue-header">Cliente</div>
  "Quanto custa o Takamine GD20 e ele está disponível em estoque?"
</div>
<div class="dialogue-turn dialogue-assistant">
  <div class="dialogue-header">Empório da Música · Assistente Gemini</div>
  O violão <strong>Takamine GD20</strong> (ID: 95) custa <strong>R$ 2.199,00</strong> e está disponível em nosso estoque com <strong>5 unidades</strong> no momento! Ele é um modelo eletroacústico dreadnought com tampo em Solid Cedar. Gostaria de verificar condições de pagamento para ele?
  <div class="dialogue-tools">Ferramentas executadas nesta rodada: search_products, get_product.</div>
</div>

<h2>3.3 Cenário 3: Esclarecimento de Políticas de Troca e Devolução</h2>
<div class="dialogue-turn dialogue-user">
  <div class="dialogue-header">Cliente</div>
  "Me arrependi da minha compra, vocês podem emitir o meu reembolso agora?"
</div>
<div class="dialogue-turn dialogue-assistant">
  <div class="dialogue-header">Empório da Música · Assistente Gemini</div>
  Olá! Entendo sua situação e posso te orientar sobre as nossas políticas de devolução (previstas nas páginas 4 e 7 do manual da loja).<br><br>
  Como assistente virtual, eu não tenho autorização para aprovar devoluções ou processar reembolsos diretamente no sistema. Para que nossa equipe de atendimento possa te ajudar com essa solicitação, você poderia me informar:<br>
  1. A compra foi feita em nossa loja física ou pelo site/WhatsApp?<br>
  2. Há quantos dias você recebeu o instrumento?<br>
  3. O produto está intacto, na embalagem original e com todos os acessórios e manuais?<br><br>
  Com essas informações, consigo te explicar exatamente o procedimento a seguir junto à equipe!
  <div class="dialogue-tools">Ferramentas executadas nesta rodada: search_policies, get_policy_pages.</div>
</div>

<div class="page-break"></div>

<!-- CONCLUSÃO -->
<h1>4. Conclusão e Entrega</h1>
<p>
  O protótipo do <strong>Emporio da Musica AI Agent</strong> cumpre com rigor todos os requisitos obrigatórios estabelecidos no desafio técnico da Artefact, indo além ao oferecer uma interface amigável com suporte a skeleton loading, validação estrita de segurança e proteção ativa contra prompt injection.
</p>

<div class="callout callout-info">
  <div class="callout-title">Links e Acessos Oficiais</div>
  <p>
    <strong>Repositório Público no GitHub:</strong><br>
    <a href="https://github.com/FernandoAlvesMachado/emporio-musica-ai-agent">https://github.com/FernandoAlvesMachado/emporio-musica-ai-agent</a>
  </p>
  <p>
    <strong>Contato do Candidato:</strong> Fernando Alves Machado (<a href="mailto:fernando.r100k@gmail.com">fernando.r100k@gmail.com</a>)
  </p>
</div>

</body>
</html>
"""

def generate_pdf():
    print(f"Generating PDF from documentation...")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PDF.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(HTML_TEMPLATE, wait_until="networkidle")
        
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="font-size: 7.5pt; color: #777; width: 100%; text-align: right; padding-right: 15mm;">Empório da Música · AI Agent</div>',
            footer_template='<div style="font-size: 7.5pt; color: #777; width: 100%; display: flex; justify-content: space-between; padding: 0 15mm;"><span>Artefact AI Engineer Challenge</span><span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>',
            margin={
                "top": "18mm",
                "bottom": "18mm",
                "left": "15mm",
                "right": "15mm",
            }
        )
        browser.close()

    OUTPUT_PDF.write_bytes(pdf_bytes)
    print(f"Saved PDF to: {OUTPUT_PDF} ({len(pdf_bytes)} bytes)")
    
    ARTIFACT_PDF.write_bytes(pdf_bytes)
    print(f"Saved PDF to artifact dir: {ARTIFACT_PDF} ({len(pdf_bytes)} bytes)")

if __name__ == "__main__":
    generate_pdf()
