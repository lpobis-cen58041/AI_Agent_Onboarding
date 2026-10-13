# 01_01 - MEP automatické generování tokenů

- **pageId**: 2164008710
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/2164008710/01_01%20-%20MEP%20automatick%C3%A9%20generov%C3%A1n%C3%AD%20token%C5%AF
- **depth**: 4
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované > George - PERF testy na PROD > 01 - PETE infrastruktura produkčního prostředí

---
Užitečné odkazy: 

[PTP generátor](https://cnfl.csin.cz/pages/viewpage.action?pageId=2271347975)

[FIT-291156 : Perf. testy na PRODukci - obnovení - červen-2025 ( dopady na MEP ) - MEP - Wiki České …](https://cnfl.csin.cz/pages/viewpage.action?pageId=1920365618)

 

[Příprava běhu github workflow PTP jobu - MEP - Wiki České Spořitelny](https://cnfl.csin.cz/pages/viewpage.action?pageId=1985331290)

 

[Run PTP Generator · Workflow runs · csas-ops/mep-tools](https://github.com/csas-ops/mep-tools/actions/workflows/run-ptp-generator.yml)

 

**Schůzka MEP - vydávání tokenů (15.7.2026) - Click here to expand...

Vydávání tokenů:**

**To-Do:**

- **zadat EPIC na MEP, po dohodě s Milanem Koppem.**
**

Zápisky ze schůzky:**

- potřebujeme na PROD zautomatizovat vydávání tokenů,- Milan Kopp:
app je v SECu, ale action je v OPSu,
je tam business logika daná securitou,- je to kontrolované a schválené,- potřeba nadefinovat se SECURITOU,
- co je potřeba:
zdrojovou strukturu,- password a artifaktory,- kam CSV uložit,- lze volat z automatu na vyžádání...- až action doběhne, tak vrátí SUCCESS,- životnost je 5 hodin,
hodnota je nastavitelná, ale nyní je to neměnné,

- provolání napřímo MEPu je na chráněný endpoint,
musela by to schválit SECURITA,- vše je sledované a logované.
