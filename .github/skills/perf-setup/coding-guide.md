# Sprievodca: nová doména + testy (pre úplného začiatočníka)

Cieľ: používateľ pridá do lokálneho repozitára (zo šablóny) jednu novú doménu a pochopí každý súbor, ktorý vznikol.
Nepredpokladaj znalosť Kotlinu ani Gatlingu. Vysvetľuj po jednom kroku, jednou vetou, s obrázkom z bežného života.

## Mentálny model (vrstvy)
Doména = jedna oblasť služby (napr. `orders`). Každá vrstva stavia na predchádzajúcej:
1. **requests** – jedno volanie API („zavolaj /orders a čakaj 200“). Ako jedno kliknutie.
2. **steps** – príprava pred volaním (vezmi riadok z CSV, nastav token). Ako „prihlás sa“.
3. **flows** – poradie krokov a volaní. Ako jeden celý postup používateľa.
4. **usecases** – flow + váha (koľko % záťaže má tvoriť). Váhy v mixe dávajú dokopy 100.
5. **simulation** – spojí use cases a spustí ich. Volá sa len cez `*MixSimulation`; request sa nikdy nevolá priamo zo simulácie.
Dáta (**data**) = feeder, CSV s testovacími vstupmi. Cesty endpointov = `env/test.properties` a `env/prod.properties` (rovnaké kľúče v oboch).

## Postup s používateľom
1. **Zisti:** názov domény (malé písmená/čísla, napr. `orders`), cestu endpointu (napr. `/orders`), metódu (GET/POST).
   Ak endpoint nepozná, použi vymyslenú cestu; reálne interné URL ani dáta nikdy nezapisuj.
2. **Over repo:** musí byť z šablóny (lokálne vytvorené cez `scaffold.py`) a `./mvnw -q test` musí prejsť ešte pred zmenou.
3. **Ukáž náhľad:** `python new_domain.py <repo> <doména> --path <cesta> --method <GET|POST> --dry-run`, vysvetli zoznam súborov.
4. **Vytvor:** rovnaký príkaz bez `--dry-run`. Skript vytvorí len nové súbory, doplní kľúč do oboch `env/*.properties` a riadok do `ci/simulation-data.csv`.
5. **Prejdi súbory vo vrstvách** (requests → steps → flows → usecases → simulation → test) a ku každému povedz, na čo je.
6. **Spustite testy:** `./mvnw -q test` (rýchle, bez siete). Vysvetli výstup. `<Doména>UseCasesTest` kontroluje, že váhy dávajú 100 a názvy sú jedinečné;
   `EnvPathsTest` kontroluje rovnaké kľúče v test/prod.
7. **Úprava na mieru (po jednej veci, vždy znova testy):**
   - viac volaní vo flow: pridaj ďalšiu metódu v `Requests` a zreťaz v `Flows` (`.exec(...)`, `.pause(1)` pre čakanie),
   - ďalšie use case: pridaj do `UseCases` a do `all`, uprav váhy tak, aby dali 100,
   - telo POST requestu: v `Requests` nahraď `StringBody("{}")` a pridaj `check(...)` na odpoveď,
   - nový stĺpec v CSV: pridaj ho do `src/test/resources/<doména>/<doména>.csv` (len vymyslené hodnoty), použi `#{stlpec}` v ceste/tele.
8. **Statická kontrola:** `./mvnw detekt:check`.
9. **Lokálny smoke beh (voliteľné):** len proti vlastnému lokálnemu mocku, príkaz podľa `README.md` vzorového repa a s menom novej `*MixSimulation`. Nikdy proti TEST/PROD.
10. **Zhrnutie a ďalší krok:** čo vzniklo, čo sa naučil, čo ostáva (reálne dáta z Artifactory, review, PR). Commit/PR urob len na jeho pokyn.

## Najčastejšie chyby (pomôž s diagnostikou)
- `Unresolved reference: <kľúč>` – kľúč chýba v `env/test.properties` (Paths.kt sa generuje z neho pri builde).
- `EnvPathsTest` padá – kľúč je len v jednom z `test`/`prod` súborov.
- `...UseCasesTest` padá na súčte – váhy nedávajú 100.
- Chyba pri `csv(...)` v teste – chýba súbor `src/test/resources/<doména>/<doména>.csv` alebo test nevolá `GatlingTestBootstrap.init()`.
- `./mvnw` hlási `Permission denied` – `chmod +x mvnw`.
- Chyba verzie Javy – treba Java 17 (`check_env.py`).

## Pravidlá
- Meň len repozitár používateľa, nie šablónu v `.github/skills/perf-setup/template/`.
- Žiadne reálne tokeny, URL ani dáta; len `local-dummy-*`.
- Nepíš veľké bloky kódu naraz; radšej malá zmena, test, vysvetlenie.
