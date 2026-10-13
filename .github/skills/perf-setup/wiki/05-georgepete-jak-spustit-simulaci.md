# 05 - GEORGEPETE - Jak spustit simulaci

- **pageId**: 2318992641
- **status**: draft

---
**Obsah**

**

- [1.0 Jak spustit simulaci lokálně](#id-05GEORGEPETEJakspustitsimulaci-1.0Jakspustitsimulacilokálně)
- [2.0 Jak spustit simulaci na CI](#id-05GEORGEPETEJakspustitsimulaci-2.0JakspustitsimulacinaCI)

[Co zkontrolovat před spuštěním](#id-05GEORGEPETEJakspustitsimulaci-Cozkontrolovatpředspuštěním)
- [Postup spuštění](#id-05GEORGEPETEJakspustitsimulaci-Postupspuštění)
- [Výsledek běhu](#id-05GEORGEPETEJakspustitsimulaci-Výsledekběhu)

**

## **1.0 Jak spustit simulaci lokálně**
- 
Otevřete terminál v rootu projektu.- Spusťte vybranou simulaci pomocí Maven příkazu.

Při lokálním spuštění se používá *dummy token* ze *src/test/resources/*.

Lokální běh slouží hlavně jako ověření, že simulaci spouštíte správně a že jsou všechny závislosti a konfigurace propojené tak, jak mají být.

**Příklad:**

```
./mvnw -q gatling:test \
  -Dgatling.simulationClass="cz.csas.georgepete.gatling.simulations.domain.info.InfoMixSimulation" \ 
  -DwebApiBaseUrl="<WEB_API_BASE_URL>" \
  -DmilaBaseUrl="<MILA_BASE_URL>" \
  -DpublicApiBaseUrl="<PUBLIC_API_BASE_URL>" \
  -DwebApiKey="<WEB_API_KEY>" \
  -DmilaApiKey="<MILA_API_KEY>" \
  -DdurationSec=120 \
  -DtargetCount=100 \
  -DconcurrentUsers=1 \
  -DloadProfile=standard
```

**

## 2.0 Jak spustit simulaci na CI**### **Co zkontrolovat před spuštěním**Před spuštěním je potřeba ověřit, že v příslušném Artifactory adresáři pro daný test už leží platný soubor s tokenem.

* Token je platný 24 hodin*** Pokud soubor chybí nebo je token prošlý, je potřeba vygenerovat nový
* Návod na generování tokenu: [Alfred 2.0 – Nástroj pro výkonnostní testování](https://cnfl.csin.cz/spaces/RDBT/pages/2017045811/Alfred+2.0+-+N%C3%A1stroj+pro+v%C3%BDkonnostn%C3%AD+testov%C3%A1n%C3%AD)

Výjimka - PrcCsvGeneration **je samostatná simulation pro generování PRC CSV. To znamená, že jde o speciální případ, ne o běžné chování pro všechny spouštění.

### Postup spuštění
- 
Otevřete repozitář v GitHubu.**- Přejděte do sekce *Actions*.
- Vyberte workflow *Gatling Performance Test*.
- Klikněte na *Run workflow*.
- Vyberte větev, ze které chcete test spustit.
- Potvrďte kliknutím na *Run workflow***. Co je potřeba vyplnit

Pro běžné spuštění jedné simulace stačí:

***simulation*** – vybraná simulace***simulationSet*** – SingleSimulation***additionalSimulations*** – nechat prázdné***environment*** – obvykle PRED

***additionalSimulations*** slouží jen pro situace, kdy chcete spustit více simulací v jednom CI běhu. Pro běžné spuštění jedné simulace se nevyplňuje.**

### Výsledek běhu**Po dokončení testu je možné stáhnout ZIP archiv s výsledky.

V archivu otevřete: **reports/index.html**

Tento soubor zobrazí detailní report se záznamy z běhu.

Vzorek: 

Nastavení simulace
