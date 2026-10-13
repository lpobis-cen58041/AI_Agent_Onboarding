# 03 - GEORGEPETE - Simulace a testovací scénáře

- **pageId**: 2318992183
- **status**: draft

---
Tato stránka poskytuje přehled typů simulací v projektu, jejich umístění a základních pravidel, podle kterých jsou skládány.

Obsah

- [1. Jak funguje simulation v tomto projektu](#id-03GEORGEPETESimulaceatestovacíscénáře-1.Jakfungujesimulationvtomtoprojektu)
- [2. Typy simulací](#id-03GEORGEPETESimulaceatestovacíscénáře-2.Typysimulací)
- [3. Use case mixy a váhy](#id-03GEORGEPETESimulaceatestovacíscénáře-3.Usecasemixyaváhy)

## 1. Jak funguje simulation v tomto projektuSimulation v projektu obvykle:

- vybere sadu use cases- sestaví mix přes MixBuilder- běží po dobu definovanou v Config- používá společný SimulationSetup**

Zjednodušeně:**

```
usecases → MixBuilder → scenario → SimulationSetup.run(...)
```

**

Jednoduchý příklad je doména pensions.

Simulation class:

- src/main/kotlin/cz/csas/georgepete/gatling/simulations/domain/pensions/PensionsMixSimulation.kt

Tato simulation:

- vytváří scénář webApiScenario("Pensions")
- používá MixBuilder.fromDefaults(PensionsUseCases.all)
- spouští se přes run(scn, Protocols.webApi)

## 2. Typy simulací2.1 Doménové simulace**

Simulace zaměřené na jednu konkrétní business doménu.**Umístění**: src/main/kotlin/cz/csas/georgepete/gatling/**simulations/domain/**

Příklady:

- PensionsMixSimulation**- InfoMixSimulation
- CardsMixSimulation
- GeorgeMixSimulation

2.2 Business simulace****
Simulace, které skládají více use cases do jednoho business pohledu.
Umístění: **src/main/kotlin/cz/csas/georgepete/gatling/**simulations/business/**

Příklad:

- OverviewMixSimulation
**2.3 Kombinované simulace**

Simulace, které spojují více oblastí do jednoho komplexního běhu.**Umístění**: src/main/kotlin/cz/csas/georgepete/gatling/**simulations/combined/**

**Příklad:

- ProdMixSimulation

## 3. Use case mixy a váhy
Každá simulation typicky běží jako mix více use cases.

Pravidla:

- aktivní use case váhy musí dát součet 100
- use case s váhou 0.0 je vypnutý
- validace probíhá přes MixBuilder a testy

Jednoduchý příklad:
v PensionsUseCases je pouze jeden use case s vahou 100.0

Důležitý validační test:**
src/test/kotlin/cz/csas/georgepete/gatling/setup/WeightSumTest.kt
