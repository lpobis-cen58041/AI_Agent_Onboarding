package cz.example.perf

import cz.example.perf.usecases.SampleUseCases
import kotlin.test.Test
import kotlin.test.assertEquals

class WeightSumTest {
    @Test
    fun `use case weights sum to 100`() {
        assertEquals(100, SampleUseCases.all.sumOf { it.weight })
    }
}
