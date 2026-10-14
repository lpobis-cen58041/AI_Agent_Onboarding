package cz.example.perf.simulations

import cz.example.perf.usecases.SampleUseCases
import io.gatling.javaapi.core.CoreDsl.constantUsersPerSec
import io.gatling.javaapi.core.CoreDsl.global
import io.gatling.javaapi.core.CoreDsl.scenario
import io.gatling.javaapi.core.Simulation
import io.gatling.javaapi.http.HttpDsl.http
import java.time.Duration

class SampleSimulation : Simulation() {
    private val baseUrl = System.getProperty("baseUrl", "http://localhost:8080")
    private val durationSec = System.getProperty("durationSec", "30").toLong()
    private val rps = System.getProperty("targetRps", "2").toDouble()

    private val protocol = http.baseUrl(baseUrl)
    private val chain = SampleUseCases.all.first().chain()

    init {
        setUp(
            scenario("Sample").exec(chain)
                .injectOpen(constantUsersPerSec(rps).during(Duration.ofSeconds(durationSec)))
        ).protocols(protocol)
            .assertions(global().failedRequests().percent().lt(1.0))
    }
}
