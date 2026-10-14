package cz.example.perf.steps

import io.gatling.javaapi.core.CoreDsl.csv
import io.gatling.javaapi.core.CoreDsl.feed
import io.gatling.javaapi.core.ChainBuilder

object SampleSteps {
    // Feeders can only be created inside a running Gatling simulation, hence lazy.
    val loadUser: ChainBuilder by lazy { feed(csv("sample-users.csv").circular()) }
}
