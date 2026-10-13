# 01_02_02 Monitoring / Incident management

- **pageId**: 2304378842
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/2304378842/01_02_02%20Monitoring%20/%20Incident%20management
- **depth**: 5
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované > George - PERF testy na PROD > 01 - PETE infrastruktura produkčního prostředí > 01_02 - Change / Incident Management

---
### Popis:Testování [George API](https://cnfl.csin.cz/x/GZczfw) bude probíhat na třech úrovních : 

- Pravidelné denní automatické load testování
cca 1/3 běžné průměrné produkční zátěže- hodinový běh v nočních hodinách ( možnost 23:00 - 05:00 )
- Pravidelný healthcheck 
1 - 10 klientů- jednorázové provolávání scénáře Overview Journey - 5 min interval
- Plánovaný perf test
postupný náběh se zatížením 120% - 150 % maximální produkční zátěže / hodinu- interval nepravidelný

### MonitoringMonitoring bude zajištěný primárně ze dvou streamů : 

- Byznys monitoring

odchycená WebApi komunikace - kibana dashboard - zachycení publicApi a mep availability
- Monitoring Gatling simulací
výsledky simulací budou odesílány přes logstash

V rámci každého testu chceme sledovat tyto metriky : 

|  **Metrika** | **Co sleduje** |
|  Count | počet requestů celkem |
|  RPS | požadavky za vteřinu |
|  P50 | medián odezvy |
|  P95

 | 95. percentil |
|  P99 | 99. percentil |
|  Max response time | maximální odezvu API |
|  Error rate | procentuální počet chyb |
|  5xx | procentuální počet nedostupností služeb |
|  4xx | procentuální počet byznys chyb |

### Alerting:
