package cz.example.perf.flows

import cz.example.perf.requests.SampleRequests
import cz.example.perf.steps.SampleSteps
import io.gatling.javaapi.core.CoreDsl.exec
import io.gatling.javaapi.core.ChainBuilder

object SampleFlows {
    val browseItems: ChainBuilder by lazy { exec(SampleSteps.loadUser).exec(SampleRequests.getItems) }
}
