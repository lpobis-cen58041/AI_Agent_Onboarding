# 01 - GEORGEPETE - Přístupy - Vývoj

- **pageId**: 2318991891
- **status**: draft

---
Tato stránka slouží jako základní onboarding pro vývojáře, kteří potřebují přístup a lokální prostředí pro práci s projektem **GEORGEPETE**.***Odkaz na GitHub* - [https://github.com/csas-dev/georgepete-georgepete-performance-test](https://github.com/csas-dev/georgepete-georgepete-performance-test)

Obsah

- [1. Přístupy do prostředí](#id-01GEORGEPETEPřístupyVývoj-1.Přístupydoprostředí)

[1.1 Produktový Redim](#id-01GEORGEPETEPřístupyVývoj-1.1ProduktovýRedim)
- [1.2 Testovací Redim](#id-01GEORGEPETEPřístupyVývoj-1.2TestovacíRedim)

- [2. Co je potřeba pro vývoj](#id-01GEORGEPETEPřístupyVývoj-2.Cojepotřebaprovývoj)

[2.1 Java](#id-01GEORGEPETEPřístupyVývoj-2.1Java)
- [2.2 Maven](#id-01GEORGEPETEPřístupyVývoj-2.2Maven)
- [2.3 IDE](#id-01GEORGEPETEPřístupyVývoj-2.3IDE)

- [3. Užitečné odkazy](#id-01GEORGEPETEPřístupyVývoj-3.Užitečnéodkazy)

## 
1. Přístupy do prostředí**### **1.1 Produktový Redim**Pro vývoj v produktovém Redim je potřeba založit Windows request na následující skupiny / role:

- 
CSIN\ART_GEORGEPETE_DELETE- CSIN\ART_GEORGEPETE_READ- CSIN\GeorgePete_Viewer- CSINIGHB_DEV_GEORGEPETE_WRITE- XUC\APIMAN_DEVELOPER

### **1.2 Testovací Redim**Pro testovací Redim je potřeba založit Windows request na následující skupiny / role:

- 
CSINT\GeorgePete_Viewer**- CSINT\Alfred_Authentication_Users
- CSINT\Alfred_Performance_Testing

## 2. Co je potřeba pro vývoj**### **2.1 Java**
- 
Pro práci na projektu je vyžadována - JDK 17. **- Pokud není JDK 17 nainstalována:
založit ticket do ServiceNow na instalaci Java JDK 17  -> [Instalovat software](https://csasprod.service-now.com/esc?id=sc_cat_item&sys_id=5f8c2a80dbc4638034def5e51d96198b)

### 2.2 Maven*****Poznámka**: samostatná instalace Maven obvykle není nutná, pokud správně funguje JDK a projekt je spuštěn přes wrapper.*

****Projekt používá Maven Wrapper, tedy build se spouští přes mvnw.
Minimální ověření, že prostředí funguje:
*
*

*./mvnw -q test-compile
*

### 2.3 IDE**Doporučené vývojové prostředí: **IntelliJ IDEA Community Edition.
**

Pokud nemáte vytvořte prosím požadavek v ServiceNow: [Instalovat software](https://csasprod.service-now.com/esc?id=sc_cat_item&sys_id=5f8c2a80dbc4638034def5e51d96198b)

## **3. Užitečné odkazy***Apiman: [https://apiman.csin.cz/dashboard](https://apiman.csin.cz/dashboard)
Artifactory / repozitáře: [https://artifactory.csin.cz/ui/repos/tree/General/accman-helm](https://artifactory.csin.cz/ui/repos/tree/General/accman-helm)
Alfred – generování tokenů: [https://alfred.csint.cz/performance-tests](https://alfred.csint.cz/performance-tests)*
