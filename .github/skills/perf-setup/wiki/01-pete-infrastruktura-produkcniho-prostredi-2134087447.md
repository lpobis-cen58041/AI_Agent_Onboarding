# 01 - PETE infrastruktura produkčního prostředí

- **pageId**: 2134087447
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/2134087447/01%20-%20PETE%20infrastruktura%20produk%C4%8Dn%C3%ADho%20prost%C5%99ed%C3%AD
- **depth**: 3
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované > George - PERF testy na PROD

---
## CílV první fázi je primárně potřeba:

- zajistit stavbu infrastruktury pro podporu realizace automatizovaných load testů na produkci- definovat klientskou datovou základnu- naplnit požadavky Compliance a Security- vydefinovat parametry testů a základní testovací scénáře pro realizaci automatizovaných load testů zaměřených na pasivní operace George
**

V další fázi bude hlavním cílem automatizovaně zajistit i performance testy George.

## Prerekvizity pro stavbu prostředí a realizaci testů:
- Vydefinovat, kdo a kde bude infrastrukturu budovat
Vlastnictví a maintenance
Zavlastnění testů - tým George- Zavlastnění infra - TCOE 
- Azure Cloud vs On-prem ( přístup pouze z venku vs možnost testování i MiLa endpointů )
Vyřešit cestu Github - > AZURE VMWare- Azure server vs. nový dedikovaný linux runner- Azure Private Storage vs Private Artifactory

- Přepsat testy z LoadRunner do Gatling- Pevný seznam cluidů v private repository
mix 2000 - 3000 cluidů z různých segmentů ve formátu csv ( v případě potřeby realizace testů jen pro konkrétní segment, budou existovat i samostatné datové sety pro konkrétní segment )- Blob storage () vs Artifactory (georgepete-generic-private-local)

- Automatický mechanismus na získání MEP tokenů ( Access Token ) - Zajištění NFRD- Zajištění distribuční skupiny pro výsledky - TL, IM, DL, G members- Domluvit zda je potřeba řešit pravidelné vystavování Change Requestů pro spouštění denních testů 

## Parametry:
- Load testy poběží pravidelně každou noc v období od 03:00 do 05:00 - plánovaná zátěž cca 3000 RPM ( ~ 1/3 produkční zátěže )- odesílání notifikací o výsledku na distribuční skupinu - ranní report- Pasivní operace - zobrazení transakční historie, načtení overview, náhled na kartu, ... 

## Prostředí
- Provoz
Runner - primárně cloudové řešení
github runner propojit na cloud AKS runner - samostatný AKS cluster - repo na scripty - určené pro vlastní testy, správa spadá pod jednotlivé aplikační týmy- repo na spouštění load testů - readonly access pro aplikační týmy, write pouze pro dedikované lidi z domény- PLÁN B - runnery na OpenShift
myslet na nastavení proxy pro onprem řešení

