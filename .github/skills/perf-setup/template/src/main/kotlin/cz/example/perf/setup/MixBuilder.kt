package cz.example.perf.setup

import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.exec
import io.gatling.javaapi.core.CoreDsl.percent
import io.gatling.javaapi.core.CoreDsl.randomSwitch

object MixBuilder {
    fun fromDefaults(useCases: List<UseCase>): ChainBuilder {
        val enabled = useCases.filter { it.defaultWeight > 0 }
        require(enabled.isNotEmpty()) { "No enabled use cases (all weights <= 0)" }
        val sum = enabled.sumOf { it.defaultWeight }
        require(sum > 99.99 && sum <= 100.000001) {
            "Enabled use case weights must sum to 100, got $sum"
        }
        return randomSwitch().on(enabled.map { percent(it.defaultWeight).then(exec(it.chain)) })
    }
}
