package cz.example.perf.requests

import io.gatling.javaapi.core.CoreDsl.exec
import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.http.HttpDsl.http
import io.gatling.javaapi.http.HttpDsl.status

object SampleRequests {
    val getItems: ChainBuilder = exec(
        http("GET /items")
            .get("/items")
            .check(status().`is`(200))
    )
}
