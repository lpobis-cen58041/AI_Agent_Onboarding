# 06 - Exekuce Load testu

- **pageId**: 2301758052
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/2301758052/06%20-%20Exekuce%20Load%20testu
- **depth**: 3
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované > George - PERF testy na PROD

---
# Ostrý plně automatizovaný test - 29.9. 2026CHR - 

SCOPE

- Spustíme plně automatizovaný testovací běh pasivních operací na produkci.- Součástí testu jsou tyto [testovací scénáře](https://cnfl.csin.cz/x/GZczfw) :

Overview - Web + Mobile- Transaction History - Web + Mobile- Show Me Card - Web + Mobile- Login Availability- Public Api

**GATLING RUN PARAMETRY:**

 **| Parameter** | **Value** |

|  Scenario | prodMix |
|  Maven profile | prodmix |
|  Scenario config | sas-georgepete/load/prodmix.properties |
|  Simulation class | cz.csas.georgepete.gatling.simulations.combined.ProdMixSimulation |
|  Target count | **X** (run override) |
|  Duration seconds | **3600** (run override) |
|  Load profile | ramp (run override) |
|  Ramp seconds | **1200**(run override) |
|  Concurrent users | **X**(run override) |
|  Stress multiplier | - |
|  Run outcome | ** |
|  Report link | 
 |

# Dry run - 21.9.2026CHR - [CHG0464316](https://csasprod.service-now.com/now/nav/ui/classic/params/target/change_request.do%3Fsys_id%3D65afec182beb4710c5bbf0afe291bf9e%26sysparm_view%3Dnormal_emergency%26sysparm_view_forced%3Dtrue)

SCOPE:**

- Provedení testovacího běhu automatizovaných pasivních operací na PROD.- Ověření celoplošné funkčnosti řešení v produkčním prostředí a připravenost pro následné pravidelné automatizované spouštění.- V rámci testu budou ověřeny pouze pasivní operace ([testovací scénáře](https://cnfl.csin.cz/x/GZczfw)) :

Overview - Web + Mobile- Transaction History - Web + Mobile- Show Me Card - Web + Mobile- Login Availability- Public Api

- Testovací běh bude proveden s kontrolovanou zátěží tak, aby bylo možné ověřit funkčnost řešení a jeho dopad na produkční prostředí. - Parametry pro následný standardní/ostrý provoz, zejména frekvence běhů a výsledná provozní zátěž, budou definovány samostatně na základě výsledku tohoto testu.
**

GATLING RUN PARAMETRY:**

 **| Parameter** | **Value** |

|  Scenario | prodMix |
|  Maven profile | prodmix |
|  Scenario config | sas-georgepete/load/prodmix.properties |
|  Simulation class | cz.csas.georgepete.gatling.simulations.combined.ProdMixSimulation |
|  Target count | 100000 (run override) |
|  Duration seconds | 600 (run override) |
|  Ramp seconds | 120 (run override) |
|  Load profile | ramp (run override) |
|  Concurrent users | 300 (run override) |
|  Stress multiplier | - |
|  Run outcome | success |
|  Report link | [Archive-expire2612212147.zip](https://artifactory.csin.cz/ui/native/georgepete-generic-private-local/pete-orchestrator/sas-georgepete/Archive-expire2612212147.zip) ( expire on 21.12.2026 ) |
