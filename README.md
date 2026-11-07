AliceMind

AliceMind é um assistente pessoal de IA para Windows, desenvolvido em Python. Ele reúne uma interface de conversa, análise de arquivos, organização de informações e execução supervisionada de algumas tarefas em projetos.

O AliceMind funciona como interface e integração: ele se conecta a um serviço compatível com a API de chat da OpenAI, como o OmniRoute. Não inclui modelos de IA e não inicia nem configura o OmniRoute. A disponibilidade e a capacidade de cada recurso dependem do endpoint, do modelo e das credenciais configuradas.

Importante: prompts, arquivos, perfil ou capturas de tela podem ser enviados ao serviço de IA quando você pede uma análise. Confira as políticas de privacidade do provedor antes de enviar informações pessoais ou confidenciais.

Índice
O que o AliceMind oferece
Chat e histórico
Arquivos, documentos e imagens
Widget de análise de tela
Central do agente
Tarefas locais
Pesquisa web
Central global de vagas
Otimizador de currículo
Execução autônoma supervisionada
Como o AliceMind usa a IA
Requisitos
Instalação e execução pelo código-fonte
Configuração
Dados locais e privacidade
Testes
Criar o executável para Windows
Estrutura do projeto
Limitações conhecidas
Licença
O que o AliceMind oferece
O aplicativo reúne quatro áreas principais:

Chat com IA: conversa com um modelo configurado pelo usuário, incluindo histórico, favoritos e anexos.
Organização local: perfil, memórias, documentos indexados, fontes consultadas e tarefas armazenados no computador.
Ferramentas de produtividade: análise e comparação de documentos, pesquisa web, currículo e oportunidades profissionais.
Fluxos supervisionados: planejamento de tarefas de projeto com ferramentas limitadas, autorização explícita e apresentação dos resultados.
O aplicativo também tem um widget flutuante que captura a tela somente quando você envia uma pergunta.

Chat e histórico
Na tela Chat principal, você pode conversar com o modelo configurado e anexar arquivos à mensagem. As conversas podem ser:

Criadas pelo botão Nova conversa.
Pesquisadas pelo título ou conteúdo.
Fixadas no histórico.
Apagadas após confirmação.
Exportadas em Markdown ou texto.
Continuadas depois de reabrir o aplicativo.
O AliceMind oferece prompts iniciais para explicar assuntos, criar ideias, revisar textos e analisar código. Há atalhos integrados e também favoritos personalizados que podem ser salvos, editados e excluídos. Os atalhos integrados não podem ser substituídos.

Memória como contexto do chat
A opção Usar memória local no chat controla se informações locais relevantes podem acompanhar uma solicitação ao modelo. Quando habilitada, o AliceMind pode incluir:

O perfil salvo.
Até 10 memórias explícitas recentes.
Trechos de até três documentos que correspondam à pergunta.
O contexto combinado é limitado a 8.000 caracteres. Desative essa opção se não quiser incluir esse contexto na conversa.

Arquivos, documentos e imagens
O AliceMind aceita arquivos de até 10 MB por arquivo.

Arquivos de texto e documentos
O sistema extrai texto de:

Arquivos de texto e código, incluindo Python (.py) e SQL (.sql).
PDF com texto selecionável.
DOCX.
XLSX.
PPTX.
O conteúdo extraído pode ser enviado junto com uma mensagem de chat ou indexado na Central do agente para busca local posterior. A indexação limita o texto extraído de cada documento a 10 Mi caracteres.

O extrator de documentos Office lê conteúdo textual de documentos, planilhas e slides; não é uma conversão completa de todos os elementos e formatações do arquivo. Um PDF que seja apenas uma imagem, sem camada de texto, pode não produzir conteúdo extraível.

Imagens
Imagens PNG, JPG, JPEG, GIF e WebP podem ser analisadas por modelos com suporte a visão. O AliceMind valida o formato e o tamanho do arquivo antes de montar a solicitação.

