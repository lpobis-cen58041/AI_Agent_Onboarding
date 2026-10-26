package cz.example.perf.setup

import cz.example.perf.testutil.GatlingTestBootstrap
import io.gatling.javaapi.core.CoreDsl.exec
import kotlin.test.Test
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull

class MixBuilderTest {
    @Test
    fun `empty mix is rejected`() {
        assertFailsWith<IllegalArgumentException> { MixBuilder.fromDefaults(emptyList()) }
    }

    @Test
    fun `enabled weights must sum to 100`() {
        GatlingTestBootstrap.init()
        val useCase = UseCase("synthetic", exec { session -> session }, 90.0)
        assertFailsWith<IllegalArgumentException> { MixBuilder.fromDefaults(listOf(useCase)) }
    }

    @Test
    fun `single enabled use case at 100 is accepted`() {
        GatlingTestBootstrap.init()
        val useCase = UseCase("synthetic", exec { session -> session }, 100.0)
        assertNotNull(MixBuilder.fromDefaults(listOf(useCase)))
    }
}
