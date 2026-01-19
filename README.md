# alpha-trading-crypto

**Version** : 0.1.0  
**Status** : 🚧 In Development  
**Repository** : https://github.com/caissatech/alpha-trading-crypto

## Overview

`alpha-trading-crypto` est un système de trading complet pour les perp futures crypto sur Hyperliquid. Il inclut :

1. **Backtesting** : Tester les stratégies du méta-modèle crypto avant le trading live
2. **Trading Live** : Exécuter les stratégies sur Hyperliquid
3. **Gestion Multi-Tokens** : Gérer plusieurs tokens avec USDC comme référence
4. **API Hyperliquid** : Intégration complète avec l'API Hyperliquid
5. **Transferts** : Gérer les transferts de tokens entre Ethereum et Hyperliquid
6. **Gestion Ordres** : Tracking, placement, annulation (Taker/Maker)
7. **Inventaire** : Suivi en temps réel des positions et balances

## Architecture

Le système suit une architecture Clean Architecture avec 3 couches :

```
┌─────────────────────────────────────────────────────────┐
│ Domain Layer (Business Logic)                           │
│ - Entities: Order, Position, Inventory, Token            │
│ - Services: OrderManager, InventoryManager, etc.        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ Application Layer (Use Cases)                           │
│ - PlaceOrder, CancelOrder, TransferTokens              │
│ - ExecuteStrategy, BacktestStrategy                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ Infrastructure Layer (External Services)                │
│ - HyperliquidAPI, BacktestEngine                        │
│ - EthereumProvider, TokenTransferService                │
└─────────────────────────────────────────────────────────┘
```

## Features

### Backtesting
- Simulation de stratégies avec données historiques
- Métriques de performance (Sharpe, drawdown, etc.)
- Comparaison avec trading live

### Trading Live
- **Taker Orders** : Exécution immédiate (market orders)
- **Maker Orders** : Market making avec Avellaneda-Stoikov
- **Order Management** : Tracking, annulation, modification
- **Position Management** : Suivi positions, PnL, funding rates

### Gestion Multi-Tokens
- Support de plusieurs tokens simultanément
- USDC comme référence (quote currency)
- Gestion des balances par token

### Transferts
- Transferts Ethereum → Hyperliquid
- Transferts Hyperliquid → Ethereum
- Gestion des gas fees
- Tracking des transferts

### Inventaire
- Suivi en temps réel des balances
- Distinction free/locked/total
- Vérification de cohérence

## Technology Stack

- **Core** : Python 3.10+
- **Dependencies** :
  - `pandas`, `numpy` (data processing)
  - `httpx`, `websockets` (API Hyperliquid)
  - `web3`, `eth-account` (blockchain transfers)
  - `pydantic` (configuration)
  - `quant-kit` (quantitative models - Avellaneda-Stoikov, etc.)

## Installation

```bash
pip install git+ssh://git@github.com/caissatech/alpha-trading-crypto.git
```

## Usage

### Backtesting

```python
from alpha_trading_crypto import BacktestStrategy
from alpha_trading_crypto.domain.entities import Strategy

# Créer une stratégie
strategy = Strategy(
    name="meta_model_crypto",
    signals_source="alpha-meta-model-crypto",
)

# Lancer backtest
backtest = BacktestStrategy()
results = backtest.run(
    strategy=strategy,
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=100000,
)
```

### Trading Live

```python
from alpha_trading_crypto import ExecuteStrategy
from alpha_trading_crypto.infrastructure.adapters import HyperliquidAPI

# Initialiser API Hyperliquid
api = HyperliquidAPI(
    private_key="0x...",
    testnet=False,
)

# Exécuter stratégie
executor = ExecuteStrategy(api=api)
executor.run(strategy=strategy)
```

### Gestion Ordres

```python
from alpha_trading_crypto import PlaceOrder, CancelOrder

# Placer un ordre
place_order = PlaceOrder(api=api)
order = place_order.execute(
    symbol="BTC",
    side="BUY",
    quantity=0.1,
    order_type="MARKET",  # ou "LIMIT"
)

# Annuler un ordre
cancel_order = CancelOrder(api=api)
cancel_order.execute(order_id=order.id)
```

### Transferts

```python
from alpha_trading_crypto import TransferTokens

# Transférer ETH → Hyperliquid
transfer = TransferTokens(api=api)
transfer.execute(
    from_chain="ethereum",
    to_chain="hyperliquid",
    token="USDC",
    amount=1000,
)
```

## Documentation

- **[ROADMAP.md](./ROADMAP.md)** : Plan de développement détaillé
- **[RULES.md](./RULES.md)** : Règles de développement
- **[STATUS.md](./STATUS.md)** : État d'avancement du projet
- **[CHANGELOG.md](./CHANGELOG.md)** : Historique des versions

## License

UNLICENSED - Private package