É possível definir um modelo para imagens separadamente do modelo geral. Sem um modelo de visão configurado, o modelo geral — inclusive auto — pode não aceitar imagens. O tempo limite de resposta para uma mensagem com imagem é maior que o usado para texto.

Comparação de documentos
A Central do agente permite carregar duas versões de um documento compatível e visualizar:

Quantidade de linhas adicionadas.
Quantidade de linhas removidas.
Diferenças no formato unified diff.
Cada texto pode ter até 500.000 caracteres. A tela mostra uma prévia limitada; se o diff for maior, é possível baixar o arquivo completo.

Widget de análise de tela
O botão Abrir assistente de tela inicia uma janela separada, móvel e redimensionável. Ela possui um campo de pergunta, um botão para capturar e analisar, uma área de resposta e um botão de fechar da própria janela.

O fluxo é pontual, não contínuo:

Você abre o widget pelo AliceMind.
Escreve o que quer saber sobre a tela.
Clica em Capturar tela e analisar.
O widget se oculta brevemente enquanto a captura é feita.
A imagem é reduzida em memória e enviada, junto com a pergunta, ao endpoint configurado.
A resposta aparece no próprio widget.
Você fecha a janela quando terminar.
O widget não fica tirando capturas em segundo plano. Ele também não grava a imagem em um arquivo local. A imagem capturada, no entanto, é transmitida ao provedor de IA para análise. O tratamento dos dados pelo provedor depende da política desse serviço.

A imagem é reduzida para no máximo 1600 pixels no lado maior, com tentativas de mantê-la abaixo de 5 MB. O widget pode usar até 10 mensagens recentes de texto como contexto, mas não mantém as imagens anteriores como parte do histórico da conversa. É necessário um modelo com suporte a visão.

Central do agente
A Central do agente reúne perfil, memórias, documentos, comparação de arquivos, busca web, execução autônoma e o gerenciamento de tarefas.

Perfil de longo prazo
Você pode escrever e salvar um perfil para o AliceMind considerar nas conversas em que a memória local estiver habilitada. O perfil é armazenado localmente e tem limite de 10.000 caracteres.

Memórias explícitas
Memórias são informações ou preferências que você escolhe salvar para uso posterior. Cada memória pode ter até 4.000 caracteres. É possível listar e excluir memórias salvas.

Documentos indexados
Você pode indexar documentos para pesquisa local, consultar trechos correspondentes e excluir documentos indexados. A pesquisa é feita localmente por correspondência de termos; não é uma busca semântica vetorial.

Os documentos indexados não são enviados automaticamente só por serem armazenados. Porém, quando a memória está habilitada no chat, trechos relevantes podem ser incluídos no contexto enviado ao modelo.

Log de atividade
A Central do agente mostra eventos recentes, como ações de perfil, documentos, tarefas e pesquisas. O log registra metadados da atividade e foi projetado para não armazenar o conteúdo integral das conversas.

Tarefas locais
As tarefas podem ser criadas e mantidas na Central do agente. Cada tarefa tem:

Título.
Status: Pendente, Em andamento ou Concluída.
Prioridade: Baixa, Média ou Alta.
Prazo opcional.
As tarefas são armazenadas no banco local. A lista é ordenada por prioridade, prazo e data de criação. O usuário pode atualizar o status, o prazo e a prioridade.

Pesquisa web
A pesquisa web da Central do agente usa a API do Tavily e requer TAVILY_API_KEY ou OMNI_SEARCH_API_KEY.

Antes de enviar uma consulta, a interface pede confirmação explícita. As consultas têm limite de 500 caracteres e a busca pode solicitar até 10 resultados. Os resultados exibem título, conteúdo e link quando fornecidos pelo serviço.

As fontes consultadas são salvas localmente. O sistema aceita para armazenamento apenas links HTTP ou HTTPS válidos, sem credenciais embutidas na URL. O banco mantém até 500 fontes; a interface mostra as 30 mais recentes.

