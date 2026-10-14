package cz.example.perf.domain.items.steps

import cz.example.perf.auth.Auth
import cz.example.perf.domain.items.data.ItemsFeeders
import io.gatling.javaapi.core.ChainBuilder
import io.gatling.javaapi.core.CoreDsl.feed

object ItemsSteps {
    fun withItemsData(): ChainBuilder = feed(ItemsFeeders.users).exec(Auth.withTokenFromSession())
}
