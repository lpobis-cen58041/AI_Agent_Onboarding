package cz.example.perf.config

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class ArrivalRateTest {
    @Test
    fun `default is two new users per second`() {
        assertEquals(2.0, resolveUsersPerSecond { null })
    }

    @Test
    fun `legacy input remains supported`() {
        assertEquals(0.5, resolveUsersPerSecond(mapOf("targetRps" to "0.5")::get))
    }

    @Test
    fun `explicit arrival rate takes precedence over legacy input`() {
        val properties = mapOf("targetRps" to "9", "usersPerSecond" to "1.5")
        assertEquals(1.5, resolveUsersPerSecond(properties::get))
    }

    @Test
    fun `invalid input never silently falls back`() {
        for (key in listOf("usersPerSecond", "targetRps")) {
            for (value in listOf("", "bad", "0", "-1", "NaN", "Infinity", "1e309")) {
                assertFailsWith<IllegalArgumentException>("$key=$value") {
                    resolveUsersPerSecond(mapOf(key to value)::get)
                }
            }
        }
        assertFailsWith<IllegalArgumentException> {
            resolveUsersPerSecond(mapOf("usersPerSecond" to "", "targetRps" to "2")::get)
        }
    }
}
