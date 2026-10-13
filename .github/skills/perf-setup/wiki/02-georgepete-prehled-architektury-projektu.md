# 02 - GEORGEPETE - Přehled architektury projektu

- **pageId**: 2318992048
- **status**: draft

---
Tato stránka popisuje základní architekturu projektu **georgepete-performance-test**, jeho hlavní vrstvy a odpovědnosti jednotlivých částí.**
Obsah:

- [1. Co je tento projekt](#id-02GEORGEPETEPřehledarchitekturyprojektu-1.Cojetentoprojekt)
- [2. Základní architektonický princip](#id-02GEORGEPETEPřehledarchitekturyprojektu-2.Základníarchitektonickýprincip)
- [3. Struktura projektu](#id-02GEORGEPETEPřehledarchitekturyprojektu-3.Strukturaprojektu)
- [4. Hlavní části produkčního kódu](#id-02GEORGEPETEPřehledarchitekturyprojektu-4.Hlavníčástiprodukčníhokódu)
- [5. Konfigurace v resources](#id-02GEORGEPETEPřehledarchitekturyprojektu-5.Konfiguracevresources)
- [6. Feeder data](#id-02GEORGEPETEPřehledarchitekturyprojektu-6.Feederdata)
- [7. Two-repo model](#id-02GEORGEPETEPřehledarchitekturyprojektu-7.Two-repomodel)
- [8. Základní build a validace](#id-02GEORGEPETEPřehledarchitekturyprojektu-8.Základníbuildavalidace)
- [9. Související zdroje](#id-02GEORGEPETEPřehledarchitekturyprojektu-9.Souvisejícízdroje)

## 1. Co je tento projekt**Projekt georgepete-performance-test je knihovna Gatling scénářů napsaná v Kotlinu.**Publikovaný Maven artefakt: cz.csas.georgepete:gatling-scenarios**

Projekt obsahuje:

- Gatling requesty- session a feeder logiku- flow kompozice- use case mixy s váhami- spustitelné simulation classy- runtime konfiguraci- auth helpery
Repozitář slouží jako scenario library, kterou používá externí orchestrátor pro řízené spouštění performance testů.

## **2. Základní architektonický princip**Každá doména v projektu používá stejný návrhový princip:***requests → steps → flows → usecases → simulation***

Význam jednotlivých vrstev

- 
requests/**obsahuje raw HTTP volání a kontrolu odpovědí- steps/
obsahuje práci se session, feeder daty, enrichment a pomocnou logiku- flows/
skládá jednotlivé kroky a requesty do business scénáře- usecases/
definuje pojmenované scénáře a jejich výchozí váhy v mixu- simulation/
spustitelná Gatling simulation, která sestaví finální mix a injection model

Důležité pravidlo: simulation nesmí volat request přímo. Vždy musí jít přes flow a use case vrstvu.

## 
 
3. Struktura projektu**Hlavní kód projektu je v **src/main**, testy a dummy data v src/test.

**Zjednodušená struktura:**

```
src/
├── main/
│   ├── kotlin/cz/csas/georgepete/gatling/
│   │   ├── auth/
│   │   ├── business/
│   │   ├── common/
│   │   ├── config/
│   │   ├── domain/
│   │   ├── setup/
│   │   └── simulations/
│   └── resources/
│       ├── env/
│       └── weights/
├── test/
│   ├── kotlin/
│   └── resources/
ci/
└── simulation-data.csv
docs/
├── endpoint-load.md
├── mix-weights.md
└── PRODMIX_API_TABULKA.md
```

** **

## **
4. Hlavní části produkčního kódu
****Produkční kód je v:
**src/main/kotlin/cz/csas/georgepete/gatling/

**

auth/
**Autentizace a token handling.

**Klíčový soubor:
**src/main/kotlin/cz/csas/georgepete/gatling/auth/Auth.kt

**Token se typicky řeší v tomto pořadí:**

- 
**hodnota v session**- **token z feeder CSV**- **systémová property (-DwebApiToken, -DmilaToken)**- **fail user**

**
config/
**Povinné runtime parametry, env konfigurace a load shaping.

**

Důležité soubory:
**

- 
src/main/kotlin/cz/csas/georgepete/gatling/config**/Config.kt
**- src/main/kotlin/cz/csas/georgepete/gatling/config/**Env.kt**

**
**Endpoint path helper **Paths.kt** je generován při buildu z env properties.** 

common/runtime/**

Optional runtime konfigurace s defaultními hodnotami.**
Důležitý soubor: **src/main/kotlin/cz/csas/georgepete/gatling/common/runtime/RuntimeConfig.kt

** 
setup/**

Sdílené stavební bloky pro mixy a simulations.

**
Důležité soubory:
**

- 
src/main/kotlin/cz/csas/georgepete/gatling/setup/UseCase.kt- src/main/kotlin/cz/csas/georgepete/gatling/setup/MixBuilder.kt- src/main/kotlin/cz/csas/georgepete/gatling/setup/SimulationSetup.kt

**

domain/**

Obsahuje jednotlivé business domény, např.:

- accounts- cards- clientProfile- codebooks- csHub- domesticPayment- george- georgeMobile- info- insurances- paymentsSingle- pensions- productRightsCache- authMonitoring
**

simulations/**

Obsahuje spustitelné Gatling simulations.**Rozdělení:

- simulations/domain/ — doménové simulace- simulations/business/ — business mixy- simulations/combined/ — kombinované simulace
## 
5. Konfigurace v resources****
src/main/resources/env/**

**
**Obsahuje environment-specific endpoint paths:

- *test.properties*- *prod.properties*
**
Pravidla:
***oba soubory musí mít stejnou množinu klíčů, při rozdílu build failne. Z klíčů se generuje typed helper Paths.kt*

**
 ****src/main/resources/weights/**

Obsahuje výchozí váhy některých mixů.

**Příklady:**

- 
overview.properties- george.properties- georgeMobile.properties- prod-mix-components.properties

## **6. Feeder data****Feeder CSV data nejsou součástí publikovaného JAR.

Použití:**

- lokálně dummy data v *src/test/resources/*- v CI reálná data dle mapování v* ci/simulation-data.csv*
**Důležitý princip:** pokud simulation používá více domén, musí existovat mapování pro každou z nich** 

## 
7. Two-repo model****

Projekt funguje jako scenario library, která je publikována jako Maven artefakt. Externí orchestrátor tuto knihovnu používá a zajišťuje řízené spouštění.

Spouštění produkčních simulací probíhá v orchestrátoru, který je umístěný v repozitáři *csas-ops***.

**To znamená:** logika scénářů a simulations je zde -  řízení běhů a navázání na externí procesy může být mimo tento repozitář

## ** 
8. Základní build a validace**

**Kontrola kompilace:**

```
./mvnw -q test-compile
```

**

Spuštění testů:**

```
./mvnw -q test
```

## ** 
9. Související zdroje**
- [README.md](http://README.md)- pom.xml- ci/simulation-data.csv- docs/[mix-weights.md](http://mix-weights.md)- docs/[endpoint-load.md](http://endpoint-load.md)
