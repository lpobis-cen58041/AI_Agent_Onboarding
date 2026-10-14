package cz.example.perf.config

import io.gatling.javaapi.http.HttpDsl.http
import io.gatling.javaapi.http.HttpProtocolBuilder

object Protocols {
    val api: HttpProtocolBuilder =
        http.baseUrl(Config.baseUrl)
            .header("Content-Type", "application/json")
            .header("api-key", Config.apiKey)
            .disableWarmUp()
}
