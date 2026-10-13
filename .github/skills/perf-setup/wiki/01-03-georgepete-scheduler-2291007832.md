# 01_03 - GEORGEPETE SCHEDULER

- **pageId**: 2291007832
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/2291007832/01_03%20-%20GEORGEPETE%20SCHEDULER
- **depth**: 4
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované > George - PERF testy na PROD > 01 - PETE infrastruktura produkčního prostředí

---
### PopisWebová aplikace pro bezpečnou automatizaci a správu produkčních zátěžových testů a dalších periodických úloh v prostředí České spořitelny. Umožňuje uživatelům vytvářet, upravovat a spravovat plány automatizovaných zátěžových testů s cron výrazy, nastavovat politiky zmeškaných běhů, definovat vlastní parametry testů a sledovat historii běhů. Aplikace je postavena na moderním React stacku s TypeScript a Material-UI komponentami. 

Server (Kotlin) funguje hlavně jako plánovací služba pro spouštění GitHub Actions workflows ( náhrada za nespolehlivý GitHub cron ). 

Celé řešení je plně auditovatelné, takže bude existovat jednoznačný záznam o tom kdo a kdy spustil, upravil nebo změnil parametry jakéhokoliv testu a všechny zásadní operace budou podléhat schvalovacímu procesu na ochranu produkčního prostředí.    

### REDIM PRÁVA
|  **prostředí** | **právo** | **popis** |
|  

TEST - csint

PROD - csin

 | GeorgePete_Admin | Admin správa pro řízení automatických testů |
|  Georgepete_Editor | Řízení automatických testů aplikace SAS_GEORGEPETE |
|  GeorgePete_Viewer | Náhled na plánované scénáře automatizovaných testů |
|  GeorgePete_Operator | Právo pro zastavení naplánovaného testu |
