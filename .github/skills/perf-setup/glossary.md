# Glosár (pre netechnický onboarding)

Všeobecné vysvetlenia pojmov. Interné špecifiká (kto, kedy, limity) vždy potvrď zo snapshotov wiki.

- **Load / perf test:** zámerné zaťaženie systému veľkým počtom simulovaných používateľov, aby sa zistilo, či zvládne reálny alebo vyšší provoz.
- **Simulácia:** spustiteľný test (Gatling) popisujúci, čo virtuálni používatelia robia a ako rýchlo.
- **Scenár / use case:** jeden typ správania používateľa (napr. „zobraz zoznam“); simulácia ich kombinuje.
- **Mix:** pomer, v akom sa scenáre spúšťajú (váhy dávajú dokopy 100 %).
- **RPS (requests per second):** koľko požiadaviek za sekundu test generuje.
- **Throttle:** obmedzenie rýchlosti tak, aby test nepresiahol zvolené RPS.
- **Ramp:** postupné zvyšovanie záťaže na cieľovú hodnotu.
- **Stress test:** zaťaženie nad bežnú hodnotu, aby sa zistil limit systému.
- **Assertion:** podmienka úspechu behu (napr. max. % chýb, odozva p95 pod limit).
- **p90 / p95 / p99:** odozva, ktorú neprekročí 90 / 95 / 99 % požiadaviek.
- **Feeder:** zdroj testovacích dát (CSV s tokenmi/účtami), z ktorého si virtuálni používatelia berú vstupy.
- **TEST / PROD:** testovacie prostredie / ostrý provoz. PROD testy sú rizikové a vyžadujú schválenie.
- **PETE:** tím/platforma pre performance testovanie; spravuje infraštruktúru a pravidlá behov.
- **Redim:** systém správy oprávnení (skupiny prístupov).
- **ServiceNow:** systém na zadávanie požiadaviek (prístupy, SaaS, softvér).
- **Artifactory:** úložisko artefaktov; CI z neho sťahuje testovacie dáta a balíky.
- **Runner:** stroj, na ktorom beží CI (GitHub Actions) vrátane záťažového testu.
- **CI / PR check:** automatická kontrola kódu pri pull requeste.
