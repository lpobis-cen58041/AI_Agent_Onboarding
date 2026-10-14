package cz.example.perf.domain.items.flows

import cz.example.perf.domain.items.requests.ItemsRequests
import cz.example.perf.domain.items.steps.ItemsSteps
import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.exec

object ItemsFlows {
    fun browseItems(): ChainBuilder =
        exec(ItemsSteps.withItemsData())
            .exec(ItemsRequests.getItems())
}
