# Roadmap - alpha-trading-crypto

**Date** : 2025-01-27  
**Version** : 0.1.0  
**Status** : 🚧 En Planification

---

## 🎯 Vision Globale

Créer un système de trading complet pour les perp futures crypto sur Hyperliquid avec :
1. **Backtesting** : Tester les stratégies avant le trading live
2. **Trading Live** : Exécuter les stratégies sur Hyperliquid
3. **Gestion Multi-Tokens** : Gérer plusieurs tokens avec USDC comme référence
4. **API Hyperliquid** : Intégration complète
5. **Transferts** : Gérer les transferts Ethereum ↔ Hyperliquid
6. **Gestion Ordres** : Tracking, placement, annulation (Taker/Maker)
7. **Inventaire** : Suivi en temps réel des positions et balances

---

## 📊 Phases de Développement

### Phase 1 : Domain Layer (Semaines 1-2)

**Objectif** : Créer les entités et services métier

#### 1.1 Entities
- [ ] `Order` : Ordre (id, symbol, side, quantity, price, type, status, timestamp)
- [ ] `Position` : Position (symbol, size, entry_price, unrealized_pnl, funding)
- [ ] `Inventory` : Inventaire (token, free, locked, total)
- [ ] `Token` : Token (symbol, decimals, chain, address)
- [ ] `Transfer` : Transfert (from_chain, to_chain, token, amount, status, tx_hash)

#### 1.2 Services
- [ ] `OrderManager` : Gestion des ordres (create, cancel, update, track)
- [ ] `InventoryManager` : Gestion inventaire (update, verify, reconcile)
- [ ] `PositionManager` : Gestion positions (update, calculate_pnl, funding)
- [ ] `TransferManager` : Gestion transferts (initiate, track, verify)

**Livrables** :
- Entités domain complètes
- Services domain avec tests unitaires
- Coverage > 90%

---

### Phase 2 : Infrastructure Layer (Semaines 3-5)

**Objectif** : Intégrer les services externes

#### 2.1 Hyperliquid API
- [ ] `HyperliquidAPI` : Client API Hyperliquid
  - [ ] Authentification (signature messages)
  - [ ] Market Data (prices, orderbook, trades)
  - [ ] Account Info (balances, positions, orders)
  - [ ] Order Placement (market, limit, stop)
  - [ ] Order Management (cancel, modify, query)
  - [ ] Funding Rates (current, historical)

#### 2.2 Backtest Engine
- [ ] `BacktestEngine` : Moteur de backtesting
  - [ ] Simulation de marché (prices, orderbook)
  - [ ] Simulation d'ordres (execution, slippage)
  - [ ] Simulation de funding
  - [ ] Métriques de performance (Sharpe, drawdown, etc.)

#### 2.3 Blockchain Integration
- [ ] `EthereumProvider` : Provider Web3 pour Ethereum
- [ ] `TokenTransferService` : Service de transfert de tokens
  - [ ] Transfert ETH → Hyperliquid
  - [ ] Transfert Hyperliquid → ETH
  - [ ] Tracking des transactions
  - [ ] Gestion des gas fees

**Livrables** :
- API Hyperliquid fonctionnelle
- Backtest engine opérationnel
- Transferts blockchain fonctionnels

---

### Phase 3 : Application Layer (Semaines 6-7)

**Objectif** : Créer les use cases

#### 3.1 Order Use Cases
- [ ] `PlaceOrder` : Placer un ordre (taker ou maker)
- [ ] `CancelOrder` : Annuler un ordre
- [ ] `ModifyOrder` : Modifier un ordre
- [ ] `QueryOrders` : Interroger les ordres

#### 3.2 Strategy Use Cases
- [ ] `ExecuteStrategy` : Exécuter une stratégie live
- [ ] `BacktestStrategy` : Backtester une stratégie
- [ ] `MonitorStrategy` : Monitorer une stratégie live

#### 3.3 Transfer Use Cases
- [ ] `TransferTokens` : Transférer des tokens
- [ ] `TrackTransfer` : Suivre un transfert
- [ ] `ReconcileBalances` : Réconcilier les balances

**Livrables** :
- Use cases complets avec tests
- Intégration avec domain et infrastructure

---

### Phase 4 : Market Making (Semaines 8-9)

**Objectif** : Implémenter le market making

#### 4.1 Avellaneda-Stoikov
- [ ] Modèle Avellaneda-Stoikov
- [ ] Calcul spread optimal
- [ ] Gestion inventaire cible
- [ ] Optimisation bid-ask

#### 4.2 Maker Orders
- [ ] Placement ordres maker
- [ ] Gestion spread dynamique
- [ ] Réajustement automatique
- [ ] Protection inventaire

**Livrables** :
- Market making fonctionnel
- Tests avec données réelles (testnet)

---

### Phase 5 : Risk Management (Semaines 10-11)

**Objectif** : Gestion des risques

#### 5.1 Position Limits
- [ ] Limites par token
- [ ] Limite globale
- [ ] Vérification avant ordre

#### 5.2 Circuit Breakers
- [ ] Détection drawdown
- [ ] Arrêt automatique
- [ ] Réactivation conditionnelle

#### 5.3 Slippage Protection
- [ ] Limites de slippage
- [ ] Vérification avant exécution
- [ ] Rejet si slippage trop élevé

**Livrables** :
- Risk management opérationnel
- Tests de sécurité

---

### Phase 6 : Monitoring & Reporting (Semaines 12-13)

**Objectif** : Monitoring et reporting

#### 6.1 Metrics
- [ ] Métriques de performance (PnL, Sharpe, etc.)
- [ ] Métriques d'exécution (latence, slippage, etc.)
- [ ] Métriques de risque (drawdown, exposure, etc.)

#### 6.2 Logging
- [ ] Logging structuré (structlog)
- [ ] Logs critiques (orders, transfers, errors)
- [ ] Rotation des logs

#### 6.3 Alerts
- [ ] Alertes erreurs critiques
- [ ] Alertes dérive performance
- [ ] Alertes limites de risque

**Livrables** :
- Monitoring complet
- Dashboard métriques (optionnel)

---

## 🔄 Intégration avec Autres Repos

### alpha-meta-model-crypto
- **Input** : Signaux du méta-modèle (portfolio optimal)
- **Output** : Ordres exécutés, positions, PnL

### prop-trading-data-warehouse
- **Input** : Données historiques pour backtesting
- **Output** : Résultats de backtest

---

## 📈 Métriques de Succès

### Backtesting
- **Performance** : Sharpe > 1.5, Max Drawdown < 20%
- **Validation** : Comparaison backtest vs live (dérive < 2σ)

### Trading Live
- **Execution** : Latence < 100ms, Slippage < 0.1%
- **Reliability** : Uptime > 99.9%, Erreurs < 0.1%

### Risk Management
- **Limits** : Respect des limites de position
- **Circuit Breakers** : Activation si drawdown > seuil

---

## 🚀 Prochaines Étapes

1. **Phase 1** : Domain Layer (entités et services)
2. **Phase 2** : Infrastructure Layer (API Hyperliquid, backtest)
3. **Phase 3** : Application Layer (use cases)
4. **Phase 4** : Market Making (Avellaneda-Stoikov)
5. **Phase 5** : Risk Management
6. **Phase 6** : Monitoring & Reporting

---

**Dernière mise à jour** : 2025-01-27

