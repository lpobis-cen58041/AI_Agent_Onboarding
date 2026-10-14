package cz.example.perf.domain.items.requests

import cz.example.perf.config.Paths
import io.gatling.javaapi.core.CoreDsl.exec
import io.gatling.javaapi.http.HttpDsl.http
import io.gatling.javaapi.http.HttpDsl.status

object ItemsRequests {
    fun getItems() = exec(
        http("Get Items")
            .get(Paths.itemsList)
            .check(status().`is`(200))
    )
}
