# 02 - Testovací scénáře

- **pageId**: 2134087449
- **url**: https://cnfl.csin.cz/spaces/tablety/pages/2134087449/02%20-%20Testovac%C3%AD%20sc%C3%A9n%C3%A1%C5%99e
- **depth**: 3
- **ancestors**: Tablety Home > Analýzy > 1. Rozpracované > George - PERF testy na PROD

---
# PopisPro realizaci automatizovaných load testů zaměřených primárně na pasivní operace George ( načtení overview, zobrazení transakční historie, náhled na kartu, dostupnost mep metod, ... ) je potřeba vydefinovat seznam api.  Aktivní operace jsou v rámci produkčního testování úplně vyjmuty ze scope.

Všechny api, které jsou volané přes WebApi, jsou převystavené na speciálních BE pro webový a mobilní svět zvlášť - /v1/zatezove-testy-web a /v1/zatezove-testy-mobil.

Api pro kontrolu dostupnosti autorizačních metod a veřejné json soubory pro podporu mobilního George jsou volané přímo.   

**

Standardní byznysové Gatling simulace zajišťují řízené generování zátěže přímo na dotčené endpointy.  

Overview - web a Transakční historie - web** se spouštějí v rámci jedné produkční simulace **Overview**.

**Overview - mobil a Transakční histori**e - mobil se spouštějí v rámci jedné produkční simulace **MobileOverview**.

**Náhled na kartu - web, Náhled na kartu - mobil, PublicApi a AuthMonitoring** se spouští každé ve své **vlastní simulaci**. 

**

Další Gatling simulace OverviewJourney** ( web i mobil ) umožňuje spustit scénář pokrytí plného průchodu Overview nad jedním klientem.   

### Seznam API

**WebApi endpointy

|  **BE

