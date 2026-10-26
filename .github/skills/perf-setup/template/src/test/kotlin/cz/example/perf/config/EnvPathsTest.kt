package cz.example.perf.config

import java.util.Properties
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class EnvPathsTest {
    private fun load(resource: String): Properties {
        val stream = Thread.currentThread().contextClassLoader.getResourceAsStream(resource)
            ?: error("Missing classpath resource: $resource")
        return Properties().apply { stream.reader(Charsets.UTF_8).use { load(it) } }
    }

    @Test
    fun `test and prod declare the same keys`() {
        assertEquals(
            load("env/test.properties").stringPropertyNames(),
            load("env/prod.properties").stringPropertyNames()
        )
    }

    @Test
    fun `every env key resolves and looks like a path`() {
        val keys = load("env/test.properties").stringPropertyNames()
        keys.forEach { assertTrue(Env[it].startsWith("/"), "Env[$it] should start with /") }
    }
}
