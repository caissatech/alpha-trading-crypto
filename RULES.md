# Règles de Développement - alpha-trading-crypto

## Architecture

### Clean Architecture
- **Domain Layer** : Entités et services métier (pas de dépendances externes)
- **Application Layer** : Use cases et ports (interfaces)
- **Infrastructure Layer** : Implémentations concrètes (API, DB, etc.)

### Séparation des Responsabilités
- **Domain** : Logique métier pure
- **Application** : Orchestration des use cases
- **Infrastructure** : Détails techniques (API, blockchain, etc.)

## Code Style

### Python
- **Version** : Python 3.10+
- **Type Hints** : Obligatoires pour toutes les fonctions publiques
- **Docstrings** : Obligoires (format Google)
- **Linting** : `ruff`, `black`, `mypy`

### Naming Conventions
- **Classes** : PascalCase (`OrderManager`, `HyperliquidAPI`)
- **Functions** : snake_case (`place_order`, `cancel_order`)
- **Constants** : UPPER_SNAKE_CASE (`MAX_POSITION_SIZE`)
- **Private** : Préfixe `_` (`_private_method`)

## Testing

### Structure
- **Unit Tests** : Tests isolés par composant
- **Integration Tests** : Tests avec API mockées
- **E2E Tests** : Tests complets (optionnel, nécessite testnet)

### Coverage
- **Minimum** : 80% de couverture
- **Domain Layer** : 100% de couverture
- **Critical Paths** : 100% de couverture (order placement, transfers)

## Security

### Secrets
- **Jamais** de secrets dans le code
- Utiliser `pydantic-settings` pour configuration
- Variables d'environnement pour secrets

### API Keys
- Stocker dans `.env` (non commité)
- Utiliser testnet pour développement
- Rotation régulière des clés

## Error Handling

### Exceptions
- **Domain Exceptions** : Exceptions métier (`InsufficientBalance`, `InvalidOrder`)
- **Infrastructure Exceptions** : Exceptions techniques (`APIError`, `NetworkError`)
- **Toujours** logger les erreurs avec contexte

### Logging
- Utiliser `structlog` pour logging structuré
- Niveaux : DEBUG, INFO, WARNING, ERROR, CRITICAL
- Logger toutes les opérations critiques (orders, transfers)

## Trading Rules

### Order Management
- **Toujours** tracker les ordres en cours
- **Vérifier** l'inventaire avant chaque ordre
- **Annuler** les ordres orphelins au démarrage

### Risk Management
- **Position Limits** : Limites par token et globale
- **Circuit Breakers** : Arrêt automatique si drawdown > seuil
- **Slippage Protection** : Limites de slippage max

### Inventaire
- **Vérification** : Vérifier cohérence inventaire vs balances API
- **Reconciliation** : Réconciliation périodique
- **Alerts** : Alertes si divergence détectée

## Backtesting

### Data
- **Historique** : Utiliser données historiques réelles
- **Slippage** : Modéliser slippage réaliste
- **Funding** : Inclure funding rates dans backtest

### Validation
- **Comparaison** : Comparer backtest vs live
- **Dérive** : Détecter dérive si performance live < backtest
- **Kill Rules** : Désactiver stratégie si dérive détectée

## Documentation

### Code
- **Docstrings** : Obligatoires pour toutes les fonctions publiques
- **Type Hints** : Obligatoires
- **Comments** : Expliquer le "pourquoi", pas le "comment"

### README
- **Usage** : Exemples d'utilisation
- **Architecture** : Diagramme d'architecture
- **Configuration** : Guide de configuration

## Git

### Branches
- **main** : Production
- **develop** : Développement
- **feature/** : Nouvelles features
- **fix/** : Corrections de bugs

### Commits
- **Format** : `type: description` (feat, fix, docs, test, refactor)
- **Messages** : En français, clairs et descriptifs

## Dependencies

### Gestion
- **Poetry** : Gestion des dépendances
- **Versioning** : Semantic versioning (MAJOR.MINOR.PATCH)
- **Updates** : Mettre à jour régulièrement (sécurité)

### External
- **Hyperliquid API** : Documentation officielle
- **Web3** : Pour transferts blockchain
- **Pandas** : Pour data processing

## Performance

### Optimization
- **Async** : Utiliser async/await pour I/O
- **Caching** : Cache pour données fréquentes (balances, prices)
- **Batching** : Grouper requêtes API quand possible

### Monitoring
- **Metrics** : Métriques de performance (latence, throughput)
- **Alerts** : Alertes si performance dégrade
- **Logging** : Logger toutes les opérations critiques

## Checklist Avant Production

- [ ] Tests passent (unit + integration)
- [ ] Coverage > 80%
- [ ] Linting OK (ruff, black, mypy)
- [ ] Documentation à jour
- [ ] Secrets dans .env (non commité)
- [ ] Testnet validé
- [ ] Risk limits configurés
- [ ] Circuit breakers activés
- [ ] Monitoring configuré
- [ ] Alerts configurées

