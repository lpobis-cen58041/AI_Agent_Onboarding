package cz.example.perf.setup

import cz.example.perf.config.Config
import io.gatling.javaapi.core.CoreDsl.constantUsersPerSec
import io.gatling.javaapi.core.CoreDsl.global
import io.gatling.javaapi.core.ScenarioBuilder
import io.gatling.javaapi.core.Simulation
import io.gatling.javaapi.http.HttpProtocolBuilder
import java.time.Duration

abstract class SimulationSetup : Simulation() {
    protected fun run(scn: ScenarioBuilder, protocol: HttpProtocolBuilder) {
        val duration = Duration.ofSeconds(Config.durationSeconds)
        setUp(scn.injectOpen(constantUsersPerSec(Config.usersPerSecond).during(duration)))
            .protocols(protocol)
            .assertions(global().failedRequests().percent().lt(Config.maxFailedPercent))
    }
}