Central global de vagas
A Central global de vagas organiza pesquisas por áreas profissionais e cargos. As áreas disponíveis incluem:

Análise de dados e BI.
Desenvolvimento e automação.
HealthTech e inovação em saúde.
Inteligência artificial e dados.
Qualidade de software e documentação.
Sucesso, operações e gestão ágil.
Você pode escolher as áreas que quer incluir. O AliceMind envia ao modelo um pedido para produzir oportunidades de entrada, levando em conta o perfil profissional salvo quando disponível, e salva o resultado localmente para consulta posterior.

Atenção: essa função pede ao modelo informações atuais, mas o AliceMind não verifica por conta própria se cada vaga está aberta, se os links continuam válidos ou se os requisitos estão corretos. Confira as informações diretamente na página da empresa ou plataforma de candidatura. A Central global de vagas não é a mesma coisa que a pesquisa Tavily da Central do agente.

Otimizador de currículo
O otimizador recebe as informações profissionais fornecidas pelo usuário e um cargo-alvo. O modelo é instruído a reescrever o currículo em português, preservar os fatos informados e não inventar experiência, qualificações ou resultados.

O resultado pode ser baixado como:

Arquivo de texto.
PDF com layout de currículo e suporte a múltiplas páginas.
O gerador de PDF aceita até 50.000 caracteres. Revise nomes, datas, contatos, qualificações e demais informações antes de usar ou compartilhar o currículo.

Execução autônoma supervisionada
Na Central do agente, você pode descrever um pedido, selecionar as capacidades permitidas e solicitar um plano de até 12 etapas. O AliceMind envia o pedido ao modelo, valida o plano recebido e apresenta as etapas e seus resultados.

As capacidades disponíveis são:

Capacidade	O que permite
Pesquisar documentos	Buscar trechos em documentos que já foram indexados localmente.
Pesquisar na web	Enviar uma consulta ao Tavily depois de confirmação explícita.
Criar tarefas	Criar tarefas locais a partir de títulos propostos pelo plano.
Atualizar tarefa	Alterar o status de uma tarefa que tenha correspondência única pelo título.
Redigir texto	Pedir ao modelo que gere um rascunho.
Criar arquivo	Criar um arquivo dentro da pasta de projeto autorizada.
Executar verificações	Rodar as verificações permitidas descritas abaixo.
Limites para alterações em arquivos
O gravador autônomo aceita extensões como .css, .html, .js, .json, .md, .py, .toml, .ts, .txt, .yaml e .yml.

Os caminhos precisam ser relativos e permanecer dentro da pasta autorizada. Pastas como .git, .omni_memory, build, dist e __pycache__, arquivos ocultos e arquivos comuns de credenciais são protegidos. O conteúdo de arquivo tem limite de 100.000 caracteres.

Criar um arquivo novo não é o mesmo que substituir um existente: a substituição exige autorização adicional, exibe uma comparação das alterações e verifica se o arquivo não mudou desde a autorização.

Verificações permitidas
Sintaxe: compila arquivos Python encontrados no projeto para validar sintaxe; não executa esses arquivos.
Testes unitários: executa a suíte encontrada na pasta tests.
Build: executa o build fixo do PyInstaller, se houver omni.spec; pede confirmação porque pode substituir artefatos de build.
A execução de testes roda código presente nos próprios testes do projeto autorizado. Execute essa capacidade somente em projetos cujos testes você considera confiáveis.

O andamento dos fluxos fica salvo localmente. Uma tarefa interrompida pode ser retomada, mas uma etapa pode ter produzido efeitos antes da interrupção. Retomar pode executar essa etapa novamente. Etapas já concluídas não são desfeitas automaticamente.

O AliceMind não oferece execução de comandos arbitrários, exclusão de arquivos, envio de mensagens, candidaturas, publicações, compras ou acesso a contas.

Como o AliceMind usa a IA
As solicitações de conversa passam pelo endpoint compatível com a API de chat configurado. O AliceMind:

Usa um modelo geral definido na barra lateral, com auto como valor inicial.
Pode selecionar um modelo de visão separado quando uma mensagem contém imagem.
Usa tempos limite diferentes para conexão, respostas de texto e respostas com imagens.
Tenta novamente algumas falhas breves de conexão.
Pode reduzir o histórico e o limite de resposta quando o provedor rejeita uma solicitação por tamanho.
Pode repetir uma vez uma resposta HTTP 503 se o provedor indicar um prazo de recuperação de até 60 segundos.
Essas tentativas não garantem que uma solicitação será concluída: o serviço pode continuar indisponível, o modelo pode não suportar o conteúdo ou o provedor pode retornar outro erro.

Requisitos
Windows.
Python 3.14.
Um endpoint de chat compatível com a API da OpenAI, como OmniRoute, iniciado separadamente.
Uma chave para o endpoint, se exigida pelo provedor.
Uma chave Tavily, opcional, para a pesquisa web.
Um modelo com suporte a visão para analisar imagens.
As dependências estão listadas em requirements-build.txt.

Instalação e execução pelo código-fonte
Clone o repositório e entre na pasta do projeto:
git clone https://github.com/nadieleschneider/alicemind.git
Set-Location alicemind

Crie um ambiente virtual e instale as dependências:
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

Configure o endpoint e inicie o aplicativo:
$env:OMNI_API_URL = "http://localhost:20128/v1/chat/completions"

# Defina OMNI_API_KEY somente se o endpoint exigir autenticação.
python -m streamlit run app.py

O app abre no navegador. Inicie o OmniRoute separadamente antes de enviar mensagens.

Configuração
As variáveis abaixo podem ser configuradas no ambiente. Algumas credenciais também podem ser fornecidas em .streamlit/secrets.toml.

Variável	Finalidade
OMNI_API_URL	URL completa do endpoint de chat. O padrão é http://localhost:20128/v1/chat/completions.
OMNI_API_KEY	Chave do endpoint de IA, se ele exigir autenticação.
OMNI_VISION_MODEL	ID de um modelo com suporte a visão.
TAVILY_API_KEY	Chave para a pesquisa web.
OMNI_SEARCH_API_KEY	Nome alternativo aceito para a chave da pesquisa web.
OMNI_MEMORY_DIR	Pasta alternativa para os dados locais.
OMNI_PROJECT_DIR	Pasta de projeto inicial para os fluxos supervisionados.

Exemplo de .streamlit/secrets.toml:
OMNI_API_URL = "http://localhost:20128/v1/chat/completions"
OMNI_API_KEY = "sua-chave"
OMNI_VISION_MODEL = "id-do-modelo-com-visao"
TAVILY_API_KEY = "sua-chave-tavily"

Remova as entradas que não usar. Nunca publique chaves reais, arquivos de secrets, .env, conversas ou bancos de dados.

Dados locais e privacidade
No modo fonte, os dados ficam em .omni_memory/ por padrão. Você pode mudar o local com OMNI_MEMORY_DIR.

No executável Windows, os dados ficam em %LOCALAPPDATA%\Omni\memory. Entre eles estão:

O banco SQLite com perfil, memórias, tarefas, documentos indexados, fontes, favoritos, logs e checkpoints de autonomia.
Arquivos JSON com histórico e estado de conversas.
Arquivos JSON com relatórios salvos da Central global de vagas.
Os dados locais não são criptografados. Não salve senhas ou informações altamente sensíveis.

O AliceMind não envia todos os dados locais automaticamente. O envio acontece de acordo com a ação solicitada: por exemplo, ao enviar uma mensagem, ativar o contexto local, pesquisar na web, otimizar um currículo ou solicitar uma análise de tela.

Testes
Ative o ambiente virtual e execute:
python -m unittest discover -s tests -v

