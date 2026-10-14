package cz.example.perf.usecases

import cz.example.perf.flows.SampleFlows
import cz.example.perf.setup.UseCase

object SampleUseCases {
    val all = listOf(UseCase("browseItems", 100) { SampleFlows.browseItems })
}