- Storage
[Artifactory](https://artifactory.csin.cz/ui/repos/tree/General/georgepete-generic-private-local) pro AKS i onprem- TO DO: 
nová síťová konektivita pro AKS a Artifactory - zařídit ACL u Netoličky- návrh adresářové struktury - vstupní data a výsledky testů za jednotlivé testovací scénáře- nahrání csv se vstupními daty ( cluids, ... )

- Monitoring / Alerting 
notifikace do provozu (IM) v případě neúspěšného výsledku testovacího scénáře- v případě úspěšně proběhlého test scénáře notifikovat definovanou distribuční skupinu ( George provoz, TL, ITDL, ... )

- NEXT STEPS 
schéma jak to bude fungovat - schůzka GIT tým, AKS tým, Security - představení- vyřešit financování provozu cloudového řešení- vyřešit connectivitu z cloudu na MILA gateway - existuje express route - IM - předat do provozu- vydefinovat usecase jak budou moci testy probíhat - kdy/kdo/co může běžet

- NICE TO HAVE
Changebot pro automatické vystavení CHR 
nejlépe do Change doplnit i finální výsledek testů - pro ranní jednoduchou kontrolu stavu testu- dokud nenastane čas realizace change(perf testu), tak changebot ověřuje stav change, pokud bude change schválena a později zamítnuta před exekucí testů, tak lze plánované testy zastavit

- Obecné 
striktně omezený a řízený přístup k runneru a storage - REDiM právo - CSIN/GHB_XXX , CSIN/Azure, .... - přístup pouze pro cca max 2-3 členy domény kvůli nutnosti zastupitelnosti a naplnění bezpečnostního požadavku na minimální počet lidí s přístup k PERF testům a vstupním a výstupním datům 

- Registrace aplikace pro prod load a perf testy George (SAS_GEORGEPETE) na MEP jaké bude client_id (AppID - urn:csas:apps:georgepete ?)?

Do aplikace se nebude možné přihlásit, nebude možné vystavit RT (RefressToken)-  Platnost AT (AccessTokenu) bude X hodin (max. 5hodin)- Token bude vystavený automatizovanou action, před spuštěním samotného testu-  Token bude omezen Scopem (PETE)-  Token bude vystaven na konkrétní hodnotu technického MUID- Více: [https://cnfl.csin.cz/pages/viewpage.action?pageId=1920365618](https://cnfl.csin.cz/pages/viewpage.action?pageId=1920365618)

- Vytvoření kopie testovaných API na WebAPI (případně i další API GW)
Duplikované služby WebAPI

Seznam kopie API - George WEB

Publish url : /v1/zatezove-testy-web

CMDB : SAS_GEORGE

[SuperAdmin](https://www.csin.cz/webapi/superadmin/#/?urlObject=eMKcwr1Xw4nCksOcwrgRw73ClQrCnsKrw5zDnCDCtXRrSyVZYS3DrcOuw5YcwqxQTGAjCRAgSABcFcOzJT7DucOowpPCv8OAwr7CjMOnwr_CnGAtw63CkmZ0wrJ9w6kow6bCjsOEw4PDi8OsT1_CokHDsMOxYW55w7Q8UsOCw7nCncOjw5jDkirDmkbDviA8fzPDrMOxwq01WjgQf8KJwqhpPG98w7h5NHkew53Dn8Ocw7_DuHrDv8Ohw67DtcO-w6jDr0DDmHLDq0zCszXCtsOcw6JWw7zCkcOPW8KCacONG8K2LcKtw6nDm8Ktw4LCmjDCvBUMwoIPwoJxwrvChcOQwoUowrdgw5Iaw5HDuMKtw6fCulXDmMOzw63DiMOJH8KMwqnCt8OcWmPDr8K4a03Do8O4wpYqAcKFwrxhw7BHw7gZMjsPw4YhNVYKPsKVw5ACw6pEw7E2KkzDn8Kww6h5w7ZsGzVYw4M5wppeKXDDqMOJw6EzAnPDi13Cr8OAw75TVE1CESEpwqdiwrRiw6JpwqzDqMOcChd7MCsJwpo9asKUa8KkG2QsUMKMeGvCqMOsc1BSTcKwNsOYwqVIWF0POcOWM8KbF8OHZCjCj8OUwpNRw7PCqMKZFMKkScO6LnVdwo5xXcORCcKUWHdEw4Q8wpFYZkLCjEhhNMOHXUVVGzwpw4rCs8K8T8K1wpbCmcKbw5smGTXCsU3DoSwDJcOvSzvCiMK-wq8Tw6HDssKFwrHDlCjDlMOZOS7CsnB5Oh0pQsKUacOJwrTDosKTwp5aNQxZw57CrTkdVy4tR8OUSMKPVMKcw7lsw4nDqhzCi8KsAGXCtcKUw4LDjcKiU8KFQMKuJngcw4VYLkNuQmvCqcKdU8ONSh8vMgV7YgvDm1LCjsOZKENYKgptw7oqw7PCsi7DgX3DiVg9w5Ukwp8GUBZqcsKpwqZVMsKLw4okccKHJsOoZsKVwpUmXsKbwpDDmjZLeSrCpWbCtcKUA8OiE2fCvsOvQ8OYwoJmSVvCmcKJdsKiwqbCs08Ww57CmXzCrH0RPMOLDMKPC8OgwqJzAsK3wotSw40wwo7CqBsWw4HCg3LCkhM3RWbClGxNPMO6WcO0KcOvwq3DtjocJcKFa0zDhsKKwqbDgsOHw7Vgw63ClMO4wr7Ci3NFQsOOwp7Cl0MyMcKsJMOtwpZcASx0wr_CqMKiWQtaUjLClFZOwosYw4kST8KYdkPDrcKZw6NjwrjCssKxclROw63CjGTDn8OIZMKeZ8OjZTvCmiYow5nDgnrCncOlBhdiw6hEQijDiUfDqD9NQ0HDmHbCmcKkwpjCuFnDusK5w5bCrMOHw4McZ8KmVGvCh8KKWsKiDMOgVsKIw47Di8KcWcK9w5RmTsOnOlw2w44XTzLClCTCscOEeMKhVhnDqFdMw5vCvFzDm8KHa8OXw5TCnTBSTcKzGEgywpd4w4hbw54ET8KmUVIaUsOmwrJMwpPCosO3wp7CscK-wpwFwqpXwpjCoFojwrzDuFokQ8OiOiYBfn5Ew6nCisKEcm7CpMOVw45xOcKZeGnCimXDicOrwqonPkDCs8Kywp1UfUzCs0YUSsKNw5xowpLDpcOWNVUacMKbwow5w7JZwpYQUVTCs0sqwpp4w6VRXwbDhGPClMOnwrjDrTxAw4HDsVjCi0pldBrCjVxQw7AswrrCqsOwwrFjRnrCvmgWw4fDliZkEmXDiMKJwpdCw6jDhHRKwogkBQDCpsOcDMKxbsKlXT1dUnrClcKkw57CiGxMw5RSw6nCjsKnwrkuw5cOwpXCgHU7wqAJGwDCvkp1wpLDqyZOw5vCuAkswojCsmccw5PCosOYIcKGwq93eUbCnsOsw4gTVMOsOEbDj8KeFsOoKcOjRQAMwr1mWcOxw6RpwrIjGQHCs8KnwojDrcKuwp9kw5kuw6YIJQjDsWtEwooVdGNRw5B0ZnAyWhtFw6vCrsKbWMKFwpHCiD7Dv8K0wo3ChHvDlcODw4NRwooDaXnDm3PCkMKtw6Row7ULZQIPF1gBA0bCnAnDv8OOwrBvBR_CmsKzw4hyw6BQYRrCoFnCoGQgw4ojw7kFXsK_w6fDvmvDugZOw6DDlMKHw4RfIgF_wr8PwpzDo8KwODJ7BHUWeDBWw7gzw4fCtsKWDw_CmMKcPhs-w7nDtTPCmsOUMzNHw6c6Hi7DhsOOT8ObwosJw4XCuMOHQn3Cm8Ove8OTw4nCjA1MwqBKwrR3RgXCn8KPw7fDuztwOMKLw5_CisKmPg_CgjA5w4Bmw7_DvsOmw7dvw7cvw4PDuwVyw7xoFcOIFlAtZsOgO8KYLX7DnsOBLApAasKGwpPDrwDDocKgwr1gOSTCoSBeYMKYIz_CnMKkByNtaMK9woY7w7bDnsOQw4vCr3vDu8KfAlfCmcOxTcOzAsKOwqZMeUDDgMO2cMK0w4nDg3zDu8O0GcOaw5oTGMObw5VHK8KCIMK6GsKSwqtfKcO0c8K4T8KYDsO0eMKWw4rDu8OWPcK_wroadsKnw5nDqsKiwrPDicOtOSRYw75GQHhfw4pDwqxjFcOww4FtA8OwGsO4w73Dl0HCjibDnmJxKsKacUfCrWjDvcKhXTfCt282wq01G8Ogw7jCusKnYsKzw7zDvFfDv8Kvwr_DvMOyTzPDvMO8D1ptQsOSX8O-wr5pw7DDpjXChyXCgm8gfx8gUMO1GsOGwrY4d8OLw6PDshjCvwApZzc-HC7DpDzDqC_CpW8PW8OBQSXCnMOrw4PDhsOww6XDscKCwqJ3w7Brw7PDscOuw61GwrhNw7DCmH8XXVxRw7TDksOQXgPDiMOWV8K1ccKmwrfClH_DpQDDr8OAC8ONTQ_CmcKyOMKGDcOEUcKzwq5FwqFMw6FuwpQyI2cPw6bClcKxI8K2bB_DnMO-w5RzO8OfYgsbCXTDlcKdH3DDlxvCj0PCjWvDsEdCw5DCjMOcw48OTsO1w77CsMODXDzDo3PCjsO9wrRewpF6wocbXHLCvT7CjmNgasKsw7sBK8OBw5bCk8K8FA7Ck8KVccKOaldhw4vDmcOFwoUeNcK4w7dVw5jCusOowolYwoDCq8OWw4NFwrfDu8K7Vx_DrsOew53CvH_CscO_w7Fhf8O_cMK_QhDCg8K2MMOQwqYXRRkOcsOpwr9vLsOzasOow5zDscOdw6PCtlVHwqsrCcObZBTDuMOETMOzw5nDpcOYwovDgwp4fnMJw4pPwotew7TDp0dUw71tw4XDlMK8w5ltDlA-PsOVwofDo1M4woDDosO_T8K_w58lw5hHOj7CgcO5N8OoNSIkwq7DhsKwXTxSw6x8bcOcwpB9w4PCscKPbMO9w63CvwEeE8OCw5nCrzHDrX_CsQPDkWnDhcKPw74HfTjDjcKVcxsuw7rDvXULPsO_G8O2VMKbw6c)

GET**

/chat-client-profile/public/chat-info

/dashboard/public/settings

/dashboard/public/widgets

/electronicstorage-george/my/electronicstorage/cases

/gapi/colors/ordered

/gapi/my/accounts

/gapi/my/cashflow

/gapi/my/configuration

/gapi/my/images/user-image

/gapi/my/transactions

/info/countries

/investment/public/securities/advertisements

/message/public/temporary-messages

/my/messenger/digest

/my/pensions

/netbanking/my/accounts

/netbanking/my/authorizationLimits

/netbanking/my/cards

/netbanking/my/contacts

/netbanking/my/contracts/buildings

/netbanking/my/contracts/insurances

/netbanking/my/instant-cash

/netbanking/my/messages

/netbanking/my/messages/mandatory

/netbanking/my/orders/payments

/netbanking/my/orders/payments/limits

/netbanking/my/plugins

/netbanking/my/profile

/netbanking/my/profile/data-consents

/netbanking/my/securities

/nfotc/public/flags

/sales/my/promotions

/store/public/my/store/info

**

POST**

/public/insurances/{id}/insurance-payments

- 

**Seznam kopie API - George GO

Publish url : /v1/zatezove-testy-mobil

CMDB : SAS_GEORGE_GO

[SuperAdmin](https://www.csin.cz/webapi/superadmin/#/?urlObject=eMKcwr1Xw4nCkhzCtxHDvcKVwo46d3tqAznDpG1ENmnChsK5woxmwoY6wpjDgWBgwqsqwqDCgEIVwoBaGcO6EsKffMO0w4lfIF1kw73ClxLDlcOLaEjCiSfDm8KXwo5CLsOIRMOiw6Flw7bCh8OPw5Egw7h4N8K3PHoaKcOhw7zDjnFsaRVtI38Qwp7Dlwx7fG3CjRYOw4TCnyNqGsOPGx8-wo8mT8Kjw5vCq8ObTy_Dt8Ovbl7DrsKPw74OwoQtwrfDjjRbY8OLLW7DhcOfw7jCvCXCmMOWwrxhw5vDksKawr7DnSrCrAnDg1vDgWDDs0EwbsK3wrB1IcOKLcKYwrRGNH7Dq8K5bhXDtnw7csOyV2PDqi3Ct8OWw5gbw65aw5M4wr7CpUpAIsKvGMO8CD9DZMOnw4E4woTDhkrDgVIJLSBPFG_Co8OCw7QNwovCnmZPwrZRwoM1wpzCo8OpwpUCwofCnhzClhHCmFvDrnoFw7YfwqJqEsKKCEk5FcKjFRNPY0XDp1bCuMOYwoNZScOQw6xRwqNcI8OdIGPCgWLDhFtDZcKfwoPCkmrCgsK1w4EuRcOCw6p6w4jCscKew5nCvDgmQ3rCpMKewozCmkfDjcKkIE3DknfCqcOrcsKMw6vCik7CoMOEwrojIsOmwonDhDITYkQKwqM5w64qwqrDmsOgSVHCnsOlfcKqwrXDjMOcw5w2w4nCqMKJbQpnGSh5X8OaQcO0fcKdCMKXL8KMwqVGwqHDjsOOccKRwoXDi8OTw6lIEcKiTEvCphXCn8O0w5TCqmHDiMOybsKNw6nCuHJpOcKiRnrCpMOiw4xnS1bDp1hkBSjCq8KlFG4Wwp0qBHI1w4HDoyjDhnIZchNKS8OtwpxqVsO6eMKRKcOYE1vDmMKWcsOMRhnCtsKlwqLDkMKmwq8yL8OrEsOcwpfCjMOVU03DsmkAZcKhJsKXalolwrPCqEwSd2jCgmpWWWnDosK1CMKpbcKzwpTCp1JqVks5ID5xw6bDuz5sW8OQLGkrM8ORTsOUdMO2w4nDgjvCk8KPwrUvwoJnwpnDoXEBXHROw6B2UcKqGcOGEXXDgyJ4UE5yw6LCpsOIwozCksKtwolHP8KLPsOlwr3DlV7Ch8KjwqRwwo3DiVjDkVTDuMK4HsKswp0Sw593ccKuSMKIw5nDs3JIJsKGwpXCpMOdwpIrwoDChcOuF1U0a0JLSsKGw5LDimkRI1nDognDk27CqD1zfAxXNlbCjsOKwqnCncKRw6wbwpnDjMOzbMK8bEfDkwQlW1jCr8Kzw5zDoEIMwp1ICCXDuQjDtcKnaUgIw5suwpMUEzdLP8OXwprDtXjCmMOjw4zClGrCrVBRS8KUAcOcCsORecKZM8KrwpfDmsOMw6lcwofDi8OGw7nDoknChsKSJMKWGC_DlCoDw7XCimnCm8KXa8O5cMOtwprCuhNGwqppFgNJw6YSD3nDi8Kbw6DDiTRKSkPDilzClmlSw7TDnjPDlsKXwrNAw7UKE1RrwoQXX8KLZEhcw4ckw4DDj8KPKF3CkVDDjsKNwrTDmjkuJxMvTcKxLHldw7XDhAdoVsK2wpPCqsKPacOWwohCwqnCkRtNwrLDnMK6wqZKA27CkzFHPsOLEiLCimp2SUUTwq88w6rDi8KAeMKMw7IcwrfCnQcoOB5rUcKpwoxOwqPCkQsKwp5FVxU-dsOMSMOPF8ONw6LDmMOawoRMwqIMMcOxUgjCncKYTgnCkcKkAMOAwpTCmyHDlsKtwrTCq8KnS0rCr8KSw5QbwpHCjcKJWirDncOxNMOXw6VawqESwrBuBzRhA8OAV8KpTnLDncOEaRs3woEFUcO2woRjWhQ7w4TDsMOlLsOPw4jCox15woTCih3Dh8Oow4nDowI9ZsK8CMKAwqHClywrHj1OdiQjYMO2GMKxw53DpcKjLMObw4UcwqEEIX7CiUjCscKCbiwKwprDjgxORmvCo2jDnXUTwqswEsORw4cfwrfCkXAveng4SnEgLW97DsKywpUcwq1-wqZMw6DDoQIrYMOAwogzw6HDnxjDtsK1w6BdcxZZDhwqTAM0C8KUDER5JMK_w4DDq8K3w5x_ScOfw4AJwpzDuhDDuHMkw6DDt8ObZTk2wosjwrNHwpBnwoEHY8KFP3Nsa8O5cMKHw4lpw5nDsMOJwq_Di8OIw5EiScKicx53D8Oaw47Cj8ObBx3CinHCj8KFw7o6w57Ct8K6wpMZG8OoQMKVaG_CjAo-w69vw7c3w6BwFsK_Fk19bgTCoXPCgMONw77DrcOVd8Kvw7fDj8ODw7sFcnxvFcOIFlAtZsOgO8OoLX7DnmlDw5ZMeDPCnMK8B8OYEAoMwrbDg3ogXmDDqCQ_wpzCpAcjbWjCvW54wqzCvsKhD1fCt8O2w7cCV8KZw7FVw7MMDsKnTHnDgMOAw7ZwwrjDiUPCh8O7w7ARCsObE2jDnMOVeyvCgiDCuhjCksKLP0zDtWPCuFPDqBDDtHjCnsOKw7vDlj3CvcK4GHbCp8O-w6rCosKzw4nDtXlTwrDDvMOTLcOhwpUpD8K7HTPCgQXCtw3CgGzDoMK3X25zNMOxFsKLU8Oiwow7akXDqw8lwrvCun7CtWnCrcOZAMOTw5c9FcKbw6XCl3_DusO_w7zDo8OXwp_DjcOww4tPwrTDmsKEwrDCv8O-e8OTw6DDjUsOwqMEw5_CrBnDtAEKVcKvwqF9wotzw408LsKPEQrCkHJ2w6XDgwFDw5TCg8O-wqHDtMO1YTo4wqjChHN9wpgcPsOfX1PDtAbCvjbDr29eb8KEw5sEwo_DuS_DkcKDwovCisKeG8OaawDDm8O6wro2w47DtMKWw7IvHMOgPXjCocK5w6khUhbDhzDCiThqw5bDsSjCpCnDnMKVUmbDpMOsw47CvDB2w4TClsOtwoPDm8O3PcK3w7M1wrYwwplAXcOdw7khd8K9w7E4w6TCuG5-TwzCmsKRw5vDmcOBwqnDnh5mwpnDu8Onw7zDqcOlwrvDqHdhw7bDk3pPw6oNbnDDicO1w7pOwo57U2PDnQ9YCcK2HsOmwrlwwpjCrMOkc1TCuwpbw44ew5zDqlHCg3tfwoUBwozCnjgGaGs9X3TCvcK_ecOxw67DpsONw5XDm2fDu093w7vDm8K7w5sVwokYwrTChcKBSj0rw4pwwpbCh8O-w7vDpmFcDcOFO1IAblt1wrTCusKQMFhGwoFaw4w0wp9dwo7DpThMwoPDp8OHd8KZwpxGwr7DqMOvw7fDiMO6w5fCisKrecKzw5vCnAB9fMK0d8OHJ3EAw4bDv8KfworCv0nCtsO3w5R8AsO0wp9QbURIXMKNYcOSwrjCp1tkMEVfw5HDrT1xf8O9wo_DgGNCOMO7I8OSw70vFiA6TcO7w5HDv8KgDMKnFnPCrsOCwoNyf1nCgsKPwr8BU8OOwpxJ)

GET**

/bff/configuration

/bff/configuration/contacttablayout

/bff/configuration/profiletablayout

/bff/overview

/bff/products/{productId}/transactions

/bff/promotions

/bff/userimage

/bff/userinsights

/bff/whats-new/{platform}/{version}

/chat-client-profile/public/chat-info

/dashboard/public/widgets

/dashboard/public/widgets

/gapi/categories

/gapi/my/accounts/{accountId}/images/image

/gapi/my/fh/calculations

/message/public/bank-messages

/message/public/temporary-messages

/nfotc/public/flags

**

POST**

/bff/notifications/android/registration

- Na kopii testovaných API omezit metody jen na GET (tam kde bude třeba umožnit i jinou metodu je třeba specifikovat a zdůvodnit a garantovat že jiná metoda nezpůsobí problém - mitigace)- Na kopii API vygenerovat APIKey jen pro aplikaci SAS_GEORGEPETE- Na kopii API zajistit ne/propagování těla response volajícímu systému GEORGEPETE - vyhodnoceno individuálně per api a případně i per metoda- Otestovat, že provolání všech kopií testovaných API nezpůsobí nechtěný scénář na backendu služby, příklad:
Volání se ne-objeví v:
Regulatorním reportingu- Trace, Cognos a z archivu (PASY)
aby nebyly zavádějící pro klientské dohledávky a business reporting
- Přehledu provedených operací, které může nahlížet klient např v SSP (SelfServicePortal)
- Neovlivní business logiku
Vyčerpání pokusů dotazů na konkrétní produkt- Ne-spustí busines akci, kterou by u daného produktu vyvolal GET request- ...
- Máme speciální CorrelationID pro PERF test pro dohledávku volání
correlation-id: "ffffffff-PeTe-Test-call-stampfffffff"

## Audit
- Auditní stopa + odeslání na CML (Centrální Management Log - Aleš Nedbálek)
Nahrání seznamu Cluidů do Artifactory - **Je to potřeba?**
Kdo nahrál+seznam cluidů+kdy: Datum+Čas**

- Vystavení tokenů na MEPu 
Cluid+hash_vraceneho_tokenu+client_id(georgepete)+Datum+Čas
Zprocesovavam input(JMENO_SOUBORU), incializovano GH_USER
- Uložení tokenů do Artifactory - Je to potřeba?**

Kdo nahrál+hash_vraceneho_tokenu+kdy: Datum+Čas

- Přidání client_id(georgepete) na API na WebAPI (případně jiné API GW)- Přidání metody (obecně modifikace) mimo GET na vybraných kopiích testovaných API- Vyčtení tokenů z Artifactory

Kdo přistoupil+kdy: Datum+Čas- Přidání oprávnění read/write

- Spuštění testu, ukončení testu
Kdo, kdy bylo spuštěno, kdy bylo ukončeno
V GitHubu bude možné dohledat, kdy byl test reálně spuštěn, kdy doběhl i jestli byl spuštěn automaticky nebo manuálně a v tom případě i kým

## Penetrační testy - scope
- Zabezpečení testserveru odkud se bude spouštět load test
omezený přístup do speciálního repa dedikovaného jen na spouštění testů
- Jak je zabezpečeno úložiště tokenů 
Private repo v Artifactory - omezený řízený přístup- Vygenerování a uložení tokenů proběhne bezprostředně před začátkem testů- Po doběhnutí testů dojde k automatickému promazání/smazání složky s tokeny
- Jak je zabezpečeno řešení na MEP, které generuje tokeny- Jak je zabezpečeno, že nebude možné provolat standartní API, tj. testserver se nezavolá na jiné endpointy než připravené
řízeno na základě apikey - povolené BE - /v1/zatezove-testy-web , /v1/zatezove-testy-mobil

- Zda nejde realizovat volání přes vybrané endpointy, které by mohly generovat nežádoucí dopad na služby (rozuměj aktivní operaci, nebo stopu, kterou by mohl klient, regulátor identifikovat), korektně fungující monitoring nevalidních scénářů atd.
