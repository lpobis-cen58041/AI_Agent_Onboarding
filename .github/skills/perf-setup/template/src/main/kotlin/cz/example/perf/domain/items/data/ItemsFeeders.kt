package cz.example.perf.domain.items.data

import io.gatling.javaapi.core.CoreDsl.csv
import io.gatling.javaapi.core.FeederBuilder

object ItemsFeeders {
    private const val basePath = "items"
    val users: FeederBuilder<String> = csv("$basePath/items.csv").random()
}
