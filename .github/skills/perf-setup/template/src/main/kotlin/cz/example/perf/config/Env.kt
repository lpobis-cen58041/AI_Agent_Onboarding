package cz.example.perf.config

import java.util.Properties

/** Loads endpoint paths from env/<env>.properties (-Denv=test|prod, default test). */
object Env {
    val name: String =
        (System.getProperty("env") ?: System.getenv("env"))
            ?.trim()?.lowercase()?.takeIf { it.isNotBlank() } ?: "test"

    private val props: Properties = Properties().apply {
        val resource = "env/$name.properties"
        val stream = Thread.currentThread().contextClassLoader.getResourceAsStream(resource)
            ?: error("Env resource not found on classpath: $resource")
        stream.reader(Charsets.UTF_8).use { load(it) }
    }

    operator fun get(key: String): String =
        props.getProperty(key) ?: error("Missing key '$key' in env/$name.properties")
}
