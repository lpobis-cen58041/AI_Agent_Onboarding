package cz.example.perf.setup

import cz.example.perf.domain.items.usecases.ItemsUseCases
import cz.example.perf.testutil.GatlingTestBootstrap
import kotlin.test.Test
import kotlin.test.assertEquals

class WeightSumTest {
    @Test
    fun `items use case weights sum to 100`() {
        GatlingTestBootstrap.init()
        assertEquals(100.0, ItemsUseCases.all.sumOf { it.defaultWeight }, 0.0001)
    }
}
