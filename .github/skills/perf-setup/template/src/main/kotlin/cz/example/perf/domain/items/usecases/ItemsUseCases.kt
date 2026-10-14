package cz.example.perf.domain.items.usecases

import cz.example.perf.domain.items.flows.ItemsFlows
import cz.example.perf.setup.UseCase

object ItemsUseCases {
    val browseItems = UseCase("browseItems", ItemsFlows.browseItems(), 100.0)

    val all = listOf(browseItems)
}