[https://www.csas.cz/webapi/api](https://www.csas.cz/webapi/api)

** | **API** | **POPULACE** |
|  [/v1/zatezove-testy-web](https://www.csin.cz/webapi/superadmin/#/?urlObject=eMKcwr1Vw41uw6M2EH4VwoFnwrnDvsOZGAVycxMlDcKaH8OXdsO2w5AgWFDDlEjCok3CkQpJw4lWwoJ9wpLCnnrDrGnCn2B7w5nDrnt1KMOJcsKUw6zDplAUwr0Iw6JwfsK_wpnDuXjDt0RKDsObVcKVAzkmwoIbOzBANUvCiU9sI8Osw44RwrV0wq5Vw4YNworCnwhTw5LCgsK0w67Ct1U5JsKPw5TDgsKjKsKhwrU2KMOKQRslfcKlE8Kfw6bDvBfCqMO8wpDCsg3DiMOIT8K0KnJfw5AswozCqMOPI3Rdw7IIwrTCj8KOY8Kew7jCqMKSKy7CrW8hw4sFOsO2wrcQw77CrMOUw4YHwq3ClV7CgMOJwpU0w6Azw4Exwo3Ciwg_w5xWGMOZWFR2wqHCqRB4FDzDo8KYw6V0w6TCk1gVMiLDhxPCn0jCmmERwrIQAsO1wovCsDkSw5TDlmAKwoHDqnckZnRjw6TDpsKBwqvCtcOYVcK8DMOHVULDi8KjHCTCqiUPIsOWw6V0RxU3wpXCmGTDo8KjTMKOJsO5SMKmw6TDvsKjT8K4OStEw4zChQAMZ3UBKMKrw4vDksOZwolQDsK_wpgKw4zCnUDDhMOtwpXCil4LbmQnw5LCgMOVcyURIAQTS2zDs3bDvVjCgsOtw4NuQADCsy7DrBPDocO4fcK7wozCtsOFbUcIZhnDk1Jpbjtwcg3DpcKKwobDu8KjwoTCncKtwo9kw4LDtcK7wqkkXRrCq8OewrR8w7R7woMVwoHCpVzCvA7DuMOWUMKpwq3DhMORSXnCvlDDgsOZw5wuwoMFGnTDoksuN10LXcOLUSfCuMKew710GcKcwqJaSA3DnGrDsQzCnAEOwoXCrQY4RHgNwrLDnMObwpbDqA7DkUXDjXLDrBLCgsKYw6IEwrzDn0sbwqVMwrFNw63CrsKFXsKxw75pwqnCnwtMwqrCthfDsgRLEyppBsOAb0rDm1kcw4zCu3vDhMK1CHHDm8OSW8ONwp3CgAzDi8Oxw7AbwonDnsK7wobDqsKSwrPCtsKWw5TDmsOcHA_Ch8OlYMK_FMKGdCrDs8OOJWp-w4fCocKPS2HDkVfCmwUeQEvCnMKuEsKWL8KdwrQqVlPCvk86AsODNMOPbQPDl2x-w6HDpVp5wrDCg03DgcK4w7fDuMOlD8O7w7fDr1_Dv1LDpcKXw48sw7Vcw5DCr8KfPEnCvXPDgMOtBw_DoxduBMOSIsODwoXDox1awpYmwq3DvxjCpRDDjcKsK8OOw4Vsw67Du8OSw4tmwp3CmytuTMOhVsO9w6nDkCBywoV_w57DrcOiw5LDo8OGcxbDlQ_CpMOXInLCqljCkcOhwpDDlUvDpRlVaAYvDHARLMOPQBUYw6nDnWjChMOUYcKYwqrDucOMwqXDicONTAjCtcKFaMKlw47ClMOeUh0Fw47DrMOXAnQ1wqcawrkEUTXDncO-PhTDilLCl2PDrcO8w4AHWRQuK8KDVV03w6zCs8KcLT_CnAc3wovDs8KAPMKLEcOsw6oWwokrKmkCWcK9HMKtY8KmwrR5TwXCj8OqSk7CucKhYU04w63CtUnCqcKGwqjDl8OQw7bChhY2dXTDicO2wrzCglRVF0fDpsOBw6LDrGZxNcK7Pgk-wqzCgsOlalnCjyDDhcObWCFMJ3HDogrDqcObB8KyHzdDw6TDmsK9wqd5LlrCrcOhGsKfAcOiCEXDrcKqw47CpMOFwqLDocOubsOnw4bDkx_DtxRNfjtMw5XCn8O1TFXDnsOAa0bCuV3DlVXCuwrDjVDDvMO_w6zDuybDgx7DuHg_w4zDn8OhV8KSwpTDsS7DjsOJc8KOwp0mLMKpw5JXHHvCoMOrw5fCr8K3wqVhCMORwrfCmMO2P0TCgMOsw59mw7IvcGjDnyXCti4ewrLCjMKlw4nDkXptHsOpelREwpEMJ2zCmx_CksOvw4LCvMO1MB1ewqIOwrhewodewoJ2w78PexouSw) | /chat-client-profile/public/chat-info | Overview - web |
|  /dashboard/public/settings |
|  /dashboard/public/widgets |
|  /electronicstorage-george/my/electronicstorage/cases |
|  /gapi/colors/ordered |
|  /gapi/my/accounts |
|  /gapi/my/cashflow |
|  /gapi/my/configuration |
|  /gapi/my/images/user-image |
|  /gapi/my/transactions | Transakční historie - web |
|  /info/countries | Overview - web |
|  /investment/public/securities/advertisements |
|  /message/public/temporary-messages |
|  /my/messenger/digest |
|  /my/pensions |
|  /netbanking/my/accounts |
|  /netbanking/my/authorizationLimits |
|  /netbanking/my/cards | Overview - web

Náhled na kartu - web

 |
|  /netbanking/my/cards/{id} | Náhled na kartu - web |
|  /netbanking/my/contacts | Overview - web |
|  /netbanking/my/contracts/buildings |
|  /netbanking/my/contracts/insurances |
|  /netbanking/my/instant-cash |
|  /netbanking/my/messages |
|  /netbanking/my/messages/mandatory |
|  /netbanking/my/orders/payments |
|  /netbanking/my/orders/payments/limits |
|  /netbanking/my/plugins |
|  /netbanking/my/profile |
|  /netbanking/my/profile/data-consents |
|  /netbanking/my/securities |
|  /nfotc/public/flags |
|  /public/insurances/{id}/insurance-payments |
|  /sales/my/promotions |
|  /store/public/my/store/info |
|  [/v1/zatezove-testy-mobil](https://www.csin.cz/webapi/superadmin/#/?urlObject=eMKcwr0Xw4nCksOcwrbDtVfCunjDrsKOAC5jwo1uE2nCrMK4IlnDssOMw4jCh8KoVCpsJB8IECQALsKgw4pfwpJTwo45w6ULwpLCi8Ojw78Kw5DDk8OTw7JYwrZPSS7DncKNwrfDr8Ovw7XDu0_DmQxiwrkLwoPDiMKeZQrCnD84QSxrwrN9w6bDr8KBw6c3J8KewrzCtUbCg8KLw6BPGTPCvRfCvU8_TyTDj8Kywr_DvMO4N8O_w6_Cv8O-w7QvM8O_w7jDt8KdF8OOwofDncOhJMOJRcO0IMKsM8O9w57DmGZPBsO4wrMIe0pYJ3rCvm_CrMKZwobCvSLCmnLCsgcew5XDjMOAwoXDnUclNTTDu0gyGMOow73Dngs9KMOiw4V-EcO0T8OGdHthwq3CsTfDgg3Cpndiw48URMKTwr7DocOxA3zCiMKawp3Cj8OESTVRKj4VaMKIFldowp_DlWbDqnnDtgzDozzCr8O2WU90dMKqwp_ClMKKPBPCvX9mwpHDgwo3wqnDiMOyPsKrGcOpXMOfwo1gwqRaA8OMFMKHwobDjMOlIMO6SMOWwozCqsK2c8K1EgMuwqhcw6NSw7coH1DCnwLCl19SwoEQw6XCh8OyacKFDmXDvsOVw4XCgV5ifsOAIsKvw5gFIxUSeSTDg8Kiw47Cn8OSw4vCi0PCgcOySEvCnl4cLlEkw4tzXAhBSMKdX8KISHZZwpYCw6Vfw5EDLcOKw7xQUkYPwpc5wq0Pw6VFUWLDvsK0eFpyEsOJKMKrw4rCosKccsKtZcOhw4LDkMOjRVPDm8OXw47DssKIFEpKZETCuzhpw4vDjcKMwrQsCsOIB1HCuMKIbCnDkwBMwq_CuWxLEMKmBhvCv8OlcsOkbGhdV3YuOyc7w5wRwo3DpFTCu8K-w6rCtjoiGcKuV2jCsMKHGsKGfMODfBJDP8OWDcKiVcOiJA3Cq10OXQfCuAbDniI5wrLDlW0tTcKJw6HCpm3DusKWI8K7AcK3wopMC8KwwoDDjFDDp8OJwqBYFSEswpRUFRQjan01WsOAwpPCrsOWFDXDgWTCiUl0wqzChsKANkbCtMKaAcKbwq0vwpJOUsKMa14rRcK4HMKXwq7Dr0LCocOyemjDgzFCwqw2w5ptwqswAGbCgxljworDlMOQOTzDqyRWQ2BKw6vDiUBVQGVyUngxQsK0PsKJw61DwqtjQMOdAEEhwrHCumrDosOlNErClsKQwqwwRcOZw5jCvsO0Um4bw5_CuF_Ds1wKwrw0ScKsccK2wpMtD8KNFAbCsWjDr8KAHG7CrUNJLMKywoVuVsK_VjErHS3CmTXCijZEwoLCjMOIWsOjw5wuIcOQACYZw4Ykw51qw4fDqybCuVLCr8OBw7TDoFXDkcOAXCIgwoNATjbDtVhDMih3wrPDhEvDi3LDsMKowpvCrV3CscKfRlQqwpo4wr0Aw6_DmjAwaQxuZ8K6SlrChnIZfEIuw57ClsKzFsKmA8OlQlXClEjCtH3DkcKIZUplUsKhwqXCpsK4YcKDNEhtRTR6WUoZRsKWwpIdM8OQwpRbLHDDqQnDmhRBeTnCmMK5IynCnzULwqvDhExNATjCg37DiWluwrEzSMKvSWxPw6lIw7tqKiTDs8Kha0Zdw4zCnjUEwqXDsMKxWENqwp46HmQxw6MCwovCslPCmsK2DsOhY1bDhALCsR1hwoPCkgfDn8Opw43DusKqwpMqT8KcwpRWwqUswoHDmALDlnbCq8K8ZsK6wqlwwrfDojlZa8O1EAzCrcOcCMKrwpFDLkbDnhUxwrhzw6rCt8K6w4vCvUPCshwbw5BlGMKLwrVrBhPDpMOSwqZ2IG5hIsOvwqLCocKww6Uyw5TDuTbCqWrCqDErwpMrwoTCs8ONYi5ANitawrsCSDDCqDJ1w4onURV0TVvCjVjDqhEHJMKawoVXw6vCtMOQwoRkwqzCm1hVN2LClsKyC8KODsKdw6bCvkPCiMKkworDpyVyAsKPaMO2EjsoeDfClXlhW29SwrJpwrnDhULDtQvDtsKyw7BSFQo3YcOOwp1cUsKZCFsVW8K7GR3Dm2vChMKJF8OVwqwGPSxrwrLCljQjwp7ClsK2XTTDpHjDqxQTw7PCtnhPanVsw4HCkQISWBJZACzClSJVQGPDi8OUwpAiJMKmw5guAxEIZkDDnWLCpGYLw7jDksKNw4fCgVEFX8O1w4rDtTLCliHCggpVYjBMTklnI3phwol6fsKcw7LDiUA_wpnCnBXDlcOUScKbK8ObLD3Di8K7wonDtHlSIwLCpmzDq8OqAQPDtCoawq7Cp8KCw5HCjh1nbMKNFsKCw4PDlMKVRBINwrU2wrzDqjzDkGrDg8OZwocfw7YZwrjCrydVwoNSIsOOfG8nEWHDh8OdYsO1c2XDkkLCq8KJwooLJBMcw7xrw4PCvwTCvMOpw48gK8OiCgLDk8OHLRU3WsOcM8Knw4XCkRbDpMKtw7DCv8K9B8KdUMKCw7lkw4LCpwzDosOnw6_Cr8KNw5PDvj3CrcOILFpcwpPDmVjDsMOnTTVYMcOfEcO6w7DDrMOFw6rCj8OPw6wiwpRsw6DDmcOZwqTCu0fCq8O8wofDvcKjwq3Dj8KFJ8Kgwr5Uw7h7G8OfLDFxwq7ChcOhw4bCqMOEw7PDrsO2w7omMsKcw4HCr8Kgw6_DjsO7NMOtw6BIc8O9w63DlR9fXcK_SEVKwpx4Z1XChG0RwrXCmVkcwo5BOmhDwo_ClsKIfn7DoMKewqPDgBjDq0g7wqcmw6fCoiZxIX_DvwDCvSfDksKGdUfCgcKnRBjDtsO4dWt_DnDCrVnCvsOpwp9Hw6fClGnDrsOLYX_Dr8Ocw6rDo8Ktw7DDvkPCjMOsRMOjMcOUwr7Cs8KQAMOZwpMZP8O5VVM_wqTCpMOaGcOYw4nCn8OWw7vDgT17w7JkPjxcKi47wpPCvD0Lwo3ClMK_KTLCjQYfwqXCnSzCiQ9hw7tYb8KzwrjDvcKlwpgTwonCtwQeDMOnw4IxC8KDwr8Pw5nDlcObb3bCgzU7wrHCijhQYMK3fcKuw4t_wrLDtljCmT_DvWPDl8KTw51LEcKPMsKxO1rCkMKGwrtvJx3CryA4w4fDjMKTw6bCpMKhwo5Qw4HCr3xyMGnCvcOHP8KGwr7CusK_wrPDrlHDoMOcwpRuwrBPwp_Dk8KUwr3CjsK_dsOvbl7DrcOAw60SR8O4Q8O2KFHDmQvDgyYdwovDrcOYaDtnJsOLw4QvGGJDeMKIw4tpworCmgrChMOiTcOnwpg5HsKaw4lMcFdKwplFw7A7w7PCtcKxC8Kxw7w6wrF9Nwkbw54SGw_CvBhXd8Ouw6lxMsKeJBvCj8OCP8OPCMONw6ltcMORwqtvw69Pw4LDm8Krw5vCjy_Cr8Ofw5zCvMK8w77DuMOyTcO2MzXDl8OrMU_DqjXDqUkjw7TCsU9OwrLCmcKxw657wqLCgB_CnXkBwo7DkMOjHDrCoV1LwqzDoMKPwrJ6w4LCkMOJwrfDqcKUZQ_DoyZOwrDCo3_DmcObw6vCm8Kvw5_DnMK8wr7DusO2w7nDtcOHwrvDq8ObwrvDm2MlwpLCiMKtTcKMw5TDs8K6ScK-PMOmwr_Drh_Dq8OVMXjCpxFAwoZBwp3CqMKew4h4wqJnacK2wpg1wpxZTsOhwrjCv8Krw4_DjcO3wrR4wrjCnH91w6LDrR4Kw7rDlMK0d8KnwpbCuC_CjMO_w79Uw77DnWnDu3k2PxTDtG_DjMOawowswpcXwr3DjX4-b8O7wqHDncKEw75iw55-HsOdX8O-w43DssKEUsOBf23DqsO-FyPCkD3DvHHDisO-B3E4L8KZcxweBcO8wpcxw7jDsB_DlBQVFw) | /bff/configuration | Overview - mobil |
|  /bff/configuration/contacttablayout |
|  /bff/configuration/profiletablayout |
|  /bff/notifications/android/registration |
|  /bff/overview | Overview - mobil

Náhled na kartu - mobil

 |
|  /bff/products/{productId}/extras/{extrasObject} | Náhled na kartu - mobil |
|  /bff/products/{productId}/transactions | Transakční historie - mobil |
|  /bff/promotions | Overview - mobil |
|  /bff/userimage |
|  /bff/userinsights |
|  /bff/whats-new/{platform}/{version} |
|  /chat-client-profile/public/chat-info |
|  /dashboard/public/widgets |
|  /fit/public/my/updates |
|  /gapi/categories |
|  /gapi/my/accounts/{accountId}/images/image |
|  /gapi/my/fh/calculations |
|  /message/public/bank-messages |
|  /message/public/temporary-messages |
|  /nfotc/public/flags |

Public endpointy

|  **BE

** | **API** | **POPULACE** |
|  https://george.csas.cz

 | /lang/mobile/ios/cs/Localizable.strings | PublicApi |
|  /lang/mobile/android/translations_cs.json

 |
|  /bff/georgego/versions.json |

AuthMonitoring endpointy

|  **BE

** | **API** | **POPULACE** |
|  https://prod-bezpecnost.csin.cz

 | /idport-fta/api/v1/int/availability

 | AuthMonitoring |

Jednotlivé metody se volají na základě parametrů transactionType a riskLevel.recommended v requestu služby. 

Volané služby:

- authz_non_financial_adaptive- authz_non_financial_bio- authz_non_financial_sec- authz_financial_adaptive- authz_financial_bio- authz_financial_sec- authz_financial_over_limit- document_sign_bio- document_sign_sec
Příklad pro authz_financial_adaptive:

authz_financial_adaptive**

```
{
  "identity": {
    "aliasType": "CLUID",
    "aliasValue": "semCLUID"
  },
  "appId": "GEORGE",
  "extTransactionId": "tadyGenerovatnahodneTRNID",
  "transactionType": "authz_financial",
  "transactionAmount": {
    "value": 0,
    "currency": "CZK"
  },
  "riskLevel": {
    "recommended": 1
  }
}
```
