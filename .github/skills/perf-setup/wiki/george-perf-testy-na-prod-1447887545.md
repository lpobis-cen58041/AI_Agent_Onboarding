# George - PERF testy na PROD

- **pageId**: 1447887545
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/1447887545/George%20-%20PERF%20testy%20na%20PROD
- **depth**: 2
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované

---
# Základní popisCílem aktivity je zajistit dlouhodobou výkonnostní stabilitu a kapacitní připravenost George a připravit kompletní infrastrukturu pro realizaci automatických load testů na produkčním prostředí.

Zahrnuje to :

- příprava podkladů pro testy - cluidy, účty, tokeny, business data...- definice základních parametrů testů - VU, RPM, doba testů, čas spouštění- zajištění dostatečných kapacit pro nočních realizaci testů - vlastní runner, ... - tvorba automatizovaných load testů spouštěných přes GitHub Actions
## Motivace
- Minimalizovat riziko výkonnostních incidentů - Zvýšit důvěru ve škálování platformy - Mít možnost pravidelného ověřování dopadů nových přírůstků do George- Průběžně monitorovat stav George- Identifikovat kapacitní limity a optimalizační příležitosti
## Metriky úspěchu
- možnost spustit load test bez manuálních zásahů

- pravidelné load testování kritických pasivních scénářů

- definovaný a schválený model testování aktivních operací

- ověřený maximální počet současně aktivních uživatelů v George na základě login load testu

- znalost kapacitního limitu George a jeho pravidelná validace

## Základní testovací USE CASE
- Login do George

- Zobrazení Dashboard

- Zobrazení transakční historie

- Náhled na kartu

## Příprava testovacích datK realizaci testů budeme využívat stávající reálné uživatele se kterými budeme provádět primárně pasivní operace bez jakékoliv možnosti editovat cokoliv. Definovaná množina klientů zahrnutých v testovací skupině bude, ve formě csv souboru, uložená na private artifactory repozitáři se striktně řízeným přístupem k datům. Stejně tak zde budou případně uložena i business data nezbytně potřebná k realizaci volání některých API.  

## Oblasti k řešení
- Identifikace testovacích scénářů a analýza jejich dopadu- Příprava testovacích dat 
Klienti- Účty- Karty- Identita
- Testovací data a operace nad testovacími daty nesmí:
být reportovány do ČNB a pod- generovat úkoly na bankéře, KCP a backoffice- výrazným způsobem ovlivnit účetnictví,- komunikovat se systémy mimo banku, atd.
- Příprava testů dle [testovacích scénářů](https://cnfl.csin.cz/pages/viewpage.action?pageId=2134087449)

### Odhady pracnosti za klíčové systémy/oblasti
|  **Oblast/systém** | **Odhad** |
|  
 | 
 |
|  
 | 
 |
|  
 | 
 |
|  
 | 
 |
|  
 | 
 |

# Jira

    
        
    
        
    

        
            
                | 
                 | 
                                                                         **Key
                            ** |
                                                                                                 **Summary
                            ** |
                                                                                                 **T
                            ** |
                                                                                                 **Created
                            ** |
                                                                                                 **Updated
                            ** |
                                                                                                 **Due
                            ** |
                                                                                                 **Assignee
                            ** |
                                                                                                 **Reporter
                            ** |
                                                                                                 **P
                            ** |
                                                                                                 **Status
                            ** |
                                                                                                 **Resolution
                            ** |
                                                            

                                                                                    | 
                     
                        

                            

                                

                                    [Authenticate](https://cnfl.csin.cz/plugins/servlet/applinks/oauth/login-dance/authorize?applicationLinkID=aaa7f4ef-1f50-3158-bf4b-16bfdfbb5396) to retrieve your issues
                                

                            

                        

                     |
                

                            

        

    

            

                            
                                            [
                                No issues found
                            ](https://csas.atlassian.net/secure/IssueNavigator.jspa?reset=true&jqlQuery=%22Parent+Link%22+%3D+DAF-332673+AND+issuetype+%3D+Epic++++&src=confmacro)
                                        
                                

        

    

# Otevřené otázky + TODO
