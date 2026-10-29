# TalentRadar AI

Radar privado de vagas com frontend HTML/CSS/JavaScript, API FastAPI e PostgreSQL persistente.

## Deploy na Vercel

O projeto usa o entrypoint FastAPI em `index.py`. O antigo `app.py` era uma interface Streamlit foi removido do caminho de deploy para não disparar a detecção Python errada.

### Variáveis obrigatórias em Vercel → Settings → Environment Variables

- `APP_PASSWORD`: senha forte para entrar na aplicação (recomendo pelo menos 16 caracteres).
- `SESSION_SECRET`: segredo aleatório de pelo menos 32 caracteres, usado para assinar sessões.
- `DATABASE_URL`: string de conexão PostgreSQL de um serviço persistente, por exemplo Supabase ou Neon. Use endpoint compatível com conexões serverless/pooling se o provedor oferecer.

Não coloque esses valores no GitHub nem no código. Depois de configurar, faça redeploy.

### Banco de dados

A API cria a tabela `jobs` e o índice na primeira requisição que acessa o banco. Os dados ficam no PostgreSQL, não no disco efêmero da função Vercel. Se `DATABASE_URL` não estiver configurada, a API retorna um erro explícito em vez de fingir que salvou dados.

### Endpoints

- `GET /api/health` — status básico (público; informa apenas se DATABASE_URL está definida).
- `POST /api/login` — valida APP_PASSWORD e define cookie de sessão HttpOnly.
- `POST /api/logout` — encerra a sessão no navegador.
- `GET /api/session` — verifica sessão.
- `GET /api/jobs` — lista vagas autenticadas; aceita `q`, `categoria`, `fit_min`, `limit`.
- `POST /api/jobs` — cadastra uma vaga.
- `DELETE /api/jobs/{id}` — exclui uma vaga.

## Desenvolvimento local

Python 3.12+ recomendado:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Defina as três variáveis de ambiente e rode:

```bash
uvicorn index:app --reload
```

Abra http://127.0.0.1:8000.

## Limitações conhecidas

- Esta versão não faz scraping automático. O módulo antigo `job_sources.py`, que continha vagas demonstrativas e contatos de exemplo, foi removido para evitar dados fictícios no repositório.
- A aderência é informada pelo usuário ao cadastrar a vaga; não é uma avaliação automática de currículo nesta versão.
- Configure proteção contra tentativas repetidas de login e mantenha a senha/segredo fortes. Para uso multiusuário, implemente identidade individual e controle de acesso por usuário.