A suíte cobre o núcleo de persistência e extração, arquivos e imagens, serviço de IA, interface, widget, launcher, verificações autônomas e geração de currículo em PDF. Testes automatizados não substituem a validação com o endpoint e os modelos que você pretende usar.

Criar o executável para Windows
O build requer Windows, Python 3.14 e acesso à internet para instalar dependências.

Pelo PowerShell:
.\build_exe.ps1

Ou abra build_exe.cmd com duplo clique.

O resultado será criado em dist\AliceMind\AliceMind.exe. Distribua a pasta dist\AliceMind inteira, não somente o executável.

Ao iniciar o executável, o launcher:

Inicia o servidor Streamlit em 127.0.0.1.
Abre o AliceMind no navegador padrão.
Mantém uma janela de controle na barra de tarefas.
Permite encerrar o servidor pela interface ou pela janela de controle.
O executável não inclui OmniRoute, modelos de IA nem credenciais. Consulte EXECUTAVEL.md para detalhes adicionais.

Estrutura do projeto
alicemind/
├── app.py                   # Interface Streamlit e telas do aplicativo
├── alice_widget.py          # Widget Tkinter para análise pontual da tela
├── agent_core.py            # Persistência, extração, contexto e utilitários
├── agent_executor.py        # Validação de planos, caminhos e verificações
├── core/
│   └── autonomy.py          # Execução autônoma limitada e supervisionada
├── data/
│   └── database.py          # Banco local, conversas e relatórios
├── services/
│   └── omni_service.py      # Chamadas e retentativas do endpoint de IA
├── resume_pdf.py            # Geração de currículo em PDF
├── omni_launcher.py         # Launcher Windows e servidor local
├── omni.spec                # Configuração do PyInstaller
├── requirements-build.txt   # Dependências de execução e build
└── tests/                   # Testes automatizados

Limitações conhecidas
A disponibilidade, a qualidade e o custo das respostas dependem do serviço e do modelo configurados.
auto pode selecionar um modelo sem suporte a visão.
O widget captura a tela inteira disponível à captura padrão do sistema; não oferece seleção de janela ou região.
A Central global de vagas não valida automaticamente se cada anúncio está ativo.
PDFs digitalizados sem texto selecionável podem não ser extraídos.
A extração de documentos é textual; ela não interpreta programas, arquivos compactados enviados pelo usuário, imagens em documentos ou layout completo de Office.
A busca de documentos indexados é local e baseada em termos, não em embeddings.
Os dados locais não têm criptografia.
Uma tarefa autônoma interrompida pode ter efeitos parciais; retomá-la pode repetir a etapa em andamento.
Licença
Distribuído sob a licença MIT. Consulte o arquivo LICENSE.

Licença MIT

Copyright (c) 2026 contribuintes do AliceMind

Por meio deste, é concedida permissão, gratuitamente, a qualquer pessoa que obtenha uma cópia deste software e dos arquivos de documentação associados (o "Software"), para lidar com o Software sem restrições, incluindo, sem limitação, os direitos de usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar e/ou vender cópias do Software, e permitir que pessoas a quem o Software seja fornecido façam o mesmo, sujeitas às seguintes condições:

O aviso de copyright acima e este aviso de permissão devem ser incluídos em todas as cópias ou partes substanciais do Software.

O SOFTWARE É FORNECIDO "NO ESTADO EM QUE SE ENCONTRA", SEM GARANTIA DE QUALQUER TIPO, EXPRESSA OU IMPLÍCITA, INCLUINDO, MAS NÃO SE LIMITANDO ÀS GARANTIAS DE COMERCIABILIDADE, ADEQUAÇÃO A UM DETERMINADO FIM E NÃO VIOLAÇÃO. EM NENHUM CASO OS AUTORES OU DETENTORES DE COPYRIGHT SERÃO RESPONSÁVEIS POR QUALQUER RECLAMAÇÃO, DANOS OU OUTRA RESPONSABILIDADE, SEJA EM AÇÃO CONTRATUAL, DELITO OU OUTRA, DECORRENTE DE, OU








