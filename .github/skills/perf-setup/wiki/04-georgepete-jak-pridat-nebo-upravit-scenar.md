# 04 - GEORGEPETE - Jak přidat nebo upravit scénář

- **pageId**: 2318992259
- **status**: draft

---
Obsah

- [4.1 Upravit už existující scénář](#id-04GEORGEPETEJakpřidatneboupravitscénář-4.1Upravitužexistujícíscénář)
- [4.2 Přidat novou doménu](#id-04GEORGEPETEJakpřidatneboupravitscénář-4.2Přidatnovoudoménu)
- [4.3 Co zkontrolovat po změně](#id-04GEORGEPETEJakpřidatneboupravitscénář-4.3Cozkontrolovatpozměně)

## 4.1 Upravit už existující scénářPokud se mění už existující scénář, je potřeba zkontrolovat i navazující vrstvy, ne jen samotný request.

Typicky se upravuje:

- requests/ — změna endpointu, parametrů nebo kontroly odpovědi- steps/ — pokud se mění feeder data, token nebo session logika- flows/ — pokud se mění posloupnost kroků- usecases/ — pokud se mění zařazení do mixu nebo váha- simulation/ — pokud změna ovlivní spuštění celého mixu
**Příklad**: **info**

**Na doméně info je to vidět takto:

- InfoRequests volá Paths.infoCountries- InfoSteps načítá feeder data a token- InfoFlows skládá step a request- InfoUseCases definuje countriesAscending- InfoMixSimulation spouští celý mix

Pokud se něco změní, je potřeba upravit i navazující části, ne jen jeden soubor.

## 4.2 Přidat novou doménu
Pokud se přidává úplně nová doména, je potřeba založit celou novou strukturu od začátku.

Pokud pro daný env ještě není přidaný potřebný webApi base URL** v Apiman, prvním krokem je založit požadavek na přidání **web API key** aplikace pro dané prostředí.**[🔗 Ukázka použití API Managera](https://cnfl.csin.cz/spaces/TCS/pages/1665533173/ApiMan+-+%C3%BAvodn%C3%AD+%C5%A1kolen%C3%AD)

Typicky se vytváří:**

- domain/<newDomain>/requests/- domain/<newDomain>/steps/- domain/<newDomain>/flows/- domain/<newDomain>/usecases/- domain/<newDomain>/data/- simulations/domain/<newDomain>/
**

Základní postup:**

- založit novou doménu v domain/- přidat requesty, steps, flows a use cases- vytvořit simulation class- doplnit feeder data- zkontrolovat env keys a CI mapování, pokud jsou potřeba
**Co je důležité při nové doméně**

- musí existovat jasná struktura všech vrstev- musí být přidaný nový use case mix- musí být doplněná simulation class- pokud doména používá data, je potřeba i feeder CSV- pokud se používá v CI, musí být doplněné mapování v ci/simulation-data.csv
## **4.3 Co zkontrolovat po změně
- jestli je změna promítnutá i do navazujících vrstev- jestli use case stále dává správnou váhu v mixu- jestli jsou doplněné feeder data- jestli je potřeba upravit ci/simulation-data.csv- jestli projde základní validace

Minimální validace**

```
./mvnw -q test-compile
./mvnw -q test
```
