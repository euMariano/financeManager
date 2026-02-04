# Finance Manager API

API do organizador financeiro (MVP): CRUD de saldo e cards de despesas, cálculo de faixa (vermelho/amarelo/verde) e exportação em planilha.

## Requisitos

- Python 3.10+
- pip

## Instalação

```bash
cd /home/mariano/labs/projects/financeManager
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

## Configuração

Antes de subir em produção, defina uma chave secreta para os tokens JWT:

```bash
export FINANCE_APP_SECRET="uma-chave-bem-segura"
```

Outras variáveis opcionais:

- `FINANCE_COOKIE_SECURE=true` &mdash; exige HTTPS para os cookies (recomendado em produção).
- `FINANCE_COOKIE_SAMESITE=strict|lax|none` &mdash; ajuste de acordo com o cenário.
- `FINANCE_ACCESS_TOKEN_MINUTES` e `FINANCE_REFRESH_TOKEN_MINUTES` &mdash; personalizam a validade dos tokens (padrões: 30 minutos e 7 dias).

> **Nota sobre o banco de dados:** o arquivo `finance_manager.db` (SQLite) recebe colunas novas automaticamente. No entanto, registros criados antes da autenticação não ficam associados a usuários. Para começar do zero, basta remover o arquivo antes de iniciar o servidor.

## Executar

```bash
uvicorn app.main:app --reload
```

- **Frontend:** http://127.0.0.1:8000/ (redireciona para /app/)
- **Documentação da API:** http://127.0.0.1:8000/docs

## Frontend

A interface fica em **http://127.0.0.1:8000/** (ou **http://127.0.0.1:8000/app/**). Para usar:

1. Cadastre-se com um nome de usuário e senha.
2. Faça login (os tokens são guardados em cookies HttpOnly).
3. Administre suas finanças. Cada usuário tem seu próprio saldo, cards e resumo.

- Definir e ver o saldo líquido
- Ver a situação (faixa verde / amarela / vermelha) e totais
- Listar, criar, editar e excluir despesas (cards)
- Filtrar por status e tipo
- Baixar a planilha Excel

A API é chamada sob o prefixo `/api` (ex.: `/api/balance`, `/api/cards`).

## Endpoints (API)

| Recurso | Método | Descrição |
|--------|--------|-----------|
| `/api/auth/register` | POST | Criar usuário e já autenticar |
| `/api/auth/login` | POST | Login (gera cookies de sessão) |
| `/api/auth/logout` | POST | Logout (limpa cookies) |
| `/api/auth/me` | GET | Dados do usuário autenticado |
| `/api/balance` | GET, PUT | Obter ou definir o saldo líquido |
| `/api/cards` | GET, POST | Listar (com filtros) ou criar cards |
| `/api/cards/summary` | GET | Resumo: totais e faixa (vermelho/amarelo/verde) |
| `/api/cards/{id}` | GET, PATCH, DELETE | Ver, editar ou excluir um card |
| `/api/export/spreadsheet` | GET | Download da planilha (.xlsx) |

## Modelo do card

Cada card (despesa) possui:

- **title** (string): nome da despesa (ex.: "Aluguel", "Mensalidade Unesp")
- **urgency** (int): grau de urgência (1 = maior prioridade)
- **expense_type**: `casa`, `faculdade`, `saude`, `lazer`, `alimentacao`, `transporte`, `outros`
- **value** (float): valor da despesa
- **percentage** (calculado): % em relação ao saldo líquido
- **due_date** (date): data para pagar
- **status**: `pago` ou `pendente`

## Faixas (zona)

- **Vermelho**: total das despesas > saldo líquido (dívidas maiores que o disponível).
- **Amarelo**: despesas ≤ saldo, mas soma das porcentagens > 60%.
- **Verde**: despesas ≤ saldo e soma das porcentagens ≤ 60%.

## Exportação

`GET /export/spreadsheet` retorna um arquivo Excel (`.xlsx`) com:

- Aba **Finanças** com uma seção por despesa (Título, urgência, tipo, valor, % do saldo, data de pagamento e status).
- Ao final da planilha, um bloco **Resumo geral** com saldo líquido, total das despesas, percentual total e situação (faixa).
